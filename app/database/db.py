"""
Database connection and session management.
Uses SQLAlchemy with PostgreSQL.
"""

import logging
from typing import Generator

from sqlalchemy import create_engine, event
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import NullPool

from app.config import settings

logger = logging.getLogger(__name__)

# Create SQLAlchemy engine
engine = create_engine(
    settings.database_url,
    echo=settings.sqlalchemy_echo,
    pool_size=10,
    max_overflow=20,
    pool_recycle=3600,  # Recycle connections every hour
    pool_pre_ping=True,  # Verify connections before using
    poolclass=NullPool if settings.environment == "development" else None,
)

# Configure event listeners for engine
@event.listens_for(engine, "connect")
def receive_connect(dbapi_conn, connection_record):
    """Enable UUID support in PostgreSQL."""
    dbapi_conn.execute("CREATE EXTENSION IF NOT EXISTS \"uuid-ossp\"")


# Create session factory
SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
)

# Base class for models
Base = declarative_base()


def get_db() -> Generator[Session, None, None]:
    """
    Dependency for FastAPI or async functions to get database session.
    
    Yields:
        SQLAlchemy Session
        
    Example:
        for session in get_db():
            # use session
    """
    db = SessionLocal()
    try:
        yield db
    except Exception as e:
        logger.error(f"Database session error: {e}")
        db.rollback()
        raise
    finally:
        db.close()


def init_db():
    """
    Initialize database tables.
    Create all tables defined in models.
    """
    try:
        Base.metadata.create_all(bind=engine)
        logger.info("Database tables created successfully")
    except Exception as e:
        logger.error(f"Failed to initialize database: {e}")
        raise


def drop_all_tables():
    """
    Drop all database tables.
    WARNING: This is destructive and should only be used in development.
    """
    if settings.environment != "development":
        raise RuntimeError("Cannot drop tables outside of development environment")
    
    try:
        Base.metadata.drop_all(bind=engine)
        logger.warning("All database tables dropped")
    except Exception as e:
        logger.error(f"Failed to drop database tables: {e}")
        raise


def get_session() -> Session:
    """
    Get a new database session.
    For use in non-async contexts.
    
    Returns:
        SQLAlchemy Session
    """
    return SessionLocal()


def close_db():
    """Close database connection pool."""
    engine.dispose()
    logger.info("Database connection pool closed")

