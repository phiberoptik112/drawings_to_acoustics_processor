# Acoustic Analysis Tool

Desktop application for LEED acoustic certification analysis built with PySide6.

## Features (Enhanced MVP) ✅

✅ **Project Management**
- Create and load acoustic analysis projects
- SQLite database with complete project persistence
- Recent projects display on splash screen
- Multi-project workflow support
- Drawing sets management with version control
- Drawing comparison engine with change detection

✅ **PDF Viewer & Drawing Tools**
- Full-featured PDF viewer with zoom and navigation
- Drawing overlay system with coordinate mapping
- Rectangle tool for room boundaries with area calculation
- Polygon tool for complex room shapes with area calculation
- HVAC component placement (AHU, VAV, diffusers, etc.)
- Duct segment drawing with connection management
- Measurement tool for scale calibration
- Scale manager with accurate coordinate transformation
- Complete drawing element persistence and reconstruction

✅ **Room Properties & Acoustic Analysis**
- Multi-tab room properties dialog with comprehensive setup
- Height input and volume calculations
- RT60 reverberation time analysis using Sabine/Eyring formulas
- Enhanced acoustic materials database (100+ materials)
- Material search engine with frequency-specific analysis
- Space type defaults for LEED certification
- Real-time calculation preview with target comparison
- Surface-specific material assignment system

✅ **Advanced HVAC Noise Analysis**
- **Unified Noise Engine**: Integrated calculation system with specialized modules
- **Component Library**: OCR-based mechanical schedule import from images/PDFs
- **Mechanical Units Database**: Project-level equipment with octave-band noise data
- **Path-based Analysis**: Complete HVAC noise calculation engine
- **Specialized Calculators**:
  - Circular duct attenuation (lined/unlined)
  - Rectangular duct attenuation (lined/unlined)
  - Flexible duct insertion loss
  - Elbow turning vane generated noise
  - Junction/elbow generated noise calculations
  - Receiver room sound correction
  - Rectangular elbow calculations
- **Advanced Path Management**: Multi-segment paths with fittings and connections
- **NC Rating Analysis**: Octave band processing with compliance checking
- **Integration**: Seamless connection between mechanical units and HVAC components

✅ **Enhanced Results & Export**
- Comprehensive results dashboard with real-time updates
- Professional Excel export with multi-sheet reports
- HVAC path analysis with detailed noise calculations
- Drawing comparison reports with acoustic impact analysis
- Validation and warning systems
- Standards compliance checking
- Treatment analysis and recommendations

✅ **Advanced Database System**
- Complete SQLAlchemy models for all project elements
- Enhanced CRUD operations through sophisticated UI dialogs
- Drawing element reconstruction with JSON properties
- Mechanical units and noise sources management
- Drawing sets and version comparison tracking
- Automated schema migrations for legacy database compatibility
- Project backup and recovery with complete data preservation

## Installation

### Prerequisites

- Python 3.8 or higher
- pip package manager
- Virtual environment (recommended)

### Setup

1. Clone or download this project
2. Create and activate virtual environment:

```bash
# Create virtual environment
python -m venv .venv

# Activate virtual environment
# On Linux/Mac:
source .venv/bin/activate
# On Windows:
.venv\Scripts\activate
```

3. Install dependencies:

```bash
pip install -r requirements.txt
```

### Running the Application

```bash
# Ensure virtual environment is activated
source .venv/bin/activate  # Linux/Mac
# .venv\Scripts\activate  # Windows

# Run the application
python src/main.py
```

## Development Status

### ✅ Enhanced MVP Complete - All Phases Finished + Advanced Features

**Phase 1 - Foundation (Complete):**

- [x] PySide6 application structure with professional UI
- [x] Splash screen with project creation/loading
- [x] SQLAlchemy database with comprehensive models
- [x] Project dashboard with multi-tab interface
- [x] Standard component and materials libraries

**Phase 2 - PDF Viewer & Drawing Tools (Complete + Enhanced):**

- [x] PyMuPDF PDF viewer integration with full navigation
- [x] Drawing interface with transparent overlay system
- [x] Rectangle and polygon tools for room boundary definition
- [x] Component, segment, and measurement tools
- [x] Scale management with coordinate transformation
- [x] Complete database persistence for all drawn elements
- [x] Drawing element reconstruction and session continuity

**Phase 3 - Room Properties & RT60 (Complete + Enhanced):**

