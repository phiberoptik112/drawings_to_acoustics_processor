# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**Acoustic Analysis Tool** - A professional desktop application for LEED acoustic certification analysis. Built with PySide6, this tool processes architectural PDF drawings and performs comprehensive acoustic calculations including RT60 reverberation time analysis and HVAC mechanical background noise evaluation.

## Project Status

**MVP COMPLETE** ✅ - Full working application with all core features implemented:

- ✅ **Phase 1**: Project structure, database models, splash screen, dashboard
- ✅ **Phase 2**: PDF viewer, drawing overlay system, scale management, drawing tools  
- ✅ **Phase 3**: Room properties dialog, RT60 calculations, space conversion
- ✅ **Phase 4**: HVAC noise calculations, NC rating analysis, Excel export
- ✅ **Final**: Results dashboard, comprehensive testing
- ✅ **Enhancement**: Acoustic materials database integration with 1,339+ materials
- ✅ **Advanced Feature**: Frequency-based material search system with treatment analysis
- ✅ **Deployment**: Windows executable build system with git-based versioning

## Development Setup

**Prerequisites:**
- Python 3.8+ 
- Virtual environment (recommended)
- All dependencies listed in `requirements.txt`

**Installation:**
```bash
# Create and activate virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Run the application
python src/main.py

# Run MVP tests
python test_mvp.py
```

**Virtual Environment Management:**
```bash
# Activate virtual environment
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Deactivate when done
deactivate

# Update requirements (if needed)
pip freeze > requirements.txt
```

**Key Dependencies:**
- PySide6 (GUI framework)
- SQLAlchemy (database ORM)
- PyMuPDF (PDF processing)
- openpyxl (Excel export)
- numpy, scipy (scientific computing)

## Architecture Overview

**Modular Architecture:**
```
src/
├── main.py                 # Application entry point
├── models/                 # SQLAlchemy database models
│   ├── database.py         # Database setup and session management
│   ├── project.py          # Project and drawing models
│   ├── space.py           # Space and room boundary models
│   └── hvac.py            # HVAC components, paths, segments
├── ui/                    # User interface components
│   ├── splash_screen.py   # Project selection interface
│   ├── project_dashboard.py # Main project management
│   ├── drawing_interface.py # PDF viewer with drawing tools
│   ├── results_widget.py   # Comprehensive results display
│   └── dialogs/           # Room properties, scale dialogs
├── drawing/               # PDF and drawing functionality
│   ├── pdf_viewer.py      # PyMuPDF PDF viewer
│   ├── drawing_overlay.py # Transparent drawing overlay
│   ├── drawing_tools.py   # Rectangle, component, segment tools
│   └── scale_manager.py   # Coordinate transformation
├── calculations/          # Acoustic calculation engines
│   ├── rt60_calculator.py # RT60 reverberation time
│   ├── noise_calculator.py # HVAC noise analysis
│   ├── hvac_path_calculator.py # Path management system
│   └── nc_rating_analyzer.py # NC rating compliance
└── data/                  # Standard libraries and export
    ├── components.py      # HVAC component library
    ├── materials.py       # Acoustic materials database integration
    └── excel_exporter.py  # Professional Excel export
materials/                 # External acoustic materials database
└── acoustic_materials.db  # SQLite database with 1,339+ materials
```

## Core Features

**Professional Calculation Engines:**
- **RT60 Analysis**: Sabine/Eyring formulas with comprehensive materials database (1,339+ materials)
- **Frequency-Specific Analysis**: Octave band calculations (125Hz - 4000Hz) with frequency-dependent absorption coefficients
- **HVAC Noise**: Path-based noise transmission with duct attenuation
- **NC Rating**: Octave band analysis and standards compliance
- **Scale Management**: Accurate coordinate transformation from PDF drawings

