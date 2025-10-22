# Materials Migration Guide

## Overview

This project uses two material systems that need to be synchronized:

### Legacy System (Space Editor)
- **Table**: `space_surface_materials`
- **Storage**: `material_key` strings (e.g., "armstrong_acoustic_ceiling_tile")
- **Source**: `STANDARD_MATERIALS` dictionary from `materials/acoustic_materials.db`
- **Used by**: Space editor, RT60 calculations

### Component Library System (New)
- **Table**: `acoustic_materials`
- **Storage**: Full material records with foreign key relationships
- **Source**: Project database
- **Used by**: Component Library Dialog, material management

## The Problem

When you assign materials to spaces in the Space Editor, they're stored as string keys referencing `STANDARD_MATERIALS`. However, the Component Library Dialog manages the `acoustic_materials` table, which is initially empty. This means:

1. ❌ Materials assigned to spaces don't appear in Component Library
2. ❌ "Show only project materials" filter shows nothing
3. ❌ You can't edit or view materials used in your project

## The Solution: Migration Script

The `migrate_materials_to_component_library.py` script imports all materials from `STANDARD_MATERIALS` into the `acoustic_materials` table, bridging the gap between the two systems.

## Running the Migration

### Step 1: Dry Run (Recommended)

First, run a dry run to see what will be migrated without making changes:

```bash
cd /Users/jakepfitsch/Documents/drawings_to_acoustics_processor
source .venv/bin/activate
python migrate_materials_to_component_library.py --dry-run
```

**Expected Output:**
```
======================================================================
Material Migration: STANDARD_MATERIALS → Component Library
======================================================================

🔍 DRY RUN MODE - No changes will be saved

📚 Found 150+ materials in STANDARD_MATERIALS

✅ CREATE: 'Acoustic Ceiling Tile' (NRC: 0.70, Category: ceilings)
✅ CREATE: 'Gypsum Board on Studs' (NRC: 0.08, Category: walls)
⏭️  SKIP: 'Vinyl Tile Floor' (already exists, ID: 42)
...

======================================================================
Migration Summary
======================================================================
Total materials in STANDARD_MATERIALS: 152
✅ Created:                             150
⏭️  Skipped (already exist):            2
❌ Errors:                              0
======================================================================
```

### Step 2: Run Actual Migration

If the dry run looks good, run the actual migration:

```bash
python migrate_materials_to_component_library.py
```

**This will:**
- ✅ Import all materials from `STANDARD_MATERIALS`
- ✅ Skip materials that already exist (by name)
- ✅ Calculate NRC for each material
- ✅ Assign categories (ceilings, walls, floors, etc.)
- ✅ Commit changes to database

### Step 3: Verify in Component Library

1. Open the Component Library Dialog from your project dashboard
2. Navigate to the **Acoustic Treatment** tab
3. You should see all materials in the list
4. Check the **"Show only project materials"** checkbox
5. You should now see the materials used in your classroom (ARMSTRONG, VINYL TILE, etc.)

## What Gets Migrated

For each material in `STANDARD_MATERIALS`, the script creates an `AcousticMaterial` record with:

| Field | Source | Notes |
|-------|--------|-------|
| `name` | `mat_data['name']` | Material display name |
| `category_id` | Mapped from `mat_data['category']` | walls, ceilings, floors, etc. |
| `description` | `mat_data['description']` | With import note |
| `absorption_125` | `coefficients['125']` | 125 Hz coefficient |
| `absorption_250` | `coefficients['250']` | 250 Hz coefficient |
| `absorption_500` | `coefficients['500']` | 500 Hz coefficient |
| `absorption_1000` | `coefficients['1000']` | 1000 Hz coefficient |
| `absorption_2000` | `coefficients['2000']` | 2000 Hz coefficient |
| `absorption_4000` | `coefficients['4000']` | 4000 Hz coefficient |
| `nrc` | Auto-calculated | Average of 4 speech frequencies |
| `source` | "STANDARD_MATERIALS migration" | Tracking info |
| `import_date` | Current timestamp | When migrated |

## Category Mapping

The script automatically maps material categories:

| Legacy Category | Component Library Category |
|----------------|---------------------------|
| ceiling | ceilings |
| wall | walls |
| floor | floors |
| door | doors |
| window | windows |
| other | specialty |

If a category doesn't exist, it will be created automatically.

## Idempotency & Safety

The migration script is **safe to run multiple times**:

