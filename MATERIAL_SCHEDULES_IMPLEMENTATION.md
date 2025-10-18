# Material Schedules Feature Implementation Summary

## Overview
Successfully implemented Material Schedule management as a property of DrawingSet, accessible through the Component Library dialog in the Project Dashboard.

## Components Implemented

### 1. Database Layer

#### MaterialSchedule Model (`src/models/material_schedule.py`)
- **Fields:**
  - `id` - Primary key
  - `drawing_set_id` - Foreign key to drawing_sets
  - `name` - Schedule name (e.g., "Interior Finishes Schedule")
  - `description` - Optional description
  - `file_path` - External PDF path
  - `managed_file_path` - Project-managed copy path
  - `schedule_type` - Category (finishes, materials, acoustic_treatments, etc.)
  - `created_date`, `modified_date` - Timestamps

- **Methods:**
  - `get_display_path()` - Returns preferred file path (managed if available, otherwise external)
  - `has_valid_file()` - Checks if at least one file path exists

#### DrawingSet Model Updates (`src/models/drawing_sets.py`)
- Added `material_schedules` relationship with cascade delete

#### Database Migration (`src/models/migrate_material_schedules.py`)
- Creates `material_schedules` table with proper indexes
- Can be run standalone: `python -m src.models.migrate_material_schedules`

### 2. File Management Utilities (`src/data/material_file_manager.py`)

Provides utilities for managing material schedule PDF files:

- `get_material_schedules_folder(project_location)` - Returns/creates materials folder
- `get_drawing_set_materials_folder(project_location, drawing_set_name)` - Returns/creates drawing set subfolder
- `copy_material_schedule_to_project(source_path, project_location, drawing_set_name, target_filename)` - Copies PDF to project folder
- `validate_material_schedule_pdf(file_path)` - Validates PDF exists and is readable
- `delete_managed_file(managed_path)` - Deletes project-managed copies (preserves external files)

**File Organization:**
```
project_location/
  materials/
    DD_Phase_1/
      Interior_Finishes.pdf
      Acoustic_Treatments.pdf
    CD_Phase_2/
      Final_Finishes.pdf
```

### 3. User Interface Components

#### Project Dashboard (`src/ui/project_dashboard.py`)
- Added "Component Library" button above "Open Drawing Editor" button
- Button opens the ComponentLibraryDialog with all three tabs

#### Component Library Dialog (`src/ui/dialogs/component_library_dialog.py`)
- **New "Acoustic Treatment" Tab:**
  - Left panel: List of material schedules grouped by drawing set
  - Right panel: PDF preview with management controls
  - Buttons: Add Schedule, Edit, Delete, Compare Schedules

- **Methods Added:**
  - `create_acoustic_treatment_tab()` - Builds the UI
  - `refresh_material_schedules()` - Loads schedules from database
  - `on_material_schedule_selected()` - Handles selection and PDF preview
  - `add_material_schedule()` - Opens add dialog
  - `edit_material_schedule()` - Opens edit dialog
  - `delete_material_schedule()` - Removes schedule with confirmation
  - `load_material_schedule_pdf()` - Manual PDF loading
  - `compare_material_schedules()` - Opens comparison window

#### Material Schedule Dialog (`src/ui/dialogs/material_schedule_dialog.py`)
Add/edit dialog for material schedules:
- Drawing Set dropdown with phase icons
- Schedule name and description fields
- Schedule type combo box (finishes, materials, acoustic_treatments, etc.)
- PDF file browser
- "Copy to project folder" checkbox (default: checked)
- Validates PDFs before saving

#### Material Schedule Comparison Dialog (`src/ui/dialogs/material_schedule_comparison_dialog.py`)
Side-by-side PDF comparison:
- Two dropdown selectors for drawing sets
- Schedule navigation for each set
- Split-view PDF viewers
- Optional zoom synchronization (placeholder for future enhancement)

## Usage

### Adding a Material Schedule

