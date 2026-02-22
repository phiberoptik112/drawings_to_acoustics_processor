#!/usr/bin/env python3
"""
Database Migration: Add target_nc field to spaces table
Adds target_nc field to store the target NC rating for HVAC noise compliance
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

def add_target_nc_field_migration():
    """Add target_nc field to the spaces table"""
    db_path = get_database_path()
    print(f"Migrating database: {db_path}")
    
    if not os.path.exists(db_path):
        print(f"Database not found at {db_path}")
        print("This is normal if you haven't created a project yet.")
        return True  # Return True since this isn't an error
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Add target_nc field to spaces if it doesn't exist
        if not check_column_exists(cursor, 'spaces', 'target_nc'):
            print("Adding 'target_nc' column to spaces table...")
            cursor.execute("ALTER TABLE spaces ADD COLUMN target_nc REAL")
            print("✅ Added 'target_nc' column to spaces")
        else:
            print("ℹ️  'target_nc' column already exists in spaces")
        
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
    print("Target NC Field Database Migration")
    print("=" * 40)
    success = add_target_nc_field_migration()
    sys.exit(0 if success else 1)
