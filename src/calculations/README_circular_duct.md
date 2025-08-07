# Circular Duct Acoustic Calculations

## Overview

This module implements acoustic calculations for circular ducts based on the ASHRAE 1991 Algorithms for HVAC Acoustics. It provides comprehensive functionality for both unlined and acoustically lined circular sheet metal ducts.

## Features

### Unlined Circular Ducts
- **Sound Attenuation Calculation**: Uses Table 5.5 data from Woods Design for Sound manual
- **Frequency Range**: 63 Hz to 4,000 Hz (1/1 octave bands)
- **Diameter Ranges**: D ≤ 7", 7 < D ≤ 15", 15 < D ≤ 30", 30 < D ≤ 60"
- **Attenuation Values**: 0.01 to 0.10 dB/ft depending on diameter and frequency

### Acoustically Lined Circular Ducts
- **Insertion Loss Calculation**: Uses Equation 5.18 with coefficients from Table 5.6
- **Frequency Range**: 63 Hz to 8,000 Hz (1/1 octave bands)
- **Diameter Range**: 6 to 60 inches
- **Lining Thickness**: 1 to 3 inches
- **Maximum Insertion Loss**: Limited to 40 dB due to structure-borne sound

## Key Equations

### Equation 5.18: Insertion Loss for Lined Circular Ducts
```
IL = (A + B•t + C•t² + D•d + E•d² + F•d³) • L
```

Where:
- `IL` = Insertion loss (dB)
- `t` = Lining thickness (inches)
- `d` = Inside duct diameter (inches)
- `L` = Duct length (feet)
- `A, B, C, D, E, F` = Frequency-dependent coefficients

## Usage Examples

### Basic Usage

```python
from circular_duct_calculations import CircularDuctCalculator

# Initialize calculator
calculator = CircularDuctCalculator()

# Calculate unlined duct attenuation
attenuation = calculator.calculate_unlined_attenuation(
    diameter=12.0,    # inches
    frequency=1000,   # Hz
    length=10.0       # feet
)

# Calculate lined duct insertion loss
insertion_loss = calculator.calculate_lined_insertion_loss(
    diameter=12.0,           # inches
    lining_thickness=1.5,    # inches
    frequency=1000,          # Hz
    length=10.0              # feet
)
```

### Spectrum Analysis

```python
# Get full frequency spectrum for unlined duct
unlined_spectrum = calculator.get_unlined_attenuation_spectrum(
    diameter=12.0,
    length=10.0
)

# Get full frequency spectrum for lined duct
lined_spectrum = calculator.get_lined_insertion_loss_spectrum(
    diameter=12.0,
    lining_thickness=1.5,
    length=10.0
)
```

### Visualization

```python
# Create comparison plots
calculator.plot_attenuation_comparison(
    diameter=12.0,
    lining_thickness=1.5,
    length=10.0
)

# Compare different diameters
diameters = [6, 12, 24, 48]
calculator.plot_diameter_comparison(
    diameters=diameters,
    lining_thickness=1.5,
    length=10.0
)
```

### Data Analysis

```python
# Create comparison DataFrame
df = calculator.create_comparison_dataframe(
    diameters=[6, 12, 24, 48],
    lining_thicknesses=[1.0, 2.0, 3.0],
    length=10.0
)

# Generate comprehensive report
report = calculator.generate_report(
    diameter=12.0,
    lining_thickness=1.5,
    length=10.0
)
print(report)
```

## Input Parameters

