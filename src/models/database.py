"""
Database setup and configuration using SQLAlchemy
Handles both development and bundled deployment scenarios
"""

from sqlalchemy import create_engine, event
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import os
import sys
import logging
from contextlib import contextmanager

# Configure module logger
logger = logging.getLogger(__name__)

# Import utilities for deployment detection
try:
    from utils import ensure_user_data_directory, is_bundled_executable, log_environment_info
except ImportError:
    # Fallback if utils not available - use ~/Library/Application Support (not Documents,
    # which is iCloud-synced and may have files evicted to cloud storage)
    def ensure_user_data_directory():
        user_dir = os.path.expanduser("~/Library/Application Support/AcousticAnalysis")
        os.makedirs(user_dir, exist_ok=True)
        return user_dir
    
    def is_bundled_executable():
        return getattr(sys, 'frozen', False)
    
    def log_environment_info():
        logger.info(f"Database initialization - Bundled: {is_bundled_executable()}")

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
				logger.info(f"Using custom database path from settings: {db_path}")
		except Exception as e:
			logger.warning(f"Could not load custom database path from settings: {e}")
		
		# If no custom path, use default
		if db_path is None:
			# Use ~/Library/Application Support — excluded from iCloud Drive sync so
			# macOS will never evict this file as a "dataless" iCloud placeholder.
			user_dir = ensure_user_data_directory()
			db_path = os.path.join(user_dir, "acoustic_analysis.db")
		
		# Ensure we're using the correct path - never use debug_data
		if "debug_data" in db_path:
			user_dir = os.path.expanduser("~/Library/Application Support/AcousticAnalysis")
			os.makedirs(user_dir, exist_ok=True)
			db_path = os.path.join(user_dir, "acoustic_analysis.db")
			logger.warning(f"Corrected database path from debug_data to: {db_path}")
		
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
		logger.info(f"Initializing database for bundled deployment: {db_path}")
	else:
		logger.info(f"Initializing database for development: {db_path}")
	
	# If engine already exists and is using the same path, don't reinitialize
	# This prevents reinitialization with wrong paths
	if engine is not None:
		current_url = str(engine.url)
		new_url = f'sqlite:///{db_path}'
		if current_url == new_url:
			logger.debug(f"Database already initialized with correct path: {db_path}")
			return db_path
		else:
			logger.warning(f"Database path changed from {current_url} to {new_url}")
			logger.info(f"Reinitializing with correct path: {db_path}")
	
	# Guard against iCloud-evicted (dataless) database files.
	# macOS can evict files in ~/Documents to iCloud to save space, leaving a
	# zero-block placeholder that reports a non-zero st_size but is unreadable.
	# Detect this before SQLAlchemy tries to open the file.
	if os.path.exists(db_path):
		stat = os.stat(db_path)
		if stat.st_size > 0 and stat.st_blocks == 0:
			raise RuntimeError(
				f"The database file appears to have been evicted to iCloud Drive and is "
				f"no longer available locally:\n\n{db_path}\n\n"
				f"To recover your data:\n"
				f"  1. Open Finder and navigate to the file's location.\n"
				f"  2. Right-click the file and choose 'Download Now'.\n"
				f"  3. Wait for the download to complete, then relaunch the application.\n\n"
				f"If iCloud Drive is not available, the data may be lost. "
				f"You can delete the placeholder file to start fresh."
			)

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
	from . import project, drawing, space, hvac, rt60_models, mechanical, drawing_sets, partition
	
	# Create all tables
	Base.metadata.create_all(bind=engine)
	
	# Run idempotent schema migrations for legacy DBs
	# Each migration should be idempotent (safe to run multiple times)
	migration_errors = []

	def run_migration(name, migration_func, *args):
		"""Run a migration and log any errors without crashing."""
		try:
			migration_func(*args)
			logger.debug(f"Migration '{name}' completed successfully")
		except Exception as e:
			migration_errors.append((name, str(e)))
			logger.warning(f"Migration '{name}' failed: {e}")

	# HVAC schema
	try:
		from .migrate_hvac_schema import ensure_hvac_schema
		run_migration("HVAC schema", ensure_hvac_schema)
	except ImportError:
		pass

	# Drawing sets schema
	try:
		from .migrate_drawing_sets import ensure_drawing_sets_schema
		run_migration("Drawing sets schema", ensure_drawing_sets_schema)
	except ImportError:
		pass

	# HVAC drawing sets association
	try:
		from .migrate_hvac_drawing_sets import ensure_hvac_drawing_sets_schema
		run_migration("HVAC drawing sets schema", ensure_hvac_drawing_sets_schema)
	except ImportError:
		pass

	# Spaces drawing set association
	try:
		from .migrate_space_drawing_sets import ensure_space_drawing_sets_schema
		run_migration("Space drawing sets schema", ensure_space_drawing_sets_schema)
	except ImportError:
		pass

	# Space polygon column
	try:
		from .migrate_space_polygon_schema import ensure_space_polygon_schema
		run_migration("Space polygon schema", ensure_space_polygon_schema)
	except ImportError:
		pass

	# Drawing element HVAC linkage
	try:
		from .migrate_drawing_element_hvac import ensure_drawing_element_hvac_schema
		run_migration("Drawing element HVAC schema", ensure_drawing_element_hvac_schema)
	except ImportError:
		pass

	# Partition isolation schema
	try:
		from .migrate_partition_schema import ensure_partition_schema
		run_migration("Partition schema", ensure_partition_schema)
	except ImportError:
		pass

	# Path element sequence column
	try:
		from .migrate_path_element_sequence import migrate_path_element_sequence_schema
		session = SessionLocal()
		try:
			run_migration("Path element sequence schema", migrate_path_element_sequence_schema, session)
		finally:
			session.close()
	except ImportError:
		pass

	# Log summary of migration issues
	if migration_errors:
		logger.error(f"Database migrations completed with {len(migration_errors)} errors:")
		for name, error in migration_errors:
			logger.error(f"  - {name}: {error}")
	
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
		logger.debug(f"HVAC session rolled back due to error: {e}")
		raise
	finally:
		try:
			session.close()
		except Exception as cleanup_error:
			logger.debug(f"Session cleanup error: {cleanup_error}")


def close_database():
	"""Close the database connection"""
	global engine
	if engine:
		engine.dispose()
		engine = None