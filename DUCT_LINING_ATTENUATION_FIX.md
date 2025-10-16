# Duct Lining Attenuation Fix

## Issue Summary

The 2-inch duct lining attenuation calculations were not being properly applied to path calculations due to a **frequency band mismatch** in the `RectangularDuctCalculator` class.

## Root Cause

### The Problem

1. **Data Structure**: The 2-inch lining attenuation data (`self.lining_2inch_data`) contains values for **7 frequency bands**: `[125, 250, 500, 1000, 2000, 4000, 8000]` Hz (no 63 Hz data available from ASHRAE tables)

2. **Frequency Bands Definition**: The `self.frequency_bands` variable was incorrectly set to `AcousticConstants.FREQUENCY_BANDS` which includes **8 frequency bands**: `[63, 125, 250, 500, 1000, 2000, 4000, 8000]` Hz

3. **Index Mismatch**: When the code looped through 8 frequency bands and tried to access the attenuation data arrays with 7 values, it caused:
   - **IndexError** when accessing beyond array bounds
   - **Incorrect frequency-to-value mapping** where values were shifted

### Code Location

File: `src/calculations/rectangular_duct_calculations.py`
- Line 120: `self.frequency_bands` definition in `_initialize_2inch_lining_data()`
- Lines 352-368: Loop in `get_2inch_lining_attenuation()` 
- Lines 411-417: Loop in `_interpolate_2inch_lining()`

## The Fix

### Changed Line 120

**Before:**
```python
self.frequency_bands = AcousticConstants.FREQUENCY_BANDS.copy()
```

**After:**
```python
self.frequency_bands = [125, 250, 500, 1000, 2000, 4000, 8000]
```

### Why This Works

1. `self.frequency_bands` now matches the actual data in `self.lining_2inch_data` (7 bands)
2. The 63 Hz band is explicitly handled separately with `result['63'] = 0.0` (lines 366 and 415)
3. The loop `for i, freq in enumerate(self.frequency_bands)` now correctly maps:
   - i=0, freq=125 → `attenuation_per_ft[0]` ✓
   - i=1, freq=250 → `attenuation_per_ft[1]` ✓
   - ...
   - i=6, freq=8000 → `attenuation_per_ft[6]` ✓

## Additional Changes

### Debug Logging

Added comprehensive debug logging to help track attenuation calculations:

1. **Input parameters**: Width, height, length
2. **Calculation method**: Exact match vs interpolated
3. **Reference size**: For interpolated calculations
4. **Frequency bands**: Shows which bands are being processed
5. **Attenuation values**: Per-foot and total for each band
6. **Result structure**: Shows all 8 bands (63 Hz through 8000 Hz)

Debug output is enabled with the `HVAC_DEBUG_EXPORT` environment variable.

## Test Results

Verified the fix with test cases:

### Test 1: Exact Match (24" x 24", 11.9 ft)
- ✓ All 8 frequency bands present
- ✓ 63 Hz correctly set to 0.00 dB
- ✓ 125-8000 Hz have calculated attenuation values
- Example: 1000 Hz = 41.65 dB attenuation

### Test 2: Interpolated (20" x 20", 5.0 ft)
- ✓ Used closest reference size (18" x 18")
- ✓ All 8 frequency bands present
- ✓ 63 Hz correctly set to 0.00 dB
- ✓ 125-8000 Hz have interpolated attenuation values

## Impact

This fix ensures that:
1. **Duct lining attenuation is properly calculated** for all rectangular ducts with 2-inch fiberglass lining
2. **Path noise calculations** now correctly include the attenuation benefit of duct lining
3. **All frequency bands** (63 Hz through 8000 Hz) are properly accounted for
4. **HVAC system noise predictions** are more accurate

## Related Files

- `src/calculations/rectangular_duct_calculations.py` - Fixed frequency band definition
- `src/calculations/hvac_noise_engine.py` - Consumes the corrected attenuation data (lines 897-910)
- `src/calculations/acoustic_utilities.py` - Defines the standard 8-band frequency array

## Date
October 4, 2025

