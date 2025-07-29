# Product Requirements Document (PRD)
## Room Acoustics Calculator Module - RT60 Analysis Integration

### Executive Summary
A PySide6-based room acoustics calculator module that integrates directly into the existing Room Properties interface of the Acoustic Analysis Tool. This module provides detailed reverberation time (RT60) calculations with surface material assignment, automatic area calculations with manual override capabilities, and comprehensive results management.

### Integration Architecture

#### Embedded Module Structure
```
Existing Room Properties Interface
├── Geometry Tab (existing)
│   ├── Rectangle Dimensions
│   ├── Height Input
│   └── Volume Calculation
├── HVAC Connections Tab (existing)
└── Acoustics Tab ← NEW EMBEDDED MODULE
    ├── Surface Materials Assignment
    ├── RT60 Calculations
    └── Results Display
```

### Enhanced Room Properties Interface

#### Updated Room Properties Window
```
Room Properties: Conference Room A
┌─────────────────────────────────────────────────────────────────────────────────┐
│ [Geometry] [HVAC] [Acoustics] [Reports]                                         │ 
├─────────────────────────────────────────────────────────────────────────────────┤
│ ◄ ACOUSTICS TAB (NEW) ►                                                         │
│                                                                                 │
│ ┌──── Room Geometry (from Geometry tab) ────┐ ┌──── Target Criteria ─────────┐ │
│ │ Floor Area: 425 sf (from drawing)         │ │ Target RT60: [0.8 ▼] seconds │ │
│ │ Perimeter: 84 ft (calculated)             │ │ Room Type: [Conference ▼]    │ │
│ │ Ceiling Height: 9.0 ft (user input)       │ │ LEED Compliance: ☐ Required  │ │
│ │ Volume: 3,825 cf (calculated)             │ │ Tolerance: [±0.1] seconds    │ │
│ └────────────────────────────────────────────┘ └───────────────────────────────┘ │
│                                                                                 │
│ ┌────────────────── Surface Materials Assignment ─────────────────────────────┐ │
│ │Surface Type         │Material               │Area (sf)    │Calc│Manual│[+/-]│ │
│ ├─────────────────────┼───────────────────────┼─────────────┼────┼──────┼─────┤ │
│ │Primary Wall #1      │[WOOD PANELING,THICK▼]│ 756 │ ✓ │ 756 │ [ ] │  ×  │ │
│ │Primary Wall #2      │[PAINTED DRYWALL   ▼]│ 0   │   │ 120 │ ☑ │  ×  │ │
│ │Door Surfaces (3×7)  │[SOLID WOOD DOORS  ▼]│ 63  │ ✓ │ 63  │ [ ] │  ×  │ │
│ │Windows              │[GLASS, WINDOW     ▼]│ 85  │ ✓ │ 85  │ [ ] │  ×  │ │
│ │Floor Surface        │[CARPET, 3/8" PILE ▼]│ 425 │ ✓ │ 425 │ [ ] │  ×  │ │
│ │Primary Ceiling      │[ACT STANDARD      ▼]│ 425 │ ✓ │ 425 │ [ ] │  ×  │ │
│ │[Add Surface ▼]      │                      │     │   │     │     │  +  │ │
│ └─────────────────────────────────────────────────────────────────────────────┘ │
│                                                                                 │
│ ┌──── Material Preview ────┐ ┌────────── Calculation Results ──────────────────┐ │
│ │Selected: WOOD PANELING   │ │Frequency(Hz)│125 │250 │500 │1000│2000│4000│NRC │ │
│ │Absorption Coefficients:  │ │Total Sabines│360 │425 │890 │945 │962 │890 │    │ │
│ │125Hz: 0.19  1kHz: 0.06  │ │RT60 (sec)   │1.8 │1.5 │0.7 │0.6 │0.6 │0.7 │    │ │
│ │250Hz: 0.14  2kHz: 0.06  │ │Target RT60  │0.8 │0.8 │0.8 │0.8 │0.8 │0.8 │    │ │
│ │500Hz: 0.09  4kHz: 0.05  │ │Status       │❌  │❌  │✅  │✅  │✅  │✅  │    │ │
│ │NRC: 0.09               │ │Overall: ❌ Exceeds target at low frequencies     │ │
│ └──────────────────────────┘ └───────────────────────────────────────────────────┘ │
│                                                                                 │
│ ┌─────────────────── RT60 Frequency Response Graph ──────────────────────────┐ │
│ │    2.0 ┌─────────────────────────────────────────────────────────────────┐ │ │
│ │        │  ●●                                                             │ │ │
│ │    1.5 │     ●●                                                          │ │ │
│ │        │       ●●                                                        │ │ │
│ │    1.0 │ ┄┄┄┄┄┄┄┄●●┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄ Target │ │ │
│ │        │             ●●●●●●●●●●●●●●●●●●●●●●●●●●●●●●●●●●●●●●●●●●●●●●●●●● │ │ │
│ │    0.5 │                                                                 │ │ │
│ │        │  — Calculated RT60    ┄┄┄ Target RT60 (0.8s)                   │ │ │
│ │    0.0 └─────────────────────────────────────────────────────────────────┘ │ │
│ │         125    250    500   1000   2000   4000                             │ │
│ │                         Frequency (Hz)                                     │ │
│ └─────────────────────────────────────────────────────────────────────────────┘ │
│                                                                                 │
│ [Recalculate] [Material Library] [Export Results] │ ✅ Saved to Project       │
└─────────────────────────────────────────────────────────────────────────────────┘
```

