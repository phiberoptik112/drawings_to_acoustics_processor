"""
HVAC Noise Calculation Service

API service wrapping existing HVAC noise calculators with strict validation.
"""

from typing import Dict, List, Optional, Any
import math
import importlib.util
import os
import sys

from src.api.schemas.common import (
    OCTAVE_BANDS_8,
    SPACE_TYPE_NC_TARGETS,
    APIError,
    ErrorCode,
)
from src.api.schemas.hvac_schemas import (
    HVACPathNoiseRequest,
    HVACPathNoiseResponse,
    PathElementInput,
    ReceiverRoomInput,
    ElementResult,
    CombinedReceiverNoiseRequest,
    CombinedReceiverNoiseResponse,
    PathContribution,
    NCComplianceRequest,
    NCComplianceResponse,
    FrequencyExceedance,
    ElementAttenuationRequest,
    ElementAttenuationResponse,
)
from src.api.validators.hvac_validators import HVACValidator


# Module-level cache for loaded modules
_cached_modules = {}


def _load_module_directly(module_name: str, file_path: str):
    """Load a module directly without triggering package __init__.py."""
    if module_name in _cached_modules:
        return _cached_modules[module_name]

    # Resolve absolute path
    if not os.path.isabs(file_path):
        base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
        file_path = os.path.join(base_dir, file_path)

    spec = importlib.util.spec_from_file_location(module_name, file_path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    _cached_modules[module_name] = module
    return module


def _import_hvac_noise_engine():
    """Import HVACNoiseEngine without triggering calculations __init__.py."""
    # First load dependencies
    _load_module_directly(
        "src.calculations.debug_logger",
        "src/calculations/debug_logger.py"
    )
    _load_module_directly(
        "src.calculations.acoustic_utilities",
        "src/calculations/acoustic_utilities.py"
    )

    # Load the main module
    module = _load_module_directly(
        "src.calculations.hvac_noise_engine",
        "src/calculations/hvac_noise_engine.py"
    )
    return module.HVACNoiseEngine()


def _import_nc_analyzer():
    """Import NCRatingAnalyzer without triggering calculations __init__.py."""
    module = _load_module_directly(
        "src.calculations.nc_rating_analyzer",
        "src/calculations/nc_rating_analyzer.py"
    )
    return module.NCRatingAnalyzer()


def _get_path_element_class():
    """Get PathElement class from hvac_noise_engine."""
    if "src.calculations.hvac_noise_engine" in _cached_modules:
        return _cached_modules["src.calculations.hvac_noise_engine"].PathElement
    module = _load_module_directly(
        "src.calculations.hvac_noise_engine",
        "src/calculations/hvac_noise_engine.py"
    )
    return module.PathElement


class HVACNoiseService:
    """
    HVAC noise calculation service for LLM agentic workflows.

    Provides stateless, strictly validated endpoints for:
    - Path noise calculation
    - Combined receiver noise (multiple paths)
    - NC compliance analysis
    - Single element attenuation

    All methods are self-contained and do not require database state.
    """

    def __init__(self):
        """Initialize the HVAC noise service."""
        self._hvac_engine = None
        self._nc_analyzer = None

    def _get_hvac_engine(self):
        """Lazy load the HVAC noise engine."""
        if self._hvac_engine is None:
            # Import directly without triggering package __init__.py
            self._hvac_engine = _import_hvac_noise_engine()
        return self._hvac_engine

    def _get_nc_analyzer(self):
        """Lazy load the NC rating analyzer."""
        if self._nc_analyzer is None:
            # Import directly without triggering package __init__.py
            self._nc_analyzer = _import_nc_analyzer()
        return self._nc_analyzer

    def calculate_path_noise(self, request: HVACPathNoiseRequest) -> HVACPathNoiseResponse:
        """
        Calculate noise transmission through an HVAC path.

        Args:
            request: HVAC path noise request with elements and optional receiver room

        Returns:
            HVACPathNoiseResponse with results or error
        """
        # Validate request
        validator = HVACValidator()
        ctx = validator.validate_hvac_path_noise_request(request)

        if not ctx.is_valid():
            return HVACPathNoiseResponse(
                status="error",
                path_id=request.path_id,
                calculation_valid=False,
                error=ctx.to_api_error(
                    "Ensure all required fields are provided for each element type. "
                    "Source requires source_noise_dba or source_octave_bands. "
                    "Duct requires length, shape, dimensions, type, lining_thickness, and flow_rate."
                )
            )

        try:
            # Convert API elements to engine PathElement objects
            PathElement = _get_path_element_class()

            engine = self._get_hvac_engine()
            path_elements = []

            for api_elem in request.path_elements:
                engine_elem = self._convert_to_engine_element(api_elem, request.receiver_room)
                path_elements.append(engine_elem)

            # Calculate path noise
            result = engine.calculate_path_noise(
                path_elements=path_elements,
                path_id=request.path_id,
                debug=request.debug_mode,
                origin="api"
            )

            # Convert result to API response
            terminal_spectrum = {}
            if result.octave_band_spectrum:
                for i, freq in enumerate(OCTAVE_BANDS_8):
                    if i < len(result.octave_band_spectrum):
                        terminal_spectrum[freq] = round(result.octave_band_spectrum[i], 1)

            # Build element results if requested
            element_results = None
            if request.include_element_breakdown and result.element_results:
                element_results = []
                for i, er in enumerate(result.element_results):
                    element_results.append(ElementResult(
                        element_id=er.get('element_id', f'element_{i}'),
                        element_type=er.get('element_type', 'unknown'),
                        element_order=i,
                        noise_before_dba=er.get('noise_before_dba', 0),
                        noise_after_dba=er.get('noise_after_dba', 0),
                        attenuation_spectrum=er.get('attenuation_spectrum', {}),
                        generated_noise_spectrum=er.get('generated_noise_spectrum', {}),
                        nc_before=er.get('nc_before', 0),
                        nc_after=er.get('nc_after', 0),
                    ))

            response = HVACPathNoiseResponse(
                status="success" if result.calculation_valid else "warning",
                path_id=result.path_id,
                source_noise_dba=round(result.source_noise_dba, 1),
                terminal_noise_dba=round(result.terminal_noise_dba, 1),
                total_attenuation_dba=round(result.total_attenuation_dba, 1),
                nc_rating=result.nc_rating,
                terminal_spectrum=terminal_spectrum,
                element_results=element_results,
                calculation_valid=result.calculation_valid,
                warnings=result.warnings or [],
            )

            if request.debug_mode and result.debug_log:
                response.debug_log = result.debug_log

            return response

        except Exception as e:
            return HVACPathNoiseResponse(
                status="error",
                path_id=request.path_id,
                calculation_valid=False,
                error=APIError(
                    error_code=ErrorCode.CALCULATION_ERROR,
                    error_message=f"Path noise calculation failed: {str(e)}",
                    suggestion="Check path element values and try again"
                )
            )

    def _convert_to_engine_element(
        self,
        api_elem: PathElementInput,
        receiver_room: Optional[ReceiverRoomInput]
    ):
        """Convert API PathElementInput to engine PathElement."""
        from src.calculations.hvac_noise_engine import PathElement

        # Build octave band list if provided
        octave_bands = None
        if api_elem.source_octave_bands:
            octave_bands = [
                api_elem.source_octave_bands.get(freq, 0)
                for freq in OCTAVE_BANDS_8
            ]

        # Get room parameters for terminal elements
        room_volume = 0.0
        room_absorption = 0.0
        if api_elem.element_type == "terminal" and receiver_room:
            room_volume = receiver_room.room_volume_cubic_ft
            room_absorption = receiver_room.room_absorption_sabins

        return PathElement(
            element_type=api_elem.element_type,
            element_id=api_elem.element_id,
            length=api_elem.length_ft or 0.0,
            width=api_elem.width_inches or 0.0,
            height=api_elem.height_inches or 0.0,
            diameter=api_elem.diameter_inches or 0.0,
            duct_shape=api_elem.duct_shape or "rectangular",
            duct_type=api_elem.duct_type or "sheet_metal",
            lining_thickness=api_elem.lining_thickness_inches or 0.0,
            flow_rate=api_elem.flow_rate_cfm or 0.0,
            flow_velocity=api_elem.flow_velocity_fpm or 0.0,
            pressure_drop=api_elem.pressure_drop_in_wg or 0.0,
            vane_chord_length=api_elem.vane_chord_length_inches or 0.0,
            num_vanes=api_elem.num_vanes or 0,
            room_volume=room_volume,
            room_absorption=room_absorption,
            source_noise_level=api_elem.source_noise_dba or 0.0,
            octave_band_levels=octave_bands,
            fitting_type=api_elem.fitting_type,
            termination_type=receiver_room.termination_type if receiver_room else "flush",
        )

    def calculate_combined_receiver_noise(
        self,
        request: CombinedReceiverNoiseRequest
    ) -> CombinedReceiverNoiseResponse:
        """
        Combine multiple HVAC path results at a single receiver.

        Uses logarithmic addition to combine noise from multiple paths.

        Args:
            request: Combined receiver noise request with path results

        Returns:
            CombinedReceiverNoiseResponse with combined results
        """
        # Validate request
        validator = HVACValidator()
        ctx = validator.validate_combined_receiver_noise_request(request)

        if not ctx.is_valid():
            return CombinedReceiverNoiseResponse(
                status="error",
                error=ctx.to_api_error(
                    "Provide valid path_results from calculate_path_noise() calls"
                )
            )

        try:
            # Filter to valid results only
            valid_results = [r for r in request.path_results if r.status != "error"]

            if not valid_results:
                return CombinedReceiverNoiseResponse(
                    status="error",
                    error=APIError(
                        error_code=ErrorCode.CALCULATION_ERROR,
                        error_message="No valid path results to combine",
                        suggestion="Ensure at least one path calculation succeeded"
                    )
                )

            # Combine spectra using log addition
            combined_spectrum = {freq: 0.0 for freq in OCTAVE_BANDS_8}

            for freq in OCTAVE_BANDS_8:
                total_power = 0.0
                for result in valid_results:
                    level = result.terminal_spectrum.get(freq, 0)
                    if level > 0:
                        total_power += 10 ** (level / 10)

                if total_power > 0:
                    combined_spectrum[freq] = round(10 * math.log10(total_power), 1)

            # Calculate combined dB(A)
            # A-weighting corrections for each octave band
            a_weights = {
                63: -26.2, 125: -16.1, 250: -8.6, 500: -3.2,
                1000: 0.0, 2000: 1.2, 4000: 1.0, 8000: -1.1
            }

            total_power_a = 0.0
            for freq in OCTAVE_BANDS_8:
                level = combined_spectrum[freq]
                weighted_level = level + a_weights.get(freq, 0)
                total_power_a += 10 ** (weighted_level / 10)

            combined_dba = round(10 * math.log10(total_power_a), 1) if total_power_a > 0 else 0

            # Determine NC rating
            nc_analyzer = self._get_nc_analyzer()
            from src.calculations.nc_rating_analyzer import OctaveBandData
            octave_data = OctaveBandData(
                freq_63=combined_spectrum.get(63, 0),
                freq_125=combined_spectrum.get(125, 0),
                freq_250=combined_spectrum.get(250, 0),
                freq_500=combined_spectrum.get(500, 0),
                freq_1000=combined_spectrum.get(1000, 0),
                freq_2000=combined_spectrum.get(2000, 0),
                freq_4000=combined_spectrum.get(4000, 0),
                freq_8000=combined_spectrum.get(8000, 0),
            )
            nc_result = nc_analyzer.analyze_octave_band_data(octave_data)
            combined_nc = nc_result.nc_rating

            # Calculate path contributions
            path_contributions = []
            max_contribution = 0
            dominant_path = ""

            total_energy = sum(10 ** (r.terminal_noise_dba / 10) for r in valid_results)

            for result in valid_results:
                energy = 10 ** (result.terminal_noise_dba / 10)
                contribution_pct = (energy / total_energy * 100) if total_energy > 0 else 0

                path_contributions.append(PathContribution(
                    path_id=result.path_id,
                    noise_dba=result.terminal_noise_dba,
                    contribution_percentage=round(contribution_pct, 1)
                ))

                if contribution_pct > max_contribution:
                    max_contribution = contribution_pct
                    dominant_path = result.path_id

            return CombinedReceiverNoiseResponse(
                status="success",
                combined_spectrum=combined_spectrum,
                combined_noise_dba=combined_dba,
                combined_nc_rating=combined_nc,
                path_contributions=path_contributions,
                dominant_path_id=dominant_path,
                num_paths_combined=len(valid_results),
            )

        except Exception as e:
            return CombinedReceiverNoiseResponse(
                status="error",
                error=APIError(
                    error_code=ErrorCode.CALCULATION_ERROR,
                    error_message=f"Combined receiver calculation failed: {str(e)}",
                    suggestion="Check path results and try again"
                )
            )

    def analyze_nc_compliance(self, request: NCComplianceRequest) -> NCComplianceResponse:
        """
        Analyze noise levels against NC rating criteria.

        Args:
            request: NC compliance request with noise levels and target

        Returns:
            NCComplianceResponse with compliance status
        """
        # Validate request
        validator = HVACValidator()
        ctx = validator.validate_nc_compliance_request(request)

        if not ctx.is_valid():
            return NCComplianceResponse(
                status="error",
                error=ctx.to_api_error(
                    "Provide octave_band_levels or dba_level, and target_nc or space_type"
                )
            )

        try:
            nc_analyzer = self._get_nc_analyzer()

            # Get or estimate octave band levels
            if request.octave_band_levels:
                from src.calculations.nc_rating_analyzer import OctaveBandData
                octave_data = OctaveBandData(
                    freq_63=request.octave_band_levels.get(63, 0),
                    freq_125=request.octave_band_levels.get(125, 0),
                    freq_250=request.octave_band_levels.get(250, 0),
                    freq_500=request.octave_band_levels.get(500, 0),
                    freq_1000=request.octave_band_levels.get(1000, 0),
                    freq_2000=request.octave_band_levels.get(2000, 0),
                    freq_4000=request.octave_band_levels.get(4000, 0),
                    freq_8000=request.octave_band_levels.get(8000, 0),
                )
            else:
                # Estimate from dB(A)
                octave_data = nc_analyzer.estimate_octave_bands_from_dba(
                    request.dba_level,
                    spectrum_type="hvac"
                )

            # Determine target NC
            if request.space_type and request.space_type in SPACE_TYPE_NC_TARGETS:
                space_targets = SPACE_TYPE_NC_TARGETS[request.space_type]
                recommended_nc = space_targets["recommended"]
                maximum_nc = space_targets["maximum"]
                target_nc = request.target_nc or recommended_nc
            else:
                target_nc = request.target_nc or 40
                recommended_nc = target_nc
                maximum_nc = target_nc + 10

            # Analyze
            nc_result = nc_analyzer.analyze_octave_band_data(octave_data, target_nc)

            # Build exceedances list
            exceedances = []
            for freq, exc in nc_result.exceedances:
                exceedances.append(FrequencyExceedance(
                    frequency_hz=freq,
                    measured_level_db=octave_data.to_list()[list(OCTAVE_BANDS_8).index(freq)],
                    nc_curve_limit_db=exc,
                    exceedance_db=exc
                ))

            # Determine compliance status
            nc_rating = nc_result.nc_rating
            meets_criteria = nc_rating <= target_nc
            improvement_needed = max(0, nc_rating - target_nc)

            if nc_rating <= recommended_nc:
                compliance_status = "Excellent"
            elif nc_rating <= maximum_nc:
                compliance_status = "Acceptable"
            else:
                compliance_status = "Non-compliant"

            # Generate recommendations
            recommendations = nc_analyzer.recommend_noise_control(nc_result, target_nc)

            return NCComplianceResponse(
                status="success",
                nc_rating=nc_rating,
                overall_dba=nc_result.overall_dba,
                meets_criteria=meets_criteria,
                target_nc=target_nc,
                recommended_nc=recommended_nc,
                maximum_nc=maximum_nc,
                exceedances=exceedances,
                compliance_status=compliance_status,
                improvement_needed_nc_points=improvement_needed,
                noise_control_recommendations=recommendations,
            )

        except Exception as e:
            return NCComplianceResponse(
                status="error",
                error=APIError(
                    error_code=ErrorCode.CALCULATION_ERROR,
                    error_message=f"NC compliance analysis failed: {str(e)}",
                    suggestion="Check input values and try again"
                )
            )

    def calculate_element_attenuation(
        self,
        request: ElementAttenuationRequest
    ) -> ElementAttenuationResponse:
        """
        Calculate attenuation for a single duct element.

        Useful for what-if analysis of individual components.

        Args:
            request: Element attenuation request

        Returns:
            ElementAttenuationResponse with attenuation spectrum
        """
        # Validate request
        validator = HVACValidator()
        ctx = validator.validate_element_attenuation_request(request)

        if not ctx.is_valid():
            return ElementAttenuationResponse(
                status="error",
                error=ctx.to_api_error(
                    "Provide all required fields for element type"
                )
            )

        try:
            engine = self._get_hvac_engine()

            # Calculate attenuation based on element type and shape
            attenuation_spectrum = {}

            if request.duct_shape == "rectangular":
                from src.calculations.rectangular_duct_calculations import RectangularDuctCalculator
                calc = RectangularDuctCalculator()

                if request.lining_thickness_inches > 0:
                    # Lined duct
                    attenuation = calc.get_lined_attenuation(
                        length_ft=request.length_ft,
                        width_in=request.width_inches,
                        height_in=request.height_inches,
                        lining_thickness=request.lining_thickness_inches
                    )
                else:
                    # Unlined duct
                    attenuation = calc.get_unlined_attenuation(
                        length_ft=request.length_ft,
                        width_in=request.width_inches,
                        height_in=request.height_inches
                    )

                for i, freq in enumerate(OCTAVE_BANDS_8):
                    if i < len(attenuation):
                        attenuation_spectrum[freq] = round(attenuation[i], 2)

            elif request.duct_shape == "circular":
                from src.calculations.circular_duct_calculations import CircularDuctCalculator
                calc = CircularDuctCalculator()

                if request.lining_thickness_inches > 0:
                    attenuation = calc.get_lined_attenuation(
                        length_ft=request.length_ft,
                        diameter_in=request.diameter_inches,
                        lining_thickness=request.lining_thickness_inches
                    )
                else:
                    attenuation = calc.get_unlined_attenuation(
                        length_ft=request.length_ft,
                        diameter_in=request.diameter_inches
                    )

                for i, freq in enumerate(OCTAVE_BANDS_8):
                    if i < len(attenuation):
                        attenuation_spectrum[freq] = round(attenuation[i], 2)

            # Calculate total A-weighted attenuation
            a_weights = {
                63: -26.2, 125: -16.1, 250: -8.6, 500: -3.2,
                1000: 0.0, 2000: 1.2, 4000: 1.0, 8000: -1.1
            }

            # Weighted average of attenuation
            total_atten = sum(
                attenuation_spectrum.get(freq, 0) * (1 + a_weights[freq] / 100)
                for freq in OCTAVE_BANDS_8
            ) / 8

            return ElementAttenuationResponse(
                status="success",
                attenuation_spectrum=attenuation_spectrum,
                total_attenuation_dba=round(total_atten, 2),
            )

        except Exception as e:
            return ElementAttenuationResponse(
                status="error",
                error=APIError(
                    error_code=ErrorCode.CALCULATION_ERROR,
                    error_message=f"Element attenuation calculation failed: {str(e)}",
                    suggestion="Check element parameters and try again"
                )
            )

    def get_schema(self) -> Dict[str, Any]:
        """Return JSON schema for this service's endpoints."""
        return {
            "calculate_path_noise": {
                "description": "Calculate noise transmission through an HVAC path",
                "input": "HVACPathNoiseRequest",
                "output": "HVACPathNoiseResponse",
                "required_fields": [
                    "path_elements (list with element_type, element_id, and type-specific fields)",
                    "source element: source_noise_dba OR source_octave_bands",
                    "duct element: length_ft, duct_shape, dimensions, duct_type, lining_thickness_inches, flow_rate_cfm",
                    "elbow element: fitting_type, dimensions, has_turning_vanes"
                ]
            },
            "calculate_combined_receiver_noise": {
                "description": "Combine multiple path results at a single receiver",
                "input": "CombinedReceiverNoiseRequest",
                "output": "CombinedReceiverNoiseResponse",
                "required_fields": [
                    "receiver_space_id",
                    "path_results (list of HVACPathNoiseResponse)",
                    "room_volume_cubic_ft",
                    "room_absorption_sabins"
                ]
            },
            "analyze_nc_compliance": {
                "description": "Analyze noise levels against NC rating criteria",
                "input": "NCComplianceRequest",
                "output": "NCComplianceResponse",
                "required_fields": [
                    "octave_band_levels OR dba_level",
                    "target_nc OR space_type"
                ]
            },
            "calculate_element_attenuation": {
                "description": "Calculate attenuation for a single duct element",
                "input": "ElementAttenuationRequest",
                "output": "ElementAttenuationResponse",
                "required_fields": [
                    "element_type",
                    "length_ft",
                    "duct_shape",
                    "dimensions (width/height or diameter)"
                ]
            }
        }
