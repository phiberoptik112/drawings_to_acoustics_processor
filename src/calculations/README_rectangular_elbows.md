# Rectangular Elbows Acoustic Calculations

## Overview

This implementation provides comprehensive calculations for rectangular elbow insertion loss based on ASHRAE 2015 Applications Handbook Chapter 48: Noise and Vibration Control. The calculations cover three main types of rectangular elbows:

1. **Unlined and Lined Square Elbows Without Turning Vanes** (Table 22)
2. **Unlined Radiused Elbows** (Table 23)
3. **Unlined and Lined Square Elbows with Turning Vanes** (Table 24)

## Key Concepts

### fw Product
The critical parameter for all calculations is the **fw product**:
- `f` = center frequency (kHz)
- `w` = width of the elbow (inches)
- `fw` = frequency (kHz) × width (inches)

### Insertion Loss
Insertion loss is the reduction in sound power level that occurs when an elbow is inserted into a duct system. It is measured in decibels (dB).

## Files

- `rectangular_elbows_calculations.py` - Main Python script with the calculator class
- `rectangular_elbows_calculations.ipynb` - Jupyter notebook for interactive analysis and visualization

## Usage

### Basic Usage

```python
from rectangular_elbows_calculations import RectangularElbowsCalculator

# Initialize calculator
calculator = RectangularElbowsCalculator()

# Calculate insertion loss for a specific case
frequency = 1000  # Hz
width = 12.0      # inches
elbow_type = 'square_no_vanes'
lined = True

insertion_loss = calculator.calculate_elbow_insertion_loss(
    frequency, width, elbow_type, lined
)
print(f"Insertion Loss: {insertion_loss:.1f} dB")
```

### Available Elbow Types

1. `'square_no_vanes'` - Square elbows without turning vanes
2. `'radiused'` - Radiused elbows
3. `'square_with_vanes'` - Square elbows with turning vanes

### Lining Options

- `lined = False` - Unlined elbows
- `lined = True` - Lined elbows (only applies to square elbows)

## Data Tables

### Table 22: Unlined and Lined Square Elbows Without Turning Vanes

| fw Range | Unlined (dB) | Lined (dB) |
|----------|--------------|------------|
| < 1.9    | 0            | 0          |
| 1.9-3.8  | 1            | 1          |
| 3.8-7.5  | 5            | 6          |
| 7.5-15   | 8            | 11         |
| 15-30    | 4            | 10         |
| > 30     | 3            | 10         |

### Table 23: Unlined Radiused Elbows

| fw Range | Insertion Loss (dB) |
|----------|-------------------|
| < 1.9    | 0                 |
| 1.9-3.8  | 1                 |
| 3.8-7.5  | 6                 |
| > 7.5    | 11                |

### Table 24: Unlined and Lined Square Elbows with Turning Vanes

| fw Range | Unlined (dB) | Lined (dB) |
|----------|--------------|------------|
| < 1.9    | 0            | 0          |
| 1.9-3.8  | 1            | 1          |
| 3.8-7.5  | 4            | 4          |
| 7.5-15   | 6            | 7          |
| > 15     | 4            | 10         |

## Features

### Core Functions

1. **`calculate_fw_product(frequency, width)`** - Calculate the fw product
2. **`calculate_elbow_insertion_loss(frequency, width, elbow_type, lined)`** - Main calculation function
3. **`calculate_spectrum_insertion_loss(width, elbow_type, lined)`** - Calculate across all octave bands
4. **`compare_elbow_types(width, lined)`** - Compare all elbow types for a given width

### Analysis Functions

1. **`create_insertion_loss_dataframe(widths, elbow_type, lined)`** - Create DataFrame for multiple widths
2. **`plot_insertion_loss_comparison(width)`** - Visualize comparison of all elbow types
3. **`plot_width_comparison(widths, elbow_type, lined)`** - Visualize effect of width
4. **`generate_report(width, elbow_type, lined)`** - Generate comprehensive report

### Validation

- **`validate_inputs(frequency, width)`** - Validate input parameters
- Input validation for frequency (positive, reasonable upper limit)
- Input validation for width (positive, reasonable upper limit)

## Octave Bands

The calculator uses standard octave band center frequencies:
- 63 Hz, 125 Hz, 250 Hz, 500 Hz, 1000 Hz, 2000 Hz, 4000 Hz, 8000 Hz

## Example Results

For a 12-inch wide elbow at 1000 Hz:

| Elbow Type | Unlined (dB) | Lined (dB) |
|------------|--------------|------------|
| Square No Vanes | 8.0 | 11.0 |
| Radiused | 11.0 | N/A |
| Square With Vanes | 6.0 | 7.0 |

## Important Notes

1. **Lining Requirements**: For lined square elbows, duct lining must extend at least 2 duct widths beyond the elbow
2. **Frequency Range**: Calculations are valid for the standard octave bands (63 Hz - 8000 Hz)
3. **Width Limitations**: The tables are based on typical HVAC duct sizes
4. **Accuracy**: Results are based on ASHRAE empirical data and should be used as guidelines

## Dependencies

- pandas >= 2.0.0
- numpy >= 1.20.0
- matplotlib >= 3.5.0
- seaborn >= 0.11.0

## Running the Script

```bash
# Activate virtual environment
venv\Scripts\activate

# Run the main script
python calc_scripts_fromMD/rectangular_elbows_calculations.py

# Or run the Jupyter notebook
jupyter notebook calc_scripts_fromMD/rectangular_elbows_calculations.ipynb
```

## Output

The script provides:
1. **Console output** with calculation results
2. **DataFrame comparisons** for analysis
3. **Visualization plots** showing insertion loss vs frequency
4. **Comprehensive reports** with detailed breakdowns

## Applications

This calculator is useful for:
- HVAC system design
- Acoustic analysis and modeling
- Noise control engineering
- Building acoustics calculations
- Duct system optimization

## References

- ASHRAE 2015 Applications Handbook Chapter 48: Noise and Vibration Control
- Beranek, L.L. 1960. Noise reduction. McGraw-Hill, New York
- Ver, I.L. 1983b. Prediction of sound transmission through duct walls: Breakout and pickup. ASHRAE Transactions 89(2A):471-501 