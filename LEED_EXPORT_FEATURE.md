# LEED Acoustic Performance Template Export

## Overview
The Excel export functionality has been enhanced to include LEED Acoustic Performance Template format sheets. This allows direct export of acoustic analysis data in the format required for LEED documentation.

## What's New

### 1. Fixed Excel Export Bug
- **Issue**: "'Cell' object is not iterable" error when exporting to Excel
- **Fix**: Updated `apply_header_style()` and `apply_subheader_style()` methods to handle both single cells and cell ranges properly

### 2. LEED Format Sheets
Added five new sheets that conform to LEED Acoustic Performance Template standards:

#### LEED - Reverberation Time
Columns match the LEED template:
- Room ID
- Room Name
- Type
- Grouping Type (if applicable)
- Required RT (sec)
- Calculated RT (sec)
- Surface Treatments Applied
- Source of RT Data
- Notes

**Data Populated**:
- Room IDs, names, and types from space data
- Target and calculated RT60 values
- Applied surface materials (ceiling, wall, floor)
- Calculation methodology

#### LEED - Absorptive Materials
Columns match the LEED template:
- Space ID
- Room Name / Type
- Surface Material ID
- Description of Material
- Manufacturer
- Absorption Coefficient (500 Hz)
- Absorption Coefficient (1000 Hz)
- Absorption Coefficient (2000 Hz)
- Surface Area (SF)
- Material Location (Floor, Ceiling, Wall)
- Source of Material Info
- Notes

**Data Populated**:
- Space IDs and names
- Material descriptions for ceiling, wall, and floor
- Surface areas for each material location
- Material source information

#### LEED - Background Noise
Columns match the LEED template:
- Room ID
- Room Name
- Type
- Sound Rating Method (NC/RC)
- Background Noise Level (dBA)
- Source of Noise Data
- Notes

**Data Populated**:
- Space information
- NC rating method
- Calculated dBA levels from HVAC receiver results
- NC ratings as notes

#### LEED - Sound Transmission
Columns match the LEED template:
- Room ID
- Room Name
- Type
- Assembly Location (Wall, Floor, Ceiling)
- Assembly ID / Description
- Adjacent Space(s)
- STC Rating
- Source of Assembly Data
- Notes

**Data Structure**: Ready for manual completion of STC ratings and assembly data

#### LEED - Wall Ceiling Floor Data
Columns match the LEED template:
- Assembly Location (Wall, Floor, Ceiling)
- Assembly ID / Description
- STC Rating
- Source of Assembly Data
- Notes

**Data Populated**:
- Unique materials organized by location (Wall, Ceiling, Floor)
- Material descriptions
- Source information

## How to Use

### From the Application
1. Open your project in the Results Analysis tab
2. Click the **"📊 Export to Excel"** button
3. Choose a filename and location
4. The exported Excel file will contain:
   - Original analysis sheets (Project Summary, Spaces Analysis, HVAC Paths, etc.)
   - Five new LEED-format sheets

### Programmatic Usage
```python
from data.excel_exporter import ExcelExporter, ExportOptions

# Create exporter
exporter = ExcelExporter()

# Configure options (LEED format is enabled by default)
options = ExportOptions(
    include_spaces=True,
    include_hvac_paths=True,
    include_components=True,
    include_rt60_details=True,
    include_nc_analysis=True,
    include_recommendations=True,
    include_charts=True,
    leed_format=True  # Enable LEED format sheets
)

# Export
success = exporter.export_project_analysis(
    project_id=1,
    export_path="project_analysis.xlsx",
    options=options
)
```

### Disabling LEED Format Sheets
If you want to export without the LEED format sheets:
```python
options = ExportOptions(leed_format=False)
```

## LEED Template Compliance

The exported sheets match the format of the official LEED Acoustic Performance Template CSV files:
- ✅ Column headers match exactly
- ✅ Data types and formats align with LEED requirements
- ✅ Ready for LEED documentation submission
- ⚠️ Some fields (like STC ratings, assembly data) may need manual completion

## Data Mapping

### From Application Data to LEED Format

| Application Data | LEED Sheet | LEED Column |
|-----------------|------------|-------------|
| Space.id | Reverberation Time | Room ID |
| Space.name | Reverberation Time | Room Name |
| Space.space_type | Reverberation Time | Type |
| Space.target_rt60 | Reverberation Time | Required RT (sec) |
| Space.calculated_rt60 | Reverberation Time | Calculated RT (sec) |
| Space materials | Absorptive Materials | All columns |
| HVACReceiverResult.total_dba | Background Noise | Background Noise Level (dBA) |
| HVACReceiverResult.nc_rating | Background Noise | Notes (as NC-XX) |

## Notes

### Automatically Populated Fields
- Room/Space identifiers and names
- RT60 calculations
- Material descriptions and locations
- Surface areas
- HVAC noise calculations (dBA and NC)

### Fields Requiring Manual Input
- Grouping Types
- Surface Material IDs
- Manufacturer information
- Absorption coefficients (500Hz, 1000Hz, 2000Hz)*
- Assembly IDs and descriptions
- Adjacent space information
- STC ratings

*Note: Absorption coefficient data may be available in the materials database but requires additional integration.

## Future Enhancements

Potential improvements for future versions:
1. Auto-populate absorption coefficients from materials database
2. Calculate and populate STC ratings based on wall assemblies
3. Add adjacent space detection and mapping
4. Include assembly detail lookups from architectural drawings
5. Add LEED compliance validation

## Testing

The LEED export functionality has been tested and verified to:
- ✅ Create all five LEED-format sheets
- ✅ Use correct column headers matching LEED template
- ✅ Populate data from application models
- ✅ Apply proper formatting and styling
- ✅ Auto-size columns for readability

## Support

For issues or questions about the LEED export feature:
1. Check that all required data is entered in the application
2. Verify that spaces have RT60 calculations completed
3. Ensure HVAC paths have been calculated for noise data
4. Review the exported Excel file for any blank required fields

