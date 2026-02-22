"""
RT60 Validation

Strict validators for RT60 calculation requests.
"""

from typing import Any, Optional, Set

from src.api.schemas.common import OCTAVE_BANDS_6
from src.api.schemas.rt60_schemas import (
    RT60CalculationRequest,
    RT60ComplianceRequest,
    MaterialRecommendationRequest,
    SurfaceDefinition,
    TreatableSurface,
)
from src.api.validators.base import (
    ValidationContext,
    validate_required_fields,
    validate_positive_number,
    validate_in_list,
    validate_material_key,
    validate_frequency_dict,
    validate_list_elements,
)


VALID_SURFACE_TYPES = ["ceiling", "wall", "floor", "door", "window"]
VALID_CALCULATION_METHODS = ["sabine", "eyring"]
VALID_ROOM_TYPES = [
    "conference", "classroom", "office_private", "office_open",
    "auditorium", "worship", "restaurant", "healthcare_patient",
    "healthcare_public", "residential", "custom"
]


class RT60Validator:
    """Strict validator for RT60 API requests."""

    def __init__(self, valid_material_keys: Optional[Set[str]] = None):
        """
        Initialize validator.

        Args:
            valid_material_keys: Set of valid material keys for validation.
                                If None, material key validation is skipped.
        """
        self.valid_material_keys = valid_material_keys

    def validate_rt60_calculation_request(
        self,
        request: RT60CalculationRequest
    ) -> ValidationContext:
        """
        Validate an RT60 calculation request.

        Enforces strict validation:
        - All geometry fields required and positive
        - All surfaces must have valid surface_type, material_key, and area
        - At least one surface required

        Args:
            request: The request to validate

        Returns:
            ValidationContext with any errors
        """
        ctx = ValidationContext()

        # Validate required geometry fields
        geometry_fields = [
            "volume_cubic_feet",
            "floor_area_sq_ft",
            "wall_area_sq_ft",
            "ceiling_area_sq_ft",
        ]
        validate_required_fields(request, geometry_fields, ctx)

        # Validate geometry values are positive
        validate_positive_number(request.volume_cubic_feet, "volume_cubic_feet", ctx)
        validate_positive_number(request.floor_area_sq_ft, "floor_area_sq_ft", ctx)
        validate_positive_number(request.wall_area_sq_ft, "wall_area_sq_ft", ctx)
        validate_positive_number(request.ceiling_area_sq_ft, "ceiling_area_sq_ft", ctx)

        # Validate surfaces list
        if request.surfaces is None:
            ctx.add_missing_field("surfaces")
        else:
            validate_list_elements(
                request.surfaces,
                "surfaces",
                ctx,
                self._validate_surface_definition,
                min_length=1
            )

        # Validate calculation method
        validate_in_list(
            request.calculation_method,
            "calculation_method",
            VALID_CALCULATION_METHODS,
            ctx
        )

        return ctx

    def _validate_surface_definition(
        self,
        surface: SurfaceDefinition,
        index: int,
        ctx: ValidationContext
    ) -> bool:
        """Validate a single surface definition."""
        valid = True

        # Required fields
        if not validate_required_fields(surface, ["surface_type", "material_key", "area_sq_ft"], ctx):
            valid = False

        # Validate surface_type
        if not validate_in_list(surface.surface_type, "surface_type", VALID_SURFACE_TYPES, ctx):
            valid = False

        # Validate area is positive
        if not validate_positive_number(surface.area_sq_ft, "area_sq_ft", ctx):
            valid = False

        # Validate material_key exists (if we have the database)
        if not validate_material_key(
            surface.material_key,
            "material_key",
            ctx,
            self.valid_material_keys
        ):
            valid = False

        # Validate custom coefficients if provided
        if surface.custom_coefficients is not None:
            if not validate_frequency_dict(
                surface.custom_coefficients,
                "custom_coefficients",
                ctx,
                OCTAVE_BANDS_6,
                all_required=True
            ):
                valid = False

        return valid

    def validate_rt60_compliance_request(
        self,
        request: RT60ComplianceRequest
    ) -> ValidationContext:
        """
        Validate an RT60 compliance request.

        Requires either target_rt60 or room_type to be specified.

        Args:
            request: The request to validate

        Returns:
            ValidationContext with any errors
        """
        ctx = ValidationContext()

        # Validate rt60_by_frequency is present and valid
        if request.rt60_by_frequency is None:
            ctx.add_missing_field("rt60_by_frequency")
        else:
            validate_frequency_dict(
                request.rt60_by_frequency,
                "rt60_by_frequency",
                ctx,
                OCTAVE_BANDS_6,
                all_required=True
            )

        # Must have either target_rt60 or room_type
        if request.target_rt60 is None and request.room_type is None:
            ctx.add_error(
                "target_rt60",
                "Either target_rt60 or room_type must be specified"
            )
            ctx.add_error(
                "room_type",
                "Either target_rt60 or room_type must be specified"
            )

        # Validate target_rt60 if provided
        if request.target_rt60 is not None:
            validate_positive_number(request.target_rt60, "target_rt60", ctx)

        # Validate room_type if provided
        if request.room_type is not None:
            validate_in_list(request.room_type, "room_type", VALID_ROOM_TYPES, ctx)

        # Validate tolerance is positive
        validate_positive_number(request.tolerance, "tolerance", ctx)

        return ctx

    def validate_material_recommendation_request(
        self,
        request: MaterialRecommendationRequest
    ) -> ValidationContext:
        """
        Validate a material recommendation request.

        Args:
            request: The request to validate

        Returns:
            ValidationContext with any errors
        """
        ctx = ValidationContext()

        # Required fields
        required = ["volume_cubic_feet", "current_rt60_by_frequency", "target_rt60", "treatable_surfaces"]
        validate_required_fields(request, required, ctx)

        # Validate positive numbers
        validate_positive_number(request.volume_cubic_feet, "volume_cubic_feet", ctx)
        validate_positive_number(request.target_rt60, "target_rt60", ctx)

        # Validate current RT60
        if request.current_rt60_by_frequency is not None:
            validate_frequency_dict(
                request.current_rt60_by_frequency,
                "current_rt60_by_frequency",
                ctx,
                OCTAVE_BANDS_6,
                all_required=True
            )

        # Validate treatable surfaces
        if request.treatable_surfaces is not None:
            validate_list_elements(
                request.treatable_surfaces,
                "treatable_surfaces",
                ctx,
                self._validate_treatable_surface,
                min_length=1
            )

        return ctx

    def _validate_treatable_surface(
        self,
        surface: TreatableSurface,
        index: int,
        ctx: ValidationContext
    ) -> bool:
        """Validate a single treatable surface."""
        valid = True

        # Required fields
        if not validate_required_fields(surface, ["surface_type", "available_area_sq_ft"], ctx):
            valid = False

        # Validate surface_type (limited to ceiling, wall, floor)
        if not validate_in_list(surface.surface_type, "surface_type", ["ceiling", "wall", "floor"], ctx):
            valid = False

        # Validate area is positive
        if not validate_positive_number(surface.available_area_sq_ft, "available_area_sq_ft", ctx):
            valid = False

        # Validate current_material_key if provided
        if surface.current_material_key is not None:
            if not validate_material_key(
                surface.current_material_key,
                "current_material_key",
                ctx,
                self.valid_material_keys
            ):
                valid = False

        return valid
