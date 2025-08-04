"""
Database migration script for space-drawing relationships
Sets drawing_id for existing spaces based on their RoomBoundary relationships
"""

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from .database import Base, initialize_database, get_session
from .space import Space
from .drawing import Drawing
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def migrate_space_drawings():
    """
    Migrate existing spaces to set drawing_id based on RoomBoundary relationships
    """
    logger.info("Starting space-drawing relationship migration...")
    
    # Initialize database if not already done
    try:
        session = get_session()
    except RuntimeError:
        # Database not initialized, so initialize it
        db_path = initialize_database()
        logger.info(f"Initialized database at: {db_path}")
        session = get_session()
    
    try:
        logger.info("Database ready for migration...")
        
        # Get all spaces that don't have drawing_id set
        spaces_to_migrate = session.query(Space).filter(
            Space.drawing_id.is_(None)
        ).all()
        
        logger.info(f"Found {len(spaces_to_migrate)} spaces to migrate")
        
        migration_count = 0
        for space in spaces_to_migrate:
            logger.info(f"Migrating space: {space.name} (ID: {space.id})")
            
            if not space.room_boundaries:
                logger.warning(f"  Space {space.id} has no room boundaries, skipping...")
                continue
            
            # Count boundaries per drawing
            drawing_counts = {}
            for boundary in space.room_boundaries:
                drawing_id = boundary.drawing_id
                drawing_counts[drawing_id] = drawing_counts.get(drawing_id, 0) + 1
            
            if not drawing_counts:
                logger.warning(f"  Space {space.id} has no valid drawing references, skipping...")
                continue
            
            # Set to the drawing with the most boundaries
            most_common_drawing = max(drawing_counts.items(), key=lambda x: x[1])[0]
            space.drawing_id = most_common_drawing
            
            # Get drawing name for logging
            drawing = session.query(Drawing).filter(Drawing.id == most_common_drawing).first()
            drawing_name = drawing.name if drawing else f"Drawing {most_common_drawing}"
            
            logger.info(f"  Set space {space.id} to drawing: {drawing_name} (ID: {most_common_drawing})")
            logger.info(f"  Boundary distribution: {drawing_counts}")
            
            migration_count += 1
        
        # Commit all changes
        session.commit()
        logger.info(f"Migration completed successfully! Migrated {migration_count} spaces.")
        
        # Verify migration
        total_spaces_with_drawings = session.query(Space).filter(Space.drawing_id.isnot(None)).count()
        logger.info(f"Total spaces with drawing assignments: {total_spaces_with_drawings}")
        
        # Show summary by drawing
        drawings_with_spaces = session.query(Drawing).filter(Drawing.spaces.any()).all()
        logger.info("Space distribution by drawing:")
        for drawing in drawings_with_spaces:
            space_count = len(drawing.spaces)
            space_names = [space.name for space in drawing.spaces]
            logger.info(f"  {drawing.name}: {space_count} spaces ({', '.join(space_names)})")
        
    except Exception as e:
        logger.error(f"Migration failed: {e}")
        session.rollback()
        raise
    finally:
        session.close()


def rollback_space_drawing_migration():
    """
    Rollback migration by clearing drawing_id from all spaces
    WARNING: This will remove all space-drawing relationships!
    """
    logger.warning("ROLLBACK: Clearing all space-drawing relationships...")
    
    try:
        session = get_session()
    except RuntimeError:
        initialize_database()
        session = get_session()
    
    try:
        # Clear drawing_id from all spaces
        updated_count = session.query(Space).update({Space.drawing_id: None})
        session.commit()
        logger.info(f"Rollback completed. Cleared drawing_id from {updated_count} spaces.")
        
    except Exception as e:
        logger.error(f"Rollback failed: {e}")
        session.rollback()
        raise
    finally:
        session.close()


def verify_space_drawing_relationships():
    """
    Verify the space-drawing relationships are correctly set
    """
    logger.info("Verifying space-drawing relationships...")
    
    try:
        session = get_session()
    except RuntimeError:
        initialize_database()
        session = get_session()
    
    try:
        # Check for orphaned spaces (no drawing_id)
        orphaned_spaces = session.query(Space).filter(Space.drawing_id.is_(None)).all()
        if orphaned_spaces:
            logger.warning(f"Found {len(orphaned_spaces)} spaces without drawing assignments:")
            for space in orphaned_spaces:
                logger.warning(f"  - {space.name} (ID: {space.id})")
        else:
            logger.info("✅ All spaces have drawing assignments")
        
        # Check for invalid drawing references
        all_spaces = session.query(Space).filter(Space.drawing_id.isnot(None)).all()
        invalid_refs = []
        for space in all_spaces:
            drawing = session.query(Drawing).filter(Drawing.id == space.drawing_id).first()
            if not drawing:
                invalid_refs.append(space)
        
        if invalid_refs:
            logger.error(f"Found {len(invalid_refs)} spaces with invalid drawing references:")
            for space in invalid_refs:
                logger.error(f"  - {space.name} (ID: {space.id}) -> Drawing ID: {space.drawing_id}")
        else:
            logger.info("✅ All drawing references are valid")
        
        # Show relationship summary
        drawings = session.query(Drawing).all()
        total_spaces = 0
        for drawing in drawings:
            space_count = len(drawing.spaces)
            total_spaces += space_count
            if space_count > 0:
                logger.info(f"📋 {drawing.name}: {space_count} spaces")
        
        logger.info(f"📊 Total: {total_spaces} space-drawing relationships")
        
    except Exception as e:
        logger.error(f"Verification failed: {e}")
        raise
    finally:
        session.close()


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1:
        if sys.argv[1] == "rollback":
            rollback_space_drawing_migration()
        elif sys.argv[1] == "verify":
            verify_space_drawing_relationships()
        else:
            print("Usage: python migrate_space_drawings.py [rollback|verify]")
    else:
        migrate_space_drawings()