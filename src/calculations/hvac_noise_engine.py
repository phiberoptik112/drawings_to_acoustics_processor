"""
HVAC Noise Calculation Engine - Unified system for HVAC acoustic analysis
Integrates all specialized calculators for complete path analysis
"""

# Custom exceptions for HVAC engine
class HVACEngineError(Exception):
    """Base exception for HVAC engine errors"""
    pass

class PathElementError(HVACEngineError):
    """Exception raised when path element processing fails"""
    pass

class CalculationError(HVACEngineError):
    """Exception raised when calculations fail"""
    pass

import math
import os
import numpy as np
from typing import Dict, List, Tuple, Optional, Union, Any
from dataclasses import dataclass
import warnings
from .debug_logger import debug_logger
from .hvac_constants import (
    NUM_OCTAVE_BANDS, DEFAULT_SPECTRUM_LEVELS, NC_CURVE_DATA,
    MIN_NC_RATING, MAX_NC_RATING, DEFAULT_NC_RATING
)
from .acoustic_utilities import AcousticConstants, SpectrumProcessor, NCRatingUtils

# Import all specialized calculators
from .circular_duct_calculations import CircularDuctCalculator
from .rectangular_duct_calculations import RectangularDuctCalculator
from .flex_duct_calculations import FlexDuctCalculator
from .elbow_turning_vane_generated_noise_calculations import ElbowTurningVaneCalculator
from .junction_elbow_generated_noise_calculations import JunctionElbowNoiseCalculator, JunctionType
from .rectangular_elbows_calculations import RectangularElbowsCalculator
from .receiver_room_sound_correction_calculations import ReceiverRoomSoundCorrection
from .end_reflection_loss import erl_from_equation, erl_from_table_flush, compute_effective_diameter_rectangular
# Note: Unlined rectangular duct calculations are handled by RectangularDuctCalculator.get_unlined_attenuation()


@dataclass
class PathElement:
    """Standardized path element data structure"""
    element_type: str  # 'duct', 'elbow', 'junction', 'flex_duct', 'terminal', 'source'
    element_id: str
    length: float = 0.0  # feet
    width: float = 0.0   # inches
    height: float = 0.0  # inches
    diameter: float = 0.0  # inches
    duct_shape: str = 'rectangular'  # 'rectangular', 'circular'
    duct_type: str = 'sheet_metal'  # 'sheet_metal', 'fiberglass', 'flexible'
    lining_thickness: float = 0.0  # inches
    flow_rate: float = 0.0  # cfm
    flow_velocity: float = 0.0  # fpm
    pressure_drop: float = 0.0  # in. w.g.
    # For elbows and junctions
    vane_chord_length: float = 0.0  # inches
    num_vanes: int = 0
    # For room correction
    room_volume: float = 0.0  # cubic feet
    room_absorption: float = 0.0  # sabins
    # Noise properties
    source_noise_level: float = 0.0  # dB(A)
    octave_band_levels: Optional[List[float]] = None  # 8-band spectrum
    # Optional fitting subtype hint (e.g., 'elbow_90', 'tee_branch', 'x_junction')
    fitting_type: Optional[str] = None
    # Optional override for BRANCH_TAKEOFF_90 spectrum choice: 'auto' | 'main_duct' | 'branch_duct'
    branch_takeoff_choice: Optional[str] = None
    # Terminal end condition for End Reflection Loss: 'flush' (grille/diffuser) or 'free' (open to space)
    termination_type: Optional[str] = None


@dataclass
class OctaveBandData:
    """Octave band sound pressure levels"""
    freq_63: float = 0.0
    freq_125: float = 0.0
    freq_250: float = 0.0
    freq_500: float = 0.0
    freq_1000: float = 0.0
    freq_2000: float = 0.0
    freq_4000: float = 0.0
    freq_8000: float = 0.0
    
    def to_list(self) -> List[float]:
        """Convert to list for processing"""
        return [self.freq_63, self.freq_125, self.freq_250, self.freq_500, 
                self.freq_1000, self.freq_2000, self.freq_4000, self.freq_8000]
    
    def from_list(self, values: List[float]) -> 'OctaveBandData':
        """Create from list of values"""
        if len(values) >= 8:
            return OctaveBandData(
                freq_63=values[0], freq_125=values[1], freq_250=values[2], freq_500=values[3],
                freq_1000=values[4], freq_2000=values[5], freq_4000=values[6], freq_8000=values[7]
            )
        return self


@dataclass
class NCAnalysisResult:
    """Result of NC rating analysis"""
    nc_rating: int
    octave_band_levels: OctaveBandData
    exceedances: List[Tuple[int, float]]  # (frequency, dB over limit)
    overall_dba: float
    calculation_method: str
    warnings: List[str]
    meets_criteria: bool


@dataclass
class PathResult:
    """Complete path analysis result"""
    path_id: str
    source_noise_dba: float
    terminal_noise_dba: float
    total_attenuation_dba: float
    nc_rating: int
    octave_band_spectrum: List[float]  # 8-band spectrum at terminal
    element_results: List[Dict]
    warnings: List[str]
    calculation_valid: bool
    error_message: Optional[str] = None
    # Optional detailed debug log with per-element spectra and NC transitions
    debug_log: Optional[List[Dict]] = None


