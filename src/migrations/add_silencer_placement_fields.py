#!/usr/bin/env python3
"""
Database Migration: Add Silencer Placement Fields to HVAC Components
Adds position_on_path and elbow_component_id fields for silencer positioning
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


def add_silencer_placement_fields_migration():
    """Add silencer placement fields to hvac_components table"""
    db_path = get_database_path()
    print(f"Migrating database: {db_path}")

    if not os.path.exists(db_path):
        print(f"Database not found at {db_path}")
        return False

    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        # Add position_on_path field (0.0-1.0 normalized position for straight silencers)
        if not check_column_exists(cursor, 'hvac_components', 'position_on_path'):
            print("Adding 'position_on_path' column to hvac_components table...")
            cursor.execute("ALTER TABLE hvac_components ADD COLUMN position_on_path REAL")
            print("  Added 'position_on_path' column")
        else:
            print("  'position_on_path' column already exists")

        # Add elbow_component_id field (FK to hvac_components for elbow silencers)
        if not check_column_exists(cursor, 'hvac_components', 'elbow_component_id'):
            print("Adding 'elbow_component_id' column to hvac_components table...")
            cursor.execute("ALTER TABLE hvac_components ADD COLUMN elbow_component_id INTEGER")
            print("  Added 'elbow_component_id' column")
        else:
            print("  'elbow_component_id' column already exists")

        conn.commit()
        conn.close()

        print(f"\nMigration completed successfully!")
        print(f"Database updated: {db_path}")
        return True

    except Exception as e:
        print(f"Migration failed: {e}")
        if 'conn' in locals():
            conn.rollback()
            conn.close()
        return False


if __name__ == "__main__":
    print("Silencer Placement Fields Database Migration")
    print("=" * 50)
    success = add_silencer_placement_fields_migration()
    sys.exit(0 if success else 1)
