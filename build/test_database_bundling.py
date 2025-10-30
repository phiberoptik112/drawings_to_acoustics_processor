#!/usr/bin/env python3
"""
Test script to verify materials database bundling and loading
Can be run in both development and bundled executable contexts
"""

import sys
import os
from pathlib import Path

# Add src to path
project_root = Path(__file__).parent.parent.absolute()
sys.path.insert(0, str(project_root / "src"))

def test_utils_detection():
    """Test that utils module correctly detects bundling state"""
    print("=" * 60)
    print("Testing Utils Module")
    print("=" * 60)
    
    try:
        from utils import is_bundled_executable, get_materials_database_path, get_resource_path
        
        is_bundled = is_bundled_executable()
        print(f"✓ is_bundled_executable(): {is_bundled}")
        
        if is_bundled:
            print(f"  Running as bundled executable")
            print(f"  _MEIPASS: {getattr(sys, '_MEIPASS', 'N/A')}")
        else:
            print(f"  Running from source")
            
        db_path = get_materials_database_path()
        print(f"✓ Materials database path: {db_path}")
        
        # Check if database file exists
        if os.path.exists(db_path):
            size_mb = os.path.getsize(db_path) / (1024 * 1024)
            print(f"✓ Database file found ({size_mb:.2f} MB)")
        else:
            print(f"✗ WARNING: Database file not found!")
            return False
            
        return True
        
    except Exception as e:
        print(f"✗ ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_materials_loading():
    """Test that materials module can load from the database"""
    print("\n" + "=" * 60)
    print("Testing Materials Loading")
    print("=" * 60)
    
    try:
        from data.materials import load_materials_from_database, STANDARD_MATERIALS
        
        # Test loading from database
        print("Loading materials from database...")
        db_materials = load_materials_from_database()
        
        if db_materials:
            print(f"✓ Loaded {len(db_materials)} materials from database")
            
            # Show a few examples
            print("\nSample materials:")
            for i, (key, material) in enumerate(list(db_materials.items())[:5]):
                print(f"  - {material.get('name', key)}")
                if i >= 4:
                    break
        else:
            print("✗ WARNING: No materials loaded from database")
            
        # Test standard materials constant
        print(f"\n✓ STANDARD_MATERIALS contains {len(STANDARD_MATERIALS)} materials")
        
        return len(db_materials) > 0
        
    except Exception as e:
        print(f"✗ ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_materials_database_class():
    """Test the MaterialsDatabase class"""
    print("\n" + "=" * 60)
    print("Testing MaterialsDatabase Class")
    print("=" * 60)
    
    try:
        from data.materials_database import MaterialsDatabase, get_materials_database
        
        # Create database instance
        db = MaterialsDatabase()
        print("✓ MaterialsDatabase instance created")
        
        # Get all materials
        all_materials = db.get_all_materials()
        print(f"✓ Total materials: {len(all_materials)}")
        
        # Test standard materials
        standard_count = len(db.standard_materials)
        print(f"  - Standard materials: {standard_count}")
        
        # Test enhanced materials
        enhanced_count = len(db.enhanced_materials)
        print(f"  - Enhanced materials: {enhanced_count}")
        
        # Test category filtering
        categories = db.get_material_categories()
        print(f"✓ Material categories: {', '.join(categories)}")
        
        # Test specific material retrieval
        if all_materials:
            first_key = list(all_materials.keys())[0]
            test_material = db.get_material(first_key)
            if test_material:
                print(f"✓ Material retrieval works: {test_material.get('name')}")
            
            # Test frequency response
            freq_response = db.get_frequency_response(first_key)
            print(f"✓ Frequency response: {len(freq_response)} frequencies")
        
        # Test global instance
        global_db = get_materials_database()
        print(f"✓ Global database instance working")
        
        return len(all_materials) > 0
        
    except Exception as e:
        print(f"✗ ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_database_file_structure():
    """Test the actual database file structure"""
    print("\n" + "=" * 60)
    print("Testing Database File Structure")
    print("=" * 60)
    
    try:
        import sqlite3
        from utils import get_materials_database_path
        
        db_path = get_materials_database_path()
        
        if not os.path.exists(db_path):
            print(f"✗ Database not found at: {db_path}")
            return False
        
        # Connect to database
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Check tables
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = cursor.fetchall()
        print(f"✓ Database tables: {[t[0] for t in tables]}")
        
        # Check acoustic_materials table
        cursor.execute("SELECT COUNT(*) FROM acoustic_materials")
        count = cursor.fetchone()[0]
        print(f"✓ Total materials in database: {count}")
        
        # Check table structure
        cursor.execute("PRAGMA table_info(acoustic_materials)")
        columns = cursor.fetchall()
        column_names = [col[1] for col in columns]
        print(f"✓ Table columns: {', '.join(column_names)}")
        
        # Sample a few materials
        cursor.execute("SELECT name, nrc FROM acoustic_materials LIMIT 5")
        samples = cursor.fetchall()
        print("\nSample materials from database:")
        for name, nrc in samples:
            print(f"  - {name} (NRC: {nrc:.2f})")
        
        conn.close()
        
        return count > 0
        
    except Exception as e:
        print(f"✗ ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Run all database bundling tests"""
    print("\n" + "=" * 60)
    print("MATERIALS DATABASE BUNDLING TEST")
    print("=" * 60)
    print(f"Python: {sys.version}")
    print(f"Platform: {sys.platform}")
    print(f"Executable: {sys.executable}")
    print()
    
    # Run all tests
    tests = [
        ("Utils Detection", test_utils_detection),
        ("Database File Structure", test_database_file_structure),
        ("Materials Loading", test_materials_loading),
        ("MaterialsDatabase Class", test_materials_database_class),
    ]
    
    results = []
    for test_name, test_func in tests:
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"\n✗ Test '{test_name}' crashed: {e}")
            results.append((test_name, False))
    
    # Summary
    print("\n" + "=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for test_name, result in results:
        status = "✓ PASS" if result else "✗ FAIL"
        print(f"{status}: {test_name}")
    
    print()
    print(f"Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("\n✓ All tests passed! Database bundling is working correctly.")
        return 0
    else:
        print(f"\n✗ {total - passed} test(s) failed. Please review the errors above.")
        return 1


if __name__ == '__main__':
    sys.exit(main())

