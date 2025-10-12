#!/usr/bin/env python3
"""
Test script to verify Excel export fix for room_type field
"""

import sys
import os

# Add the src directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from models import get_session, Project, Space
from models.database import initialize_database
from data import ExcelExporter, ExportOptions, EXCEL_EXPORT_AVAILABLE

def test_excel_export_with_room_type():
    """Test that Excel export works with the room_type field"""
    print("=" * 60)
    print("Testing Excel Export with room_type field")
    print("=" * 60)
    
    if not EXCEL_EXPORT_AVAILABLE:
        print("❌ Excel export not available (openpyxl not installed)")
        return False
    
    try:
        # Try to initialize database with existing database path
        db_path = os.path.expanduser("~/Documents/AcousticAnalysis/acoustic_analysis.db")
        if os.path.exists(db_path):
            initialize_database(db_path)
            print(f"✅ Database initialized: {db_path}")
        else:
            print(f"❌ Database not found at {db_path}")
            return False
        
        session = get_session()
        
        # Get first project
        project = session.query(Project).first()
        if not project:
            print("❌ No projects found in database")
            session.close()
            return False
        
        print(f"✅ Found project: {project.name}")
        
        # Get spaces
        spaces = session.query(Space).filter(Space.project_id == project.id).all()
        if not spaces:
            print("❌ No spaces found in project")
            session.close()
            return False
        
        print(f"✅ Found {len(spaces)} spaces")
        
        # Check if spaces have room_type field
        for space in spaces:
            print(f"\nSpace: {space.name}")
            print(f"  - room_type: {space.room_type}")
            print(f"  - Has room_type attribute: {hasattr(space, 'room_type')}")
        
        # Create exporter
        exporter = ExcelExporter()
        print("\n✅ Created Excel exporter")
        
        # Get export summary (this will test the updated code)
        summary = exporter.get_export_summary(project.id)
        
        if "error" in summary:
            print(f"❌ Export summary failed: {summary['error']}")
            session.close()
            return False
        
        print(f"\n✅ Export summary generated successfully:")
        print(f"  - Project: {summary['project_name']}")
        print(f"  - Total spaces: {summary['total_spaces']}")
        print(f"  - Sheets to export: {len(summary['sheets_to_export'])}")
        
        # Test actual export (optional - uncomment to test full export)
        # export_path = "/tmp/test_export.xlsx"
        # options = ExportOptions()
        # success = exporter.export_project_analysis(project.id, export_path, options)
        # if success:
        #     print(f"\n✅ Full export successful: {export_path}")
        # else:
        #     print("\n❌ Full export failed")
        #     session.close()
        #     return False
        
        session.close()
        print("\n" + "=" * 60)
        print("✅ All tests passed!")
        print("=" * 60)
        return True
        
    except Exception as e:
        print(f"\n❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_excel_export_with_room_type()
    sys.exit(0 if success else 1)

