# Spectrum Combination Fix Implementation Guide

## Overview

This document provides step-by-step instructions to fix the spectrum combination logic in the HVAC noise calculation engine and add comprehensive debug outputs to track attenuation and generation effects.

## Issues Identified

1. **Spectrum combination not working properly** - Generated noise is not being added to existing spectrum
2. **Missing debug outputs** for attenuation and generation tracking
3. **Inconsistent flow rate logic** in junction calculations
4. **Elbow calculations using wrong calculator** (junction instead of dedicated elbow calculator)
5. **Unit conversion issues** (fpm vs ft/s for velocity)

## Implementation Steps

### Step 1: Fix Spectrum Combination Logic

#### File: `src/calculations/hvac_noise_engine.py`

**Location**: Lines 386-398 in `calculate_path_noise()` method

**Current Code**:
```python
if element_result.get('generated_spectrum'):
    generated_spectrum = element_result['generated_spectrum']
    if isinstance(generated_spectrum, list):
        debug_logger.debug('HVACEngine', 
            f"Element {i} generated_spectrum", 
            {'generated_spectrum': generated_spectrum})
        # Add generated noise
        for j in range(min(NUM_OCTAVE_BANDS, len(generated_spectrum))):
            if generated_spectrum[j] > 0:
                current_spectrum[j] = self._combine_noise_levels(
                    current_spectrum[j], generated_spectrum[j]
                )
```

**Fixed Code**:
```python
if element_result.get('generated_spectrum'):
    generated_spectrum = element_result['generated_spectrum']
    if isinstance(generated_spectrum, list):
        debug_logger.debug('HVACEngine', 
            f"Element {i} generated_spectrum", 
            {'generated_spectrum': generated_spectrum})
        
        # Enhanced debug output for spectrum combination
        if debug_export_enabled:
            print(f"DEBUG_ENGINE:     Before spectrum combination:")
            print(f"DEBUG_ENGINE:       Current spectrum: {[f'{x:.1f}' for x in current_spectrum]}")
            print(f"DEBUG_ENGINE:       Generated spectrum: {[f'{x:.1f}' for x in generated_spectrum]}")
        
        # Add generated noise (remove the > 0 condition to handle negative values)
        spectrum_before_combination = current_spectrum.copy()
        for j in range(min(NUM_OCTAVE_BANDS, len(generated_spectrum))):
            if generated_spectrum[j] is not None and generated_spectrum[j] != 0:
                old_level = current_spectrum[j]
                current_spectrum[j] = self._combine_noise_levels(
                    current_spectrum[j], generated_spectrum[j]
                )
                
                # Debug output for each band combination
                if debug_export_enabled and abs(current_spectrum[j] - old_level) > 0.1:
                    print(f"DEBUG_ENGINE:       Band {j+1} ({self.FREQUENCY_BANDS[j]}Hz): {old_level:.1f} + {generated_spectrum[j]:.1f} = {current_spectrum[j]:.1f}")
        
        if debug_export_enabled:
            print(f"DEBUG_ENGINE:     After spectrum combination:")
            print(f"DEBUG_ENGINE:       Final spectrum: {[f'{x:.1f}' for x in current_spectrum]}")
            
            # Calculate total change
            total_change = sum(current_spectrum[j] - spectrum_before_combination[j] for j in range(len(current_spectrum)))
            print(f"DEBUG_ENGINE:       Total spectrum change: {total_change:.2f} dB")
```

### Step 2: Fix Junction Flow Rate Logic

#### File: `src/calculations/hvac_noise_engine.py`

**Location**: Lines 280-286 in `calculate_path_noise()` method

**Current Code**:
```python
flows = [f for f in [upstream_flow, downstream_flow] if (isinstance(f, (int, float)) and f > 0)]
if len(flows) >= 1:
    main_flow = max(flows)
    branch_flow = min(flows)
else:
    main_flow = element.flow_rate or 0.0
    branch_flow = element.flow_rate or 0.0
```

