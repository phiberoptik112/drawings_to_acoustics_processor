"""
Database setup and configuration using SQLAlchemy
Handles both development and bundled deployment scenarios
"""

from sqlalchemy import create_engine, event
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import os
import sys
from contextlib import contextmanager

# Import utilities for deployment detection
try:
    from utils import ensure_user_data_directory, is_bundled_executable, log_environment_info
except ImportError:
    # Fallback if utils not available - use correct user data directory
    def ensure_user_data_directory():
        # Always use the correct user data directory, not debug_data
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
		# Check for custom database path from settings
		try:
			from utils.settings_manager import get_settings_manager
			settings_manager = get_settings_manager()
			custom_path = settings_manager.get_database_path()
			if custom_path:
				db_path = custom_path
				print(f"Using custom database path from settings: {db_path}")
		except Exception as e:
			print(f"Warning: Could not load custom database path from settings: {e}")
		
		# If no custom path, use default
		if db_path is None:
			# Always use user's Documents directory for project database
			# This ensures user data persists and is accessible even after app updates
			user_dir = ensure_user_data_directory()
			db_path = os.path.join(user_dir, "acoustic_analysis.db")
		
		# Ensure we're using the correct path - never use debug_data
		# If somehow we got the wrong path, correct it
		if "debug_data" in db_path:
			user_dir = os.path.expanduser("~/Documents/AcousticAnalysis")
			os.makedirs(user_dir, exist_ok=True)
			db_path = os.path.join(user_dir, "acoustic_analysis.db")
			print(f"WARNING: Corrected database path from debug_data to: {db_path}")
		
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
	
	# If engine already exists and is using the same path, don't reinitialize
	# This prevents reinitialization with wrong paths
	if engine is not None:
		current_url = str(engine.url)
		new_url = f'sqlite:///{db_path}'
		if current_url == new_url:
			print(f"Database already initialized with correct path: {db_path}")
			return db_path
		else:
			print(f"WARNING: Database path changed from {current_url} to {new_url}")
			print(f"Reinitializing with correct path: {db_path}")
	
	# Create engine
	engine = create_engine(f'sqlite:///{db_path}', echo=False)
	
	# Enable foreign key constraints for SQLite
	@event.listens_for(engine, "connect")
	def set_sqlite_pragma(dbapi_connection, connection_record):
		cursor = dbapi_connection.cursor()
		cursor.execute("PRAGMA foreign_keys=ON")
		cursor.close()
	
	# Create session factory
	# expire_on_commit=False prevents ORM instances used by the UI from
	# expiring their loaded attributes after commit, which otherwise causes
	# detached refresh errors once the session is closed.
	SessionLocal = sessionmaker(
		autocommit=False,
		autoflush=False,
		expire_on_commit=False,
		bind=engine,
	)
	
	# Import all models to ensure they're registered
	from . import project, drawing, space, hvac, rt60_models, mechanical, drawing_sets
	
	# Create all tables
	Base.metadata.create_all(bind=engine)
	
	# Run idempotent schema migrations for legacy DBs
	try:
		from .migrate_hvac_schema import ensure_hvac_schema
		ensure_hvac_schema()
	except Exception as e:
		# Avoid crashing startup; downstream code may still operate on fresh DBs
		# If migration fails, it will surface when querying; better to log minimal info here
		print(f"Warning: HVAC schema migration failed: {e}")
	
	# New: drawing sets schema/migration
	try:
		from .migrate_drawing_sets import ensure_drawing_sets_schema
		ensure_drawing_sets_schema()
	except Exception as e:
		print(f"Warning: Drawing sets schema migration failed: {e}")
	
	# New: HVAC paths drawing set association
	try:
		from .migrate_hvac_drawing_sets import ensure_hvac_drawing_sets_schema
		ensure_hvac_drawing_sets_schema()
	except Exception as e:
		print(f"Warning: HVAC drawing sets schema migration failed: {e}")
	
	# New: Spaces drawing set association
	try:
		from .migrate_space_drawing_sets import ensure_space_drawing_sets_schema
		ensure_space_drawing_sets_schema()
	except Exception as e:
		print(f"Warning: Space drawing sets schema migration failed: {e}")
	
	# New: space polygon column migration
	try:
		from .migrate_space_polygon_schema import ensure_space_polygon_schema
		ensure_space_polygon_schema()
	except Exception as e:
		print(f"Warning: Space polygon schema migration failed: {e}")
	
	# New: drawing element HVAC linkage columns
	try:
		from .migrate_drawing_element_hvac import ensure_drawing_element_hvac_schema
		ensure_drawing_element_hvac_schema()
	except Exception as e:
		print(f"Warning: Drawing element HVAC schema migration failed: {e}")
	
	return db_path


def get_session():
	"""Get a new database session"""
	if SessionLocal is None:
		raise RuntimeError("Database not initialized. Call initialize_database() first.")
	return SessionLocal()


@contextmanager
def get_hvac_session():
	"""Context manager for HVAC operations with proper cleanup and error handling
	
	This should be used for all HVAC-related database operations to ensure
	consistent session handling and proper cleanup.
	
	Usage:
		with get_hvac_session() as session:
			# All DB operations
			pass
	"""
	session = get_session()
	try:
		yield session
		session.commit()
	except Exception as e:
		session.rollback()
		print(f"DEBUG: HVAC session rolled back due to error: {e}")
		raise
	finally:
		try:
			session.close()
		except Exception as cleanup_error:
			print(f"DEBUG: Session cleanup error: {cleanup_error}")


def close_database():
	"""Close the database connection"""
	global engine
	if engine:
		engine.dispose()
		engine = None