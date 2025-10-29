# Acoustic Materials Tab Enhancement

## Overview

The Component Library Dialog's Acoustic Treatment tab has been enhanced to display acoustic materials alongside material schedules in a side-by-side layout. Users can now view, add, edit, and delete acoustic materials directly from the Component Library interface.

## Features Implemented

### 1. Restructured Tab Layout

The Acoustic Treatment tab now uses a **horizontal splitter** with two main sections:

**Left Section - Acoustic Materials:**
- Filter checkbox: "Show only project materials"
- Materials list displaying all acoustic materials with NRC values
- Absorption coefficients table (6 frequency bands + NRC)
- Action buttons: Manual Treatment Add, Edit, Delete, Save Changes

**Right Section - Material Schedules:**
- Existing material schedules list grouped by drawing set
- PDF preview functionality
- Add/Edit/Delete/Compare buttons (unchanged from previous implementation)

### 2. Materials Display and Filtering

**Materials List:**
- Shows all acoustic materials from the global `acoustic_materials` table
- Display format: `"Material Name - NRC: 0.XX"`
- Tooltips show additional info: category, manufacturer, mounting type, thickness
- Placeholder text when no materials are found

**Project Filtering:**
- Checkbox option: "Show only project materials"
- When enabled: filters to materials used in the project's `RoomSurfaceInstance` records
- Filter state persists during the session

### 3. Absorption Coefficients Table

**Display:**
- 7 columns: 125, 250, 500, 1000, 2000, 4000 Hz, NRC
- Single row showing selected material's absorption coefficients
- NRC column is read-only with grey background

**Editing:**
- Double-click or click to edit absorption values (0.00 - 1.00 range)
- Auto-calculates NRC from 250, 500, 1000, 2000 Hz values
- Marks table as "dirty" when edited
- "Save Changes" button enabled when modifications are made

### 4. Manual Treatment Add Dialog

**Form Fields:**
- Name* (required)
- Category (dropdown from SurfaceCategory table)
- Manufacturer (optional)
- Product Code (optional)
- Mounting Type (dropdown: direct, suspended, spaced)
- Thickness (free text, e.g., "1 inch", "25mm")
- Description (multi-line text)

**Absorption Coefficients:**
- 6 spin boxes for each frequency band (125-4000 Hz)
- Range: 0.00 - 1.00, step 0.01
- Auto-calculates and displays NRC in real-time
- NRC updates as coefficients are changed

**Validation:**
- Name is required
- At least one absorption coefficient must be > 0
- NRC automatically calculated from 250, 500, 1000, 2000 Hz

### 5. Edit Material Dialog

**Functionality:**
- Pre-populated with selected material's data
- Same form layout as Add dialog
- Updates existing material record in database
- Recalculates NRC on save

### 6. Delete Material

**Safety Features:**
- Confirmation dialog before deletion
- Checks if material is used in any RoomSurfaceInstance
- Shows warning with usage count if material is in use
- Allows deletion even if in use (with explicit confirmation)

### 7. Save Direct Edits

**Table Editing:**
- Edit absorption coefficients directly in the table
- Auto-calculates NRC as you edit
- "Save Changes" button commits edits to database
- Refreshes list to show updated NRC values

## Technical Implementation

### Database Models Used

**Primary Model:**
```python
from models.rt60_models import AcousticMaterial, SurfaceCategory, RoomSurfaceInstance
```

**AcousticMaterial Fields:**
- 6 absorption coefficient fields (125-4000 Hz)
- NRC (calculated from 4 speech frequencies)
- Category, manufacturer, product_code, description
- Mounting type, thickness, source reference
- Created/modified timestamps

### Key Methods Implemented

**Component Library Dialog:**
- `refresh_acoustic_materials()` - Loads materials with optional project filtering
- `_clear_acoustic_material_preview()` - Clears absorption table
- `_on_acoustic_material_selected()` - Populates table when material is selected
- `_toggle_acoustic_material_buttons()` - Enables/disables Edit/Delete buttons
- `_on_acoustic_material_filter_changed()` - Handles filter checkbox
- `_on_acoustic_material_cell_changed()` - Marks dirty and auto-calculates NRC
- `save_acoustic_material_changes()` - Saves direct table edits
- `manual_add_acoustic_material()` - Opens add dialog
- `edit_selected_acoustic_material()` - Opens edit dialog
- `delete_selected_acoustic_material()` - Deletes with confirmation