### Enhanced Database Schema

#### Surface Categories and Types
```sql
-- Surface Categories for organized material selection
CREATE TABLE surface_categories (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL, -- 'walls', 'ceilings', 'floors', 'doors', 'windows', 'specialty'
    description TEXT
);

-- Surface Types (predefined surface options)
CREATE TABLE surface_types (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL, -- 'Primary Wall', 'Secondary Wall', 'Acoustic Treatment', etc.
    category_id INTEGER,
    default_calculation_method TEXT, -- 'perimeter_height', 'manual', 'percentage'
    FOREIGN KEY (category_id) REFERENCES surface_categories (id)
);

-- Enhanced Acoustic Materials with Categories
CREATE TABLE acoustic_materials (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    category_id INTEGER, -- Links to surface_categories
    manufacturer TEXT,
    product_code TEXT,
    description TEXT,
    absorption_125 REAL,
    absorption_250 REAL,
    absorption_500 REAL,
    absorption_1000 REAL,
    absorption_2000 REAL,
    absorption_4000 REAL,
    nrc REAL,
    mounting_type TEXT, -- 'direct', 'suspended', 'spaced'
    thickness TEXT,
    source TEXT,
    import_date TIMESTAMP,
    FOREIGN KEY (category_id) REFERENCES surface_categories (id)
);

-- Room Surface Instances (multiple instances per surface type)
CREATE TABLE room_surface_instances (
    id INTEGER PRIMARY KEY,
    space_id INTEGER,
    surface_type_id INTEGER,
    instance_name TEXT, -- 'Primary Wall #1', 'Primary Wall #2', etc.
    material_id INTEGER,
    calculated_area REAL, -- Auto-calculated area
    manual_area REAL, -- User override area
    use_manual_area BOOLEAN DEFAULT FALSE,
    area_calculation_notes TEXT,
    created_date TIMESTAMP,
    FOREIGN KEY (space_id) REFERENCES spaces (id),
    FOREIGN KEY (surface_type_id) REFERENCES surface_types (id),
    FOREIGN KEY (material_id) REFERENCES acoustic_materials (id)
);

-- Enhanced RT60 Results with Target Tracking
CREATE TABLE rt60_calculation_results (
    id INTEGER PRIMARY KEY,
    space_id INTEGER,
    calculation_date TIMESTAMP,
    target_rt60 REAL,
    target_tolerance REAL,
    room_type TEXT, -- 'conference', 'office', 'classroom', etc.
    leed_compliance_required BOOLEAN,
    
    -- Calculated values
    total_sabines_125 REAL,
    total_sabines_250 REAL,
    total_sabines_500 REAL,
    total_sabines_1000 REAL,
    total_sabines_2000 REAL,
    total_sabines_4000 REAL,
    
    rt60_125 REAL,
    rt60_250 REAL,
    rt60_500 REAL,
    rt60_1000 REAL,
    rt60_2000 REAL,
    rt60_4000 REAL,
    
    meets_target_125 BOOLEAN,
    meets_target_250 BOOLEAN,
    meets_target_500 BOOLEAN,
    meets_target_1000 BOOLEAN,
    meets_target_2000 BOOLEAN,
    meets_target_4000 BOOLEAN,
    
    overall_compliance BOOLEAN,
    compliance_notes TEXT,
    
    FOREIGN KEY (space_id) REFERENCES spaces (id)
);
```

