# Quick Start - Building Version 1.0

## Windows Users

```batch
# 1. Navigate to project
cd drawings_to_acoustics_processor

# 2. Run build
build\build.bat

# 3. Find executable
build\deploy\AcousticAnalysisTool.exe
```

## macOS Users

```bash
# 1. Navigate to project
cd drawings_to_acoustics_processor

# 2. Make scripts executable (first time only)
chmod +x build/build.sh build/deploy.sh

# 3. Run build
./build/build.sh

# 4. Find application
build/deploy/AcousticAnalysisTool.app
```

## Creating Installers

### Windows
```batch
build\deploy.bat
```
Creates professional installer with desktop shortcut option.

### macOS
```bash
./build/deploy.sh
```
Choose from:
- DMG (drag-to-Applications installer)
- ZIP (simple archive)
- Both

## Testing the Build

```bash
# Test database bundling
python build/test_database_bundling.py
```

## What Gets Bundled

✅ Python runtime  
✅ All dependencies (PySide6, numpy, pandas, matplotlib, etc.)  
✅ Acoustic materials database (1,383 materials)  
✅ Application resources  

## Build Outputs

**Windows:** `AcousticAnalysisTool.exe` (~150-200 MB)  
**macOS:** `AcousticAnalysisTool.app` (~150-200 MB)

## Need Help?

See full documentation: `build/README_BUILD.md`