### Unlined Duct Calculations
- **diameter**: Duct diameter in inches (≤ 60")
- **frequency**: Frequency in Hz (63, 125, 250, 500, 1000, 2000, 4000)
- **length**: Duct length in feet (> 0)

### Lined Duct Calculations
- **diameter**: Inside duct diameter in inches (6-60")
- **lining_thickness**: Lining thickness in inches (1-3")
- **frequency**: Frequency in Hz (63, 125, 250, 500, 1000, 2000, 4000, 8000)
- **length**: Duct length in feet (> 0)

## Output Data

### Unlined Duct Attenuation
- **Unit**: dB
- **Range**: 0.01 to 0.10 dB/ft (varies by diameter and frequency)
- **Frequency Bands**: 63, 125, 250, 500, 1000, 2000, 4000 Hz

### Lined Duct Insertion Loss
- **Unit**: dB
- **Range**: 0 to 40 dB (maximum limit applied)
- **Frequency Bands**: 63, 125, 250, 500, 1000, 2000, 4000, 8000 Hz

## Validation and Limits

### ASHRAE Validation
- **Unlined Ducts**: Data validated against Table 5.5 (Woods Design for Sound)
- **Lined Ducts**: Calculations based on Equation 5.18 with Table 5.6 coefficients
- **Maximum Insertion Loss**: Limited to 40 dB due to structure-borne sound transmission

### Input Validation
- **Diameter Range**: 6-60 inches for lined ducts, ≤ 60 inches for unlined ducts
- **Lining Thickness**: 1-3 inches for lined ducts
- **Length**: Must be positive
- **Frequency**: Automatically mapped to nearest standard frequency band

## Reference Data

### Table 5.5: Sound Attenuation in Straight Circular Ducts
| Diameter Range | 63 Hz | 125 Hz | 250 Hz | 500 Hz | 1000 Hz | 2000 Hz | 4000 Hz |
|----------------|-------|--------|--------|--------|---------|---------|---------|
| D ≤ 7"         | 0.03  | 0.03   | 0.05   | 0.05   | 0.10    | 0.10    | 0.10    |
| 7 < D ≤ 15"    | 0.03  | 0.03   | 0.03   | 0.05   | 0.07    | 0.07    | 0.07    |
| 15 < D ≤ 30"   | 0.02  | 0.02   | 0.02   | 0.03   | 0.05    | 0.05    | 0.05    |
| 30 < D ≤ 60"   | 0.01  | 0.01   | 0.01   | 0.02   | 0.02    | 0.02    | 0.02    |

### Table 5.6: Constants for Equation 5.18
| Frequency (Hz) | A      | B      | C        | D        | E        | F        |
|----------------|--------|--------|----------|----------|----------|----------|
| 63             | 0.2825 | 0.3447 | -5.251E-02| -0.03837 | 9.1315E-04| -8.294E-06|
| 125            | 0.5237 | 0.2234 | -4.936E-03| -0.02724 | 3.377E-04| -2.49E-04|
| 250            | 0.3652 | 0.79   | -0.1157  | -1.834E-02| -1.211E-04| 2.681E-04|
| 500            | 0.1333 | 1.845  | -0.3735  | -1.293E-02| 8.624E-05| -4.986E-06|
| 1000           | 1.933  | 0      | 0        | 6.135E-02| -3.891E-03| 3.934E-05|
| 2000           | 2.73   | 0      | 0        | -7.341E-02| 4.428E-04| 1.006E-06|
| 4000           | 2.8    | 0      | 0        | -0.1467  | 3.404E-03| -2.851E-05|
| 8000           | 1.545  | 0      | 0        | -5.452E-02| 1.290E-03| -1.318E-05|

## Technical Notes

### Frequency Dependencies
- **63-500 Hz**: Insertion loss depends on both duct diameter and lining thickness
- **1000+ Hz**: Insertion loss depends on duct diameter only (B=C=0)

### Regression Equation Limitations
- Equation 5.18 is a regression equation based on experimental data
- Should not be extrapolated beyond the data limits
- Valid for spiral, dual-wall circular ducts with 0.75 lb/ft³ fiberglass lining
- Perforated galvanized steel liner with 25% open area

### Comparison with Rectangular Ducts
- Circular ducts are more rigid than rectangular ducts
- Provide about one-tenth the sound attenuation at low frequencies
- Natural attenuation: ~0.03 dB/ft below 1000 Hz, rising to ~0.1 dB/ft at high frequencies

## Dependencies

- **pandas**: Data manipulation and analysis
- **numpy**: Numerical computations
- **matplotlib**: Plotting and visualization
- **seaborn**: Enhanced plotting styles
- **scipy**: Scientific computing (if needed for advanced analysis)

## Files

- `circular_duct_calculations.py`: Main implementation
- `circular_duct_calculations.ipynb`: Jupyter notebook interface
- `README_circular_duct.md`: This documentation file

## References

1. ASHRAE 1991 Algorithms for HVAC Acoustics
2. Woods Design for Sound manual
3. ASHRAE 1987 HVAC Systems and Applications Handbook
4. Bodley (8) - Spiral dual-wall circular duct data
5. Reynolds and Bledsoe - Multi-variable regression analysis

## Author

HVAC Acoustics Calculator - 2024 