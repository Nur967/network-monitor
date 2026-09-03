import time
from typing import Optional, List
from urllib.parse import urlparse

import httpx
from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, field_validator
from sqlalchemy.orm import Session
from sqlalchemy import desc

from database import init_db, get_db
from models import MonitoringTarget, CheckHistory
from schemas import TargetCreate, TargetResponse, CheckHistoryResponse, MonitoringHistoryResponse, TargetStatsResponse
from monitoring import start_scheduler, stop_scheduler, perform_check

app = FastAPI(title="Network Monitor")

# Initialize database tables on startup
@app.on_event("startup")
def startup_event():
    """Initialize database on application startup."""
    init_db()
    start_scheduler()


@app.on_event("shutdown")
def shutdown_event():
    """Clean up on application shutdown."""
    stop_scheduler()

# Enable CORS for local React development server
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class CheckRequest(BaseModel):
    """Request model for URL health check."""
    url: str

    @field_validator('url')
    @classmethod
    def validate_url(cls, v: str) -> str:
        """Validate that URL has HTTP or HTTPS scheme."""
        parsed = urlparse(v)
        if parsed.scheme not in ('http', 'https'):
            raise ValueError("URL must start with http:// or https://")
        if not parsed.netloc:
            raise ValueError("Invalid URL format")
        return v


class CheckResponse(BaseModel):
    """Response model for URL health check."""
    url: str
    online: bool
    status_code: Optional[int] = None
    response_time_ms: Optional[float] = None
    error: Optional[str] = None


@app.get("/health")
def health_check():
    """Health check endpoint."""
    return {"status": "ok"}


@app.post("/check", response_model=CheckResponse)
async def check_url(request: CheckRequest) -> CheckResponse:
    """
    Check if a URL is online and responsive.
    
    Returns the HTTP status code, response time, and any errors encountered.
    """
    online, status_code, response_time_ms, error = await perform_check(request.url)
    
    return CheckResponse(
        url=request.url,
        online=online,
        status_code=status_code,
        response_time_ms=response_time_ms,
        error=error,
    )


# Monitoring target management endpoints
@app.post("/targets", response_model=TargetResponse, status_code=status.HTTP_201_CREATED)
def create_target(payload: TargetCreate, db: Session = Depends(get_db)):
    """Create a monitoring target. Reject duplicates and validate URL scheme."""
    # Check duplicate
    existing = db.query(MonitoringTarget).filter(MonitoringTarget.url == payload.url).first()
    if existing:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Target URL already exists")

    target = MonitoringTarget(url=payload.url)
    db.add(target)
    db.commit()
    db.refresh(target)

    return TargetResponse.from_orm(target)


@app.get("/targets", response_model=List[TargetResponse])
def list_targets(db: Session = Depends(get_db)):
    """Return all monitoring targets."""
    targets = db.query(MonitoringTarget).order_by(MonitoringTarget.id).all()
    return [TargetResponse.from_orm(t) for t in targets]


@app.delete("/targets/{target_id}")
def delete_target(target_id: int, db: Session = Depends(get_db)):
    """Delete a monitoring target; cascade deletes CheckHistory via relationship."""
    target = db.query(MonitoringTarget).filter(MonitoringTarget.id == target_id).first()
    if not target:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Target not found")

    db.delete(target)
    db.commit()
    return {"detail": "deleted"}


@app.post("/targets/{target_id}/check", response_model=CheckHistoryResponse)
async def check_target(target_id: int, db: Session = Depends(get_db)):
    """
    Immediately check a specific monitoring target.
    Store the result in CheckHistory and return it.
    """
    target = db.query(MonitoringTarget).filter(MonitoringTarget.id == target_id).first()
    if not target:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Target not found")
    
    online, status_code, response_time_ms, error = await perform_check(target.url)
    
    check_record = CheckHistory(
        target_id=target_id,
        online=online,
        status_code=status_code,
        response_time_ms=response_time_ms,
        error=error,
    )
    db.add(check_record)
    db.commit()
    db.refresh(check_record)
    
    return CheckHistoryResponse.from_orm(check_record)


@app.get("/targets/{target_id}/history", response_model=MonitoringHistoryResponse)
def get_target_history(target_id: int, db: Session = Depends(get_db)):
    """
    Get the latest 50 checks for a monitoring target.
    Ordered newest first.
    """
    target = db.query(MonitoringTarget).filter(MonitoringTarget.id == target_id).first()
    if not target:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Target not found")
    
    checks = db.query(CheckHistory).filter(
        CheckHistory.target_id == target_id
    ).order_by(desc(CheckHistory.checked_at)).limit(50).all()
    
    return MonitoringHistoryResponse(
        target_id=target_id,
        checks=[CheckHistoryResponse.from_orm(c) for c in checks],
    )


@app.get("/targets/{target_id}/stats", response_model=TargetStatsResponse)
def get_target_stats(target_id: int, db: Session = Depends(get_db)):
    """
    Get statistics for a monitoring target.
    Includes total checks, successful checks, uptime percentage, average response time.
    """
    target = db.query(MonitoringTarget).filter(MonitoringTarget.id == target_id).first()
    if not target:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Target not found")
    
    checks = db.query(CheckHistory).filter(
        CheckHistory.target_id == target_id
    ).all()
    
    total_checks = len(checks)
    
    if total_checks == 0:
        return TargetStatsResponse(
            target_id=target_id,
            total_checks=0,
            successful_checks=0,
            uptime_percentage=0.0,
            average_response_time_ms=None,
            last_checked_at=None,
            current_status=False,
        )
    
    successful_checks = len([c for c in checks if c.online])
    uptime_percentage = round((successful_checks / total_checks) * 100, 2)
    
    response_times = [c.response_time_ms for c in checks if c.response_time_ms is not None]
    average_response_time_ms = round(sum(response_times) / len(response_times), 1) if response_times else None
    
    last_check = max(checks, key=lambda c: c.checked_at)
    
    return TargetStatsResponse(
        target_id=target_id,
        total_checks=total_checks,
        successful_checks=successful_checks,
        uptime_percentage=uptime_percentage,
        average_response_time_ms=average_response_time_ms,
        last_checked_at=last_check.checked_at,
        current_status=last_check.online,
    )


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
