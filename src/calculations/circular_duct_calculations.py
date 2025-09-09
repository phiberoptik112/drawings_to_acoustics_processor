"""
Circular Duct Acoustic Calculations
Based on ASHRAE 1991 Algorithms for HVAC Acoustics

This script implements calculations for:
1. Unlined circular sheet metal duct attenuation using Table 5.5 data
2. Acoustically lined circular duct insertion loss using Equation 5.18
3. Support for frequency bands from 63 Hz to 8,000 Hz
4. Validation against reference data and limits

Author: HVAC Acoustics Calculator
Date: 2024
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from typing import Tuple, Dict, List, Optional, Union, Any
import warnings

# Set up plotting style
plt.style.use('seaborn-v0_8')
sns.set_palette("husl")

class CircularDuctCalculator:
    """
    Calculator for circular duct acoustic properties based on ASHRAE 1991 standards.
    
    Implements:
    - Unlined circular duct attenuation (Table 5.5)
    - Acoustically lined circular duct insertion loss (Equation 5.18)
    """
    
    def __init__(self):
        """Initialize the calculator with ASHRAE reference data."""
        self._initialize_reference_data()
        self._initialize_frequency_bands()
        
    def _initialize_reference_data(self):
        """Initialize reference data from Tables 5.5 and 5.6."""
        # Table 5.5: Sound Attenuation in Straight Circular Ducts (dB/ft)
        # Format: diameter_range -> {frequency_bands} -> attenuation
        self.unlined_attenuation_data = {
            'D ≤ 7': {
                '63': 0.03, '125': 0.03, '250': 0.05, '500': 0.05,
                '1000': 0.10, '2000': 0.10, '4000': 0.10
            },
            '7 < D ≤ 15': {
                '63': 0.03, '125': 0.03, '250': 0.03, '500': 0.05,
                '1000': 0.07, '2000': 0.07, '4000': 0.07
            },
            '15 < D ≤ 30': {
                '63': 0.02, '125': 0.02, '250': 0.02, '500': 0.03,
                '1000': 0.05, '2000': 0.05, '4000': 0.05
            },
            '30 < D ≤ 60': {
                '63': 0.01, '125': 0.01, '250': 0.01, '500': 0.02,
                '1000': 0.02, '2000': 0.02, '4000': 0.02
            }
        }
        
        # Table 5.6: Constants for Use in Equation (5.18)
        # Format: frequency -> {A, B, C, D, E, F} coefficients
        self.lined_coefficients = {
            63: {'A': 0.2825, 'B': 0.3447, 'C': -5.251E-02, 'D': -0.03837, 'E': 9.1315E-04, 'F': -8.294E-06},
            125: {'A': 0.5237, 'B': 0.2234, 'C': -4.936E-03, 'D': -0.02724, 'E': 3.377E-04, 'F': -2.49E-04},
            250: {'A': 0.3652, 'B': 0.79, 'C': -0.1157, 'D': -1.834E-02, 'E': -1.211E-04, 'F': 2.681E-04},
            500: {'A': 0.1333, 'B': 1.845, 'C': -0.3735, 'D': -1.293E-02, 'E': 8.624E-05, 'F': -4.986E-06},
            1000: {'A': 1.933, 'B': 0, 'C': 0, 'D': 6.135E-02, 'E': -3.891E-03, 'F': 3.934E-05},
            2000: {'A': 2.73, 'B': 0, 'C': 0, 'D': -7.341E-02, 'E': 4.428E-04, 'F': 1.006E-06},
            4000: {'A': 2.8, 'B': 0, 'C': 0, 'D': -0.1467, 'E': 3.404E-03, 'F': -2.851E-05},
            8000: {'A': 1.545, 'B': 0, 'C': 0, 'D': -5.452E-02, 'E': 1.290E-03, 'F': -1.318E-05}
        }
        
    def _initialize_frequency_bands(self):
        """Initialize standard frequency bands."""
        self.frequency_bands = [63, 125, 250, 500, 1000, 2000, 4000, 8000]
        
    def get_diameter_range(self, diameter: float) -> str:
        """
        Determine the diameter range category for unlined duct calculations.
        
        Args:
            diameter: Duct diameter in inches
            
        Returns:
            Diameter range category string
        """
        if diameter <= 7:
            return 'D ≤ 7'
        elif diameter <= 15:
            return '7 < D ≤ 15'
        elif diameter <= 30:
            return '15 < D ≤ 30'
        elif diameter <= 60:
            return '30 < D ≤ 60'
        else:
            raise ValueError(f"Duct diameter {diameter} inches exceeds maximum range of 60 inches")
            
    def calculate_unlined_attenuation(self, diameter: float, frequency: float, length: float = 1.0) -> float:
        """
        Calculate sound attenuation for unlined circular ducts using Table 5.5.
        
        Args:
            diameter: Duct diameter in inches
            frequency: Frequency in Hz (must be one of the standard bands)
            length: Duct length in feet
            
        Returns:
            Sound attenuation in dB
        """
        if diameter <= 0:
            raise ValueError("Duct diameter must be positive")
        if length <= 0:
            raise ValueError("Duct length must be positive")
            
        # Get diameter range
        diameter_range = self.get_diameter_range(diameter)
        
        # Find closest frequency band
        freq_bands = [63, 125, 250, 500, 1000, 2000, 4000]
        closest_freq = min(freq_bands, key=lambda x: abs(x - frequency))
        print("INSIDE THE CIRCULAR DUCT CALCULATION")
        # Get attenuation per foot from Table 5.5
        attenuation_per_ft = self.unlined_attenuation_data[diameter_range][str(closest_freq)]
        print("RETURNING FROM THE CIRCULAR DUCT CALCULATION")
        print(f"ATTENUATION PER FOOT: {attenuation_per_ft}")
        # Calculate total attenuation   
        total_attenuation = attenuation_per_ft * length
        print("RETURNING FROM THE CIRCULAR DUCT CALCULATION")
        print(f"TOTAL ATTENUATION: {total_attenuation}")
        return total_attenuation
        
    def calculate_lined_insertion_loss(self, diameter: float, lining_thickness: float, 
                                     frequency: float, length: float = 1.0) -> float:
        """
        Calculate insertion loss for acoustically lined circular ducts using Equation 5.18.
        
        IL = (A + B•t + C•t² + D•d + E•d² + F•d³) • L
        
        Args:
            diameter: Inside duct diameter in inches
            lining_thickness: Lining thickness in inches
            frequency: Frequency in Hz (must be one of the standard bands)
            length: Duct length in feet
            
        Returns:
            Insertion loss in dB
        """
        if diameter < 6 or diameter > 60:
            raise ValueError("Duct diameter must be between 6 and 60 inches")
        if lining_thickness < 1 or lining_thickness > 3:
            raise ValueError("Lining thickness must be between 1 and 3 inches")
        if length <= 0:
            raise ValueError("Duct length must be positive")
            
        # Find closest frequency band
        closest_freq = min(self.frequency_bands, key=lambda x: abs(x - frequency))
        
        # Get coefficients for the frequency
        coeffs = self.lined_coefficients[closest_freq]
        
        # Calculate insertion loss using Equation 5.18
        t = lining_thickness
        d = diameter
        
        IL = (coeffs['A'] + coeffs['B'] * t + coeffs['C'] * t**2 + 
              coeffs['D'] * d + coeffs['E'] * d**2 + coeffs['F'] * d**3) * length
        
        # Apply maximum limit of 40 dB due to structure-borne sound
        IL = min(IL, 40.0)
        
        return max(IL, 0.0)  # Ensure non-negative
        
    def get_unlined_attenuation_spectrum(self, diameter: float, length: float = 1.0) -> Dict[str, float]:
        """
        Calculate unlined duct attenuation across all frequency bands.
        
        Args:
            diameter: Duct diameter in inches
            length: Duct length in feet
            
        Returns:
            Dictionary of frequency -> attenuation values
        """
        spectrum = {}
        for freq in self.frequency_bands:
            if freq <= 4000:  # Table 5.5 only goes up to 4000 Hz
                spectrum[str(freq)] = self.calculate_unlined_attenuation(diameter, freq, length)
            else:
                spectrum[str(freq)] = 0.0  # No data for 8000 Hz
                
        return spectrum
        
    def get_lined_insertion_loss_spectrum(self, diameter: float, lining_thickness: float, 
                                        length: float = 1.0) -> Dict[str, float]:
        """
        Calculate lined duct insertion loss across all frequency bands.
        
        Args:
            diameter: Inside duct diameter in inches
            lining_thickness: Lining thickness in inches
            length: Duct length in feet
            
        Returns:
            Dictionary of frequency -> insertion loss values
        """
        spectrum = {}
        for freq in self.frequency_bands:
            spectrum[str(freq)] = self.calculate_lined_insertion_loss(diameter, lining_thickness, freq, length)
                
        return spectrum
        
    def create_comparison_dataframe(self, diameters: List[float], lining_thicknesses: List[float], 
                                  length: float = 1.0) -> pd.DataFrame:
        """
        Create a comparison DataFrame for multiple duct configurations.
        
        Args:
            diameters: List of duct diameters in inches
            lining_thicknesses: List of lining thicknesses in inches
            length: Duct length in feet
            
        Returns:
            DataFrame with comparison data
        """
        data = []
        
        for diameter in diameters:
            # Unlined duct data
            unlined_spectrum = self.get_unlined_attenuation_spectrum(diameter, length)
            row = {
                'Diameter (in)': diameter,
                'Lining Thickness (in)': 0,
                'Type': 'Unlined',
                'Length (ft)': length
            }
            row.update({f'Attenuation_{freq}Hz': unlined_spectrum[freq] for freq in unlined_spectrum})
            data.append(row)
            
            # Lined duct data
            for thickness in lining_thicknesses:
                lined_spectrum = self.get_lined_insertion_loss_spectrum(diameter, thickness, length)
                row = {
                    'Diameter (in)': diameter,
                    'Lining Thickness (in)': thickness,
                    'Type': 'Lined',
                    'Length (ft)': length
                }
                row.update({f'Insertion_Loss_{freq}Hz': lined_spectrum[freq] for freq in lined_spectrum})
                data.append(row)
                
        return pd.DataFrame(data)
        
    def plot_attenuation_comparison(self, diameter: float, lining_thickness: float = 1.0, 
                                  length: float = 1.0, save_path: Optional[str] = None):
        """
        Create comparison plot of unlined vs lined duct performance.
        
        Args:
            diameter: Duct diameter in inches
            lining_thickness: Lining thickness in inches
            length: Duct length in feet
            save_path: Optional path to save the plot
        """
        # Get spectra
        unlined_spectrum = self.get_unlined_attenuation_spectrum(diameter, length)
        lined_spectrum = self.get_lined_insertion_loss_spectrum(diameter, lining_thickness, length)
        
        # Prepare data for plotting
        frequencies = [int(f) for f in unlined_spectrum.keys()]
        unlined_values = list(unlined_spectrum.values())
        lined_values = list(lined_spectrum.values())
        
        # Create plot
        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(15, 6))
        
        # Unlined duct plot
        ax1.semilogx(frequencies, unlined_values, 'o-', linewidth=2, markersize=8, 
                    label=f'D={diameter}" Unlined')
        ax1.set_xlabel('Frequency (Hz)')
        ax1.set_ylabel('Attenuation (dB)')
        ax1.set_title(f'Unlined Circular Duct Attenuation\nDiameter: {diameter}"')
        ax1.grid(True, alpha=0.3)
        ax1.legend()
        
        # Lined duct plot
        ax2.semilogx(frequencies, lined_values, 's-', linewidth=2, markersize=8, 
                    label=f'D={diameter}", t={lining_thickness}" Lined')
        ax2.set_xlabel('Frequency (Hz)')
        ax2.set_ylabel('Insertion Loss (dB)')
        ax2.set_title(f'Lined Circular Duct Insertion Loss\nDiameter: {diameter}", Thickness: {lining_thickness}"')
        ax2.grid(True, alpha=0.3)
        ax2.legend()
        
        plt.tight_layout()
        
        if save_path:
            plt.savefig(save_path, dpi=300, bbox_inches='tight')
        plt.show()
        
    def plot_diameter_comparison(self, diameters: List[float], lining_thickness: float = 1.0, 
                               length: float = 1.0, save_path: Optional[str] = None):
        """
        Create comparison plot across different duct diameters.
        
        Args:
            diameters: List of duct diameters in inches
            lining_thickness: Lining thickness in inches
            length: Duct length in feet
            save_path: Optional path to save the plot
        """
        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(15, 6))
        
        frequencies = self.frequency_bands[:-1]  # Exclude 8000 Hz for unlined
        
        # Unlined duct comparison
        for diameter in diameters:
            spectrum = self.get_unlined_attenuation_spectrum(diameter, length)
            values = [spectrum[str(f)] for f in frequencies]
            ax1.semilogx(frequencies, values, 'o-', linewidth=2, markersize=6, 
                        label=f'D={diameter}"')
            
        ax1.set_xlabel('Frequency (Hz)')
        ax1.set_ylabel('Attenuation (dB)')
        ax1.set_title('Unlined Circular Duct Attenuation Comparison')
        ax1.grid(True, alpha=0.3)
        ax1.legend()
        
        # Lined duct comparison
        for diameter in diameters:
            spectrum = self.get_lined_insertion_loss_spectrum(diameter, lining_thickness, length)
            values = [spectrum[str(f)] for f in self.frequency_bands]
            ax2.semilogx(self.frequency_bands, values, 's-', linewidth=2, markersize=6, 
                        label=f'D={diameter}"')
            
        ax2.set_xlabel('Frequency (Hz)')
        ax2.set_ylabel('Insertion Loss (dB)')
        ax2.set_title(f'Lined Circular Duct Insertion Loss Comparison\nThickness: {lining_thickness}"')
        ax2.grid(True, alpha=0.3)
        ax2.legend()
        
        plt.tight_layout()
        
        if save_path:
            plt.savefig(save_path, dpi=300, bbox_inches='tight')
        plt.show()
        
    def generate_report(self, diameter: float, lining_thickness: float = 1.0, 
                       length: float = 1.0) -> str:
        """
        Generate a comprehensive report for circular duct calculations.
        
        Args:
            diameter: Duct diameter in inches
            lining_thickness: Lining thickness in inches
            length: Duct length in feet
            
        Returns:
            Formatted report string
        """
        report = []
        report.append("=" * 60)
        report.append("CIRCULAR DUCT ACOUSTIC CALCULATIONS")
        report.append("ASHRAE 1991 Algorithms for HVAC Acoustics")
        report.append("=" * 60)
        report.append("")
        
        # Input parameters
        report.append("INPUT PARAMETERS:")
        report.append(f"  Duct Diameter: {diameter} inches")
        report.append(f"  Lining Thickness: {lining_thickness} inches")
        report.append(f"  Duct Length: {length} feet")
        report.append("")
        
        # Unlined duct results
        report.append("UNLINED CIRCULAR DUCT ATTENUATION:")
        report.append("-" * 40)
        unlined_spectrum = self.get_unlined_attenuation_spectrum(diameter, length)
        for freq, atten in unlined_spectrum.items():
            report.append(f"  {freq} Hz: {atten:.3f} dB")
        report.append("")
        
        # Lined duct results
        report.append("LINED CIRCULAR DUCT INSERTION LOSS:")
        report.append("-" * 40)
        lined_spectrum = self.get_lined_insertion_loss_spectrum(diameter, lining_thickness, length)
        for freq, loss in lined_spectrum.items():
            report.append(f"  {freq} Hz: {loss:.3f} dB")
        report.append("")
        
        # Summary statistics
        unlined_avg = np.mean(list(unlined_spectrum.values()))
        lined_avg = np.mean(list(lined_spectrum.values()))
        improvement = lined_avg - unlined_avg
        
        report.append("SUMMARY:")
        report.append("-" * 40)
        report.append(f"  Average Unlined Attenuation: {unlined_avg:.3f} dB")
        report.append(f"  Average Lined Insertion Loss: {lined_avg:.3f} dB")
        report.append(f"  Average Improvement: {improvement:.3f} dB")
        report.append("")
        
        # Validation notes
        report.append("VALIDATION NOTES:")
        report.append("-" * 40)
        report.append("  • Unlined duct data from Table 5.5 (Woods Design for Sound)")
        report.append("  • Lined duct calculations use Equation 5.18")
        report.append("  • Maximum insertion loss limited to 40 dB")
        report.append("  • Valid diameter range: 6-60 inches")
        report.append("  • Valid lining thickness: 1-3 inches")
        report.append("")
        
        return "\n".join(report)
        
    def validate_limits(self, diameter: float, lining_thickness: float) -> Dict[str, bool]:
        """
        Validate input parameters against ASHRAE limits.
        
        Args:
            diameter: Duct diameter in inches
            lining_thickness: Lining thickness in inches
            
        Returns:
            Dictionary of validation results
        """
        validation = {}
        
        # Diameter limits for lined ducts
        validation['diameter_in_range'] = 6 <= diameter <= 60
        
        # Lining thickness limits
        validation['thickness_in_range'] = 1 <= lining_thickness <= 3
        
        # Diameter limits for unlined ducts
        validation['diameter_unlined_ok'] = diameter <= 60
        
        return validation

def main():
    """Main function to demonstrate the calculator functionality."""
    print("Circular Duct Acoustic Calculator")
    print("Based on ASHRAE 1991 Algorithms for HVAC Acoustics")
    print("=" * 50)
    
    # Initialize calculator
    calculator = CircularDuctCalculator()
    
    # Example calculations
    diameter = 12.0  # inches
    lining_thickness = 1.5  # inches
    length = 10.0  # feet
    
    print(f"\nExample Calculation:")
    print(f"Duct Diameter: {diameter} inches")
    print(f"Lining Thickness: {lining_thickness} inches")
    print(f"Duct Length: {length} feet")
    
    # Generate report
    report = calculator.generate_report(diameter, lining_thickness, length)
    print(report)
    
    # Create comparison plots
    print("\nGenerating comparison plots...")
    calculator.plot_attenuation_comparison(diameter, lining_thickness, length)
    
    # Diameter comparison
    diameters = [6, 12, 24, 48]
    calculator.plot_diameter_comparison(diameters, lining_thickness, length)
    
    # Create comparison DataFrame
    print("\nCreating comparison DataFrame...")
    df = calculator.create_comparison_dataframe(diameters, [1.0, 2.0, 3.0], length)
    print(df.head())
    
    # Validation
    print("\nValidating input parameters...")
    validation = calculator.validate_limits(diameter, lining_thickness)
    for check, result in validation.items():
        print(f"  {check}: {'✓' if result else '✗'}")

if __name__ == "__main__":
    main() 