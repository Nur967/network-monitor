import time
from typing import Optional, List
from urllib.parse import urlparse

import httpx
from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, field_validator
from sqlalchemy.orm import Session

from database import init_db, get_db
from models import MonitoringTarget
from schemas import TargetCreate, TargetResponse

app = FastAPI(title="Network Monitor")

# Initialize database tables on startup
@app.on_event("startup")
def startup_event():
    """Initialize database on application startup."""
    init_db()

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
    start_time = time.time()
    
    try:
        async with httpx.AsyncClient(follow_redirects=True) as client:
            response = await client.get(request.url, timeout=5.0)
        
        elapsed_ms = (time.time() - start_time) * 1000
        
        return CheckResponse(
            url=request.url,
            online=True,
            status_code=response.status_code,
            response_time_ms=round(elapsed_ms, 1),
            error=None,
        )
    except httpx.TimeoutException:
        elapsed_ms = (time.time() - start_time) * 1000
        return CheckResponse(
            url=request.url,
            online=False,
            status_code=None,
            response_time_ms=round(elapsed_ms, 1),
            error="Request timeout (5 seconds exceeded)",
        )
    except httpx.ConnectError:
        elapsed_ms = (time.time() - start_time) * 1000
        return CheckResponse(
            url=request.url,
            online=False,
            status_code=None,
            response_time_ms=round(elapsed_ms, 1),
            error="Connection failed",
        )
    except httpx.RequestError as e:
        elapsed_ms = (time.time() - start_time) * 1000
        return CheckResponse(
            url=request.url,
            online=False,
            status_code=None,
            response_time_ms=round(elapsed_ms, 1),
            error=f"Request failed: {str(e)}",
        )
    except Exception as e:
        elapsed_ms = (time.time() - start_time) * 1000
        return CheckResponse(
            url=request.url,
            online=False,
            status_code=None,
            response_time_ms=round(elapsed_ms, 1),
            error=f"Unexpected error: {str(e)}",
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


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