**Advanced User Interface:**
- **PDF Viewer**: Full-featured with zoom, navigation, coordinate mapping
- **Drawing Tools**: Rectangle (rooms), Component (HVAC), Segment (ducts), Measurement
- **Database Persistence**: All elements saved with complete reconstruction
- **Results Dashboard**: Comprehensive analysis display with real-time updates
- **Excel Export**: Professional multi-sheet reports with formatting
- **Advanced Material Search**: Frequency-based analysis with interactive graphs and treatment recommendations

**Professional Standards:**
- LEED acoustic certification requirements
- NC rating compliance for different space types
- Industry-standard material absorption coefficients with frequency-dependent data
- Comprehensive acoustic materials database (1,339+ materials from professional sources)
- HVAC component noise levels and duct attenuation

## Commands

**Primary Commands:**
```bash
# Activate virtual environment first
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Launch application
python src/main.py

# Run comprehensive tests
python test_mvp.py

# Development testing (components only)
python src/test_structure.py
```

**Windows Deployment Commands:**
```bash
# Build Windows executable
cd build
python build.py

# Or use batch script
build.bat

# Test deployment
python test_deployment.py

# User deployment setup
deploy.bat
```

**Database Operations:**
- SQLite database automatically created on first run
- Database location: `projects.db` in application directory
- Acoustic materials database: `materials/acoustic_materials.db` (1,339+ materials)
- Full CRUD operations through UI
- Export/backup via Excel functionality

**Acoustic Calculations:**
- RT60: Automatic calculation when space properties defined with frequency-specific coefficients
- Material Selection: 1,339+ professional acoustic materials with NRC and octave band data
- HVAC Noise: Path analysis from drawn components and segments  
- NC Rating: Compliance checking against space type standards
- Results: Real-time updates with validation and warnings

## Workflow

**Typical User Workflow:**
1. **Project Setup**: Create new project or load existing
2. **Import Drawings**: Load architectural PDF plans
3. **Set Scale**: Calibrate drawing scale for accurate measurements
4. **Draw Rooms**: Use rectangle tool to define space boundaries
5. **Define Spaces**: Convert rectangles to acoustic spaces with materials
6. **Place HVAC**: Add components (AHU, VAV, diffusers) and connect with segments
7. **Calculate**: Perform RT60 and HVAC noise analysis
8. **Review Results**: Use comprehensive results dashboard
9. **Export**: Generate professional Excel reports

## Testing

**MVP Test Coverage:**
- ✅ Core module imports
- ✅ Database operations (CRUD)
- ✅ RT60 calculation engine
- ✅ HVAC noise calculation engine  
- ✅ NC rating analysis
- ✅ Data libraries (components, materials, fittings)
- ✅ Excel export functionality
- ✅ GUI component initialization

**Run Tests:**
```bash
python test_mvp.py
```

## Implementation Status

**✅ All Phases Complete:**

**Phase 1 - Foundation (Complete):**
- Project structure and PySide6 foundation
- SQLAlchemy database with comprehensive models
- Splash screen and project dashboard
- Standard component/materials libraries

**Phase 2 - PDF Viewer & Drawing Tools (Complete):**
- PyMuPDF PDF viewer integration
- Drawing interface with overlay system
- Rectangle, component, segment, and measurement tools
- Scale management and coordinate calculation

**Phase 3 - Room Properties & RT60 (Complete):**
- Room properties dialog with comprehensive material selection (1,339+ materials)
- Height input and volume calculation
- Database persistence for drawn elements
- RT60 calculation engine with frequency-dependent materials database

**Phase 4 - HVAC Noise & NC Rating (Complete):**
- HVAC noise calculation engine
- Component noise database and segment attenuation
- Path-based noise calculation with NC rating conversion
- Advanced NC rating analyzer with octave band processing

**Final Phase - Export & Results (Complete):**
- Comprehensive Excel export functionality
- Professional results dashboard with real-time updates
- MVP testing suite with full coverage
- Complete project documentation

