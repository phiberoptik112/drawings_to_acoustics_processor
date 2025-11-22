#!/usr/bin/env python3
"""
Database Migration Runner: HVAC Path Fields
Run this script to apply HVAC path field migrations to the database
"""

import sys
import os
from pathlib import Path

# Add src to Python path
src_path = Path(__file__).parent / "src"
sys.path.insert(0, str(src_path))

def main():
    """Run the HVAC path fields migration"""
    print("Running HVAC path fields migration...")
    print("=" * 50)
    
    try:
        from migrations.add_hvac_path_fields import add_hvac_path_fields_migration
        success = add_hvac_path_fields_migration()
        
        if success:
            print("\n🎉 Migration completed successfully!")
            return 0
        else:
            print("\n❌ Migration failed!")
            return 1
            
    except ImportError as e:
        print(f"❌ Could not import migration: {e}")
        print("Make sure you're running from the project root directory")
        return 1
    except Exception as e:
        print(f"❌ Migration error: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(main())