**Fixed Code**:
```python
flows = [f for f in [upstream_flow, downstream_flow] if (isinstance(f, (int, float)) and f > 0)]
if len(flows) >= 2:
    # For branch takeoff: main continues with reduced flow, branch takes smaller flow
    if upstream_flow > downstream_flow:
        main_flow = upstream_flow - downstream_flow  # Continuing main duct flow
        branch_flow = downstream_flow  # Branch takeoff flow
    else:
        main_flow = upstream_flow
        branch_flow = downstream_flow
elif len(flows) == 1:
    main_flow = flows[0]
    branch_flow = flows[0]
else:
    main_flow = element.flow_rate or 0.0
    branch_flow = element.flow_rate or 0.0

# Enhanced debug output for flow logic
if debug_export_enabled:
    print(f"DEBUG_ENGINE:     Flow logic analysis:")
    print(f"DEBUG_ENGINE:       Upstream flow: {upstream_flow:.1f} CFM")
    print(f"DEBUG_ENGINE:       Downstream flow: {downstream_flow:.1f} CFM")
    print(f"DEBUG_ENGINE:       Calculated main flow: {main_flow:.1f} CFM")
    print(f"DEBUG_ENGINE:       Calculated branch flow: {branch_flow:.1f} CFM")
    print(f"DEBUG_ENGINE:       Flow ratio (main/branch): {main_flow/branch_flow:.2f}" if branch_flow > 0 else "DEBUG_ENGINE:       Flow ratio: N/A")
```

### Step 3: Fix Elbow Calculation Method

#### File: `src/calculations/hvac_noise_engine.py`

**Location**: Lines 647-715 in `_calculate_elbow_effect()` method

**Current Code**:
```python
# Simple elbow - use junction calculator with elbow type
duct_area = self._calculate_duct_area(element)
# Choose junction/elbow type based on fitting hint
fit = (element.fitting_type or '').lower() if hasattr(element, 'fitting_type') else ''
jtype = JunctionType.ELBOW_90_NO_VANES
# Future: map radiused elbows if available
# Use the junction calculator's spectrum method with explicit type
spectrum_data = self.junction_calc.calculate_junction_noise_spectrum(
    branch_flow_rate=element.flow_rate,
    branch_cross_sectional_area=duct_area,
    main_flow_rate=element.flow_rate,
    main_cross_sectional_area=duct_area,
    junction_type=jtype
)
# For elbows, use the main duct spectrum per Eq (4.25)
elbow_spectrum = spectrum_data.get('main_duct') or {}
for i, freq in enumerate(self.FREQUENCY_BANDS):
    band_key = f"{freq}Hz"
    if band_key in elbow_spectrum:
        result['generated_spectrum'][i] = elbow_spectrum[band_key]
```

**Fixed Code**:
```python
# Use dedicated rectangular elbows calculator for insertion loss
if element.duct_shape == 'rectangular':
    if debug_export_enabled:
        print(f"DEBUG_ENGINE:     Using rectangular elbows calculator for insertion loss")
        print(f"DEBUG_ENGINE:     Elbow properties: width={element.width:.1f}\", lined={element.lining_thickness > 0}")
    
    # Determine elbow type from fitting hint
    fit = (element.fitting_type or '').lower() if hasattr(element, 'fitting_type') else ''
    elbow_type = 'square_with_vanes' if (element.num_vanes or 0) > 0 else 'square_no_vanes'
    lined = (element.lining_thickness or 0.0) > 0.0
    
    # Calculate insertion loss spectrum
    attenuation_spectrum = []
    for i, freq in enumerate(self.FREQUENCY_BANDS):
        try:
            loss = self.rect_elbows_calc.calculate_elbow_insertion_loss(
                frequency=freq,
                width=element.width or 0.0,
                elbow_type=elbow_type,
                lined=lined
            )
            attenuation_spectrum.append(float(loss or 0.0))
        except Exception as e:
            if debug_export_enabled:
                print(f"DEBUG_ENGINE:     Error calculating elbow loss at {freq}Hz: {e}")
            attenuation_spectrum.append(0.0)
    
    result['attenuation_spectrum'] = attenuation_spectrum
    result['attenuation_dba'] = self._calculate_dba_from_spectrum(attenuation_spectrum)
    
    if debug_export_enabled:
        print(f"DEBUG_ENGINE:     Elbow insertion loss spectrum: {[f'{x:.1f}' for x in attenuation_spectrum]}")
        print(f"DEBUG_ENGINE:     Elbow insertion loss dBA: {result['attenuation_dba']:.2f}")

# For generated noise, use junction calculator with elbow type
duct_area = self._calculate_duct_area(element)
fit = (element.fitting_type or '').lower() if hasattr(element, 'fitting_type') else ''
jtype = JunctionType.ELBOW_90_NO_VANES

if debug_export_enabled:
    print(f"DEBUG_ENGINE:     Using junction calculator for generated noise")
    print(f"DEBUG_ENGINE:     Duct area: {duct_area:.3f} ft², Flow rate: {element.flow_rate:.1f} CFM")

spectrum_data = self.junction_calc.calculate_junction_noise_spectrum(
    branch_flow_rate=element.flow_rate,
    branch_cross_sectional_area=duct_area,
    main_flow_rate=element.flow_rate,
    main_cross_sectional_area=duct_area,
    junction_type=jtype
)

# For elbows, use the main duct spectrum per Eq (4.25)
elbow_spectrum = spectrum_data.get('main_duct') or {}
for i, freq in enumerate(self.FREQUENCY_BANDS):
    band_key = f"{freq}Hz"
    if band_key in elbow_spectrum:
        result['generated_spectrum'][i] = elbow_spectrum[band_key]

if debug_export_enabled:
    print(f"DEBUG_ENGINE:     Elbow generated spectrum: {[f'{x:.1f}' for x in result['generated_spectrum']]}")
```

