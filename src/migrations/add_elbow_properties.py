#!/usr/bin/env python3
"""
Database Migration: Add Elbow Properties to HVAC Components
Adds turning vanes and lining fields to hvac_components table
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

def add_elbow_properties_migration():
    """Add elbow-specific fields to hvac_components table"""
    db_path = get_database_path()
    print(f"Migrating database: {db_path}")
    
    if not os.path.exists(db_path):
        print(f"Database not found at {db_path}")
        return False
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Add has_turning_vanes field
        if not check_column_exists(cursor, 'hvac_components', 'has_turning_vanes'):
            print("Adding 'has_turning_vanes' column to hvac_components table...")
            cursor.execute("ALTER TABLE hvac_components ADD COLUMN has_turning_vanes INTEGER DEFAULT 0")
            print("✅ Added 'has_turning_vanes' column")
        else:
            print("❌ 'has_turning_vanes' column already exists")
        
        # Add vane_chord_length field
        if not check_column_exists(cursor, 'hvac_components', 'vane_chord_length'):
            print("Adding 'vane_chord_length' column to hvac_components table...")
            cursor.execute("ALTER TABLE hvac_components ADD COLUMN vane_chord_length REAL")
            print("✅ Added 'vane_chord_length' column")
        else:
            print("❌ 'vane_chord_length' column already exists")
        
        # Add num_vanes field
        if not check_column_exists(cursor, 'hvac_components', 'num_vanes'):
            print("Adding 'num_vanes' column to hvac_components table...")
            cursor.execute("ALTER TABLE hvac_components ADD COLUMN num_vanes INTEGER")
            print("✅ Added 'num_vanes' column")
        else:
            print("❌ 'num_vanes' column already exists")
        
        # Add lining_thickness field (for all component types)
        if not check_column_exists(cursor, 'hvac_components', 'lining_thickness'):
            print("Adding 'lining_thickness' column to hvac_components table...")
            cursor.execute("ALTER TABLE hvac_components ADD COLUMN lining_thickness REAL")
            print("✅ Added 'lining_thickness' column")
        else:
            print("❌ 'lining_thickness' column already exists")
        
        # Add pressure_drop field
        if not check_column_exists(cursor, 'hvac_components', 'pressure_drop'):
            print("Adding 'pressure_drop' column to hvac_components table...")
            cursor.execute("ALTER TABLE hvac_components ADD COLUMN pressure_drop REAL")
            print("✅ Added 'pressure_drop' column")
        else:
            print("❌ 'pressure_drop' column already exists")
        
        # Initialize existing elbow components with defaults
        print("\nInitializing existing elbow components with default values...")
        cursor.execute("""
            UPDATE hvac_components 
            SET has_turning_vanes = 0,
                vane_chord_length = NULL,
                num_vanes = NULL,
                lining_thickness = NULL,
                pressure_drop = NULL
            WHERE (component_type LIKE '%elbow%' OR component_type = 'elbow')
            AND has_turning_vanes IS NULL
        """)
        
        rows_updated = cursor.rowcount
        if rows_updated > 0:
            print(f"  Initialized {rows_updated} elbow components with default values")
        else:
            print(f"  No elbow components needed initialization")
        
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
    print("Elbow Properties Database Migration")
    print("=" * 40)
    success = add_elbow_properties_migration()
    sys.exit(0 if success else 1)

