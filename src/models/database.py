"""
Database setup and configuration using SQLAlchemy
"""

from sqlalchemy import create_engine, event
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import os

# Create base class for declarative models
Base = declarative_base()

# Global session factory
SessionLocal = None
engine = None


def initialize_database(db_path=None):
    """Initialize the database connection and create tables"""
    global engine, SessionLocal
    
    if db_path is None:
        # Default to user's home directory
        db_dir = os.path.expanduser("~/Documents/AcousticAnalysis")
        os.makedirs(db_dir, exist_ok=True)
        db_path = os.path.join(db_dir, "acoustic_analysis.db")
    
    # Create engine
    engine = create_engine(f'sqlite:///{db_path}', echo=False)
    
    # Enable foreign key constraints for SQLite
    @event.listens_for(engine, "connect")
    def set_sqlite_pragma(dbapi_connection, connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()
    
    # Create session factory
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    
    # Import all models to ensure they're registered
    from . import project, drawing, space, hvac, rt60_models
    
    # Create all tables
    Base.metadata.create_all(bind=engine)
    
    return db_path


def get_session():
    """Get a new database session"""
    if SessionLocal is None:
        raise RuntimeError("Database not initialized. Call initialize_database() first.")
    return SessionLocal()


def close_database():
    """Close the database connection"""
    global engine
    if engine:
        engine.dispose()
        engine = None