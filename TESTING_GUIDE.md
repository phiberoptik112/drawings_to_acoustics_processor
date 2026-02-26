# Development Environment Setup - Testing Guide

## Issue: GUI Testing with DISPLAY :99

### Problem Summary

When attempting to test the Acoustic Analysis Tool GUI on DISPLAY=:99, the computer use tool cannot properly interact with the application window, despite the application running and being visible via tools like `scrot`.

### Root Causes Identified

1. **Window Manager Configuration**: Initially, the window manager (xfwm4) was running on DISPLAY=:1 while the application was on DISPLAY=:99. This has been corrected.

2. **Computer Tool Display Mismatch**: The computer use tool appears to be capturing a different display than DISPLAY=:99, where the application is actually running.

3. **Event Processing**: Without a proper window manager on the same display, Qt applications may not process mouse/keyboard events correctly.

### Solution: Programmatic Testing

Since direct GUI interaction via computer use is not reliable in this environment, we've created a programmatic testing approach:

#### Test Script: `test_project_creation.py`

This script demonstrates the "New Project" functionality by:
- Initializing the database
- Creating a project named "Test Project" programmatically
- Verifying the project exists in the database
- Confirming all project attributes are set correctly

**Usage:**
```bash
source .venv/bin/activate
python test_project_creation.py
```

**Expected Output:**
```
✓ Project created successfully!
  - ID: 2
  - Name: Test Project
  - Description: Test project created programmatically for demonstration
  - Location: Test Location
  - Scale: 0.25
  - Units: imperial
  - Created: 2026-02-26 21:20:37.340080

✓ Test completed successfully!
```

### Verified Functionality

✅ **Database Operations**: Projects can be created, stored, and retrieved
✅ **Project Model**: All required fields (name, description, location, scale, units) work correctly
✅ **Recent Projects Display**: After restarting the application, the created projects appear in the Recent Projects list on the splash screen

### Environment Configuration

**Current Setup:**
- Display: DISPLAY=:99 (X virtual framebuffer)
- Window Manager: xfwm4 (now running on DISPLAY=:99)
- Application: Python 3.x with PySide6
- Database: SQLite at `~/Documents/AcousticAnalysis/acoustic_analysis.db`

### Recommendations for Future Testing

1. **Automated Testing**: Use the programmatic approach (`test_project_creation.py`) for CI/CD pipelines

2. **Manual GUI Testing**: For manual testing, use a display with a properly configured window manager:
   ```bash
   DISPLAY=:1 python src/main.py
   ```

3. **Integration Tests**: Extend the test script to cover:
   - Opening existing projects
   - Project dashboard functionality
   - Drawing operations
   - Calculation engines

4. **Screenshot Verification**: Use `scrot` for capturing specific window areas:
   ```bash
   DISPLAY=:99 scrot -u -a 300,300,600,400 /tmp/window.png
   ```

### Files Created

- `test_project_creation.py`: Programmatic project creation test
- `TESTING_GUIDE.md`: This documentation

### Test Results

✅ Project creation works correctly via database API
✅ Created projects appear in the Recent Projects list
✅ Application initializes properly with window manager on DISPLAY=:99
✅ Database migrations complete successfully
✅ All project attributes are persisted correctly

### Known Limitations

❌ Direct GUI interaction via computer use tool not working on DISPLAY=:99
❌ Dialog boxes cannot be tested programmatically in current setup
⚠️ Manual clicking/keyboard input requires alternative testing approach

### Next Steps

1. Add more programmatic tests for other features
2. Consider using Qt Test framework for automated GUI testing
3. Document manual testing procedures for features requiring GUI interaction
4. Create Docker container with properly configured X server for consistent testing
