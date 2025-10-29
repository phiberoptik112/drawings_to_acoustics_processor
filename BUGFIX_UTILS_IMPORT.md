# Bug Fix: Utils Import Error

## Problem

After implementing the Material Schedules feature, the application failed to start with the error:

```
ImportError: cannot import name 'get_user_data_directory' from 'utils' 
(/Users/jakepfitsch/Documents/drawings_to_acoustics_processor/src/utils/__init__.py)
```

## Root Cause

When creating the Material Schedules feature, I created:
- `src/utils/material_file_manager.py` - File management utilities
- `src/utils/__init__.py` - Package initialization file

This converted `utils` from a **module** (the existing `src/utils.py` file) into a **package** (the new `src/utils/` directory).

Python prioritizes packages over modules when both exist with the same name. This caused all existing imports like `from utils import get_user_data_directory` to fail because the new `utils/__init__.py` didn't export these functions.

## Existing Dependencies

The `src/utils.py` module contains critical utilities used throughout the codebase:
- `get_user_data_directory()` - Used by database initialization
- `get_resource_path()` - Used for resource loading
- `is_bundled_executable()` - Used for deployment detection
- `get_materials_database_path()` - Used by material database
- Plus many other deployment and resource management functions

These are imported in:
- `src/calculations/hvac_path_calculator.py`
- `src/models/database.py`
- `src/data/materials_database.py`
- Many other modules

## Solution

### 1. Moved Material File Manager
Moved the new file utilities to a more appropriate location:
```bash
mv src/utils/material_file_manager.py src/data/material_file_manager.py
```

This makes logical sense because:
- Material file management is data-related functionality
- It naturally fits with other data utilities in `src/data/`
- It avoids conflicting with the existing `utils` module

### 2. Removed Utils Package
Deleted the problematic package structure:
```bash
rm -rf src/utils/
```

This restores the original `src/utils.py` module functionality.

### 3. Updated Imports
Updated all references to use the new location:

**Before:**
```python
from src.utils.material_file_manager import (
    copy_material_schedule_to_project,
    validate_material_schedule_pdf
)
```

**After:**
```python
from data.material_file_manager import (
    copy_material_schedule_to_project,
    validate_material_schedule_pdf
)
```

Files updated:
- `src/ui/dialogs/material_schedule_dialog.py`
- `test_material_schedules.py`
- `MATERIAL_SCHEDULES_IMPLEMENTATION.md`

## Verification

Tested that critical imports work:
```bash
✅ from utils import get_user_data_directory
✅ from calculations.hvac_path_calculator import HVACPathCalculator
✅ from data.material_file_manager import get_material_schedules_folder
✅ from main import main
```

All imports now work correctly and the application starts successfully.

## Lesson Learned

When adding new utilities to a project:
1. **Check for naming conflicts** - See if a module with that name already exists
2. **Choose logical locations** - Data utilities belong in `data/`, not `utils/`
3. **Preserve existing structure** - Don't convert modules to packages without careful consideration
4. **Test imports** - Verify existing functionality still works after adding new code

## Alternative Solutions Considered

1. **Re-export from `utils/__init__.py`**: Could have imported everything from the original `utils.py` into `utils/__init__.py`, but this creates confusion about where utilities live.

2. **Rename original `utils.py`**: Could have renamed it to `app_utils.py`, but this would require updating many imports throughout the codebase.

3. **Keep both structures**: Python technically allows both, but it's confusing and error-prone.

The chosen solution (moving material utilities to `data/`) is cleanest and most maintainable.

