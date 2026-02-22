"""
RT60 Calculation Service

API service wrapping existing RT60 calculators with strict validation.
"""

from typing import Dict, List, Optional, Set, Any
import math

from src.api.schemas.common import (
    OCTAVE_BANDS_6,
    ROOM_TYPE_TARGETS,
    APIError,
    ErrorCode,
)
from src.api.schemas.rt60_schemas import (
    RT60CalculationRequest,
    RT60CalculationResponse,
    RT60ComplianceRequest,
    RT60ComplianceResponse,
    MaterialRecommendationRequest,
    MaterialRecommendationResponse,
    SurfaceDefinition,
    SurfaceAnalysis,
    FrequencyCompliance,
    ComplianceRecommendation,
    TreatableSurface,
    SurfaceRecommendation,
    MaterialSuggestion,
    TreatmentStrategy,
)
from src.api.validators.rt60_validators import RT60Validator


class RT60CalculationService:
    """
    RT60 calculation service for LLM agentic workflows.

    Provides stateless, strictly validated endpoints for:
    - RT60 calculation (Sabine/Eyring)
    - Compliance analysis
    - Material recommendations

    All methods are self-contained and do not require database state.
    """

    def __init__(self):
        """Initialize the RT60 calculation service."""
        self._rt60_calculator = None
        self._materials_db = None
        self._valid_material_keys: Optional[Set[str]] = None

    def _get_rt60_calculator(self):
        """Lazy load the RT60 calculator."""
        if self._rt60_calculator is None:
            # Create a minimal RT60 calculator that uses our materials database
            self._rt60_calculator = _MinimalRT60Calculator(self._get_materials_db())
        return self._rt60_calculator

    def _get_materials_db(self) -> Dict:
        """Lazy load the materials database."""
        if self._materials_db is None:
            try:
                from src.data.materials_database import get_all_materials
                self._materials_db = get_all_materials()
            except ImportError:
                from src.data.materials import STANDARD_MATERIALS
                self._materials_db = STANDARD_MATERIALS
        return self._materials_db

    def _get_valid_material_keys(self) -> Set[str]:
        """Get set of valid material keys."""
        if self._valid_material_keys is None:
            self._valid_material_keys = set(self._get_materials_db().keys())
        return self._valid_material_keys

    def calculate_rt60(self, request: RT60CalculationRequest) -> RT60CalculationResponse:
        """
        Calculate RT60 reverberation time for a space.

        Args:
            request: RT60 calculation request with geometry and materials

        Returns:
            RT60CalculationResponse with results or error
        """
        # Validate request
        validator = RT60Validator(valid_material_keys=self._get_valid_material_keys())
        ctx = validator.validate_rt60_calculation_request(request)

        if not ctx.is_valid():
            return RT60CalculationResponse(
                status="error",
                error=ctx.to_api_error(
                    "Ensure all geometry values are positive and all materials exist in the database. "
                    "Use materials.search_materials() to find valid material keys."
                )
            )

        try:
            # Prepare calculation
            calculator = self._get_rt60_calculator()
            materials_db = self._get_materials_db()

            # Build surfaces list for calculator
            surfaces = []
            surface_analysis = []
            total_area = 0.0

            for surf_def in request.surfaces:
                # Get material info
                material_key = surf_def.material_key
                material_info = materials_db.get(material_key, {})
                material_name = material_info.get('name', material_key)

                # Get absorption coefficients
                if surf_def.custom_coefficients:
                    coefficients = surf_def.custom_coefficients
                    nrc = sum(coefficients.get(f, 0) for f in [250, 500, 1000, 2000]) / 4.0
                else:
                    coefficients = self._get_material_coefficients(material_key, material_info)
                    nrc = material_info.get('nrc', material_info.get('absorption_coeff', 0))

                surface = {
                    'area': surf_def.area_sq_ft,
                    'material_key': material_key,
                    'type': surf_def.surface_type,
                    'absorption_coefficients': coefficients if surf_def.custom_coefficients else None,
                }
                surfaces.append(surface)
                total_area += surf_def.area_sq_ft

                # Calculate absorption per frequency for analysis
                absorption_by_freq = {}
                for freq in OCTAVE_BANDS_6:
                    coeff = coefficients.get(freq, nrc)
                    absorption_by_freq[freq] = surf_def.area_sq_ft * coeff

                surface_analysis.append(SurfaceAnalysis(
                    surface_type=surf_def.surface_type,
                    material_name=material_name,
                    material_key=material_key,
                    area_sq_ft=surf_def.area_sq_ft,
                    nrc=nrc,
                    absorption_by_frequency=absorption_by_freq,
                    contribution_percentage=0.0  # Will be calculated after totals
                ))

            # Calculate RT60 for each frequency
            rt60_by_frequency = {}
            total_absorption_by_frequency = {}

            for freq in OCTAVE_BANDS_6:
                total_absorption = calculator.calculate_total_absorption(surfaces, frequency=freq)
                total_absorption_by_frequency[freq] = total_absorption

                if request.calculation_method == "sabine":
                    rt60 = calculator.calculate_rt60_sabine(request.volume_cubic_feet, total_absorption)
                else:
                    rt60 = calculator.calculate_rt60_eyring(request.volume_cubic_feet, surfaces, frequency=freq)

                # Cap infinite values
                if rt60 == float('inf') or rt60 > 999.9:
                    rt60 = 999.9

                rt60_by_frequency[freq] = round(rt60, 3)

            # Calculate average RT60 (typically speech frequencies: 500, 1000, 2000 Hz)
            speech_freqs = [500, 1000, 2000]
            average_rt60 = sum(rt60_by_frequency[f] for f in speech_freqs) / len(speech_freqs)

            # Calculate total absorption at NRC frequency (1000 Hz)
            total_absorption_nrc = total_absorption_by_frequency.get(1000, 0)
            avg_absorption_coeff = total_absorption_nrc / total_area if total_area > 0 else 0

            # Update contribution percentages
            for analysis in surface_analysis:
                freq_absorption = analysis.absorption_by_frequency.get(1000, 0)
                analysis.contribution_percentage = (
                    (freq_absorption / total_absorption_nrc * 100) if total_absorption_nrc > 0 else 0
                )

            # Build debug info if requested
            debug_info = None
            if request.debug_mode:
                debug_info = {
                    "calculation_steps": [
                        {"step": "Parse surfaces", "surface_count": len(surfaces)},
                        {"step": "Calculate absorption per frequency", "frequencies": list(OCTAVE_BANDS_6)},
                        {"step": f"Apply {request.calculation_method} formula", "volume": request.volume_cubic_feet},
                    ],
                    "raw_totals": {
                        "total_area": total_area,
                        "total_absorption_1000hz": total_absorption_nrc,
                    }
                }

            return RT60CalculationResponse(
                status="success",
                rt60_by_frequency=rt60_by_frequency,
                average_rt60=round(average_rt60, 3),
                calculation_method=request.calculation_method,
                total_absorption_by_frequency={k: round(v, 2) for k, v in total_absorption_by_frequency.items()},
                surface_analysis=surface_analysis,
                total_surface_area_sq_ft=total_area,
                average_absorption_coefficient=round(avg_absorption_coeff, 3),
                volume_cubic_feet=request.volume_cubic_feet,
                debug_info=debug_info,
            )

        except Exception as e:
            return RT60CalculationResponse(
                status="error",
                error=APIError(
                    error_code=ErrorCode.CALCULATION_ERROR,
                    error_message=f"Calculation failed: {str(e)}",
                    suggestion="Check input values and try again"
                )
            )

    def _get_material_coefficients(self, material_key: str, material_info: Dict) -> Dict[int, float]:
        """Extract frequency-dependent coefficients from material info."""
        coefficients = {}

        # Try to get from 'coefficients' dict
        if 'coefficients' in material_info:
            raw_coeffs = material_info['coefficients']
            for freq in OCTAVE_BANDS_6:
                freq_str = str(freq)
                if freq_str in raw_coeffs:
                    coefficients[freq] = raw_coeffs[freq_str]
                elif freq in raw_coeffs:
                    coefficients[freq] = raw_coeffs[freq]

        # Fill missing with NRC or absorption_coeff
        fallback = material_info.get('nrc', material_info.get('absorption_coeff', 0.1))
        for freq in OCTAVE_BANDS_6:
            if freq not in coefficients:
                coefficients[freq] = fallback

        return coefficients

    def analyze_compliance(self, request: RT60ComplianceRequest) -> RT60ComplianceResponse:
        """
        Analyze RT60 values against compliance targets.

        Args:
            request: Compliance request with RT60 values and target

        Returns:
            RT60ComplianceResponse with compliance status
        """
        # Validate request
        validator = RT60Validator()
        ctx = validator.validate_rt60_compliance_request(request)

        if not ctx.is_valid():
            return RT60ComplianceResponse(
                status="error",
                error=ctx.to_api_error(
                    "Provide rt60_by_frequency with all 6 octave bands and either target_rt60 or room_type"
                )
            )

        try:
            # Determine target RT60 and tolerance
            if request.room_type and request.room_type in ROOM_TYPE_TARGETS:
                target_info = ROOM_TYPE_TARGETS[request.room_type]
                target_rt60 = request.target_rt60 or target_info["target_rt60"]
                tolerance = request.tolerance if request.tolerance != 0.1 else target_info["tolerance"]
            else:
                target_rt60 = request.target_rt60
                tolerance = request.tolerance

            # Analyze each frequency
            compliance_by_frequency = {}
            passing = 0
            failing = 0
            recommendations = []

            for freq in OCTAVE_BANDS_6:
                current = request.rt60_by_frequency.get(freq, 0)
                deviation = current - target_rt60
                is_compliant = abs(deviation) <= tolerance

                compliance_by_frequency[freq] = FrequencyCompliance(
                    frequency_hz=freq,
                    current_rt60=current,
                    target_rt60=target_rt60,
                    tolerance=tolerance,
                    is_compliant=is_compliant,
                    deviation=round(deviation, 3)
                )

                if is_compliant:
                    passing += 1
                else:
                    failing += 1
                    # Add recommendation
                    if deviation > 0:
                        recommendations.append(ComplianceRecommendation(
                            priority="high" if abs(deviation) > 0.3 else "medium",
                            frequency_hz=freq,
                            recommendation_type="increase_absorption",
                            message=f"RT60 at {freq}Hz is {deviation:.2f}s over target. Add absorption."
                        ))
                    else:
                        recommendations.append(ComplianceRecommendation(
                            priority="medium",
                            frequency_hz=freq,
                            recommendation_type="decrease_absorption",
                            message=f"RT60 at {freq}Hz is {abs(deviation):.2f}s under target. Reduce absorption."
                        ))

            overall_compliance = failing == 0

            # Generate compliance notes
            if overall_compliance:
                notes = f"All {passing} frequency bands meet the target RT60 of {target_rt60}s (±{tolerance}s)"
            else:
                notes = f"{failing} of {passing + failing} frequency bands exceed tolerance. "
                if failing > 3:
                    notes += "Consider comprehensive acoustic treatment."

            return RT60ComplianceResponse(
                status="success",
                overall_compliance=overall_compliance,
                compliance_by_frequency=compliance_by_frequency,
                frequencies_passing=passing,
                frequencies_failing=failing,
                compliance_notes=notes,
                target_rt60=target_rt60,
                tolerance=tolerance,
                room_type=request.room_type,
                recommendations=recommendations,
            )

        except Exception as e:
            return RT60ComplianceResponse(
                status="error",
                error=APIError(
                    error_code=ErrorCode.CALCULATION_ERROR,
                    error_message=f"Compliance analysis failed: {str(e)}",
                    suggestion="Check input values and try again"
                )
            )

    def recommend_materials(self, request: MaterialRecommendationRequest) -> MaterialRecommendationResponse:
        """
        Recommend materials to achieve target RT60.

        Args:
            request: Recommendation request with current state and treatable surfaces

        Returns:
            MaterialRecommendationResponse with material suggestions
        """
        # Validate request
        validator = RT60Validator(valid_material_keys=self._get_valid_material_keys())
        ctx = validator.validate_material_recommendation_request(request)

        if not ctx.is_valid():
            return MaterialRecommendationResponse(
                status="error",
                error=ctx.to_api_error(
                    "Provide valid current_rt60_by_frequency, target_rt60, and treatable_surfaces"
                )
            )

        try:
            materials_db = self._get_materials_db()

            # Calculate current average RT60
            speech_freqs = [500, 1000, 2000]
            current_avg = sum(request.current_rt60_by_frequency.get(f, 0) for f in speech_freqs) / len(speech_freqs)

            # Check if treatment is needed
            if current_avg <= request.target_rt60:
                return MaterialRecommendationResponse(
                    status="no_treatment_needed",
                    treatment_needed=False,
                    current_average_rt60=round(current_avg, 3),
                    target_rt60=request.target_rt60,
                    absorption_gap_sabins=0,
                )

            # Calculate absorption gap (simplified)
            # Using Sabine: RT60 = 0.049 * V / A
            # A_current = 0.049 * V / RT60_current
            # A_target = 0.049 * V / RT60_target
            # Gap = A_target - A_current
            a_current = 0.049 * request.volume_cubic_feet / current_avg if current_avg > 0 else 0
            a_target = 0.049 * request.volume_cubic_feet / request.target_rt60 if request.target_rt60 > 0 else 0
            absorption_gap = max(0, a_target - a_current)

            # Find suitable materials for each treatable surface
            surface_recommendations = []

            for surface in request.treatable_surfaces:
                recommendations = self._find_materials_for_surface(
                    surface=surface,
                    materials_db=materials_db,
                    absorption_gap=absorption_gap,
                    current_rt60=request.current_rt60_by_frequency,
                    target_rt60=request.target_rt60,
                    volume=request.volume_cubic_feet,
                    max_recommendations=request.max_recommendations,
                    preferred_categories=request.preferred_categories,
                )
                surface_recommendations.append(recommendations)

            # Generate treatment strategies
            strategies = self._generate_treatment_strategies(
                surface_recommendations=surface_recommendations,
                target_rt60=request.target_rt60,
                volume=request.volume_cubic_feet,
            )

            return MaterialRecommendationResponse(
                status="success",
                treatment_needed=True,
                current_average_rt60=round(current_avg, 3),
                target_rt60=request.target_rt60,
                absorption_gap_sabins=round(absorption_gap, 2),
                surface_recommendations=surface_recommendations,
                treatment_strategies=strategies,
            )

        except Exception as e:
            return MaterialRecommendationResponse(
                status="error",
                error=APIError(
                    error_code=ErrorCode.CALCULATION_ERROR,
                    error_message=f"Material recommendation failed: {str(e)}",
                    suggestion="Check input values and try again"
                )
            )

    def _find_materials_for_surface(
        self,
        surface: TreatableSurface,
        materials_db: Dict,
        absorption_gap: float,
        current_rt60: Dict[int, float],
        target_rt60: float,
        volume: float,
        max_recommendations: int,
        preferred_categories: Optional[List[str]],
    ) -> SurfaceRecommendation:
        """Find suitable materials for a surface."""
        suggestions = []

        # Map surface type to material categories
        category_map = {
            "ceiling": ["ceiling", "panels"],
            "wall": ["wall", "panels", "fabric"],
            "floor": ["floor", "carpet"],
        }

        target_categories = category_map.get(surface.surface_type, [surface.surface_type])
        if preferred_categories:
            target_categories = [c for c in preferred_categories if c in target_categories] or target_categories

        # Score and rank materials
        scored_materials = []

        for key, material in materials_db.items():
            category = material.get('category', '').lower()

            # Filter by category
            if not any(cat in category for cat in target_categories):
                continue

            nrc = material.get('nrc', material.get('absorption_coeff', 0))
            coefficients = self._get_material_coefficients(key, material)

            # Calculate expected RT60 improvement
            expected_change = {}
            effectiveness = 0

            for freq in OCTAVE_BANDS_6:
                coeff = coefficients.get(freq, nrc)
                added_absorption = surface.available_area_sq_ft * coeff

                # Estimate new RT60 at this frequency
                current_freq_rt60 = current_rt60.get(freq, 1.0)
                current_absorption = 0.049 * volume / current_freq_rt60 if current_freq_rt60 > 0 else 0
                new_absorption = current_absorption + added_absorption
                new_rt60 = 0.049 * volume / new_absorption if new_absorption > 0 else current_freq_rt60

                change = new_rt60 - current_freq_rt60
                expected_change[freq] = round(change, 3)

                # Score based on how much it helps achieve target
                if current_freq_rt60 > target_rt60:
                    improvement = min(current_freq_rt60 - target_rt60, abs(change))
                    effectiveness += improvement

            # Normalize effectiveness score (0-100)
            effectiveness_score = min(100, effectiveness * 50)

            scored_materials.append({
                'key': key,
                'material': material,
                'nrc': nrc,
                'coefficients': coefficients,
                'expected_change': expected_change,
                'effectiveness_score': effectiveness_score,
            })

        # Sort by effectiveness and take top N
        scored_materials.sort(key=lambda x: x['effectiveness_score'], reverse=True)
        top_materials = scored_materials[:max_recommendations]

        for mat in top_materials:
            suggestions.append(MaterialSuggestion(
                material_key=mat['key'],
                material_name=mat['material'].get('name', mat['key']),
                category=mat['material'].get('category', 'unknown'),
                nrc=mat['nrc'],
                absorption_coefficients=mat['coefficients'],
                expected_rt60_change=mat['expected_change'],
                effectiveness_score=round(mat['effectiveness_score'], 1),
            ))

        return SurfaceRecommendation(
            surface_type=surface.surface_type,
            current_material=surface.current_material_key,
            available_area_sq_ft=surface.available_area_sq_ft,
            recommended_materials=suggestions,
        )

    def _generate_treatment_strategies(
        self,
        surface_recommendations: List[SurfaceRecommendation],
        target_rt60: float,
        volume: float,
    ) -> List[TreatmentStrategy]:
        """Generate combined treatment strategies."""
        strategies = []

        # Strategy 1: Use best material from each surface
        if surface_recommendations:
            changes = []
            for sr in surface_recommendations:
                if sr.recommended_materials:
                    best = sr.recommended_materials[0]
                    changes.append({
                        "surface_type": sr.surface_type,
                        "material_key": best.material_key,
                        "area_sq_ft": sr.available_area_sq_ft,
                    })

            if changes:
                # Estimate combined effect
                total_improvement = sum(
                    sr.recommended_materials[0].effectiveness_score
                    for sr in surface_recommendations
                    if sr.recommended_materials
                ) / len(changes)

                strategies.append(TreatmentStrategy(
                    strategy_id="best_each_surface",
                    strategy_name="Best Material Per Surface",
                    changes=changes,
                    expected_average_rt60=target_rt60,  # Simplified
                    expected_rt60_by_frequency={},
                    effectiveness_score=min(100, total_improvement),
                    cost_indicator="medium" if len(changes) > 1 else "low",
                ))

        return strategies

    def get_schema(self) -> Dict[str, Any]:
        """Return JSON schema for this service's endpoints."""
        return {
            "calculate_rt60": {
                "description": "Calculate RT60 reverberation time for a space",
                "input": "RT60CalculationRequest",
                "output": "RT60CalculationResponse",
                "required_fields": [
                    "volume_cubic_feet",
                    "floor_area_sq_ft",
                    "wall_area_sq_ft",
                    "ceiling_area_sq_ft",
                    "surfaces (list with surface_type, material_key, area_sq_ft)"
                ]
            },
            "analyze_compliance": {
                "description": "Analyze RT60 values against compliance targets",
                "input": "RT60ComplianceRequest",
                "output": "RT60ComplianceResponse",
                "required_fields": [
                    "rt60_by_frequency",
                    "target_rt60 OR room_type"
                ]
            },
            "recommend_materials": {
                "description": "Recommend materials to achieve target RT60",
                "input": "MaterialRecommendationRequest",
                "output": "MaterialRecommendationResponse",
                "required_fields": [
                    "volume_cubic_feet",
                    "current_rt60_by_frequency",
                    "target_rt60",
                    "treatable_surfaces"
                ]
            }
        }