class HVACNoiseEngine:
    """
    Unified HVAC noise calculation engine that integrates all specialized calculators
    """
    
    # Use centralized constants
    FREQUENCY_BANDS = AcousticConstants.FREQUENCY_BANDS
    NC_CURVES = AcousticConstants.NC_CURVES
    
    def __init__(self):
        """Initialize the noise engine with all calculators"""
        self.circular_calc = CircularDuctCalculator()
        self.rectangular_calc = RectangularDuctCalculator()
        self.flex_calc = FlexDuctCalculator()
        self.elbow_calc = ElbowTurningVaneCalculator()
        self.junction_calc = JunctionElbowNoiseCalculator()
        self.room_calc = ReceiverRoomSoundCorrection()
        # Note: unlined_rect_calc functionality integrated into rectangular_calc
        self.rect_elbows_calc = RectangularElbowsCalculator()
        
    def calculate_path_noise(self, path_elements: List[PathElement], 
                           path_id: str = "path_1",
                           debug: bool = False,
                           origin: str = "user") -> PathResult:
        """
        Calculate complete noise transmission through HVAC path
        
        Args:
            path_elements: List of PathElement objects defining the path
            path_id: Unique identifier for the path
            
        Returns:
            PathResult with complete analysis
        """
        # Enhanced debugging for calculation pipeline
        debug_export_enabled = os.environ.get('HVAC_DEBUG_EXPORT')
        if debug_export_enabled:
            print(f"\n===== [NOISE ENGINE] START | origin={origin} | path_id={path_id} =====")
            print(f"DEBUG_ENGINE: Received {len(path_elements)} path elements")
            for i, elem in enumerate(path_elements):
                print(f"DEBUG_ENGINE: Element {i}: type={elem.element_type}, id={elem.element_id}")
                if elem.element_type == 'source':
                    print(f"DEBUG_ENGINE:   Source - noise_level={elem.source_noise_level}, bands={elem.octave_band_levels}")
                elif elem.element_type in ['duct', 'elbow', 'junction', 'flex_duct']:
                    length_val = elem.length if elem.length is not None else 0.0
                    flow_val = elem.flow_rate if elem.flow_rate is not None else 0.0
                    width_val = elem.width if elem.width is not None else 0.0
                    height_val = elem.height if elem.height is not None else 0.0
                    print(f"DEBUG_ENGINE:   {elem.element_type} - length={length_val}, flow_rate={flow_val}, duct={width_val}x{height_val}")
                elif elem.element_type == 'terminal':
                    room_vol = elem.room_volume if elem.room_volume is not None else 0.0
                    room_abs = elem.room_absorption if elem.room_absorption is not None else 0.0
                    print(f"DEBUG_ENGINE:   Terminal - room_vol={room_vol}, room_abs={room_abs}")
            
        try:
            warnings_list = []
            element_results = []
            debug_steps: List[Dict] = [] if debug else []
            
            # Validate path
            if not path_elements:
                return PathResult(
                    path_id=path_id,
                    source_noise_dba=0.0,
                    terminal_noise_dba=0.0,
                    total_attenuation_dba=0.0,
                    nc_rating=0,
                    octave_band_spectrum=[0.0] * NUM_OCTAVE_BANDS,
                    element_results=[],
                    warnings=["No path elements provided"],
                    calculation_valid=False,
                    error_message="Empty path"
                )
            
            # Find source element
            source_element = None
            for element in path_elements:
                if element.element_type == 'source':
                    source_element = element
                    break
            
            if not source_element:
                warnings_list.append("No source element found, using default 50 dB(A)")
                current_spectrum = DEFAULT_SPECTRUM_LEVELS.copy()  # Default spectrum
                current_dba = 50.0
                if debug_export_enabled:
                    print(f"DEBUG_ENGINE: No source element - using defaults: dBA={current_dba}, spectrum={current_spectrum}")
            else:
                if source_element.octave_band_levels:
                    current_spectrum = source_element.octave_band_levels.copy()
                    current_dba = source_element.source_noise_level or self._calculate_dba_from_spectrum(current_spectrum)
                    debug_logger.info('HVACEngine', 
                        "Seeded source from spectrum", 
                        {'spectrum': current_spectrum, 'dba': current_dba})
                    if debug_export_enabled:
                        print(f"DEBUG_ENGINE: Source from spectrum - dBA={current_dba}, spectrum={current_spectrum}")
                        print(f"NOISE_PIPELINE: Seed -> dBA={current_dba:.1f}")
                else:
                    # Estimate spectrum from A-weighted level
                    current_spectrum = self._estimate_spectrum_from_dba(source_element.source_noise_level)
                    current_dba = source_element.source_noise_level
                    debug_logger.info('HVACEngine', 
                        "Estimated source spectrum from dBA", 
                        {'input_dba': current_dba, 'estimated_spectrum': current_spectrum})
                    if debug_export_enabled:
                        print(f"DEBUG_ENGINE: Source estimated - dBA={current_dba}, spectrum={current_spectrum}")
                        print(f"NOISE_PIPELINE: Seed (estimated) -> dBA={current_dba:.1f}")

            # Add a pseudo element result for the Source so UI numbering starts at 1
            try:
                source_result = {
                    'element_id': getattr(source_element, 'element_id', 'source_1'),
                    'element_type': 'source',
                    'element_order': 0,
                    'segment_number': 1,
                    'noise_before': current_dba,
                    'noise_after': current_dba,
                    'noise_after_dba': current_dba,
                    'noise_after_spectrum': current_spectrum.copy(),
                    'nc_rating': self._calculate_nc_rating(current_spectrum),
                }
                element_results.append(source_result)
                if debug:
                    debug_steps.append({
                        'order': 0,
                        'element_id': source_result['element_id'],
                        'element_type': 'source',
                        'spectrum_before': current_spectrum.copy(),
                        'spectrum_after': current_spectrum.copy(),
                        'attenuation_spectrum': [0.0] * NUM_OCTAVE_BANDS,
                        'generated_spectrum': [0.0] * NUM_OCTAVE_BANDS,
                        'dba_before': current_dba,
                        'dba_after': current_dba,
                        'nc_before': self._calculate_nc_rating(current_spectrum),
                        'nc_after': self._calculate_nc_rating(current_spectrum),
                    })
            except Exception:
                pass
            
            # Process each element in the path
            total_attenuation_dba = 0.0
            
            # Initialize flow rate tracking from source element
            last_flow_rate: float = 0.0
            if source_element and hasattr(source_element, 'flow_rate') and source_element.flow_rate:
                last_flow_rate = source_element.flow_rate
                if debug_export_enabled:
                    print(f"DEBUG_ENGINE: Initialized last_flow_rate from source: {last_flow_rate:.1f} CFM")
            else:
                if debug_export_enabled:
                    print(f"DEBUG_ENGINE: Source element has no flow_rate, last_flow_rate remains 0.0")
            last_element_with_geometry: Optional[PathElement] = None
            for i, element in enumerate(path_elements):
                if element.element_type == 'source':
                    continue  # Already processed
                
                # Capture noise before this element for legacy UI / debug
                noise_before_dba = current_dba
                spectrum_before = current_spectrum.copy()
                nc_before = self._calculate_nc_rating(spectrum_before)
                
                if debug_export_enabled:
                    print(f"\nDEBUG_ENGINE: Processing element {i}: {element.element_type} ({element.element_id})")
                    print(f"DEBUG_ENGINE:   Input - dBA={noise_before_dba:.1f}, spectrum={[f'{x:.1f}' for x in spectrum_before]}")
                    length_val = element.length if element.length is not None else 0.0
                    flow_val = element.flow_rate if element.flow_rate is not None else 0.0
                    print(f"DEBUG_ENGINE:   Element props - length={length_val}, flow_rate={flow_val}")
                    
                    # Show fitting type if present
                    if hasattr(element, 'fitting_type') and element.fitting_type:
                        print(f"DEBUG_ENGINE:   Fitting type: {element.fitting_type}")
                    
                    # Show duct properties for duct elements
                    if element.element_type == 'duct':
                        if hasattr(element, 'duct_shape') and element.duct_shape:
                            if element.duct_shape == 'circular':
                                print(f"DEBUG_ENGINE:   Duct properties: shape={element.duct_shape}, type={getattr(element, 'duct_type', 'unknown')}, lining={getattr(element, 'lining_thickness', 0)}")
                            else:
                                print(f"DEBUG_ENGINE:   Duct properties: shape={element.duct_shape}, type={getattr(element, 'duct_type', 'unknown')}, lining={getattr(element, 'lining_thickness', 0)}")
                    
                debug_logger.log_element_processing('HVACEngine', 
                    element.element_type, 
                    element.element_id,
                    input_spectrum=spectrum_before)

                # Context-aware junction handling: derive main vs branch flows from neighbors
                if element.element_type == 'junction':
                    try:
                        # Determine upstream and downstream flows
                        print("--------------------------------")
                        print("DEBUG_ENGINE:     Junction context:")
                        print(f"DEBUG_ENGINE:       Last flow rate: {last_flow_rate:.1f} CFM")
                        print(f"DEBUG_ENGINE:       Element flow rate: {element.flow_rate:.1f} CFM")
                        print("--------------------------------")
                        upstream_flow = last_flow_rate or (element.flow_rate or 0.0)
                        # Find next geometric element (skip terminal)
                        next_elem: Optional[PathElement] = None
                        for j in range(i + 1, len(path_elements)):
                            if path_elements[j].element_type not in ['source']:
                                next_elem = path_elements[j]
                                break
                        downstream_flow = (
                            (next_elem.flow_rate if next_elem and hasattr(next_elem, 'flow_rate') else None)
                        ) or (element.flow_rate or 0.0)

                        # Compute branch/main flows
                        flows = [f for f in [upstream_flow, downstream_flow] if (isinstance(f, (int, float)) and f > 0)]
                        if len(flows) >= 2:
                            # For branch takeoff: main continues with reduced flow, branch takes smaller flow
                            if upstream_flow > downstream_flow:
                                main_flow = upstream_flow - downstream_flow  # Continuing main duct flow
                                print("MAIN FLOW SELECTED")
                                print(f"DEBUG_ENGINE:     Main flow: {main_flow:.1f} CFM")
                                branch_flow = downstream_flow  # Branch takeoff flow
                            else:
                                main_flow = upstream_flow
                                print(f"DEBUG_ENGINE:     Main flow: {main_flow:.1f} CFM")
                                branch_flow = downstream_flow
                        elif len(flows) == 1:
                            main_flow = flows[0]
                            branch_flow = flows[0]
                        else:
                            main_flow = element.flow_rate or 0.0
                            branch_flow = element.flow_rate or 0.0

                        # Enhanced debug output for flow logic
                        if debug_export_enabled:
                            print(f"DEBUG_ENGINE:     Flow logic analysis:")
                            print(f"DEBUG_ENGINE:       last_flow_rate: {last_flow_rate:.1f} CFM")
                            print(f"DEBUG_ENGINE:       element.flow_rate: {element.flow_rate:.1f} CFM")
                            print(f"DEBUG_ENGINE:       Upstream flow: {upstream_flow:.1f} CFM")
                            print(f"DEBUG_ENGINE:       Downstream flow: {downstream_flow:.1f} CFM")
                            print(f"DEBUG_ENGINE:       Calculated main flow: {main_flow:.1f} CFM")
                            print(f"DEBUG_ENGINE:       Calculated branch flow: {branch_flow:.1f} CFM")
                            print(f"DEBUG_ENGINE:       Flow ratio (main/branch): {main_flow/branch_flow:.2f}" if branch_flow > 0 else "DEBUG_ENGINE:       Flow ratio: N/A")

                        # Compute cross-sectional areas using available geometry
                        def _area_for(elem: Optional[PathElement]) -> float:
                            try:
                                if elem is None:
                                    return 0.0
                                return self._calculate_duct_area(elem)
                            except Exception:
                                return 0.0

                        branch_area = _area_for(next_elem) or _area_for(element)
                        main_area = _area_for(last_element_with_geometry) or _area_for(element)
                        if main_area <= 0.0:
                            main_area = branch_area or _area_for(element)
                        if branch_area <= 0.0:
                            branch_area = main_area or _area_for(element)

                        # Map fitting hint to junction type
                        fit = (element.fitting_type or '').lower() if hasattr(element, 'fitting_type') else ''
                        jtype = JunctionType.T_JUNCTION
                        if 'x' in fit or 'cross' in fit:
                            jtype = JunctionType.X_JUNCTION
                            print(" USING X JUNCTION")
                        elif 'branch' in fit:
                            jtype = JunctionType.BRANCH_TAKEOFF_90
                            print(" USING BRANCH TAKEOFF 90")
                        elif 'tee' in fit or 't_' in fit:
                            jtype = JunctionType.T_JUNCTION
                            print(" USING T JUNCTION")

                        if debug_export_enabled:
                            print(f"DEBUG_ENGINE:     Junction context: upstream_flow={upstream_flow:.1f}, downstream_flow={downstream_flow:.1f}")
                            print(f"DEBUG_ENGINE:     Areas: main_area={main_area:.3f} ft^2, branch_area={branch_area:.3f} ft^2")
                            print(f"DEBUG_ENGINE:     Fitting hint='{fit}', selected_junction_type={jtype.name}")

                        # Calculate velocities in ft/s for junction calculator
                        branch_velocity_ft_s = branch_flow / (branch_area * 60) if branch_area > 0 else 0
                        main_velocity_ft_s = main_flow / (main_area * 60) if main_area > 0 else 0


                        print(f"DEBUG_ENGINE:     Velocity calculations:")
                        print(f"DEBUG_ENGINE:       Branch velocity: {branch_velocity_ft_s:.3f} ft/s")
                        print(f"DEBUG_ENGINE:       Main velocity: {main_velocity_ft_s:.3f} ft/s")

                        # Calculate spectra using contextual flows/areas
                        spectrum_data = self.junction_calc.calculate_junction_noise_spectrum(
                            branch_flow_rate=branch_flow,
                            branch_cross_sectional_area=max(branch_area, 1e-6),
                            main_flow_rate=main_flow,
                            main_cross_sectional_area=max(main_area, 1e-6),
                            junction_type=jtype
                        )
                        print("--------------------------------")
                        print(f"DEBUG_ENGINE:   JUNCTION CALCULATOR RETURNED DATA: {spectrum_data}")
                        print("--------------------------------")
                        # Decide spectrum based on user override first, then auto heuristic
                        override = None
                        try:
                            # PathElement may carry a hint via fitting_type or extra attribute on upstream element
                            override = getattr(element, 'branch_takeoff_choice', None)
                            if not override and isinstance(last_element_with_geometry, PathElement):
                                override = getattr(last_element_with_geometry, 'branch_takeoff_choice', None)
                        except Exception:
                            override = None
                        if debug_export_enabled:
                            try:
                                print(f"DEBUG_ENGINE:     Junction override preference detected: {override}")
                            except Exception:
                                pass
                        if (jtype == JunctionType.BRANCH_TAKEOFF_90) and override and str(override).lower() in {'main', 'main_duct'}:
                            which = 'main_duct'
                        elif (jtype == JunctionType.BRANCH_TAKEOFF_90) and override and str(override).lower() in {'branch', 'branch_duct'}:
                            which = 'branch_duct'
                        else:
                            # Auto selection with tie-breakers for BRANCH_TAKEOFF_90
                            # Primary rule: branch if downstream flow is smaller than upstream
                            follows_branch = (downstream_flow > 0 and upstream_flow > 0 and downstream_flow < upstream_flow)
                            which = 'branch_duct' if follows_branch else 'main_duct'
                            # Tie-breaker: if flows are approximately equal, prefer branch when branch area is smaller or branch velocity is higher
                            if jtype == JunctionType.BRANCH_TAKEOFF_90 and upstream_flow > 0 and downstream_flow > 0:
                                flow_ratio = downstream_flow / upstream_flow if upstream_flow > 0 else 1.0
                                approx_equal = 0.9 <= flow_ratio <= 1.1
                                try:
                                    if approx_equal:
                                        # Use geometric/velocity cues to infer branch takeoff
                                        prefer_branch = False
                                        try:
                                            prefer_branch = (branch_area > 0 and main_area > 0 and branch_area < main_area)
                                        except Exception:
                                            pass
                                        try:
                                            prefer_branch = prefer_branch or (branch_velocity_ft_s > 0 and main_velocity_ft_s > 0 and branch_velocity_ft_s >= main_velocity_ft_s)
                                        except Exception:
                                            pass
                                        if prefer_branch:
                                            which = 'branch_duct'
                                except Exception:
                                    pass
                        chosen = spectrum_data.get(which) or {}

                        params = spectrum_data.get('parameters', {})
                        print(f"DEBUG_ENGINE:     Junction spectra computed. Using '{which}' spectrum")
                        print(f"DEBUG_ENGINE:     Calc params: vel_ratio={params.get('velocity_ratio', 0):.3f}, main_vel={params.get('main_velocity_ft_s', 0):.3f} ft/s, branch_vel={params.get('branch_velocity_ft_s', 0):.3f} ft/s")
                        try:
                            print(f"DEBUG_ENGINE:     Tie-break info: upstream={upstream_flow:.1f} CFM, downstream={downstream_flow:.1f} CFM, main_area={main_area:.3f} ft^2, branch_area={branch_area:.3f} ft^2, main_vel={main_velocity_ft_s:.3f} ft/s, branch_vel={branch_velocity_ft_s:.3f} ft/s")
                        except Exception:
                            pass

                        # Treat junction results as generated noise (not insertion loss)
                        element_result = {
                            'attenuation_spectrum': [0.0] * NUM_OCTAVE_BANDS,
                            'generated_spectrum': [0.0] * NUM_OCTAVE_BANDS,
                            'attenuation_dba': 0.0,
                            'generated_dba': 0.0
                        }
                        # Convert chosen spectrum to generated noise levels
                        # Junction calculator returns sound power levels in dB (can be negative for very low levels)
                        # These represent generated noise, not insertion loss
                        # Only include generated noise if it's above a reasonable threshold
                        MIN_GENERATED_NOISE_THRESHOLD = -40.0  # dB - ignore very low generated noise
                        for k, freq in enumerate(self.FREQUENCY_BANDS):
                            key = f"{freq}Hz"
                            if key in chosen:
                                val = float(chosen[key])
                                # Only include generated noise if it's above threshold
                                if val > MIN_GENERATED_NOISE_THRESHOLD:
                                    # Convert sound power level to generated noise level
                                    # Add offset to convert to reasonable noise levels for combination
                                    generated_noise = val + 50.0  # Offset to make values reasonable for noise combination
                                    element_result['generated_spectrum'][k] = max(0.0, generated_noise)
                                else:
                                    element_result['generated_spectrum'][k] = 0.0
                        element_result['generated_dba'] = self._calculate_dba_from_spectrum(element_result['generated_spectrum'])

                        if debug_export_enabled:
                            print(f"DEBUG_ENGINE:     Junction generated noise A-weighted={element_result['generated_dba']:.2f} dB")
                            try:
                                gen_vals = element_result['generated_spectrum']
                                if isinstance(gen_vals, list) and gen_vals:
                                    gen_min = min(gen_vals)
                                    gen_max = max(gen_vals)
                                    gen_avg = sum(gen_vals) / len(gen_vals)
                                    print(f"DEBUG_ENGINE:     Generated noise stats: min={gen_min:.1f} dB, max={gen_max:.1f} dB, avg={gen_avg:.1f} dB")
                            except Exception:
                                pass
                    except Exception as _e:
                        # Fallback to legacy per-element calculation on any failure
                        if debug_export_enabled:
                            print(f"DEBUG_ENGINE:     Junction context calc failed; falling back. Error: {_e}")
                        element_result = self._calculate_element_effect(element, current_spectrum, current_dba)
                else:
                    element_result = self._calculate_element_effect(element, current_spectrum, current_dba)
                    print(f"DEBUG_ENGINE:   Element result: {element_result}")
                    print("FALLBACK CONDITION MET - PATH NOISE")
                    print("--------------------------------")
                if debug_export_enabled:
                    att_dba = element_result.get('attenuation_dba') or 0.0
                    gen_dba = element_result.get('generated_dba') or 0.0
                    print(f"DEBUG_ENGINE:   Element result: attenuation_dba={att_dba}, generated_dba={gen_dba}")
                    if element_result.get('error'):
                        print(f"DEBUG_ENGINE:   ERROR in element calculation: {element_result.get('error')}")
                
                element_result['element_id'] = element.element_id
                element_result['element_type'] = element.element_type
                element_result['element_order'] = i
                # Maintain legacy compatibility: some UI expects 'segment_number'
                # Use 1-based index for human-readable ordering
                element_result['segment_number'] = i + 1
                
                # Apply the effect
                if element_result.get('attenuation_spectrum'):
                    attenuation_spectrum = element_result['attenuation_spectrum']
                    if isinstance(attenuation_spectrum, list):
                        debug_logger.debug('HVACEngine', 
                            f"Element {i} attenuation_spectrum", 
                            {'attenuation_spectrum': attenuation_spectrum})
                        
                        # Enhanced debug output for attenuation
                        if debug_export_enabled:
                            print(f"DEBUG_ENGINE:     Before attenuation application:")
                            print(f"DEBUG_ENGINE:       Current spectrum: {[f'{x:.1f}' for x in current_spectrum]}")
                            print(f"DEBUG_ENGINE:       Attenuation spectrum: {[f'{x:.1f}' for x in attenuation_spectrum]}")
                        
                        spectrum_before_attenuation = current_spectrum.copy()
                        # Apply attenuation (subtract)
                        for j in range(min(NUM_OCTAVE_BANDS, len(attenuation_spectrum))):
                            old_level = current_spectrum[j]
                            current_spectrum[j] -= attenuation_spectrum[j]
                            current_spectrum[j] = max(0.0, current_spectrum[j])  # Prevent negative
                            
                            # Debug output for significant attenuation
                            if debug_export_enabled and abs(current_spectrum[j] - old_level) > 0.1:
                                print(f"DEBUG_ENGINE:       Band {j+1} ({self.FREQUENCY_BANDS[j]}Hz): {old_level:.1f} - {attenuation_spectrum[j]:.1f} = {current_spectrum[j]:.1f}")
                        
                        if debug_export_enabled:
                            print(f"DEBUG_ENGINE:     After attenuation application:")
                            print(f"DEBUG_ENGINE:       Final spectrum: {[f'{x:.1f}' for x in current_spectrum]}")
                            
                            # Calculate total attenuation
                            total_attenuation = sum(spectrum_before_attenuation[j] - current_spectrum[j] for j in range(len(current_spectrum)))
                            print(f"DEBUG_ENGINE:       Total attenuation applied: {total_attenuation:.2f} dB")
                
                if element_result.get('generated_spectrum'):
                    generated_spectrum = element_result['generated_spectrum']
                    if isinstance(generated_spectrum, list):
                        debug_logger.debug('HVACEngine', 
                            f"Element {i} generated_spectrum", 
                            {'generated_spectrum': generated_spectrum})
                        
                        # Enhanced debug output for spectrum combination
                        if debug_export_enabled:
                            print(f"DEBUG_ENGINE:     Before spectrum combination:")
                            print(f"DEBUG_ENGINE:       Current spectrum: {[f'{x:.1f}' for x in current_spectrum]}")
                            print(f"DEBUG_ENGINE:       Generated spectrum: {[f'{x:.1f}' for x in generated_spectrum]}")
                        
                        # Add generated noise (handle both positive and negative values)
                        spectrum_before_combination = current_spectrum.copy()
                        for j in range(min(NUM_OCTAVE_BANDS, len(generated_spectrum))):
                            if (j < len(generated_spectrum) and 
                                generated_spectrum[j] is not None and 
                                generated_spectrum[j] > 0):
                                old_level = current_spectrum[j]
                                # Positive generated noise - add to existing spectrum
                                current_spectrum[j] = self._combine_noise_levels(
                                    current_spectrum[j], generated_spectrum[j]
                                )
                                operation = "+"
                                
                                # Debug output for each band combination
                                if debug_export_enabled and abs(current_spectrum[j] - old_level) > 0.1:
                                    print(f"DEBUG_ENGINE:       Band {j+1} ({self.FREQUENCY_BANDS[j]}Hz): {old_level:.1f} {operation} {generated_spectrum[j]:.1f} = {current_spectrum[j]:.1f}")
                        
                        if debug_export_enabled:
                            print(f"DEBUG_ENGINE:     After spectrum combination:")
                            print(f"DEBUG_ENGINE:       Final spectrum: {[f'{x:.1f}' for x in current_spectrum]}")
                            
                            # Calculate total change
                            total_change = sum(current_spectrum[j] - spectrum_before_combination[j] for j in range(len(current_spectrum)))
                            print(f"DEBUG_ENGINE:       Total spectrum change: {total_change:.2f} dB")
                
                # Update A-weighted level
                current_dba = self._calculate_dba_from_spectrum(current_spectrum)
                nc_after = self._calculate_nc_rating(current_spectrum)
                
                if debug_export_enabled:
                    print(f"DEBUG_ENGINE:   Output - dBA={current_dba:.1f}, spectrum={[f'{x:.1f}' for x in current_spectrum]}, NC={nc_after}")
                    print(f"DEBUG_ENGINE:   Change - dBA_delta={current_dba - noise_before_dba:.1f}")
                    # Explicit pipeline log for pass-through clarity
                    try:
                        att_dba_dbg = element_result.get('attenuation_dba') or 0.0
                        gen_dba_dbg = element_result.get('generated_dba') or 0.0
                        print(f"NOISE_PIPELINE: After element {i} ({element.element_type}) -> before={noise_before_dba:.1f} dBA, att={att_dba_dbg:.2f}, gen={gen_dba_dbg:.2f}, after={current_dba:.1f}")
                    except Exception:
                        pass
                
                debug_logger.log_element_processing('HVACEngine', 
                    element.element_type, 
                    element.element_id,
                    output_spectrum=current_spectrum,
                    attenuation_dba=current_dba - noise_before_dba)
                
                # Provide legacy keys expected by UI
                element_result['noise_before'] = noise_before_dba
                element_result['noise_after'] = current_dba
                element_result['noise_after_dba'] = current_dba
                element_result['noise_after_spectrum'] = current_spectrum.copy()
                # Include per-element NC rating for UI summary panels
                try:
                    element_result['nc_rating'] = nc_after
                except Exception:
                    # If NC calculation fails, omit but do not break pipeline
                    pass
                
                element_results.append(element_result)

                # Track last element flow and geometry for next iteration context
                try:
                    if element.element_type not in ['source', 'terminal']:
                        last_flow_rate = float(getattr(element, 'flow_rate', 0.0) or 0.0)
                        last_element_with_geometry = element
                        if debug_export_enabled:
                            print(f"DEBUG_ENGINE:   Flow context update -> last_flow_rate={last_flow_rate:.1f} CFM")
                except Exception:
                    pass

                if debug:
                    debug_steps.append({
                        'order': i,
                        'element_id': element.element_id,
                        'element_type': element.element_type,
                        'spectrum_before': spectrum_before,
                        'attenuation_spectrum': element_result.get('attenuation_spectrum'),
                        'generated_spectrum': element_result.get('generated_spectrum'),
                        'spectrum_after': current_spectrum.copy(),
                        'dba_before': noise_before_dba,
                        'dba_after': current_dba,
                        'nc_before': nc_before,
                        'nc_after': nc_after,
                    })
                
                # Track total attenuation
                if element_result.get('attenuation_dba'):
                    total_attenuation_dba += element_result['attenuation_dba']
            
            # Calculate NC rating
            nc_rating = self._calculate_nc_rating(current_spectrum)
            
            if debug_export_enabled:
                print(f"\nDEBUG_ENGINE: Final calculation results:")
                source_dba = (source_element.source_noise_level if source_element and source_element.source_noise_level is not None else 50.0)
                print(f"DEBUG_ENGINE:   Source dBA: {source_dba:.1f}")
                print(f"DEBUG_ENGINE:   Terminal dBA: {current_dba:.1f}")
                print(f"DEBUG_ENGINE:   Total attenuation: {total_attenuation_dba:.1f}")
                print(f"DEBUG_ENGINE:   NC rating: {nc_rating}")
                print(f"DEBUG_ENGINE:   Final spectrum: {[f'{x:.1f}' for x in current_spectrum]}")
                print(f"DEBUG_ENGINE:   Element results count: {len(element_results)}")
                print(f"DEBUG_ENGINE:   Warnings: {warnings_list}")
                
                # Enhanced summary with spectrum analysis
                print(f"DEBUG_ENGINE:   Spectrum analysis:")
                print(f"DEBUG_ENGINE:     Source spectrum: {[f'{x:.1f}' for x in (source_element.octave_band_levels if source_element and source_element.octave_band_levels else [50.0]*8)]}")
                print(f"DEBUG_ENGINE:     Terminal spectrum: {[f'{x:.1f}' for x in current_spectrum]}")
                
                # Calculate spectrum changes
                if source_element and source_element.octave_band_levels:
                    source_spectrum = source_element.octave_band_levels
                    spectrum_changes = [current_spectrum[i] - source_spectrum[i] for i in range(min(len(current_spectrum), len(source_spectrum)))]
                    print(f"DEBUG_ENGINE:     Spectrum changes: {[f'{x:+.1f}' for x in spectrum_changes]}")
                    
                    # Identify dominant effects
                    max_increase = max(spectrum_changes) if spectrum_changes else 0
                    max_decrease = min(spectrum_changes) if spectrum_changes else 0
                    print(f"DEBUG_ENGINE:     Max spectrum increase: {max_increase:+.1f} dB")
                    print(f"DEBUG_ENGINE:     Max spectrum decrease: {max_decrease:+.1f} dB")
                
                print(f"===== [NOISE ENGINE] END   | origin={origin} | path_id={path_id} | nc={nc_rating} | terminal={current_dba:.1f} dB(A) =====\n")
            
            # Calculate final source dBA for result
            final_source_dba = 50.0  # Default
            if source_element:
                if source_element.source_noise_level is not None:
                    final_source_dba = source_element.source_noise_level
                elif source_element.octave_band_levels:
                    # Calculate from spectrum if available
                    final_source_dba = self._calculate_dba_from_spectrum(source_element.octave_band_levels)
            
            return PathResult(
                path_id=path_id,
                source_noise_dba=final_source_dba,
                terminal_noise_dba=current_dba,
                total_attenuation_dba=total_attenuation_dba,
                nc_rating=nc_rating,
                octave_band_spectrum=current_spectrum,
                element_results=element_results,
                warnings=warnings_list,
                calculation_valid=True,
                debug_log=debug_steps if debug else None
            )
            
        except PathElementError as e:
            return PathResult(
                path_id=path_id,
                source_noise_dba=0.0,
                terminal_noise_dba=0.0,
                total_attenuation_dba=0.0,
                nc_rating=0,
                octave_band_spectrum=[0.0] * 8,
                element_results=[],
                warnings=[],
                calculation_valid=False,
                error_message=f"Path element error: {e}",
                debug_log=debug_steps if debug else None
            )
        except CalculationError as e:
            return PathResult(
                path_id=path_id,
                source_noise_dba=0.0,
                terminal_noise_dba=0.0,
                total_attenuation_dba=0.0,
                nc_rating=0,
                octave_band_spectrum=[0.0] * 8,
                element_results=[],
                warnings=[],
                calculation_valid=False,
                error_message=f"Calculation error: {e}",
                debug_log=debug_steps if debug else None
            )
        except Exception as e:
            return PathResult(
                path_id=path_id,
                source_noise_dba=0.0,
                terminal_noise_dba=0.0,
                total_attenuation_dba=0.0,
                nc_rating=0,
                octave_band_spectrum=[0.0] * 8,
                element_results=[],
                warnings=[],
                calculation_valid=False,
                error_message=f"Unexpected error: {e}",
                debug_log=debug_steps if debug else None
            )
    
    def _calculate_element_effect(self, element: PathElement, 
                                input_spectrum: List[float], 
                                input_dba: float) -> Dict[str, Any]:
        """Calculate the acoustic effect of a single path element"""
        result: Dict[str, Any] = {
            'attenuation_spectrum': None,
            'generated_spectrum': None,
            'attenuation_dba': None,
            'generated_dba': None
        }
        
        debug_export_enabled = os.environ.get('HVAC_DEBUG_EXPORT')
        
        try:
            if debug_export_enabled:
                print(f"DEBUG_ENGINE:     Calculating {element.element_type} effect...")
                print(f"DEBUG_ENGINE:     Element details: id={element.element_id}, length={element.length}, width={element.width}, height={element.height}")
                print(f"DEBUG_ENGINE:     Duct properties: shape={element.duct_shape}, type={element.duct_type}, lining={element.lining_thickness}")
                
            if element.element_type == 'duct':
                if debug_export_enabled:
                    print(f"DEBUG_ENGINE:     -> Calling _calculate_duct_effect for {element.element_id}")
                result = self._calculate_duct_effect(element)
            elif element.element_type == 'elbow':
                if debug_export_enabled:
                    print(f"DEBUG_ENGINE:     -> Calling _calculate_elbow_effect for {element.element_id}")
                result = self._calculate_elbow_effect(element)
            elif element.element_type == 'junction':
                if debug_export_enabled:
                    print(f"DEBUG_ENGINE:     -> Calling _calculate_junction_effect for {element.element_id}")
                    print(f"DEBUG_ENGINE:     -> Junction element detected - will use JunctionElbowNoiseCalculator")
                result = self._calculate_junction_effect(element)
            elif element.element_type == 'flex_duct':
                if debug_export_enabled:
                    print(f"DEBUG_ENGINE:     -> Calling _calculate_flex_duct_effect for {element.element_id}")
                result = self._calculate_flex_duct_effect(element)
            elif element.element_type == 'terminal':
                if debug_export_enabled:
                    print(f"DEBUG_ENGINE:     -> Calling _calculate_terminal_effect for {element.element_id}")
                result = self._calculate_terminal_effect(element)
            else:
                # Unknown element type - pass through
                if debug_export_enabled:
                    print(f"DEBUG_ENGINE:     Unknown element type '{element.element_type}' - passing through")
                pass
                
            if debug_export_enabled:
                att_spec = result.get('attenuation_spectrum')
                gen_spec = result.get('generated_spectrum')
                att_dba = result.get('attenuation_dba') or 0.0
                gen_dba = result.get('generated_dba') or 0.0
                print(f"DEBUG_ENGINE:     Result - att_dba={att_dba}, gen_dba={gen_dba}")
                if att_spec and isinstance(att_spec, list):
                    print(f"DEBUG_ENGINE:     Attenuation spectrum: {[f'{x:.1f}' for x in att_spec if x is not None]}")
                if gen_spec and isinstance(gen_spec, list):
                    print(f"DEBUG_ENGINE:     Generated spectrum: {[f'{x:.1f}' for x in gen_spec if x is not None]}")
                
        except Exception as e:
            result['error'] = str(e)
            if debug_export_enabled:
                print(f"DEBUG_ENGINE:     ERROR in {element.element_type} calculation: {e}")
            
        return result
    
    def _calculate_duct_effect(self, element: PathElement) -> Dict[str, Any]:
        """Calculate duct attenuation effect, including any fittings within the duct segment"""
        result: Dict[str, Any] = {
            'attenuation_spectrum': [0.0] * NUM_OCTAVE_BANDS,
            'generated_spectrum': [0.0] * NUM_OCTAVE_BANDS,
            'attenuation_dba': 0.0,
            'generated_dba': 0.0
        }
        
        debug_export_enabled = os.environ.get('HVAC_DEBUG_EXPORT')
        
        if debug_export_enabled:
            print("================================================")
            if element.duct_shape == 'circular':
                print("INSIDE THE CIRCULAR DUCT CALCULATION")
            else:
                print("INSIDE THE RECTANGULAR DUCT CALCULATION")
            print("================================================")
            print(f"DEBUG_DUCT: Processing duct element: {element.element_id}")
            print(f"DEBUG_DUCT:   Length: {element.length} ft")
            if element.duct_shape == 'circular':
                print(f"DEBUG_DUCT:   Diameter: {element.diameter} in")
            else:
                print(f"DEBUG_DUCT:   Dimensions: {element.width}x{element.height} in")
            print(f"DEBUG_DUCT:   Shape: {element.duct_shape}")
            print(f"DEBUG_DUCT:   Lining: {element.lining_thickness} in")
            print(f"DEBUG_DUCT:   Fitting type: {element.fitting_type}")
        
        try:
            # 1. Calculate duct attenuation (the main purpose of this method)
            if element.duct_shape == 'circular':
                # Use circular duct calculator
                if debug_export_enabled:
                    print(f"DEBUG_DUCT:   Using circular duct calculator")
                    print(f"DEBUG_DUCT:   Diameter: {element.diameter} in, Length: {element.length} ft")
                
                if element.lining_thickness > 0:
                    # Lined circular duct
                    if debug_export_enabled:
                        print(f"DEBUG_DUCT:   Calculating lined circular duct insertion loss")
                        print(f"DEBUG_DUCT:   Lining thickness: {element.lining_thickness} in")
                    
                    for i, freq in enumerate(self.FREQUENCY_BANDS):
                        if freq <= 4000:  # Circular calc supports up to 4000 Hz
                            attenuation = self.circular_calc.calculate_lined_insertion_loss(
                                element.diameter, element.lining_thickness, freq, element.length
                            )
                            result['attenuation_spectrum'][i] = attenuation
                            if debug_export_enabled and i < 3:  # Show first few frequencies
                                print(f"DEBUG_DUCT:     {freq}Hz: {attenuation:.3f} dB")
                else:
                    # Unlined circular duct
                    if debug_export_enabled:
                        print(f"DEBUG_DUCT:   Calculating unlined circular duct attenuation")
                    
                    spectrum = self.circular_calc.get_unlined_attenuation_spectrum(
                        element.diameter, element.length
                    )
                    for i, freq in enumerate(self.FREQUENCY_BANDS):
                        if str(freq) in spectrum:
                            result['attenuation_spectrum'][i] = spectrum[str(freq)]
                            if debug_export_enabled and i < 3:  # Show first few frequencies
                                print(f"DEBUG_DUCT:     {freq}Hz: {spectrum[str(freq)]:.3f} dB")
                            
            else:
                # Rectangular duct
                if element.lining_thickness > 0:
                    # Lined rectangular duct
                    if element.lining_thickness <= 1.0:
                        spectrum = self.rectangular_calc.get_1inch_lining_insertion_loss(
                            element.width, element.height, element.length
                        )
                    else:
                        spectrum = self.rectangular_calc.get_2inch_lining_attenuation(
                            element.width, element.height, element.length
                        )
                    
                    for i, freq in enumerate(self.FREQUENCY_BANDS):
                        if str(freq) in spectrum:
                            result['attenuation_spectrum'][i] = spectrum[str(freq)]
                else:
                    # Unlined rectangular duct
                    spectrum = self.rectangular_calc.get_unlined_attenuation(
                        element.width, element.height, element.length
                    )
                    for i, freq in enumerate(self.FREQUENCY_BANDS):
                        if str(freq) in spectrum:
                            result['attenuation_spectrum'][i] = spectrum[str(freq)]
            
            # Calculate A-weighted attenuation
            result['attenuation_dba'] = self._calculate_dba_from_spectrum(result['attenuation_spectrum'])
            
            if debug_export_enabled:
                print(f"DEBUG_DUCT:   Duct attenuation A-weighted IL (diagnostic): {result['attenuation_dba']:.2f} dB")
                print(f"DEBUG_DUCT:   Duct attenuation spectrum (IL): {[f'{x:.1f}' for x in result['attenuation_spectrum']]}")
            
            # 2. FITTING CALCULATIONS DISABLED
            # Note: Fittings are now modeled as standalone components for better control
            # This section is disabled to prevent fittings from affecting NC calculations
            # Only standalone elbow/junction components will affect path noise
            
            if debug_export_enabled:
                fitting_type_lower = (element.fitting_type or '').lower()
                print(f"DEBUG_DUCT:   Fitting type check (DISABLED):")
                print(f"DEBUG_DUCT:     Raw fitting_type: '{element.fitting_type}'")
                print(f"DEBUG_DUCT:     ⚠️  Fitting calculations are DISABLED - use component-based elbows instead")
            
            # Fitting effects are now disabled - use standalone elbow/junction components instead
            
        except Exception as e:
            result['error'] = f"Duct calculation error: {str(e)}"
            if debug_export_enabled:
                print(f"DEBUG_DUCT:   ERROR: {e}")
        
        if debug_export_enabled:
            if element.duct_shape == 'circular':
                print("RETURNING FROM THE CIRCULAR DUCT CALCULATION")
            else:
                print("RETURNING FROM THE RECTANGULAR DUCT CALCULATION")
            print(f"IL SPECTRUM (attenuation): {result['attenuation_spectrum']}")
            print(f"GENERATED SPECTRUM: {result['generated_spectrum']}")
        
        return result
    
    def _calculate_fitting_effect_for_duct(self, element: PathElement) -> Optional[Dict[str, Any]]:
        """Calculate fitting effects for a duct segment that contains a fitting"""
        debug_export_enabled = os.environ.get('HVAC_DEBUG_EXPORT')
        
        if debug_export_enabled:
            print(f"DEBUG_FITTING: Starting fitting effect calculation for {element.element_id}")
            print(f"DEBUG_FITTING:   Fitting type: '{element.fitting_type}'")
            print(f"DEBUG_FITTING:   Element type: {element.element_type}")
            print(f"DEBUG_FITTING:   Flow rate: {element.flow_rate} CFM")
        
        try:
            fitting_type = element.fitting_type.lower()
            
            if debug_export_enabled:
                print(f"DEBUG_FITTING:   Processing fitting type: '{fitting_type}'")
            
            if fitting_type in ['elbow'] or 'elbow' in fitting_type:
                # Use elbow calculation logic
                if debug_export_enabled:
                    print(f"DEBUG_DUCT:     Calculating elbow fitting effect")
                
                # Calculate elbow insertion loss using rectangular elbows calculator
                attenuation_spectrum = [0.0] * NUM_OCTAVE_BANDS
                lined = (element.lining_thickness or 0.0) > 0.0
                elbow_type = 'square_with_vanes' if (element.num_vanes or 0) > 0 else 'square_no_vanes'
                
                for i, freq in enumerate(self.FREQUENCY_BANDS):
                    try:
                        loss = self.rect_elbows_calc.calculate_elbow_insertion_loss(
                            frequency=freq,
                            width=element.width or 0.0,
                            elbow_type=elbow_type,
                            lined=lined
                        )
                        attenuation_spectrum[i] = float(loss or 0.0)
                        if debug_export_enabled:
                            print(f"DEBUG_FITTING:   ELBOW ATTENUATION SPECTRUM: {attenuation_spectrum[i]}")
                    except Exception as e:
                        if debug_export_enabled:
                            print(f"DEBUG_DUCT:     Error calculating elbow loss at {freq}Hz: {e}")
                        attenuation_spectrum[i] = 0.0
                
                # Calculate generated noise using junction calculator
                duct_area = self._calculate_duct_area(element)
                jtype = JunctionType.ELBOW_90_NO_VANES
                
                if debug_export_enabled:
                    print(f"DEBUG_FITTING:     Duct area: {duct_area:.3f} ft²")
                    print(f"DEBUG_FITTING:     Junction type: {jtype}")
                    print(f"DEBUG_FITTING:     Calling junction calculator for elbow...")
                
                spectrum_data = self.junction_calc.calculate_junction_noise_spectrum(
                    branch_flow_rate=element.flow_rate,
                    branch_cross_sectional_area=duct_area,
                    main_flow_rate=element.flow_rate,
                    main_cross_sectional_area=duct_area,
                    junction_type=jtype
                )
                if debug_export_enabled:
                    print(f"DEBUG_FITTING:   JUNCTION CALCULATOR RETURNED DATA: {spectrum_data}")
                if debug_export_enabled:
                    print(f"DEBUG_FITTING:     Junction calculator returned data")
                    print(f"DEBUG_FITTING:     Available keys: {list(spectrum_data.keys())}")
                
                # For elbows, use the main duct spectrum
                elbow_spectrum = spectrum_data.get('main_duct') or {}
                generated_spectrum = [0.0] * NUM_OCTAVE_BANDS
                for i, freq in enumerate(self.FREQUENCY_BANDS):
                    band_key = f"{freq}Hz"
                    if band_key in elbow_spectrum:
                        generated_spectrum[i] = elbow_spectrum[band_key]
                if debug_export_enabled:
                    print(f"DEBUG_FITTING:   GENERATED SPECTRUM: {generated_spectrum}")
                return {
                    'attenuation_spectrum': attenuation_spectrum,
                    'generated_spectrum': generated_spectrum,
                    'attenuation_dba': self._calculate_dba_from_spectrum(attenuation_spectrum),
                    'generated_dba': self._calculate_dba_from_spectrum(generated_spectrum)
                }
                
            elif (fitting_type in ['junction', 'tee', 'branch', 'branch_takeoff_90', 'branch_takeoff', 'branch_90'] or
                  'junction' in fitting_type or 'tee' in fitting_type or 'branch' in fitting_type):
                # Use junction calculation logic
                if debug_export_enabled:
                    print(f"DEBUG_FITTING:     Calculating junction fitting effect")
                    print(f"DEBUG_FITTING:     Fitting type matches junction pattern")
                
                duct_area = self._calculate_duct_area(element)
                jtype = JunctionType.T_JUNCTION
                if 'x' in fitting_type or 'cross' in fitting_type:
                    jtype = JunctionType.X_JUNCTION
                elif 'branch' in fitting_type:
                    jtype = JunctionType.BRANCH_TAKEOFF_90
                
                if debug_export_enabled:
                    print(f"DEBUG_FITTING:     Duct area: {duct_area:.3f} ft²")
                    print(f"DEBUG_FITTING:     Junction type: {jtype}")
                    print(f"DEBUG_FITTING:     Calling junction calculator...")
                
                spectrum_data = self.junction_calc.calculate_junction_noise_spectrum(
                    branch_flow_rate=element.flow_rate,
                    branch_cross_sectional_area=duct_area,
                    main_flow_rate=element.flow_rate,
                    main_cross_sectional_area=duct_area,
                    junction_type=jtype
                )
                
                if debug_export_enabled:
                    print(f"DEBUG_FITTING:     Junction calculator returned data")
                    print(f"DEBUG_FITTING:     Available keys: {list(spectrum_data.keys())}")
                
                # For junctions, use main duct spectrum
                junction_spectrum = spectrum_data.get('main_duct') or {}
                generated_spectrum = [0.0] * NUM_OCTAVE_BANDS
                for i, freq in enumerate(self.FREQUENCY_BANDS):
                    band_key = f"{freq}Hz"
                    if band_key in junction_spectrum:
                        generated_spectrum[i] = junction_spectrum[band_key]
                
                return {
                    'attenuation_spectrum': [0.0] * NUM_OCTAVE_BANDS,  # Junctions typically don't have insertion loss
                    'generated_spectrum': generated_spectrum,
                    'attenuation_dba': 0.0,
                    'generated_dba': self._calculate_dba_from_spectrum(generated_spectrum)
                }
            
            if debug_export_enabled:
                print(f"DEBUG_FITTING:     No matching fitting type found for: '{fitting_type}'")
            return None
            
        except Exception as e:
            if debug_export_enabled:
                print(f"DEBUG_FITTING:     Error calculating fitting effect: {e}")
            return None
    
    def _calculate_elbow_effect(self, element: PathElement) -> Dict[str, Any]:
        """Calculate elbow generated noise effect"""
        result: Dict[str, Any] = {
            'attenuation_spectrum': [0.0] * NUM_OCTAVE_BANDS,
            'generated_spectrum': [0.0] * NUM_OCTAVE_BANDS,
            'attenuation_dba': 0.0,
            'generated_dba': 0.0
        }
        
        debug_export_enabled = os.environ.get('HVAC_DEBUG_EXPORT')
        
        print(f"╔═══════════════════════════════════════════════════════════════╗")
        print(f"║  ELBOW EFFECT CALCULATION - STARTING                         ║")
        print(f"╚═══════════════════════════════════════════════════════════════╝")
        print(f"DEBUG_ELBOW_ENGINE: Element properties received:")
        print(f"DEBUG_ELBOW_ENGINE:   element.element_id = {getattr(element, 'element_id', 'N/A')}")
        print(f"DEBUG_ELBOW_ENGINE:   element.duct_shape = {getattr(element, 'duct_shape', 'N/A')}")
        print(f"DEBUG_ELBOW_ENGINE:   element.width = {getattr(element, 'width', 'N/A')} in")
        print(f"DEBUG_ELBOW_ENGINE:   element.lining_thickness = {getattr(element, 'lining_thickness', 'N/A')} in")
        print(f"DEBUG_ELBOW_ENGINE:   element.num_vanes = {getattr(element, 'num_vanes', 'N/A')}")
        print(f"DEBUG_ELBOW_ENGINE:   element.vane_chord_length = {getattr(element, 'vane_chord_length', 'N/A')} in")
        
        try:
            # Optional insertion loss due to elbow (rectangular elbows per ASHRAE tables)
            # Apply only for rectangular ducts; circular elbow insertion loss model not integrated here
            attenuation_spectrum: List[float] = [0.0] * NUM_OCTAVE_BANDS
            if (getattr(element, 'duct_shape', 'rectangular') != 'circular'):
                lining_value = element.lining_thickness or 0.0
                lined = lining_value > 0.0
                
                print(f"DEBUG_ELBOW_ENGINE: Rectangular elbow insertion loss calculation:")
                print(f"DEBUG_ELBOW_ENGINE:   lining_value = {lining_value} in")
                print(f"DEBUG_ELBOW_ENGINE:   lined (boolean) = {lined}")
                
                # Determine elbow type from hints
                elbow_type = 'square_with_vanes' if (element.num_vanes or 0) > 0 else 'square_no_vanes'
                print(f"DEBUG_ELBOW_ENGINE:   elbow_type = {elbow_type}")
                
                if lined:
                    print(f"DEBUG_ELBOW_ENGINE:   ✓✓✓ LINING BEING APPLIED IN CALCULATION ✓✓✓")
                    print(f"DEBUG_ELBOW_ENGINE:   Calling rect_elbows_calc with lined=True")
                else:
                    print(f"DEBUG_ELBOW_ENGINE:   ✗✗✗ NO LINING IN CALCULATION ✗✗✗")
                    print(f"DEBUG_ELBOW_ENGINE:   Calling rect_elbows_calc with lined=False")
                
                # Use width in inches; calculator expects per-frequency calls
                for i, freq in enumerate(self.FREQUENCY_BANDS):
                    attenuation_spectrum[i] = float(self.rect_elbows_calc.calculate_elbow_insertion_loss(
                        frequency=freq,
                        width=element.width or 0.0,
                        elbow_type=elbow_type,
                        lined=lined
                    ) or 0.0)
                
                result['attenuation_spectrum'] = attenuation_spectrum
                result['attenuation_dba'] = self._calculate_dba_from_spectrum(attenuation_spectrum)
                
                print(f"DEBUG_ELBOW_ENGINE: Insertion loss calculation complete:")
                print(f"DEBUG_ELBOW_ENGINE:   attenuation_spectrum = {[f'{x:.2f}' for x in attenuation_spectrum]}")
                print(f"DEBUG_ELBOW_ENGINE:   attenuation_dba = {result['attenuation_dba']:.2f} dB")

            if element.vane_chord_length > 0 and element.num_vanes > 0:
                # Elbow with turning vanes - estimate pressure drop if not provided
                pressure_drop = element.pressure_drop if element.pressure_drop else 0.2  # Typical elbow: 0.1-0.3 in. w.g.
                
                if debug_export_enabled:
                    print(f"DEBUG_ENGINE:     Turning vane elbow detected")
                    print(f"DEBUG_ENGINE:       vane_chord_length={element.vane_chord_length} in")
                    print(f"DEBUG_ENGINE:       num_vanes={element.num_vanes}")
                    print(f"DEBUG_ENGINE:       pressure_drop={pressure_drop} in. w.g. {'(estimated)' if not element.pressure_drop else '(provided)'}")
                
                duct_area = self._calculate_duct_area(element)
                spectrum = self.elbow_calc.calculate_complete_spectrum(
                    element.flow_rate, duct_area, element.height,
                    element.vane_chord_length, element.num_vanes,
                    pressure_drop, element.flow_velocity
                )
                
                for i, freq in enumerate(self.FREQUENCY_BANDS):
                    if str(freq) in spectrum:
                        result['generated_spectrum'][i] = spectrum[str(freq)]
            else:
                # Use dedicated rectangular elbows calculator for insertion loss
                if element.duct_shape == 'rectangular':
                    if debug_export_enabled:
                        print(f"DEBUG_ENGINE:     Using rectangular elbows calculator for insertion loss")
                        print(f"DEBUG_ENGINE:     Elbow properties: width={element.width:.1f}\", lined={element.lining_thickness > 0}")
                    
                    # Determine elbow type from fitting hint
                    fit = (element.fitting_type or '').lower() if hasattr(element, 'fitting_type') else ''
                    elbow_type = 'square_with_vanes' if (element.num_vanes or 0) > 0 else 'square_no_vanes'
                    lined = (element.lining_thickness or 0.0) > 0.0
                    
                    # Calculate insertion loss spectrum
                    attenuation_spectrum = []
                    for i, freq in enumerate(self.FREQUENCY_BANDS):
                        try:
                            loss = self.rect_elbows_calc.calculate_elbow_insertion_loss(
                                frequency=freq,
                                width=element.width or 0.0,
                                elbow_type=elbow_type,
                                lined=lined
                            )
                            attenuation_spectrum.append(float(loss or 0.0))
                        except Exception as e:
                            if debug_export_enabled:
                                print(f"DEBUG_ENGINE:     Error calculating elbow loss at {freq}Hz: {e}")
                            attenuation_spectrum.append(0.0)
                    
                    result['attenuation_spectrum'] = attenuation_spectrum
                    result['attenuation_dba'] = self._calculate_dba_from_spectrum(attenuation_spectrum)
                    if debug_export_enabled:
                        print("-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-")
                        print(f"DEBUG_ENGINE:   ELBOW ATTENUATION SPECTRUM: {attenuation_spectrum}")
                        print("-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-")
                    if debug_export_enabled:
                        print(f"DEBUG_ENGINE:     Elbow insertion loss spectrum: {[f'{x:.1f}' for x in attenuation_spectrum]}")
                        print(f"DEBUG_ENGINE:     Elbow insertion loss dBA: {result['attenuation_dba']:.2f}")

                # For generated noise, use junction calculator with elbow type
                duct_area = self._calculate_duct_area(element)
                fit = (element.fitting_type or '').lower() if hasattr(element, 'fitting_type') else ''
                jtype = JunctionType.ELBOW_90_NO_VANES

                if debug_export_enabled:
                    print(f"DEBUG_ENGINE:     Using junction calculator for generated noise")
                    print(f"DEBUG_ENGINE:     Duct area: {duct_area:.3f} ft², Flow rate: {element.flow_rate:.1f} CFM")

                spectrum_data = self.junction_calc.calculate_junction_noise_spectrum(
                    branch_flow_rate=element.flow_rate,
                    branch_cross_sectional_area=duct_area,
                    main_flow_rate=element.flow_rate,
                    main_cross_sectional_area=duct_area,
                    junction_type=jtype
                )

                # For elbows, use the main duct spectrum per Eq (4.25)
                elbow_spectrum = spectrum_data.get('main_duct') or {}
                for i, freq in enumerate(self.FREQUENCY_BANDS):
                    band_key = f"{freq}Hz"
                    if band_key in elbow_spectrum:
                        result['generated_spectrum'][i] = elbow_spectrum[band_key]

                if debug_export_enabled:
                    print(f"DEBUG_ENGINE:     Elbow generated spectrum: {[f'{x:.1f}' for x in result['generated_spectrum']]}")
            
            # Calculate A-weighted generated noise
            result['generated_dba'] = self._calculate_dba_from_spectrum(result['generated_spectrum'])
            
            # Debug: Verify insertion loss propagation
            print(f"╔═══════════════════════════════════════════════════════════════╗")
            print(f"║  ELBOW EFFECT CALCULATION - COMPLETE                         ║")
            print(f"╚═══════════════════════════════════════════════════════════════╝")
            print(f"DEBUG_ELBOW_ENGINE: Final results:")
            print(f"DEBUG_ELBOW_ENGINE:   Insertion loss spectrum: {[f'{x:.2f}' for x in result['attenuation_spectrum']]}")
            print(f"DEBUG_ELBOW_ENGINE:   Insertion loss dBA: {result['attenuation_dba']:.2f}")
            print(f"DEBUG_ELBOW_ENGINE:   Generated noise spectrum: {[f'{x:.2f}' for x in result['generated_spectrum']]}")
            print(f"DEBUG_ELBOW_ENGINE:   Generated noise dBA: {result['generated_dba']:.2f}")
            
            if element.lining_thickness and element.lining_thickness > 0:
                print(f"DEBUG_ELBOW_ENGINE:   ✓ Lining effect included: {element.lining_thickness} in")
            else:
                print(f"DEBUG_ELBOW_ENGINE:   ✗ No lining applied")
                
            if element.vane_chord_length and element.num_vanes:
                print(f"DEBUG_ELBOW_ENGINE:   ✓ Turning vane effect included: {element.num_vanes} vanes, {element.vane_chord_length} in chord")
            else:
                print(f"DEBUG_ELBOW_ENGINE:   ✗ No turning vanes")
            print(f"═══════════════════════════════════════════════════════════════")
            
        except Exception as e:
            result['error'] = f"Elbow calculation error: {str(e)}"
            if debug_export_enabled:
                print(f"DEBUG_ELBOW: Error in elbow calculation: {e}")
            
        return result
    
    def _calculate_junction_effect(self, element: PathElement) -> Dict[str, Any]:
        """Calculate junction generated noise effect"""
        result: Dict[str, Any] = {
            'attenuation_spectrum': None,
            'generated_spectrum': [0.0] * NUM_OCTAVE_BANDS,
            'attenuation_dba': None,
            'generated_dba': 0.0
        }
        
        debug_export_enabled = os.environ.get('HVAC_DEBUG_EXPORT')
        
        try:
            if debug_export_enabled:
                print(f"DEBUG_JUNCTION: Calculating junction effect for element {element.element_id}")
                print(f"DEBUG_JUNCTION:   fitting_type: {element.fitting_type}")
                print(f"DEBUG_JUNCTION:   flow_rate: {element.flow_rate}")
                print(f"DEBUG_JUNCTION:   width: {element.width}, height: {element.height}")
            
            duct_area = self._calculate_duct_area(element)
            # Use the junction calculator's spectrum method with explicit type
            fit = (element.fitting_type or '').lower() if hasattr(element, 'fitting_type') else ''
            jtype = JunctionType.T_JUNCTION
            if 'x' in fit or 'cross' in fit:
                jtype = JunctionType.X_JUNCTION
            elif 'branch' in fit:
                jtype = JunctionType.BRANCH_TAKEOFF_90
            elif 'tee' in fit or 't_' in fit:
                jtype = JunctionType.T_JUNCTION
            
            if debug_export_enabled:
                print(f"DEBUG_JUNCTION:   Mapped fitting_type '{fit}' to junction_type: {jtype}")
                print(f"DEBUG_JUNCTION:   duct_area: {duct_area:.3f} ft²")
                print(f"DEBUG_JUNCTION:   Calling junction_calc.calculate_junction_noise_spectrum...")
            
            spectrum_data = self.junction_calc.calculate_junction_noise_spectrum(
                branch_flow_rate=element.flow_rate,
                branch_cross_sectional_area=duct_area,
                main_flow_rate=element.flow_rate,
                main_cross_sectional_area=duct_area,
                junction_type=jtype
            )
            
            if debug_export_enabled:
                print(f"DEBUG_JUNCTION:   Junction calculator returned spectrum data")
                print(f"DEBUG_JUNCTION:   Available keys: {list(spectrum_data.keys())}")
            
            # For junctions, interpret spectrum as generated noise (not insertion loss)
            junction_spectrum = spectrum_data.get('main_duct') or {}
            MIN_GENERATED_NOISE_THRESHOLD = -40.0  # dB - ignore very low generated noise
            for i, freq in enumerate(self.FREQUENCY_BANDS):
                band_key = f"{freq}Hz"
                if band_key in junction_spectrum:
                    val = float(junction_spectrum[band_key])
                    # Only include generated noise if it's above threshold
                    if val > MIN_GENERATED_NOISE_THRESHOLD:
                        # Convert sound power level to generated noise level
                        generated_noise = val + 50.0  # Offset to make values reasonable for noise combination
                        result['generated_spectrum'][i] = max(0.0, generated_noise)
                    else:
                        result['generated_spectrum'][i] = 0.0
            
            # Calculate A-weighted generated noise (diagnostic)
            result['generated_dba'] = self._calculate_dba_from_spectrum(result['generated_spectrum'])
            
            if debug_export_enabled:
                print(f"DEBUG_JUNCTION:   Generated noise spectrum: {[f'{x:.1f}' for x in result['generated_spectrum']]}")
                print(f"DEBUG_JUNCTION:   Generated noise A-weighted: {result['generated_dba']:.2f} dB")
            
        except Exception as e:
            result['error'] = f"Junction calculation error: {str(e)}"
            if debug_export_enabled:
                print(f"DEBUG_JUNCTION:   ERROR: {e}")
            
        return result
    
    def _calculate_flex_duct_effect(self, element: PathElement) -> Dict[str, Any]:
        """Calculate flexible duct insertion loss effect"""
        result: Dict[str, Any] = {
            'attenuation_spectrum': [0.0] * NUM_OCTAVE_BANDS,
            'generated_spectrum': None,
            'attenuation_dba': 0.0,
            'generated_dba': None
        }
        
        try:
            spectrum = self.flex_calc.get_insertion_loss(element.diameter, element.length)
            
            for i, freq in enumerate(self.FREQUENCY_BANDS):
                if freq in spectrum:
                    result['attenuation_spectrum'][i] = spectrum[freq]
            
            # Calculate A-weighted attenuation
            result['attenuation_dba'] = self._calculate_dba_from_spectrum(result['attenuation_spectrum'])
            
        except Exception as e:
            result['error'] = f"Flex duct calculation error: {str(e)}"
            
        return result
    
    def _calculate_terminal_effect(self, element: PathElement) -> Dict[str, Any]:
        """Calculate terminal unit effect including End Reflection Loss (ERL)"""
        debug_export_enabled = os.environ.get('HVAC_DEBUG_EXPORT')
        
        result: Dict[str, Any] = {
            'attenuation_spectrum': None,
            'generated_spectrum': None,
            'attenuation_dba': None,
            'generated_dba': None
        }
        
        try:
            # 1) End Reflection Loss at terminal
            diameter_in: float = 0.0
            width_in: float = 0.0
            height_in: float = 0.0
            
            try:
                if (getattr(element, 'duct_shape', 'rectangular') or '').lower() == 'circular':
                    diameter_in = float(getattr(element, 'diameter', 0.0) or 0.0)
                    if debug_export_enabled:
                        print(f"DEBUG_ERL: Circular duct - diameter={diameter_in:.2f} inches")
                else:
                    width_in = float(getattr(element, 'width', 0.0) or 0.0)
                    height_in = float(getattr(element, 'height', 0.0) or 0.0)
                    if debug_export_enabled:
                        print(f"DEBUG_ERL: Rectangular duct - width={width_in:.2f}, height={height_in:.2f} inches")
                    if width_in > 0 and height_in > 0:
                        diameter_in = float(compute_effective_diameter_rectangular(width_in, height_in))
                        if debug_export_enabled:
                            print(f"DEBUG_ERL: Effective diameter={diameter_in:.2f} inches")
            except Exception as e:
                diameter_in = 0.0
                if debug_export_enabled:
                    print(f"DEBUG_ERL: Error computing diameter: {e}")

            # Get termination type (flush for grilles/diffusers, free for open terminations)
            termination_type = getattr(element, 'termination_type', 'flush') or 'flush'
            if termination_type not in ['flush', 'free']:
                termination_type = 'flush'
            
            if debug_export_enabled:
                print(f"DEBUG_ERL: Termination type: {termination_type}")
                print(f"DEBUG_ERL: Computing End Reflection Loss...")

            if diameter_in > 0:
                erl_spectrum: List[float] = []
                for freq in self.FREQUENCY_BANDS:
                    try:
                        # Use ASHRAE TABLE28 for frequencies where it's available (<=1000 Hz)
                        # TABLE28 is empirically measured and more accurate than the equation
                        # For frequencies >1000 Hz, use the simplified equation for extrapolation
                        if freq <= 1000:
                            # Use TABLE28 (flush termination, most common)
                            erl_db = float(erl_from_table_flush(
                                diameter_in=diameter_in,
                                frequency_hz=float(freq),
                            ))
                            method_used = "TABLE28"
                        else:
                            # Use equation for frequencies beyond TABLE28 range
                            erl_db = float(erl_from_equation(
                                diameter=diameter_in,
                                frequency_hz=float(freq),
                                diameter_units='in',
                                termination=termination_type,
                            ))
                            method_used = "Equation"
                        
                        if debug_export_enabled:
                            print(f"DEBUG_ERL: {freq}Hz: {erl_db:.2f} dB ({method_used})")
                    except Exception as e:
                        erl_db = 0.0
                        if debug_export_enabled:
                            print(f"DEBUG_ERL: Error computing ERL at {freq}Hz: {e}")
                    erl_spectrum.append(max(0.0, erl_db))

                result['attenuation_spectrum'] = erl_spectrum
                result['attenuation_dba'] = self._calculate_dba_from_spectrum(erl_spectrum)
                
                if debug_export_enabled:
                    print(f"DEBUG_ERL: ERL spectrum (dB): {[f'{x:.2f}' for x in erl_spectrum]}")
                    print(f"Frequency Bands: {self.FREQUENCY_BANDS}")
                    print(f"DEBUG_ERL: ERL A-weighted total: {result['attenuation_dba']:.2f} dB")
                
                debug_logger.debug('HVACEngine', 
                    "Terminal ERL attenuation", 
                    {'diameter_in': diameter_in,
                     'width_in': width_in,
                     'height_in': height_in,
                     'termination_type': termination_type,
                     'attenuation_spectrum': erl_spectrum,
                     'attenuation_dba': result['attenuation_dba']})
            else:
                if debug_export_enabled:
                    print(f"DEBUG_ERL: WARNING - No valid duct dimensions for ERL calculation")
                    print(f"DEBUG_ERL: Element width={width_in}, height={height_in}, diameter={diameter_in}")

            # 2) Optional receiver room correction metadata (non-blocking)
            try:
                if element.room_volume > 0 and element.room_absorption > 0:
                    result['room_correction_available'] = True
                    result['room_volume'] = element.room_volume
                    result['room_absorption'] = element.room_absorption
            except Exception:
                pass
                
        except Exception as e:
            result['error'] = f"Terminal calculation error: {str(e)}"
            if debug_export_enabled:
                print(f"DEBUG_ERL: Terminal calculation error: {e}")
            
        return result
    
    def _calculate_duct_area(self, element: PathElement) -> float:
        """Calculate duct cross-sectional area in square feet"""
        if element.duct_shape == 'circular':
            # Convert diameter from inches to feet
            radius_ft = (element.diameter / 2.0) / 12.0
            return math.pi * radius_ft * radius_ft
        else:
            # Rectangular duct
            width_ft = element.width / 12.0
            height_ft = element.height / 12.0
            return width_ft * height_ft
    
    def _estimate_spectrum_from_dba(self, dba: float) -> List[float]:
        """Estimate octave band spectrum from A-weighted level"""
        return SpectrumProcessor.estimate_spectrum_from_dba(dba)
    
    def _calculate_dba_from_spectrum(self, spectrum: List[float]) -> float:
        """Calculate A-weighted level from octave band spectrum"""
        return SpectrumProcessor.calculate_dba_from_spectrum(spectrum)
    
    def _combine_noise_levels(self, level1: float, level2: float) -> float:
        """Combine two noise levels using logarithmic addition"""
        return SpectrumProcessor.combine_noise_levels(level1, level2)
    
    def _calculate_nc_rating(self, spectrum: List[float]) -> int:
        """Calculate NC rating from octave band spectrum"""
        return SpectrumProcessor.calculate_nc_rating(spectrum)
    
    def get_nc_description(self, nc_rating: int) -> str:
        """Get description of NC rating"""
        return NCRatingUtils.get_nc_description(nc_rating)
    
    def validate_path_elements(self, path_elements: List[PathElement]) -> Tuple[bool, List[str]]:
        """Validate path elements for calculation"""
        warnings = []
        is_valid = True
        
        if not path_elements:
            warnings.append("No path elements provided")
            return False, warnings
        
        # Check for source element
        has_source = any(elem.element_type == 'source' for elem in path_elements)
        if not has_source:
            warnings.append("No source element found")
            is_valid = False
        
        # Validate each element
        for i, element in enumerate(path_elements):
            element_num = i + 1
            
            if element.element_type == 'duct':
                if element.length <= 0:
                    warnings.append(f"Element {element_num}: Invalid duct length ({element.length})")
                    is_valid = False
                
                if element.duct_shape == 'circular':
                    if element.diameter <= 0:
                        warnings.append(f"Element {element_num}: Invalid duct diameter ({element.diameter})")
                        is_valid = False
                else:
                    if element.width <= 0 or element.height <= 0:
                        warnings.append(f"Element {element_num}: Invalid duct dimensions ({element.width}x{element.height})")
                        is_valid = False
            
            elif element.element_type in ['elbow', 'junction']:
                if element.flow_rate <= 0:
                    warnings.append(f"Element {element_num}: Invalid flow rate ({element.flow_rate})")
                    is_valid = False
        
        return is_valid, warnings
    
    # ============================================================================
    # LEGACY API COMPATIBILITY METHODS
    # Provides backward compatibility with the old NoiseCalculator interface
    # ============================================================================
    
    def calculate_hvac_path_noise(self, path_data: Dict, debug: bool = False, origin: str = "user", path_id: Optional[str] = None) -> Dict:
        """
        Legacy API: Calculate noise transmission through an HVAC path from source to terminal
        
        Args:
            path_data: Dictionary containing path information including:
                - source_component: Source component data
                - segments: List of segment data
                - terminal_component: Terminal component data
                
        Returns:
            Dictionary with calculation results (legacy format)
        """
        import os
        debug_export_enabled = os.environ.get('HVAC_DEBUG_EXPORT')
        
        try:
            if debug_export_enabled:
                pid = path_id or str(path_data.get('path_id', 'unknown'))
                print(f"\n===== [HVAC NOISE ENGINE - LEGACY API] START | origin={origin} | path_id={pid} =====")
                print(f"DEBUG_HNE_LEGACY: Input path_data keys: {list(path_data.keys())}")
                
            # Convert path_data to PathElement objects
            path_elements = self._convert_path_data_to_elements(path_data)
            
            if debug_export_enabled:
                print(f"DEBUG_HNE_LEGACY: Converted to {len(path_elements)} PathElements")
                for i, elem in enumerate(path_elements):
                    print(f"DEBUG_HNE_LEGACY:   Element {i}: {elem.element_type} - {elem.element_id}")
                    if elem.element_type == 'source':
                        print(f"DEBUG_HNE_LEGACY:     Source noise_level: {elem.source_noise_level}")
                        print(f"DEBUG_HNE_LEGACY:     Source octave_bands: {elem.octave_band_levels}")
            
            # Use the main calculation method
            result = self.calculate_path_noise(path_elements, path_id=(path_id or "path_1"), debug=debug, origin=origin)
            
            if debug_export_enabled:
                print(f"DEBUG_HNE_LEGACY: Engine returned - valid: {result.calculation_valid}, error: {result.error_message}")
                print(f"DEBUG_HNE_LEGACY: Source dBA: {result.source_noise_dba}, Terminal dBA: {result.terminal_noise_dba}")
                pid = path_id or str(path_data.get('path_id', 'unknown'))
                print(f"===== [HVAC NOISE ENGINE - LEGACY API] END   | origin={origin} | path_id={pid} | valid={result.calculation_valid} =====\n")
            
            # Convert back to the expected legacy format
            return self._convert_result_to_legacy_dict(result)
            
        except Exception as e:
            if debug_export_enabled:
                print(f"DEBUG_HNE_LEGACY: Exception in calculate_hvac_path_noise: {e}")
                import traceback
                print(f"DEBUG_HNE_LEGACY: Traceback: {traceback.format_exc()}")
                pid = path_id or str(path_data.get('path_id', 'unknown'))
                try:
                    print(f"===== [HVAC NOISE ENGINE - LEGACY API] END   | origin={origin} | path_id={pid} | valid=False | error=1 =====\n")
                except Exception:
                    pass
            return {
                'source_noise': 0.0,
                'terminal_noise': 0.0,
                'total_attenuation': 0.0,
                'path_segments': [],
                'nc_rating': 0,
                'calculation_valid': False,
                'error': str(e)
            }
    
    def _convert_path_data_to_elements(self, path_data: Dict) -> List[PathElement]:
        """Convert legacy path data format to PathElement objects"""
        elements = []
        debug_export_enabled = os.environ.get('HVAC_DEBUG_EXPORT')
        
        # Add source element
        source_component = path_data.get('source_component', {})
        if source_component:
            if debug_export_enabled:
                print(f"DEBUG_HNE_LEGACY: Source component data received:")
                print(f"DEBUG_HNE_LEGACY:   Source component keys: {list(source_component.keys())}")
                print(f"DEBUG_HNE_LEGACY:   Source component full data: {source_component}")
                print(f"DEBUG_HNE_LEGACY:   Source component flow_rate: {source_component.get('flow_rate', 'None')}")
                print(f"DEBUG_HNE_LEGACY:   Source component flow_rate type: {type(source_component.get('flow_rate', None))}")
            
            # Get source flow rate from the first segment or source component
            source_flow_rate = source_component.get('flow_rate', 0.0)
            segments = path_data.get('segments', [])
            
            if not source_flow_rate:
                if segments:
                    source_flow_rate = segments[0].get('flow_rate', 0.0)
            
            if debug_export_enabled:
                print(f"DEBUG_HNE_LEGACY: Source CFM assignment:")
                print(f"DEBUG_HNE_LEGACY:   Source component flow_rate: {source_component.get('flow_rate', 'None')}")
                print(f"DEBUG_HNE_LEGACY:   First segment flow_rate: {segments[0].get('flow_rate', 'None') if segments else 'No segments'}")
                print(f"DEBUG_HNE_LEGACY:   Final source flow_rate: {source_flow_rate}")
            
            source_element = PathElement(
                element_type='source',
                element_id='source_1',
                source_noise_level=source_component.get('noise_level', 50.0),
                octave_band_levels=source_component.get('octave_band_levels'),
                flow_rate=source_flow_rate
            )
            elements.append(source_element)
        
        # Add segments
        segments = path_data.get('segments', [])
        for i, segment in enumerate(segments):
            element_type = self._determine_element_type(segment)
            
            # Normalize duct shape nomenclature ('round' -> 'circular')
            shape = segment.get('duct_shape', 'rectangular')
            if isinstance(shape, str):
                sl = shape.lower()
                shape = 'circular' if sl in ('round', 'circular') else 'rectangular'

            # Debug segment CFM assignment
            segment_flow_rate = segment.get('flow_rate', 0.0)
            if debug_export_enabled:
                print(f"DEBUG_HNE_LEGACY: Segment {i+1} CFM assignment:")
                print(f"DEBUG_HNE_LEGACY:   Raw segment flow_rate: {segment_flow_rate}")
                print(f"DEBUG_HNE_LEGACY:   Segment keys: {list(segment.keys())}")
                if 'flow_rate' not in segment:
                    print(f"DEBUG_HNE_LEGACY:   WARNING: No 'flow_rate' key in segment data")
                elif not segment_flow_rate or segment_flow_rate <= 0:
                    print(f"DEBUG_HNE_LEGACY:   WARNING: Segment flow_rate is {segment_flow_rate}, may use defaults")
            
            # Calculate diameter for circular ducts if not provided
            diameter = segment.get('diameter', 0.0)
            if shape == 'circular' and diameter <= 0:
                width = segment.get('duct_width', 12.0)
                height = segment.get('duct_height', 8.0)
                if width > 0 and height > 0:
                    diameter = compute_effective_diameter_rectangular(width, height)
                    if debug_export_enabled:
                        print(f"DEBUG_HNE_LEGACY:   Calculated diameter for circular duct: {diameter:.2f} in from {width}x{height} in")
            
            # Debug: show what's being passed to PathElement
            print(f"╔═══════════════════════════════════════════════════════════════╗")
            print(f"║  CREATING PathElement #{i+1} ({element_type})                ")
            print(f"╚═══════════════════════════════════════════════════════════════╝")
            print(f"DEBUG_PATH_ELEMENT: Creating PathElement from segment data:")
            print(f"DEBUG_PATH_ELEMENT:   element_type = {element_type}")
            print(f"DEBUG_PATH_ELEMENT:   lining_thickness from dict = {segment.get('lining_thickness', 'NOT_IN_DICT')}")
            print(f"DEBUG_PATH_ELEMENT:   vane_chord_length from dict = {segment.get('vane_chord_length', 'NOT_IN_DICT')}")
            print(f"DEBUG_PATH_ELEMENT:   num_vanes from dict = {segment.get('num_vanes', 'NOT_IN_DICT')}")
            print(f"DEBUG_PATH_ELEMENT:   fitting_type from dict = {segment.get('fitting_type', 'NOT_IN_DICT')}")
            
            element = PathElement(
                element_type=element_type,
                element_id=f'segment_{i+1}',
                length=segment.get('length', 0.0),
                width=segment.get('duct_width', 12.0),
                height=segment.get('duct_height', 8.0),
                diameter=diameter,
                duct_shape=shape,
                duct_type=segment.get('duct_type', 'sheet_metal'),
                lining_thickness=segment.get('lining_thickness', 0.0),
                flow_rate=segment_flow_rate,
                flow_velocity=segment.get('flow_velocity', 0.0),
                pressure_drop=segment.get('pressure_drop', 0.0),
                vane_chord_length=segment.get('vane_chord_length', 0.0),
                num_vanes=segment.get('num_vanes', 0),
                room_volume=segment.get('room_volume', 0.0),
                room_absorption=segment.get('room_absorption', 0.0),
                fitting_type=segment.get('fitting_type'),
                branch_takeoff_choice=segment.get('branch_takeoff_choice')
            )
            
            print(f"DEBUG_PATH_ELEMENT: PathElement created with:")
            print(f"DEBUG_PATH_ELEMENT:   element.lining_thickness = {element.lining_thickness}")
            print(f"DEBUG_PATH_ELEMENT:   element.vane_chord_length = {element.vane_chord_length}")
            print(f"DEBUG_PATH_ELEMENT:   element.num_vanes = {element.num_vanes}")
            print(f"═══════════════════════════════════════════════════════════════")
            if debug_export_enabled and element.branch_takeoff_choice:
                try:
                    print(f"DEBUG_HNE_LEGACY:   PathElement {i+1} branch_takeoff_choice={element.branch_takeoff_choice}")
                except Exception:
                    pass
            
            if debug_export_enabled:
                print(f"DEBUG_HNE_LEGACY:   Created PathElement {i+1}:")
                print(f"DEBUG_HNE_LEGACY:     element_type: {element.element_type}")
                print(f"DEBUG_HNE_LEGACY:     element_id: {element.element_id}")
                print(f"DEBUG_HNE_LEGACY:     length: {element.length}")
                print(f"DEBUG_HNE_LEGACY:     width: {element.width}")
                print(f"DEBUG_HNE_LEGACY:     height: {element.height}")
                print(f"DEBUG_HNE_LEGACY:     duct_shape: {element.duct_shape}")
                print(f"DEBUG_HNE_LEGACY:     duct_type: {element.duct_type}")
                print(f"DEBUG_HNE_LEGACY:     lining_thickness: {element.lining_thickness}")
                print(f"DEBUG_HNE_LEGACY:     flow_rate: {element.flow_rate}")
                print(f"DEBUG_HNE_LEGACY:     fitting_type: {element.fitting_type}")
            
            elements.append(element)
        
        # Add terminal element
        terminal_component = path_data.get('terminal_component', {})
        if terminal_component:
            # Propagate duct dimensions from the last segment for End Reflection Loss calculation
            last_width = 0.0
            last_height = 0.0
            last_diameter = 0.0
            last_shape = 'rectangular'
            
            if elements:
                # Find the last element with duct dimensions
                for elem in reversed(elements):
                    if elem.element_type in ['duct', 'flex_duct', 'elbow', 'junction']:
                        last_width = elem.width
                        last_height = elem.height
                        last_diameter = elem.diameter
                        last_shape = elem.duct_shape
                        break
            
            # Get termination type from terminal_component or default to 'flush'
            termination_type = terminal_component.get('termination_type', 'flush')
            if termination_type not in ['flush', 'free']:
                termination_type = 'flush'  # Default to flush for grilles/diffusers
            
            if debug_export_enabled:
                print(f"DEBUG_HNE_LEGACY: Creating terminal element:")
                print(f"DEBUG_HNE_LEGACY:   Propagated dimensions - width={last_width}, height={last_height}, diameter={last_diameter}")
                print(f"DEBUG_HNE_LEGACY:   Duct shape: {last_shape}")
                print(f"DEBUG_HNE_LEGACY:   Termination type: {termination_type}")
            
            terminal_element = PathElement(
                element_type='terminal',
                element_id='terminal_1',
                width=last_width,
                height=last_height,
                diameter=last_diameter,
                duct_shape=last_shape,
                source_noise_level=terminal_component.get('noise_level', 0.0),
                room_volume=terminal_component.get('room_volume', 0.0),
                room_absorption=terminal_component.get('room_absorption', 0.0),
                termination_type=termination_type
            )
            elements.append(terminal_element)
        
        return elements
    
    def _determine_element_type(self, segment: Dict) -> str:
        """Determine the element type based on segment properties"""
        import re
        debug_export_enabled = os.environ.get('HVAC_DEBUG_EXPORT')
        
        # Allow explicit override from builder
        try:
            override = segment.get('element_type')
            if isinstance(override, str):
                ot = override.strip().lower()
                # Normalize common aliases
                if ot == 'flex':
                    ot = 'flex_duct'
                allowed = {'duct', 'junction', 'elbow', 'flex_duct', 'terminal', 'source'}
                if ot in allowed:
                    if debug_export_enabled:
                        print(f"DEBUG_HNE_LEGACY: Explicit element_type override detected: {ot}")
                    return ot
        except Exception:
            pass

        if debug_export_enabled:
            print(f"DEBUG_HNE_LEGACY: Determining element type for segment:")
            print(f"DEBUG_HNE_LEGACY:   duct_type: {segment.get('duct_type')}")
            print(f"DEBUG_HNE_LEGACY:   fitting_type: {segment.get('fitting_type')}")
            print(f"DEBUG_HNE_LEGACY:   length: {segment.get('length')}")
            print(f"DEBUG_HNE_LEGACY:   duct_width: {segment.get('duct_width')}")
            print(f"DEBUG_HNE_LEGACY:   duct_height: {segment.get('duct_height')}")
        
        # Tokenize fitting_type to avoid substring misclassifications
        ft_raw = (segment.get('fitting_type') or '')
        ft = ft_raw.lower()
        tokens = re.findall(r"[a-z0-9]+", ft)
        token_set = set(tokens)

        has_elbow = 'elbow' in token_set
        has_tee_like = ('tee' in token_set) or ('t' in token_set and 'junction' in token_set)
        has_branch = 'branch' in token_set or any(tok.startswith('branch') for tok in tokens)
        has_wye = 'wye' in token_set
        has_cross = 'cross' in token_set or ('x' in token_set and 'junction' in token_set)
        has_junction = ('junction' in token_set) or has_tee_like or has_branch or has_wye or has_cross

        is_pure_fitting = has_elbow or has_junction

        if debug_export_enabled:
            print(f"DEBUG_HNE_LEGACY:   parsed tokens: {tokens}")
            print(f"DEBUG_HNE_LEGACY:   has_elbow={has_elbow}, has_junction={has_junction}")

        # PRIORITY 1: Check if segment has duct dimensions first
        segment_length = segment.get('length', 0.0) or 0.0
        segment_width = segment.get('duct_width', 0.0) or 0.0
        segment_height = segment.get('duct_height', 0.0) or 0.0
        
        if segment_length > 0 or segment_width > 0 or segment_height > 0:
            # Segment has duct dimensions - treat as duct regardless of fitting_type
            if segment.get('duct_type') == 'flexible':
                element_type = 'flex_duct'
            else:
                element_type = 'duct'
            
            if debug_export_enabled:
                print(f"DEBUG_HNE_LEGACY:   Has duct dimensions - treating as {element_type}")
                print(f"DEBUG_HNE_LEGACY:   fitting_type '{segment.get('fitting_type')}' will be handled as additional property")
        else:
            # No duct dimensions - check fitting type
            if debug_export_enabled:
                print(f"DEBUG_HNE_LEGACY:   No duct dimensions - checking fitting type")
            
            if is_pure_fitting:
                if debug_export_enabled:
                    print(f"DEBUG_HNE_LEGACY:   Pure fitting detected - determining type from tokens")
                if segment.get('duct_type') == 'flexible':
                    element_type = 'flex_duct'
                else:
                    element_type = 'elbow' if has_elbow else 'junction'
            else:
                # No fitting type and no duct dimensions - default to duct
                if segment.get('duct_type') == 'flexible':
                    element_type = 'flex_duct'
                else:
                    element_type = 'duct'
        
        if debug_export_enabled:
            print(f"DEBUG_HNE_LEGACY:   Determined element_type: {element_type}")
        
        return element_type
    
    def _convert_result_to_legacy_dict(self, result: PathResult) -> Dict:
        """Convert PathResult to legacy dictionary format"""
        return {
            'source_noise': result.source_noise_dba,
            'terminal_noise': result.terminal_noise_dba,
            'total_attenuation': result.total_attenuation_dba,
            'total_attenuation_dba': result.total_attenuation_dba,
            'path_segments': result.element_results,
            'path_elements': result.element_results,
            'nc_rating': result.nc_rating,
            'calculation_valid': result.calculation_valid,
            'warnings': result.warnings,
            'error': result.error_message,
            'octave_band_spectrum': result.octave_band_spectrum,
            'debug_log': getattr(result, 'debug_log', None)
        }
    
    def calculate_segment_attenuation(self, segment_data: Dict) -> Dict:
        """
        Legacy API: Calculate noise attenuation for a single duct segment
        
        Args:
            segment_data: Dictionary containing segment properties
            
        Returns:
            Dictionary with attenuation calculations
        """
        # Convert to PathElement and use the engine
        shape = segment_data.get('duct_shape', 'rectangular')
        if isinstance(shape, str):
            sl = shape.lower()
            shape = 'circular' if sl in ('round', 'circular') else 'rectangular'

        # Calculate diameter for circular ducts if not provided
        diameter = segment_data.get('diameter', 0.0)
        if shape == 'circular' and diameter <= 0:
            width = segment_data.get('duct_width', 12.0)
            height = segment_data.get('duct_height', 8.0)
            if width > 0 and height > 0:
                diameter = compute_effective_diameter_rectangular(width, height)
        
        element = PathElement(
            element_type=self._determine_element_type(segment_data),
            element_id='temp_segment',
            length=segment_data.get('length', 0.0),
            width=segment_data.get('duct_width', 12.0),
            height=segment_data.get('duct_height', 8.0),
            diameter=diameter,
            duct_shape=shape,
            duct_type=segment_data.get('duct_type', 'sheet_metal'),
            lining_thickness=segment_data.get('lining_thickness', 0.0),
            flow_rate=segment_data.get('flow_rate', 0.0),
            flow_velocity=segment_data.get('flow_velocity', 0.0),
            pressure_drop=segment_data.get('pressure_drop', 0.0),
            vane_chord_length=segment_data.get('vane_chord_length', 0.0),
            num_vanes=segment_data.get('num_vanes', 0),
            fitting_type=segment_data.get('fitting_type')
        )
        
        # Create a dummy input spectrum
        input_spectrum = [50.0] * 8
        input_dba = 50.0
        
        # Calculate effect
        effect = self._calculate_element_effect(element, input_spectrum, input_dba)
        
        # Convert to legacy format
        return {
            'distance_loss': 0.0,  # Not calculated in engine
            'duct_loss': effect.get('attenuation_dba', 0.0),
            'fitting_additions': effect.get('generated_dba', 0.0),
            'total_attenuation': (effect.get('attenuation_dba', 0.0) - effect.get('generated_dba', 0.0)),
            'attenuation_spectrum': effect.get('attenuation_spectrum'),
            'generated_spectrum': effect.get('generated_spectrum')
        }
    
    def calculate_duct_attenuation(self, segment_data: Dict) -> float:
        """
        Legacy API: Calculate noise attenuation due to duct characteristics
        
        Args:
            segment_data: Dictionary containing duct properties
            
        Returns:
            Attenuation in dB
        """
        result = self.calculate_segment_attenuation(segment_data)
        return result.get('duct_loss', 0.0)
    
    def calculate_nc_rating_legacy(self, data: Optional[Any] = None) -> int:
        """
        Legacy API: Determine NC rating using final octave-band data when available.
        
        Args:
            data: Octave band spectrum, dictionary with spectrum, or A-weighted level
            
        Returns:
            NC rating (15-65)
        """
        try:
            spectrum: Optional[List[float]] = None
            
            # Accept dicts from final calculation results
            if isinstance(data, dict):
                bands = data.get('octave_band_spectrum') or data.get('octave_band_levels')
                if isinstance(bands, (list, tuple)):
                    spectrum = [float(x or 0.0) for x in bands[:8]]
            # Accept direct list/tuple of bands
            elif isinstance(data, (list, tuple)):
                spectrum = [float(x or 0.0) for x in list(data)[:8]]
            
            # If we have a spectrum, ensure 8 bands and compute NC from curves
            if spectrum is not None:
                if len(spectrum) < 8:
                    spectrum = spectrum + [0.0] * (8 - len(spectrum))
                return self._calculate_nc_rating(spectrum)
            
            # Fallback: treat as A-weighted overall level mapping
            noise_level = float(data) if isinstance(data, (int, float)) else 0.0
            if noise_level <= 20:
                return 15
            elif noise_level <= 25:
                return 20
            elif noise_level <= 30:
                return 25
            elif noise_level <= 35:
                return 30
            elif noise_level <= 40:
                return 35
            elif noise_level <= 45:
                return 40
            elif noise_level <= 50:
                return 45
            elif noise_level <= 55:
                return 50
            elif noise_level <= 60:
                return 55
            elif noise_level <= 65:
                return 60
            else:
                return 65
        except Exception:
            return 30  # Default NC rating
    
    def combine_noise_sources(self, noise1: float, noise2: float) -> float:
        """
        Legacy API: Combine two noise sources using logarithmic addition
        
        Args:
            noise1: First noise source level (dB)
            noise2: Second noise source level (dB)
            
        Returns:
            Combined noise level (dB)
        """
        return self._combine_noise_levels(noise1, noise2)
    
    def validate_path_data(self, path_data: Dict) -> Tuple[bool, List[str]]:
        """
        Legacy API: Validate HVAC path data for calculation
        
        Args:
            path_data: Path data dictionary
            
        Returns:
            Tuple of (is_valid, list_of_warnings)
        """
        try:
            path_elements = self._convert_path_data_to_elements(path_data)
            return self.validate_path_elements(path_elements)
        except Exception as e:
            return False, [f"Validation error: {str(e)}"]
    
    def analyze_space_nc_compliance(self, noise_level: float, space_type: str, target_nc: Optional[int] = None) -> Dict:
        """
        Legacy API: Analyze NC compliance for a specific space type
        
        Args:
            noise_level: Measured noise level in dB(A)
            space_type: Type of space (office, classroom, etc.)
            target_nc: Optional target NC rating
            
        Returns:
            Dictionary with compliance analysis
        """
        try:
            # Estimate octave band spectrum from A-weighted level
            estimated_spectrum = self._estimate_spectrum_from_dba(noise_level)
            
            # Calculate NC rating
            nc_rating = self._calculate_nc_rating(estimated_spectrum)
            
            # Determine if meets target
            meets_target = True
            if target_nc and nc_rating > target_nc:
                meets_target = False
            
            return {
                'measured_noise_dba': noise_level,
                'nc_rating': nc_rating,
                'octave_band_levels': estimated_spectrum,
                'space_type': space_type,
                'meets_target': meets_target,
                'nc_description': self.get_nc_description(nc_rating),
                'recommendations': self._get_recommendations(nc_rating, target_nc) if not meets_target else []
            }
            
        except Exception as e:
            return {
                'error': str(e),
                'measured_noise_dba': noise_level,
                'nc_rating': self.calculate_nc_rating_legacy(noise_level),
                'analysis_failed': True
            }
    
    def _get_recommendations(self, current_nc: int, target_nc: Optional[int]) -> List[str]:
        """Get noise control recommendations"""
        recommendations = []
        
        if target_nc and current_nc > target_nc:
            improvement_needed = current_nc - target_nc
            
            if improvement_needed <= 5:
                recommendations.append("Consider adding duct lining or acoustic treatment")
            elif improvement_needed <= 10:
                recommendations.append("Add duct lining and consider silencers")
                recommendations.append("Review duct routing to minimize fittings")
            else:
                recommendations.append("Significant noise reduction required")
                recommendations.append("Consider multiple noise control measures")
                recommendations.append("Review entire HVAC system design")
        
        return recommendations
    
    # Legacy alias for backward compatibility
    def calculate_nc_rating(self, data: Optional[Any] = None) -> int:
        """Legacy alias for calculate_nc_rating_legacy"""
        return self.calculate_nc_rating_legacy(data)
    
    # ========================================================================
    # NC RATING ANALYSIS METHODS (from nc_rating_analyzer.py)
    # ========================================================================
    
    def analyze_octave_band_data(self, octave_data: OctaveBandData, target_nc: Optional[int] = None) -> NCAnalysisResult:
        """
        Analyze octave band data to determine NC rating
        
        Args:
            octave_data: Octave band sound pressure levels
            target_nc: Target NC rating for comparison (optional)
            
        Returns:
            NCAnalysisResult with detailed analysis
        """
        levels = octave_data.to_list()
        
        # Determine NC rating
        nc_rating = self.determine_nc_rating(levels)
        
        # Check for exceedances if target NC is specified
        exceedances = []
        meets_criteria = True
        
        if target_nc and target_nc in self.NC_CURVES:
            target_levels = self.NC_CURVES[target_nc]
            for i, (measured, limit) in enumerate(zip(levels, target_levels)):
                if measured > limit:
                    exceedance = measured - limit
                    exceedances.append((self.FREQUENCY_BANDS[i], exceedance))
                    meets_criteria = False
        
        # Calculate overall dB(A) using centralized utility
        overall_dba = SpectrumProcessor.calculate_dba_from_spectrum(levels)
        
        # Generate warnings
        warnings = self.generate_nc_warnings(levels, nc_rating, exceedances)
        
        return NCAnalysisResult(
            nc_rating=nc_rating,
            octave_band_levels=octave_data,
            exceedances=exceedances,
            overall_dba=overall_dba,
            calculation_method="Octave Band Analysis",
            warnings=warnings,
            meets_criteria=meets_criteria
        )
    
    def estimate_octave_bands_from_dba(self, dba_level: float, spectrum_type: str = "typical_hvac") -> OctaveBandData:
        """
        Estimate octave band levels from overall dB(A) level
        
        Args:
            dba_level: Overall A-weighted sound level
            spectrum_type: Type of noise spectrum for estimation
            
        Returns:
            OctaveBandData with estimated levels
        """
        # Typical HVAC spectrum shapes (relative to 1000 Hz)
        spectrum_shapes = {
            "typical_hvac": [5, 3, 1, -1, 0, -2, -4, -6],  # Fan/duct noise
            "fan_noise": [8, 5, 2, -1, 0, -3, -6, -9],     # Centrifugal fan
            "diffuser_noise": [0, -2, -1, 0, 0, -1, -3, -5], # Terminal diffuser
            "duct_breakout": [3, 1, 0, -1, 0, -2, -4, -7],  # Duct wall transmission
            "flat_spectrum": [0, 0, 0, 0, 0, 0, 0, 0]       # Flat across frequencies
        }
        
        shape = spectrum_shapes.get(spectrum_type, spectrum_shapes["typical_hvac"])
        
        # Estimate 1000 Hz level from dB(A)
        # This is an approximation - exact conversion requires iterative calculation
        level_1000 = dba_level - 2  # Typical adjustment for HVAC spectra
        
        # Calculate octave band levels
        octave_levels = []
        for i, relative_level in enumerate(shape):
            band_level = level_1000 + relative_level
            octave_levels.append(max(0, band_level))  # Don't go below 0 dB
        
        return OctaveBandData().from_list(octave_levels)
    
    def determine_nc_rating(self, octave_levels: List[float]) -> int:
        """
        Determine NC rating from octave band levels
        
        Args:
            octave_levels: List of 8 octave band levels
            
        Returns:
            NC rating (15-65)
        """
        if len(octave_levels) != 8:
            return 30  # Default if invalid data
        
        # Find the highest NC curve that is not exceeded by any frequency
        for nc_rating in sorted(self.NC_CURVES.keys()):
            nc_limits = self.NC_CURVES[nc_rating]
            
            # Check if all octave bands are below this NC curve
            exceeds_curve = False
            for measured, limit in zip(octave_levels, nc_limits):
                if measured > limit:
                    exceeds_curve = True
                    break
            
            if not exceeds_curve:
                return nc_rating
        
        # If all curves are exceeded, return highest rating
        return max(self.NC_CURVES.keys())
    
    def generate_nc_warnings(self, levels: List[float], nc_rating: int, exceedances: List[Tuple[int, float]]) -> List[str]:
        """
        Generate analysis warnings based on results
        
        Args:
            levels: Octave band levels
            nc_rating: Determined NC rating
            exceedances: List of frequency exceedances
            
        Returns:
            List of warning messages
        """
        warnings = []
        
        # Check for unusual spectral characteristics
        if len(levels) >= 8:
            # Check for low frequency dominance
            if levels[0] > levels[4] + 10:  # 63 Hz > 1000 Hz + 10 dB
                warnings.append("Low frequency noise dominance detected")
            
            # Check for high frequency emphasis
            if levels[7] > levels[4] + 5:  # 8000 Hz > 1000 Hz + 5 dB
                warnings.append("High frequency noise emphasis detected")
            
            # Check for very low levels
            if max(levels) < 20:
                warnings.append("Very low noise levels - verify measurement accuracy")
        
        # NC rating warnings
        if nc_rating > 50:
            warnings.append("High NC rating - may require noise control measures")
        elif nc_rating < 20:
            warnings.append("Very low NC rating - verify calculations")
        
        # Exceedance warnings
        if exceedances:
            freq_list = [str(freq) for freq, _ in exceedances]
            warnings.append(f"Target NC exceeded at frequencies: {', '.join(freq_list)} Hz")
        
        return warnings
    
    def get_nc_description(self, nc_rating: int) -> str:
        """
        Get description of NC rating suitability
        
        Args:
            nc_rating: NC rating value
            
        Returns:
            Description of suitability for different spaces
        """
        descriptions = {
            15: "Very quiet - Concert halls, broadcasting studios, private offices",
            20: "Quiet - Executive offices, conference rooms, libraries",
            25: "Moderately quiet - Open offices, classrooms, hospitals",
            30: "Moderate - General offices, retail spaces, restaurants",
            35: "Moderately noisy - Cafeterias, gymnasiums, lobbies",
            40: "Noisy - Light industrial, workshops, kitchens",
            45: "Very noisy - Heavy industrial, mechanical rooms",
            50: "Extremely noisy - Factories, transportation terminals",
            55: "Unacceptable for most occupied spaces",
            60: "Unacceptable for occupied spaces except very briefly",
            65: "Hearing protection recommended"
        }
        
        # Find closest NC rating description
        closest_nc = min(descriptions.keys(), key=lambda x: abs(x - nc_rating))
        base_desc = descriptions.get(closest_nc, "Unknown criteria")
        
        if nc_rating != closest_nc:
            return f"NC-{nc_rating}: Between NC-{closest_nc} criteria - {base_desc}"
        else:
            return f"NC-{nc_rating}: {base_desc}"
    
    def compare_to_standards(self, nc_rating: int, space_type: str) -> Dict[str, any]:
        """
        Compare NC rating to recommended standards for different space types
        
        Args:
            nc_rating: Measured NC rating
            space_type: Type of space (office, classroom, etc.)
            
        Returns:
            Dictionary with comparison results
        """
        # Recommended NC ratings for different space types
        standards = {
            "private_office": {"recommended": 25, "maximum": 30},
            "open_office": {"recommended": 30, "maximum": 35},
            "conference_room": {"recommended": 20, "maximum": 25},
            "classroom": {"recommended": 25, "maximum": 30},
            "library": {"recommended": 20, "maximum": 25},
            "hospital_room": {"recommended": 25, "maximum": 30},
            "restaurant": {"recommended": 35, "maximum": 40},
            "retail": {"recommended": 35, "maximum": 40},
            "gymnasium": {"recommended": 40, "maximum": 45},
            "lobby": {"recommended": 35, "maximum": 40},
            "corridor": {"recommended": 35, "maximum": 40}
        }
        
        standard = standards.get(space_type.lower().replace(" ", "_"), 
                                {"recommended": 30, "maximum": 35})
        
        recommended = standard["recommended"]
        maximum = standard["maximum"]
        
        # Determine compliance
        if nc_rating <= recommended:
            compliance = "Excellent"
            status = "Meets recommended criteria"
        elif nc_rating <= maximum:
            compliance = "Acceptable"
            status = "Meets maximum criteria but exceeds recommended"
        else:
            compliance = "Non-compliant"
            status = f"Exceeds maximum criteria by {nc_rating - maximum} NC points"
        
        return {
            "space_type": space_type,
            "measured_nc": nc_rating,
            "recommended_nc": recommended,
            "maximum_nc": maximum,
            "compliance": compliance,
            "status": status,
            "improvement_needed": max(0, nc_rating - maximum)
        }
    
    def recommend_noise_control(self, analysis_result: NCAnalysisResult, target_nc: int) -> List[str]:
        """
        Recommend noise control measures based on analysis
        
        Args:
            analysis_result: NC analysis result
            target_nc: Target NC rating to achieve
            
        Returns:
            List of recommended noise control measures
        """
        recommendations = []
        
        if analysis_result.nc_rating <= target_nc:
            recommendations.append("Current noise levels meet target criteria")
            return recommendations
        
        reduction_needed = analysis_result.nc_rating - target_nc
        
        # General recommendations based on reduction needed
        if reduction_needed <= 5:
            recommendations.extend([
                "Consider adding duct silencers in main supply ducts",
                "Install flexible duct connections at equipment",
                "Add acoustic lining to supply and return ducts"
            ])
        elif reduction_needed <= 10:
            recommendations.extend([
                "Install high-performance duct silencers",
                "Relocate noisy equipment away from quiet spaces",
                "Add vibration isolation to mechanical equipment",
                "Consider variable speed drives to reduce fan noise"
            ])
        else:
            recommendations.extend([
                "Major noise control measures required",
                "Consider equipment replacement with quieter alternatives",
                "Install sound-rated mechanical room construction",
                "Add multiple stages of silencing in ductwork",
                "Evaluate system design for noise optimization"
            ])
        
        # Frequency-specific recommendations
        levels = analysis_result.octave_band_levels.to_list()
        if len(levels) >= 8:
            # Low frequency problems
            if levels[0] > levels[4] + 10 or levels[1] > levels[4] + 8:
                recommendations.append("Address low frequency noise with equipment isolation and structural modifications")
            
            # High frequency problems  
            if levels[6] > levels[4] + 5 or levels[7] > levels[4] + 5:
                recommendations.append("Add high frequency absorption and consider diffuser design")
        
        return recommendations


