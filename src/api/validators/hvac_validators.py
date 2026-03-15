"""
HVAC Validation

Strict validators for HVAC noise calculation requests.
"""

from typing import Any, Optional

from src.api.schemas.common import OCTAVE_BANDS_8
from src.api.schemas.hvac_schemas import (
    HVACPathNoiseRequest,
    PathElementInput,
    ReceiverRoomInput,
    CombinedReceiverNoiseRequest,
    NCComplianceRequest,
    ElementAttenuationRequest,
    HVACPathNoiseResponse,
)
from src.api.validators.base import (
    ValidationContext,
    validate_required_fields,
    validate_positive_number,
    validate_in_list,
    validate_frequency_dict,
    validate_list_elements,
)


VALID_ELEMENT_TYPES = ["source", "duct", "elbow", "junction", "flex_duct", "terminal"]
VALID_DUCT_SHAPES = ["rectangular", "circular"]
VALID_DUCT_TYPES = ["sheet_metal", "fiberglass", "flexible"]
VALID_FITTING_TYPES = [
    "elbow_90", "elbow_45", "elbow_90_with_vanes",
    "tee_branch", "tee_main", "x_junction", "y_junction",
    "reducer", "expansion"
]
VALID_SPACE_TYPES = [
    "private_office", "conference_room", "classroom", "open_office",
    "library", "auditorium", "theater", "hospital_patient",
    "hospital_operating", "residence", "restaurant", "retail", "warehouse"
]


