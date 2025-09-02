# Duct Dimensions Fix Summary

## Issue Description

The debugging output in `debug_data/path_6_Path__SMALL105_to_R-F-1-1_20250828_115521.csv` showed that duct dimensions entered in the Edit HVAC Segment window were not being properly passed to the calculation engine. The CSV output consistently showed default values (12.0" width, 8.0" height) even when users changed these values in the UI.

## Root Cause Analysis

The issue was in the HVAC segment dialog's `_get_upstream_context()` method in `src/ui/dialogs/hvac_segment_dialog.py`. This method calls `self.path_calculator.calculate_path_noise(self.hvac_path_id)` to get real-time calculation results for display in the dialog.

**Problem**: The path calculator was reading segment data from the database, which contained the old/default values, rather than using the current UI values that the user had entered but not yet saved.

**Flow**:
1. User opens Edit HVAC Segment dialog
2. User changes duct dimensions (e.g., width from 12" to 18")
3. Dialog calls `_get_upstream_context()` to show real-time calculations
4. `_get_upstream_context()` calls `path_calculator.calculate_path_noise()`
5. Path calculator reads segment data from database (still shows 12" width)
6. Debug output reflects database values, not UI values

## Solution Implemented

**Fix**: Modified the `_get_upstream_context()` method to update the in-memory segment object with current UI values before running the path calculation.

**Code Change** (lines 515-520 in `src/ui/dialogs/hvac_segment_dialog.py`):

```python
def _get_upstream_context(self) -> tuple:
    """Return (dba, spectrum) before this segment based on current path calc"""
    try:
        if not self.hvac_path_id:
            raise ValueError('no path id')
        
        # Update the in-memory segment object with current UI values before calculation
        if self.segment:
            self.update_segment_properties(self.segment)
        
        result = self.path_calculator.calculate_path_noise(self.hvac_path_id)
        # ... rest of method unchanged
```

## How the Fix Works

1. **Before calculation**: The fix calls `self.update_segment_properties(self.segment)` which updates the in-memory segment object with current UI values:
   - `segment.duct_width = self.width_spin.value()`
   - `segment.duct_height = self.height_spin.value()`
   - `segment.diameter = self.diameter_spin.value()`
   - etc.

2. **During calculation**: The path calculator now uses the updated in-memory segment object, which reflects the current UI values.

3. **Debug output**: The generated CSV now shows the current UI values rather than the saved database values.

## Benefits

- **Real-time accuracy**: Debug output now accurately reflects what the user sees in the UI
- **Consistent behavior**: The dialog's real-time calculations match the debug output
- **Better debugging**: Users can verify that their duct dimension changes are being properly processed
- **No side effects**: The fix only affects the dialog's real-time calculations; saved database values remain unchanged until the user explicitly saves

## Testing

The fix was verified with a test script that:
1. Created a test HVAC path with default duct dimensions (12" × 8")
2. Updated the segment dimensions in memory (18" × 12")
3. Confirmed that subsequent path calculations used the updated dimensions

## Files Modified

- `src/ui/dialogs/hvac_segment_dialog.py` - Added segment property update before path calculation

## Related Methods

The fix also benefits other methods in the same dialog that call `_get_upstream_context()`:
- `_get_downstream_context()` - Now uses updated segment properties
- `refresh_context()` - Now shows accurate real-time calculations
- `_recalc_upstream_auto()` and `_recalc_downstream_context_and_auto()` - Now use correct dimensions for fitting calculations
