# HVAC Path Restructuring Guide - Component-Based Elbows

## Overview
Fittings have been **disabled** from affecting NC calculations. All acoustic effects must now come from **standalone components** (elbow components, junction components, etc.) that segments connect through.

## Changes Made

### 1. Disabled Fitting Calculations
**File: `src/calculations/hvac_noise_engine.py`** (line 929-940)
- Fitting effects in duct calculations are now **DISABLED**
- Fittings are treated as informational/optional only
- No impact on NC values or octave band spectra

**File: `src/calculations/path_data_builder.py`** (line 342-346)
- Automatic junction/elbow element insertion from fittings **DISABLED**
- Fittings no longer create standalone calculation elements

### 2. Component Properties Work Correctly
**When segments connect through elbow components:**
- Lining thickness is extracted from component
- Turning vane properties are extracted from component
- Properties flow through PathElement to calculations
- Elbow effect calculations use component properties

## How to Structure Paths for Elbow Effects

### OLD WAY (Fittings - Now Disabled) ❌
```
[Fan Component] 
    ↓
[Segment with elbow_90 fitting] ← Fitting doesn't affect calculations anymore
    ↓
[Terminal Component]
```

**Problem:** Fittings don't have lining/turning vane properties and don't affect NC.

---

### NEW WAY (Components - Enabled) ✅
```
[Fan Component - RF 1-1]
    ↓
[Segment 1: Straight duct run]
    ↓
[Elbow Component - ELBOW-1] ← Has lining & turning vane properties
    ↓
[Segment 2: Straight duct run]
    ↓
[Terminal Component - Diffuser]
```

**Benefit:** Elbow component has all properties and affects calculations.

## Step-by-Step: Creating a Proper Elbow Path

### Step 1: Create Components

1. **Create Source Component (Fan/AHU)**
   - Component Type: `fan`, `ahu`, `rf`, or similar
   - Set noise level and CFM
   - Position it on drawing

2. **Create Elbow Component**
   - Component Type: `elbow`, `elbow_90_no_vanes`, or similar
   - Configure elbow properties:
     - Check "Has Lining" → Set thickness (0.5, 1.0, or 2.0 inches)
     - Check "Has Turning Vanes" → Set chord length and vane count
   - Position it on drawing downstream from source

3. **Create Terminal Component (Grille/Diffuser)**
   - Component Type: `grille` or `diffuser`
   - Position it on drawing downstream from elbow

### Step 2: Create Segments

1. **Segment 1: Source to Elbow**
   - From: Fan component
   - To: Elbow component
   - Set duct dimensions (width, height, shape)
   - Set lining if duct itself is lined
   - **Do NOT add elbow as fitting** - it's a component!

2. **Segment 2: Elbow to Terminal**
   - From: Elbow component
   - To: Terminal component
   - Set duct dimensions
   - Set lining if duct itself is lined

### Step 3: Set Primary Source

1. Open path properties
2. Set Primary Source to the **Fan component** (not the elbow!)
3. Link to mechanical unit for accurate spectrum (optional)

### Step 4: Calculate

1. Calculate path noise
2. Check debug output for:
   ```
   ═══════════════════════════════════════════════════════
   DEBUG_ELBOW_LINING: Extracting elbow properties from component
   DEBUG_ELBOW_LINING:   ✓ LINING APPLIED: 2.0 inches
   ```
3. Verify elbow effect in output:
   ```
   ╔═══════════════════════════════════════════════════════════════╗
   ║  ELBOW EFFECT CALCULATION - STARTING                         ║
   ╚═══════════════════════════════════════════════════════════════╝
   DEBUG_ELBOW_ENGINE:   ✓✓✓ LINING BEING APPLIED IN CALCULATION ✓✓✓
   ```

## Example: Converting Existing Path

### Current Structure (With Fittings - Not Working)
```
Primary Source: ELBOW-1 (component ID=5)
Segments:
  - Segment 1: Component 218 → 217 (with tee_branch fitting)
  - Segment 2: Component 217 → 215 (with tee_branch and elbow_90 fittings)
  - Segment 3: Component 215 → 216 (with elbow_90 fitting)
```

**Problems:**
- Elbow is primary source (should be equipment)
- Segments don't connect through elbow component
- Elbow exists only as fittings (now disabled)
- Lining on ELBOW-1 component is never used

