# Receiver Room Sound Correction Calculations (Shultz Method)

## Overview

This module implements the Shultz method for receiver room sound correction calculations as described in the ASHRAE 2015 Applications Handbook Chapter 48: Noise and Vibration Control. The calculations account for room acoustics and provide sound pressure levels at specified locations within a room.

## Equations Implemented

### 1. Single Point Source in Small Rooms (< 15,000 ft³)

**Equation (26)**: Lp = Lw – 10log r – 5log V – 3log f + 25

**Equation (27)**: Lp = Lw + A – B

Where:
- Lp = sound pressure level at specified distance from sound source, dB (re 20 µPa)
- Lw = sound power level of sound source, dB (re 10⁻¹² W)
- r = distance from source to receiver, ft
- V = volume of room, ft³
- f = frequency, Hz
- A, B = correction factors from Tables 35 and 36

### 2. Single Point Source in Large Rooms (15,000-150,000 ft³)

**Equation (28)**: Lp = Lw – C – 5

Where:
- C = correction factor from Table 37 based on distance and frequency

### 3. Distributed Ceiling Array

**Equation (29)**: Lp(5) = LW(s) – D

Where:
- Lp(5) = sound pressure level at 5 ft above floor, dB (re 20 µPa)
- LW(s) = sound power level of single diffuser in array, dB (re 10⁻¹² W)
- D = correction factor from Table 38 based on ceiling height and floor area per diffuser

## Usage

### Basic Usage

```python
from receiver_room_sound_correction_calculations import ReceiverRoomSoundCorrection

# Initialize calculator
calculator = ReceiverRoomSoundCorrection()

# Example parameters
lw_spectrum = [85, 82, 78, 75, 72, 68, 65]  # Sound power spectrum [63, 125, 250, 500, 1000, 2000, 4000] Hz
distance = 10  # ft
room_volume = 8000  # ft³
ceiling_height = 10  # ft
floor_area_per_diffuser = 150  # ft²

# Calculate results
df = calculator.create_comparison_dataframe(lw_spectrum, distance, room_volume, 
                                          ceiling_height, floor_area_per_diffuser)
print(df)

# Generate comprehensive report
report = calculator.generate_report(lw_spectrum, distance, room_volume, 
                                  ceiling_height, floor_area_per_diffuser)
print(report)
```

### Individual Calculations

```python
# Single point source in small room
lp_eq26 = calculator.calculate_single_source_small_room(85, 10, 8000, 500, 'equation_26')
lp_eq27 = calculator.calculate_single_source_small_room(85, 10, 8000, 500, 'equation_27')

# Single point source in large room
lp_eq28 = calculator.calculate_single_source_large_room(85, 10, 500)

# Distributed ceiling array
lp_distributed = calculator.calculate_distributed_ceiling_array(70, 12, 200, 500)
```

### Octave Band Spectrum Calculations

```python
# Calculate full octave band spectrum
spectrum_results = calculator.calculate_octave_band_spectrum(
    lw_spectrum, distance, room_volume, method='auto')

# Calculate distributed array spectrum
distributed_spectrum = calculator.calculate_distributed_array_spectrum(
    lw_single_spectrum, ceiling_height, floor_area_per_diffuser)
```

## Input Parameters

### Required Parameters

- **lw_spectrum**: List of 7 sound power levels for octave bands [63, 125, 250, 500, 1000, 2000, 4000] Hz
- **distance**: Distance from sound source to receiver, ft
- **room_volume**: Volume of room, ft³

### Optional Parameters

- **ceiling_height**: Ceiling height for distributed array calculations, ft (default: 10)
- **floor_area_per_diffuser**: Floor area served by each diffuser, ft² (default: 150)

## Output

### DataFrame Output

The `create_comparison_dataframe()` method returns a pandas DataFrame with columns:
- Frequency_Hz: Octave band frequencies
- Sound_Power_Level_dB: Input sound power levels
- Equation_26_dB: Results using Equation 26 (small rooms only)
- Equation_27_dB: Results using Equation 27 (small rooms only)
- Equation_28_dB: Results using Equation 28 (large rooms only)
- Distributed_Array_dB: Results using Equation 29

### Report Output

The `generate_report()` method returns a formatted text report including:
- Input parameters summary
- Detailed results table
- Method selection guidelines
- Approximate A-weighted sound pressure level

## Method Selection

The calculator automatically selects the appropriate method based on room volume:

- **Rooms < 15,000 ft³**: Equations 26 and 27 are available
- **Rooms 15,000-150,000 ft³**: Equation 28 is used
- **Distributed arrays**: Equation 29 is always available

## Tables Referenced

### Table 35: Values for A in Equation (27)
Room volume vs. frequency correction factors for small rooms.

### Table 36: Values for B in Equation (27)
Distance correction factors for small rooms.

### Table 37: Values for C in Equation (28)
Distance and frequency correction factors for large rooms.

### Table 38: Values for D in Equation (29)
Ceiling height and floor area correction factors for distributed arrays.

## Interpolation

The calculator includes interpolation capabilities for:
- Room volumes between table values (Table 35)
- Distances between table values (Tables 36 and 37)
- Ceiling heights and floor areas (Table 38)

## Visualization

```python
# Create comparison plot
calculator.plot_spectrum_comparison(lw_spectrum, distance, room_volume, 
                                  ceiling_height, floor_area_per_diffuser,
                                  save_path='comparison_plot.png')
```

## Examples

### Example 1: Small Office Room
```python
# Small office: 8,000 ft³, 10 ft distance
lw_spectrum = [85, 82, 78, 75, 72, 68, 65]
results = calculator.calculate_octave_band_spectrum(lw_spectrum, 10, 8000)
```

### Example 2: Large Conference Room
```python
# Large room: 50,000 ft³, 15 ft distance
results = calculator.calculate_octave_band_spectrum(lw_spectrum, 15, 50000)
```

### Example 3: Distributed Ceiling Array
```python
# Office with ceiling diffusers: 12 ft ceiling, 200 ft² per diffuser
lw_single = [70, 68, 65, 62, 58, 55, 52]
results = calculator.calculate_distributed_array_spectrum(lw_single, 12, 200)
```

## Dependencies

- pandas >= 2.0.0
- numpy >= 1.20.0
- matplotlib >= 3.5.0
- seaborn >= 0.11.0
- scipy >= 1.7.0

## Files

- `receiver_room_sound_correction_calculations.py`: Main calculation script
- `receiver_room_sound_correction_calculations.ipynb`: Jupyter notebook with examples
- `README_receiver_room_sound_correction.md`: This documentation file

## References

1. ASHRAE 2015 Applications Handbook, Chapter 48: Noise and Vibration Control
2. Schultz, T. J. 1985. "Relationship between sound power level and sound pressure level in domestic and office spaces." Report VDI 2716, VDI-Verlag, Düsseldorf, Germany.

## Notes

- All calculations are based on normally furnished rooms with acoustic characteristics ranging from average to medium dead
- Results are typically accurate within 2 to 5 dB for room volumes up to 150,000 ft³
- The distributed array method assumes nominally equal sound power levels from all diffusers
- A-weighted levels are approximate and use standard A-weighting factors 