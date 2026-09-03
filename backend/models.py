"""SQLAlchemy models for the Network Monitor."""

from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, Boolean, Float, DateTime, ForeignKey
from sqlalchemy.orm import relationship

from database import Base


class MonitoringTarget(Base):
    """Model for a URL monitoring target."""
    
    __tablename__ = "monitoring_targets"
    
    id = Column(Integer, primary_key=True, index=True)
    url = Column(String, unique=True, nullable=False, index=True)
    created_at = Column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))
    
    # Relationship to check history
    checks = relationship("CheckHistory", back_populates="target", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<MonitoringTarget(id={self.id}, url={self.url})>"


class CheckHistory(Base):
    """Model for storing URL check results."""
    
    __tablename__ = "check_history"
    
    id = Column(Integer, primary_key=True, index=True)
    target_id = Column(Integer, ForeignKey("monitoring_targets.id"), nullable=False, index=True)
    online = Column(Boolean, nullable=False)
    status_code = Column(Integer, nullable=True)
    response_time_ms = Column(Float, nullable=True)
    error = Column(String, nullable=True)
    checked_at = Column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))
    
    # Relationship to monitoring target
    target = relationship("MonitoringTarget", back_populates="checks")
    
    def __repr__(self):
        return f"<CheckHistory(id={self.id}, target_id={self.target_id}, online={self.online})>"
