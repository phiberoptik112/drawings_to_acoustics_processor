"""
PyInstaller spec file for Acoustic Analysis Tool
Configured for Windows executable deployment with database bundling
"""

import os
import sys
from PyInstaller.utils.hooks import collect_data_files, collect_submodules
from pathlib import Path

# Get the project root directory
project_root = Path(__file__).parent.parent.absolute()
src_path = project_root / "src"
materials_path = project_root / "materials"

# Add src to path for imports
sys.path.insert(0, str(src_path))

# Define paths
main_script = str(src_path / "main.py")
icon_path = str(project_root / "resources" / "icon.ico") if (project_root / "resources" / "icon.ico").exists() else None

# Collect data files
datas = [
    # Bundle version info (will be generated during build)
    (str(project_root / "src" / "version.py"), "."),
]

# Bundle the acoustic materials database (if it exists)
# For "Build Machine Only" workflow: database may not exist on dev machines
db_path = materials_path / "acoustic_materials.db"
if db_path.exists():
    datas.append((str(db_path), "materials"))
    print(f"✓ Including materials database in bundle: {db_path}")
else:
    print(f"⚠ Warning: Materials database not found at {db_path}")
    print("  Building without proprietary materials database (dev build)")

# Bundle any CSV files in materials directory (if they exist)
csv_files = list(materials_path.glob("*.csv"))
if csv_files:
    for csv_file in csv_files:
        datas.append((str(csv_file), "materials"))
        print(f"✓ Including CSV file: {csv_file}")

# Add any resource files if they exist
resources_path = project_root / "resources"
if resources_path.exists():
    for file_pattern in ["*.png", "*.jpg", "*.ico", "*.svg"]:
        datas.append((str(resources_path / file_pattern), "resources"))

# Hidden imports - modules that PyInstaller might miss
hiddenimports = [
    # PySide6 modules
    'PySide6.QtCore',
    'PySide6.QtWidgets', 
    'PySide6.QtGui',
    'PySide6.QtPrintSupport',
    
    # SQLAlchemy and database modules
    'sqlalchemy.sql.default_comparator',
    'sqlalchemy.ext.declarative',
    'sqlalchemy.orm',
    'sqlalchemy.pool',
    
    # PyMuPDF
    'fitz',
    
    # Scientific computing
    'numpy',
    'scipy',
    'scipy.sparse.csgraph._validation',
    'pandas',
    
    # Plotting
    'matplotlib',
    'matplotlib.backends.backend_qt5agg',
    'seaborn',
    
    # Excel export
    'openpyxl',
    'openpyxl.workbook',
    'openpyxl.worksheet',
    
    # Date utilities
    'dateutil',
    'dateutil.relativedelta',
    
    # Application modules
    'models.database',
    'models.project',
    'models.space',
    'models.hvac',
    'data.materials',
    'data.components',
    'calculations.rt60_calculator',
    'calculations.noise_calculator',
]

# Binaries - additional DLLs that might be needed
binaries = []

# Exclude unnecessary modules to reduce size
excludes = [
    'tkinter',
    'unittest',
    'test',
    'curses',
    'PyQt5',
    'PyQt6',
    'django',
    'flask',
    'tornado',
]

# Analysis configuration
a = Analysis(
    [main_script],
    pathex=[str(src_path)],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=excludes,
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=None,
    noarchive=False
)

# Remove duplicate files
pyz = PYZ(a.pure, a.zipped_data, cipher=None)

# Create executable
exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='AcousticAnalysisTool',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,  # Compress executable
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,  # Windows GUI application
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=icon_path,
    version='file_version_info.txt'  # Will be generated during build
)

# Create directory structure for distribution
coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='AcousticAnalysisTool'
)