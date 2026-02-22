# Page Navigation and Element Visibility Fix Summary

## Problem Description

Users reported multiple issues with drawing elements (components and segments) across multi-page PDF drawings:

1. **Ghost elements**: Components and segments appeared in the Path Element List on page 1 that weren't visible on the PDF
2. **Elements disappearing after page navigation**: After creating a path on page 2, navigating to page 1 and back to page 2 caused elements to become invisible
3. **Visibility toggles not working**: The eye icon and "Show All" buttons failed to restore visibility after page navigation
4. **Elements appearing on wrong pages**: Path elements created on page 2 sometimes appeared on page 1

## Root Cause Analysis

Through runtime log analysis, the following issues were identified:

### Issue 1: Path elements not re-registered after page change
When changing pages, the system:
1. Called `clear_all_elements()` to remove all overlay elements
2. Called `load_saved_elements()` which correctly skips path-linked elements (to avoid duplicates)
3. **Failed to re-register HVAC paths**, leaving path-linked elements missing from the overlay

### Issue 2: Incorrect page_number assignment during reconstruction
When `_reconstruct_path_visuals_from_db()` ran, it was assigning `page_number: current_page` (the page being viewed) instead of the element's actual creation page. This caused elements to be tagged with the wrong page.

### Issue 3: Missing page-level filtering at render time
The drawing methods (`draw_components`, `draw_segments`) weren't filtering elements by page, allowing elements from other pages to be rendered.

## Fixes Applied

### Fix 1: Re-register HVAC paths after page change
**File:** `src/ui/drawing_interface.py`

Added new method `_register_hvac_paths_for_current_page()` that queries all HVAC paths for the project and registers their elements after a page change:

```python
def _register_hvac_paths_for_current_page(self):
    """Re-register HVAC paths after page change to load path-linked elements."""
    if not self.project_id or not self.drawing_overlay:
        return
    
    from models.hvac import HVACPath
    session = get_session()
    
    hvac_paths = session.query(HVACPath).filter(
        HVACPath.project_id == self.project_id
    ).all()
    
    for hvac_path in hvac_paths:
        self.register_existing_path_elements(hvac_path)
    
    session.close()
```

This is called in `_on_page_changed()` after `load_saved_elements()`.

### Fix 2: Correct page_number sourcing during reconstruction
**File:** `src/ui/drawing_interface.py`

Modified `_reconstruct_path_visuals_from_db()` to source `page_number` from the actual database records instead of using the currently viewed page:

- For components: `comp_page = getattr(db_comp, 'page_number', None)`
- For segments: `seg_page = getattr(from_comp, 'page_number', None) or getattr(to_comp, 'page_number', None)`

### Fix 3: Page-level filtering in drawing methods
**File:** `src/drawing/drawing_overlay.py`

Added `current_page` tracking to `DrawingOverlay` and filtering logic in `draw_components()` and `draw_segments()`:

```python
# In __init__:
self.current_page = 1

# In draw_components/draw_segments:
if comp_page is not None and comp_page != self.current_page:
    continue  # Skip elements not on current page
```

### Fix 4: Update overlay's current_page on navigation
**File:** `src/ui/drawing_interface.py`

In `_on_page_changed()`, added:
```python
self.drawing_overlay.current_page = self.current_page_number
```

## Files Modified

1. **src/ui/drawing_interface.py**
   - Added `_register_hvac_paths_for_current_page()` method
   - Modified `_on_page_changed()` to call new method and update overlay's current_page
   - Fixed page_number assignment in `_reconstruct_path_visuals_from_db()`
   - Removed incorrect page_number fallbacks in `register_existing_path_elements()`

2. **src/drawing/drawing_overlay.py**
   - Added `self.current_page` attribute
   - Added page filtering in `draw_components()` and `draw_segments()`

## Testing Verification

The fix was verified through runtime logging which showed:
- Before fix: `total_segments: 2` on page 1, then `total_segments: 0` on page 2 after navigation
- After fix: Path elements correctly load and display on their assigned page after navigation

## Notes

**Ghost Elements**: Some legacy DrawingElement records may exist in the database without proper `hvac_path_id` linkage. These are loaded by `load_elements()` and appear as "ghost" entries. They can be cleaned up by deleting orphaned DrawingElement records from the database, or they will be removed when the user clicks the "Clear" button.
