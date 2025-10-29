"""
Migration script to add material_schedules table
"""

from sqlalchemy import text
from .database import get_session, initialize_database


def ensure_material_schedules_table():
    """Create material_schedules table if it doesn't exist"""
    session = get_session()
    
    try:
        # Check if table exists
        result = session.execute(text(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='material_schedules'"
        ))
        exists = result.fetchone() is not None
        
        if not exists:
            print("Creating material_schedules table...")
            
            # Create the table
            session.execute(text("""
                CREATE TABLE material_schedules (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    drawing_set_id INTEGER NOT NULL,
                    name VARCHAR(255) NOT NULL,
                    description TEXT,
                    file_path VARCHAR(1000),
                    managed_file_path VARCHAR(1000),
                    schedule_type VARCHAR(100) DEFAULT 'finishes',
                    created_date DATETIME DEFAULT CURRENT_TIMESTAMP,
                    modified_date DATETIME DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (drawing_set_id) REFERENCES drawing_sets(id) ON DELETE CASCADE
                )
            """))
            
            # Create indexes for better query performance
            session.execute(text("""
                CREATE INDEX idx_material_schedules_drawing_set 
                ON material_schedules(drawing_set_id)
            """))
            
            session.execute(text("""
                CREATE INDEX idx_material_schedules_schedule_type 
                ON material_schedules(schedule_type)
            """))
            
            session.commit()
            print("✓ material_schedules table created successfully")
        else:
            print("✓ material_schedules table already exists")
    
    except Exception as e:
        session.rollback()
        print(f"✗ Error creating material_schedules table: {e}")
        raise
    finally:
        session.close()


if __name__ == '__main__':
    print("Running material schedules migration...")
    
    # Initialize database first
    try:
        initialize_database()
        print("✓ Database initialized")
    except Exception as e:
        print(f"Database already initialized or error: {e}")
    
    ensure_material_schedules_table()
    print("Migration complete!")