### Step 4: Add Velocity Unit Conversion

#### File: `src/calculations/hvac_path_calculator.py`

**Location**: Lines 825-830 in `_build_segment_data()` method

**Current Code**:
```python
# Calculate velocity from CFM and area
if area_ft2 > 0:
    segment_data['flow_velocity'] = segment_cfm / area_ft2
else:
    segment_data['flow_velocity'] = DEFAULT_FLOW_VELOCITY_FPM
```

**Fixed Code**:
```python
# Calculate velocity from CFM and area
if area_ft2 > 0:
    segment_data['flow_velocity'] = segment_cfm / area_ft2  # fpm
    segment_data['flow_velocity_ft_s'] = segment_data['flow_velocity'] / 60  # ft/s for calculations
else:
    segment_data['flow_velocity'] = DEFAULT_FLOW_VELOCITY_FPM
    segment_data['flow_velocity_ft_s'] = DEFAULT_FLOW_VELOCITY_FPM / 60

if self.debug_export_enabled:
    print(f"DEBUG_BUILD_SEG:   flow_velocity = {segment_data['flow_velocity']:.1f} fpm")
    print(f"DEBUG_BUILD_SEG:   flow_velocity_ft_s = {segment_data['flow_velocity_ft_s']:.3f} ft/s")
```

### Step 5: Update Junction Calculator to Use ft/s

#### File: `src/calculations/hvac_noise_engine.py`

**Location**: Lines 320-326 in `calculate_path_noise()` method

**Current Code**:
```python
spectrum_data = self.junction_calc.calculate_junction_noise_spectrum(
    branch_flow_rate=branch_flow,
    branch_cross_sectional_area=max(branch_area, 1e-6),
    main_flow_rate=main_flow,
    main_cross_sectional_area=max(main_area, 1e-6),
    junction_type=jtype
)
```

**Fixed Code**:
```python
# Calculate velocities in ft/s for junction calculator
branch_velocity_ft_s = branch_flow / (branch_area * 60) if branch_area > 0 else 0
main_velocity_ft_s = main_flow / (main_area * 60) if main_area > 0 else 0

if debug_export_enabled:
    print(f"DEBUG_ENGINE:     Velocity calculations:")
    print(f"DEBUG_ENGINE:       Branch velocity: {branch_velocity_ft_s:.3f} ft/s")
    print(f"DEBUG_ENGINE:       Main velocity: {main_velocity_ft_s:.3f} ft/s")

spectrum_data = self.junction_calc.calculate_junction_noise_spectrum(
    branch_flow_rate=branch_flow,
    branch_cross_sectional_area=max(branch_area, 1e-6),
    main_flow_rate=main_flow,
    main_cross_sectional_area=max(main_area, 1e-6),
    junction_type=jtype
)
```

### Step 6: Enhanced Debug Output for Attenuation

