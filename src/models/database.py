"""
Database setup and configuration using SQLAlchemy
Handles both development and bundled deployment scenarios
"""

from sqlalchemy import create_engine, event
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import os
import sys

# Import utilities for deployment detection
try:
    from utils import ensure_user_data_directory, is_bundled_executable, log_environment_info
except ImportError:
    # Fallback if utils not available
    def ensure_user_data_directory():
        user_dir = os.path.expanduser("~/Documents/AcousticAnalysis")
        os.makedirs(user_dir, exist_ok=True)
        return user_dir
    
    def is_bundled_executable():
        return getattr(sys, 'frozen', False)
    
    def log_environment_info():
        print(f"Database initialization - Bundled: {is_bundled_executable()}")

# Create base class for declarative models
Base = declarative_base()

# Global session factory
SessionLocal = None
engine = None


def initialize_database(db_path=None):
    """Initialize the database connection and create tables
    
    Handles both development and bundled deployment scenarios.
    User project data is always stored in Documents/AcousticAnalysis
    regardless of deployment type.
    """
    global engine, SessionLocal
    
    # Log environment info for debugging
    if os.environ.get('DEBUG'):
        log_environment_info()
    
    if db_path is None:
        # Always use user's Documents directory for project database
        # This ensures user data persists and is accessible even after app updates
        user_dir = ensure_user_data_directory()
        db_path = os.path.join(user_dir, "acoustic_analysis.db")
        
        # Create a README for users on first run
        readme_path = os.path.join(user_dir, "README.txt")
        if not os.path.exists(readme_path):
            with open(readme_path, 'w') as f:
                f.write("Acoustic Analysis Tool - User Data Directory\n\n")
                f.write("This directory contains your acoustic analysis projects and database.\n")
                f.write("DO NOT DELETE this directory unless you want to lose your project data.\n\n")
                f.write("Files in this directory:\n")
                f.write("- acoustic_analysis.db: Your project database\n")
                f.write("- Exported files from your analysis results\n\n")
                f.write("The application will recreate this database if deleted,\n")
                f.write("but all your existing projects will be lost.\n")
    
    if is_bundled_executable():
        print(f"Initializing database for bundled deployment: {db_path}")
    else:
        print(f"Initializing database for development: {db_path}")
    
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
    from . import project, drawing, space, hvac, rt60_models, mechanical
    
    # Create all tables
    Base.metadata.create_all(bind=engine)
    
    # Run idempotent HVAC schema migrations for legacy DBs
    try:
        from .migrate_hvac_schema import ensure_hvac_schema
        ensure_hvac_schema()
    except Exception as e:
        # Avoid crashing startup; downstream code may still operate on fresh DBs
        # If migration fails, it will surface when querying; better to log minimal info here
        print(f"Warning: HVAC schema migration failed: {e}")
    
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