#!/usr/bin/env python3
"""
Database migration to add page_number columns to drawing_elements and room_boundaries tables
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from models import get_session, initialize_database
from sqlalchemy import text
import traceback


def add_page_number_columns():
    """Add page_number columns to tables that need them"""
    try:
        # Initialize database first
        initialize_database()
        session = get_session()
        
        # Check if drawing_elements table exists and if page_number column exists
        try:
            result = session.execute(text("SELECT page_number FROM drawing_elements LIMIT 1"))
            print("✓ drawing_elements.page_number column already exists")
        except Exception:
            # Column doesn't exist, add it
            print("Adding page_number column to drawing_elements table...")
            session.execute(text("ALTER TABLE drawing_elements ADD COLUMN page_number INTEGER DEFAULT 1"))
            session.commit()
            print("✓ Added page_number column to drawing_elements")
        
        # Check if room_boundaries table exists and if page_number column exists
        try:
            result = session.execute(text("SELECT page_number FROM room_boundaries LIMIT 1"))
            print("✓ room_boundaries.page_number column already exists")
        except Exception:
            # Column doesn't exist, add it
            print("Adding page_number column to room_boundaries table...")
            session.execute(text("ALTER TABLE room_boundaries ADD COLUMN page_number INTEGER DEFAULT 1"))
            session.commit()
            print("✓ Added page_number column to room_boundaries")
        
        # Update any existing records to have page_number = 1 (default page)
        print("Updating existing records to set default page numbers...")
        
        # Update drawing_elements
        result = session.execute(text("UPDATE drawing_elements SET page_number = 1 WHERE page_number IS NULL"))
        updated_elements = result.rowcount
        if updated_elements > 0:
            print(f"✓ Updated {updated_elements} drawing elements with default page number")
        
        # Update room_boundaries  
        result = session.execute(text("UPDATE room_boundaries SET page_number = 1 WHERE page_number IS NULL"))
        updated_boundaries = result.rowcount
        if updated_boundaries > 0:
            print(f"✓ Updated {updated_boundaries} room boundaries with default page number")
        
        session.commit()
        session.close()
        
        print("\n🎉 Database migration completed successfully!")
        print("✓ page_number columns added to drawing_elements and room_boundaries tables")
        print("✓ Existing records updated with default page numbers")
        
        return True
        
    except Exception as e:
        print(f"\n❌ Migration failed: {str(e)}")
        print("\nFull traceback:")
        traceback.print_exc()
        
        if 'session' in locals():
            try:
                session.rollback()
                session.close()
            except:
                pass
                
        return False


def verify_migration():
    """Verify the migration was successful"""
    try:
        initialize_database()
        session = get_session()
        
        print("\nVerifying migration...")
        
        # Check drawing_elements table structure
        result = session.execute(text("PRAGMA table_info(drawing_elements)"))
        columns = [row[1] for row in result.fetchall()]
        
        if 'page_number' in columns:
            print("✓ drawing_elements.page_number column exists")
        else:
            print("❌ drawing_elements.page_number column missing")
            return False
        
        # Check room_boundaries table structure
        result = session.execute(text("PRAGMA table_info(room_boundaries)"))
        columns = [row[1] for row in result.fetchall()]
        
        if 'page_number' in columns:
            print("✓ room_boundaries.page_number column exists")
        else:
            print("❌ room_boundaries.page_number column missing")
            return False
        
        # Count records with page numbers
        result = session.execute(text("SELECT COUNT(*) FROM drawing_elements WHERE page_number IS NOT NULL"))
        element_count = result.scalar()
        print(f"✓ {element_count} drawing elements have page numbers")
        
        result = session.execute(text("SELECT COUNT(*) FROM room_boundaries WHERE page_number IS NOT NULL"))
        boundary_count = result.scalar()
        print(f"✓ {boundary_count} room boundaries have page numbers")
        
        session.close()
        
        print("\n✅ Migration verification successful!")
        return True
        
    except Exception as e:
        print(f"\n❌ Migration verification failed: {str(e)}")
        if 'session' in locals():
            try:
                session.close()
            except:
                pass
        return False


if __name__ == "__main__":
    print("🔄 Starting database migration to add page_number columns...")
    print("=" * 60)
    
    # Run migration
    success = add_page_number_columns()
    
    if success:
        # Verify migration
        verify_migration()
    else:
        print("\n❌ Migration failed. Please check the error messages above.")
        sys.exit(1)
    
    print("\n" + "=" * 60)
    print("🎉 Migration completed! Multi-page PDF support is now available.")
    print("\nFeatures added:")
    print("• Elements and spaces are now tied to specific PDF pages")
    print("• Page navigation preserves elements per page")
    print("• Spaces created on different pages are kept separate")