"""
Migration script to add partition-related tables and columns for LEED Sound Transmission compliance.

Tables created:
- partition_types: Project-level partition assembly library
- partition_schedule_documents: Reference PDFs for partition schedules
- space_partitions: Individual partition assignments per space

Columns added to spaces:
- room_id: Space identifier (e.g., "105")
- location_in_project: Building level/zone (e.g., "Level 1")
- space_type: Space classification (e.g., "Classroom")
"""

from sqlalchemy import text
from .database import get_session


def ensure_partition_schema():
    """Ensure partition-related tables and columns exist in the database."""
    session = get_session()
    
    try:
        conn = session.connection()
        
        # Check and create partition_types table
        result = conn.execute(text(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='partition_types'"
        ))
        if not result.fetchone():
            conn.execute(text("""
                CREATE TABLE partition_types (
                    id INTEGER PRIMARY KEY,
                    project_id INTEGER NOT NULL,
                    assembly_id VARCHAR(50) NOT NULL,
                    description TEXT,
                    stc_rating INTEGER,
                    source_document VARCHAR(255),
                    notes TEXT,
                    created_date DATETIME,
                    modified_date DATETIME,
                    FOREIGN KEY (project_id) REFERENCES projects(id)
                )
            """))
            print("Created partition_types table")
        
        # Check and create partition_schedule_documents table
        result = conn.execute(text(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='partition_schedule_documents'"
        ))
        if not result.fetchone():
            conn.execute(text("""
                CREATE TABLE partition_schedule_documents (
                    id INTEGER PRIMARY KEY,
                    project_id INTEGER NOT NULL,
                    name VARCHAR(255) NOT NULL,
                    description TEXT,
                    file_path VARCHAR(1000),
                    managed_file_path VARCHAR(1000),
                    page_number INTEGER DEFAULT 1,
                    created_date DATETIME,
                    modified_date DATETIME,
                    FOREIGN KEY (project_id) REFERENCES projects(id)
                )
            """))
            print("Created partition_schedule_documents table")
        
        # Check and create space_partitions table
        result = conn.execute(text(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='space_partitions'"
        ))
        if not result.fetchone():
            conn.execute(text("""
                CREATE TABLE space_partitions (
                    id INTEGER PRIMARY KEY,
                    space_id INTEGER NOT NULL,
                    partition_type_id INTEGER,
                    assembly_location VARCHAR(50),
                    adjacent_space_type VARCHAR(100),
                    adjacent_space_id INTEGER,
                    minimum_stc_required INTEGER,
                    stc_rating_override INTEGER,
                    notes TEXT,
                    created_date DATETIME,
                    modified_date DATETIME,
                    FOREIGN KEY (space_id) REFERENCES spaces(id),
                    FOREIGN KEY (partition_type_id) REFERENCES partition_types(id),
                    FOREIGN KEY (adjacent_space_id) REFERENCES spaces(id)
                )
            """))
            print("Created space_partitions table")
        
        # Check and add columns to spaces table
        result = conn.execute(text("PRAGMA table_info(spaces)"))
        existing_columns = {row[1] for row in result.fetchall()}
        
        # Add room_id column
        if 'room_id' not in existing_columns:
            conn.execute(text("ALTER TABLE spaces ADD COLUMN room_id VARCHAR(50)"))
            print("Added room_id column to spaces table")
        
        # Add location_in_project column
        if 'location_in_project' not in existing_columns:
            conn.execute(text("ALTER TABLE spaces ADD COLUMN location_in_project VARCHAR(100)"))
            print("Added location_in_project column to spaces table")
        
        # Add space_type column
        if 'space_type' not in existing_columns:
            conn.execute(text("ALTER TABLE spaces ADD COLUMN space_type VARCHAR(100)"))
            print("Added space_type column to spaces table")
        
        session.commit()
        print("Partition schema migration completed successfully")
        
    except Exception as e:
        session.rollback()
        print(f"Error during partition schema migration: {e}")
        raise
    finally:
        session.close()


if __name__ == "__main__":
    # Allow running migration directly
    from .database import initialize_database
    initialize_database()
    ensure_partition_schema()

