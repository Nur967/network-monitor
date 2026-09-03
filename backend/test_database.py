"""Tests for database models and operations."""

import pytest
import tempfile
import os
from datetime import datetime
from sqlalchemy import create_engine, inspect
from sqlalchemy.orm import sessionmaker

from database import Base
from models import MonitoringTarget, CheckHistory


# Create a temporary database for testing
@pytest.fixture
def test_db():
    """Create a temporary SQLite database for testing."""
    # Create a temporary file
    temp_fd, temp_db_path = tempfile.mkstemp(suffix=".db")
    os.close(temp_fd)
    
    # Create engine for test database
    db_url = f"sqlite:///{temp_db_path}"
    engine = create_engine(db_url, connect_args={"check_same_thread": False})
    
    # Create tables
    Base.metadata.create_all(bind=engine)
    
    # Create session factory
    TestSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    session = TestSessionLocal()
    
    yield session
    
    # Cleanup
    session.close()
    try:
        os.unlink(temp_db_path)
    except OSError:
        pass


class TestDatabaseTables:
    """Test that database tables are created correctly."""
    
    def test_tables_created(self, test_db):
        """Test that tables are created in the database."""
        inspector = inspect(test_db.get_bind())
        tables = inspector.get_table_names()
        
        assert "monitoring_targets" in tables
        assert "check_history" in tables
    
    def test_monitoring_targets_schema(self, test_db):
        """Test that monitoring_targets table has correct columns."""
        inspector = inspect(test_db.get_bind())
        columns = {col["name"]: col for col in inspector.get_columns("monitoring_targets")}
        
        assert "id" in columns
        assert "url" in columns
        assert "created_at" in columns
        
        # Check id is primary key
        pk_columns = inspector.get_pk_constraint("monitoring_targets")["constrained_columns"]
        assert "id" in pk_columns
    
    def test_check_history_schema(self, test_db):
        """Test that check_history table has correct columns."""
        inspector = inspect(test_db.get_bind())
        columns = {col["name"]: col for col in inspector.get_columns("check_history")}
        
        assert "id" in columns
        assert "target_id" in columns
        assert "online" in columns
        assert "status_code" in columns
        assert "response_time_ms" in columns
        assert "error" in columns
        assert "checked_at" in columns
        
        # Check id is primary key
        pk_columns = inspector.get_pk_constraint("check_history")["constrained_columns"]
        assert "id" in pk_columns


class TestMonitoringTarget:
    """Test MonitoringTarget model."""
    
    def test_create_monitoring_target(self, test_db):
        """Test creating a monitoring target."""
        target = MonitoringTarget(url="https://example.com")
        test_db.add(target)
        test_db.commit()
        test_db.refresh(target)
        
        assert target.id is not None
        assert target.url == "https://example.com"
        assert target.created_at is not None
        assert isinstance(target.created_at, datetime)
    
    def test_monitoring_target_url_is_unique(self, test_db):
        """Test that URL field has unique constraint."""
        target1 = MonitoringTarget(url="https://example.com")
        test_db.add(target1)
        test_db.commit()
        
        # Try to add another target with same URL
        target2 = MonitoringTarget(url="https://example.com")
        test_db.add(target2)
        
        from sqlalchemy.exc import IntegrityError
        with pytest.raises(IntegrityError):
            test_db.commit()
    
    def test_monitoring_target_url_is_required(self, test_db):
        """Test that URL field is required."""
        from sqlalchemy.exc import IntegrityError
        
        target = MonitoringTarget(url=None)
        test_db.add(target)
        
        with pytest.raises(IntegrityError):
            test_db.commit()
    
    def test_monitoring_target_creation_time_auto_set(self, test_db):
        """Test that created_at is automatically set."""
        target = MonitoringTarget(url="https://example.com")
        test_db.add(target)
        test_db.commit()
        
        assert target.created_at is not None
        assert isinstance(target.created_at, datetime)
    
    def test_retrieve_monitoring_target(self, test_db):
        """Test retrieving a monitoring target from database."""
        # Add a target
        target = MonitoringTarget(url="https://example.com")
        test_db.add(target)
        test_db.commit()
        target_id = target.id
        
        # Clear session to force fresh query
        test_db.expunge_all()
        
        # Retrieve it
        retrieved = test_db.query(MonitoringTarget).filter(
            MonitoringTarget.id == target_id
        ).first()
        
        assert retrieved is not None
        assert retrieved.id == target_id
        assert retrieved.url == "https://example.com"


