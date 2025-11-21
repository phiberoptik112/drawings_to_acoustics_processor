"""
Database Manager - Utility functions for database operations
"""

import os
import shutil
import sqlite3
from datetime import datetime
from typing import Optional, Dict, Tuple
from models import close_database, get_session, Project


def get_database_info(db_path: str) -> Dict:
    """
    Get information about a database file
    
    Args:
        db_path: Path to the database file
        
    Returns:
        Dictionary with database information:
        - exists: bool
        - size: int (bytes)
        - size_mb: float (megabytes)
        - modified_date: datetime or None
        - project_count: int
        - readable: bool
        - writable: bool
    """
    info = {
        'exists': False,
        'size': 0,
        'size_mb': 0.0,
        'modified_date': None,
        'project_count': 0,
        'readable': False,
        'writable': False
    }
    
    if not os.path.exists(db_path):
        return info
    
    info['exists'] = True
    
    # File size
    try:
        info['size'] = os.path.getsize(db_path)
        info['size_mb'] = info['size'] / (1024 * 1024)
    except Exception:
        pass
    
    # Modified date
    try:
        mtime = os.path.getmtime(db_path)
        info['modified_date'] = datetime.fromtimestamp(mtime)
    except Exception:
        pass
    
    # Permissions
    info['readable'] = os.access(db_path, os.R_OK)
    info['writable'] = os.access(db_path, os.W_OK)
    
    # Project count (if database is valid)
    if info['readable']:
        try:
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            # Check if projects table exists
            cursor.execute("""
                SELECT name FROM sqlite_master 
                WHERE type='table' AND name='projects'
            """)
            if cursor.fetchone():
                cursor.execute("SELECT COUNT(*) FROM projects")
                info['project_count'] = cursor.fetchone()[0]
            conn.close()
        except Exception:
            # Database might be locked or invalid
            pass
    
    return info


def validate_database_path(path: str) -> Tuple[bool, Optional[str]]:
    """
    Validate that a database path is writable and valid
    
    Args:
        path: Path to validate
        
    Returns:
        Tuple of (is_valid, error_message)
        - is_valid: True if path is valid, False otherwise
        - error_message: Error description if invalid, None if valid
    """
    if not path:
        return False, "Path is empty"
    
    # Expand user path
    path = os.path.expanduser(path)
    
    # Get directory
    dir_path = os.path.dirname(path)
    
    # Check if directory exists or can be created
    if not os.path.exists(dir_path):
        try:
            os.makedirs(dir_path, exist_ok=True)
        except Exception as e:
            return False, f"Cannot create directory: {str(e)}"
    
    # Check if directory is writable
    if not os.access(dir_path, os.W_OK):
        return False, "Directory is not writable"
    
    # Check if file exists and is writable (if it exists)
    if os.path.exists(path):
        if not os.access(path, os.W_OK):
            return False, "Database file exists but is not writable"
    
    return True, None


def copy_database(source_path: str, dest_path: str, progress_callback=None) -> Tuple[bool, Optional[str]]:
    """
    Copy a database file to a new location
    
    Args:
        source_path: Source database file path
        dest_path: Destination database file path
        progress_callback: Optional callback function(current, total) for progress updates
        
    Returns:
        Tuple of (success, error_message)
        - success: True if copy succeeded, False otherwise
        - error_message: Error description if failed, None if succeeded
    """
    if not os.path.exists(source_path):
        return False, f"Source database not found: {source_path}"
    
    # Validate destination path
    is_valid, error_msg = validate_database_path(dest_path)
    if not is_valid:
        return False, error_msg
    
    # Check if destination exists
    if os.path.exists(dest_path):
        return False, "Destination file already exists. Please choose a different location or remove the existing file."
    
    try:
        # Close any open database connections before copying
        close_database()
        
        # Get file size for progress tracking
        file_size = os.path.getsize(source_path)
        
        # Copy the file
        if progress_callback:
            progress_callback(0, file_size)
        
        # Use shutil.copy2 to preserve metadata
        shutil.copy2(source_path, dest_path)
        
        if progress_callback:
            progress_callback(file_size, file_size)
        
        # Verify copy by checking file sizes match
        if os.path.getsize(dest_path) != file_size:
            # Clean up partial copy
            try:
                os.remove(dest_path)
            except Exception:
                pass
            return False, "Copy verification failed: file sizes do not match"
        
        return True, None
        
    except PermissionError:
        return False, "Permission denied. Make sure the database is not in use and you have write permissions."
    except Exception as e:
        return False, f"Error copying database: {str(e)}"


def format_file_size(size_bytes: int) -> str:
    """
    Format file size in human-readable format
    
    Args:
        size_bytes: Size in bytes
        
    Returns:
        Formatted string (e.g., "1.5 MB")
    """
    if size_bytes < 1024:
        return f"{size_bytes} B"
    elif size_bytes < 1024 * 1024:
        return f"{size_bytes / 1024:.1f} KB"
    else:
        return f"{size_bytes / (1024 * 1024):.2f} MB"