1. Open Project Dashboard
2. Click "Component Library" button
3. Navigate to "Acoustic Treatment" tab
4. Click "Add Schedule"
5. Fill in details:
   - Select drawing set
   - Enter schedule name
   - Choose schedule type
   - Browse for PDF file
   - Check "Copy to project folder" if desired
6. Click "Save"

### Viewing Material Schedules

Material schedules are organized by drawing set in the list:
```
═══ 🟦 DD Phase 1 (DD) ═══
  📄 Interior Finishes (finishes)
  📄 Acoustic Treatments (acoustic_treatments)
═══ 🟥 CD Phase 2 (CD) ═══
  📄 Final Finishes (finishes)
```

Click any schedule to preview the PDF in the right panel.

### Comparing Material Schedules

1. In the Acoustic Treatment tab, click "Compare Schedules"
2. Select base drawing set and schedule (left side)
3. Select compare drawing set and schedule (right side)
4. View PDFs side-by-side

### Editing/Deleting

- Select a schedule and click "Edit" to modify properties
- Select a schedule and click "Delete" to remove (PDF files remain on disk)

## File Storage Options

The system supports two storage modes:

1. **External Path Only:**
   - Uncheck "Copy to project folder"
   - Only stores reference to original PDF location
   - Use when PDFs are in shared network location

2. **Project-Managed Copy:**
   - Check "Copy to project folder" (default)
   - Copies PDF to `project_location/materials/{drawing_set_name}/`
   - Use for project portability

Both paths are stored; managed path is preferred when displaying.

## Testing

Run the test suite:
```bash
python test_material_schedules.py
```

Tests cover:
- Database model creation and relationships
- File utility operations
- Model methods (get_display_path, has_valid_file)

## Future Enhancements

Planned but not yet implemented:

1. **OCR Parsing:** Parse material data from PDFs (similar to mechanical schedule import)
2. **Material Linking:** Link parsed materials to Space objects
3. **Advanced Comparison:** Show specific material changes with acoustic impact analysis
4. **Change Tracking:** Track material changes across drawing set versions
5. **RT60 Integration:** Automatic RT60 recalculation when materials change

## Database Schema

```sql
CREATE TABLE material_schedules (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    drawing_set_id INTEGER NOT NULL,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    file_path VARCHAR(1000),           -- External path
    managed_file_path VARCHAR(1000),   -- Project-managed copy
    schedule_type VARCHAR(100) DEFAULT 'finishes',
    created_date DATETIME DEFAULT CURRENT_TIMESTAMP,
    modified_date DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (drawing_set_id) REFERENCES drawing_sets(id) ON DELETE CASCADE
);

CREATE INDEX idx_material_schedules_drawing_set ON material_schedules(drawing_set_id);
CREATE INDEX idx_material_schedules_schedule_type ON material_schedules(schedule_type);
```

## Files Created/Modified

### New Files:
- `src/models/material_schedule.py` - MaterialSchedule model
- `src/models/migrate_material_schedules.py` - Database migration
- `src/data/material_file_manager.py` - File management utilities
- `src/ui/dialogs/material_schedule_dialog.py` - Add/edit dialog
- `src/ui/dialogs/material_schedule_comparison_dialog.py` - Comparison dialog
- `test_material_schedules.py` - Test suite

### Modified Files:
- `src/models/drawing_sets.py` - Added material_schedules relationship
- `src/models/__init__.py` - Added MaterialSchedule import
- `src/ui/project_dashboard.py` - Added Component Library button
- `src/ui/dialogs/component_library_dialog.py` - Added Acoustic Treatment tab

## Notes

- Material schedule PDFs are never automatically deleted from disk, even when removing schedules from the database
- Drawing set names are sanitized for filesystem safety (alphanumeric, spaces, hyphens, underscores)
- PDF validation uses PyMuPDF when available for thorough validation
- Maximum PDF size: 100 MB
- The feature integrates seamlessly with existing drawing set version tracking

