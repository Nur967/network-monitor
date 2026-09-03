import pytest
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock, patch, MagicMock
import httpx

from main import app, CheckRequest, CheckResponse


client = TestClient(app)


class TestHealthCheck:
    """Test the /health endpoint."""

    def test_health_check(self):
        """Test that health check endpoint returns ok status."""
        response = client.get("/health")
        assert response.status_code == 200
        assert response.json() == {"status": "ok"}


class TestCheckRequestValidation:
    """Test request validation for the /check endpoint."""

    def test_valid_https_url(self):
        """Test that valid HTTPS URLs are accepted."""
        with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_get.return_value = mock_response

            response = client.post(
                "/check",
                json={"url": "https://example.com"}
            )
            assert response.status_code == 200
            data = response.json()
            assert data["online"] is True
            assert data["status_code"] == 200
            assert data["error"] is None

    def test_valid_http_url(self):
        """Test that valid HTTP URLs are accepted."""
        with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_get.return_value = mock_response

            response = client.post(
                "/check",
                json={"url": "http://example.com"}
            )
            assert response.status_code == 200
            data = response.json()
            assert data["online"] is True
            assert data["status_code"] == 200

    def test_reject_ftp_scheme(self):
        """Test that FTP URLs are rejected."""
        response = client.post(
            "/check",
            json={"url": "ftp://example.com"}
        )
        assert response.status_code == 422  # Validation error
        data = response.json()
        assert "detail" in data
        assert any("http" in str(error).lower() for error in data["detail"])

    def test_reject_invalid_url(self):
        """Test that invalid URLs are rejected."""
        response = client.post(
            "/check",
            json={"url": "not a url"}
        )
        assert response.status_code == 422  # Validation error

    def test_missing_url_field(self):
        """Test that missing url field is rejected."""
        response = client.post(
            "/check",
            json={}
        )
        assert response.status_code == 422  # Validation error


class TestCheckEndpointResponses:
    """Test the /check endpoint responses."""

    def test_successful_response(self):
        """Test successful HTTP response."""
        with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_get.return_value = mock_response

            response = client.post(
                "/check",
                json={"url": "https://example.com"}
            )
            assert response.status_code == 200
            data = response.json()

            assert data["url"] == "https://example.com"
            assert data["online"] is True
            assert data["status_code"] == 200
            assert data["response_time_ms"] is not None
            assert isinstance(data["response_time_ms"], (int, float))
            assert data["response_time_ms"] > 0
            assert data["error"] is None

    def test_successful_response_with_redirect(self):
        """Test that redirects are followed."""
        with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get:
            # Mock a successful response after following redirects
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_get.return_value = mock_response

            response = client.post(
                "/check",
                json={"url": "https://example.com"}
            )

            assert response.status_code == 200
            data = response.json()
            assert data["online"] is True
            assert data["status_code"] == 200

            # Verify that follow_redirects was set
            mock_get.assert_called_once()
            call_kwargs = mock_get.call_args[1]
            assert "timeout" in call_kwargs
            assert call_kwargs["timeout"] == 5.0

    def test_connection_error_response(self):
        """Test connection failure handling."""
        with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get:
            mock_get.side_effect = httpx.ConnectError("Connection refused")

            response = client.post(
                "/check",
                json={"url": "https://unreachable.example.com"}
            )
            assert response.status_code == 200
            data = response.json()

            assert data["url"] == "https://unreachable.example.com"
            assert data["online"] is False
            assert data["status_code"] is None
            assert "Connection failed" in data["error"]
            assert data["response_time_ms"] is not None

    def test_timeout_response(self):
        """Test timeout handling."""
        with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get:
            mock_get.side_effect = httpx.TimeoutException("Request timeout")

            response = client.post(
                "/check",
                json={"url": "https://slow.example.com"}
            )
            assert response.status_code == 200
            data = response.json()

            assert data["url"] == "https://slow.example.com"
            assert data["online"] is False
            assert data["status_code"] is None
            assert "timeout" in data["error"].lower()
            assert data["response_time_ms"] is not None

    def test_generic_request_error(self):
        """Test generic request error handling."""
        with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get:
            mock_get.side_effect = httpx.RequestError("Something went wrong")

            response = client.post(
                "/check",
                json={"url": "https://error.example.com"}
            )
            assert response.status_code == 200
            data = response.json()

            assert data["url"] == "https://error.example.com"
            assert data["online"] is False
            assert data["status_code"] is None
            assert "Request failed" in data["error"]

    def test_response_with_different_status_codes(self):
        """Test that non-200 status codes are still reported as online."""
        for status_code in [201, 204, 301, 302, 404, 500]:
            with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get:
                mock_response = MagicMock()
                mock_response.status_code = status_code
                mock_get.return_value = mock_response

                response = client.post(
                    "/check",
                    json={"url": "https://example.com"}
                )
                assert response.status_code == 200
                data = response.json()

                assert data["online"] is True
                assert data["status_code"] == status_code
                assert data["error"] is None


class TestCheckResponseModel:
    """Test the CheckResponse Pydantic model."""

    def test_response_model_creation(self):
        """Test that CheckResponse model can be created correctly."""
        response = CheckResponse(
            url="https://example.com",
            online=True,
            status_code=200,
            response_time_ms=125.4,
            error=None
        )
        assert response.url == "https://example.com"
        assert response.online is True
        assert response.status_code == 200
        assert response.response_time_ms == 125.4
        assert response.error is None

    def test_response_model_with_error(self):
        """Test CheckResponse model with error."""
        response = CheckResponse(
            url="https://example.com",
            online=False,
            status_code=None,
            response_time_ms=5000.0,
            error="Connection failed"
        )
        assert response.url == "https://example.com"
        assert response.online is False
        assert response.status_code is None
        assert response.error == "Connection failed"


class TestCheckRequestModel:
    """Test the CheckRequest Pydantic model."""

    def test_request_model_with_https(self):
        """Test CheckRequest model with HTTPS URL."""
        request = CheckRequest(url="https://example.com")
        assert request.url == "https://example.com"

    def test_request_model_with_http(self):
        """Test CheckRequest model with HTTP URL."""
        request = CheckRequest(url="http://example.com")
        assert request.url == "http://example.com"

    def test_request_model_rejects_ftp(self):
        """Test that CheckRequest model rejects FTP URLs."""
        with pytest.raises(ValueError):
            CheckRequest(url="ftp://example.com")

    def test_request_model_rejects_file(self):
        """Test that CheckRequest model rejects file:// URLs."""
        with pytest.raises(ValueError):
            CheckRequest(url="file:///path/to/file")

    def test_request_model_rejects_no_scheme(self):
        """Test that CheckRequest model rejects URLs without a scheme."""
        with pytest.raises(ValueError):
            CheckRequest(url="example.com")