- [x] Multi-tab room properties dialog with comprehensive setup
- [x] Height input and volume calculations
- [x] Professional RT60 calculation engine with Sabine/Eyring formulas
- [x] Enhanced acoustic materials database (100+ materials)
- [x] Material search engine with frequency-specific analysis
- [x] Space conversion from rectangles/polygons to acoustic spaces
- [x] Real-time calculation preview with target achievement analysis

**Phase 4 - Advanced HVAC Noise & Analysis (Complete + Enhanced):**

- [x] **Unified HVAC Noise Engine** with integrated specialized calculators
- [x] **Component Library System** with OCR import capabilities
- [x] **Mechanical Units Database** with octave-band noise data
- [x] **Advanced Path Management** with multi-segment noise analysis
- [x] **Specialized Calculation Modules**:
  - [x] Circular duct calculations (lined/unlined)
  - [x] Rectangular duct calculations (lined/unlined)  
  - [x] Flexible duct insertion loss
  - [x] Elbow turning vane generated noise
  - [x] Junction/elbow generated noise
  - [x] Receiver room sound correction
  - [x] Rectangular elbow calculations
- [x] **Enhanced NC Rating Analysis** with octave band processing
- [x] **Complete Air Path Modeling** from source to terminal

**Phase 5 - Drawing Comparison & Version Control (Complete):**

- [x] **Drawing Sets Management** for design phase tracking
- [x] **Drawing Comparison Engine** with automated change detection
- [x] **Acoustic Impact Analysis** of drawing changes
- [x] **Version Control Workflow** for multi-phase projects
- [x] **Change Documentation** with detailed impact reports

**Final Phase - Enhanced Export & Advanced Features (Complete):**

- [x] **Professional Excel Export** with enhanced multi-sheet reports
- [x] **Advanced Results Dashboard** with real-time calculation updates
- [x] **Treatment Analysis** with acoustic treatment recommendations
- [x] **Enhanced Validation Systems** with comprehensive warnings
- [x] **Component Library Integration** with OCR-based schedule import
- [x] **Complete MVP Testing Suite** with comprehensive validation

## Usage

### Enhanced Workflow

1. **Start Application**: Run `python src/main.py` (with virtual environment activated)
2. **Create Project**: Click "New Project" and fill in project details
3. **Import Drawings**: Load architectural PDF plans
4. **Set Up Drawing Sets**: Organize drawings by design phase (DD, SD, CD)
5. **Set Scale**: Use measurement tool to calibrate drawing scale
6. **Draw Rooms**: Use rectangle or polygon tools to define space boundaries
7. **Define Spaces**: Convert drawn shapes to acoustic spaces with materials
8. **Import Equipment**: Use Component Library to import mechanical schedules via OCR
9. **Place HVAC**: Add components (AHU, VAV, diffusers) and connect with segments
10. **Create Paths**: Build complete HVAC paths with noise analysis
11. **Calculate**: Perform comprehensive RT60 and HVAC noise analysis
12. **Compare Drawings**: Use drawing sets to track design phase changes
13. **Review Results**: Use enhanced results dashboard with detailed analysis
14. **Export**: Generate professional Excel reports with acoustic impact analysis

### New Advanced Features

#### Component Library Management
```bash
# Import mechanical schedules from images or PDFs
- Use "Import from Library" in HVAC component dialogs
- OCR-based automatic extraction from drawings
- Octave-band noise data integration
```

#### Drawing Comparison Workflow
```bash
# Track changes across design phases
- Create drawing sets for each design phase (DD, SD, CD)
- Compare sets to detect changes
- Analyze acoustic impact of modifications
- Generate change reports
```

#### Enhanced Materials Management
```bash
# Advanced material search and selection
- Frequency-specific material analysis
- Enhanced materials database (100+ materials)
- Category-based material filtering
- NRC and absorption coefficient management
```

### Testing

```bash
# Run comprehensive enhanced MVP tests
python test_mvp.py

# Run HVAC integration tests
python test_hvac_integration.py

# Run drawing comparison tests
python test_dialog_integration.py

# Run development structure tests
python test_structure.py
```

## Technical Details

### Enhanced Technologies

