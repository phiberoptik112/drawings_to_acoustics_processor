"""
Schedule Validator
-----------------
Validation, auto-correction, and column mapping for mechanical schedules.
"""

from __future__ import annotations

import re
import logging
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum

logger = logging.getLogger(__name__)


class ValidationSeverity(Enum):
    """Validation issue severity levels"""
    ERROR = "error"  # Must fix before import
    WARNING = "warning"  # Should fix but can proceed
    INFO = "info"  # Informational only


@dataclass
class ValidationIssue:
    """A validation issue"""
    row: int
    column: Optional[int] = None
    severity: ValidationSeverity = ValidationSeverity.WARNING
    message: str = ""
    auto_fixable: bool = False
    suggested_fix: Optional[str] = None


@dataclass
class ColumnMapping:
    """Mapping of table columns to mechanical unit fields"""
    name_col: Optional[int] = None
    type_col: Optional[int] = None
    
    # Frequency band columns (8 bands each for Inlet, Radiated, Outlet)
    inlet_63_col: Optional[int] = None
    inlet_125_col: Optional[int] = None
    inlet_250_col: Optional[int] = None
    inlet_500_col: Optional[int] = None
    inlet_1000_col: Optional[int] = None
    inlet_2000_col: Optional[int] = None
    inlet_4000_col: Optional[int] = None
    inlet_8000_col: Optional[int] = None
    
    radiated_63_col: Optional[int] = None
    radiated_125_col: Optional[int] = None
    radiated_250_col: Optional[int] = None
    radiated_500_col: Optional[int] = None
    radiated_1000_col: Optional[int] = None
    radiated_2000_col: Optional[int] = None
    radiated_4000_col: Optional[int] = None
    radiated_8000_col: Optional[int] = None
    
    outlet_63_col: Optional[int] = None
    outlet_125_col: Optional[int] = None
    outlet_250_col: Optional[int] = None
    outlet_500_col: Optional[int] = None
    outlet_1000_col: Optional[int] = None
    outlet_2000_col: Optional[int] = None
    outlet_4000_col: Optional[int] = None
    outlet_8000_col: Optional[int] = None
    
    extra_cols: Dict[int, str] = field(default_factory=dict)  # Additional columns
    
    def get_inlet_cols(self) -> List[Optional[int]]:
        """Get inlet frequency columns in order"""
        return [
            self.inlet_63_col, self.inlet_125_col, self.inlet_250_col, self.inlet_500_col,
            self.inlet_1000_col, self.inlet_2000_col, self.inlet_4000_col, self.inlet_8000_col
        ]
    
    def get_radiated_cols(self) -> List[Optional[int]]:
        """Get radiated frequency columns in order"""
        return [
            self.radiated_63_col, self.radiated_125_col, self.radiated_250_col, self.radiated_500_col,
            self.radiated_1000_col, self.radiated_2000_col, self.radiated_4000_col, self.radiated_8000_col
        ]
    
    def get_outlet_cols(self) -> List[Optional[int]]:
        """Get outlet frequency columns in order"""
        return [
            self.outlet_63_col, self.outlet_125_col, self.outlet_250_col, self.outlet_500_col,
            self.outlet_1000_col, self.outlet_2000_col, self.outlet_4000_col, self.outlet_8000_col
        ]


