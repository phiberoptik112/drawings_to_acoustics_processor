"""
Junction and Elbow Generated Noise Calculations
Based on ASHRAE 1991 Algorithms for HVAC Acoustics

This script implements calculations for:
1. Regenerated sound power levels in branch ducts associated with air flowing in duct turns and junctions
2. Applies to 90° elbows without turning vanes, X-junctions, T-junctions, and 90° branch takeoffs
3. Includes corrections for rounding effects and upstream turbulence

Equations implemented:
- Main equation (4.13): L_w(fo)_b = L_b(fo) + Dr + DT
- Branch sound power level (4.14): L_b(fo) = K_J + 10*log10(f/41) + 50*log10(U_B) + 10*log10(S_B) + 10*log10(D_B)
- Equivalent diameter for rectangular ducts (4.15): D_B = (4*S_B/π)^0.5
- Flow velocity (4.16): U_B = Q_B/(S_B*60)
- Rounding correction (4.17): Dr = (1.0 - RD/0.13) * (6.793 - 1.86*log10(S_t))
- Rounding parameter (4.18): RD = R/(12*D_B)
- Strouhal number (4.19): S_t = f*D_B/U_B
- Turbulence correction (4.20): DT = -1.667 + 1.8*m - 0.133*m²
- Velocity ratio (4.21): m = U_M/U_B
- Characteristic spectrum (4.22): K_J = -21.6 + 12.388*m^0.4751 - 16.482*m^(-0.3071)*log10(S_t) - 5.047*m^(-0.2372)*(log10(S_t))²
- Main duct sound power levels for different junction types (4.23-4.26)

Author: HVAC Acoustics Calculator
Date: 2024
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from typing import Tuple, Dict, List, Optional, Union
import warnings
from enum import Enum

# Set up plotting style
plt.style.use('seaborn-v0_8')
sns.set_palette("husl")

class JunctionType(Enum):
    """Enumeration of junction types."""
    X_JUNCTION = "x_junction"
    T_JUNCTION = "t_junction"
    ELBOW_90_NO_VANES = "elbow_90_no_vanes"
    BRANCH_TAKEOFF_90 = "branch_takeoff_90"

class DuctShape(Enum):
    """Enumeration of duct shapes."""
    CIRCULAR = "circular"
    RECTANGULAR = "rectangular"

class JunctionElbowNoiseCalculator:
    """
    Calculator for junction and elbow generated noise based on ASHRAE 1991 standards.
    """
    
    def __init__(self):
        """Initialize the calculator with standard octave bands."""
        self._initialize_octave_bands()
        
    def _initialize_octave_bands(self):
        """Initialize standard octave band center frequencies."""
        self.octave_bands = [63, 125, 250, 500, 1000, 2000, 4000, 8000]  # Hz
        
    def calculate_equivalent_diameter(self, cross_sectional_area: float, 
                                    duct_shape: DuctShape = DuctShape.RECTANGULAR,
                                    diameter: Optional[float] = None) -> float:
        """
        Calculate equivalent diameter for circular or rectangular ducts.
        
        Args:
            cross_sectional_area: Cross-sectional area in ft²
            duct_shape: Shape of the duct (circular or rectangular)
            diameter: Diameter in ft (required for circular ducts)
            
        Returns:
            Equivalent diameter in ft
        """
        if duct_shape == DuctShape.CIRCULAR:
            if diameter is None:
                raise ValueError("Diameter must be provided for circular ducts")
            return diameter
        elif duct_shape == DuctShape.RECTANGULAR:
            # Equation (4.15): D_B = (4*S_B/π)^0.5
            return np.sqrt(4 * cross_sectional_area / np.pi)
        else:
            raise ValueError(f"Unsupported duct shape: {duct_shape}")
    
    def calculate_flow_velocity(self, volume_flow_rate: float, 
                              cross_sectional_area: float) -> float:
        """
        Calculate flow velocity from volume flow rate and cross-sectional area.
        
        Args:
            volume_flow_rate: Volume flow rate in ft³/min
            cross_sectional_area: Cross-sectional area in ft²
            
        Returns:
            Flow velocity in ft/s
        """
        # Equation (4.16): U_B = Q_B/(S_B*60)
        return volume_flow_rate / (cross_sectional_area * 60)
    
    def calculate_velocity_ratio(self, main_duct_velocity: float, 
                               branch_duct_velocity: float) -> float:
        """
        Calculate velocity ratio between main and branch ducts.
        
        Args:
            main_duct_velocity: Flow velocity in main duct (ft/s)
            branch_duct_velocity: Flow velocity in branch duct (ft/s)
            
        Returns:
            Velocity ratio m = U_M/U_B
        """
        # Equation (4.21): m = U_M/U_B
        return main_duct_velocity / branch_duct_velocity
    
    def calculate_strouhal_number(self, frequency: float, equivalent_diameter: float,
                                flow_velocity: float) -> float:
        """
        Calculate Strouhal number.
        
        Args:
            frequency: Frequency in Hz
            equivalent_diameter: Equivalent diameter in ft
            flow_velocity: Flow velocity in ft/s
            
        Returns:
            Strouhal number
        """
        # Equation (4.19): S_t = f*D_B/U_B
        return frequency * equivalent_diameter / flow_velocity
    
    def calculate_rounding_parameter(self, radius: float, equivalent_diameter: float) -> float:
        """
        Calculate rounding parameter RD.
        
        Args:
            radius: Radius of bend or elbow in inches
            equivalent_diameter: Equivalent diameter in ft
            
        Returns:
            Rounding parameter RD
        """
        # Equation (4.18): RD = R/(12*D_B)
        return radius / (12 * equivalent_diameter)
    
    def calculate_rounding_correction(self, rounding_parameter: float, 
                                    strouhal_number: float) -> float:
        """
        Calculate rounding correction Dr.
        
        Args:
            rounding_parameter: Rounding parameter RD
            strouhal_number: Strouhal number S_t
            
        Returns:
            Rounding correction Dr
        """
        # Equation (4.17): Dr = (1.0 - RD/0.13) * (6.793 - 1.86*log10(S_t))
        if strouhal_number <= 0:
            return 0.0
        
        log_st = np.log10(strouhal_number)
        return (1.0 - rounding_parameter / 0.13) * (6.793 - 1.86 * log_st)
    
    def calculate_turbulence_correction(self, velocity_ratio: float) -> float:
        """
        Calculate turbulence correction DT.
        
        Args:
            velocity_ratio: Velocity ratio m = U_M/U_B
            
        Returns:
            Turbulence correction DT
        """
        # Equation (4.20): DT = -1.667 + 1.8*m - 0.133*m²
        return -1.667 + 1.8 * velocity_ratio - 0.133 * velocity_ratio**2
    
    def calculate_characteristic_spectrum(self, velocity_ratio: float, 
                                       strouhal_number: float) -> float:
        """
        Calculate characteristic spectrum K_J.
        
        Args:
            velocity_ratio: Velocity ratio m = U_M/U_B
            strouhal_number: Strouhal number S_t
            
        Returns:
            Characteristic spectrum K_J
        """
        if strouhal_number <= 0:
            return 0.0
        
        # Equation (4.22): K_J = -21.6 + 12.388*m^0.4751 - 16.482*m^(-0.3071)*log10(S_t) - 5.047*m^(-0.2372)*(log10(S_t))²
        log_st = np.log10(strouhal_number)
        m = velocity_ratio
        
        k_j = (-21.6 + 
               12.388 * m**0.4751 - 
               16.482 * m**(-0.3071) * log_st - 
               5.047 * m**(-0.2372) * log_st**2)
        
        return k_j
    
    def calculate_branch_sound_power_level(self, frequency: float, 
                                         equivalent_diameter: float,
                                         flow_velocity: float, 
                                         cross_sectional_area: float,
                                         characteristic_spectrum: float) -> float:
        """
        Calculate branch sound power level L_b(fo).
        
        Args:
            frequency: Frequency in Hz
            equivalent_diameter: Equivalent diameter in ft
            flow_velocity: Flow velocity in ft/s
            cross_sectional_area: Cross-sectional area in ft²
            characteristic_spectrum: Characteristic spectrum K_J
            
        Returns:
            Branch sound power level in dB
        """
        # Equation (4.14): L_b(fo) = K_J + 10*log10(f/41) + 50*log10(U_B) + 10*log10(S_B) + 10*log10(D_B)
        if frequency <= 0 or flow_velocity <= 0 or cross_sectional_area <= 0 or equivalent_diameter <= 0:
            return 0.0
        
        l_b = (characteristic_spectrum + 
               10 * np.log10(frequency / 41) + 
               50 * np.log10(flow_velocity) + 
               10 * np.log10(cross_sectional_area) + 
               10 * np.log10(equivalent_diameter))
        
        return l_b
    
    def calculate_main_duct_sound_power_level(self, branch_sound_power: float,
                                            junction_type: JunctionType,
                                            main_duct_diameter: float,
                                            branch_duct_diameter: float) -> float:
        """
        Calculate main duct sound power level based on junction type.
        
        Args:
            branch_sound_power: Branch sound power level in dB
            junction_type: Type of junction or elbow
            main_duct_diameter: Main duct equivalent diameter in ft
            branch_duct_diameter: Branch duct equivalent diameter in ft
            
        Returns:
            Main duct sound power level in dB
        """
        if junction_type == JunctionType.X_JUNCTION:
            # Equation (4.23): L_w(fo)_m = L_w(fo)_b + 20*log10(D_M/D_B) + 3
            return branch_sound_power + 20 * np.log10(main_duct_diameter / branch_duct_diameter) + 3
        
        elif junction_type == JunctionType.T_JUNCTION:
            # Equation (4.24): L_w(fo)_m = L_w(fo)_b + 3
            return branch_sound_power + 3
        
        elif junction_type == JunctionType.ELBOW_90_NO_VANES:
            # Equation (4.25): L_w(fo)_m = L_w(fo)_b
            return branch_sound_power
        
        elif junction_type == JunctionType.BRANCH_TAKEOFF_90:
            # Equation (4.26): L_w(fo)_m = L_w(fo)_b + 20*log10(D_M/D_B)
            return branch_sound_power + 20 * np.log10(main_duct_diameter / branch_duct_diameter)
        
        else:
            raise ValueError(f"Unsupported junction type: {junction_type}")
    
    def calculate_total_branch_sound_power(self, branch_sound_power: float,
                                         rounding_correction: float,
                                         turbulence_correction: float = 0.0) -> float:
        """
        Calculate total branch sound power level including corrections.
        
        Args:
            branch_sound_power: Branch sound power level in dB
            rounding_correction: Rounding correction Dr
            turbulence_correction: Turbulence correction DT (default 0.0)
            
        Returns:
            Total branch sound power level in dB
        """
        # Equation (4.13): L_w(fo)_b = L_b(fo) + Dr + DT
        return branch_sound_power + rounding_correction + turbulence_correction
    
    def calculate_junction_noise_spectrum(self, 
                                        # Branch duct parameters
                                        branch_flow_rate: float,
                                        branch_cross_sectional_area: float,
                                        main_flow_rate: float,
                                        main_cross_sectional_area: float,
                                        # Optional parameters
                                        branch_duct_shape: DuctShape = DuctShape.RECTANGULAR,
                                        branch_diameter: Optional[float] = None,
                                        main_duct_shape: DuctShape = DuctShape.RECTANGULAR,
                                        main_diameter: Optional[float] = None,
                                        junction_type: JunctionType = JunctionType.T_JUNCTION,
                                        radius: float = 0.0,
                                        turbulence_present: bool = False) -> Dict[str, Dict[str, float]]:
        """
        Calculate complete noise spectrum for a junction or elbow.
        
        Args:
            branch_flow_rate: Branch duct volume flow rate (ft³/min)
            branch_cross_sectional_area: Branch duct cross-sectional area (ft²)
            branch_duct_shape: Branch duct shape
            branch_diameter: Branch duct diameter (ft, for circular ducts)
            main_flow_rate: Main duct volume flow rate (ft³/min)
            main_cross_sectional_area: Main duct cross-sectional area (ft²)
            main_duct_shape: Main duct shape
            main_diameter: Main duct diameter (ft, for circular ducts)
            junction_type: Type of junction or elbow
            radius: Radius of bend or elbow (inches)
            turbulence_present: Whether upstream turbulence is present
            
        Returns:
            Dictionary containing noise spectra for branch and main ducts
        """
        # Calculate equivalent diameters
        branch_equiv_diameter = self.calculate_equivalent_diameter(
            branch_cross_sectional_area, branch_duct_shape, branch_diameter)
        main_equiv_diameter = self.calculate_equivalent_diameter(
            main_cross_sectional_area, main_duct_shape, main_diameter)
        
        # Calculate flow velocities
        branch_velocity = self.calculate_flow_velocity(branch_flow_rate, branch_cross_sectional_area)
        main_velocity = self.calculate_flow_velocity(main_flow_rate, main_cross_sectional_area)
        
        # Calculate velocity ratio
        velocity_ratio = self.calculate_velocity_ratio(main_velocity, branch_velocity)
        
        # Calculate rounding parameter and correction
        rounding_param = self.calculate_rounding_parameter(radius, branch_equiv_diameter)
        
        # Calculate turbulence correction
        turbulence_correction = 0.0
        if turbulence_present:
            turbulence_correction = self.calculate_turbulence_correction(velocity_ratio)
        
        # Initialize results
        branch_spectrum = {}
        main_spectrum = {}
        
        # Calculate for each octave band
        for frequency in self.octave_bands:
            # Calculate Strouhal number
            strouhal_number = self.calculate_strouhal_number(frequency, branch_equiv_diameter, branch_velocity)
            
            # Calculate rounding correction
            rounding_correction = self.calculate_rounding_correction(rounding_param, strouhal_number)
            
            # Calculate characteristic spectrum
            characteristic_spectrum = self.calculate_characteristic_spectrum(velocity_ratio, strouhal_number)
            
            # Calculate branch sound power level
            branch_sound_power = self.calculate_branch_sound_power_level(
                frequency, branch_equiv_diameter, branch_velocity, 
                branch_cross_sectional_area, characteristic_spectrum)
            
            # Calculate total branch sound power with corrections
            total_branch_sound_power = self.calculate_total_branch_sound_power(
                branch_sound_power, rounding_correction, turbulence_correction)
            
            # Calculate main duct sound power level
            main_sound_power = self.calculate_main_duct_sound_power_level(
                total_branch_sound_power, junction_type, main_equiv_diameter, branch_equiv_diameter)
            
            # Store results
            branch_spectrum[f"{frequency}Hz"] = total_branch_sound_power
            main_spectrum[f"{frequency}Hz"] = main_sound_power
        
        return {
            "branch_duct": branch_spectrum,
            "main_duct": main_spectrum,
            "parameters": {
                "branch_equivalent_diameter_ft": branch_equiv_diameter,
                "main_equivalent_diameter_ft": main_equiv_diameter,
                "branch_velocity_ft_s": branch_velocity,
                "main_velocity_ft_s": main_velocity,
                "velocity_ratio": velocity_ratio,
                "rounding_parameter": rounding_param,
                "turbulence_correction": turbulence_correction
            }
        }
    
    def create_noise_spectrum_dataframe(self, noise_spectrum: Dict[str, Dict[str, float]]) -> pd.DataFrame:
        """
        Create a pandas DataFrame from noise spectrum results.
        
        Args:
            noise_spectrum: Noise spectrum dictionary from calculate_junction_noise_spectrum
            
        Returns:
            DataFrame with frequency bands and sound power levels
        """
        data = []
        for frequency in self.octave_bands:
            freq_key = f"{frequency}Hz"
            data.append({
                'Frequency (Hz)': frequency,
                'Branch Duct (dB)': noise_spectrum['branch_duct'][freq_key],
                'Main Duct (dB)': noise_spectrum['main_duct'][freq_key]
            })
        
        return pd.DataFrame(data)
    
    def plot_noise_spectrum(self, noise_spectrum: Dict[str, Dict[str, float]], 
                          title: str = "Junction/Elbow Generated Noise Spectrum",
                          save_path: Optional[str] = None):
        """
        Plot the noise spectrum for branch and main ducts.
        
        Args:
            noise_spectrum: Noise spectrum dictionary
            title: Plot title
            save_path: Optional path to save the plot
        """
        df = self.create_noise_spectrum_dataframe(noise_spectrum)
        
        plt.figure(figsize=(12, 8))
        
        # Plot both spectra
        plt.semilogx(df['Frequency (Hz)'], df['Branch Duct (dB)'], 
                    'o-', linewidth=2, markersize=8, label='Branch Duct', color='blue')
        plt.semilogx(df['Frequency (Hz)'], df['Main Duct (dB)'], 
                    's-', linewidth=2, markersize=8, label='Main Duct', color='red')
        
        plt.xlabel('Frequency (Hz)', fontsize=12)
        plt.ylabel('Sound Power Level (dB)', fontsize=12)
        plt.title(title, fontsize=14, fontweight='bold')
        plt.grid(True, alpha=0.3)
        plt.legend(fontsize=11)
        
        # Set x-axis ticks to octave bands
        plt.xticks(self.octave_bands, [f'{f} Hz' for f in self.octave_bands])
        
        plt.tight_layout()
        
        if save_path:
            plt.savefig(save_path, dpi=300, bbox_inches='tight')
        
        plt.show()
    
    def compare_junction_types(self, 
                             # Duct parameters
                             branch_flow_rate: float,
                             branch_cross_sectional_area: float,
                             main_flow_rate: float,
                             main_cross_sectional_area: float,
                             branch_duct_shape: DuctShape = DuctShape.RECTANGULAR,
                             main_duct_shape: DuctShape = DuctShape.RECTANGULAR,
                             radius: float = 0.0,
                             turbulence_present: bool = False) -> pd.DataFrame:
        """
        Compare noise generation across different junction types.
        
        Args:
            branch_flow_rate: Branch duct volume flow rate (ft³/min)
            branch_cross_sectional_area: Branch duct cross-sectional area (ft²)
            main_flow_rate: Main duct volume flow rate (ft³/min)
            main_cross_sectional_area: Main duct cross-sectional area (ft²)
            branch_duct_shape: Branch duct shape
            main_duct_shape: Main duct shape
            radius: Radius of bend or elbow (inches)
            turbulence_present: Whether upstream turbulence is present
            
        Returns:
            DataFrame comparing junction types
        """
        results = []
        
        for junction_type in JunctionType:
            spectrum = self.calculate_junction_noise_spectrum(
                branch_flow_rate, branch_cross_sectional_area,
                main_flow_rate, main_cross_sectional_area,
                branch_duct_shape=branch_duct_shape, main_duct_shape=main_duct_shape,
                junction_type=junction_type, radius=radius, turbulence_present=turbulence_present)
            
            # Calculate overall sound power level (simple average for comparison)
            branch_overall = np.mean(list(spectrum['branch_duct'].values()))
            main_overall = np.mean(list(spectrum['main_duct'].values()))
            
            results.append({
                'Junction Type': junction_type.value.replace('_', ' ').title(),
                'Branch Duct Overall (dB)': branch_overall,
                'Main Duct Overall (dB)': main_overall,
                'Difference (dB)': main_overall - branch_overall
            })
        
        return pd.DataFrame(results)
    
    def generate_report(self, noise_spectrum: Dict[str, Dict[str, float]], 
                       junction_type: JunctionType,
                       parameters: Dict[str, float]) -> str:
        """
        Generate a comprehensive report of the calculations.
        
        Args:
            noise_spectrum: Noise spectrum dictionary
            junction_type: Type of junction or elbow
            parameters: Calculation parameters
            
        Returns:
            Formatted report string
        """
        df = self.create_noise_spectrum_dataframe(noise_spectrum)
        
        report = f"""