# ============================================================================
# LEGACY COMPATIBILITY WRAPPER CLASS
# Provides complete backward compatibility with the old NoiseCalculator class
# ============================================================================

class NoiseCalculator:
    """
    Legacy compatibility wrapper for HVACNoiseEngine
    
    This class provides complete backward compatibility with the old NoiseCalculator
    interface while delegating all calculations to the unified HVACNoiseEngine.
    
    DEPRECATED: Use HVACNoiseEngine directly for new code.
    """
    
    # Use centralized constants for backward compatibility
    NC_FREQUENCIES = AcousticConstants.FREQUENCY_BANDS
    NC_CURVES = AcousticConstants.NC_CURVES
    
    def __init__(self):
        """Initialize the compatibility wrapper with HVACNoiseEngine"""
        import warnings
        warnings.warn(
            "NoiseCalculator is deprecated. Use HVACNoiseEngine directly for new code.",
            DeprecationWarning,
            stacklevel=2
        )
        self.hvac_engine = HVACNoiseEngine()
    
    def calculate_hvac_path_noise(self, path_data: Dict, debug: bool = False, origin: str = "user", path_id: Optional[str] = None) -> Dict:
        """Legacy wrapper: Calculate noise transmission through an HVAC path"""
        return self.hvac_engine.calculate_hvac_path_noise(path_data, debug, origin, path_id)
    
    def calculate_segment_attenuation(self, segment_data: Dict) -> Dict:
        """Legacy wrapper: Calculate noise attenuation for a single duct segment"""
        return self.hvac_engine.calculate_segment_attenuation(segment_data)
    
    def calculate_duct_attenuation(self, segment_data: Dict) -> float:
        """Legacy wrapper: Calculate noise attenuation due to duct characteristics"""
        return self.hvac_engine.calculate_duct_attenuation(segment_data)
    
    def calculate_nc_rating(self, data: Optional[Any] = None) -> int:
        """Legacy wrapper: Determine NC rating"""
        return self.hvac_engine.calculate_nc_rating_legacy(data)
    
    def combine_noise_sources(self, noise1: float, noise2: float) -> float:
        """Legacy wrapper: Combine two noise sources using logarithmic addition"""
        return self.hvac_engine.combine_noise_sources(noise1, noise2)
    
    def get_nc_criteria_description(self, nc_rating: int) -> str:
        """Legacy wrapper: Get description of NC rating criteria"""
        return self.hvac_engine.get_nc_description(nc_rating)
    
    def validate_path_data(self, path_data: Dict) -> Tuple[bool, List[str]]:
        """Legacy wrapper: Validate HVAC path data for calculation"""
        return self.hvac_engine.validate_path_data(path_data)
    
    def analyze_space_nc_compliance(self, noise_level: float, space_type: str, target_nc: Optional[int] = None) -> Dict:
        """Legacy wrapper: Analyze NC compliance for a specific space type"""
        return self.hvac_engine.analyze_space_nc_compliance(noise_level, space_type, target_nc)


