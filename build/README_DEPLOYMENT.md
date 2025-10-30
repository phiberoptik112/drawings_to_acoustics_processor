# Acoustic Analysis Tool - Windows Deployment System

This directory contains the complete Windows executable deployment system for the Acoustic Analysis Tool, a professional desktop application for LEED acoustic certification analysis.

## Quick Start

### Building the Executable

1. **Prerequisites:**
   - Windows 10/11 development machine
   - Python 3.8+ with virtual environment
   - Git (for version information)
   - All dependencies from `requirements.txt` installed

2. **Build Process:**
   ```bash
   # Activate your virtual environment
   source venv/bin/activate  # or venv\Scripts\activate on Windows
   
   # Run the build
   cd build
   python build.py
   
   # Or use the batch script
   build.bat
   ```

3. **Result:**
   - Executable: `build/deploy/AcousticAnalysisTool.exe`
   - Ready for distribution to Windows users

## System Architecture

### Deployment Strategy

**Packaging Tool:** PyInstaller
- Superior PySide6/Qt support
- Automatic dependency detection
- Bundle data files and resources
- Professional executable with version metadata

**Database Strategy:**
- **Materials Database:** Bundled read-only resource (1,339+ acoustic materials)
- **User Projects:** Stored in `Documents/AcousticAnalysis` for persistence across updates

**Versioning System:**
- Git commit-based build numbers
- Automatic version generation from git history
- Version displayed in UI and executable metadata

### Directory Structure

```
build/
├── build_spec.py              # PyInstaller configuration
├── build.py                   # Main build script with versioning
├── build.bat                  # Windows build batch script
├── deploy.bat                 # User deployment script
├── test_deployment.py         # Build validation tests
├── version_template.py        # Version information template
├── requirements-build.txt     # Build-specific dependencies
└── deploy/
    ├── AcousticAnalysisTool.exe    # Built executable
    ├── build_info.json             # Build metadata
    ├── test_results.json           # Validation results
    ├── README_INSTALL.txt          # User installation guide
    └── uninstall.bat               # Generated uninstaller
```

## Build System Components

### 1. Version Management (`version_template.py`)

Generates dynamic version information:
- Major.Minor.Patch version (1.0.0)
- Git commit-based build numbers
- Build timestamp and git commit hash
- Displays in application UI

### 2. PyInstaller Configuration (`build_spec.py`)

Professional executable settings:
- Single-file executable
- Bundled materials database
- Hidden imports for all dependencies
- Windows version metadata
- Optimized size with UPX compression

### 3. Build Script (`build.py`)

Automated build process:
- Git version extraction
- Database bundling validation
- PyInstaller execution
- Build validation and packaging
- Error handling and logging

### 4. Deployment Scripts

**`build.bat`** - Developer build script:
- Environment validation
- Python build process execution
- Error handling and status reporting

**`deploy.bat`** - User deployment script:
- Desktop shortcut creation
- User data folder setup
- Application testing
- Uninstaller generation

### 5. Validation System (`test_deployment.py`)

Comprehensive testing:
- Build artifact validation
- Resource bundling verification
- Version consistency checks
- Basic startup simulation
- Dependency analysis

## Database Integration

### Materials Database Bundling

The acoustic materials database (`materials/acoustic_materials.db`) containing 1,339+ professional materials is bundled into the executable:

```python
# Bundled as read-only resource
datas = [
    (str(materials_path / "acoustic_materials.db"), "materials"),
]
```

### User Data Persistence

User project data remains in a persistent location:
- **Location:** `%USERPROFILE%/Documents/AcousticAnalysis/`
- **Contents:** Project database, exported files
- **Behavior:** Preserved across application updates
- **Auto-creation:** Directory and README created on first run

### Deployment-Aware Code

The application detects bundled vs development environments:

```python
def is_bundled_executable():
    return getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS')

def get_materials_database_path():
    if is_bundled_executable():
        return get_resource_path("materials/acoustic_materials.db")
    else:
        return get_resource_path("materials/acoustic_materials.db")
```

## Build Process Details

### 1. Environment Setup
- Virtual environment activation check
- Build dependencies installation
- Git availability validation

### 2. Version Generation
- Extract current git commit hash and count
- Generate `src/version.py` from template
- Create Windows version info file

### 3. PyInstaller Execution
- Clean previous builds
- Execute spec file with all configurations
- Bundle resources and databases
- Create optimized executable