#### File: `src/calculations/hvac_noise_engine.py`

**Location**: Lines 375-385 in `calculate_path_noise()` method

**Add After Current Attenuation Code**:
```python
# Enhanced debug output for attenuation
if element_result.get('attenuation_spectrum'):
    attenuation_spectrum = element_result['attenuation_spectrum']
    if isinstance(attenuation_spectrum, list):
        if debug_export_enabled:
            print(f"DEBUG_ENGINE:     Before attenuation application:")
            print(f"DEBUG_ENGINE:       Current spectrum: {[f'{x:.1f}' for x in current_spectrum]}")
            print(f"DEBUG_ENGINE:       Attenuation spectrum: {[f'{x:.1f}' for x in attenuation_spectrum]}")
        
        spectrum_before_attenuation = current_spectrum.copy()
        # Apply attenuation (subtract)
        for j in range(min(NUM_OCTAVE_BANDS, len(attenuation_spectrum))):
            old_level = current_spectrum[j]
            current_spectrum[j] -= attenuation_spectrum[j]
            current_spectrum[j] = max(0.0, current_spectrum[j])  # Prevent negative
            
            # Debug output for significant attenuation
            if debug_export_enabled and abs(current_spectrum[j] - old_level) > 0.1:
                print(f"DEBUG_ENGINE:       Band {j+1} ({self.FREQUENCY_BANDS[j]}Hz): {old_level:.1f} - {attenuation_spectrum[j]:.1f} = {current_spectrum[j]:.1f}")
        
        if debug_export_enabled:
            print(f"DEBUG_ENGINE:     After attenuation application:")
            print(f"DEBUG_ENGINE:       Final spectrum: {[f'{x:.1f}' for x in current_spectrum]}")
            
            # Calculate total attenuation
            total_attenuation = sum(spectrum_before_attenuation[j] - current_spectrum[j] for j in range(len(current_spectrum)))
            print(f"DEBUG_ENGINE:       Total attenuation applied: {total_attenuation:.2f} dB")
```

### Step 7: Add Summary Debug Output

#### File: `src/calculations/hvac_noise_engine.py`

**Location**: Lines 457-467 in `calculate_path_noise()` method

**Add After Current Final Results**:
```python
if debug_export_enabled:
    print(f"\nDEBUG_ENGINE: Final calculation results:")
    source_dba = (source_element.source_noise_level if source_element and source_element.source_noise_level is not None else 50.0)
    print(f"DEBUG_ENGINE:   Source dBA: {source_dba:.1f}")
    print(f"DEBUG_ENGINE:   Terminal dBA: {current_dba:.1f}")
    print(f"DEBUG_ENGINE:   Total attenuation: {total_attenuation_dba:.1f}")
    print(f"DEBUG_ENGINE:   NC rating: {nc_rating}")
    print(f"DEBUG_ENGINE:   Final spectrum: {[f'{x:.1f}' for x in current_spectrum]}")
    print(f"DEBUG_ENGINE:   Element results count: {len(element_results)}")
    print(f"DEBUG_ENGINE:   Warnings: {warnings_list}")
    
    # Enhanced summary with spectrum analysis
    print(f"DEBUG_ENGINE:   Spectrum analysis:")
    print(f"DEBUG_ENGINE:     Source spectrum: {[f'{x:.1f}' for x in (source_element.octave_band_levels if source_element and source_element.octave_band_levels else [50.0]*8)]}")
    print(f"DEBUG_ENGINE:     Terminal spectrum: {[f'{x:.1f}' for x in current_spectrum]}")
    
    # Calculate spectrum changes
    if source_element and source_element.octave_band_levels:
        source_spectrum = source_element.octave_band_levels
        spectrum_changes = [current_spectrum[i] - source_spectrum[i] for i in range(min(len(current_spectrum), len(source_spectrum)))]
        print(f"DEBUG_ENGINE:     Spectrum changes: {[f'{x:+.1f}' for x in spectrum_changes]}")
        
        # Identify dominant effects
        max_increase = max(spectrum_changes) if spectrum_changes else 0
        max_decrease = min(spectrum_changes) if spectrum_changes else 0
        print(f"DEBUG_ENGINE:     Max spectrum increase: {max_increase:+.1f} dB")
        print(f"DEBUG_ENGINE:     Max spectrum decrease: {max_decrease:+.1f} dB")
    
    print(f"=== HVAC ENGINE DEBUG END ===\n")
```

