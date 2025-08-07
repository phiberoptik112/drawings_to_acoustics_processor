# Flex Duct Acoustic Calculations

## Overview

This module implements acoustic calculations for nonmetallic insulated flexible ducts based on ASHRAE 2015 Applications Handbook Chapter 48: Noise and Vibration Control. The calculations focus on insertion loss values for specified duct diameters and lengths as provided in Table 25.

## Background

Nonmetallic insulated flexible ducts can significantly reduce airborne noise in HVAC systems. The insertion loss values depend on:
- Duct diameter (4-16 inches)
- Duct length (3-12 feet)
- Frequency bands (63, 125, 250, 500, 1000, 2000, 4000 Hz)

### ASHRAE Guidelines

- **Recommended duct lengths**: 3 to 6 feet
- **Installation**: Keep flexible ducts straight with long radius bends
- **Avoid**: Abrupt bends that may cause high airflow noise
- **Consider**: Breakout sound levels above sound-sensitive spaces

## Features

### Core Functionality

1. **Insertion Loss Calculation**
   - Direct lookup from Table 25 data
   - Interpolation for values not in the table
   - Support for all frequency bands (63-4000 Hz)

2. **Design Validation**
   - Parameter validation against ASHRAE recommendations
   - Warning system for non-optimal designs
   - Design recommendations and best practices

3. **Data Analysis**
   - Average insertion loss calculations
   - Frequency band analysis
   - Comparative analysis across different duct sizes

4. **Visualization**
   - Insertion loss spectrum plots
   - Heatmaps for specific frequencies
   - Comparative plots for different configurations

### Data Source

The calculations are based on **Table 25: Insertion Loss for Lined Flexible Duct** from ASHRAE 2015 Applications Handbook Chapter 48. The table provides insertion loss values in dB for:

- **Diameters**: 4, 5, 6, 7, 8, 9, 10, 12, 14, 16 inches
- **Lengths**: 3, 6, 9, 12 feet
- **Frequencies**: 63, 125, 250, 500, 1000, 2000, 4000 Hz

## Usage

### Basic Usage

```python
from flex_duct_calculations import FlexDuctCalculator

# Initialize calculator
calculator = FlexDuctCalculator()

# Get insertion loss for specific duct
diameter = 6  # inches
length = 9    # feet
insertion_loss = calculator.get_insertion_loss(diameter, length)

# Print results
for freq, loss in insertion_loss.items():
    print(f"{freq} Hz: {loss:.1f} dB")
```

### Advanced Usage

```python
# Get insertion loss for specific frequency
loss_500hz = calculator.get_insertion_loss(6, 9, frequency=500)

# Calculate average insertion loss
avg_loss = calculator.calculate_average_insertion_loss(6, 9)

# Validate design parameters
validation = calculator.validate_design_parameters(6, 9)
print(f"Valid design: {validation['is_valid']}")

# Generate comprehensive report
report = calculator.generate_report(6, 9)
print(report)
```

### Visualization

```python
# Create insertion loss spectrum plot
calculator.plot_insertion_loss_spectrum(6, 9)

# Create heatmap for specific frequency
calculator.plot_insertion_loss_heatmap(500)

# Create comparison DataFrame
diameters = [4, 6, 8, 10, 12, 14, 16]
lengths = [3, 6, 9, 12]
df = calculator.create_insertion_loss_dataframe(diameters, lengths)
```

## Class Methods

### FlexDuctCalculator

#### Core Methods

- `get_insertion_loss(diameter, length, frequency=None)`
  - Returns insertion loss in dB for specified parameters
  - If frequency is None, returns dict for all frequencies

- `calculate_average_insertion_loss(diameter, length, frequency_range=None)`
  - Calculates average insertion loss across frequency bands
  - Optional frequency range parameter

- `validate_design_parameters(diameter, length)`
  - Validates design against ASHRAE recommendations
  - Returns validation results with warnings and recommendations

#### Data Analysis Methods

- `create_insertion_loss_dataframe(diameters, lengths)`
  - Creates comprehensive DataFrame for analysis
  - Useful for comparative studies

- `get_recommended_length_range()`
  - Returns ASHRAE recommended length range (3-6 feet)

#### Visualization Methods