### 4. Deployment Package Creation
- Copy executable to deploy directory
- Generate build metadata file
- Create installation documentation
- Validate build integrity

### 5. Testing and Validation
- File size and structure checks
- Resource availability verification
- Version consistency validation
- Basic startup simulation

## User Experience

### Installation Options

**Option 1: Direct Run**
- Download `AcousticAnalysisTool.exe`
- Double-click to run immediately
- User data folder created automatically

**Option 2: Full Setup**
- Download deployment package
- Run `deploy.bat` for complete setup
- Desktop shortcuts and uninstaller created

### First Run Experience
- Splash screen with version information
- Automatic user data directory creation
- Materials database immediately available
- No additional configuration required

### Data Management
- All user projects in `Documents/AcousticAnalysis`
- Materials database bundled and always available
- Safe to move/copy executable file
- User data persists across updates

## Distribution Strategy

### Target Audience
- Acoustic consultants and engineers
- LEED certification professionals
- Architecture and construction firms
- Research institutions

### System Requirements
- Windows 10/11 (64-bit)
- 4 GB RAM minimum, 8 GB recommended
- 500 MB disk space
- 1024x768 minimum display resolution

### Distribution Methods
- **Direct download:** Single executable file
- **Package distribution:** Complete deployment folder
- **Network deployment:** Copy to shared drives
- **USB distribution:** Portable executable

## Testing and Quality Assurance

### Automated Testing
```bash
# Run validation tests after building
python build/test_deployment.py
```

### Manual Testing Checklist
- [ ] Application starts without errors
- [ ] All major features functional
- [ ] Materials database accessible
- [ ] User data persistence works
- [ ] Excel export functionality
- [ ] PDF viewing and drawing tools
- [ ] Version information displays correctly

### Performance Validation
- [ ] Startup time under 10 seconds
- [ ] Memory usage reasonable (<500 MB typical)
- [ ] File operations responsive
- [ ] No memory leaks during extended use

## Troubleshooting

### Common Build Issues

**PyInstaller Import Errors:**
- Add missing modules to `hiddenimports` in `build_spec.py`
- Check for dynamic imports in application code

**Large Executable Size:**
- Review included dependencies
- Check for unnecessary data files
- Consider excluding test/development modules

**Database Access Issues:**
- Verify materials database bundling in spec file
- Check path resolution in bundled environment
- Test resource path utilities

### Common User Issues

**Application Won't Start:**
- Verify Windows 10/11 requirement
- Check for antivirus false positives
- Ensure sufficient disk space and memory

**Missing Features:**
- Confirm complete deployment package
- Check for corrupted download
- Verify materials database integrity

**Data Loss:**
- Check `Documents/AcousticAnalysis` directory
- Look for database backup files
- Review uninstaller logs

## Maintenance and Updates

### Version Updates
1. Update version numbers in template
2. Rebuild executable with new version
3. Test thoroughly on clean systems
4. Update documentation as needed

### Dependency Updates
1. Update `requirements-build.txt`
2. Test with new dependencies
3. Update hidden imports if needed
4. Validate build size and performance

### Feature Additions
1. Update spec file if new resources needed
2. Test bundling of additional data files
3. Validate database compatibility
4. Update user documentation

## Security Considerations

### Code Signing
- Consider code signing for professional distribution
- Reduces Windows security warnings
- Improves user trust and adoption

### Data Security
- User data stored locally only
- No network communication required
- Materials database read-only
- No sensitive information in bundled resources

### Distribution Security
- Verify executable integrity before distribution
- Use secure download channels
- Provide checksums for verification
- Monitor for false positive antivirus reports

## Support and Documentation

### User Support Materials
- `README_INSTALL.txt` - Installation instructions
- In-application help and tooltips
- Version information in About dialog
- Contact information for technical support

### Developer Documentation
- This deployment guide
- PyInstaller spec file comments
- Build script documentation
- Testing procedures and checklists

## Success Metrics

A successful deployment should achieve:
- **Build Success Rate:** 100% on development machines
- **User Startup Success:** >95% on target Windows systems
- **Feature Availability:** All major features accessible offline
- **Performance:** Startup <10s, responsive UI, <500MB RAM typical
- **User Experience:** Single-click installation, no configuration required

---

**Contact Information:**
- Technical Support: support@acousticsolutions.com
- Developer Documentation: This README and source code comments
- Build Issues: Check test results in `deploy/test_results.json`