# Version 1.0 Release Checklist

Use this checklist when preparing a new release build.

## Pre-Build Checks

### Code & Repository
- [ ] All changes committed to git
- [ ] Version number updated if needed (in `build.py` or version files)
- [ ] README.md up to date
- [ ] No debug code or console.log statements
- [ ] All tests passing

### Database & Resources
- [ ] Materials database exists: `materials/acoustic_materials.db`
- [ ] Database contains expected materials (1,383+)
- [ ] Run database test: `python build/test_database_bundling.py`
- [ ] All resource files present (icons, etc.)

### Dependencies
- [ ] requirements.txt is current
- [ ] build/requirements-build.txt includes PyInstaller
- [ ] Virtual environment is clean (no conflicting packages)

---

## Build Process

### Windows Build

- [ ] Open clean command prompt or PowerShell
- [ ] Activate virtual environment if using one
- [ ] Navigate to project root
- [ ] Run: `build\build.bat`
- [ ] Check for build errors
- [ ] Verify output: `build\deploy\AcousticAnalysisTool.exe`
- [ ] Check executable size (150-250 MB expected)
- [ ] Review build_info.json for correct version

### macOS Build

- [ ] Open clean terminal session
- [ ] Activate virtual environment if using one
- [ ] Navigate to project root
- [ ] Make scripts executable: `chmod +x build/build.sh build/deploy.sh`
- [ ] Run: `./build/build.sh`
- [ ] Check for build errors
- [ ] Verify output: `build/deploy/AcousticAnalysisTool.app`
- [ ] Check bundle size (150-250 MB expected)
- [ ] Review build_info.json for correct version

---

## Testing

### Launch Testing

**Windows:**
- [ ] Double-click `AcousticAnalysisTool.exe`
- [ ] Application window appears
- [ ] No error dialogs on startup
- [ ] Splash screen displays (if implemented)

**macOS:**
- [ ] Right-click → Open (first time if unsigned)
- [ ] Accept Gatekeeper dialog
- [ ] Application window appears
- [ ] No crash dialogs
- [ ] Check Console.app for errors

### Functional Testing

- [ ] **Materials Database**
  - [ ] Material library accessible
  - [ ] Can browse materials
  - [ ] Material search works
  - [ ] Shows correct material count (1,383+)
  
- [ ] **RT60 Calculations**
  - [ ] Can create new space
  - [ ] Can assign materials to surfaces
  - [ ] RT60 calculation produces results
  - [ ] Results appear reasonable
  
- [ ] **HVAC Analysis**
  - [ ] Can create HVAC paths
  - [ ] Can add segments
  - [ ] Noise calculations work
  - [ ] NC ratings calculated
  
- [ ] **Excel Export**
  - [ ] Export menu accessible
  - [ ] Export produces .xlsx file
  - [ ] File opens in Excel/Numbers
  - [ ] Data is formatted correctly
  
- [ ] **Project Management**
  - [ ] Can save project
  - [ ] Can load project
  - [ ] Project data persists correctly

### Performance Testing

- [ ] Application starts in <10 seconds
- [ ] Materials database loads quickly
- [ ] Calculations complete in reasonable time
- [ ] UI remains responsive during calculations
- [ ] Memory usage reasonable (<500 MB typical)

---

## Deployment Package Creation

### Windows Installer (Optional)

- [ ] Run: `build\deploy.bat`
- [ ] Test installer on clean Windows VM
- [ ] Verify desktop shortcut option works
- [ ] Verify Start Menu entry created
- [ ] Verify uninstaller works

### macOS Distribution

- [ ] Run: `./build/deploy.sh`
- [ ] Choose deployment format:
  - [ ] DMG for professional distribution
  - [ ] ZIP for simple distribution
- [ ] Test DMG/ZIP on clean macOS system
- [ ] Verify drag-to-Applications works (DMG)
- [ ] Verify extracted app works (ZIP)

---

## Code Signing (Production Only)

### Windows Code Signing

- [ ] Obtain Authenticode certificate
- [ ] Sign executable:
  ```batch
  signtool sign /f certificate.pfx /p password /t http://timestamp.digicert.com AcousticAnalysisTool.exe
  ```