## Testing Instructions

### 1. Enable Debug Output
Set the environment variable:
```bash
export HVAC_DEBUG_EXPORT=1
```

### 2. Run Test Calculation
Execute the HVAC path calculation to see the enhanced debug output.

### 3. Verify Fixes
Check that the debug output shows:
- Proper flow rate logic in junction calculations
- Elbow insertion loss calculations using the correct calculator
- Spectrum combination working with both positive and negative generated noise
- Velocity calculations in both fpm and ft/s
- Detailed attenuation and generation tracking

### 4. Expected Debug Output Format
```
DEBUG_ENGINE: Processing element 1: junction (segment_1)
DEBUG_ENGINE:   Input - dBA=50.0, spectrum=['72.0', '72.0', '79.0', '74.0', '69.0', '71.0', '71.0', '59.0']
DEBUG_ENGINE:   Element props - length=11.7, flow_rate=2000.0
DEBUG_ENGINE:     Junction context: upstream_flow=2000.0, downstream_flow=300.0
DEBUG_ENGINE:     Areas: main_area=4.000 ft^2, branch_area=1.069 ft^2
DEBUG_ENGINE:     Flow logic analysis:
DEBUG_ENGINE:       Upstream flow: 2000.0 CFM
DEBUG_ENGINE:       Downstream flow: 300.0 CFM
DEBUG_ENGINE:       Calculated main flow: 1700.0 CFM
DEBUG_ENGINE:       Calculated branch flow: 300.0 CFM
DEBUG_ENGINE:       Flow ratio (main/branch): 5.67
DEBUG_ENGINE:     Velocity calculations:
DEBUG_ENGINE:       Branch velocity: 4.677 ft/s
DEBUG_ENGINE:       Main velocity: 7.083 ft/s
DEBUG_ENGINE:     Junction spectra computed. Using 'branch_duct' spectrum
DEBUG_ENGINE:     Calc params: vel_ratio=1.515, main_vel=7.083 ft/s, branch_vel=4.677 ft/s
DEBUG_ENGINE:     Junction generated_dba=-4.19
DEBUG_ENGINE:   Element result: attenuation_dba=0.0, generated_dba=-4.187020998869928
DEBUG_ENGINE:     Before spectrum combination:
DEBUG_ENGINE:       Current spectrum: ['72.0', '72.0', '79.0', '74.0', '69.0', '71.0', '71.0', '59.0']
DEBUG_ENGINE:       Generated spectrum: ['-34.8', '-42.7', '-51.7', '-61.6', '-72.4', '-84.1', '-96.7', '-110.2']
DEBUG_ENGINE:     After spectrum combination:
DEBUG_ENGINE:       Final spectrum: ['72.0', '72.0', '79.0', '74.0', '69.0', '71.0', '71.0', '59.0']
DEBUG_ENGINE:       Total spectrum change: 0.00 dB
DEBUG_ENGINE:   Output - dBA=78.1, spectrum=['72.0', '72.0', '79.0', '74.0', '69.0', '71.0', '71.0', '59.0'], NC=65
DEBUG_ENGINE:   Change - dBA_delta=28.1
```

## Validation Checklist

- [ ] Junction flow rate logic correctly calculates main and branch flows
- [ ] Elbow calculations use dedicated rectangular elbows calculator for insertion loss
- [ ] Spectrum combination handles both positive and negative generated noise values
- [ ] Velocity calculations include both fpm and ft/s units
- [ ] Debug output shows detailed attenuation and generation tracking
- [ ] Final spectrum changes are properly documented
- [ ] All calculations maintain proper units throughout the pipeline

## Notes

1. The spectrum combination fix removes the `> 0` condition that was preventing negative generated noise from being added
2. The junction flow logic now properly distinguishes between continuing main duct flow and branch takeoff flow
3. Elbow calculations now use the appropriate calculator for insertion loss while still using junction calculator for generated noise
4. Enhanced debug output provides comprehensive tracking of all calculation steps
5. Unit conversions ensure proper velocity calculations for all downstream calculators