- `plot_insertion_loss_spectrum(diameter, length, save_path=None)`
  - Creates 4-panel plot with spectrum, bar chart, and comparisons

- `plot_insertion_loss_heatmap(frequency=500, save_path=None)`
  - Creates heatmap showing insertion loss across diameter/length combinations

#### Reporting Methods

- `generate_report(diameter, length)`
  - Generates comprehensive text report with analysis and recommendations

## Input Parameters

### Diameter
- **Range**: 4-16 inches
- **Typical values**: 4, 5, 6, 7, 8, 9, 10, 12, 14, 16 inches
- **Interpolation**: Available for intermediate values

### Length
- **Range**: 3-12 feet
- **Recommended**: 3-6 feet (ASHRAE guidelines)
- **Typical values**: 3, 6, 9, 12 feet
- **Interpolation**: Available for intermediate values

### Frequency
- **Available bands**: 63, 125, 250, 500, 1000, 2000, 4000 Hz
- **Note**: 63 Hz values are estimated from higher-frequency data

## Output Format

### Insertion Loss Values
- **Unit**: Decibels (dB)
- **Range**: Typically 1-42 dB depending on configuration
- **Format**: Dictionary with frequency keys or single float value

### Validation Results
```python
{
    'is_valid': bool,
    'warnings': List[str],
    'recommendations': List[str]
}
```

## Examples

### Example 1: Standard Configuration
```python
# 6-inch diameter, 9-foot length
calculator = FlexDuctCalculator()
loss = calculator.get_insertion_loss(6, 9)

# Results:
# 63 Hz: 6.0 dB
# 125 Hz: 9.0 dB
# 250 Hz: 13.0 dB
# 500 Hz: 25.0 dB
# 1000 Hz: 29.0 dB
# 2000 Hz: 30.0 dB
# 4000 Hz: 20.0 dB
```

### Example 2: Design Validation
```python
validation = calculator.validate_design_parameters(6, 9)
# Returns:
# {
#     'is_valid': True,
#     'warnings': [],
#     'recommendations': [
#         'Keep flexible ducts straight with long radius bends',
#         'Avoid abrupt bends to prevent high airflow noise',
#         'Consider breakout sound levels above sound-sensitive spaces'
#     ]
# }
```

### Example 3: Interpolation
```python
# 7.5-inch diameter, 7.5-foot length (not in table)
loss = calculator.get_insertion_loss(7.5, 7.5)
# Returns interpolated values based on surrounding data points
```

## Dependencies

- **pandas**: Data manipulation and analysis
- **numpy**: Numerical computations and interpolation
- **matplotlib**: Plotting and visualization
- **seaborn**: Enhanced plotting styles
- **scipy**: Interpolation functions

## Installation

1. Ensure all dependencies are installed:
```bash
pip install pandas numpy matplotlib seaborn scipy
```

2. Import the calculator:
```python
from flex_duct_calculations import FlexDuctCalculator
```

## Limitations and Notes

1. **Data Source**: Based on ASHRAE 2015 Applications Handbook Chapter 48
2. **Duct Type**: Nonmetallic insulated flexible ducts only
3. **Frequency**: 63 Hz values are estimated from higher-frequency data
4. **Interpolation**: Linear interpolation used for values not in table
5. **Validation**: Based on ASHRAE recommendations and typical ranges

## Best Practices

1. **Duct Length**: Use 3-6 feet for optimal performance
2. **Installation**: Keep ducts straight with long radius bends
3. **Avoid**: Abrupt bends and sharp turns
4. **Consider**: Breakout noise in sound-sensitive areas
5. **Validation**: Always validate design parameters before implementation

## References

- ASHRAE 2015 Applications Handbook, Chapter 48: Noise and Vibration Control
- Table 25: Insertion Loss for Lined Flexible Duct
- ARI Standard 885 (referenced in ASHRAE document)

## Support

For questions or issues with the calculations:
1. Verify input parameters are within valid ranges
2. Check ASHRAE documentation for specific application requirements
3. Consider consulting with acoustic engineering professionals for critical applications

---

**Note**: This calculator is based on published ASHRAE data and provides engineering estimates. For critical applications, verify results against actual testing or consult with qualified acoustic engineers. 