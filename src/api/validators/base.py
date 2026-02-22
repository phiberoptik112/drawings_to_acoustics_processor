"""
Base Validation Utilities

Strict validation framework that rejects requests with missing physics-relevant fields.
"""

from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Set, Tuple, TypeVar, Union
from src.api.schemas.common import APIError, ErrorCode, ValidationError


T = TypeVar('T')


@dataclass
class ValidationContext:
    """
    Context for tracking validation state and errors.

    Used to accumulate all errors before returning, providing
    comprehensive feedback for LLM correction.
    """
    errors: List[ValidationError] = field(default_factory=list)
    missing_fields: List[str] = field(default_factory=list)
    field_path_prefix: str = ""

    def add_error(
        self,
        field_path: str,
        error_message: str,
        expected_type: Optional[str] = None,
        actual_value: Optional[Any] = None
    ) -> None:
        """Add a validation error"""
        full_path = f"{self.field_path_prefix}{field_path}" if self.field_path_prefix else field_path
        self.errors.append(ValidationError(
            field_path=full_path,
            error_message=error_message,
            expected_type=expected_type,
            actual_value=actual_value
        ))

    def add_missing_field(self, field_path: str) -> None:
        """Mark a required field as missing"""
        full_path = f"{self.field_path_prefix}{field_path}" if self.field_path_prefix else field_path
        self.missing_fields.append(full_path)
        self.add_error(full_path, "Required field is missing")

    def with_prefix(self, prefix: str) -> "ValidationContext":
        """Create a child context with a field path prefix"""
        return ValidationContext(
            errors=self.errors,
            missing_fields=self.missing_fields,
            field_path_prefix=f"{self.field_path_prefix}{prefix}"
        )

    def is_valid(self) -> bool:
        """Check if validation passed with no errors"""
        return len(self.errors) == 0 and len(self.missing_fields) == 0

    def to_api_error(self, suggestion: str = "") -> APIError:
        """Convert validation context to API error response"""
        field_errors = {err.field_path: err.error_message for err in self.errors}

        if self.missing_fields:
            error_code = ErrorCode.MISSING_REQUIRED_FIELDS
            error_message = f"Request rejected: {len(self.missing_fields)} required field(s) missing"
        else:
            error_code = ErrorCode.VALIDATION_ERROR
            error_message = f"Request rejected: {len(self.errors)} validation error(s)"

        return APIError(
            error_code=error_code,
            error_message=error_message,
            field_errors=field_errors,
            missing_fields=self.missing_fields,
            suggestion=suggestion or self._generate_suggestion()
        )

    def _generate_suggestion(self) -> str:
        """Generate a helpful suggestion based on errors"""
        if self.missing_fields:
            fields_str = ", ".join(self.missing_fields[:3])
            if len(self.missing_fields) > 3:
                fields_str += f" (and {len(self.missing_fields) - 3} more)"
            return f"Provide values for: {fields_str}"
        return "Check field values and try again"


class StrictValidator:
    """
    Strict validator that rejects requests with missing required fields.

    Usage:
        validator = StrictValidator()
        ctx = validator.validate_rt60_request(request)
        if not ctx.is_valid():
            return ctx.to_api_error()
    """

    def __init__(self, materials_db: Optional[Any] = None):
        """
        Initialize validator.

        Args:
            materials_db: Optional materials database for material key validation
        """
        self._materials_db = materials_db
        self._valid_material_keys: Optional[Set[str]] = None

    def set_materials_db(self, materials_db: Any) -> None:
        """Set the materials database for validation"""
        self._materials_db = materials_db
        self._valid_material_keys = None  # Reset cache

    def get_valid_material_keys(self) -> Set[str]:
        """Get set of valid material keys (cached)"""
        if self._valid_material_keys is None:
            if self._materials_db is not None:
                try:
                    # Try to get keys from database
                    self._valid_material_keys = set(self._materials_db.get_all_material_keys())
                except Exception:
                    self._valid_material_keys = set()
            else:
                self._valid_material_keys = set()
        return self._valid_material_keys


def validate_required_fields(
    obj: Any,
    required_fields: List[str],
    ctx: ValidationContext
) -> bool:
    """
    Validate that all required fields are present and not None.

    Args:
        obj: Object to validate (dataclass or dict)
        required_fields: List of field names that must be present
        ctx: Validation context to accumulate errors

    Returns:
        True if all required fields are present
    """
    all_present = True

    for field_name in required_fields:
        if isinstance(obj, dict):
            value = obj.get(field_name)
        else:
            value = getattr(obj, field_name, None)

        if value is None:
            ctx.add_missing_field(field_name)
            all_present = False

    return all_present


