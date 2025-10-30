"""
Version information template for Acoustic Analysis Tool
This file is generated during build process with git commit information
"""

# Version information (populated during build)
VERSION_MAJOR = 1
VERSION_MINOR = 0
VERSION_PATCH = 0
BUILD_NUMBER = "{{BUILD_NUMBER}}"
GIT_COMMIT = "{{GIT_COMMIT}}"
BUILD_DATE = "{{BUILD_DATE}}"
BUILD_TIME = "{{BUILD_TIME}}"

# Composite version string
VERSION_STRING = f"{VERSION_MAJOR}.{VERSION_MINOR}.{VERSION_PATCH}"
FULL_VERSION_STRING = f"{VERSION_STRING}.{BUILD_NUMBER}"

# Build information
BUILD_INFO = {
    'version': VERSION_STRING,
    'full_version': FULL_VERSION_STRING,
    'build_number': BUILD_NUMBER,
    'git_commit': GIT_COMMIT,
    'build_date': BUILD_DATE,
    'build_time': BUILD_TIME,
    'build_timestamp': f"{BUILD_DATE} {BUILD_TIME}"
}

def get_version():
    """Get the version string"""
    return VERSION_STRING

def get_full_version():
    """Get the full version string including build number"""
    return FULL_VERSION_STRING

def get_build_info():
    """Get complete build information"""
    return BUILD_INFO.copy()

def get_version_display():
    """Get formatted version for display in UI"""
    return f"Acoustic Analysis Tool v{VERSION_STRING} (Build {BUILD_NUMBER})"

def get_about_text():
    """Get formatted text for About dialog"""
    return f"""Acoustic Analysis Tool
Version: {VERSION_STRING}
Build: {BUILD_NUMBER}
Git Commit: {GIT_COMMIT[:8]}
Built: {BUILD_DATE} {BUILD_TIME}

Professional desktop application for LEED acoustic certification analysis.
Built with PySide6 and Python."""