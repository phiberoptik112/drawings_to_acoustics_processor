"""
Database migration script for surface materials
Migrates from single material fields to multiple materials system
"""

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from .database import Base, initialize_database, get_session
from .space import Space, SpaceSurfaceMaterial, SurfaceType
import logging
import os

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def migrate_surface_materials():
    """
    Migrate existing single surface materials to new multiple materials system
    """
    logger.info("Starting surface materials migration...")
    
    # Initialize database if not already done
    try:
        session = get_session()
    except RuntimeError:
        # Database not initialized, so initialize it
        db_path = initialize_database()
        logger.info(f"Initialized database at: {db_path}")
        session = get_session()
    
    try:
        # Tables are created automatically by initialize_database
        logger.info("Database ready for migration...")
        
        # Get all spaces that need migration
        spaces_to_migrate = session.query(Space).filter(
            (Space.ceiling_material.isnot(None)) |
            (Space.wall_material.isnot(None)) |
            (Space.floor_material.isnot(None))
        ).all()
        
        logger.info(f"Found {len(spaces_to_migrate)} spaces to migrate")
        
        migration_count = 0
        for space in spaces_to_migrate:
            logger.info(f"Migrating space: {space.name} (ID: {space.id})")
            
            # Check if this space already has new materials
            existing_materials = session.query(SpaceSurfaceMaterial).filter(
                SpaceSurfaceMaterial.space_id == space.id
            ).count()
            
            if existing_materials > 0:
                logger.info(f"  Space {space.id} already has new materials, skipping...")
                continue
            
            # Migrate legacy materials
            migrations = []
            
            if space.ceiling_material:
                logger.info(f"  Migrating ceiling material: {space.ceiling_material}")
                migrations.append(SpaceSurfaceMaterial(
                    space_id=space.id,
                    surface_type=SurfaceType.CEILING,
                    material_key=space.ceiling_material,
                    order_index=0
                ))
            
            if space.wall_material:
                logger.info(f"  Migrating wall material: {space.wall_material}")
                migrations.append(SpaceSurfaceMaterial(
                    space_id=space.id,
                    surface_type=SurfaceType.WALL,
                    material_key=space.wall_material,
                    order_index=0
                ))
            
            if space.floor_material:
                logger.info(f"  Migrating floor material: {space.floor_material}")
                migrations.append(SpaceSurfaceMaterial(
                    space_id=space.id,
                    surface_type=SurfaceType.FLOOR,
                    material_key=space.floor_material,
                    order_index=0
                ))
            
            # Add new material records
            for material in migrations:
                session.add(material)
            
            migration_count += 1
        
        # Commit all changes
        session.commit()
        logger.info(f"Migration completed successfully! Migrated {migration_count} spaces.")
        
        # Verify migration
        total_surface_materials = session.query(SpaceSurfaceMaterial).count()
        logger.info(f"Total surface materials in database: {total_surface_materials}")
        
    except Exception as e:
        logger.error(f"Migration failed: {e}")
        session.rollback()
        raise
    finally:
        session.close()


def rollback_migration():
    """
    Rollback migration by deleting all surface materials records
    WARNING: This will delete all multiple materials data!
    """
    logger.warning("ROLLBACK: Deleting all surface materials...")
    
    try:
        session = get_session()
    except RuntimeError:
        initialize_database()
        session = get_session()
    
    try:
        # Delete all surface materials
        deleted_count = session.query(SpaceSurfaceMaterial).delete()
        session.commit()
        logger.info(f"Rollback completed. Deleted {deleted_count} surface material records.")
        
    except Exception as e:
        logger.error(f"Rollback failed: {e}")
        session.rollback()
        raise
    finally:
        session.close()


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "rollback":
        rollback_migration()
    else:
        migrate_surface_materials()