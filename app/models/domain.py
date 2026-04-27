from sqlalchemy import Column, String, DateTime, Float, Integer, Boolean, ForeignKey, JSON, Text
from sqlalchemy.dialects.postgresql import ARRAY, UUID
from datetime import datetime, timezone
import uuid
from app.models.base import Base

class User(Base):
    __tablename__ = "users"
    user_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

class Session(Base):
    __tablename__ = "sessions"
    session_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.user_id"), nullable=False)
    started_at = Column(DateTime(timezone=True), nullable=False)
    ended_at = Column(DateTime(timezone=True), nullable=False)
    trade_count = Column(Integer, default=0)
    win_rate = Column(Float, nullable=True)
    total_pnl = Column(Float, nullable=True)

class Trade(Base):
    __tablename__ = "trades"
    trade_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    session_id = Column(UUID(as_uuid=True), ForeignKey("sessions.session_id"), nullable=False)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.user_id"), nullable=False)
    asset = Column(String, nullable=False)
    asset_class = Column(String, nullable=False)
    direction = Column(String, nullable=False)
    entry_price = Column(Float, nullable=False)
    exit_price = Column(Float, nullable=True)
    quantity = Column(Float, nullable=False)
    entry_at = Column(DateTime(timezone=True), nullable=False)
    exit_at = Column(DateTime(timezone=True), nullable=True)
    status = Column(String, nullable=False)
    outcome = Column(String, nullable=True)
    pnl = Column(Float, nullable=True)
    plan_adherence = Column(Integer, nullable=True)
    emotional_state = Column(String, nullable=True)
    entry_rationale = Column(Text, nullable=True)
    revenge_flag = Column(Boolean, default=False)

class MemorySession(Base):
    __tablename__ = "memory_sessions"
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.user_id"), primary_key=True)
    session_id = Column(UUID(as_uuid=True), ForeignKey("sessions.session_id"), primary_key=True)
    summary = Column(Text, nullable=False)
    metrics_json = Column(JSON, nullable=False)
    tags = Column(ARRAY(String), nullable=False, default=list)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

class Profile(Base):
    __tablename__ = "profiles"
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.user_id"), primary_key=True)
    profile_json = Column(JSON, nullable=False)
    generated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
