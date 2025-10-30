"""
PyInstaller spec file for Acoustic Analysis Tool - macOS Version
Configured for macOS .app bundle deployment with database bundling
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
icon_path = str(project_root / "resources" / "icon.icns") if (project_root / "resources" / "icon.icns").exists() else None

# Collect data files
datas = [
    # Bundle the acoustic materials database
    (str(materials_path / "acoustic_materials.db"), "materials"),
    # Bundle any CSV files in materials directory
    (str(materials_path / "*.csv"), "materials"),
    # Bundle version info (will be generated during build)
    (str(project_root / "src" / "version.py"), "."),
]

# Add any resource files if they exist
resources_path = project_root / "resources"
if resources_path.exists():
    for file_pattern in ["*.png", "*.jpg", "*.icns", "*.svg"]:
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

# Binaries - additional libraries that might be needed
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
    [],
    exclude_binaries=True,
    name='AcousticAnalysisTool',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,  # Compress executable
    console=False,  # GUI application
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=icon_path
)

# Collect all files for the .app bundle
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

# Create macOS .app bundle
app = BUNDLE(
    coll,
    name='AcousticAnalysisTool.app',
    icon=icon_path,
    bundle_identifier='com.acousticsolutions.acousticanalysistool',
    info_plist={
        'NSPrincipalClass': 'NSApplication',
        'NSHighResolutionCapable': 'True',
        'CFBundleName': 'Acoustic Analysis Tool',
        'CFBundleDisplayName': 'Acoustic Analysis Tool',
        'CFBundleShortVersionString': '1.0.0',
        'CFBundleVersion': '1.0.0',
        'CFBundlePackageType': 'APPL',
        'CFBundleSignature': '????',
        'CFBundleExecutable': 'AcousticAnalysisTool',
        'CFBundleIdentifier': 'com.acousticsolutions.acousticanalysistool',
        'LSMinimumSystemVersion': '10.13.0',
        'NSRequiresAquaSystemAppearance': False,
        'CFBundleDocumentTypes': [
            {
                'CFBundleTypeName': 'Acoustic Analysis Project',
                'CFBundleTypeRole': 'Editor',
                'LSHandlerRank': 'Owner',
                'LSItemContentTypes': ['com.acousticsolutions.project']
            }
        ],
        'UTExportedTypeDeclarations': [
            {
                'UTTypeConformsTo': ['public.data'],
                'UTTypeDescription': 'Acoustic Analysis Project',
                'UTTypeIdentifier': 'com.acousticsolutions.project',
                'UTTypeTagSpecification': {
                    'public.filename-extension': ['aap']
                }
            }
        ]
    }
)

