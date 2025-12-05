"""
Database migration to add HVAC linkage columns to drawing_elements table.

This migration adds hvac_path_id, hvac_segment_id, and hvac_component_id columns
to the drawing_elements table, enabling direct association between visual overlay
elements and their corresponding HVAC database records.
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


def _link_existing_elements_to_paths(session):
    """
    Best-effort linking of existing drawing elements to HVAC paths.
    
    This attempts to match drawing elements (components, segments) to their
    corresponding HVAC records based on position matching.
    """
    try:
        # Link component elements to HVACComponents by position
        print("Attempting to link existing component elements to HVAC components...")
        
        # Get all component drawing elements and HVAC components
        component_elements = session.execute(text("""
            SELECT de.id, de.x_position, de.y_position, de.drawing_id,
                   json_extract(de.properties, '$.component_type') as comp_type
            FROM drawing_elements de
            WHERE de.element_type = 'component'
            AND de.hvac_component_id IS NULL
        """)).fetchall()
        
        hvac_components = session.execute(text("""
            SELECT id, x_position, y_position, drawing_id, component_type
            FROM hvac_components
        """)).fetchall()
        
        # Build lookup dict for HVAC components by position
        hvac_comp_lookup = {}
        for hc in hvac_components:
            key = (hc[1], hc[2], hc[3], hc[4])  # x, y, drawing_id, type
            hvac_comp_lookup[key] = hc[0]  # id
        
        linked_components = 0
        for de in component_elements:
            de_id, x, y, drawing_id, comp_type = de
            key = (x, y, drawing_id, comp_type)
            if key in hvac_comp_lookup:
                hvac_comp_id = hvac_comp_lookup[key]
                session.execute(text("""
                    UPDATE drawing_elements 
                    SET hvac_component_id = :hvac_comp_id
                    WHERE id = :de_id
                """), {"hvac_comp_id": hvac_comp_id, "de_id": de_id})
                linked_components += 1
        
        if linked_components > 0:
            session.commit()
            print(f"Linked {linked_components} component elements to HVAC components")
        
        # Link segment elements to HVACSegments and their paths
        print("Attempting to link existing segment elements to HVAC segments...")
        
        segment_elements = session.execute(text("""
            SELECT de.id, 
                   json_extract(de.properties, '$.start_x') as start_x,
                   json_extract(de.properties, '$.start_y') as start_y,
                   json_extract(de.properties, '$.end_x') as end_x,
                   json_extract(de.properties, '$.end_y') as end_y,
                   de.drawing_id
            FROM drawing_elements de
            WHERE de.element_type = 'segment'
            AND de.hvac_segment_id IS NULL
        """)).fetchall()
        
        # Get HVAC segments with their component positions
        hvac_segments = session.execute(text("""
            SELECT hs.id, hs.hvac_path_id,
                   fc.x_position as from_x, fc.y_position as from_y,
                   tc.x_position as to_x, tc.y_position as to_y
            FROM hvac_segments hs
            JOIN hvac_components fc ON hs.from_component_id = fc.id
            JOIN hvac_components tc ON hs.to_component_id = tc.id
        """)).fetchall()
        
        linked_segments = 0
        tolerance = 15.0  # pixels tolerance for position matching
        
        for de in segment_elements:
            de_id, start_x, start_y, end_x, end_y, drawing_id = de
            if start_x is None or start_y is None:
                continue
                
            start_x, start_y = float(start_x), float(start_y)
            end_x, end_y = float(end_x or 0), float(end_y or 0)
            
            for hs in hvac_segments:
                hs_id, path_id, from_x, from_y, to_x, to_y = hs
                # Check if positions match within tolerance
                d1 = abs(start_x - from_x) + abs(start_y - from_y)
                d2 = abs(end_x - to_x) + abs(end_y - to_y)
                
                if d1 <= tolerance and d2 <= tolerance:
                    session.execute(text("""
                        UPDATE drawing_elements 
                        SET hvac_segment_id = :hs_id, hvac_path_id = :path_id
                        WHERE id = :de_id
                    """), {"hs_id": hs_id, "path_id": path_id, "de_id": de_id})
                    linked_segments += 1
                    break
        
        if linked_segments > 0:
            session.commit()
            print(f"Linked {linked_segments} segment elements to HVAC segments/paths")
        
        # Also link component elements to paths via their HVAC components
        print("Linking component elements to their HVAC paths...")
        session.execute(text("""
            UPDATE drawing_elements
            SET hvac_path_id = (
                SELECT DISTINCT hs.hvac_path_id
                FROM hvac_segments hs
                WHERE hs.from_component_id = drawing_elements.hvac_component_id
                   OR hs.to_component_id = drawing_elements.hvac_component_id
                LIMIT 1
            )
            WHERE element_type = 'component'
            AND hvac_component_id IS NOT NULL
            AND hvac_path_id IS NULL
        """))
        session.commit()
        
    except Exception as e:
        print(f"Warning: Could not link existing elements to HVAC paths: {e}")
        session.rollback()


def ensure_drawing_element_hvac_schema():
    """
    Ensure drawing_elements table has HVAC linkage columns.
    Also attempts to link existing elements to their HVAC records.
    """
    try:
        session = get_session()
        
        # Import models to ensure tables exist
        from . import project, drawing, space, hvac, drawing_elements  # noqa: F401
        
        # Add HVAC linkage columns to drawing_elements if missing
        _add_column_if_missing(
            session,
            "drawing_elements",
            [
                ("hvac_path_id", "INTEGER"),
                ("hvac_segment_id", "INTEGER"),
                ("hvac_component_id", "INTEGER"),
            ]
        )
        
        # Create indexes for efficient queries
        try:
            session.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_drawing_elements_hvac_path 
                ON drawing_elements(hvac_path_id)
            """))
            session.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_drawing_elements_hvac_segment 
                ON drawing_elements(hvac_segment_id)
            """))
            session.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_drawing_elements_hvac_component 
                ON drawing_elements(hvac_component_id)
            """))
            session.commit()
        except Exception as e:
            print(f"Index creation skipped or already exists: {e}")
        
        # Attempt to link existing elements to HVAC records
        _link_existing_elements_to_paths(session)
        
        session.close()
        print("Drawing element HVAC schema migration completed successfully")
        
    except Exception as e:
        print(f"Error during drawing element HVAC migration: {e}")
        try:
            session.rollback()
            session.close()
        except:
            pass