class _MinimalRT60Calculator:
    """
    Minimal RT60 calculator for the API layer.

    This avoids import issues with the main calculations package
    while providing the core calculation methods needed by the API.
    """

    def __init__(self, materials_db: Dict):
        """Initialize with materials database."""
        self.materials_db = materials_db

    def calculate_surface_absorption(
        self, area: float, material_key: str, frequency: int = None
    ) -> float:
        """Calculate absorption for a surface."""
        if material_key not in self.materials_db:
            return 0.0

        material = self.materials_db[material_key]

        # Try frequency-specific coefficient
        if frequency and 'coefficients' in material:
            freq_str = str(frequency)
            if freq_str in material['coefficients']:
                coeff = material['coefficients'][freq_str]
                return area * coeff

        # Fallback to NRC or general absorption coefficient
        coeff = material.get('nrc', material.get('absorption_coeff', 0.1))
        return area * coeff

    def calculate_total_absorption(
        self, surfaces: List[Dict], frequency: int = None
    ) -> float:
        """Calculate total absorption from multiple surfaces."""
        total = 0.0
        for surface in surfaces:
            area = surface.get('area', 0)
            material_key = surface.get('material_key')
            if area > 0 and material_key:
                total += self.calculate_surface_absorption(area, material_key, frequency)
        return total

    def calculate_rt60_sabine(self, volume: float, total_absorption: float) -> float:
        """Calculate RT60 using Sabine formula."""
        if total_absorption <= 0:
            return float('inf')
        return 0.049 * volume / total_absorption

    def calculate_rt60_eyring(
        self, volume: float, surfaces: List[Dict], frequency: int = None
    ) -> float:
        """Calculate RT60 using Eyring formula."""
        total_area = 0.0
        weighted_absorption = 0.0

        for surface in surfaces:
            area = surface.get('area', 0)
            material_key = surface.get('material_key')

            if area > 0 and material_key and material_key in self.materials_db:
                material = self.materials_db[material_key]

                # Get absorption coefficient
                if frequency and 'coefficients' in material:
                    freq_str = str(frequency)
                    coeff = material['coefficients'].get(freq_str, material.get('nrc', 0.1))
                else:
                    coeff = material.get('nrc', material.get('absorption_coeff', 0.1))

                total_area += area
                weighted_absorption += area * coeff

        if total_area <= 0:
            return float('inf')

        avg_coeff = weighted_absorption / total_area

        # Clamp to avoid math errors
        if avg_coeff >= 1.0:
            avg_coeff = 0.99
        elif avg_coeff <= 0:
            return float('inf')

        try:
            denominator = -total_area * math.log(1 - avg_coeff)
            if denominator <= 0:
                return float('inf')
            return 0.049 * volume / denominator
        except (ValueError, ZeroDivisionError):
            return float('inf')