class HVACValidator:
    """Strict validator for HVAC API requests."""

    def validate_hvac_path_noise_request(
        self,
        request: HVACPathNoiseRequest
    ) -> ValidationContext:
        """
        Validate an HVAC path noise calculation request.

        Enforces strict validation:
        - At least 2 path elements required (source + terminal)
        - First element must be type "source"
        - All elements must have required fields for their type

        Args:
            request: The request to validate

        Returns:
            ValidationContext with any errors
        """
        ctx = ValidationContext()

        # Validate path_elements list
        if request.path_elements is None:
            ctx.add_missing_field("path_elements")
            return ctx

        if len(request.path_elements) < 2:
            ctx.add_error(
                "path_elements",
                f"Must have at least 2 elements (source + terminal), got {len(request.path_elements)}"
            )
            return ctx

        # First element must be source
        if request.path_elements[0].element_type != "source":
            ctx.add_error(
                "path_elements[0].element_type",
                f"First element must be type 'source', got '{request.path_elements[0].element_type}'"
            )

        # Validate each element
        validate_list_elements(
            request.path_elements,
            "path_elements",
            ctx,
            self._validate_path_element,
            min_length=2
        )

        # Validate receiver room if provided
        if request.receiver_room is not None:
            self._validate_receiver_room(request.receiver_room, ctx.with_prefix("receiver_room."))

        return ctx

    def _validate_path_element(
        self,
        element: PathElementInput,
        index: int,
        ctx: ValidationContext
    ) -> bool:
        """Validate a single path element based on its type."""
        valid = True

        # Always required
        if not validate_required_fields(element, ["element_type", "element_id"], ctx):
            valid = False
            return valid

        # Validate element_type
        if not validate_in_list(element.element_type, "element_type", VALID_ELEMENT_TYPES, ctx):
            valid = False

        # Type-specific validation
        if element.element_type == "source":
            valid = self._validate_source_element(element, ctx) and valid
        elif element.element_type == "duct":
            valid = self._validate_duct_element(element, ctx) and valid
        elif element.element_type == "elbow":
            valid = self._validate_elbow_element(element, ctx) and valid
        elif element.element_type == "junction":
            valid = self._validate_junction_element(element, ctx) and valid
        elif element.element_type == "flex_duct":
            valid = self._validate_flex_duct_element(element, ctx) and valid
        # terminal has no additional required fields

        return valid

    def _validate_source_element(
        self,
        element: PathElementInput,
        ctx: ValidationContext
    ) -> bool:
        """Validate source element - requires noise level."""
        # Must have either source_noise_dba or source_octave_bands
        if element.source_noise_dba is None and element.source_octave_bands is None:
            ctx.add_error(
                "source_noise_dba",
                "Source element requires either source_noise_dba or source_octave_bands"
            )
            ctx.add_error(
                "source_octave_bands",
                "Source element requires either source_noise_dba or source_octave_bands"
            )
            return False

        if element.source_noise_dba is not None:
            validate_positive_number(element.source_noise_dba, "source_noise_dba", ctx, allow_zero=True)

        if element.source_octave_bands is not None:
            validate_frequency_dict(
                element.source_octave_bands,
                "source_octave_bands",
                ctx,
                OCTAVE_BANDS_8,
                all_required=True
            )

        return True

    def _validate_duct_element(
        self,
        element: PathElementInput,
        ctx: ValidationContext
    ) -> bool:
        """Validate duct element - requires dimensions, length, type, lining, flow."""
        valid = True

        # Required fields for duct
        required = ["length_ft", "duct_shape", "duct_type", "lining_thickness_inches", "flow_rate_cfm"]
        for field in required:
            value = getattr(element, field, None)
            if value is None:
                ctx.add_missing_field(field)
                valid = False

        # Validate duct_shape
        if not validate_in_list(element.duct_shape, "duct_shape", VALID_DUCT_SHAPES, ctx):
            valid = False

        # Validate duct_type
        if not validate_in_list(element.duct_type, "duct_type", VALID_DUCT_TYPES, ctx):
            valid = False

        # Validate dimensions based on shape
        if element.duct_shape == "rectangular":
            if element.width_inches is None:
                ctx.add_missing_field("width_inches")
                valid = False
            else:
                validate_positive_number(element.width_inches, "width_inches", ctx)

            if element.height_inches is None:
                ctx.add_missing_field("height_inches")
                valid = False
            else:
                validate_positive_number(element.height_inches, "height_inches", ctx)

        elif element.duct_shape == "circular":
            if element.diameter_inches is None:
                ctx.add_missing_field("diameter_inches")
                valid = False
            else:
                validate_positive_number(element.diameter_inches, "diameter_inches", ctx)

        # Validate positive numbers
        validate_positive_number(element.length_ft, "length_ft", ctx)
        validate_positive_number(element.lining_thickness_inches, "lining_thickness_inches", ctx, allow_zero=True)
        validate_positive_number(element.flow_rate_cfm, "flow_rate_cfm", ctx)

        return valid

    def _validate_elbow_element(
        self,
        element: PathElementInput,
        ctx: ValidationContext
    ) -> bool:
        """Validate elbow element - requires fitting_type, dimensions, has_turning_vanes."""
        valid = True

        # Required fields
        if element.fitting_type is None:
            ctx.add_missing_field("fitting_type")
            valid = False

        if element.has_turning_vanes is None:
            ctx.add_missing_field("has_turning_vanes")
            valid = False

        # Require dimensions (width/height or diameter)
        has_rect = element.width_inches is not None and element.height_inches is not None
        has_circ = element.diameter_inches is not None

        if not has_rect and not has_circ:
            ctx.add_error(
                "width_inches",
                "Elbow requires dimensions: either (width_inches + height_inches) or diameter_inches"
            )
            valid = False

        # Validate positive dimensions
        if element.width_inches is not None:
            validate_positive_number(element.width_inches, "width_inches", ctx)
        if element.height_inches is not None:
            validate_positive_number(element.height_inches, "height_inches", ctx)
        if element.diameter_inches is not None:
            validate_positive_number(element.diameter_inches, "diameter_inches", ctx)

        return valid

    def _validate_junction_element(
        self,
        element: PathElementInput,
        ctx: ValidationContext
    ) -> bool:
        """Validate junction element - requires fitting_type and dimensions."""
        valid = True

        if element.fitting_type is None:
            ctx.add_missing_field("fitting_type")
            valid = False

        # Require dimensions
        has_rect = element.width_inches is not None and element.height_inches is not None
        has_circ = element.diameter_inches is not None

        if not has_rect and not has_circ:
            ctx.add_error(
                "width_inches",
                "Junction requires dimensions: either (width_inches + height_inches) or diameter_inches"
            )
            valid = False

        return valid

    def _validate_flex_duct_element(
        self,
        element: PathElementInput,
        ctx: ValidationContext
    ) -> bool:
        """Validate flex duct element - requires length and diameter."""
        valid = True

        if element.length_ft is None:
            ctx.add_missing_field("length_ft")
            valid = False
        else:
            validate_positive_number(element.length_ft, "length_ft", ctx)

        if element.diameter_inches is None:
            ctx.add_missing_field("diameter_inches")
            valid = False
        else:
            validate_positive_number(element.diameter_inches, "diameter_inches", ctx)

        return valid

    def _validate_receiver_room(
        self,
        room: ReceiverRoomInput,
        ctx: ValidationContext
    ) -> bool:
        """Validate receiver room parameters."""
        valid = True

        # All fields required
        required = ["room_volume_cubic_ft", "room_absorption_sabins"]
        if not validate_required_fields(room, required, ctx):
            valid = False

        validate_positive_number(room.room_volume_cubic_ft, "room_volume_cubic_ft", ctx)
        validate_positive_number(room.room_absorption_sabins, "room_absorption_sabins", ctx)
        validate_positive_number(room.distance_from_terminal_ft, "distance_from_terminal_ft", ctx)

        if not validate_in_list(room.termination_type, "termination_type", ["flush", "free"], ctx):
            valid = False

        return valid

    def validate_combined_receiver_noise_request(
        self,
        request: CombinedReceiverNoiseRequest
    ) -> ValidationContext:
        """Validate a combined receiver noise request."""
        ctx = ValidationContext()

        # Required fields
        required = ["receiver_space_id", "path_results", "room_volume_cubic_ft", "room_absorption_sabins"]
        validate_required_fields(request, required, ctx)

        # Validate path_results
        if request.path_results is not None:
            if len(request.path_results) < 1:
                ctx.add_error("path_results", "Must have at least 1 path result")
            else:
                for i, result in enumerate(request.path_results):
                    if not isinstance(result, HVACPathNoiseResponse):
                        ctx.add_error(
                            f"path_results[{i}]",
                            "Must be HVACPathNoiseResponse object"
                        )
                    elif result.status == "error":
                        ctx.add_error(
                            f"path_results[{i}]",
                            f"Path result has error status: cannot combine"
                        )

        # Validate room parameters
        validate_positive_number(request.room_volume_cubic_ft, "room_volume_cubic_ft", ctx)
        validate_positive_number(request.room_absorption_sabins, "room_absorption_sabins", ctx)

        return ctx

    def validate_nc_compliance_request(
        self,
        request: NCComplianceRequest
    ) -> ValidationContext:
        """Validate an NC compliance request."""
        ctx = ValidationContext()

        # Must have either octave_band_levels or dba_level
        if request.octave_band_levels is None and request.dba_level is None:
            ctx.add_error(
                "octave_band_levels",
                "Either octave_band_levels or dba_level must be provided"
            )
            ctx.add_error(
                "dba_level",
                "Either octave_band_levels or dba_level must be provided"
            )

        # Validate octave_band_levels if provided
        if request.octave_band_levels is not None:
            validate_frequency_dict(
                request.octave_band_levels,
                "octave_band_levels",
                ctx,
                OCTAVE_BANDS_8,
                all_required=True
            )

        # Validate dba_level if provided
        if request.dba_level is not None:
            validate_positive_number(request.dba_level, "dba_level", ctx, allow_zero=True)

        # Must have either target_nc or space_type
        if request.target_nc is None and request.space_type is None:
            ctx.add_error(
                "target_nc",
                "Either target_nc or space_type must be provided"
            )
            ctx.add_error(
                "space_type",
                "Either target_nc or space_type must be provided"
            )

        # Validate space_type if provided
        if request.space_type is not None:
            validate_in_list(request.space_type, "space_type", VALID_SPACE_TYPES, ctx)

        return ctx

    def validate_element_attenuation_request(
        self,
        request: ElementAttenuationRequest
    ) -> ValidationContext:
        """Validate an element attenuation request."""
        ctx = ValidationContext()

        # Required fields
        required = ["element_type", "length_ft", "duct_shape"]
        validate_required_fields(request, required, ctx)

        # Validate element_type
        validate_in_list(request.element_type, "element_type", ["duct", "elbow", "flex_duct"], ctx)

        # Validate duct_shape
        validate_in_list(request.duct_shape, "duct_shape", VALID_DUCT_SHAPES, ctx)

        # Validate element_type + duct_shape compatibility
        if request.element_type == "elbow" and request.duct_shape == "circular":
            ctx.add_error(
                "duct_shape",
                "Elbow element type requires duct_shape='rectangular'. Circular elbow insertion loss is not supported."
            )
        elif request.element_type == "flex_duct" and request.duct_shape == "rectangular":
            ctx.add_error(
                "duct_shape",
                "Flex duct element type requires duct_shape='circular'. Flex duct is circular per ASHRAE."
            )

        # Validate dimensions based on shape
        if request.duct_shape == "rectangular":
            if request.width_inches is None:
                ctx.add_missing_field("width_inches")
            else:
                validate_positive_number(request.width_inches, "width_inches", ctx)

            if request.height_inches is None:
                ctx.add_missing_field("height_inches")
            else:
                validate_positive_number(request.height_inches, "height_inches", ctx)

        elif request.duct_shape == "circular":
            if request.diameter_inches is None:
                ctx.add_missing_field("diameter_inches")
            else:
                validate_positive_number(request.diameter_inches, "diameter_inches", ctx)

        # Validate other fields
        # Elbow insertion loss does not use length; allow 0 for elbow
        allow_length_zero = request.element_type == "elbow"
        validate_positive_number(
            request.length_ft, "length_ft", ctx, allow_zero=allow_length_zero
        )
        validate_positive_number(request.lining_thickness_inches, "lining_thickness_inches", ctx, allow_zero=True)

        if request.flow_rate_cfm is not None:
            validate_positive_number(request.flow_rate_cfm, "flow_rate_cfm", ctx)

        return ctx