---

### Restructured (Component-Based - Working)
```
Primary Source: RF 1-1 (fan component)

Components:
  - Component 1: RF 1-1 (fan) - ID=197
  - Component 2: ELBOW-1 (elbow) - ID=5 - Has lining & turning vanes
  - Component 3: DIFFUSER-1 (diffuser) - ID=216

Segments:
  - Segment 1: RF 1-1 → ELBOW-1
    - Duct dimensions: 24x24 inches
    - Lining: 2 inches (duct lining, separate from elbow lining)
    - NO fittings needed
    
  - Segment 2: ELBOW-1 → DIFFUSER-1
    - Duct dimensions: 12x8 inches
    - Lining: as needed
    - NO fittings needed
```

**Benefits:**
- Clear acoustic path
- Elbow properties properly extracted
- Lining on elbow component affects elbow insertion loss
- Turning vanes generate additional noise
- Path calculations work correctly

## What About Junctions?

Same principle - create junction components:

```
[Main Duct] → [Junction Component - JUNCTION-T-1] → [Branch Duct]
                       ↑
              Component-based junction
              Properties can be configured
```

Available junction component types:
- `junction_t` - T-Junction
- `junction_x` - X-Junction (cross)
- `branch_takeoff_90` - 90° Branch Takeoff

## Verifying It Works

After restructuring, you should see:

### Debug Output
```
═══════════════════════════════════════════════════════
DEBUG_ELBOW_LINING: Extracting elbow properties from component
DEBUG_ELBOW_LINING:   Component ID: 5
DEBUG_ELBOW_LINING:   Component name: ELBOW-1
DEBUG_ELBOW_LINING:   Component type: elbow
DEBUG_ELBOW_LINING:   ✓ LINING APPLIED: 2.0 inches
DEBUG_ELBOW_LINING:   ✓ TURNING VANES: chord=6.0 in, num=5
═══════════════════════════════════════════════════════

╔═══════════════════════════════════════════════════════════════╗
║  CREATING PathElement #2 (elbow)                
╚═══════════════════════════════════════════════════════════════╝
DEBUG_PATH_ELEMENT:   element.lining_thickness = 2.0

╔═══════════════════════════════════════════════════════════════╗
║  ELBOW EFFECT CALCULATION - STARTING                         ║
╚═══════════════════════════════════════════════════════════════╝
DEBUG_ELBOW_ENGINE:   ✓✓✓ LINING BEING APPLIED IN CALCULATION ✓✓✓
DEBUG_ELBOW_ENGINE:   ✓ Turning vane effect included: 5 vanes, 6.0 in chord
```

### Calculation Results
- Elbow insertion loss will be higher with lining (more attenuation)
- Terminal noise will be lower (more quiet)
- NC rating may improve
- Turning vanes will add generated noise in specific frequency bands

## Migration Checklist

For each existing path with elbows:

- [ ] Identify elbow locations (currently as fittings)
- [ ] Create elbow components at those locations
- [ ] Configure elbow properties (lining, turning vanes)
- [ ] Update segments to connect through elbow components
- [ ] Remove elbow fittings from segments
- [ ] Set proper primary source (equipment, not elbow)
- [ ] Recalculate path
- [ ] Verify debug output shows elbow properties being used
- [ ] Compare results: terminal noise and NC rating

## Quick Test Path

Create a simple test path to verify everything works:

1. **Components:**
   - FAN-1 (x=100, y=100, noise=78 dBA, CFM=1000)
   - ELBOW-1 (x=200, y=100, with 2" lining, 5 turning vanes, 6" chord)
   - DIFF-1 (x=300, y=100)

2. **Segments:**
   - Seg 1: FAN-1 → ELBOW-1 (10 ft, 24x24")
   - Seg 2: ELBOW-1 → DIFF-1 (10 ft, 12x8")

3. **Calculate:**
   - Should see elbow property extraction
   - Should see elbow effect calculation
   - Terminal noise should include elbow attenuation + turning vane noise

## Summary

✅ Fitting calculations disabled - fittings won't affect NC
✅ Elbow component properties ready to use
✅ Debug logging comprehensive
✅ Code ready for component-based approach

**Next step:** Restructure your test path to have segments connect through the elbow component instead of using it as the source or as fittings.

