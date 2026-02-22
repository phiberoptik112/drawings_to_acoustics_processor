# Acoustic Analysis API

A pure Python API for acoustic calculations designed for LLM agentic workflows. This API provides stateless, strictly validated endpoints for RT60 reverberation time analysis and HVAC mechanical background noise calculations.

## Table of Contents

- [Quick Start](#quick-start)
- [API Architecture](#api-architecture)
- [Services](#services)
  - [RT60 Calculation Service](#rt60-calculation-service)
  - [HVAC Noise Service](#hvac-noise-service)
  - [Materials Service](#materials-service)
  - [Simulation Service](#simulation-service)
- [Schema Discovery](#schema-discovery)
- [Strict Validation](#strict-validation)
- [Error Handling](#error-handling)
- [Example Workflows](#example-workflows)
- [Expansion Ideas](#expansion-ideas)

---

## Quick Start

```python
from src.api import AcousticAnalysisAPI
from src.api.schemas.rt60_schemas import RT60CalculationRequest, SurfaceDefinition

# Initialize the API
api = AcousticAnalysisAPI()

# Discover available endpoints
schema = api.get_api_schema()
examples = api.get_quick_start_examples()

# Calculate RT60 for a conference room
request = RT60CalculationRequest(
    volume_cubic_feet=12000,
    floor_area_sq_ft=1200,
    wall_area_sq_ft=1600,
    ceiling_area_sq_ft=1200,
    surfaces=[
        SurfaceDefinition(surface_type="ceiling", material_key="act_nrc_0.70", area_sq_ft=1200),
        SurfaceDefinition(surface_type="wall", material_key="concrete_block_painted", area_sq_ft=1600),
        SurfaceDefinition(surface_type="floor", material_key="carpet_-_heavy_on_concrete", area_sq_ft=1200),
    ],
    calculation_method="sabine"
)

result = api.rt60.calculate_rt60(request)
print(f"Average RT60: {result.average_rt60}s")
print(f"RT60 by frequency: {result.rt60_by_frequency}")
```

---

## API Architecture

### Design Principles

1. **Stateless**: Each API call receives all required data - no hidden state or database dependencies
2. **Strict Validation**: Missing physics-relevant fields are rejected with detailed error messages
3. **Composable**: Outputs are designed to feed into subsequent operations
4. **LLM-Friendly**: Schema discovery endpoints help agents understand available operations

### Package Structure

```
src/api/
├── __init__.py              # Main entry point (exports AcousticAnalysisAPI)
├── facade.py                # Unified API facade
├── schemas/
│   ├── common.py            # Shared types, constants, error classes
│   ├── rt60_schemas.py      # RT60 request/response dataclasses
│   ├── hvac_schemas.py      # HVAC path noise schemas
│   ├── material_schemas.py  # Materials database schemas
│   └── simulation_schemas.py # What-if scenario schemas
├── validators/
│   ├── base.py              # Core validation utilities
│   ├── rt60_validators.py   # RT60-specific validation
│   └── hvac_validators.py   # HVAC-specific validation
└── endpoints/
    ├── rt60_api.py          # RT60 calculation service
    ├── hvac_api.py          # HVAC noise service
    ├── materials_api.py     # Materials database service
    └── simulation_api.py    # What-if simulation service
```

---

## Services

### RT60 Calculation Service

Calculates reverberation time (RT60) using Sabine or Eyring formulas.

#### `api.rt60.calculate_rt60(request)`

Calculate RT60 for a space with defined surfaces and materials.

**Request:**
```python
from src.api.schemas.rt60_schemas import RT60CalculationRequest, SurfaceDefinition

request = RT60CalculationRequest(
    volume_cubic_feet=12000,          # Required: Room volume
    floor_area_sq_ft=1200,            # Required: Floor area
    wall_area_sq_ft=1600,             # Required: Total wall area
    ceiling_area_sq_ft=1200,          # Required: Ceiling area
    surfaces=[                         # Required: At least one surface
        SurfaceDefinition(
            surface_type="ceiling",    # ceiling, wall, floor, door, window
            material_key="act_nrc_0.70",  # Material from database
            area_sq_ft=1200
        ),
        # ... more surfaces
    ],
    calculation_method="sabine",       # sabine or eyring
    debug_mode=False                   # Optional: Include debug info
)
```

**Response:**
```python
result = api.rt60.calculate_rt60(request)

result.status                    # "success", "warning", or "error"
result.rt60_by_frequency         # {125: 0.93, 250: 0.88, 500: 0.55, ...}
result.average_rt60              # Average across speech frequencies (500-2000 Hz)
result.total_absorption_by_frequency  # Sabins at each frequency
result.surface_analysis          # Detailed breakdown per surface
result.error                     # APIError if status == "error"
```

#### `api.rt60.analyze_compliance(request)`

Check RT60 values against compliance targets.

```python
from src.api.schemas.rt60_schemas import RT60ComplianceRequest

request = RT60ComplianceRequest(
    rt60_by_frequency={125: 1.2, 250: 1.0, 500: 0.8, 1000: 0.7, 2000: 0.6, 4000: 0.5},
    room_type="conference",  # Or specify target_rt60 directly
    tolerance=0.1            # Acceptable deviation (default: 0.1s)
)

result = api.rt60.analyze_compliance(request)
result.overall_compliance        # True/False
result.frequencies_passing       # Count of compliant bands
result.recommendations           # Suggested improvements
```

**Supported Room Types:**
- `conference`, `classroom`, `office_private`, `office_open`
- `auditorium`, `worship`, `restaurant`
- `healthcare_patient`, `healthcare_public`, `residential`

#### `api.rt60.recommend_materials(request)`

Get material recommendations to achieve a target RT60.

```python
from src.api.schemas.rt60_schemas import MaterialRecommendationRequest, TreatableSurface

request = MaterialRecommendationRequest(
    volume_cubic_feet=12000,
    current_rt60_by_frequency={125: 1.5, 250: 1.3, 500: 1.1, 1000: 0.9, 2000: 0.8, 4000: 0.7},
    target_rt60=0.6,
    treatable_surfaces=[
        TreatableSurface(surface_type="ceiling", available_area_sq_ft=1200),
        TreatableSurface(surface_type="wall", available_area_sq_ft=800),
    ],
    max_recommendations=5
)

result = api.rt60.recommend_materials(request)
result.treatment_needed          # True/False
result.absorption_gap_sabins     # How much more absorption needed
result.surface_recommendations   # Material suggestions per surface
result.treatment_strategies      # Combined treatment plans
```

---

### HVAC Noise Service

Calculates mechanical background noise through HVAC duct paths.

#### `api.hvac.calculate_path_noise(request)`

Calculate noise transmission through an HVAC path from source to terminal.

**Request:**
```python
from src.api.schemas.hvac_schemas import (
    HVACPathNoiseRequest, PathElementInput, ReceiverRoomInput
)

request = HVACPathNoiseRequest(
    path_id="supply_path_1",
    path_elements=[
        PathElementInput(
            element_type="source",
            element_id="ahu_1",
            source_noise_dba=65,           # Or source_octave_bands for spectrum
        ),
        PathElementInput(
            element_type="duct",
            element_id="main_duct",
            length_ft=50,
            duct_shape="rectangular",      # rectangular or circular
            width_inches=24,
            height_inches=16,
            duct_type="sheet_metal",       # sheet_metal, fiberglass_lined, flex
            lining_thickness_inches=1.0,   # Required for ducts
            flow_rate_cfm=2000
        ),
        PathElementInput(
            element_type="elbow",
            element_id="elbow_1",
            elbow_type="square_no_vanes"   # square_no_vanes, square_with_vanes, radius
        ),
        PathElementInput(
            element_type="terminal",
            element_id="diffuser_1"
        )
    ],
    receiver_room=ReceiverRoomInput(
        room_volume_cubic_ft=12000,
        room_absorption_sabins=400,
        distance_from_terminal_ft=8.0,
        termination_type="flush"           # flush or free_space
    ),
    include_element_breakdown=True,
    debug_mode=False
)
```

**Response:**
```python
result = api.hvac.calculate_path_noise(request)

result.status                    # "success", "warning", or "error"
result.source_noise_dba          # Noise at path start
result.terminal_noise_dba        # Noise at path end (before room correction)
result.total_attenuation_dba     # Total path attenuation
result.nc_rating                 # NC rating at terminal
result.terminal_spectrum         # {63: 45, 125: 40, 250: 35, ...}
result.element_results           # Breakdown per element (if requested)
```

**Supported Element Types:**
- `source` - Noise source (AHU, fan, etc.)
- `duct` - Straight duct section
- `elbow` - Duct elbow/turn
- `silencer` - Sound attenuator
- `split` - Duct branch/split
- `terminal` - Diffuser/grille

#### `api.hvac.calculate_combined_receiver_noise(request)`

Combine noise from multiple paths serving a single space.

```python
from src.api.schemas.hvac_schemas import CombinedReceiverNoiseRequest

# First calculate individual paths
path1_result = api.hvac.calculate_path_noise(path1_request)
path2_result = api.hvac.calculate_path_noise(path2_request)

# Combine results
request = CombinedReceiverNoiseRequest(
    receiver_space_id="conference_room_1",
    path_results=[path1_result, path2_result],
    room_volume_cubic_ft=12000,
    room_absorption_sabins=400
)

result = api.hvac.calculate_combined_receiver_noise(request)
result.combined_noise_dba        # Total noise from all paths
result.combined_nc_rating        # Combined NC rating
result.num_paths_combined        # Number of paths
result.dominant_path_id          # Path contributing most noise
result.path_contributions        # Breakdown per path
```

#### `api.hvac.analyze_nc_compliance(request)`

Check noise levels against NC criteria for a space type.

```python
from src.api.schemas.hvac_schemas import NCComplianceRequest

request = NCComplianceRequest(
    octave_band_levels={63: 45, 125: 40, 250: 35, 500: 30, 1000: 28, 2000: 25, 4000: 22, 8000: 20},
    space_type="private_office"  # Or specify target_nc directly
)

result = api.hvac.analyze_nc_compliance(request)
result.nc_rating                 # Calculated NC rating
result.target_nc                 # Target for space type
result.compliance_status         # "Excellent", "Acceptable", "Non-compliant"
result.exceedances               # Frequencies exceeding NC curve
```

**Supported Space Types:**
- `private_office`, `open_office`, `conference_room`
- `classroom`, `library`, `hospital_patient_room`
- `concert_hall`, `recording_studio`

---

### Materials Service

Access the acoustic materials database (1,339+ materials).

#### `api.materials.search_materials(request)`

Search for materials by category, NRC, or frequency performance.

```python
from src.api.schemas.material_schemas import MaterialSearchRequest

request = MaterialSearchRequest(
    category="ceiling",          # Filter by category
    min_nrc=0.7,                 # Minimum NRC rating
    max_nrc=0.9,                 # Maximum NRC rating
    frequency_filter={           # Optional: filter by frequency performance
        1000: 0.8                # Minimum coefficient at 1000 Hz
    },
    search_term="acoustic tile", # Text search in name/description
    limit=20
)

result = api.materials.search_materials(request)
result.materials                 # List of MaterialInfo objects
result.total_count               # Total matching materials
```

#### `api.materials.get_material(request)`

Get detailed information for a specific material.

```python
from src.api.schemas.material_schemas import MaterialDetailRequest

request = MaterialDetailRequest(material_key="act_nrc_0.70")

result = api.materials.get_material(request)
result.material.name             # "ACT NRC 0.70"
result.material.category         # "Ceiling"
result.material.nrc              # 0.70
result.material.coefficients     # {125: 0.25, 250: 0.45, 500: 0.75, ...}
```

#### `api.materials.list_categories()`

List all available material categories.

```python
result = api.materials.list_categories()
result.categories                # ["Ceiling", "Wall", "Floor", ...]
result.total_materials           # 1339
result.materials_by_category     # {"Ceiling": 271, "Wall": 952, ...}
```

---

### Simulation Service

What-if scenario analysis for design optimization.

#### `api.simulation.simulate_rt60_material_change(request)`

Simulate the effect of changing materials on RT60.

```python
from src.api.schemas.simulation_schemas import RT60MaterialChangeRequest, MaterialChange

# First get baseline calculation
baseline = api.rt60.calculate_rt60(baseline_request)

# Simulate material change
request = RT60MaterialChangeRequest(
    baseline_rt60_response=baseline,
    volume_cubic_feet=12000,
    floor_area_sq_ft=1200,
    wall_area_sq_ft=1600,
    ceiling_area_sq_ft=1200,
    material_changes=[
        MaterialChange(
            surface_type="ceiling",
            original_material_key="gypsum_board",
            new_material_key="act_nrc_0.85",
            area_sq_ft=600  # Partial coverage
        )
    ]
)

result = api.simulation.simulate_rt60_material_change(request)
result.baseline_rt60_by_frequency    # Original values
result.simulated_rt60_by_frequency   # New values
result.rt60_change_by_frequency      # Delta per frequency
result.improvement_percentage        # Overall improvement
```

#### `api.simulation.simulate_hvac_path_modification(request)`

Simulate modifications to an HVAC path.

```python
from src.api.schemas.simulation_schemas import HVACPathModificationRequest, ElementModification

request = HVACPathModificationRequest(
    baseline_path_response=baseline_path_result,
    modifications=[
        ElementModification(
            element_id="main_duct",
            new_lining_thickness_inches=2.0  # Upgrade from 1.0"
        )
    ]
)

result = api.simulation.simulate_hvac_path_modification(request)
result.baseline_terminal_dba         # Original noise
result.simulated_terminal_dba        # New noise
result.noise_reduction_dba           # Improvement
result.baseline_nc_rating            # Original NC
result.simulated_nc_rating           # New NC
```

---

## Schema Discovery

The API provides endpoints for LLM agents to discover available operations:

```python
api = AcousticAnalysisAPI()

# Get complete API schema
schema = api.get_api_schema()
print(schema["api_version"])         # "1.0.0"
print(schema["services"].keys())     # ["rt60", "hvac", "materials", "simulation"]
print(schema["frequency_bands"])     # RT60 and HVAC frequency bands
print(schema["units"])               # Unit conventions used

# Get example requests
examples = api.get_quick_start_examples()
print(examples["rt60_calculation"])  # Example RT60 request
print(examples["hvac_path_noise"])   # Example HVAC request
print(examples["material_search"])   # Example material search
```

---

## Strict Validation

All requests are strictly validated before processing. Missing or invalid fields return detailed errors:

```python
# Missing required field
request = RT60CalculationRequest(
    volume_cubic_feet=12000,
    floor_area_sq_ft=1200,
    # wall_area_sq_ft missing!
    ceiling_area_sq_ft=1200,
    surfaces=[...]
)

result = api.rt60.calculate_rt60(request)
print(result.status)  # "error"
print(result.error.missing_fields)  # ["wall_area_sq_ft"]
print(result.error.suggestion)  # Helpful guidance
```

**Validation includes:**
- All geometry values must be positive numbers
- All material keys must exist in the database
- Frequency dictionaries must include all required bands
- Duct elements require dimensions, type, lining thickness, and flow rate
- Source elements require noise level specification

---

## Error Handling

All responses include a `status` field and optional `error` object:

```python
result = api.rt60.calculate_rt60(request)

if result.status == "success":
    # Use results normally
    print(result.average_rt60)

elif result.status == "warning":
    # Results available but with caveats
    print(result.warnings)
    print(result.average_rt60)

elif result.status == "error":
    # Request failed
    print(result.error.error_code)      # e.g., "VALIDATION_ERROR"
    print(result.error.error_message)   # Human-readable description
    print(result.error.field_errors)    # Per-field errors
    print(result.error.missing_fields)  # List of missing required fields
    print(result.error.suggestion)      # How to fix the issue
```

**Error Codes:**
- `VALIDATION_ERROR` - Request validation failed
- `CALCULATION_ERROR` - Calculation failed (invalid physics)
- `MATERIAL_NOT_FOUND` - Unknown material key
- `INVALID_ELEMENT_TYPE` - Unknown HVAC element type

---

## Example Workflows

### Complete Room Acoustics Analysis

```python
from src.api import AcousticAnalysisAPI
from src.api.schemas.rt60_schemas import *

api = AcousticAnalysisAPI()

# 1. Search for appropriate materials
ceiling_materials = api.materials.search_materials(
    MaterialSearchRequest(category="ceiling", min_nrc=0.7, limit=5)
)

# 2. Calculate RT60 with selected materials
rt60_result = api.rt60.calculate_rt60(RT60CalculationRequest(
    volume_cubic_feet=15000,
    floor_area_sq_ft=1500,
    wall_area_sq_ft=2000,
    ceiling_area_sq_ft=1500,
    surfaces=[
        SurfaceDefinition("ceiling", ceiling_materials.materials[0].material_key, 1500),
        SurfaceDefinition("wall", "gypsum_board_on_studs", 2000),
        SurfaceDefinition("floor", "carpet_-_heavy_on_concrete", 1500),
    ]
))

# 3. Check compliance
compliance = api.rt60.analyze_compliance(RT60ComplianceRequest(
    rt60_by_frequency=rt60_result.rt60_by_frequency,
    room_type="conference"
))

# 4. If non-compliant, get recommendations
if not compliance.overall_compliance:
    recommendations = api.rt60.recommend_materials(MaterialRecommendationRequest(
        volume_cubic_feet=15000,
        current_rt60_by_frequency=rt60_result.rt60_by_frequency,
        target_rt60=compliance.target_rt60,
        treatable_surfaces=[
            TreatableSurface("ceiling", 1500),
            TreatableSurface("wall", 500),
        ]
    ))
```

### HVAC System Noise Analysis

```python
from src.api import AcousticAnalysisAPI
from src.api.schemas.hvac_schemas import *

api = AcousticAnalysisAPI()

# 1. Calculate supply path noise
supply_path = api.hvac.calculate_path_noise(HVACPathNoiseRequest(
    path_id="supply_1",
    path_elements=[
        PathElementInput("source", "ahu_1", source_noise_dba=70),
        PathElementInput("duct", "main_supply", length_ft=80,
                        duct_shape="rectangular", width_inches=24, height_inches=18,
                        duct_type="sheet_metal", lining_thickness_inches=1.0, flow_rate_cfm=3000),
        PathElementInput("elbow", "elbow_1", elbow_type="square_with_vanes"),
        PathElementInput("terminal", "diffuser_1")
    ],
    receiver_room=ReceiverRoomInput(12000, 400, 8.0, "flush")
))

# 2. Calculate return path noise
return_path = api.hvac.calculate_path_noise(HVACPathNoiseRequest(
    path_id="return_1",
    path_elements=[
        PathElementInput("source", "ahu_1", source_noise_dba=65),
        PathElementInput("duct", "main_return", length_ft=60,
                        duct_shape="rectangular", width_inches=30, height_inches=20,
                        duct_type="sheet_metal", lining_thickness_inches=1.0, flow_rate_cfm=2800),
        PathElementInput("terminal", "return_grille_1")
    ],
    receiver_room=ReceiverRoomInput(12000, 400, 10.0, "flush")
))

# 3. Combine paths for total room noise
combined = api.hvac.calculate_combined_receiver_noise(CombinedReceiverNoiseRequest(
    receiver_space_id="conference_room",
    path_results=[supply_path, return_path],
    room_volume_cubic_ft=12000,
    room_absorption_sabins=400
))

# 4. Check NC compliance
nc_check = api.hvac.analyze_nc_compliance(NCComplianceRequest(
    octave_band_levels=combined.combined_spectrum,
    space_type="conference_room"
))

print(f"Combined NC: {combined.combined_nc_rating}")
print(f"Compliance: {nc_check.compliance_status}")
```

---

## Expansion Ideas

### Near-Term Enhancements

1. **Breakout Noise Calculation**
   - Add duct breakout/flanking path analysis
   - Calculate noise radiating through duct walls
   - Important for ducts passing through sensitive spaces

2. **STC/OITC Wall Analysis**
   - Sound Transmission Class calculations
   - Outdoor-Indoor Transmission Class
   - Partition performance analysis

3. **Background Noise Addition**
   - Combine HVAC noise with other sources
   - Equipment noise (projectors, computers)
   - External noise intrusion

4. **Detailed Fitting Library**
   - Expand silencer product database
   - Add VAV box noise generation
   - Fan-powered terminal units
   - Diffuser directivity patterns

### Medium-Term Enhancements

5. **Speech Privacy Metrics**
   - Articulation Index (AI) calculation
   - Speech Intelligibility Index (SII)
   - Privacy metrics (PI, NIC)

6. **Multi-Room Analysis**
   - Adjacent room noise transfer
   - Ceiling plenum paths
   - Door undercut calculations

7. **Time-Domain Analysis**
   - Early Decay Time (EDT)
   - Clarity (C50, C80)
   - Definition (D50)
   - Speech Transmission Index (STI)

8. **Optimization Engine**
   - Automatic material selection for target RT60
   - Duct sizing optimization for NC targets
   - Cost-weighted recommendations

### Long-Term Vision

9. **3D Room Modeling**
   - Ray tracing for complex geometries
   - Acoustic modeling integration (Odeon, EASE)
   - BIM/IFC import

10. **Real-Time Measurement Integration**
    - Import field measurement data
    - Calibration with measured values
    - Commissioning verification

11. **Machine Learning Enhancements**
    - Material recommendation from room photos
    - Automatic space classification
    - Predictive compliance checking

12. **Regulatory Compliance Engine**
    - LEED acoustic credit calculations
    - WELL Building Standard compliance
    - Local code compliance checking
    - Automated documentation generation

### API Architecture Improvements

13. **Async Operations**
    - Batch calculation support
    - Progress callbacks for long operations
    - Parallel path analysis

14. **Caching Layer**
    - Material lookup caching
    - Calculation result caching
    - Incremental updates

15. **Event System**
    - Calculation completion hooks
    - Compliance threshold alerts
    - Change notification system

16. **Version Management**
    - API versioning support
    - Schema migration utilities
    - Backward compatibility layer

---

## Testing

Run the test suite:

```bash
# Activate virtual environment
source .venv/bin/activate

# Run API tests
python -m pytest tests/test_api.py -v

# Run with coverage
python -m pytest tests/test_api.py -v --cov=src/api
```

---

## Contributing

When extending the API:

1. **Add schemas first** - Define request/response dataclasses in `schemas/`
2. **Add validation** - Implement validators in `validators/`
3. **Implement endpoint** - Add service methods in `endpoints/`
4. **Update facade** - Expose new service in `facade.py`
5. **Add tests** - Cover all new functionality in `tests/test_api.py`
6. **Update documentation** - Add examples to this file

---

## License

Part of the Acoustic Analysis Tool project. See main repository for license information.
