@echo off
REM Build script for Acoustic Analysis Tool Windows executable
REM This script handles the complete build process including environment setup

echo ========================================
echo Acoustic Analysis Tool - Build Script
echo ========================================

REM Check if Python is available
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python not found in PATH
    echo Please install Python 3.8+ and ensure it's in your PATH
    pause
    exit /b 1
)

REM Check if we're in a virtual environment
if not defined VIRTUAL_ENV (
    echo WARNING: Not running in a virtual environment
    echo It's recommended to activate your virtual environment first
    echo.
    choice /C YN /M "Continue anyway"
    if errorlevel 2 exit /b 1
)

REM Get the directory where this batch file is located
set "BUILD_DIR=%~dp0"
set "PROJECT_ROOT=%BUILD_DIR%.."

REM Change to project root
cd /d "%PROJECT_ROOT%"

echo Current directory: %CD%
echo Build directory: %BUILD_DIR%
echo.

REM Check if git is available for version info
git --version >nul 2>&1
if errorlevel 1 (
    echo WARNING: Git not found - version info will be limited
    echo.
)

REM Run the Python build script
echo Starting Python build process...
echo.
python "%BUILD_DIR%build.py"

if errorlevel 1 (
    echo.
    echo BUILD FAILED!
    echo Check the error messages above for details
    pause
    exit /b 1
)

echo.
echo ========================================
echo BUILD COMPLETED SUCCESSFULLY!
echo ========================================
echo.
echo Executable created in: %BUILD_DIR%deploy\AcousticAnalysisTool.exe
echo.
echo Next steps:
echo 1. Test the executable: cd build\deploy && AcousticAnalysisTool.exe
echo 2. Create deployment package: deploy.bat
echo 3. Distribute for testing
echo.
pause