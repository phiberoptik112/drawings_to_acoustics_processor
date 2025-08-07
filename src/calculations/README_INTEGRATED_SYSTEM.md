# HVAC Noise Calculation System - Integrated Backend

This document describes the integrated HVAC noise calculation system that provides a unified backend for analyzing HVAC acoustic paths from source to receiver.

## Overview

The system integrates all specialized HVAC acoustic calculators into a unified engine that can process complete HVAC paths and provide comprehensive noise analysis results. It's designed to work seamlessly with front-end drawing applications that generate HVAC path data.

## Architecture

### Core Components

1. **HVACNoiseEngine** (`hvac_noise_engine.py`) - The main calculation engine
2. **HVACPathCalculator** (`hvac_path_calculator.py`) - Path management and analysis
3. **NoiseCalculator** (`noise_calculator.py`) - Legacy compatibility layer

### Integrated Calculators

- **Circular Duct Calculator** - Unlined and lined circular duct attenuation
- **Rectangular Duct Calculator** - Unlined and lined rectangular duct attenuation
- **Flexible Duct Calculator** - Flexible duct insertion loss
- **Elbow Turning Vane Calculator** - Generated noise from elbows with turning vanes
- **Junction/Elbow Calculator** - Generated noise from junctions and elbows
- **Receiver Room Calculator** - Room sound correction factors

## Data Structures

### PathElement

The fundamental data structure for representing HVAC path elements:

```python
@dataclass
class PathElement:
    element_type: str  # 'duct', 'elbow', 'junction', 'flex_duct', 'terminal', 'source'
    element_id: str
    length: float = 0.0  # feet
    width: float = 0.0   # inches
    height: float = 0.0  # inches
    diameter: float = 0.0  # inches
    duct_shape: str = 'rectangular'  # 'rectangular', 'circular'
    duct_type: str = 'sheet_metal'  # 'sheet_metal', 'fiberglass', 'flexible'
    lining_thickness: float = 0.0  # inches
    flow_rate: float = 0.0  # cfm
    flow_velocity: float = 0.0  # fpm
    pressure_drop: float = 0.0  # in. w.g.
    vane_chord_length: float = 0.0  # inches
    num_vanes: int = 0
    room_volume: float = 0.0  # cubic feet
    room_absorption: float = 0.0  # sabins
    source_noise_level: float = 0.0  # dB(A)
    octave_band_levels: Optional[List[float]] = None  # 8-band spectrum
```

### PathResult

The result structure containing complete analysis results:

```python
@dataclass
class PathResult:
    path_id: str
    source_noise_dba: float
    terminal_noise_dba: float
    total_attenuation_dba: float
    nc_rating: int
    octave_band_spectrum: List[float]  # 8-band spectrum at terminal
    element_results: List[Dict]
    warnings: List[str]
    calculation_valid: bool
    error_message: Optional[str] = None
```

## Usage Examples

### Basic Path Calculation

```python
from hvac_noise_engine import HVACNoiseEngine, PathElement

# Create path elements
path_elements = [
    # Source: Air handler
    PathElement(
        element_type='source',
        element_id='air_handler_1',
        source_noise_level=75.0
    ),
    
    # Duct segment
    PathElement(
        element_type='duct',
        element_id='main_duct_1',
        length=50.0,
        width=24.0,
        height=12.0,
        duct_shape='rectangular',
        duct_type='sheet_metal',
        lining_thickness=1.0
    ),
    
    # Terminal
    PathElement(
        element_type='terminal',
        element_id='diffuser_1',
        source_noise_level=25.0
    )
]

# Calculate
engine = HVACNoiseEngine()
result = engine.calculate_path_noise(path_elements, "path_1")

print(f"Terminal Noise: {result.terminal_noise_dba:.1f} dB(A)")
print(f"NC Rating: {result.nc_rating}")
```

### Front-end Integration

```python
from hvac_path_calculator import HVACPathCalculator

# Front-end drawing data
drawing_data = {
    'components': [
        {
            'id': 1,
            'component_type': 'air_handler',
            'name': 'AHU-1',
            'x': 100, 'y': 100
        },
        {
            'id': 2,
            'component_type': 'diffuser',
            'name': 'DIFF-1',
            'x': 200, 'y': 200
        }
    ],
    'segments': [
        {
            'id': 1,
            'from_component': {'id': 1, 'x': 100, 'y': 100},
            'to_component': {'id': 2, 'x': 200, 'y': 200},
            'length_real': 60.0,
            'duct_width': 18.0,
            'duct_height': 10.0,
            'duct_shape': 'rectangular',
            'duct_type': 'sheet_metal',
            'lining_thickness': 1.0,
            'flow_rate': 1500.0
        }
    ]
}

# Create and analyze path
path_calc = HVACPathCalculator()
path_data = path_calc.create_hvac_path_from_drawing("project_1", drawing_data)

if path_data:
    calc_result = path_data['calculation_result']
    print(f"Terminal Noise: {calc_result.terminal_noise_dba:.1f} dB(A)")
    print(f"NC Rating: {calc_result.nc_rating}")
```

### Legacy Compatibility