- **Framework**: PySide6 for professional desktop GUI
- **Database**: SQLite with SQLAlchemy ORM and automated migrations
- **PDF Processing**: PyMuPDF for full-featured PDF viewer
- **OCR Processing**: Tesseract for mechanical schedule import
- **Export**: openpyxl for professional Excel reports with enhanced formatting
- **Calculations**: NumPy/SciPy for acoustic analysis with specialized HVAC engines
- **Architecture**: Modular design with unified calculation engine and specialized modules

### Professional Standards & Enhancements

- **LEED Acoustic Certification**: Complete compliance requirements
- **ASHRAE 1991 Algorithms**: Industry-standard HVAC acoustic calculations
- **NC Rating Compliance**: Detailed octave-band analysis for space types
- **Enhanced Material Database**: 100+ acoustic materials with frequency-specific data
- **Professional HVAC Analysis**: Complete path-based noise modeling
- **Drawing Version Control**: Multi-phase project tracking and change analysis
- **Equipment Integration**: OCR-based mechanical schedule import and management

## Architecture

### Enhanced Modular Structure

```text
src/
├── main.py                    # Application entry point
├── models/                    # Enhanced SQLAlchemy database models
│   ├── database.py           # Database setup with automated migrations
│   ├── project.py            # Project and drawing models
│   ├── space.py              # Space and room boundary models (enhanced)
│   ├── hvac.py               # HVAC components, paths, segments
│   ├── mechanical.py         # Mechanical units and noise sources (NEW)
│   ├── drawing_sets.py       # Drawing sets and comparison models (NEW)
│   ├── drawing_elements.py   # Drawing persistence with JSON properties
│   └── rt60_models.py        # RT60 calculation and surface models
├── ui/                       # Enhanced user interface components
│   ├── splash_screen.py      # Project selection interface
│   ├── project_dashboard.py  # Main project management (enhanced)
│   ├── drawing_interface.py  # PDF viewer with advanced drawing tools
│   ├── hvac_management_widget.py # Comprehensive HVAC management (NEW)
│   ├── results_widget.py     # Enhanced results display
│   └── dialogs/              # Advanced dialog system
│       ├── room_properties.py      # Multi-tab room setup
│       ├── hvac_component_dialog.py # HVAC component management
│       ├── hvac_path_dialog.py     # HVAC path creation and analysis
│       ├── component_library_dialog.py # Equipment library with OCR import (NEW)
│       ├── drawing_sets_dialog.py     # Drawing sets management (NEW)
│       ├── comparison_selection_dialog.py # Drawing comparison tools (NEW)
│       └── material_search_dialog.py    # Advanced material search (NEW)
├── drawing/                   # Enhanced PDF and drawing functionality
│   ├── pdf_viewer.py         # PyMuPDF PDF viewer
│   ├── drawing_overlay.py    # Transparent drawing overlay (enhanced)
│   ├── drawing_tools.py      # Rectangle, polygon, component, segment tools
│   ├── drawing_comparison.py # Drawing comparison engine (NEW)
│   └── scale_manager.py      # Coordinate transformation
├── calculations/             # Advanced acoustic calculation engines
│   ├── hvac_noise_engine.py  # Unified HVAC calculation engine (NEW)
│   ├── hvac_path_calculator.py # Path management system (enhanced)
│   ├── rt60_calculator.py    # RT60 reverberation time (enhanced)
│   ├── enhanced_rt60_calculator.py # Advanced RT60 features (NEW)
│   ├── noise_calculator.py   # Legacy noise analysis
│   ├── nc_rating_analyzer.py # Enhanced NC rating compliance
│   ├── treatment_analyzer.py # Acoustic treatment analysis (NEW)
│   ├── surface_area_calculator.py # Surface area calculations (NEW)
│   ├── circular_duct_calculations.py # Circular duct attenuation (NEW)
│   ├── rectangular_duct_calculations.py # Rectangular duct attenuation (NEW)
│   ├── flex_duct_calculations.py # Flexible duct calculations (NEW)
│   ├── elbow_turning_vane_generated_noise_calculations.py # Elbow noise (NEW)
│   ├── junction_elbow_generated_noise_calculations.py # Junction noise (NEW)
│   ├── receiver_room_sound_correction_calculations.py # Room correction (NEW)
│   └── rectangular_elbows_calculations.py # Rectangular elbow noise (NEW)
└── data/                     # Enhanced data management and export
    ├── components.py         # Enhanced HVAC component library
    ├── materials.py          # Acoustic materials database (enhanced)
    ├── enhanced_materials.py # Advanced materials with frequency data (NEW)
    ├── materials_database.py # Centralized materials management (NEW)
    ├── material_search.py    # Advanced material search engine (NEW)
    ├── silencer_database.py  # Silencer component database (NEW)
    └── excel_exporter.py     # Professional Excel export (enhanced)
```

