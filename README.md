# Acoustic Analysis Tool

Desktop application for LEED acoustic certification analysis built with PySide6.

## Features (MVP Complete) ✅

✅ **Project Management**
- Create and load acoustic analysis projects
- SQLite database with complete project persistence
- Recent projects display on splash screen
- Multi-project workflow support

✅ **PDF Viewer & Drawing Tools**
- Full-featured PDF viewer with zoom and navigation
- Drawing overlay system with coordinate mapping
- Rectangle tool for room boundaries with area calculation
- HVAC component placement (AHU, VAV, diffusers, etc.)
- Duct segment drawing with connection management
- Measurement tool for scale calibration
- Scale manager with accurate coordinate transformation

✅ **Room Properties & Acoustic Analysis**
- Room properties dialog with material selection
- Height input and volume calculations
- RT60 reverberation time analysis using Sabine/Eyring formulas
- Professional acoustic materials database (17 materials)
- Space type defaults for LEED certification

✅ **HVAC Noise Analysis**
- Path-based HVAC noise calculation engine
- Component noise database with typical sound levels
- Duct segment attenuation calculations
- NC rating analysis with octave band processing
- Complete air path modeling from source to terminal

✅ **Results & Export**
- Comprehensive results dashboard with real-time updates
- Professional Excel export with multi-sheet reports
- Validation and warning systems
- Standards compliance checking

✅ **Database Persistence**
- Complete SQLAlchemy models for all project elements
- Full CRUD operations through UI
- Drawing element reconstruction
- Project backup and recovery

## Installation

### Prerequisites

- Python 3.8 or higher
- pip package manager

### Setup

1. Clone or download this project
2. Install dependencies:

```bash
pip install -r requirements.txt
```

### Running the Application

```bash
python src/main.py
```


## Development Status

### ✅ MVP Complete - All Phases Finished

**Phase 1 - Foundation (Complete):**

- [x] PySide6 application structure with professional UI
- [x] Splash screen with project creation/loading
- [x] SQLAlchemy database with comprehensive models
- [x] Project dashboard with multi-tab interface
- [x] Standard component and materials libraries

**Phase 2 - PDF Viewer & Drawing Tools (Complete):**

- [x] PyMuPDF PDF viewer integration with full navigation
- [x] Drawing interface with transparent overlay system
- [x] Rectangle, component, segment, and measurement tools
- [x] Scale management with coordinate transformation
- [x] Database persistence for all drawn elements

**Phase 3 - Room Properties & RT60 (Complete):**

- [x] Room properties dialog with material selection
- [x] Height input and volume calculations
- [x] RT60 calculation engine with Sabine/Eyring formulas
- [x] Professional acoustic materials database
- [x] Space conversion from rectangles to acoustic spaces

**Phase 4 - HVAC Noise & NC Rating (Complete):**

- [x] HVAC component placement and noise database
- [x] Duct segment drawing with attenuation calculations
- [x] Path-based noise calculation engine
- [x] NC rating analysis with octave band processing
- [x] Complete air path modeling and analysis

**Final Phase - Export & Results (Complete):**

- [x] Comprehensive Excel export with professional formatting
- [x] Results dashboard with real-time calculation updates
- [x] Validation and warning systems
- [x] Complete MVP testing suite

## Usage

### Complete Workflow

1. **Start Application**: Run `python src/main.py`
2. **Create Project**: Click "New Project" and fill in project details
3. **Import Drawings**: Load architectural PDF plans
4. **Set Scale**: Use measurement tool to calibrate drawing scale
5. **Draw Rooms**: Use rectangle tool to define space boundaries
6. **Define Spaces**: Convert rectangles to acoustic spaces with materials
7. **Place HVAC**: Add components (AHU, VAV, diffusers) and connect with segments
8. **Calculate**: Perform RT60 and HVAC noise analysis
9. **Review Results**: Use comprehensive results dashboard
10. **Export**: Generate professional Excel reports

### Testing

```bash
# Run comprehensive MVP tests
python test_mvp.py

# Run development structure tests
python src/test_structure.py
```

## Technical Details

### Key Technologies

- **Framework**: PySide6 for professional desktop GUI
- **Database**: SQLite with SQLAlchemy ORM for complete persistence
- **PDF Processing**: PyMuPDF for full-featured PDF viewer
- **Export**: openpyxl for professional Excel reports
- **Calculations**: NumPy/SciPy for acoustic analysis
- **Architecture**: Modular design with separated calculation engines

### Professional Standards

- LEED acoustic certification requirements
- NC rating compliance for different space types
- Industry-standard material absorption coefficients
- HVAC component noise levels and duct attenuation
- Sabine/Eyring RT60 calculation formulas

## Architecture

### Modular Structure

```text
src/
├── main.py                 # Application entry point
├── models/                 # SQLAlchemy database models
│   ├── database.py         # Database setup and session management
│   ├── project.py          # Project and drawing models
│   ├── space.py            # Space and room boundary models
│   └── hvac.py             # HVAC components, paths, segments
├── ui/                     # User interface components
│   ├── splash_screen.py    # Project selection interface
│   ├── project_dashboard.py# Main project management
│   ├── drawing_interface.py# PDF viewer with drawing tools
│   ├── results_widget.py   # Comprehensive results display
│   └── dialogs/            # Room properties, scale dialogs
├── drawing/                # PDF and drawing functionality
│   ├── pdf_viewer.py       # PyMuPDF PDF viewer
│   ├── drawing_overlay.py  # Transparent drawing overlay
│   ├── drawing_tools.py    # Rectangle, component, segment tools
│   └── scale_manager.py    # Coordinate transformation
├── calculations/           # Acoustic calculation engines
│   ├── rt60_calculator.py  # RT60 reverberation time
│   ├── noise_calculator.py # HVAC noise analysis
│   ├── hvac_path_calculator.py # Path management system
│   └── nc_rating_analyzer.py # NC rating compliance
└── data/                   # Standard libraries and export
    ├── components.py       # HVAC component library
    ├── materials.py        # Acoustic materials database
    └── excel_exporter.py   # Professional Excel export
```

### Professional Implementation

- Complete CRUD operations with database persistence
- Real-time calculation updates with validation
- Professional UI with consistent styling
- Industry-standard acoustic analysis algorithms
- Comprehensive error handling and user feedback
- Multi-sheet Excel export with professional formatting