### Surface Area Calculation Engine

#### Automatic Area Calculation
```python
class SurfaceAreaCalculator:
    def __init__(self, space):
        self.space = space
        self.floor_area = space.calculated_area  # From rectangle drawing
        self.perimeter = space.calculated_perimeter
        self.ceiling_height = space.ceiling_height
        
    def calculate_surface_areas(self):
        """Calculate areas for different surface types"""
        areas = {}
        
        # Wall areas
        total_wall_area = self.perimeter * self.ceiling_height
        areas['total_walls'] = total_wall_area
        
        # Floor and ceiling (same as floor area from drawing)
        areas['floor'] = self.floor_area
        areas['ceiling'] = self.floor_area
        
        return areas
    
    def get_calculated_area(self, surface_type, instance_number=1):
        """Get calculated area for specific surface type"""
        areas = self.calculate_surface_areas()
        
        # Default distribution logic
        if 'wall' in surface_type.name.lower():
            return areas['total_walls']  # User can manually divide
        elif 'floor' in surface_type.name.lower():
            return areas['floor']
        elif 'ceiling' in surface_type.name.lower():
            return areas['ceiling']
        else:
            return 0.0  # Manual input required
```

### Material Database with Categories

#### Predefined Surface Categories and Types
```python
SURFACE_CATEGORIES = {
    'walls': {
        'types': ['Primary Wall', 'Secondary Wall', 'Accent Wall', 'Acoustic Treatment'],
        'calculation': 'perimeter_height'
    },
    'ceilings': {
        'types': ['Primary Ceiling', 'Secondary Ceiling', 'Clouds/Baffles', 'Mechanical'],
        'calculation': 'floor_area'
    },
    'floors': {
        'types': ['Floor Surface', 'Raised Floor', 'Floor Treatment'],
        'calculation': 'floor_area'
    },
    'doors': {
        'types': ['Entry Doors', 'Interior Doors', 'Glazed Doors'],
        'calculation': 'manual'
    },
    'windows': {
        'types': ['Windows', 'Glazed Partitions', 'Curtain Wall'],
        'calculation': 'manual'
    },
    'specialty': {
        'types': ['Custom Surface', 'Equipment', 'Furniture'],
        'calculation': 'manual'
    }
}
```

### Enhanced User Interface Components