```python
from noise_calculator import NoiseCalculator

# Legacy format data
legacy_path_data = {
    'source_component': {
        'component_type': 'fan',
        'noise_level': 78.0
    },
    'segments': [
        {
            'length': 25.0,
            'duct_width': 16.0,
            'duct_height': 8.0,
            'duct_shape': 'rectangular',
            'duct_type': 'sheet_metal',
            'lining_thickness': 1.0
        }
    ],
    'terminal_component': {
        'component_type': 'diffuser',
        'noise_level': 22.0
    }
}

# Use legacy calculator
noise_calc = NoiseCalculator()
result = noise_calc.calculate_hvac_path_noise(legacy_path_data)

print(f"Terminal Noise: {result['terminal_noise']:.1f} dB(A)")
print(f"NC Rating: {result['nc_rating']}")
```

## Element Types and Properties

### Source Elements
- **element_type**: 'source'
- **source_noise_level**: A-weighted noise level in dB(A)
- **octave_band_levels**: Optional 8-band spectrum

### Duct Elements
- **element_type**: 'duct'
- **length**: Duct length in feet
- **width/height**: Rectangular duct dimensions in inches
- **diameter**: Circular duct diameter in inches
- **duct_shape**: 'rectangular' or 'circular'
- **duct_type**: 'sheet_metal', 'fiberglass', or 'flexible'
- **lining_thickness**: Lining thickness in inches

### Elbow Elements
- **element_type**: 'elbow'
- **width/height**: Duct dimensions
- **flow_rate**: Air flow rate in cfm
- **flow_velocity**: Air velocity in fpm
- **pressure_drop**: Pressure drop across elbow in in. w.g.
- **vane_chord_length**: Turning vane chord length in inches
- **num_vanes**: Number of turning vanes

### Junction Elements
- **element_type**: 'junction'
- **width/height**: Duct dimensions
- **flow_rate**: Air flow rate in cfm
- **flow_velocity**: Air velocity in fpm

### Flexible Duct Elements
- **element_type**: 'flex_duct'
- **diameter**: Duct diameter in inches
- **length**: Duct length in feet

### Terminal Elements
- **element_type**: 'terminal'
- **source_noise_level**: Terminal unit noise level
- **room_volume**: Room volume in cubic feet
- **room_absorption**: Room absorption in sabins

## Frequency Bands

The system uses standard 1/1 octave frequency bands:
- 63 Hz
- 125 Hz
- 250 Hz
- 500 Hz
- 1000 Hz
- 2000 Hz
- 4000 Hz
- 8000 Hz

## NC Rating Calculation

The system calculates NC ratings by comparing the octave band spectrum to standard NC curves and finding the highest NC rating that the spectrum doesn't exceed.

## Validation

The system includes comprehensive validation:

```python
# Validate path elements
is_valid, warnings = engine.validate_path_elements(path_elements)

if not is_valid:
    print("Validation warnings:")
    for warning in warnings:
        print(f"  - {warning}")
```

## Error Handling

All calculations include robust error handling:

```python
result = engine.calculate_path_noise(path_elements, "path_1")

if not result.calculation_valid:
    print(f"Calculation failed: {result.error_message}")
else:
    print(f"Calculation successful: {result.terminal_noise_dba:.1f} dB(A)")
```

## Testing

Run the test script to verify the system:

```bash
python test_integrated_system.py
```

This will test:
- Simple HVAC paths
- Flexible duct paths
- Circular duct paths
- Front-end integration
- Legacy compatibility

## Front-end Integration Guide

### Data Flow

1. **Front-end Drawing**: User draws HVAC components and connections
2. **Path Generation**: Front-end generates path data structure
3. **Backend Calculation**: Send path data to HVAC noise engine
4. **Results**: Receive comprehensive noise analysis results
5. **Display**: Show results in front-end interface

### Required Front-end Data

The front-end should provide:

```javascript
{
  components: [
    {
      id: 1,
      component_type: 'air_handler',
      name: 'AHU-1',
      x: 100,
      y: 100,
      noise_level: 75.0  // Optional
    }
  ],
  segments: [
    {
      id: 1,
      from_component: {id: 1, x: 100, y: 100},
      to_component: {id: 2, x: 200, y: 200},
      length_real: 60.0,
      duct_width: 18.0,
      duct_height: 10.0,
      duct_shape: 'rectangular',
      duct_type: 'sheet_metal',
      lining_thickness: 1.0,
      flow_rate: 1500.0,
      flow_velocity: 1000.0
    }
  ]
}
```

### API Endpoints

The front-end can call these backend functions:

1. **Create Path**: `create_hvac_path_from_drawing(project_id, drawing_data)`
2. **Calculate Path**: `calculate_path_noise(path_id, path_elements)`
3. **Validate Path**: `validate_path_elements(path_elements)`
4. **Get Summary**: `get_path_summary(project_paths)`
5. **Export Results**: `export_path_results(project_paths)`

## Performance Considerations

- The system is optimized for typical HVAC paths (1-20 elements)
- Calculations are performed in memory without database dependencies
- Octave band calculations provide detailed frequency analysis
- Results include both A-weighted and octave band data

## Dependencies

- Python 3.7+
- NumPy
- Pandas
- Matplotlib (for visualization)
- SciPy (for interpolation)

## Installation

1. Ensure all calculator modules are in the same directory
2. Install required dependencies: `pip install numpy pandas matplotlib scipy`
3. Import the integrated system modules
4. Run tests to verify installation

## Support

For issues or questions:
1. Check the test script for usage examples
2. Verify input data format matches requirements
3. Review validation warnings for data issues
4. Ensure all required calculator modules are available 