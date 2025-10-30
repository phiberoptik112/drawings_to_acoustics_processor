# Acoustic Analysis Tool - Build & Deployment Guide

Complete guide for building and deploying the Acoustic Analysis Tool on Windows and macOS platforms using PyInstaller.

## Table of Contents

- [Overview](#overview)
- [Prerequisites](#prerequisites)
- [Quick Start](#quick-start)
- [Platform-Specific Instructions](#platform-specific-instructions)
  - [Windows Build](#windows-build)
  - [macOS Build](#macos-build)
- [Build System Architecture](#build-system-architecture)
- [Database Bundling](#database-bundling)
- [Testing the Build](#testing-the-build)
- [Troubleshooting](#troubleshooting)
- [Distribution](#distribution)

---

## Overview

The Acoustic Analysis Tool uses **PyInstaller** to create standalone executables that include:
- Python runtime environment
- All required dependencies (PySide6, numpy, pandas, matplotlib, etc.)
- Acoustic materials database (1,383+ materials)
- Application resources and assets

**Build outputs:**
- **Windows**: `AcousticAnalysisTool.exe` (standalone executable)
- **macOS**: `AcousticAnalysisTool.app` (application bundle)

---

## Prerequisites

### Common Requirements (Both Platforms)

1. **Python 3.11+** installed and accessible from command line
2. **Git** for version control (used for build numbering)
3. **Virtual environment** (recommended):
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate  # macOS/Linux
   # or
   .venv\Scripts\activate     # Windows
   ```

4. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   pip install -r build/requirements-build.txt
   ```

### Windows-Specific Requirements

- Windows 10 or later
- No additional requirements (PyInstaller handles everything)

### macOS-Specific Requirements

- macOS 10.13 (High Sierra) or later
- Xcode Command Line Tools:
  ```bash
  xcode-select --install
  ```
- **Optional but recommended** for professional DMG creation:
  ```bash
  brew install create-dmg
  ```

---

## Quick Start

### Windows

```batch
# Navigate to project root
cd drawings_to_acoustics_processor

# Run build (will install requirements automatically)
build\build.bat

# Or run build script directly
python build\build.py

# Find executable at:
build\deploy\AcousticAnalysisTool.exe
```

### macOS

```bash
# Navigate to project root
cd drawings_to_acoustics_processor

# Make scripts executable (first time only)
chmod +x build/build.sh build/deploy.sh

# Run build
./build/build.sh

# Find application at:
build/deploy/AcousticAnalysisTool.app
```

---

## Platform-Specific Instructions

### Windows Build

#### Step 1: Prepare Environment

```batch
# Create and activate virtual environment
python -m venv .venv
.venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
pip install -r build\requirements-build.txt
```

#### Step 2: Run Build

```batch
# Option A: Use batch file (recommended)
build\build.bat

# Option B: Run Python script directly
python build\build.py
```

#### Step 3: Build Output

The build process creates:
```
build/
  deploy/
    AcousticAnalysisTool.exe    # Standalone executable (~150-200 MB)
    build_info.json              # Build metadata
```

#### Step 4: Create Installer (Optional)

```batch
# Run deployment script to create installer
build\deploy.bat
```

This creates a user-friendly installer with:
- Desktop shortcut option
- Start menu entry
- Install directory selection
- Uninstaller

### macOS Build

#### Step 1: Prepare Environment

```bash
# Create and activate virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt
pip install -r build/requirements-build.txt
```

#### Step 2: Run Build

```bash
# Make script executable (first time only)
chmod +x build/build.sh

# Run build
./build/build.sh
```

#### Step 3: Build Output

The build process creates:
```
build/
  deploy/
    AcousticAnalysisTool.app/   # Application bundle (~150-200 MB)
      Contents/
        MacOS/
          AcousticAnalysisTool  # Executable
        Resources/
          materials/
            acoustic_materials.db
        Info.plist
    build_info.json             # Build metadata
```

#### Step 4: Create DMG Installer (Optional)

```bash
# Make script executable (first time only)
chmod +x build/deploy.sh

# Run deployment script
./build/deploy.sh
```

Choose deployment format:
1. **DMG** (Disk Image) - Professional installer with drag-to-Applications
2. **ZIP** - Simple archive for distribution
3. **Both** - Create both formats

Output:
- `build/deploy/AcousticAnalysisTool-macOS.dmg` (if DMG selected)
- `build/deploy/AcousticAnalysisTool-macOS.zip` (if ZIP selected)

---

## Build System Architecture

### File Structure

```
build/
  ├── build.py                  # Main build orchestration script
  ├── build.bat                 # Windows build launcher
  ├── build.sh                  # macOS build launcher
  ├── build_spec.py             # PyInstaller spec for Windows
  ├── build_spec_macos.py       # PyInstaller spec for macOS
  ├── deploy.bat                # Windows deployment script
  ├── deploy.sh                 # macOS deployment script
  ├── version_template.py       # Version file template
  ├── requirements-build.txt    # Build dependencies
  ├── test_database_bundling.py # Database bundling verification
  └── README_BUILD.md           # This file
```

### Build Process Flow

1. **Platform Detection**
   - Automatically detects Windows/macOS/Linux
   - Selects appropriate spec file and build parameters

2. **Version Generation**
   - Reads git commit information
   - Generates `src/version.py` with build metadata
   - Creates Windows version info (Windows only)

3. **PyInstaller Execution**
   - Uses platform-specific spec file
   - Bundles Python runtime and dependencies
   - Includes materials database and resources

4. **Package Creation**
   - Windows: Copies executable to deploy directory
   - macOS: Copies .app bundle to deploy directory
   - Generates build_info.json metadata file

5. **Validation**
   - Checks file size is reasonable
   - Verifies bundle structure (macOS)
   - Validates executable exists

---

## Database Bundling

The acoustic materials database is **automatically bundled** into the executable.

### Database Details

- **File**: `materials/acoustic_materials.db` (SQLite3)
- **Size**: ~300 KB
- **Materials**: 1,383 acoustic materials with frequency-specific absorption coefficients
- **Format**: SQLite3 database with `acoustic_materials` table

### How It Works

1. **Spec File Configuration**
   ```python
   # In build_spec.py and build_spec_macos.py
   datas = [
       (str(materials_path / "acoustic_materials.db"), "materials"),
   ]
   ```

2. **Runtime Path Resolution**
   ```python
   # In src/utils.py
   def get_materials_database_path():
       if is_bundled_executable():
           # Running as bundled app - use PyInstaller temp directory
           return get_resource_path("materials/acoustic_materials.db")
       else:
           # Running from source - use project materials folder
           return get_resource_path("materials/acoustic_materials.db")
   ```

3. **Loading in Application**
   ```python
   # In src/data/materials.py
   from utils import get_materials_database_path
   db_path = get_materials_database_path()
   conn = sqlite3.connect(db_path)
   ```

### Testing Database Bundling

Run the test script to verify database bundling configuration:

```bash
# From project root
python build/test_database_bundling.py
```

Expected output:
```
✓ All tests passed! Database bundling is working correctly.
```

The test verifies:
- Database path resolution in development mode
- Database file exists and is readable
- Materials can be loaded from database
- MaterialsDatabase class functions correctly
- All 1,383 materials are accessible

---

## Testing the Build

### Development Testing

Test the build system without creating a full build:

```bash
# Test database bundling
python build/test_database_bundling.py

# Verify git info extraction
git rev-parse HEAD
git rev-list --count HEAD
```

### Build Testing (Windows)

```batch
# 1. Build the executable
build\build.bat

# 2. Navigate to deploy directory
cd build\deploy

# 3. Run the executable
AcousticAnalysisTool.exe

# 4. Test key features:
#    - Application launches without errors
#    - Materials database loads (check material library)
#    - RT60 calculations work
#    - HVAC analysis functions
#    - Excel export works
```

### Build Testing (macOS)

```bash
# 1. Build the application
./build/build.sh

# 2. Open the application
open build/deploy/AcousticAnalysisTool.app

# 3. Test key features:
#    - Application launches without Gatekeeper issues
#    - Materials database loads (check material library)
#    - RT60 calculations work
#    - HVAC analysis functions
#    - Excel export works

# 4. Check logs for errors
# Console.app → Filter: AcousticAnalysisTool
```

### First-Time macOS Launch

On macOS, unsigned applications require special handling:

1. **Right-click** on `AcousticAnalysisTool.app`
2. Select **"Open"**
3. Click **"Open"** in the security dialog
4. Application will launch and be remembered as safe

Alternatively, allow in System Preferences:
```
System Preferences → Security & Privacy → General
→ Click "Open Anyway" next to the blocked app
```

---

## Troubleshooting

### Common Build Errors

#### Error: "PyInstaller not found"

**Solution:**
```bash
pip install -r build/requirements-build.txt
```

#### Error: "Git not found" or version info fails

**Solution:**
```bash
# Check git is installed
git --version

# If not, install git:
# Windows: Download from git-scm.com
# macOS: xcode-select --install
```

#### Error: "Materials database not found"

**Solution:**
Verify database exists at `materials/acoustic_materials.db`:
```bash
ls -lh materials/acoustic_materials.db
# Should show ~300 KB file
```

#### Windows: Antivirus Blocks Build

**Solution:**
- Add project folder to antivirus exclusions
- Temporarily disable real-time protection during build
- After build, scan executable and whitelist if needed

#### macOS: "Cannot verify developer"

**Solution for testing:**
```bash
# Remove quarantine attribute
xattr -cr build/deploy/AcousticAnalysisTool.app

# Or use right-click → Open method
```

**Solution for distribution:**
- Sign the application with Apple Developer certificate
- Notarize with Apple
- Staple notarization ticket

### Build Size Issues

**Expected sizes:**
- Windows: 150-250 MB executable
- macOS: 150-250 MB application bundle

**If size is too large (>500 MB):**
- Check for unnecessary files in datas
- Verify excludes list in spec file
- Remove unused dependencies

**If size is too small (<50 MB):**
- Dependencies may not be bundled
- Check hiddenimports in spec file
- Verify UPX compression isn't causing issues

### Runtime Errors

#### "Failed to load materials database"

**Debug steps:**
```python
# Add to application startup
from utils import log_environment_info
log_environment_info()
```

Check output shows correct database path and file exists.

#### Import Errors in Bundled App

**Solution:**
Add missing module to `hiddenimports` in spec file:
```python
hiddenimports = [
    # ... existing imports ...
    'missing.module.name',
]
```

Rebuild after modifying spec file.

---

## Distribution

### Windows Distribution

**Option 1: Direct Executable**
1. Distribute `AcousticAnalysisTool.exe` directly
2. Users double-click to run (no installation needed)
3. Consider packaging with README or instructions

**Option 2: Installer (Recommended)**
1. Run `build\deploy.bat` to create installer
2. Distribute the installer executable
3. Provides professional install experience

**Code Signing (Optional but Recommended):**
```batch
# Requires code signing certificate
signtool sign /f certificate.pfx /p password /t http://timestamp.digicert.com AcousticAnalysisTool.exe
```

Benefits:
- No "Unknown Publisher" warnings
- Improved trustworthiness
- Fewer antivirus false positives

### macOS Distribution

**Option 1: Application Bundle**
1. Distribute `AcousticAnalysisTool.app` in a ZIP file
2. Users extract and drag to Applications
3. Include instructions for first launch (right-click → Open)

**Option 2: DMG Installer (Recommended)**
1. Run `./build/deploy.sh` and select DMG option
2. Distribute the DMG file
3. Professional presentation with drag-to-Applications

**Code Signing & Notarization (Required for Easy Distribution):**

1. **Sign the application:**
   ```bash
   codesign --deep --force --verify --verbose \
     --sign "Developer ID Application: Your Name (TEAM_ID)" \
     --options runtime \
     build/deploy/AcousticAnalysisTool.app
   ```

2. **Create DMG:**
   ```bash
   ./build/deploy.sh
   ```

3. **Notarize the DMG:**
   ```bash
   xcrun notarytool submit AcousticAnalysisTool-macOS.dmg \
     --apple-id your@email.com \
     --team-id TEAM_ID \
     --password app-specific-password \
     --wait
   ```

4. **Staple notarization ticket:**
   ```bash
   xcrun stapler staple AcousticAnalysisTool-macOS.dmg
   ```

Benefits:
- No Gatekeeper warnings
- Professional distribution
- Works on latest macOS versions
- Users can simply double-click to install

---

## Version Information

Version numbers are automatically generated from git:

**Format:** `1.0.0.BUILD_NUMBER`

Where `BUILD_NUMBER` is the total number of commits in the repository.

**Example:** `1.0.0.347`

Build metadata includes:
- Git commit hash
- Build date and time
- Git branch name
- Platform information

View build info:
```bash
# In built application
cat build/deploy/build_info.json
```

---

## Support & Additional Resources

**Documentation:**
- Main README: `README.md`
- Deployment Guide: `build/README_DEPLOYMENT.md`
- This Build Guide: `build/README_BUILD.md`

**Testing:**
- Database bundling test: `build/test_database_bundling.py`
- Deployment test: `build/test_deployment.py`

**Scripts:**
- Windows build: `build/build.bat`
- macOS build: `build/build.sh`
- Windows deploy: `build/deploy.bat`
- macOS deploy: `build/deploy.sh`

For issues or questions, check the troubleshooting section above or review the build logs for specific error messages.

---

**Last Updated:** 2025-01-29  
**Version:** 1.0.0  
**Build System:** PyInstaller 5.13+