#### Surface Management Interface
```python
class SurfaceManagementWidget(QWidget):
    def __init__(self, space):
        self.space = space
        self.surface_calculator = SurfaceAreaCalculator(space)
        
    def add_surface_instance(self, surface_type):
        """Add new instance of surface type"""
        instance_count = self.get_instance_count(surface_type)
        instance_name = f"{surface_type.name} #{instance_count + 1}"
        
        # Create new surface instance
        surface_instance = RoomSurfaceInstance(
            space_id=self.space.id,
            surface_type_id=surface_type.id,
            instance_name=instance_name,
            calculated_area=self.surface_calculator.get_calculated_area(surface_type)
        )
        
    def toggle_manual_area(self, surface_instance, use_manual):
        """Toggle between calculated and manual area input"""
        surface_instance.use_manual_area = use_manual
        if not use_manual:
            # Revert to calculated area
            surface_instance.manual_area = surface_instance.calculated_area
```

#### Material Search with Category Filter
```python
class MaterialSelectionDialog(QDialog):
    def __init__(self, surface_category):
        self.surface_category = surface_category
        self.setup_ui()
        
    def setup_ui(self):
        # Category-filtered material search
        self.category_filter = QComboBox()
        self.category_filter.addItems(['All Materials', 'Wall Materials', 
                                     'Ceiling Materials', 'Floor Materials'])
        
        # Search functionality
        self.search_box = QLineEdit()
        self.search_box.textChanged.connect(self.filter_materials)
        
        # Material list with absorption preview
        self.material_list = QListWidget()
        self.material_list.currentItemChanged.connect(self.preview_material)
```

### Target RT60 and Compliance Tracking

#### Target RT60 Curves by Room Type
```python
RT60_TARGETS = {
    'conference': {'target': 0.8, 'tolerance': 0.1},
    'office_private': {'target': 0.6, 'tolerance': 0.1},
    'office_open': {'target': 0.8, 'tolerance': 0.15},
    'classroom': {'target': 0.6, 'tolerance': 0.1},
    'auditorium': {'target': 1.2, 'tolerance': 0.2},
    'gym': {'target': 2.0, 'tolerance': 0.3},
    'custom': {'target': None, 'tolerance': 0.1}  # User-defined
}
```

#### Compliance Checker
```python
class ComplianceChecker:
    def __init__(self, target_rt60, tolerance):
        self.target_rt60 = target_rt60
        self.tolerance = tolerance
        
    def check_frequency_compliance(self, calculated_rt60):
        """Check compliance for each frequency band"""
        compliance = {}
        for freq, rt60_value in calculated_rt60.items():
            lower_bound = self.target_rt60 - self.tolerance
            upper_bound = self.target_rt60 + self.tolerance
            compliance[freq] = lower_bound <= rt60_value <= upper_bound
        return compliance
```

### Integration Points with Existing System

#### Room Properties Enhancement
```python
# Update existing room properties dialog
class RoomPropertiesDialog(QDialog):
    def __init__(self, space):
        super().__init__()
        self.space = space
        self.setup_tabs()
        
    def setup_tabs(self):
        self.tab_widget = QTabWidget()
        
        # Existing tabs
        self.geometry_tab = GeometryTab(self.space)
        self.hvac_tab = HVACConnectionsTab(self.space)
        
        # New acoustics tab
        self.acoustics_tab = AcousticsCalculatorTab(self.space)  # NEW
        
        self.tab_widget.addTab(self.geometry_tab, "Geometry")
        self.tab_widget.addTab(self.hvac_tab, "HVAC")
        self.tab_widget.addTab(self.acoustics_tab, "Acoustics")  # NEW
```

### Export and Reporting

#### Enhanced Export Options
```python
class RT60ResultsExporter:
    def export_to_excel(self, space, results):
        """Export RT60 results to Excel format matching prototype"""
        # Create workbook matching the Excel prototype layout
        
    def export_to_project_database(self, space, results):
        """Save results to main project database"""
        
    def generate_compliance_report(self, space, results):
        """Generate LEED compliance report"""
```

This revised PRD embeds the Room Acoustics Calculator directly into your existing Room Properties interface, provides flexible surface management with calculated+manual area options, includes comprehensive target RT60 tracking, and maintains full integration with your project database system.