#!/usr/bin/env python3
"""
Migration Script: Import STANDARD_MATERIALS into Component Library

This script migrates materials from the materials/acoustic_materials.db 
(STANDARD_MATERIALS) into the project's AcousticMaterial table for the 
Component Library.

This bridges the gap between:
- Legacy system: SpaceSurfaceMaterial with material_key strings
- Component Library: AcousticMaterial table with full records

Usage:
    python migrate_materials_to_component_library.py [--dry-run]
"""

import sys
import os
from datetime import datetime

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from models import get_session, initialize_database
from models.rt60_models import AcousticMaterial, SurfaceCategory
from data.materials import STANDARD_MATERIALS


def get_or_create_category(session, category_name: str, dry_run=False):
    """Get or create a surface category"""
    # Normalize category name
    category_map = {
        'ceiling': 'ceilings',
        'wall': 'walls',
        'floor': 'floors',
        'door': 'doors',
        'window': 'windows',
        'other': 'specialty'
    }
    
    normalized_name = category_map.get(category_name.lower(), category_name.lower())
    
    # Try to find existing category
    category = session.query(SurfaceCategory).filter(
        SurfaceCategory.name == normalized_name
    ).first()
    
    if not category:
        if dry_run:
            # In dry-run mode, create a temporary in-memory category without flush
            category = SurfaceCategory(
                id=hash(normalized_name) % 1000,  # Fake ID for dry run
                name=normalized_name,
                description=f"{normalized_name.capitalize()} materials"
            )
            print(f"  (Dry run) Would create category: {normalized_name}")
        else:
            # Actually create the category
            category = SurfaceCategory(
                name=normalized_name,
                description=f"{normalized_name.capitalize()} materials"
            )
            session.add(category)
            session.flush()
            print(f"  Created new category: {normalized_name}")
    
    return category


def migrate_materials(dry_run=False):
    """
    Migrate materials from STANDARD_MATERIALS to AcousticMaterial table
    
    Args:
        dry_run: If True, don't commit changes, just report what would happen
    """
    print("=" * 70)
    print("Material Migration: STANDARD_MATERIALS → Component Library")
    print("=" * 70)
    print()
    
    if dry_run:
        print("🔍 DRY RUN MODE - No changes will be saved")
        print()
    
    # Initialize database
    initialize_database()
    session = get_session()
    
    try:
        print(f"📚 Found {len(STANDARD_MATERIALS)} materials in STANDARD_MATERIALS")
        print()
        
        stats = {
            'total': len(STANDARD_MATERIALS),
            'created': 0,
            'skipped': 0,
            'errors': 0
        }
        
        for mat_key, mat_data in STANDARD_MATERIALS.items():
            mat_name = mat_data.get('name', mat_key)
            
            try:
                # Check if material already exists (by name)
                existing = session.query(AcousticMaterial).filter(
                    AcousticMaterial.name == mat_name
                ).first()
                
                if existing:
                    print(f"⏭️  SKIP: '{mat_name}' (already exists, ID: {existing.id})")
                    stats['skipped'] += 1
                    continue
                
                # Extract coefficients
                coeffs = mat_data.get('coefficients', {})
                
                # Get category
                category_name = mat_data.get('category', 'specialty')
                category = get_or_create_category(session, category_name, dry_run=dry_run)
                
                # Create new AcousticMaterial
                new_material = AcousticMaterial(
                    name=mat_name,
                    category_id=category.id,
                    description=mat_data.get('description', f"{mat_name} (imported from STANDARD_MATERIALS)"),
                    absorption_125=float(coeffs.get('125', 0.0)) if coeffs.get('125') is not None else 0.0,
                    absorption_250=float(coeffs.get('250', 0.0)) if coeffs.get('250') is not None else 0.0,
                    absorption_500=float(coeffs.get('500', 0.0)) if coeffs.get('500') is not None else 0.0,
                    absorption_1000=float(coeffs.get('1000', 0.0)) if coeffs.get('1000') is not None else 0.0,
                    absorption_2000=float(coeffs.get('2000', 0.0)) if coeffs.get('2000') is not None else 0.0,
                    absorption_4000=float(coeffs.get('4000', 0.0)) if coeffs.get('4000') is not None else 0.0,
                    source="STANDARD_MATERIALS migration",
                    import_date=datetime.utcnow()
                )
                
                # Calculate NRC
                new_material.calculate_nrc()
                
                nrc_text = f"{new_material.nrc:.2f}" if new_material.nrc is not None else "N/A"
                
                if not dry_run:
                    session.add(new_material)
                    session.flush()
                    print(f"✅ CREATE: '{mat_name}' (NRC: {nrc_text}, Category: {category.name})")
                else:
                    print(f"✅ Would CREATE: '{mat_name}' (NRC: {nrc_text}, Category: {category.name})")
                
                stats['created'] += 1
                
            except Exception as e:
                print(f"❌ ERROR: Failed to migrate '{mat_name}': {e}")
                stats['errors'] += 1
                continue
        
        if not dry_run:
            session.commit()
            print()
            print("💾 Changes committed to database")
        else:
            session.rollback()
            print()
            print("🔄 Changes rolled back (dry run)")
        
        print()
        print("=" * 70)
        print("Migration Summary")
        print("=" * 70)
        print(f"Total materials in STANDARD_MATERIALS: {stats['total']}")
        print(f"✅ Created:                             {stats['created']}")
        print(f"⏭️  Skipped (already exist):            {stats['skipped']}")
        print(f"❌ Errors:                              {stats['errors']}")
        print("=" * 70)
        
        if dry_run:
            print()
            print("To perform the actual migration, run without --dry-run:")
            print("    python migrate_materials_to_component_library.py")
        else:
            print()
            print("✨ Migration complete!")
            print()
            print("Next steps:")
            print("1. Open the Component Library Dialog")
            print("2. Go to the Acoustic Treatment tab")
            print("3. Your materials should now appear in the list")
            print("4. Enable 'Show only project materials' to see materials used in spaces")
        
        session.close()
        return stats['errors'] == 0
        
    except Exception as e:
        session.rollback()
        session.close()
        print()
        print(f"❌ CRITICAL ERROR: Migration failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Main entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Migrate materials from STANDARD_MATERIALS to Component Library"
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help="Show what would be migrated without making changes"
    )
    
    args = parser.parse_args()
    
    success = migrate_materials(dry_run=args.dry_run)
    
    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())