- [ ] Verify signature:
  ```batch
  signtool verify /pa AcousticAnalysisTool.exe
  ```
- [ ] Test signed executable
- [ ] No "Unknown Publisher" warning

### macOS Code Signing & Notarization

- [ ] Obtain Apple Developer certificate
- [ ] Sign application:
  ```bash
  codesign --deep --force --verify --verbose \
    --sign "Developer ID Application: Your Name (TEAM_ID)" \
    --options runtime \
    build/deploy/AcousticAnalysisTool.app
  ```
- [ ] Verify signature:
  ```bash
  codesign --verify --deep --strict --verbose=2 AcousticAnalysisTool.app
  ```
- [ ] Create DMG
- [ ] Submit for notarization:
  ```bash
  xcrun notarytool submit AcousticAnalysisTool-macOS.dmg \
    --apple-id your@email.com \
    --team-id TEAM_ID \
    --password app-specific-password \
    --wait
  ```
- [ ] Staple notarization:
  ```bash
  xcrun stapler staple AcousticAnalysisTool-macOS.dmg
  ```
- [ ] Test notarized DMG on clean Mac
- [ ] No Gatekeeper warnings

---

## Documentation

- [ ] README.md reflects current version
- [ ] CHANGELOG.md updated (if exists)
- [ ] User guide updated (if exists)
- [ ] Release notes prepared
- [ ] Known issues documented

---

## Distribution

### File Preparation

- [ ] Create release folder
- [ ] Copy executable/app to release folder
- [ ] Include README or installation instructions
- [ ] Include license file (if applicable)
- [ ] Create ZIP archive for distribution
- [ ] Name format: `AcousticAnalysisTool-v1.0.0-Windows.zip`
- [ ] Name format: `AcousticAnalysisTool-v1.0.0-macOS.dmg`

### Upload & Release

- [ ] Upload to distribution server/platform
- [ ] Create GitHub release (if using)
- [ ] Tag git repository: `v1.0.0`
- [ ] Push tag to remote
- [ ] Upload binaries to release
- [ ] Publish release notes

### Testing Downloads

- [ ] Download from distribution server
- [ ] Verify download integrity (checksums)
- [ ] Test downloaded file works
- [ ] Links work in release notes

---

## Communication

### Internal

- [ ] Notify team of new release
- [ ] Update internal documentation
- [ ] Brief support team on changes
- [ ] Update training materials if needed

### External

- [ ] Send release announcement to users
- [ ] Update website with download links
- [ ] Post on social media (if applicable)
- [ ] Update documentation site

---

## Post-Release

### Monitoring

- [ ] Monitor user feedback
- [ ] Watch for bug reports
- [ ] Track download statistics
- [ ] Monitor crash reports (if telemetry enabled)

### Support

- [ ] Respond to user questions
- [ ] Document common issues
- [ ] Update FAQ if needed
- [ ] Plan hotfixes if critical issues found

### Planning

- [ ] Review release process
- [ ] Note improvements for next release
- [ ] Update this checklist if needed
- [ ] Plan next version features

---

## Quick Command Reference

```bash
# Test database bundling
python build/test_database_bundling.py

# Windows build
build\build.bat

# macOS build
./build/build.sh

# Windows deploy
build\deploy.bat

# macOS deploy
./build/deploy.sh

# Git tag release
git tag -a v1.0.0 -m "Release version 1.0.0"
git push origin v1.0.0
```

---

## Emergency Rollback

If critical issues found after release:

1. **Stop Distribution**
   - [ ] Remove download links
   - [ ] Post notice of issue
   
2. **Assess Impact**
   - [ ] Determine affected users
   - [ ] Severity of issue
   
3. **Fix or Rollback**
   - [ ] Prepare hotfix build
   - [ ] Or revert to previous version
   
4. **Communicate**
   - [ ] Notify users of issue
   - [ ] Provide workaround if possible
   - [ ] Announce fix timeline

---

**Checklist Version:** 1.0  
**Last Updated:** 2025-01-29  
**For Release:** Version 1.0.0

