@echo off
REM Deployment script for Acoustic Analysis Tool
REM Creates user-friendly installation package

setlocal EnableDelayedExpansion

echo ============================================
echo Acoustic Analysis Tool - Deployment Setup
echo ============================================

REM Get the directory where this batch file is located
set "DEPLOY_DIR=%~dp0deploy"
set "EXE_PATH=%DEPLOY_DIR%\AcousticAnalysisTool.exe"

REM Check if executable exists
if not exist "%EXE_PATH%" (
    echo ERROR: Executable not found at %EXE_PATH%
    echo Please run build.bat first to create the executable
    pause
    exit /b 1
)

echo Found executable: %EXE_PATH%

REM Get file size
for %%A in ("%EXE_PATH%") do set "FILE_SIZE=%%~zA"
set /a "SIZE_MB=!FILE_SIZE! / 1024 / 1024"
echo Executable size: !SIZE_MB! MB

REM Create desktop shortcut option
echo.
choice /C YN /M "Create desktop shortcut"
if not errorlevel 2 (
    echo Creating desktop shortcut...
    
    REM Create VBScript to make shortcut
    echo Set oWS = WScript.CreateObject("WScript.Shell"^) > "%TEMP%\createshortcut.vbs"
    echo sLinkFile = "%USERPROFILE%\Desktop\Acoustic Analysis Tool.lnk" >> "%TEMP%\createshortcut.vbs"
    echo Set oLink = oWS.CreateShortcut(sLinkFile^) >> "%TEMP%\createshortcut.vbs"
    echo oLink.TargetPath = "%EXE_PATH%" >> "%TEMP%\createshortcut.vbs"
    echo oLink.WorkingDirectory = "%DEPLOY_DIR%" >> "%TEMP%\createshortcut.vbs"
    echo oLink.Description = "Acoustic Analysis Tool - LEED Acoustic Certification" >> "%TEMP%\createshortcut.vbs"
    echo oLink.Save >> "%TEMP%\createshortcut.vbs"
    
    cscript /nologo "%TEMP%\createshortcut.vbs"
    del "%TEMP%\createshortcut.vbs"
    
    if exist "%USERPROFILE%\Desktop\Acoustic Analysis Tool.lnk" (
        echo Desktop shortcut created successfully
    ) else (
        echo Warning: Could not create desktop shortcut
    )
)

REM Create Documents folder for user data
set "DOCS_DIR=%USERPROFILE%\Documents\AcousticAnalysis"
if not exist "%DOCS_DIR%" (
    echo.
    echo Creating user data directory...
    mkdir "%DOCS_DIR%"
    echo Created: %DOCS_DIR%
    
    REM Create README in user directory
    echo Acoustic Analysis Tool - User Data Directory > "%DOCS_DIR%\README.txt"
    echo. >> "%DOCS_DIR%\README.txt"
    echo This directory will contain your acoustic analysis projects. >> "%DOCS_DIR%\README.txt"
    echo The application will automatically create a database file here >> "%DOCS_DIR%\README.txt"
    echo when you create your first project. >> "%DOCS_DIR%\README.txt"
    echo. >> "%DOCS_DIR%\README.txt"
    echo DO NOT DELETE this directory or move the database files >> "%DOCS_DIR%\README.txt"
    echo unless you want to lose your project data. >> "%DOCS_DIR%\README.txt"
    echo. >> "%DOCS_DIR%\README.txt"
    echo For support, contact: support@acousticsolutions.com >> "%DOCS_DIR%\README.txt"
)

REM Test run option
echo.
choice /C YN /M "Test run the application now"
if not errorlevel 2 (
    echo.
    echo Starting Acoustic Analysis Tool...
    echo (This may take a moment on first run)
    echo.
    
    REM Start application and wait a few seconds to see if it starts properly
    start "" "%EXE_PATH%"
    timeout /t 3 /nobreak >nul
    
    echo If the application started successfully, setup is complete!
    echo If you encounter any issues, check the console for error messages.
) else (
    echo.
    echo Setup completed without test run.
)

REM Create uninstall script
echo.
echo Creating uninstaller...
set "UNINSTALL_PATH=%DEPLOY_DIR%\uninstall.bat"

echo @echo off > "%UNINSTALL_PATH%"
echo REM Uninstaller for Acoustic Analysis Tool >> "%UNINSTALL_PATH%"
echo echo Uninstalling Acoustic Analysis Tool... >> "%UNINSTALL_PATH%"
echo. >> "%UNINSTALL_PATH%"
echo REM Remove desktop shortcut >> "%UNINSTALL_PATH%"
echo if exist "%USERPROFILE%\Desktop\Acoustic Analysis Tool.lnk" ( >> "%UNINSTALL_PATH%"
echo     del "%USERPROFILE%\Desktop\Acoustic Analysis Tool.lnk" >> "%UNINSTALL_PATH%"
echo     echo Desktop shortcut removed >> "%UNINSTALL_PATH%"
echo ^) >> "%UNINSTALL_PATH%"
echo. >> "%UNINSTALL_PATH%"
echo echo NOTE: User data directory not removed: >> "%UNINSTALL_PATH%"
echo echo %DOCS_DIR% >> "%UNINSTALL_PATH%"
echo echo Delete manually if you want to remove all project data >> "%UNINSTALL_PATH%"
echo. >> "%UNINSTALL_PATH%"
echo echo Uninstall completed >> "%UNINSTALL_PATH%"
echo pause >> "%UNINSTALL_PATH%"

echo.
echo ============================================
echo DEPLOYMENT SETUP COMPLETE!
echo ============================================
echo.
echo Installation Summary:
echo - Executable: %EXE_PATH%
echo - User data: %DOCS_DIR%
if exist "%USERPROFILE%\Desktop\Acoustic Analysis Tool.lnk" (
    echo - Desktop shortcut: Yes
) else (
    echo - Desktop shortcut: No
)
echo - Uninstaller: %UNINSTALL_PATH%
echo.
echo The application is ready to use!
echo Run "AcousticAnalysisTool.exe" or use the desktop shortcut.
echo.
echo For distribution to other users:
echo 1. Copy the entire deploy folder
echo 2. Have users run deploy.bat to set up shortcuts and folders
echo 3. Or simply run AcousticAnalysisTool.exe directly
echo.
pause