"""Monitoring logic and scheduler management."""

import time
import logging
from typing import Optional, Tuple
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger
import httpx

from database import SessionLocal
from models import MonitoringTarget, CheckHistory

logger = logging.getLogger(__name__)

scheduler: Optional[BackgroundScheduler] = None


async def perform_check(url: str) -> Tuple[bool, Optional[int], Optional[float], Optional[str]]:
    """
    Perform an HTTP health check on a URL.
    
    Returns:
        Tuple of (online, status_code, response_time_ms, error)
    """
    start_time = time.time()
    
    try:
        async with httpx.AsyncClient(follow_redirects=True) as client:
            response = await client.get(url, timeout=5.0)
        
        elapsed_ms = (time.time() - start_time) * 1000
        return (True, response.status_code, round(elapsed_ms, 1), None)
    
    except httpx.TimeoutException:
        elapsed_ms = (time.time() - start_time) * 1000
        return (False, None, round(elapsed_ms, 1), "Request timeout (5 seconds exceeded)")
    
    except httpx.ConnectError:
        elapsed_ms = (time.time() - start_time) * 1000
        return (False, None, round(elapsed_ms, 1), "Connection failed")
    
    except httpx.RequestError as e:
        elapsed_ms = (time.time() - start_time) * 1000
        return (False, None, round(elapsed_ms, 1), f"Request failed: {str(e)}")
    
    except Exception as e:
        elapsed_ms = (time.time() - start_time) * 1000
        return (False, None, round(elapsed_ms, 1), f"Unexpected error: {str(e)}")


def perform_check_sync(url: str) -> Tuple[bool, Optional[int], Optional[float], Optional[str]]:
    """
    Synchronous wrapper for HTTP health check (for scheduler).
    """
    import asyncio
    
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        return loop.run_until_complete(perform_check(url))
    finally:
        loop.close()


def check_all_targets():
    """
    Check all monitoring targets and store results in CheckHistory.
    Called by the scheduler every 60 seconds.
    """
    db = SessionLocal()
    try:
        targets = db.query(MonitoringTarget).all()
        
        for target in targets:
            online, status_code, response_time_ms, error = perform_check_sync(target.url)
            
            check_record = CheckHistory(
                target_id=target.id,
                online=online,
                status_code=status_code,
                response_time_ms=response_time_ms,
                error=error,
            )
            db.add(check_record)
        
        db.commit()
        logger.info(f"Checked {len(targets)} monitoring targets")
    
    except Exception as e:
        logger.error(f"Error during scheduled check: {e}")
        db.rollback()
    
    finally:
        db.close()


def start_scheduler():
    """Start the background scheduler."""
    global scheduler
    
    if scheduler is not None:
        return
    
    scheduler = BackgroundScheduler()
    scheduler.add_job(
        check_all_targets,
        trigger=IntervalTrigger(seconds=60),
        id="check_all_targets",
        name="Check all monitoring targets",
        replace_existing=True,
    )
    scheduler.start()
    logger.info("Scheduler started")


def stop_scheduler():
    """Stop the background scheduler."""
    global scheduler
    
    if scheduler is not None:
        scheduler.shutdown(wait=True)
        scheduler = None
        logger.info("Scheduler stopped")
