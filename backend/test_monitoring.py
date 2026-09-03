"""Tests for monitoring endpoints and scheduler."""

import tempfile
import os
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from unittest.mock import AsyncMock, patch, MagicMock

import pytest

from main import app
import database
from models import MonitoringTarget, CheckHistory


@pytest.fixture
def client_with_temp_db():
    """Create a test client with a temporary database."""
    # Create temporary SQLite file
    temp_fd, temp_db_path = tempfile.mkstemp(suffix=".db")
    os.close(temp_fd)
    db_url = f"sqlite:///{temp_db_path}"

    # Patch database engine and SessionLocal
    engine = create_engine(db_url, connect_args={"check_same_thread": False})
    TestSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

    # Replace in module
    database.engine.dispose()
    database.engine = engine
    database.SessionLocal = TestSessionLocal

    # Initialize tables
    database.init_db()

    client = TestClient(app)

    yield client

    client.close()
    try:
        os.unlink(temp_db_path)
    except OSError:
        pass


class TestManualTargetCheck:
    """Test manual target check endpoint."""

    def test_check_target_success(self, client_with_temp_db):
        """Test checking a target that returns 200."""
        client = client_with_temp_db
        
        # Create target
        create_resp = client.post("/targets", json={"url": "https://example.com"})
        target_id = create_resp.json()["id"]
        
        # Mock successful check
        with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_get.return_value = mock_response
            
            response = client.post(f"/targets/{target_id}/check")
        
        assert response.status_code == 200
        data = response.json()
        assert data["target_id"] == target_id
        assert data["online"] is True
        assert data["status_code"] == 200
        assert data["error"] is None
        assert "checked_at" in data

    def test_check_target_failure(self, client_with_temp_db):
        """Test checking a target that times out."""
        client = client_with_temp_db
        
        # Create target
        create_resp = client.post("/targets", json={"url": "https://example.com"})
        target_id = create_resp.json()["id"]
        
        # Mock timeout
        with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get:
            mock_get.side_effect = Exception("Connection error")
            
            response = client.post(f"/targets/{target_id}/check")
        
        assert response.status_code == 200
        data = response.json()
        assert data["target_id"] == target_id
        assert data["online"] is False
        assert data["error"] is not None

    def test_check_nonexistent_target_returns_404(self, client_with_temp_db):
        """Test checking a target that doesn't exist."""
        client = client_with_temp_db
        
        response = client.post("/targets/99999/check")
        assert response.status_code == 404

    def test_check_stored_in_history(self, client_with_temp_db):
        """Test that check result is stored in CheckHistory."""
        client = client_with_temp_db
        
        # Create target
        create_resp = client.post("/targets", json={"url": "https://example.com"})
        target_id = create_resp.json()["id"]
        
        # Mock successful check
        with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_get.return_value = mock_response
            
            response = client.post(f"/targets/{target_id}/check")
        
        assert response.status_code == 200
        
        # Verify it's in history
        history_resp = client.get(f"/targets/{target_id}/history")
        assert history_resp.status_code == 200
        history_data = history_resp.json()
        assert len(history_data["checks"]) == 1


class TestMonitoringHistory:
    """Test monitoring history retrieval."""

    def test_get_empty_history(self, client_with_temp_db):
        """Test getting history for a target with no checks."""
        client = client_with_temp_db
        
        # Create target
        create_resp = client.post("/targets", json={"url": "https://example.com"})
        target_id = create_resp.json()["id"]
        
        # Get history
        response = client.get(f"/targets/{target_id}/history")
        
        assert response.status_code == 200
        data = response.json()
        assert data["target_id"] == target_id
        assert data["checks"] == []

    def test_get_history_returns_latest_50(self, client_with_temp_db):
        """Test that history returns latest 50 checks in reverse chronological order."""
        client = client_with_temp_db
        
        # Create target
        create_resp = client.post("/targets", json={"url": "https://example.com"})
        target_id = create_resp.json()["id"]
        
        # Create 75 checks manually
        db = database.SessionLocal()
        try:
            for i in range(75):
                check = CheckHistory(
                    target_id=target_id,
                    online=(i % 2 == 0),
                    status_code=200 if (i % 2 == 0) else None,
                    response_time_ms=100.0 + i,
                )
                db.add(check)
            db.commit()
        finally:
            db.close()
        
        # Get history
        response = client.get(f"/targets/{target_id}/history")
        
        assert response.status_code == 200
        data = response.json()
        assert len(data["checks"]) == 50
        
        # Verify they're ordered newest first
        for i in range(len(data["checks"]) - 1):
            assert data["checks"][i]["checked_at"] >= data["checks"][i + 1]["checked_at"]

    def test_get_history_nonexistent_target_returns_404(self, client_with_temp_db):
        """Test getting history for a nonexistent target."""
        client = client_with_temp_db
        
        response = client.get("/targets/99999/history")
        assert response.status_code == 404

    def test_history_includes_all_fields(self, client_with_temp_db):
        """Test that history includes all required fields."""
        client = client_with_temp_db
        
        # Create target
        create_resp = client.post("/targets", json={"url": "https://example.com"})
        target_id = create_resp.json()["id"]
        
        # Add check
        db = database.SessionLocal()
        try:
            check = CheckHistory(
                target_id=target_id,
                online=True,
                status_code=200,
                response_time_ms=125.5,
                error=None,
            )
            db.add(check)
            db.commit()
        finally:
            db.close()
        
        # Get history
        response = client.get(f"/targets/{target_id}/history")
        
        assert response.status_code == 200
        data = response.json()
        check_data = data["checks"][0]
        
        assert "online" in check_data
        assert "status_code" in check_data
        assert "response_time_ms" in check_data
        assert "error" in check_data
        assert "checked_at" in check_data