### Advanced Implementation Features

- **Unified Calculation Engine**: HVACNoiseEngine integrates 8+ specialized calculators
- **Advanced Database System**: Automated migrations with enhanced models
- **OCR Integration**: Automatic mechanical schedule extraction from drawings
- **Drawing Version Control**: Complete change tracking and acoustic impact analysis
- **Enhanced Materials System**: 100+ materials with frequency-specific data
- **Professional UI Dialogs**: Sophisticated multi-tab interfaces for complex workflows
- **Real-time Analysis**: Live calculation updates with comprehensive validation
- **Industry Compliance**: ASHRAE 1991 algorithms and LEED certification standards

### Enhanced Professional Implementation

- **Complete CRUD Operations**: Advanced database operations with enhanced UI
- **Real-time Calculation Engine**: Live updates with specialized HVAC modules
- **Professional UI System**: Multi-tab dialogs with sophisticated workflows
- **Industry-Standard Algorithms**: ASHRAE-compliant acoustic analysis
- **Comprehensive Error Handling**: Enhanced validation and user feedback
- **Advanced Excel Export**: Multi-sheet reports with drawing comparison analysis
- **Equipment Library Integration**: OCR-based import with noise data management
- **Drawing Version Control**: Multi-phase project tracking and change analysis

## Advanced Features & Capabilities

### HVAC Noise Analysis Engine

The application now includes a sophisticated HVAC noise analysis system based on **ASHRAE 1991 Algorithms**:

#### Specialized Calculation Modules
- **Circular Duct Calculator**: Lined and unlined circular duct attenuation
- **Rectangular Duct Calculator**: Lined and unlined rectangular duct attenuation  
- **Flexible Duct Calculator**: Insertion loss calculations for flexible ducts
- **Elbow Turning Vane Calculator**: Generated noise from elbows with turning vanes
- **Junction/Elbow Calculator**: Generated noise from junctions and elbows without vanes
- **Receiver Room Calculator**: Room sound correction factors
- **Rectangular Elbow Calculator**: Specialized calculations for rectangular elbows

#### Unified Engine Features
- **PathElement Structure**: Standardized data format for all HVAC elements
- **Octave Band Analysis**: Complete 8-band frequency analysis (63Hz-8kHz)
- **NC Rating Integration**: Professional noise criteria compliance checking
- **A-weighted Calculations**: Industry-standard sound level computation
- **Path Result Analysis**: Complete source-to-receiver noise modeling

### Component Library & Equipment Management

#### OCR-Based Import System
- **Image Import**: Extract mechanical schedules from PNG/JPG drawings
- **PDF Import**: Direct extraction from mechanical schedule PDFs
- **Automatic Processing**: Tesseract OCR with intelligent data parsing
- **Noise Data Integration**: Octave-band sound power levels from equipment

#### Mechanical Units Database
- **Equipment Library**: Project-level mechanical equipment records
- **Noise Specifications**: Inlet, outlet, and radiated noise levels
- **Equipment Integration**: Link mechanical units to HVAC components
- **Performance Data**: Airflow, static pressure, and power specifications

### Drawing Comparison & Version Control

#### Drawing Sets Management
- **Phase Organization**: Group drawings by design phase (DD, SD, CD, Final)
- **Version Tracking**: Complete change history across design development
- **Set Comparison**: Automated comparison between drawing sets
- **Change Detection**: Intelligent identification of modifications

#### Acoustic Impact Analysis
- **Geometric Analysis**: Detect changes in room boundaries and HVAC layouts
- **Acoustic Impact Scoring**: Quantify potential acoustic effects of changes
- **Change Documentation**: Detailed reports with acoustic implications
- **Professional Reporting**: Excel export with change analysis

### Enhanced Materials System

#### Advanced Materials Database
- **100+ Materials**: Comprehensive acoustic materials library
- **Frequency Data**: Complete octave-band absorption coefficients
- **Category Organization**: Ceiling, wall, floor, doors, windows categories
- **Search Engine**: Advanced text and frequency-based material search
- **NRC Calculations**: Automatic noise reduction coefficient computation