JUNCTION AND ELBOW GENERATED NOISE CALCULATION REPORT
=====================================================

Junction Type: {junction_type.value.replace('_', ' ').title()}

INPUT PARAMETERS:
----------------
Branch Duct:
  - Equivalent Diameter: {parameters['branch_equivalent_diameter_ft']:.3f} ft
  - Flow Velocity: {parameters['branch_velocity_ft_s']:.1f} ft/s

Main Duct:
  - Equivalent Diameter: {parameters['main_equivalent_diameter_ft']:.3f} ft
  - Flow Velocity: {parameters['main_velocity_ft_s']:.1f} ft/s

Calculated Parameters:
  - Velocity Ratio: {parameters['velocity_ratio']:.3f}
  - Rounding Parameter: {parameters['rounding_parameter']:.3f}
  - Turbulence Correction: {parameters['turbulence_correction']:.3f} dB

NOISE SPECTRUM RESULTS:
----------------------
{df.to_string(index=False, float_format='%.1f')}

SUMMARY:
--------
Branch Duct - Average Sound Power Level: {np.mean(list(noise_spectrum['branch_duct'].values())):.1f} dB
Main Duct - Average Sound Power Level: {np.mean(list(noise_spectrum['main_duct'].values())):.1f} dB
Difference: {np.mean(list(noise_spectrum['main_duct'].values())) - np.mean(list(noise_spectrum['branch_duct'].values())):.1f} dB