class ScheduleValidator:
    """
    Validator for mechanical schedule data with auto-correction
    """
    
    FREQUENCY_BANDS = ["63", "125", "250", "500", "1000", "2000", "4000", "8000"]
    VALID_UNIT_TYPES = {"RTU", "AHU", "RF", "EF", "FCU", "VAV", "FAN", "BLOWER"}
    
    def __init__(self):
        self.issues: List[ValidationIssue] = []
    
    def validate_mechanical_unit_row(self, row: List[str], row_idx: int, mapping: ColumnMapping) -> List[ValidationIssue]:
        """
        Validate a single mechanical unit row
        
        Args:
            row: List of cell values
            row_idx: Row index (for error reporting)
            mapping: Column mapping
        
        Returns:
            List of validation issues
        """
        issues = []
        
        # Check name
        if mapping.name_col is not None:
            name = row[mapping.name_col].strip() if mapping.name_col < len(row) else ""
            if not name:
                issues.append(ValidationIssue(
                    row=row_idx,
                    column=mapping.name_col,
                    severity=ValidationSeverity.ERROR,
                    message=f"Row {row_idx + 1}: Missing unit name",
                    auto_fixable=False
                ))
        
        # Check unit type
        if mapping.type_col is not None:
            unit_type = row[mapping.type_col].strip().upper() if mapping.type_col < len(row) else ""
            if unit_type and unit_type not in self.VALID_UNIT_TYPES:
                issues.append(ValidationIssue(
                    row=row_idx,
                    column=mapping.type_col,
                    severity=ValidationSeverity.WARNING,
                    message=f"Row {row_idx + 1}: Unknown unit type '{unit_type}'",
                    auto_fixable=False
                ))
        
        # Check frequency values
        for section_name, cols in [
            ("Inlet", mapping.get_inlet_cols()),
            ("Radiated", mapping.get_radiated_cols()),
            ("Outlet", mapping.get_outlet_cols())
        ]:
            for i, col_idx in enumerate(cols):
                if col_idx is not None and col_idx < len(row):
                    value = row[col_idx].strip()
                    
                    if not value:
                        issues.append(ValidationIssue(
                            row=row_idx,
                            column=col_idx,
                            severity=ValidationSeverity.WARNING,
                            message=f"Row {row_idx + 1}: Missing {section_name} {self.FREQUENCY_BANDS[i]}Hz value",
                            auto_fixable=False
                        ))
                    else:
                        # Check if numeric
                        if not self._is_valid_sound_level(value):
                            issues.append(ValidationIssue(
                                row=row_idx,
                                column=col_idx,
                                severity=ValidationSeverity.ERROR,
                                message=f"Row {row_idx + 1}: Invalid {section_name} {self.FREQUENCY_BANDS[i]}Hz value '{value}'",
                                auto_fixable=True,
                                suggested_fix=self._try_fix_sound_level(value)
                            ))
        
        return issues
    
    def _is_valid_sound_level(self, value: str) -> bool:
        """Check if value is a valid sound level (numeric, 0-150 dB)"""
        try:
            # Remove common suffixes
            cleaned = value.replace("dB", "").replace("db", "").strip()
            num = float(cleaned)
            return 0 <= num <= 150
        except ValueError:
            return False
    
    def _try_fix_sound_level(self, value: str) -> Optional[str]:
        """Try to auto-fix a sound level value"""
        # Remove dB suffix
        fixed = value.replace("dB", "").replace("db", "").strip()
        
        # Fix common OCR errors
        fixed = fixed.replace("O", "0")  # Letter O -> digit 0
        fixed = fixed.replace("o", "0")
        fixed = fixed.replace("l", "1")  # Letter l -> digit 1
        fixed = fixed.replace("I", "1")  # Letter I -> digit 1
        
        # Try to parse
        try:
            num = float(fixed)
            if 0 <= num <= 150:
                return str(int(num)) if num == int(num) else str(num)
        except ValueError:
            pass
        
        return None
    
    def auto_fix_row(self, row: List[str], issues: List[ValidationIssue]) -> List[str]:
        """
        Automatically fix issues in a row where possible
        
        Args:
            row: Original row data
            issues: List of validation issues for this row
        
        Returns:
            Fixed row data
        """
        fixed_row = row.copy()
        
        for issue in issues:
            if issue.auto_fixable and issue.suggested_fix and issue.column is not None:
                if issue.column < len(fixed_row):
                    fixed_row[issue.column] = issue.suggested_fix
                    logger.info(f"Auto-fixed row {issue.row} col {issue.column}: '{row[issue.column]}' -> '{issue.suggested_fix}'")
        
        return fixed_row
    
    def suggest_column_mapping(self, headers: List[str], sample_rows: List[List[str]]) -> ColumnMapping:
        """
        Intelligently suggest column mapping based on headers and data
        
        Args:
            headers: List of column headers
            sample_rows: Sample rows for pattern detection
        
        Returns:
            Suggested ColumnMapping
        """
        mapping = ColumnMapping()
        
        # Normalize headers for matching
        norm_headers = [h.lower().strip() for h in headers]
        
        # Find name column
        for i, header in enumerate(norm_headers):
            if any(keyword in header for keyword in ["name", "tag", "mark", "id", "unit id"]):
                mapping.name_col = i
                logger.info(f"Detected name column: {i} ('{headers[i]}')")
                break
        
        # Find type column
        for i, header in enumerate(norm_headers):
            if any(keyword in header for keyword in ["type", "unit type", "equipment"]):
                mapping.type_col = i
                logger.info(f"Detected type column: {i} ('{headers[i]}')")
                break
        
        # Find frequency columns
        # Look for patterns like "63", "125", "Inlet 500", etc.
        for i, header in enumerate(norm_headers):
            # Check each frequency band
            for freq in self.FREQUENCY_BANDS:
                freq_pattern = f"\\b{freq}\\b|\\b{freq}hz\\b"
                if re.search(freq_pattern, header):
                    # Determine section (Inlet, Radiated, Outlet)
                    if "inlet" in header or "in" == header[:2]:
                        self._set_inlet_col(mapping, freq, i)
                        logger.info(f"Detected Inlet {freq}Hz column: {i} ('{headers[i]}')")
                    elif "radiated" in header or "rad" in header:
                        self._set_radiated_col(mapping, freq, i)
                        logger.info(f"Detected Radiated {freq}Hz column: {i} ('{headers[i]}')")
                    elif "outlet" in header or "out" in header:
                        self._set_outlet_col(mapping, freq, i)
                        logger.info(f"Detected Outlet {freq}Hz column: {i} ('{headers[i]}')")
                    else:
                        # Default to outlet if section unclear
                        self._set_outlet_col(mapping, freq, i)
                        logger.info(f"Detected {freq}Hz column (defaulting to Outlet): {i} ('{headers[i]}')")
                    break
        
        # Detect sequential frequency bands (common pattern)
        self._detect_sequential_bands(mapping, norm_headers, sample_rows)
        
        return mapping
    
    def _set_inlet_col(self, mapping: ColumnMapping, freq: str, col: int):
        """Set inlet column for a frequency"""
        if freq == "63":
            mapping.inlet_63_col = col
        elif freq == "125":
            mapping.inlet_125_col = col
        elif freq == "250":
            mapping.inlet_250_col = col
        elif freq == "500":
            mapping.inlet_500_col = col
        elif freq == "1000":
            mapping.inlet_1000_col = col
        elif freq == "2000":
            mapping.inlet_2000_col = col
        elif freq == "4000":
            mapping.inlet_4000_col = col
        elif freq == "8000":
            mapping.inlet_8000_col = col
    
    def _set_radiated_col(self, mapping: ColumnMapping, freq: str, col: int):
        """Set radiated column for a frequency"""
        if freq == "63":
            mapping.radiated_63_col = col
        elif freq == "125":
            mapping.radiated_125_col = col
        elif freq == "250":
            mapping.radiated_250_col = col
        elif freq == "500":
            mapping.radiated_500_col = col
        elif freq == "1000":
            mapping.radiated_1000_col = col
        elif freq == "2000":
            mapping.radiated_2000_col = col
        elif freq == "4000":
            mapping.radiated_4000_col = col
        elif freq == "8000":
            mapping.radiated_8000_col = col
    
    def _set_outlet_col(self, mapping: ColumnMapping, freq: str, col: int):
        """Set outlet column for a frequency"""
        if freq == "63":
            mapping.outlet_63_col = col
        elif freq == "125":
            mapping.outlet_125_col = col
        elif freq == "250":
            mapping.outlet_250_col = col
        elif freq == "500":
            mapping.outlet_500_col = col
        elif freq == "1000":
            mapping.outlet_1000_col = col
        elif freq == "2000":
            mapping.outlet_2000_col = col
        elif freq == "4000":
            mapping.outlet_4000_col = col
        elif freq == "8000":
            mapping.outlet_8000_col = col
    
    def _detect_sequential_bands(self, mapping: ColumnMapping, norm_headers: List[str], sample_rows: List[List[str]]):
        """
        Detect sequential frequency band columns (e.g., 8 consecutive numeric columns)
        """
        # Look for sequences of 8 columns with numeric data
        if not sample_rows:
            return
        
        # Check each potential starting position
        for start_col in range(len(norm_headers) - 7):
            # Check if next 8 columns all contain numeric data
            all_numeric = True
            for row in sample_rows[:min(3, len(sample_rows))]:  # Check first 3 rows
                if len(row) <= start_col + 7:
                    all_numeric = False
                    break
                for i in range(8):
                    cell_value = row[start_col + i].strip()
                    if cell_value and not self._is_numeric(cell_value):
                        all_numeric = False
                        break
                if not all_numeric:
                    break
            
            if all_numeric:
                # Found a sequence - assign to outlet if not already mapped
                logger.info(f"Detected sequential frequency bands at columns {start_col}-{start_col+7}")
                if mapping.outlet_63_col is None:
                    for i, freq in enumerate(self.FREQUENCY_BANDS):
                        self._set_outlet_col(mapping, freq, start_col + i)
                    logger.info(f"Assigned sequential bands to Outlet")
                    break
    
    def _is_numeric(self, value: str) -> bool:
        """Check if value is numeric (allowing dB suffix)"""
        cleaned = value.replace("dB", "").replace("db", "").strip()
        try:
            float(cleaned)
            return True
        except ValueError:
            return False
    
    def check_duplicate_names(self, rows: List[List[str]], name_col: int) -> List[ValidationIssue]:
        """
        Check for duplicate unit names
        
        Args:
            rows: All data rows
            name_col: Index of name column
        
        Returns:
            List of validation issues for duplicates
        """
        issues = []
        names_seen: Dict[str, int] = {}
        
        for i, row in enumerate(rows):
            if name_col < len(row):
                name = row[name_col].strip()
                if name:
                    if name in names_seen:
                        issues.append(ValidationIssue(
                            row=i,
                            column=name_col,
                            severity=ValidationSeverity.WARNING,
                            message=f"Row {i + 1}: Duplicate name '{name}' (also in row {names_seen[name] + 1})",
                            auto_fixable=False
                        ))
                    else:
                        names_seen[name] = i
        
        return issues
    
    def normalize_frequency_notation(self, value: str) -> str:
        """
        Normalize frequency notation (1k -> 1000, 2K -> 2000)
        
        Args:
            value: Input frequency string
        
        Returns:
            Normalized frequency string
        """
        value = value.strip().lower()
        
        # Replace k with 000
        if 'k' in value:
            value = value.replace('k', '000')
        
        return value