class TestTargetStatistics:
    """Test target statistics retrieval."""

    def test_get_stats_for_empty_target(self, client_with_temp_db):
        """Test getting stats for a target with no checks."""
        client = client_with_temp_db
        
        # Create target
        create_resp = client.post("/targets", json={"url": "https://example.com"})
        target_id = create_resp.json()["id"]
        
        # Get stats
        response = client.get(f"/targets/{target_id}/stats")
        
        assert response.status_code == 200
        data = response.json()
        assert data["target_id"] == target_id
        assert data["total_checks"] == 0
        assert data["successful_checks"] == 0
        assert data["uptime_percentage"] == 0.0
        assert data["average_response_time_ms"] is None
        assert data["last_checked_at"] is None
        assert data["current_status"] is False

    def test_uptime_calculation(self, client_with_temp_db):
        """Test uptime percentage calculation."""
        client = client_with_temp_db
        
        # Create target
        create_resp = client.post("/targets", json={"url": "https://example.com"})
        target_id = create_resp.json()["id"]
        
        # Add 10 checks: 7 successful, 3 failed
        db = database.SessionLocal()
        try:
            for i in range(7):
                check = CheckHistory(
                    target_id=target_id,
                    online=True,
                    status_code=200,
                    response_time_ms=100.0,
                )
                db.add(check)
            
            for i in range(3):
                check = CheckHistory(
                    target_id=target_id,
                    online=False,
                    status_code=None,
                    error="Connection error",
                )
                db.add(check)
            
            db.commit()
        finally:
            db.close()
        
        # Get stats
        response = client.get(f"/targets/{target_id}/stats")
        
        assert response.status_code == 200
        data = response.json()
        assert data["total_checks"] == 10
        assert data["successful_checks"] == 7
        assert data["uptime_percentage"] == 70.0

    def test_average_response_time(self, client_with_temp_db):
        """Test average response time calculation."""
        client = client_with_temp_db
        
        # Create target
        create_resp = client.post("/targets", json={"url": "https://example.com"})
        target_id = create_resp.json()["id"]
        
        # Add checks with specific response times
        db = database.SessionLocal()
        try:
            response_times = [100.0, 150.0, 120.0, 130.0]
            for rt in response_times:
                check = CheckHistory(
                    target_id=target_id,
                    online=True,
                    status_code=200,
                    response_time_ms=rt,
                )
                db.add(check)
            
            db.commit()
        finally:
            db.close()
        
        # Get stats
        response = client.get(f"/targets/{target_id}/stats")
        
        assert response.status_code == 200
        data = response.json()
        expected_avg = round(sum(response_times) / len(response_times), 1)
        assert data["average_response_time_ms"] == expected_avg

    def test_current_status_is_last_check(self, client_with_temp_db):
        """Test that current_status reflects the last check."""
        client = client_with_temp_db
        
        # Create target
        create_resp = client.post("/targets", json={"url": "https://example.com"})
        target_id = create_resp.json()["id"]
        
        # Add offline check
        db = database.SessionLocal()
        try:
            check1 = CheckHistory(
                target_id=target_id,
                online=False,
                error="Connection error",
            )
            db.add(check1)
            db.commit()
            
            import time
            time.sleep(0.01)  # Ensure different timestamp
            
            # Add online check (most recent)
            check2 = CheckHistory(
                target_id=target_id,
                online=True,
                status_code=200,
                response_time_ms=100.0,
            )
            db.add(check2)
            db.commit()
        finally:
            db.close()
        
        # Get stats
        response = client.get(f"/targets/{target_id}/stats")
        
        assert response.status_code == 200
        data = response.json()
        # Should reflect the most recent check
        assert data["current_status"] is True

    def test_stats_nonexistent_target_returns_404(self, client_with_temp_db):
        """Test getting stats for a nonexistent target."""
        client = client_with_temp_db
        
        response = client.get("/targets/99999/stats")
        assert response.status_code == 404


class TestCheckHistoryStorage:
    """Test that checks are properly stored in CheckHistory."""

    def test_multiple_checks_stored_for_same_target(self, client_with_temp_db):
        """Test that multiple checks are stored for the same target."""
        client = client_with_temp_db
        
        # Create target
        create_resp = client.post("/targets", json={"url": "https://example.com"})
        target_id = create_resp.json()["id"]
        
        # Perform multiple checks
        with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_get.return_value = mock_response
            
            for _ in range(3):
                response = client.post(f"/targets/{target_id}/check")
                assert response.status_code == 200
        
        # Verify all are stored
        history_resp = client.get(f"/targets/{target_id}/history")
        assert history_resp.status_code == 200
        data = history_resp.json()
        assert len(data["checks"]) == 3