class TestCheckHistory:
    """Test CheckHistory model."""
    
    def test_create_check_history(self, test_db):
        """Test creating a check history record."""
        # First create a monitoring target
        target = MonitoringTarget(url="https://example.com")
        test_db.add(target)
        test_db.commit()
        
        # Create check history
        check = CheckHistory(
            target_id=target.id,
            online=True,
            status_code=200,
            response_time_ms=125.5,
            error=None
        )
        test_db.add(check)
        test_db.commit()
        test_db.refresh(check)
        
        assert check.id is not None
        assert check.target_id == target.id
        assert check.online is True
        assert check.status_code == 200
        assert check.response_time_ms == 125.5
        assert check.error is None
        assert check.checked_at is not None
    
    def test_check_history_checked_at_auto_set(self, test_db):
        """Test that checked_at is automatically set."""
        target = MonitoringTarget(url="https://example.com")
        test_db.add(target)
        test_db.commit()
        
        check = CheckHistory(
            target_id=target.id,
            online=True,
            status_code=200,
            response_time_ms=100.0
        )
        test_db.add(check)
        test_db.commit()
        
        assert check.checked_at is not None
        assert isinstance(check.checked_at, datetime)
    
    def test_check_history_with_error(self, test_db):
        """Test creating check history with error."""
        target = MonitoringTarget(url="https://example.com")
        test_db.add(target)
        test_db.commit()
        
        check = CheckHistory(
            target_id=target.id,
            online=False,
            status_code=None,
            response_time_ms=5000.0,
            error="Connection timeout"
        )
        test_db.add(check)
        test_db.commit()
        test_db.refresh(check)
        
        assert check.online is False
        assert check.status_code is None
        assert check.error == "Connection timeout"
    
    def test_check_history_target_relationship(self, test_db):
        """Test that check history is linked to target."""
        # Create target
        target = MonitoringTarget(url="https://example.com")
        test_db.add(target)
        test_db.commit()
        target_id = target.id
        
        # Create checks
        check1 = CheckHistory(target_id=target_id, online=True, status_code=200)
        check2 = CheckHistory(target_id=target_id, online=False, error="Timeout")
        test_db.add(check1)
        test_db.add(check2)
        test_db.commit()
        
        # Clear session
        test_db.expunge_all()
        
        # Retrieve target with checks
        retrieved_target = test_db.query(MonitoringTarget).filter(
            MonitoringTarget.id == target_id
        ).first()
        
        assert len(retrieved_target.checks) == 2
        assert retrieved_target.checks[0].online is True
        assert retrieved_target.checks[1].online is False
    
    def test_multiple_checks_for_same_target(self, test_db):
        """Test storing multiple checks for the same target."""
        target = MonitoringTarget(url="https://example.com")
        test_db.add(target)
        test_db.commit()
        
        # Add multiple checks
        for i in range(3):
            check = CheckHistory(
                target_id=target.id,
                online=i % 2 == 0,  # Alternate online/offline
                status_code=200 if i % 2 == 0 else None,
                response_time_ms=100.0 + i * 10
            )
            test_db.add(check)
        
        test_db.commit()
        
        # Query all checks for this target
        checks = test_db.query(CheckHistory).filter(
            CheckHistory.target_id == target.id
        ).all()
        
        assert len(checks) == 3
        assert checks[0].online is True
        assert checks[1].online is False
        assert checks[2].online is True
    
    def test_check_history_requires_target_id(self, test_db):
        """Test that target_id is required."""
        from sqlalchemy.exc import IntegrityError
        
        check = CheckHistory(
            target_id=None,
            online=True,
            status_code=200
        )
        test_db.add(check)
        
        with pytest.raises(IntegrityError):
            test_db.commit()
    
    def test_query_checks_by_target(self, test_db):
        """Test querying checks by target."""
        # Create two targets
        target1 = MonitoringTarget(url="https://example1.com")
        target2 = MonitoringTarget(url="https://example2.com")
        test_db.add_all([target1, target2])
        test_db.commit()
        
        # Add checks to both targets
        check1 = CheckHistory(target_id=target1.id, online=True, status_code=200)
        check2 = CheckHistory(target_id=target1.id, online=False, error="Timeout")
        check3 = CheckHistory(target_id=target2.id, online=True, status_code=200)
        test_db.add_all([check1, check2, check3])
        test_db.commit()
        
        # Query checks for target1
        target1_checks = test_db.query(CheckHistory).filter(
            CheckHistory.target_id == target1.id
        ).all()
        
        assert len(target1_checks) == 2
        assert all(c.target_id == target1.id for c in target1_checks)
        
        # Query checks for target2
        target2_checks = test_db.query(CheckHistory).filter(
            CheckHistory.target_id == target2.id
        ).all()
        
        assert len(target2_checks) == 1
        assert target2_checks[0].target_id == target2.id


class TestDatabaseIntegration:
    """Integration tests for the database."""
    
    def test_cascade_delete_checks_when_target_deleted(self, test_db):
        """Test that checks are deleted when target is deleted."""
        # Create target with checks
        target = MonitoringTarget(url="https://example.com")
        test_db.add(target)
        test_db.commit()
        
        check1 = CheckHistory(target_id=target.id, online=True, status_code=200)
        check2 = CheckHistory(target_id=target.id, online=False, error="Error")
        test_db.add_all([check1, check2])
        test_db.commit()
        
        target_id = target.id
        
        # Delete target
        test_db.delete(target)
        test_db.commit()
        
        # Verify checks are also deleted
        remaining_checks = test_db.query(CheckHistory).filter(
            CheckHistory.target_id == target_id
        ).all()
        
        assert len(remaining_checks) == 0
    
    def test_full_workflow(self, test_db):
        """Test a complete workflow: create target, add checks, query."""
        # Create target
        target = MonitoringTarget(url="https://google.com")
        test_db.add(target)
        test_db.commit()
        
        # Add multiple checks
        results = [
            (True, 200, 150.5, None),
            (True, 200, 152.3, None),
            (False, None, 5000.0, "Request timeout"),
            (True, 200, 148.9, None),
        ]
        
        for online, status_code, response_time, error in results:
            check = CheckHistory(
                target_id=target.id,
                online=online,
                status_code=status_code,
                response_time_ms=response_time,
                error=error
            )
            test_db.add(check)
        
        test_db.commit()
        
        # Query and verify
        retrieved_target = test_db.query(MonitoringTarget).filter(
            MonitoringTarget.url == "https://google.com"
        ).first()
        
        assert retrieved_target is not None
        assert len(retrieved_target.checks) == 4
        
        # Count online checks
        online_checks = [c for c in retrieved_target.checks if c.online]
        assert len(online_checks) == 3
        
        # Count offline checks
        offline_checks = [c for c in retrieved_target.checks if not c.online]
        assert len(offline_checks) == 1