**Enhancement Phase - Materials Database Integration (Complete):**
- Integration of comprehensive acoustic materials database (1,339+ materials)
- Frequency-dependent absorption coefficients (125Hz - 4000Hz)
- NRC (Noise Reduction Coefficient) support
- Automatic material categorization and filtering
- Enhanced RT60 calculations with professional materials data

## Key Technical Implementation

**Database Models:**
- `Project`: Main project container with settings and metadata
- `Drawing`: PDF drawings with scale information and element storage
- `Space`: Acoustic spaces with RT60 calculations and material assignments
- `RoomBoundary`: Rectangle boundaries drawn on PDFs with area calculations
- `HVACComponent`: Equipment placed on drawings (AHU, VAV, diffusers, etc.)
- `HVACPath`: Complete air paths from source to terminal with noise calculations
- `HVACSegment`: Individual duct segments with attenuation properties
- `SegmentFitting`: Fittings within segments (elbows, tees, etc.)

**Calculation Engines:**
- **RT60Calculator**: Professional reverberation time using Sabine/Eyring formulas with frequency-specific coefficients
- **NoiseCalculator**: HVAC noise transmission with distance and duct losses
- **HVACPathCalculator**: Complete path management and analysis system
- **NCRatingAnalyzer**: Advanced NC rating with octave band processing

**Professional Libraries:**
- 8 standard HVAC components with typical noise levels
- 1,339+ acoustic materials with frequency-dependent absorption coefficients (125Hz-4000Hz)
- Material categorization: 271 ceiling, 952 wall, 116 floor materials
- NRC (Noise Reduction Coefficient) data for all materials
- 6 room type defaults for quick professional setup
- Standard duct sizes, shapes, and fitting noise adjustments

## Windows Deployment System

**Professional Executable Distribution:**
- **PyInstaller-based**: Single executable with bundled dependencies
- **Git-integrated Versioning**: Automatic build numbers from git commits
- **Database Bundling**: 1,339+ materials database travels with application
- **User Data Persistence**: Projects stored in Documents/AcousticAnalysis
- **Automated Testing**: Comprehensive deployment validation suite
- **Professional Metadata**: Version info embedded in executable

**Build System Components:**
```
build/
├── build.py              # Main build script with git versioning
├── build_spec.py         # PyInstaller configuration 
├── build.bat            # Windows build batch script
├── deploy.bat           # User deployment script
├── test_deployment.py   # Build validation tests
└── deploy/
    ├── AcousticAnalysisTool.exe  # Built executable
    └── README_INSTALL.txt        # User instructions
```

**User Experience:**
- **Single-click Installation**: No additional software required
- **Portable Application**: Can run from any Windows location
- **Automatic Setup**: User data directories created on first run
- **Version Display**: Build info shown in application UI
- **Professional Uninstaller**: Clean removal with data preservation

**Distribution Ready:**
- **Target**: Windows 10/11 (64-bit)
- **Size**: ~100-200 MB self-contained executable
- **Requirements**: No additional installations needed
- **Testing**: Automated validation of all components
- **Support**: Complete installation and troubleshooting documentation

## Notes for Future Development

**Potential Enhancements:**
- **3D Visualization**: Room acoustics visualization with ray tracing
- **Advanced Materials**: Custom material definitions and frequency analysis
- **Batch Processing**: Multiple drawing analysis and comparison
- **Cloud Integration**: Project sharing and collaboration features
- **Mobile Companion**: Field measurement integration and data collection
- **AI Integration**: Automatic space detection and acoustic optimization
- **Real-time Collaboration**: Multi-user project editing
- **Advanced Reporting**: Custom report templates and automated compliance checking

**Code Quality:**
- Comprehensive error handling throughout application
- Professional UI with consistent styling and user experience
- Modular architecture for easy extension and maintenance
- Database-backed persistence with complete data integrity
- Industry-standard calculations with validation and warnings
- Export capabilities for professional reporting and documentation
- Complete test coverage for all major functionality
- Professional deployment system with automated building and validation