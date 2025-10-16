#!/usr/bin/env python3
"""
Database Migration: Add ceiling_area field to spaces table
Adds ceiling_area field to store explicit ceiling area (defaults to floor_area if not set)
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
    local_db = Path(__file__).parent.parent.parent / "projects.db"
    if local_db.exists():
        return str(local_db)
    
    # Default to development location
    return str(dev_db)

def check_column_exists(cursor, table_name, column_name):
    """Check if a column exists in a table"""
    cursor.execute(f"PRAGMA table_info({table_name})")
    columns = [row[1] for row in cursor.fetchall()]
    return column_name in columns

def add_ceiling_area_field_migration():
    """Add ceiling_area field to the spaces table"""
    db_path = get_database_path()
    print(f"Migrating database: {db_path}")
    
    if not os.path.exists(db_path):
        print(f"Database not found at {db_path}")
        print("This is normal if you haven't created a project yet.")
        return True  # Return True since this isn't an error
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Add ceiling_area field to spaces if it doesn't exist
        if not check_column_exists(cursor, 'spaces', 'ceiling_area'):
            print("Adding 'ceiling_area' column to spaces table...")
            cursor.execute("ALTER TABLE spaces ADD COLUMN ceiling_area REAL")
            print("✅ Added 'ceiling_area' column to spaces")
            
            # Optionally, initialize ceiling_area to floor_area for existing spaces
            print("Initializing ceiling_area = floor_area for existing spaces...")
            cursor.execute("""
                UPDATE spaces 
                SET ceiling_area = floor_area 
                WHERE ceiling_area IS NULL AND floor_area IS NOT NULL
            """)
            rows_updated = cursor.rowcount
            if rows_updated > 0:
                print(f"✅ Updated {rows_updated} spaces with ceiling_area = floor_area")
        else:
            print("ℹ️  'ceiling_area' column already exists in spaces")
        
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
    print("Ceiling Area Field Database Migration")
    print("=" * 40)
    success = add_ceiling_area_field_migration()
    sys.exit(0 if success else 1)

