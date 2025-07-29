"""
Standard data libraries for the Acoustic Analysis Tool
"""

from .components import STANDARD_COMPONENTS, STANDARD_FITTINGS, STANDARD_DUCT_SIZES, STANDARD_ROUND_DUCT_SIZES
from .materials import STANDARD_MATERIALS, ROOM_TYPE_DEFAULTS

try:
    from .excel_exporter import ExcelExporter, ExportOptions
    EXCEL_EXPORT_AVAILABLE = True
except ImportError:
    EXCEL_EXPORT_AVAILABLE = False
    ExcelExporter = None
    ExportOptions = None

__all__ = [
    'STANDARD_COMPONENTS',
    'STANDARD_FITTINGS', 
    'STANDARD_DUCT_SIZES',
    'STANDARD_ROUND_DUCT_SIZES',
    'STANDARD_MATERIALS',
    'ROOM_TYPE_DEFAULTS',
    'ExcelExporter',
    'ExportOptions',
    'EXCEL_EXPORT_AVAILABLE'
]