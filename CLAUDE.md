# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**Acoustic Analysis Tool** - A desktop application for LEED acoustic certification analysis built with PyQt5. The system processes architectural drawings (PDFs) and performs acoustic calculations including RT60 reverberation time and HVAC mechanical background noise analysis.

## Project Status - Phase 3 Complete ✅

**Phase 1 MVP Foundation (Weeks 1-2): COMPLETE**
- ✅ Complete PyQt5 application structure with SQLAlchemy database
- ✅ Project management system with splash screen and dashboard
- ✅ Database models for projects, drawings, spaces, and HVAC systems
- ✅ Standard component and materials libraries
- ✅ Professional UI with project creation and management

**Phase 2 PDF Viewer & Drawing Tools (Weeks 3-4): COMPLETE**
- ✅ PyMuPDF PDF viewer with zoom, navigation, and page controls
- ✅ Drawing overlay system with transparent tool layer
- ✅ Rectangle tool for room boundary drawing with real-world area calculation
- ✅ Component placement tool with standard HVAC component library
- ✅ Segment drawing tool for duct connections with length calculation
- ✅ Measurement tool with scale-accurate distance conversion
- ✅ Scale management system with multiple calibration methods
- ✅ Professional drawing interface with toolbar and element management

**Phase 3 Room Properties & RT60 Calculations (Weeks 5-6): COMPLETE**
- ✅ Room properties dialog with material selection and volume calculation
- ✅ RT60 calculation engine using Sabine and Eyring formulas
- ✅ Database persistence for all drawn elements with JSON properties
- ✅ Room-to-space conversion system with acoustic material assignment
- ✅ Real-time RT60 calculation with visual feedback and target comparison
- ✅ Element management with context menus and drawing persistence
- ✅ Material database with absorption coefficients and room type presets

**Current Architecture:**
- **Framework**: PyQt5 desktop application with drawing overlay system
- **Database**: SQLite with SQLAlchemy ORM and JSON properties for element storage
- **PDF Processing**: PyMuPDF for viewing and coordinate mapping
- **Drawing Tools**: Modular tool system (Rectangle, Component, Segment, Measure)
- **Scale System**: Coordinate transformation and real-world measurements
- **Calculations**: RT60 engine with Sabine/Eyring formulas and materials database
- **Persistence**: Element save/load system with overlay reconstruction
- **Models**: Segment-based HVAC paths, rectangle-based room boundaries, space-material assignments
- **Libraries**: Standard HVAC components, acoustic materials, and room type presets

## Development Setup

**Prerequisites:**
- Python 3.7 or higher
- pip package manager

**Installation Commands:**
```bash
# Quick setup test (no dependencies needed)
python test_structure.py

# Install all dependencies
python install_dev.py
# OR manually:
pip install -r requirements.txt

# Run the application
cd src
python main.py
```

**Dependencies (requirements.txt):**
- PyQt5>=5.15.7 (GUI framework)
- SQLAlchemy>=1.4.0 (Database ORM)
- PyMuPDF>=1.21.0 (PDF processing - Phase 2)
- openpyxl>=3.0.10 (Excel export - Phase 4)
- numpy>=1.21.0, scipy>=1.7.0 (Calculations - Phase 4)

## Architecture Notes

**Database Structure (SQLAlchemy Models):**
- `Project`: Main project container with settings
- `Drawing`: PDF drawings with scale information  
- `Space`: Rooms/spaces for acoustic analysis with RT60 calculations
- `RoomBoundary`: Rectangle boundaries drawn on PDFs
- `HVACComponent`: Equipment placed on drawings (AHU, VAV, diffusers)
- `HVACPath`: Complete air paths from source to terminal
- `HVACSegment`: Individual duct segments between components
- `SegmentFitting`: Fittings within segments (elbows, tees, etc.)

**UI Structure:**
- `SplashScreen`: Project selection and creation
- `ProjectDashboard`: Main project management interface
- `DrawingInterface`: PDF viewer with drawing tools (Phase 2)
- `ProjectDialog`: New project creation dialog

**Standard Libraries:**
- 8 HVAC components with typical noise levels
- 17 acoustic materials with absorption coefficients
- 6 room type defaults for quick setup
- Standard duct sizes and fittings

## Commands

**Development:**
```bash
# Test project structure
python test_structure.py

# Install development environment
python install_dev.py

# Run application
cd src && python main.py

# Test database models (no PyQt5 needed)
python -c "from src.models import Project; print('Models working')"
```

**Application Usage:**
1. Start application: `python main.py` from src directory
2. Create new project or open existing
3. Project dashboard manages drawings, spaces, and HVAC paths
4. Import PDFs and draw room boundaries (Phase 2)
5. Place HVAC components and draw segments (Phase 3)
6. Calculate RT60 and noise levels (Phase 4-5)
7. Export results to Excel (Phase 6)

## Implementation Status

**✅ Phase 1 Complete:**
- Project structure and PyQt5 foundation
- SQLAlchemy database with all models
- Splash screen and project dashboard
- Standard component/materials libraries

**✅ Phase 2 Complete:**
- PyMuPDF PDF viewer integration
- Drawing interface with overlay system
- Rectangle, component, segment, and measurement tools
- Scale management and coordinate calculation

**✅ Phase 3 Complete:**
- Room properties dialog with material selection
- Height input and volume calculation
- Database persistence for drawn elements
- RT60 calculation engine with materials database

**🔄 Phase 4 Next (Weeks 7-8):**
- HVAC noise calculation engine
- Component noise database and segment attenuation
- Path-based noise calculation with NC rating conversion
- Integration with RT60 results for complete acoustic analysis

**📋 Remaining Phases:**
- Phase 4: HVAC noise calculation engine and NC rating conversion
- Phase 5: Excel export functionality and results display
- Phase 6: Final integration, testing, and MVP completion

## Notes for Future Development

**Technical Approach:**
- Segment-based HVAC modeling for accurate path calculations
- Rectangle-based room definitions for simple area calculations
- Scale-accurate measurements from PDF coordinates
- Modular calculation engines (RT60, noise) for extensibility

**Key Files to Understand:**
- `src/main.py`: Application entry point
- `src/models/`: Database schema and relationships
- `src/ui/project_dashboard.py`: Main project interface
- `src/ui/drawing_interface.py`: PDF viewer and drawing tools
- `src/ui/dialogs/room_properties.py`: Room creation and material selection
- `src/drawing/`: PDF viewer, drawing tools, and scale management
- `src/calculations/`: RT60 and acoustic calculation engines
- `src/data/`: Standard component and materials libraries
- `prd.md`: Complete product requirements document

**Development Guidelines:**
- Follow existing PyQt5 patterns and styling
- Use SQLAlchemy session management (`get_session()`)
- Import standard libraries from `src/data/`
- Maintain segment-based approach for HVAC paths
- Keep rectangle-based approach for room boundaries