#### Material Management Features
- **Database Integration**: SQLite-based materials with custom additions
- **Enhanced Search**: Frequency-specific material analysis
- **Category Filtering**: Surface-type specific material selection
- **Performance Analysis**: Material effectiveness comparison tools

## Development Environment

### Virtual Environment Setup

The project uses a Python virtual environment for dependency isolation:

```bash
# Create virtual environment (one-time setup)
python -m venv .venv

# Activate environment (required for each session)
source .venv/bin/activate  # Linux/Mac
.venv\Scripts\activate     # Windows

# Install dependencies
pip install -r requirements.txt
```

### Enhanced Dependencies

#### Core Framework
- **PySide6**: Professional desktop GUI framework
- **SQLAlchemy**: Advanced ORM with automated migrations

#### Image & Document Processing  
- **PyMuPDF**: Professional PDF processing and rendering
- **OpenCV**: Image processing for OCR workflows
- **Tesseract**: OCR engine for mechanical schedule extraction
- **pdf2image**: PDF to image conversion for processing

#### Scientific Computing
- **NumPy/SciPy**: Advanced mathematical computations
- **Pandas**: Data analysis and manipulation
- **Matplotlib/Seaborn**: Professional visualization and plotting

#### Export & Reporting
- **openpyxl**: Professional Excel export with formatting
- **python-dateutil**: Enhanced date/time handling

### Development Workflow

#### Code Organization
- **Modular Architecture**: Separated calculation engines and UI components
- **Database Migrations**: Automated schema updates for legacy compatibility
- **Professional Standards**: ASHRAE and LEED compliance implementation
- **Comprehensive Testing**: Multi-level test suite with integration validation

#### Debug and Development Features
- **Debug Output Retention**: Comprehensive logging for HVAC feature development
- **Development Environment**: Virtual environment with dependency isolation
- **Migration System**: Automated database schema updates
- **Error Handling**: Enhanced validation and user feedback systems

## Current Development Status

### Production-Ready Features ✅

The Acoustic Analysis Tool has evolved from an MVP to a comprehensive, production-ready application with advanced capabilities:

#### Core Functionality
- **Complete LEED Compliance**: Full acoustic certification workflow
- **Professional HVAC Analysis**: Industry-standard noise calculations with ASHRAE algorithms
- **Advanced Drawing Tools**: Professional CAD-like drawing interface with persistence
- **Database Excellence**: Robust SQLite system with automated migrations
- **Excel Integration**: Professional reporting with multi-sheet analysis

#### Advanced Capabilities  
- **OCR Integration**: Automatic mechanical schedule import from images and PDFs
- **Drawing Version Control**: Multi-phase project tracking with change analysis
- **Enhanced Materials Library**: 100+ acoustic materials with frequency-specific data
- **Specialized Calculators**: 8+ HVAC calculation engines for comprehensive analysis
- **Professional UI**: Sophisticated multi-tab dialogs with real-time calculations

#### Technical Excellence
- **Unified Architecture**: Modular design with specialized calculation engines
- **Professional Standards**: ASHRAE, LEED, and NC rating compliance
- **Advanced Persistence**: Complete project data management with JSON flexibility
- **Performance Optimization**: Efficient calculations with real-time updates
- **Error Resilience**: Comprehensive validation and graceful error handling

### Ready for Production Deployment

The application represents a significant advancement in acoustic analysis tools:

1. **Industry Compliance**: Meets all LEED acoustic certification requirements
2. **Professional Workflow**: Complete design-to-analysis workflow integration
3. **Advanced Analysis**: Sophisticated HVAC noise modeling with specialized engines
4. **Version Control**: Drawing comparison and change tracking capabilities
5. **Equipment Integration**: OCR-based mechanical schedule import and management
6. **Comprehensive Reporting**: Professional Excel export with detailed analysis

### Recommended Next Steps

For organizations implementing the tool:

1. **Production Deployment**: The application is ready for professional use
2. **User Training**: Familiarize teams with advanced HVAC and comparison features
3. **Integration Planning**: Consider integration with existing CAD workflows
4. **Custom Extensions**: Leverage the modular architecture for organization-specific needs

The Acoustic Analysis Tool has evolved into a comprehensive, professional-grade application that significantly exceeds the original MVP requirements while maintaining ease of use and reliability.