def validate_positive_number(
    value: Optional[float],
    field_name: str,
    ctx: ValidationContext,
    allow_zero: bool = False
) -> bool:
    """
    Validate that a number is positive.

    Args:
        value: Value to validate
        field_name: Name of field for error messages
        ctx: Validation context
        allow_zero: Whether zero is allowed

    Returns:
        True if valid
    """
    if value is None:
        return True  # None handling is done by required fields check

    if not isinstance(value, (int, float)):
        ctx.add_error(field_name, f"Must be a number, got {type(value).__name__}")
        return False

    if allow_zero:
        if value < 0:
            ctx.add_error(field_name, f"Must be >= 0, got {value}")
            return False
    else:
        if value <= 0:
            ctx.add_error(field_name, f"Must be > 0, got {value}")
            return False

    return True


def validate_in_list(
    value: Optional[Any],
    field_name: str,
    valid_values: List[Any],
    ctx: ValidationContext
) -> bool:
    """
    Validate that a value is in a list of valid values.

    Args:
        value: Value to validate
        field_name: Name of field for error messages
        valid_values: List of allowed values
        ctx: Validation context

    Returns:
        True if valid
    """
    if value is None:
        return True  # None handling is done by required fields check

    if value not in valid_values:
        valid_str = ", ".join(str(v) for v in valid_values[:5])
        if len(valid_values) > 5:
            valid_str += f" (and {len(valid_values) - 5} more)"
        ctx.add_error(
            field_name,
            f"Invalid value '{value}'. Must be one of: {valid_str}"
        )
        return False

    return True


def validate_material_key(
    key: Optional[str],
    field_name: str,
    ctx: ValidationContext,
    valid_keys: Optional[Set[str]] = None
) -> bool:
    """
    Validate that a material key exists in the database.

    Args:
        key: Material key to validate
        field_name: Name of field for error messages
        ctx: Validation context
        valid_keys: Optional set of valid keys (for performance)

    Returns:
        True if valid
    """
    if key is None:
        return True  # None handling is done by required fields check

    if not isinstance(key, str):
        ctx.add_error(field_name, f"Material key must be a string, got {type(key).__name__}")
        return False

    if valid_keys is not None and key not in valid_keys:
        ctx.add_error(
            field_name,
            f"Material '{key}' not found in database. Use materials search endpoint to find valid keys."
        )
        return False

    return True


def validate_frequency_dict(
    data: Optional[Dict[int, float]],
    field_name: str,
    ctx: ValidationContext,
    required_frequencies: Tuple[int, ...],
    all_required: bool = True
) -> bool:
    """
    Validate a frequency-keyed dictionary.

    Args:
        data: Dictionary to validate
        field_name: Name of field for error messages
        ctx: Validation context
        required_frequencies: Tuple of valid frequency values
        all_required: Whether all frequencies must be present

    Returns:
        True if valid
    """
    if data is None:
        return True  # None handling is done by required fields check

    if not isinstance(data, dict):
        ctx.add_error(field_name, f"Must be a dictionary, got {type(data).__name__}")
        return False

    valid = True

    # Check for invalid frequencies
    for freq in data.keys():
        if freq not in required_frequencies:
            ctx.add_error(
                f"{field_name}[{freq}]",
                f"Invalid frequency {freq}. Valid frequencies: {required_frequencies}"
            )
            valid = False

    # Check all required frequencies are present
    if all_required:
        for freq in required_frequencies:
            if freq not in data:
                ctx.add_missing_field(f"{field_name}[{freq}]")
                valid = False

    # Validate values are numbers
    for freq, value in data.items():
        if not isinstance(value, (int, float)):
            ctx.add_error(
                f"{field_name}[{freq}]",
                f"Value must be a number, got {type(value).__name__}"
            )
            valid = False

    return valid


def validate_list_elements(
    items: Optional[List[T]],
    field_name: str,
    ctx: ValidationContext,
    element_validator: Callable[[T, int, ValidationContext], bool],
    min_length: int = 0,
    max_length: Optional[int] = None
) -> bool:
    """
    Validate a list and its elements.

    Args:
        items: List to validate
        field_name: Name of field for error messages
        ctx: Validation context
        element_validator: Function to validate each element (item, index, ctx) -> bool
        min_length: Minimum required list length
        max_length: Maximum allowed list length

    Returns:
        True if valid
    """
    if items is None:
        return True  # None handling is done by required fields check

    if not isinstance(items, list):
        ctx.add_error(field_name, f"Must be a list, got {type(items).__name__}")
        return False

    if len(items) < min_length:
        ctx.add_error(field_name, f"Must have at least {min_length} item(s), got {len(items)}")
        return False

    if max_length is not None and len(items) > max_length:
        ctx.add_error(field_name, f"Must have at most {max_length} item(s), got {len(items)}")
        return False

    valid = True
    for i, item in enumerate(items):
        child_ctx = ctx.with_prefix(f"{field_name}[{i}].")
        if not element_validator(item, i, child_ctx):
            valid = False

    return valid
