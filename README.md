# Acoustic Analysis Tool

Desktop application for LEED acoustic certification analysis built with PySide6.

## Features (MVP Phase 1 Complete)

✅ **Project Management**
- Create and load acoustic analysis projects
- SQLite database with project persistence
- Recent projects display on splash screen

✅ **Project Dashboard**
- Multi-tab interface for drawings, spaces, and HVAC paths
- Component library display
- Analysis status tracking

✅ **Database Models**
- Complete SQLAlchemy models for projects, drawings, spaces, and HVAC systems
- Segment-based HVAC path modeling
- Room boundary definitions

✅ **Standard Libraries**
- Pre-built HVAC component library (AHU, VAV, diffusers, etc.)
- Acoustic materials database with absorption coefficients
- Room type defaults for quick setup

## Installation

### Prerequisites
- Python 3.7 or higher
- pip package manager

### Setup
1. Clone or download this project
2. Install dependencies:
```bash
pip install -r requirements.txt
```

### Running the Application
```bash
cd src
python main.py
```

## Project Structure

```
src/
├── main.py                 # Application entry point
├── models/                 # Database models (SQLAlchemy)
├── ui/                     # PyQt5 user interface
├── data/                   # Standard component/material libraries
├── calculations/           # Acoustic calculation engines (Phase 2)
├── drawing/                # PDF viewer and drawing tools (Phase 2)
└── utils/                  # Utilities and helpers (Phase 2)
```

## Development Status

### ✅ Phase 1 Complete (Weeks 1-2)
- [x] Basic PyQt5 application structure
- [x] Splash screen with project creation/loading
- [x] SQLAlchemy database setup with core tables
- [x] Project dashboard layout
- [x] Standard component and materials libraries

### 🔄 Phase 2 Next (Weeks 3-4)
- [ ] PDF viewer integration with PyMuPDF
- [ ] Drawing interface with overlay system
- [ ] Rectangle tool for room boundaries
- [ ] Basic scale input and coordinate mapping
- [ ] Room properties dialog

### 📋 Remaining Phases
- **Phase 3**: HVAC component placement and segment drawing
- **Phase 4**: RT60 calculator and materials assignment  
- **Phase 5**: Mechanical noise calculation engine
- **Phase 6**: Excel export and final integration

## Usage

1. **Start Application**: Run `python main.py` from the src directory
2. **Create Project**: Click "New Project" and fill in project details
3. **Project Dashboard**: View and manage drawings, spaces, and HVAC paths
4. **Next Phase**: Drawing interface and tools (coming next)

## Technical Details

- **Framework**: PySide6 for desktop GUI
- **Database**: SQLite with SQLAlchemy ORM
- **PDF Processing**: PyMuPDF (planned for Phase 2)
- **Export**: openpyxl for Excel output (planned for Phase 4)
- **Calculations**: NumPy/SciPy for acoustic analysis (planned for Phase 4-5)

## Development Notes

The application follows the PRD specification with a segment-based approach for HVAC paths and rectangle-based room definitions. The foundation is now complete and ready for Phase 2 implementation.