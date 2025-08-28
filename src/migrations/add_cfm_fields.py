#!/usr/bin/env python3
"""
Database Migration: Add CFM fields to HVAC models
Adds cfm field to hvac_components and flow_rate/flow_velocity to hvac_segments
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

def add_cfm_fields_migration():
    """Add CFM-related fields to the database"""
    db_path = get_database_path()
    print(f"Migrating database: {db_path}")
    
    if not os.path.exists(db_path):
        print(f"Database not found at {db_path}")
        return False
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Add cfm field to hvac_components if it doesn't exist
        if not check_column_exists(cursor, 'hvac_components', 'cfm'):
            print("Adding 'cfm' column to hvac_components table...")
            cursor.execute("ALTER TABLE hvac_components ADD COLUMN cfm REAL")
            print("✅ Added 'cfm' column to hvac_components")
        else:
            print("❌ 'cfm' column already exists in hvac_components")
        
        # Add flow_rate field to hvac_segments if it doesn't exist
        if not check_column_exists(cursor, 'hvac_segments', 'flow_rate'):
            print("Adding 'flow_rate' column to hvac_segments table...")
            cursor.execute("ALTER TABLE hvac_segments ADD COLUMN flow_rate REAL")
            print("✅ Added 'flow_rate' column to hvac_segments")
        else:
            print("❌ 'flow_rate' column already exists in hvac_segments")
        
        # Add flow_velocity field to hvac_segments if it doesn't exist
        if not check_column_exists(cursor, 'hvac_segments', 'flow_velocity'):
            print("Adding 'flow_velocity' column to hvac_segments table...")
            cursor.execute("ALTER TABLE hvac_segments ADD COLUMN flow_velocity REAL")
            print("✅ Added 'flow_velocity' column to hvac_segments")
        else:
            print("❌ 'flow_velocity' column already exists in hvac_segments")
        
        # Update existing components with default CFM values based on component type
        print("\nUpdating existing components with default CFM values...")
        
        # CFM defaults by component type
        cfm_defaults = {
            'ahu': 5000.0,
            'fan': 2000.0,
            'vav': 500.0,
            'diffuser': 150.0,
            'grille': 200.0,
            'damper': 100.0,
            'silencer': 1000.0,
            'coil': 800.0,
            'elbow': 100.0,
            'branch': 300.0,
            'doas': 3000.0,
            'rtu': 4000.0,
            'rf': 2500.0,
            'sf': 2500.0
        }
        
        for comp_type, default_cfm in cfm_defaults.items():
            cursor.execute("""
                UPDATE hvac_components 
                SET cfm = ? 
                WHERE component_type = ? AND cfm IS NULL
            """, (default_cfm, comp_type))
            
            rows_updated = cursor.rowcount
            if rows_updated > 0:
                print(f"  Updated {rows_updated} {comp_type} components with {default_cfm} CFM")
        
        # Set general fallback CFM for any remaining NULL values
        cursor.execute("""
            UPDATE hvac_components 
            SET cfm = 1000.0 
            WHERE cfm IS NULL
        """)
        
        fallback_rows = cursor.rowcount
        if fallback_rows > 0:
            print(f"  Set fallback CFM (1000) for {fallback_rows} components")
        
        # Update existing segments with flow rates from their source components
        print("\nUpdating existing segments with flow rates from components...")
        cursor.execute("""
            UPDATE hvac_segments 
            SET flow_rate = (
                SELECT cfm 
                FROM hvac_components 
                WHERE hvac_components.id = hvac_segments.from_component_id
            )
            WHERE flow_rate IS NULL
            AND from_component_id IS NOT NULL
        """)
        
        segment_rows = cursor.rowcount
        if segment_rows > 0:
            print(f"  Updated {segment_rows} segments with component CFM values")
        
        # Set fallback flow rate for remaining segments
        cursor.execute("""
            UPDATE hvac_segments 
            SET flow_rate = 1000.0 
            WHERE flow_rate IS NULL
        """)
        
        fallback_segments = cursor.rowcount
        if fallback_segments > 0:
            print(f"  Set fallback flow rate (1000 CFM) for {fallback_segments} segments")
        
        # Calculate flow velocities for segments based on duct dimensions and flow rate
        print("\nCalculating flow velocities for segments...")
        cursor.execute("""
            UPDATE hvac_segments 
            SET flow_velocity = CASE 
                WHEN duct_shape = 'rectangular' AND duct_width > 0 AND duct_height > 0 THEN
                    flow_rate / ((duct_width / 12.0) * (duct_height / 12.0))
                WHEN duct_shape = 'circular' AND diameter > 0 THEN
                    flow_rate / (3.14159 * ((diameter / 2.0) / 12.0) * ((diameter / 2.0) / 12.0))
                ELSE 800.0
            END
            WHERE flow_velocity IS NULL AND flow_rate IS NOT NULL
        """)
        
        velocity_rows = cursor.rowcount
        if velocity_rows > 0:
            print(f"  Calculated flow velocities for {velocity_rows} segments")
        
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
    print("CFM Fields Database Migration")
    print("=" * 40)
    success = add_cfm_fields_migration()
    sys.exit(0 if success else 1)