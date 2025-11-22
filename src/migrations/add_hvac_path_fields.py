#!/usr/bin/env python3
"""
Database Migration: Add HVAC Path Fields
Adds primary_source_id and drawing_set_id fields to hvac_paths table
"""

import sqlite3
import os
import sys
from pathlib import Path

def get_database_path():
    """Get the database path from environment or default location"""
    # Check for development database first
    dev_db = Path.home() / "Documents" / "AcousticAnalysis" / "acoustic_analysis.db"
    if dev_db.exists():
        return str(dev_db)
    
    # Check for local projects.db
    # Assuming this script is in src/migrations/, go up 2 levels
    local_db = Path(__file__).parent.parent.parent / "projects.db"
    if local_db.exists():
        return str(local_db)
    
    # Check relative to current working directory if running from root
    cwd_db = Path("projects.db")
    if cwd_db.exists():
        return str(cwd_db)

    # Default to development location even if not exists (will likely fail connection)
    return str(dev_db)

def check_column_exists(cursor, table_name, column_name):
    """Check if a column exists in a table"""
    try:
        cursor.execute(f"PRAGMA table_info({table_name})")
        columns = [row[1] for row in cursor.fetchall()]
        return column_name in columns
    except Exception:
        return False

def add_hvac_path_fields_migration():
    """Add fields to hvac_paths table"""
    db_path = get_database_path()
    print(f"Migrating database: {db_path}")
    
    if not os.path.exists(db_path):
        print(f"Database not found at {db_path}")
        # Try creating one for testing if needed, or just return False
        return False
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Check if hvac_paths table exists
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='hvac_paths'")
        if not cursor.fetchone():
            print("❌ hvac_paths table does not exist. Skipping migration.")
            conn.close()
            return False

        # Add primary_source_id field if it doesn't exist
        if not check_column_exists(cursor, 'hvac_paths', 'primary_source_id'):
            print("Adding 'primary_source_id' column to hvac_paths table...")
            cursor.execute("ALTER TABLE hvac_paths ADD COLUMN primary_source_id INTEGER REFERENCES hvac_components(id)")
            print("✅ Added 'primary_source_id' column to hvac_paths")
        else:
            print("ℹ️ 'primary_source_id' column already exists in hvac_paths")
        
        # Add drawing_set_id field if it doesn't exist
        if not check_column_exists(cursor, 'hvac_paths', 'drawing_set_id'):
            print("Adding 'drawing_set_id' column to hvac_paths table...")
            cursor.execute("ALTER TABLE hvac_paths ADD COLUMN drawing_set_id INTEGER REFERENCES drawing_sets(id)")
            print("✅ Added 'drawing_set_id' column to hvac_paths")
        else:
            print("ℹ️ 'drawing_set_id' column already exists in hvac_paths")
            
        conn.commit()
        conn.close()
        
        print(f"\n✅ Migration completed successfully!")
        print(f"Database updated: {db_path}")
        return True
        
    except Exception as e:
        print(f"❌ Migration failed: {e}")
        if 'conn' in locals():
            conn.rollback()
            conn.close()
        return False

if __name__ == "__main__":
    print("HVAC Path Fields Database Migration")
    print("=" * 40)
    success = add_hvac_path_fields_migration()
    sys.exit(0 if success else 1)

