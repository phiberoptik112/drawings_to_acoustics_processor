# Unlined Rectangular Duct Acoustic Calculations

## Overview

This implementation provides calculations for sound attenuation in unlined rectangular sheet metal ducts based on **ASHRAE 1991 Algorithms for HVAC Acoustics**. The calculations follow the equations and methodology described in the reference document.

## Equations Implemented

### Equation 5.13
**For P/A ≥ 3 and frequencies ≤ 250 Hz:**
```
ATTN = 17.0 • (P/A)^-0.25 • FREQ^-0.85 • L
```

### Equation 5.14
**For P/A < 3 and frequencies ≤ 250 Hz:**
```
ATTN = 1.64 • (P/A)^0.73 • FREQ^-0.58 • L
```

### Equation 5.15
**For frequencies > 250 Hz:**
```
ATTN = 0.02 • (P/A)^0.8 • L
```

### External Lining Factor
If the duct is externally lined with fiberglass, multiply results from equations 5.13 or 5.14 by a factor of 2.

## Variables

- **ATTN**: Total attenuation (dB)
- **P**: Length of duct perimeter (ft)
- **A**: Duct cross-sectional area (ft²)
- **P/A**: Perimeter-to-area ratio (1/ft)
- **FREQ**: 1/1 octave band center frequency (Hz)
- **L**: Duct length (ft)

## Files

### `unlined_rectangular_duct_calculations.py`
Main Python script containing the `UnlinedRectangularDuctCalculator` class with all calculation methods.

### `unlined_rectangular_duct_calculations.ipynb`
Jupyter notebook providing an interactive interface for the calculations with examples and visualizations.

## Usage Examples

### Basic Calculation
```python
from unlined_rectangular_duct_calculations import UnlinedRectangularDuctCalculator

# Initialize calculator
calculator = UnlinedRectangularDuctCalculator()

# Calculate for 12" × 12" duct (1ft × 1ft)
width, height = 1.0, 1.0  # feet
spectrum = calculator.get_attenuation_spectrum(width, height)

# Print results
for freq_band, atten in spectrum.items():
    print(f"{freq_band}: {atten:.3f} dB")
```

### With External Lining
```python
# Calculate with external fiberglass lining
spectrum_lined = calculator.get_attenuation_spectrum(
    width, height, externally_lined=True
)
```

### Validation Against Reference Data
```python
# Validate against Table 5.2 reference data
validation = calculator.validate_against_reference(width, height)
print(f"P/A Ratio: {validation['p_a_ratio']:.2f} 1/ft")
```

### Generate Comprehensive Report
```python
# Generate detailed report
report = calculator.generate_report(width, height, length=5.0)
print(report)
```

## Frequency Bands

The calculator supports standard frequency bands:
- 63 Hz
- 125 Hz
- 250 Hz
- 500 Hz
- 1000 Hz
- 2000 Hz
- 4000 Hz
- 8000 Hz

## Reference Data

The implementation includes validation against Table 5.2 from the ASHRAE document, which provides reference attenuation values for various P/A ratios and frequency bands.

### Table 5.2 Reference Values (dB/ft)

| P/A (1/ft) | 63 Hz | 125 Hz | 250 Hz | >250 Hz |
|------------|-------|--------|--------|---------|
| 8.0        | 0.35  | 0.19   | 0.09   | 0.10    |
| 4.0        | 0.31  | 0.24   | 0.10   | 0.06    |
| 3.0        | 0.35  | 0.29   | 0.13   | 0.05    |
| 2.0        | 0.20  | 0.20   | 0.10   | 0.03    |
| 1.0        | 0.20  | 0.20   | 0.10   | 0.02    |
| 0.7        | 0.10  | 0.10   | 0.05   | 0.02    |

## Key Features

1. **Equation Selection**: Automatically selects the appropriate equation based on P/A ratio and frequency
2. **External Lining Support**: Handles 2x multiplier for fiberglass-lined ducts
3. **Validation**: Compares calculated values against reference data
4. **Visualization**: Creates plots showing attenuation characteristics
5. **Comprehensive Reporting**: Generates detailed reports with all relevant information
6. **Multiple Duct Sizes**: Supports batch calculations for multiple duct configurations

## Limitations and Assumptions

1. **SMACNA Standards**: Calculations apply only to rectangular sheet metal ducts with gauge thicknesses selected according to SMACNA HVAC duct construction standards
2. **Straight Ducts**: Results are for straight unlined rectangular sheet metal ducts
3. **Frequency Range**: Equations are validated for the specified frequency ranges
4. **P/A Ratio**: Calculations are most accurate for P/A ratios within the reference data range

## Dependencies

- pandas >= 2.0.0
- numpy >= 1.20.0
- matplotlib >= 3.5.0
- seaborn >= 0.11.0

## Installation

1. Ensure you have the required dependencies installed:
   ```bash
   pip install pandas numpy matplotlib seaborn
   ```

2. Place the Python script in your working directory or add it to your Python path.

3. For Jupyter notebook usage, ensure Jupyter is installed:
   ```bash
   pip install jupyter
   ```

## Testing

The script includes built-in validation against reference data. Run the main function to see example calculations:

```bash
python unlined_rectangular_duct_calculations.py
```

## References

- ASHRAE 1991 Algorithms for HVAC Acoustics
- Table 5.2: Sound Attenuation of Unlined Rectangular Sheet Metal Ducts
- Equations 5.13, 5.14, and 5.15

## Author

HVAC Acoustics Calculator - Based on ASHRAE 1991 standards 