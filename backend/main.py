import time
from typing import Optional
from urllib.parse import urlparse

import httpx
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, field_validator

app = FastAPI(title="Network Monitor")

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


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
