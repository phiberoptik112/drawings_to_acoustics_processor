"""
Database migration script to add drawing_id column to spaces table
"""

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from .database import initialize_database, get_session
import logging
import os

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def add_drawing_id_column():
    """
    Add drawing_id column to spaces table
    """
    logger.info("Adding drawing_id column to spaces table...")
    
    # Initialize database if not already done
    try:
        session = get_session()
    except RuntimeError:
        # Database not initialized, so initialize it
        db_path = initialize_database()
        logger.info(f"Initialized database at: {db_path}")
        session = get_session()
    
    try:
        # Check if column already exists
        result = session.execute(text("PRAGMA table_info(spaces)"))
        columns = [row[1] for row in result.fetchall()]
        
        if 'drawing_id' in columns:
            logger.info("drawing_id column already exists")
            session.close()
            return
        
        # Add the drawing_id column
        logger.info("Adding drawing_id column...")
        session.execute(text("ALTER TABLE spaces ADD COLUMN drawing_id INTEGER"))
        
        # Add foreign key constraint (SQLite doesn't support adding FK constraints after table creation,
        # but we'll handle this through the ORM)
        
        session.commit()
        logger.info("Successfully added drawing_id column to spaces table")
        
        # Verify the column was added
        result = session.execute(text("PRAGMA table_info(spaces)"))
        columns = [row[1] for row in result.fetchall()]
        if 'drawing_id' in columns:
            logger.info("✅ Column addition verified")
        else:
            logger.error("❌ Column addition failed")
        
    except Exception as e:
        logger.error(f"Migration failed: {e}")
        session.rollback()
        raise
    finally:
        session.close()


def remove_drawing_id_column():
    """
    Remove drawing_id column from spaces table (SQLite doesn't support DROP COLUMN)
    This would require recreating the table, so we'll skip it for now
    """
    logger.warning("SQLite doesn't support DROP COLUMN. To remove drawing_id, you would need to recreate the table.")


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "remove":
        remove_drawing_id_column()
    else:
        add_drawing_id_column()