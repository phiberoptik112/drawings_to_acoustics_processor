# Elbow Lining Debug Output Guide

## Overview
Added comprehensive debug logging to track elbow lining and turning vane properties through the entire calculation pipeline.

## Debug Output Sections

### 1. Component Property Extraction (Path Builder)
**Location:** `src/calculations/hvac_path_calculator.py` - `_build_segment_data()` method

**What to look for:**
```
═══════════════════════════════════════════════════════
DEBUG_ELBOW_LINING: Extracting elbow properties from component
DEBUG_ELBOW_LINING:   Component ID: [component_id]
DEBUG_ELBOW_LINING:   Component name: [component_name]
DEBUG_ELBOW_LINING:   Raw lining_thickness value: [value or None]
```

**Indicates success:**
```
DEBUG_ELBOW_LINING:   ✓ LINING APPLIED: 2.0 inches
DEBUG_ELBOW_LINING:   ✓ Added to segment_data['lining_thickness']
```

**Indicates problem:**
```
DEBUG_ELBOW_LINING:   ✗ NO LINING: value is None
```

**What this tells you:**
- If you see "✗ NO LINING" and you added lining in the UI, the component's lining_thickness field wasn't saved to the database correctly
- Check that the component was saved after adding lining
- Try re-opening the component dialog to verify the lining value is still there

---

### 2. PathElement Creation (Engine Conversion)
**Location:** `src/calculations/hvac_noise_engine.py` - `_convert_path_data_to_elements()` method

**What to look for:**
```
╔═══════════════════════════════════════════════════════════════╗
║  CREATING PathElement #[N] (elbow)                            
╚═══════════════════════════════════════════════════════════════╝
DEBUG_PATH_ELEMENT: Creating PathElement from segment data:
DEBUG_PATH_ELEMENT:   lining_thickness from dict = [value]
DEBUG_PATH_ELEMENT:   vane_chord_length from dict = [value]
DEBUG_PATH_ELEMENT:   num_vanes from dict = [value]
```

**Then:**
```
DEBUG_PATH_ELEMENT: PathElement created with:
DEBUG_PATH_ELEMENT:   element.lining_thickness = [value]
DEBUG_PATH_ELEMENT:   element.vane_chord_length = [value]
DEBUG_PATH_ELEMENT:   element.num_vanes = [value]
```

**What this tells you:**
- If "lining_thickness from dict = NOT_IN_DICT", the property extraction in step 1 failed
- If "element.lining_thickness = 0.0" but "from dict = 2.0", there's an issue in PathElement creation
- Both values should match and be non-zero if lining was applied

---

### 3. Elbow Calculation (Engine Processing)
**Location:** `src/calculations/hvac_noise_engine.py` - `_calculate_elbow_effect()` method

**What to look for:**
```
╔═══════════════════════════════════════════════════════════════╗
║  ELBOW EFFECT CALCULATION - STARTING                         ║
╚═══════════════════════════════════════════════════════════════╝
DEBUG_ELBOW_ENGINE: Element properties received:
DEBUG_ELBOW_ENGINE:   element.lining_thickness = [value] in
DEBUG_ELBOW_ENGINE:   element.num_vanes = [value]
DEBUG_ELBOW_ENGINE:   element.vane_chord_length = [value] in
```

**Then for rectangular elbows:**
```
DEBUG_ELBOW_ENGINE: Rectangular elbow insertion loss calculation:
DEBUG_ELBOW_ENGINE:   lining_value = [value] in
DEBUG_ELBOW_ENGINE:   lined (boolean) = [True/False]
DEBUG_ELBOW_ENGINE:   elbow_type = [square_with_vanes or square_no_vanes]
```

**Success indicator:**
```
DEBUG_ELBOW_ENGINE:   ✓✓✓ LINING BEING APPLIED IN CALCULATION ✓✓✓
DEBUG_ELBOW_ENGINE:   Calling rect_elbows_calc with lined=True
```

**Problem indicator:**
```
DEBUG_ELBOW_ENGINE:   ✗✗✗ NO LINING IN CALCULATION ✗✗✗
DEBUG_ELBOW_ENGINE:   Calling rect_elbows_calc with lined=False
```