**New Dialog Classes:**
- `ManualAcousticMaterialAddDialog` - Add new materials
- `AcousticMaterialEditDialog` - Edit existing materials

### NRC Calculation

NRC (Noise Reduction Coefficient) is calculated as the average of absorption coefficients at 4 speech frequencies:

```python
NRC = (α₂₅₀ + α₅₀₀ + α₁₀₀₀ + α₂₀₀₀) / 4
```

This follows the standard ASTM C423 method for calculating NRC.

### Project Filtering Logic

When "Show only project materials" is enabled:

1. Query all spaces in the current project
2. Find all RoomSurfaceInstance records for those spaces
3. Extract distinct material_ids that are in use
4. Filter AcousticMaterial query to only those IDs

## Usage Guide

### Viewing Materials

1. Open Component Library Dialog (from project dashboard or menu)
2. Navigate to "Acoustic Treatment" tab
3. Left panel shows all acoustic materials
4. Click any material to view its absorption coefficients

### Adding a New Material

1. Click "Manual Treatment Add" button
2. Fill in material name (required)
3. Enter absorption coefficients for each frequency band
4. NRC auto-calculates as you enter values
5. Fill in optional metadata (category, manufacturer, etc.)
6. Click "Save" to add to database

### Editing a Material

**Method 1: Edit Dialog**
1. Select material from list
2. Click "Edit" button
3. Modify fields as needed
4. Click "Save"

**Method 2: Direct Table Edit**
1. Select material from list
2. Double-click absorption values in table
3. Edit values directly
4. Click "Save Changes" when done

### Deleting a Material

1. Select material from list
2. Click "Delete" button
3. Review usage warning if material is in use
4. Confirm deletion

### Filtering by Project

1. Check "Show only project materials" checkbox
2. List updates to show only materials used in current project
3. Uncheck to show all global materials again

## Testing

A test script is provided: `test_acoustic_materials_tab.py`

**To run:**
```bash
python test_acoustic_materials_tab.py
```

**Test checklist:**
- [ ] Tab layout shows materials on left, schedules on right
- [ ] Materials list populates correctly
- [ ] Filter checkbox works (shows all vs project materials)
- [ ] Selecting a material displays absorption coefficients
- [ ] Manual Treatment Add dialog opens and saves correctly
- [ ] NRC auto-calculates in dialogs
- [ ] Edit dialog pre-populates and saves correctly
- [ ] Direct table editing works and enables Save button
- [ ] Delete checks for usage and confirms before deletion
- [ ] Save Changes commits table edits to database

## Notes

### Frequency Bands

**Acoustic Materials (6 bands):**
- 125, 250, 500, 1000, 2000, 4000 Hz

**Mechanical Units (8 bands):**
- 63, 125, 250, 500, 1000, 2000, 4000, 8000 Hz

Note the difference: Acoustic materials don't include 63 Hz and 8000 Hz bands.

### Global vs Project-Specific

Acoustic materials are **global** - they're stored in a shared `acoustic_materials` table, not project-specific. This allows materials to be reused across multiple projects. The project filter simply shows which materials are currently used in a specific project's spaces.

### Material Categories

Categories come from the `surface_categories` table:
- walls
- ceilings
- floors
- doors
- windows
- specialty

Categories help organize materials and can be used for filtering in other parts of the application.

## Future Enhancements

Potential improvements for future iterations:

1. **Import from PDF/CSV** - Similar to mechanical schedules, allow importing material data from manufacturer spec sheets
2. **Batch Operations** - Select and edit multiple materials at once
3. **Material Templates** - Create material templates for common treatments
4. **Material Comparison** - Side-by-side comparison of absorption coefficients
5. **Export Materials** - Export material list to Excel/CSV
6. **Material Search** - Search/filter materials by name, category, manufacturer
7. **Material History** - Track changes to materials over time
8. **Material Validation** - Warn if absorption coefficients are outside typical ranges
9. **Frequency Response Chart** - Visual graph of absorption vs frequency

## Files Modified

- `src/ui/dialogs/component_library_dialog.py` - Main implementation
- `test_acoustic_materials_tab.py` - Test script (new file)
- `ACOUSTIC_MATERIALS_TAB_ENHANCEMENT.md` - This documentation (new file)

## Dependencies

No new dependencies required. Uses existing:
- PySide6 for UI
- SQLAlchemy for database operations
- Existing models from `models.rt60_models`