# ============================================================================
# NC RATING ANALYZER COMPATIBILITY WRAPPER CLASS
# Provides complete backward compatibility with the old NCRatingAnalyzer class
# ============================================================================

class NCRatingAnalyzer:
    """
    Compatibility wrapper for NCRatingAnalyzer functionality
    
    DEPRECATED: Use HVACNoiseEngine directly for new code
    This wrapper provides backward compatibility for existing code
    """
    
    def __init__(self):
        """Initialize with deprecation warning"""
        warnings.warn(
            "NCRatingAnalyzer is deprecated. Use HVACNoiseEngine for new code.",
            DeprecationWarning,
            stacklevel=2
        )
        self.hvac_engine = HVACNoiseEngine()
    
    # Legacy NC curves and frequencies - redirect to centralized constants
    @property
    def NC_CURVES(self) -> Dict[int, List[float]]:
        """Legacy property: NC curves data"""
        return self.hvac_engine.NC_CURVES
    
    @property
    def FREQUENCIES(self) -> List[int]:
        """Legacy property: Frequency bands"""
        return self.hvac_engine.FREQUENCY_BANDS
    
    @property
    def A_WEIGHTING(self) -> List[float]:
        """Legacy property: A-weighting factors"""
        return AcousticConstants.A_WEIGHTING
    
    def analyze_octave_band_data(self, octave_data: OctaveBandData, target_nc: Optional[int] = None) -> NCAnalysisResult:
        """Legacy wrapper: Analyze octave band data to determine NC rating"""
        return self.hvac_engine.analyze_octave_band_data(octave_data, target_nc)
    
    def estimate_octave_bands_from_dba(self, dba_level: float, spectrum_type: str = "typical_hvac") -> OctaveBandData:
        """Legacy wrapper: Estimate octave band levels from overall dB(A) level"""
        return self.hvac_engine.estimate_octave_bands_from_dba(dba_level, spectrum_type)
    
    def determine_nc_rating(self, octave_levels: List[float]) -> int:
        """Legacy wrapper: Determine NC rating from octave band levels"""
        return self.hvac_engine.determine_nc_rating(octave_levels)
    
    def calculate_overall_dba(self, octave_levels: List[float]) -> float:
        """Legacy wrapper: Calculate overall A-weighted sound level from octave bands"""
        return SpectrumProcessor.calculate_dba_from_spectrum(octave_levels)
    
    def generate_warnings(self, levels: List[float], nc_rating: int, exceedances: List[Tuple[int, float]]) -> List[str]:
        """Legacy wrapper: Generate analysis warnings based on results"""
        return self.hvac_engine.generate_nc_warnings(levels, nc_rating, exceedances)
    
    def get_nc_description(self, nc_rating: int) -> str:
        """Legacy wrapper: Get description of NC rating suitability"""
        return self.hvac_engine.get_nc_description(nc_rating)
    
    def compare_to_standards(self, nc_rating: int, space_type: str) -> Dict[str, any]:
        """Legacy wrapper: Compare NC rating to recommended standards for different space types"""
        return self.hvac_engine.compare_to_standards(nc_rating, space_type)
    
    def recommend_noise_control(self, analysis_result: NCAnalysisResult, target_nc: int) -> List[str]:
        """Legacy wrapper: Recommend noise control measures based on analysis"""
        return self.hvac_engine.recommend_noise_control(analysis_result, target_nc)