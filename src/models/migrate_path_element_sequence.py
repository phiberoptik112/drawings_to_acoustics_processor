"""
Database migration to add element_sequence column to hvac_paths table.

This migration adds the element_sequence column which stores the ordered
sequence of components and segments in a path as JSON.
"""

from sqlalchemy import text


def _add_column_if_missing(session, table_name, columns_to_add):
    """
    Add columns to table if they don't already exist.
    
    Args:
        session: SQLAlchemy session
        table_name: Name of the table
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


def migrate_path_element_sequence_schema(session):
    """
    Add element_sequence column to hvac_paths table if it doesn't exist.
    
    The element_sequence column stores the ordered sequence of elements
    (components and segments) in a path as JSON.
    Format: [{"type": "component", "id": 1}, {"type": "segment", "id": 1}, ...]
    """
    try:
        # Add element_sequence column to hvac_paths if missing
        _add_column_if_missing(
            session,
            'hvac_paths',
            [
                ('element_sequence', 'TEXT'),
            ]
        )
        
        session.commit()
        print("Path element sequence schema migration completed successfully")
        return True
        
    except Exception as e:
        session.rollback()
        print(f"Error during path element sequence schema migration: {e}")
        return False


def ensure_path_element_sequence_schema():
    """
    Convenience function to run the migration with a fresh session.
    Can be called directly without needing to manage a session.
    """
    from . import get_session
    session = get_session()
    try:
        return migrate_path_element_sequence_schema(session)
    finally:
        session.close()


if __name__ == "__main__":
    # Allow running this script directly to migrate an existing database
    import sys
    sys.path.insert(0, str(__file__).rsplit('/', 3)[0])
    
    from models import initialize_database
    initialize_database()
    
    print("Migration complete.")
