"""
SQLAlchemy models for the Scholarship Agent.
Defines database schema for scholarships, messages, and logs.
"""

import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import (
    Column,
    String,
    Text,
    DateTime,
    Boolean,
    Integer,
    Float,
    Enum,
    Index,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID, JSONB

from app.database.db import Base


class Scholarship(Base):
    """
    Main scholarship record.
    Stores extracted scholarship information.
    """

    __tablename__ = "scholarships"

    # Primary Key
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # Basic Information
    title = Column(String(500), nullable=False, index=True)
    country = Column(String(100), nullable=False, index=True)
    university = Column(String(300), nullable=False, index=True)

    # Scholarship Details
    degree_level = Column(String(50), nullable=False)  # Bachelor's, Master's, PhD
    benefits = Column(Text, nullable=True)  # JSON or formatted text
    eligibility = Column(Text, nullable=True)  # JSON or formatted text
    required_documents = Column(Text, nullable=True)  # JSON or formatted text

    # Dates
    application_deadline = Column(DateTime, nullable=True, index=True)
    posted_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # URLs and Links
    official_link = Column(String(1000), nullable=False, unique=True)
    application_url = Column(String(1000), nullable=True)

    # Application Process
    application_process = Column(Text, nullable=True)

    # Content
    summary = Column(Text, nullable=True)
    raw_content = Column(Text, nullable=True)  # Original scraped content

    # Processing Flags
    is_active = Column(Boolean, default=True, index=True)
    is_duplicate = Column(Boolean, default=False, index=True)
    duplicate_of_id = Column(UUID(as_uuid=True), nullable=True)  # Reference to original

    # Tracking
    source_url = Column(String(1000), nullable=True)  # Where we found it
    hash_value = Column(String(64), nullable=True, unique=True)  # For duplicate detection

    # Metadata
    metadata = Column(JSONB, nullable=True)  # Store additional extraction data

    __table_args__ = (
        Index("idx_scholarship_country_deadline", "country", "application_deadline"),
        Index("idx_scholarship_active", "is_active", "is_duplicate"),
        UniqueConstraint("official_link", name="uq_scholarship_link"),
    )

    def __repr__(self):
        return f"<Scholarship(id={self.id}, title={self.title}, country={self.country})>"


class TelegramMessage(Base):
    """
    Telegram message record.
    Tracks all messages sent to Telegram channels/groups.
    """

    __tablename__ = "telegram_messages"

    # Primary Key
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # Foreign Key
    scholarship_id = Column(UUID(as_uuid=True), nullable=False, index=True)

    # Message Content
    message_text = Column(Text, nullable=False)
    formatted_message = Column(Text, nullable=True)  # After grammar correction

    # Telegram Details
    telegram_message_id = Column(Integer, nullable=True)  # Message ID from Telegram
    telegram_chat_id = Column(String(100), nullable=False)  # Channel or Group ID
    telegram_chat_type = Column(String(20), nullable=False)  # 'channel' or 'group'

    # Status Tracking
    is_sent = Column(Boolean, default=False, index=True)
    sent_at = Column(DateTime, nullable=True, index=True)
    send_error = Column(Text, nullable=True)

    # Engagement
    view_count = Column(Integer, default=0)
    reaction_count = Column(Integer, default=0)
    forward_count = Column(Integer, default=0)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (
        Index("idx_telegram_sent", "is_sent", "sent_at"),
        Index("idx_telegram_scholarship", "scholarship_id"),
    )

    def __repr__(self):
        return f"<TelegramMessage(id={self.id}, scholarship_id={self.scholarship_id}, sent={self.is_sent})>"


class ProcessingLog(Base):
    """
    Processing log for tracking agent execution.
    Useful for debugging and monitoring.
    """

    __tablename__ = "processing_logs"

    # Primary Key
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # Processing Details
    agent_name = Column(String(100), nullable=False, index=True)
    action = Column(String(100), nullable=False)  # search, extract, grammar, etc.
    status = Column(String(20), nullable=False)  # success, failed, partial
    scholarship_id = Column(UUID(as_uuid=True), nullable=True)

    # Input and Output
    input_data = Column(JSONB, nullable=True)
    output_data = Column(JSONB, nullable=True)
    error_message = Column(Text, nullable=True)

    # Performance Metrics
    duration_seconds = Column(Float, nullable=True)
    tokens_used = Column(Integer, nullable=True)
    api_calls = Column(Integer, default=0)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    __table_args__ = (
        Index("idx_log_agent_action", "agent_name", "action"),
        Index("idx_log_status", "status"),
        Index("idx_log_timestamp", "created_at"),
    )

    def __repr__(self):
        return f"<ProcessingLog(agent={self.agent_name}, action={self.action}, status={self.status})>"


class DuplicateCache(Base):
    """
    Cache for duplicate detection.
    Stores scholarship hashes for quick comparison.
    """

    __tablename__ = "duplicate_cache"

    # Primary Key
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # Scholarship Reference
    scholarship_id = Column(UUID(as_uuid=True), nullable=False, unique=True, index=True)

    # Hash Values
    title_hash = Column(String(64), nullable=False, index=True)
    content_hash = Column(String(64), nullable=False, unique=True)
    combined_hash = Column(String(64), nullable=False)

    # Similarity Metadata
    similar_scholarships = Column(JSONB, nullable=True)  # List of similar scholarship IDs

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (
        Index("idx_duplicate_hashes", "title_hash", "content_hash"),
    )

    def __repr__(self):
        return f"<DuplicateCache(scholarship_id={self.scholarship_id})>"


class SchedulerRun(Base):
    """
    Track scheduler runs for monitoring and debugging.
    """

    __tablename__ = "scheduler_runs"

    # Primary Key
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # Run Details
    run_number = Column(Integer, nullable=False)  # Sequential run number
    scheduled_time = Column(DateTime, nullable=False)
    actual_start_time = Column(DateTime, default=datetime.utcnow)
    actual_end_time = Column(DateTime, nullable=True)

    # Results
    total_scholarships_found = Column(Integer, default=0)
    scholarships_processed = Column(Integer, default=0)
    scholarships_saved = Column(Integer, default=0)
    messages_sent = Column(Integer, default=0)
    errors_count = Column(Integer, default=0)

    # Status
    status = Column(String(20), nullable=False)  # running, completed, failed
    error_message = Column(Text, nullable=True)

    # Metadata
    execution_time_seconds = Column(Float, nullable=True)
    metadata = Column(JSONB, nullable=True)

    __table_args__ = (
        Index("idx_scheduler_run_time", "actual_start_time"),
        Index("idx_scheduler_status", "status"),
    )

    def __repr__(self):
        return f"<SchedulerRun(run={self.run_number}, status={self.status})>"