- ✅ Skips materials that already exist (checks by name)
- ✅ Creates missing categories automatically
- ✅ Handles errors gracefully without crashing
- ✅ Provides detailed progress output
- ✅ Dry run mode for testing

## After Migration

Once the migration is complete:

### Component Library Features Now Work

1. **View All Materials**
   - Uncheck "Show only project materials"
   - See complete library of available materials

2. **View Project Materials**
   - Check "Show only project materials"
   - See only materials used in your spaces

3. **Edit Materials**
   - Select any material
   - Click "Edit" to modify absorption coefficients
   - Changes persist in database

4. **Add New Materials**
   - Click "Manual Treatment Add"
   - Create custom materials
   - They're immediately available for assignment

5. **Delete Unused Materials**
   - Select material
   - Click "Delete"
   - Warning shown if material is in use

### Material Assignment Still Works

The space editor continues to work normally:
- Materials are still stored as `material_key` strings
- `STANDARD_MATERIALS` dictionary is still used
- No breaking changes to existing functionality

### Filter Now Works

The filter correctly finds materials by:
1. Checking `RoomSurfaceInstance` (new RT60 system)
2. Checking `SpaceSurfaceMaterial` (legacy system)
3. Matching `material_key` strings to `AcousticMaterial` names

## Troubleshooting

### "No materials found" after migration

**Problem**: Materials migrated but list is empty

**Solution**: 
1. Close and reopen Component Library Dialog
2. Click refresh (if available)
3. Try unchecking "Show only project materials"

### "Already exists" errors

**Problem**: Script says material exists but you don't see it

**Solution**: Material exists but may have slightly different name
- Check existing materials in Component Library
- Look for similar names
- Script matches by exact name

### Filter shows no materials

**Problem**: "Show only project materials" returns empty

**Solution**:
1. Verify spaces have materials assigned in Space Editor
2. Check that material names match exactly
3. Try running migration again (it's safe)
4. Uncheck filter to see if materials exist at all

### Import errors

**Problem**: Some materials failed to import

**Solution**:
1. Check error messages in migration output
2. Verify `materials/acoustic_materials.db` exists
3. Check database permissions
4. Run dry run to identify problematic materials

## Manual Verification

To verify the migration worked, run this query:

```python
from models import get_session
from models.rt60_models import AcousticMaterial

session = get_session()
count = session.query(AcousticMaterial).count()
print(f"Total materials in Component Library: {count}")

# Show some examples
materials = session.query(AcousticMaterial).limit(5).all()
for mat in materials:
    print(f"- {mat.name} (NRC: {mat.nrc:.2f})")
session.close()
```

Expected output:
```
Total materials in Component Library: 152
- Acoustic Ceiling Tile (NRC: 0.70)
- Gypsum Board on Studs (NRC: 0.08)
- Vinyl Tile Floor (NRC: 0.03)
- Carpet on Concrete (NRC: 0.25)
- Glass Window (NRC: 0.05)
```

## Rollback (If Needed)

If something goes wrong, you can remove all migrated materials:

```python
from models import get_session
from models.rt60_models import AcousticMaterial

session = get_session()
# Delete only materials from this migration
migrated = session.query(AcousticMaterial).filter(
    AcousticMaterial.source == "STANDARD_MATERIALS migration"
).all()

count = len(migrated)
for mat in migrated:
    session.delete(mat)

session.commit()
session.close()
print(f"Removed {count} migrated materials")
```

## Best Practices

1. **Always run dry run first** - See what will happen
2. **Backup your database** - Before running migration
3. **Run during off-hours** - If working with production data
4. **Verify results** - Check Component Library after migration
5. **Document custom materials** - Note any manual additions

## Future Improvements

Consider these enhancements:

1. **Bi-directional Sync** - Keep both systems in sync automatically
2. **Material Versioning** - Track changes over time
3. **Bulk Updates** - Update multiple materials at once
4. **Material Templates** - Pre-defined material sets
5. **Import from CSV** - Import materials from spreadsheets

## Need Help?

- Check `ACOUSTIC_MATERIALS_TAB_ENHANCEMENT.md` for Component Library details
- Review `IMPLEMENTATION_SUMMARY.md` for technical architecture
- See `ACOUSTIC_MATERIALS_QUICKSTART.md` for usage guide

## Related Scripts

- `migrate_surface_materials.py` - Migrates legacy single materials to new system
- `populate_silencer_database.py` - Populates silencer data
- `test_acoustic_materials_tab.py` - Tests Component Library dialog