Note: Calculations based on ASHRAE 1991 Algorithms for HVAC Acoustics
"""
        return report
    
    def validate_inputs(self, branch_flow_rate: float, branch_cross_sectional_area: float,
                       main_flow_rate: float, main_cross_sectional_area: float,
                       radius: float) -> bool:
        """
        Validate input parameters.
        
        Args:
            branch_flow_rate: Branch duct volume flow rate (ft³/min)
            branch_cross_sectional_area: Branch duct cross-sectional area (ft²)
            main_flow_rate: Main duct volume flow rate (ft³/min)
            main_cross_sectional_area: Main duct cross-sectional area (ft²)
            radius: Radius of bend or elbow (inches)
            
        Returns:
            True if inputs are valid, False otherwise
        """
        if branch_flow_rate <= 0:
            print("Error: Branch flow rate must be positive")
            return False
        
        if branch_cross_sectional_area <= 0:
            print("Error: Branch cross-sectional area must be positive")
            return False
        
        if main_flow_rate <= 0:
            print("Error: Main flow rate must be positive")
            return False
        
        if main_cross_sectional_area <= 0:
            print("Error: Main cross-sectional area must be positive")
            return False
        
        if radius < 0:
            print("Error: Radius cannot be negative")
            return False
        
        return True


def main():
    """
    Main function demonstrating the use of JunctionElbowNoiseCalculator.
    """
    print("Junction and Elbow Generated Noise Calculator")
    print("=" * 50)
    
    # Initialize calculator
    calculator = JunctionElbowNoiseCalculator()
    
    # Example parameters (typical HVAC system values)
    branch_flow_rate = 500  # ft³/min
    branch_cross_sectional_area = 2.0  # ft² (24" x 12" duct)
    main_flow_rate = 2000  # ft³/min
    main_cross_sectional_area = 4.0  # ft² (24" x 24" duct)
    radius = 6.0  # inches
    turbulence_present = True
    
    print(f"Example Calculation Parameters:")
    print(f"Branch Flow Rate: {branch_flow_rate} ft³/min")
    print(f"Branch Cross-sectional Area: {branch_cross_sectional_area} ft²")
    print(f"Main Flow Rate: {main_flow_rate} ft³/min")
    print(f"Main Cross-sectional Area: {main_cross_sectional_area} ft²")
    print(f"Radius: {radius} inches")
    print(f"Turbulence Present: {turbulence_present}")
    print()
    
    # Validate inputs
    if not calculator.validate_inputs(branch_flow_rate, branch_cross_sectional_area,
                                    main_flow_rate, main_cross_sectional_area, radius):
        return
    
    # Calculate for T-junction
    print("Calculating T-Junction Noise Spectrum...")
    t_junction_spectrum = calculator.calculate_junction_noise_spectrum(
        branch_flow_rate, branch_cross_sectional_area,
        main_flow_rate, main_cross_sectional_area,
        junction_type=JunctionType.T_JUNCTION, radius=radius, turbulence_present=turbulence_present)
    
    # Create and display results
    df = calculator.create_noise_spectrum_dataframe(t_junction_spectrum)
    print("\nT-Junction Noise Spectrum:")
    print(df.to_string(index=False, float_format='%.1f'))
    
    # Generate report
    report = calculator.generate_report(t_junction_spectrum, JunctionType.T_JUNCTION, 
                                      t_junction_spectrum['parameters'])
    print("\n" + report)
    
    # Compare junction types
    print("\nComparing Junction Types...")
    comparison_df = calculator.compare_junction_types(
        branch_flow_rate, branch_cross_sectional_area,
        main_flow_rate, main_cross_sectional_area,
        radius=radius, turbulence_present=turbulence_present)
    
    print("\nJunction Type Comparison:")
    print(comparison_df.to_string(index=False, float_format='%.1f'))
    
    # Plot results
    print("\nGenerating plots...")
    calculator.plot_noise_spectrum(t_junction_spectrum, 
                                 "T-Junction Generated Noise Spectrum")
    
    # Save results to CSV
    output_filename = "t_junction_noise_spectrum.csv"
    df.to_csv(output_filename, index=False)
    print(f"\nResults saved to {output_filename}")


if __name__ == "__main__":
    main() 