**Final results:**
```
╔═══════════════════════════════════════════════════════════════╗
║  ELBOW EFFECT CALCULATION - COMPLETE                         ║
╚═══════════════════════════════════════════════════════════════╝
DEBUG_ELBOW_ENGINE: Final results:
DEBUG_ELBOW_ENGINE:   Insertion loss spectrum: [...]
DEBUG_ELBOW_ENGINE:   Insertion loss dBA: [value]
DEBUG_ELBOW_ENGINE:   ✓ Lining effect included: [thickness] in
```

**What this tells you:**
- If "element.lining_thickness = N/A", the PathElement didn't receive the property
- If "lined (boolean) = False" but you added lining, the value isn't propagating
- If "✓ Lining effect included" appears, the calculation is working correctly
- Compare insertion loss dBA with and without lining - lined elbows should have higher insertion loss (more attenuation)

---

## Troubleshooting Guide

### Problem: No debug output for "ELBOW_LINING" section
**Cause:** The segment doesn't have an elbow component connected to it, or the component type doesn't contain 'elbow'

**Fix:** 
- Verify the component type includes "elbow" in the name
- Check that the path actually connects through the elbow component
- Look at earlier debug output to see what components are in the path

---

### Problem: Shows "✗ NO LINING" but you added lining in UI
**Cause:** The lining value wasn't saved to the database

**Fix:**
1. Re-open the elbow component in the UI
2. Check if the lining checkbox is still checked
3. If not checked, the save didn't work - check for errors
4. If checked, the value might be 0 - verify the spinbox shows the right value
5. Try saving again and recalculating the path

---

### Problem: Lining extracted but not in PathElement dict
**Cause:** The segment_data isn't being properly converted to path_data dictionary

**Fix:**
- Check that the segment is being built correctly
- Look for errors in the path building phase
- May indicate a bug in the conversion logic

---

### Problem: PathElement has lining but calculation doesn't use it
**Cause:** The element type might not be 'elbow', or duct_shape is 'circular'

**Fix:**
- Check the "ELBOW EFFECT CALCULATION - STARTING" output
- Verify element.duct_shape is 'rectangular' (circular elbows use different calculation)
- Verify element_type is 'elbow'

---

## Expected Output for Working Lining

When everything is working correctly, you should see:

1. **Extraction phase:**
   ```
   DEBUG_ELBOW_LINING:   ✓ LINING APPLIED: 2.0 inches
   ```

2. **PathElement creation:**
   ```
   DEBUG_PATH_ELEMENT:   lining_thickness from dict = 2.0
   DEBUG_PATH_ELEMENT:   element.lining_thickness = 2.0
   ```

3. **Calculation phase:**
   ```
   DEBUG_ELBOW_ENGINE:   element.lining_thickness = 2.0 in
   DEBUG_ELBOW_ENGINE:   lined (boolean) = True
   DEBUG_ELBOW_ENGINE:   ✓✓✓ LINING BEING APPLIED IN CALCULATION ✓✓✓
   ```

4. **Final results:**
   ```
   DEBUG_ELBOW_ENGINE:   ✓ Lining effect included: 2.0 in
   DEBUG_ELBOW_ENGINE:   Insertion loss dBA: [higher value than unlined]
   ```

---

## Comparing Lined vs Unlined

To verify lining is working:

1. Calculate path with unlined elbow, note the insertion loss dBA
2. Add 2-inch lining to elbow component and save
3. Recalculate the path
4. Compare insertion loss dBA values:
   - Lined elbow should have **higher insertion loss** (more attenuation)
   - Typical increase: 3-8 dB depending on frequency
   - Terminal noise should be **lower** with lined elbow

---

## Next Steps

Run your test again with these debug statements and paste the output. The debug messages will clearly show:
- Whether lining is being extracted from the component
- Whether it's being passed through the PathElement
- Whether it's being used in the calculation
- What the actual insertion loss values are

This will pinpoint exactly where the issue is occurring.

