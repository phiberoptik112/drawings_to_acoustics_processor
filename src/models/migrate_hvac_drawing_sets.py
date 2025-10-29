"""
Database migration to add drawing_set_id to hvac_paths table
"""

from sqlalchemy import text
from .database import get_session


def _add_column_if_missing(session, table_name, columns_to_add):
    """
    Add columns to table if they don't already exist.
    
    Args:
        session: SQLAlchemy session
        table_name: Name of table to modify
        columns_to_add: List of tuples (column_name, column_definition)
                       e.g., ("drawing_set_id", "INTEGER")
    """
    # Get existing columns
    result = session.execute(text(f"PRAGMA table_info({table_name})"))
    existing_columns = {row[1] for row in result.fetchall()}
    
    # Add missing columns
    for col_name, col_def in columns_to_add:
        if col_name not in existing_columns:
            print(f"Adding column {col_name} to {table_name}")
            session.execute(text(f"ALTER TABLE {table_name} ADD COLUMN {col_name} {col_def}"))
            session.commit()


def _populate_drawing_sets_for_existing_paths(session):
    """
    Best-effort population of drawing_set_id for existing paths.
    Derives drawing set from the path's components' drawings.
    """
    try:
        # Find paths without drawing_set_id
        query = text("""
            SELECT hp.id, hc.drawing_id
            FROM hvac_paths hp
            LEFT JOIN hvac_segments hs ON hs.hvac_path_id = hp.id
            LEFT JOIN hvac_components hc ON hc.id = hs.from_component_id
            WHERE hp.drawing_set_id IS NULL
            AND hc.drawing_id IS NOT NULL
            GROUP BY hp.id
            ORDER BY hp.id, hs.segment_order
        """)
        
        results = session.execute(query).fetchall()
        
        for path_id, drawing_id in results:
            if drawing_id:
                # Get drawing_set_id from the component's drawing
                drawing_set_query = text("""
                    SELECT drawing_set_id FROM drawings 
                    WHERE id = :drawing_id AND drawing_set_id IS NOT NULL
                    LIMIT 1
                """)
                drawing_set_result = session.execute(
                    drawing_set_query, 
                    {"drawing_id": drawing_id}
                ).fetchone()
                
                if drawing_set_result and drawing_set_result[0]:
                    drawing_set_id = drawing_set_result[0]
                    # Update the path with the derived drawing_set_id
                    update_query = text("""
                        UPDATE hvac_paths 
                        SET drawing_set_id = :drawing_set_id 
                        WHERE id = :path_id
                    """)
                    session.execute(
                        update_query, 
                        {"drawing_set_id": drawing_set_id, "path_id": path_id}
                    )
        
        session.commit()
        print(f"Populated drawing_set_id for {len(results)} existing paths")
        
    except Exception as e:
        print(f"Warning: Could not populate drawing sets for existing paths: {e}")
        session.rollback()


def ensure_hvac_drawing_sets_schema():
    """
    Ensure hvac_paths table has drawing_set_id column with proper foreign key.
    Also populates existing paths with drawing set information.
    """
    try:
        session = get_session()
        
        # Import models to ensure tables exist
        from . import project, drawing, space, hvac, rt60_models, mechanical, drawing_sets  # noqa: F401
        
        # Add drawing_set_id column to hvac_paths if missing
        _add_column_if_missing(
            session,
            "hvac_paths",
            [("drawing_set_id", "INTEGER")]
        )
        
        # Create index for efficient queries
        try:
            session.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_hvac_paths_drawing_set 
                ON hvac_paths(drawing_set_id)
            """))
            session.commit()
        except Exception as e:
            print(f"Index creation skipped or already exists: {e}")
        
        # Populate drawing_set_id for existing paths
        _populate_drawing_sets_for_existing_paths(session)
        
        session.close()
        print("HVAC drawing sets schema migration completed successfully")
        
    except Exception as e:
        print(f"Error during HVAC drawing sets migration: {e}")
        try:
            session.rollback()
            session.close()
        except:
            pass

