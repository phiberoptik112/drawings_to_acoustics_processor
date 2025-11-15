"""
Utils package - Utility modules for the Acoustic Analysis Tool
"""

from .location_manager import LocationManager
from .general_utils import (
    is_bundled_executable,
    get_resource_path,
    get_application_directory,
    get_user_data_directory,
    ensure_user_data_directory,
    get_materials_database_path,
    get_version_info,
    get_application_title,
    get_about_text,
    log_environment_info
)

__all__ = [
    'LocationManager',
    'is_bundled_executable',
    'get_resource_path',
    'get_application_directory',
    'get_user_data_directory',
    'ensure_user_data_directory',
    'get_materials_database_path',
    'get_version_info',
    'get_application_title',
    'get_about_text',
    'log_environment_info'
]
