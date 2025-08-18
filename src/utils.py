"""
Utility functions for the Acoustic Analysis Tool
Includes deployment detection and resource path management
"""

import os
import sys
from pathlib import Path


def is_bundled_executable():
    """
    Detect if running as a bundled executable (PyInstaller)
    Returns True if bundled, False if running from source
    """
    return getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS')


def get_resource_path(relative_path):
    """
    Get absolute path to resource files, works for both development and bundled executable
    
    Args:
        relative_path (str): Relative path to the resource from the project root
        
    Returns:
        str: Absolute path to the resource
    """
    if is_bundled_executable():
        # Running as bundled executable - resources are in the temp directory
        base_path = Path(sys._MEIPASS)
    else:
        # Running from source - use the project root
        # Get the directory containing this utils.py file (src/)
        src_dir = Path(__file__).parent
        # Project root is parent of src/
        base_path = src_dir.parent
    
    return str(base_path / relative_path)


def get_application_directory():
    """
    Get the directory containing the application executable or main script
    This is useful for creating files relative to the application location
    
    Returns:
        str: Absolute path to application directory
    """
    if is_bundled_executable():
        # Return directory containing the .exe file
        return os.path.dirname(sys.executable)
    else:
        # Return the project root directory
        src_dir = Path(__file__).parent
        return str(src_dir.parent)


def get_user_data_directory():
    """
    Get the user data directory for storing project databases
    This remains consistent between development and deployment
    
    Returns:
        str: Absolute path to user data directory
    """
    return os.path.expanduser("~/Documents/drawings_to_acoustics_processor/debug_data")


def ensure_user_data_directory():
    """
    Ensure the user data directory exists
    
    Returns:
        str: Absolute path to created user data directory
    """
    user_dir = get_user_data_directory()
    os.makedirs(user_dir, exist_ok=True)
    return user_dir


def get_materials_database_path():
    """
    Get the path to the acoustic materials database
    Handles both development and bundled deployment scenarios
    
    Returns:
        str: Absolute path to materials database
    """
    if is_bundled_executable():
        # In bundled executable, database is in materials subfolder
        return get_resource_path("materials/acoustic_materials.db")
    else:
        # In development, database is in project materials folder
        return get_resource_path("materials/acoustic_materials.db")


def get_version_info():
    """
    Get version information, with fallback if version module not available
    
    Returns:
        dict: Version information dictionary
    """
    try:
        # Try to import the generated version module
        if is_bundled_executable():
            # In bundled executable, version.py is in the root
            sys.path.insert(0, sys._MEIPASS)
        
        import version
        return version.get_build_info()
        
    except ImportError:
        # Fallback version info for development
        return {
            'version': '1.0.0',
            'full_version': '1.0.0.dev',
            'build_number': 'dev',
            'git_commit': 'development',
            'build_date': 'unknown',
            'build_time': 'unknown',
            'build_timestamp': 'development'
        }


def get_application_title():
    """
    Get the application title with version information
    
    Returns:
        str: Application title string
    """
    version_info = get_version_info()
    return f"Acoustic Analysis Tool v{version_info['version']}"


def get_about_text():
    """
    Get formatted about text for the application
    
    Returns:
        str: Formatted about text
    """
    version_info = get_version_info()
    
    about_text = f"""Acoustic Analysis Tool
Version: {version_info['version']}"""
    
    if version_info['build_number'] != 'dev':
        about_text += f"""
Build: {version_info['build_number']}
Git Commit: {version_info['git_commit'][:8] if len(version_info['git_commit']) > 8 else version_info['git_commit']}
Built: {version_info['build_date']} {version_info['build_time']}"""
    else:
        about_text += "\nDevelopment Version"
    
    about_text += """

Professional desktop application for LEED acoustic certification analysis.
Built with PySide6 and Python.

Features:
• RT60 reverberation time calculations
• HVAC noise analysis and NC ratings
• 1,339+ acoustic materials database
• PDF drawing analysis tools
• Professional Excel export

© 2025 Acoustic Solutions"""
    
    return about_text


def log_environment_info():
    """
    Log environment information for debugging
    Useful for troubleshooting deployment issues
    """
    print(f"Bundled executable: {is_bundled_executable()}")
    print(f"Python executable: {sys.executable}")
    
    if is_bundled_executable():
        print(f"Temp directory: {sys._MEIPASS}")
    
    print(f"Application directory: {get_application_directory()}")
    print(f"User data directory: {get_user_data_directory()}")
    print(f"Materials database: {get_materials_database_path()}")
    
    version_info = get_version_info()
    print(f"Version: {version_info['full_version']}")
    
    # Check if critical resources exist
    materials_db = get_materials_database_path()
    if os.path.exists(materials_db):
        size_mb = os.path.getsize(materials_db) / (1024 * 1024)
        print(f"Materials database found: {size_mb:.1f} MB")
    else:
        print("WARNING: Materials database not found!")