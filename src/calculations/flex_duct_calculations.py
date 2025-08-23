"""
Flex Duct Acoustic Calculations
Based on ASHRAE 2015 Applications Handbook Chapter 48: Noise and Vibration Control

This script implements calculations for:
1. Nonmetallic insulated flexible duct insertion loss
2. Interpolation for duct diameters and lengths not in Table 25
3. Analysis and visualization of insertion loss data

Author: HVAC Acoustics Calculator
Date: 2024
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from typing import Tuple, Dict, List, Optional, Union
import warnings
from scipy.interpolate import RegularGridInterpolator

# Set up plotting style
plt.style.use('seaborn-v0_8')
sns.set_palette("husl")

class FlexDuctCalculator:
    """
    Calculator for nonmetallic insulated flexible duct acoustic properties 
    based on ASHRAE 2015 Applications Handbook Chapter 48.
    """
    
    def __init__(self):
        """Initialize the calculator with ASHRAE reference data from Table 25."""
        self.frequencies = [63, 125, 250, 500, 1000, 2000, 4000, 8000]
        self._initialize_insertion_loss_data()
        
    def _initialize_insertion_loss_data(self):
        """
        Initialize insertion loss data from Table 25: Insertion Loss for Lined Flexible Duct.
        Data format: {(diameter_in, length_ft): [63, 125, 250, 500, 1000, 2000, 4000, 8000] Hz}
        """
        # Data from Table 25: Insertion Loss for Lined Flexible Duct
        # Format: (diameter_inches, length_feet): [insertion_loss_63, 125, 250, 500, 1000, 2000, 4000, 8000]
        self.insertion_loss_data = {
            # 4-inch diameter
            (4, 12): [6, 11, 12, 31, 37, 42, 27, 15],
            (4, 9): [5, 8, 9, 23, 28, 32, 20, 12],
            (4, 6): [3, 6, 6, 16, 19, 21, 14, 8],
            (4, 3): [2, 3, 3, 8, 9, 11, 7, 4],
            
            # 5-inch diameter
            (5, 12): [7, 12, 14, 32, 38, 41, 26, 15],
            (5, 9): [5, 9, 11, 24, 29, 31, 20, 12],
            (5, 6): [4, 6, 7, 16, 19, 21, 13, 8],
            (5, 3): [2, 3, 4, 8, 10, 10, 7, 4],
            
            # 6-inch diameter
            (6, 12): [8, 12, 17, 33, 38, 40, 26, 15],
            (6, 9): [6, 9, 13, 25, 29, 30, 20, 12],
            (6, 6): [4, 6, 9, 17, 19, 20, 13, 8],
            (6, 3): [2, 3, 4, 8, 10, 10, 7, 4],
            
            # 7-inch diameter
            (7, 12): [9, 12, 19, 33, 37, 38, 25, 14],
            (7, 9): [6, 9, 14, 25, 28, 29, 19, 11],
            (7, 6): [4, 6, 10, 17, 19, 19, 13, 8],
            (7, 3): [2, 3, 5, 8, 9, 10, 6, 4],
            
            # 8-inch diameter
            (8, 12): [8, 11, 21, 33, 37, 37, 24, 13],
            (8, 9): [6, 8, 16, 25, 28, 28, 18, 10],
            (8, 6): [4, 6, 11, 17, 19, 19, 12, 7],
            (8, 3): [2, 3, 5, 8, 9, 9, 6, 4],
            
            # 9-inch diameter
            (9, 12): [8, 11, 22, 33, 37, 36, 22, 12],
            (9, 9): [6, 8, 17, 25, 28, 27, 17, 10],
            (9, 6): [4, 6, 11, 17, 19, 18, 11, 7],
            (9, 3): [2, 3, 6, 8, 9, 9, 6, 4],
            
            # 10-inch diameter
            (10, 12): [8, 10, 22, 32, 36, 34, 21, 11],
            (10, 9): [6, 8, 17, 24, 27, 26, 16, 9],
            (10, 6): [4, 5, 11, 16, 18, 17, 11, 6],
            (10, 3): [2, 3, 6, 8, 9, 9, 5, 3],
            
            # 12-inch diameter
            (12, 12): [7, 9, 20, 30, 34, 31, 18, 10],
            (12, 9): [5, 7, 15, 23, 26, 23, 14, 8],
            (12, 6): [3, 5, 10, 15, 17, 16, 9, 5],
            (12, 3): [2, 2, 5, 8, 9, 8, 5, 3],
            
            # 14-inch diameter
            (14, 12): [5, 7, 16, 27, 31, 27, 14, 8],
            (14, 9): [4, 5, 12, 20, 23, 20, 11, 6],
            (14, 6): [3, 4, 8, 14, 16, 14, 7, 4],
            (14, 3): [1, 2, 4, 7, 8, 7, 4, 2],
            
            # 16-inch diameter
            (16, 12): [2, 4, 9, 23, 28, 23, 9, 5],
            (16, 9): [2, 3, 7, 17, 21, 17, 7, 4],
            (16, 6): [1, 2, 5, 12, 14, 12, 5, 3],
            (16, 3): [1, 1, 2, 6, 7, 6, 2, 1]
        }
        
        # Create interpolation grids
        self._create_interpolation_grids()
        
    def _create_interpolation_grids(self):
        """Create interpolation grids for each frequency band."""
        # Extract unique diameters and lengths
        diameters = sorted(list(set(key[0] for key in self.insertion_loss_data.keys())))
        lengths = sorted(list(set(key[1] for key in self.insertion_loss_data.keys())))
        
        # Create interpolation functions for each frequency
        self.interpolators = {}
        for i, freq in enumerate(self.frequencies):
            # Create data grid for this frequency
            data_grid = np.zeros((len(diameters), len(lengths)))
            for di, diam in enumerate(diameters):
                for li, length in enumerate(lengths):
                    if (diam, length) in self.insertion_loss_data:
                        data_grid[di, li] = self.insertion_loss_data[(diam, length)][i]
                    else:
                        data_grid[di, li] = np.nan
            
            # Create interpolation function using RegularGridInterpolator
            # RegularGridInterpolator expects the grid points and the data array
            # The data array should have shape (len(diameters), len(lengths))
            self.interpolators[freq] = RegularGridInterpolator(
                (diameters, lengths), data_grid, 
                method='linear', bounds_error=False, fill_value=np.nan
            )
    
    def get_insertion_loss(self, diameter: float, length: float, 
                          frequency: Optional[int] = None) -> Union[float, Dict[int, float]]:
        """
        Get insertion loss for specified duct diameter and length.
        
        Args:
            diameter: Duct diameter in inches
            length: Duct length in feet
            frequency: Specific frequency in Hz (optional). If None, returns all frequencies.
            
        Returns:
            Insertion loss in dB (single value or dict for all frequencies)
        """
        # Validate inputs
        if diameter <= 0 or length <= 0:
            raise ValueError("Diameter and length must be positive values")
        
        # Check if exact values exist in data
        if (diameter, length) in self.insertion_loss_data:
            if frequency is None:
                return dict(zip(self.frequencies, self.insertion_loss_data[(diameter, length)]))
            else:
                freq_idx = self.frequencies.index(frequency)
                return self.insertion_loss_data[(diameter, length)][freq_idx]
        
        # Use interpolation for values not in table
        if frequency is None:
            # Return all frequencies
            result = {}
            for freq in self.frequencies:
                if freq in self.interpolators:
                    try:
                        result[freq] = float(self.interpolators[freq]([diameter, length]))
                    except:
                        result[freq] = np.nan
                else:
                    result[freq] = np.nan
            return result
        else:
            # Return specific frequency
            if frequency in self.interpolators:
                try:
                    return float(self.interpolators[frequency]([diameter, length]))
                except:
                    return np.nan
            else:
                return np.nan
    
    def get_recommended_length_range(self) -> Tuple[float, float]:
        """
        Get recommended duct length range from ASHRAE guidelines.
        
        Returns:
            Tuple of (min_length, max_length) in feet
        """
        return (3.0, 6.0)
    
    def validate_design_parameters(self, diameter: float, length: float) -> Dict[str, Union[bool, str]]:
        """
        Validate flex duct design parameters against ASHRAE recommendations.
        
        Args:
            diameter: Duct diameter in inches
            length: Duct length in feet
            
        Returns:
            Dictionary with validation results and recommendations
        """
        min_length, max_length = self.get_recommended_length_range()
        
        validation = {
            'is_valid': True,
            'warnings': [],
            'recommendations': []
        }
        
        # Check diameter range
        if diameter < 4 or diameter > 16:
            validation['warnings'].append(f"Diameter {diameter} inches is outside typical range (4-16 inches)")
        
        # Check length recommendations
        if length < min_length:
            validation['warnings'].append(f"Length {length} ft is below recommended minimum ({min_length} ft)")
            validation['recommendations'].append("Consider increasing duct length for better noise reduction")
        elif length > max_length:
            validation['warnings'].append(f"Length {length} ft exceeds recommended maximum ({max_length} ft)")
            validation['recommendations'].append("Longer ducts may have diminishing returns for noise reduction")
        
        # Check for straight duct recommendation
        validation['recommendations'].append("Keep flexible ducts straight with long radius bends")
        validation['recommendations'].append("Avoid abrupt bends to prevent high airflow noise")
        validation['recommendations'].append("Consider breakout sound levels above sound-sensitive spaces")
        
        if validation['warnings']:
            validation['is_valid'] = False
            
        return validation
    
    def create_insertion_loss_dataframe(self, diameters: List[float], 
                                      lengths: List[float]) -> pd.DataFrame:
        """
        Create a comprehensive DataFrame of insertion loss values.
        
        Args:
            diameters: List of duct diameters in inches
            lengths: List of duct lengths in feet
            
        Returns:
            DataFrame with insertion loss values for all combinations
        """
        data = []
        
        for diameter in diameters:
            for length in lengths:
                insertion_loss = self.get_insertion_loss(diameter, length)
                row = {'Diameter_in': diameter, 'Length_ft': length}
                row.update(insertion_loss)
                data.append(row)
        
        return pd.DataFrame(data)
    
    def plot_insertion_loss_spectrum(self, diameter: float, length: float, 
                                   save_path: Optional[str] = None):
        """
        Plot insertion loss spectrum for specified duct parameters.
        
        Args:
            diameter: Duct diameter in inches
            length: Duct length in feet
            save_path: Optional path to save the plot
        """
        insertion_loss = self.get_insertion_loss(diameter, length)
        
        plt.figure(figsize=(12, 8))
        
        # Create subplot for insertion loss spectrum
        plt.subplot(2, 2, 1)
        frequencies = list(insertion_loss.keys())
        losses = list(insertion_loss.values())
        
        plt.semilogx(frequencies, losses, 'o-', linewidth=2, markersize=8)
        plt.grid(True, alpha=0.3)
        plt.xlabel('Frequency (Hz)')
        plt.ylabel('Insertion Loss (dB)')
        plt.title(f'Flex Duct Insertion Loss Spectrum\n{diameter}" diameter, {length} ft length')
        plt.xlim(50, 8000)
        
        # Create subplot for frequency band comparison
        plt.subplot(2, 2, 2)
        bars = plt.bar(range(len(frequencies)), losses, 
                      color=sns.color_palette("husl", len(frequencies)))
        plt.xlabel('Frequency Band')
        plt.ylabel('Insertion Loss (dB)')
        plt.title('Insertion Loss by Frequency Band')
        plt.xticks(range(len(frequencies)), [f'{f} Hz' for f in frequencies], rotation=45)
        
        # Add value labels on bars
        for bar, loss in zip(bars, losses):
            plt.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.5,
                    f'{loss:.1f}', ha='center', va='bottom')
        
        # Create subplot for length comparison (same diameter)
        plt.subplot(2, 2, 3)
        lengths_to_compare = [3, 6, 9, 12]
        for length_comp in lengths_to_compare:
            if length_comp != length:  # Don't plot the same length twice
                loss_comp = self.get_insertion_loss(diameter, length_comp)
                plt.semilogx(frequencies, list(loss_comp.values()), 
                           '--', linewidth=1.5, alpha=0.7, 
                           label=f'{length_comp} ft')
        
        # Plot the main length with thicker line
        plt.semilogx(frequencies, losses, 'o-', linewidth=3, markersize=8, 
                    label=f'{length} ft (selected)')
        plt.grid(True, alpha=0.3)
        plt.xlabel('Frequency (Hz)')
        plt.ylabel('Insertion Loss (dB)')
        plt.title(f'Length Comparison - {diameter}" Diameter')
        plt.legend()
        plt.xlim(50, 8000)
        
        # Create subplot for diameter comparison (same length)
        plt.subplot(2, 2, 4)
        diameters_to_compare = [4, 8, 12, 16]
        for diam_comp in diameters_to_compare:
            if diam_comp != diameter:  # Don't plot the same diameter twice
                loss_comp = self.get_insertion_loss(diam_comp, length)
                plt.semilogx(frequencies, list(loss_comp.values()), 
                           '--', linewidth=1.5, alpha=0.7, 
                           label=f'{diam_comp}"')
        
        # Plot the main diameter with thicker line
        plt.semilogx(frequencies, losses, 'o-', linewidth=3, markersize=8, 
                    label=f'{diameter}" (selected)')
        plt.grid(True, alpha=0.3)
        plt.xlabel('Frequency (Hz)')
        plt.ylabel('Insertion Loss (dB)')
        plt.title(f'Diameter Comparison - {length} ft Length')
        plt.legend()
        plt.xlim(50, 8000)
        
        plt.tight_layout()
        
        if save_path:
            plt.savefig(save_path, dpi=300, bbox_inches='tight')
        
        plt.show()
    
    def plot_insertion_loss_heatmap(self, frequency: int = 500, 
                                  save_path: Optional[str] = None):
        """
        Create a heatmap of insertion loss for a specific frequency.
        
        Args:
            frequency: Frequency in Hz for the heatmap
            save_path: Optional path to save the plot
        """
        diameters = np.arange(4, 17, 0.5)  # 4 to 16 inches in 0.5" steps
        lengths = np.arange(3, 13, 0.5)    # 3 to 12 feet in 0.5' steps
        
        # Create meshgrid
        D, L = np.meshgrid(diameters, lengths)
        
        # Calculate insertion loss for each point
        Z = np.zeros_like(D)
        for i, length in enumerate(lengths):
            for j, diameter in enumerate(diameters):
                Z[i, j] = self.get_insertion_loss(diameter, length, frequency)
        
        plt.figure(figsize=(12, 8))
        
        # Create heatmap
        im = plt.imshow(Z, extent=[diameters.min(), diameters.max(), 
                                  lengths.min(), lengths.max()],
                       aspect='auto', cmap='viridis', origin='lower')
        
        plt.colorbar(im, label=f'Insertion Loss (dB) at {frequency} Hz')
        plt.xlabel('Duct Diameter (inches)')
        plt.ylabel('Duct Length (feet)')
        plt.title(f'Flex Duct Insertion Loss Heatmap - {frequency} Hz')
        
        # Add contour lines
        contour = plt.contour(D, L, Z, colors='white', alpha=0.5, linewidths=0.5)
        plt.clabel(contour, inline=True, fontsize=8, fmt='%.1f')
        
        if save_path:
            plt.savefig(save_path, dpi=300, bbox_inches='tight')
        
        plt.show()
    
    def calculate_average_insertion_loss(self, diameter: float, length: float, 
                                       frequency_range: Optional[List[int]] = None) -> float:
        """
        Calculate average insertion loss across frequency bands.
        
        Args:
            diameter: Duct diameter in inches
            length: Duct length in feet
            frequency_range: List of frequencies to average (default: all frequencies)
            
        Returns:
            Average insertion loss in dB
        """
        insertion_loss = self.get_insertion_loss(diameter, length)
        
        if frequency_range is None:
            frequency_range = self.frequencies
        
        values = [insertion_loss[freq] for freq in frequency_range if freq in insertion_loss]
        
        if not values:
            return np.nan
        
        return np.mean(values)
    
    def generate_report(self, diameter: float, length: float) -> str:
        """
        Generate a comprehensive report for flex duct design.
        
        Args:
            diameter: Duct diameter in inches
            length: Duct length in feet
            
        Returns:
            Formatted report string
        """
        insertion_loss = self.get_insertion_loss(diameter, length)
        avg_loss = self.calculate_average_insertion_loss(diameter, length)
        validation = self.validate_design_parameters(diameter, length)
        
        report = f"""
FLEX DUCT ACOUSTIC ANALYSIS REPORT
==================================

Duct Parameters:
- Diameter: {diameter} inches
- Length: {length} feet

Insertion Loss by Frequency:
"""
        
        for freq, loss in insertion_loss.items():
            report += f"- {freq} Hz: {loss:.1f} dB\n"
        
        report += f"""
Summary Statistics:
- Average Insertion Loss: {avg_loss:.1f} dB
- Maximum Insertion Loss: {max(insertion_loss.values()):.1f} dB at {max(insertion_loss, key=insertion_loss.get)} Hz
- Minimum Insertion Loss: {min(insertion_loss.values()):.1f} dB at {min(insertion_loss, key=insertion_loss.get)} Hz

Design Validation:
- Valid Design: {'Yes' if validation['is_valid'] else 'No'}
"""
        
        if validation['warnings']:
            report += "\nWarnings:\n"
            for warning in validation['warnings']:
                report += f"- {warning}\n"
        
        if validation['recommendations']:
            report += "\nRecommendations:\n"
            for rec in validation['recommendations']:
                report += f"- {rec}\n"
        
        report += f"""
ASHRAE Guidelines:
- Recommended length range: {self.get_recommended_length_range()[0]}-{self.get_recommended_length_range()[1]} feet
- Keep ducts straight with long radius bends
- Avoid abrupt bends to prevent high airflow noise
- Consider breakout sound levels above sound-sensitive spaces

Note: 63 Hz insertion loss values are estimated from higher-frequency values.
"""
        
        return report

def main():
    """Main function to demonstrate flex duct calculations."""
    print("Flex Duct Acoustic Calculator")
    print("=" * 50)
    
    # Initialize calculator
    calculator = FlexDuctCalculator()
    
    # Example calculations
    print("\nExample 1: 6-inch diameter, 9-foot length")
    print("-" * 40)
    insertion_loss = calculator.get_insertion_loss(6, 9)
    for freq, loss in insertion_loss.items():
        print(f"{freq} Hz: {loss:.1f} dB")
    
    print(f"\nAverage insertion loss: {calculator.calculate_average_insertion_loss(6, 9):.1f} dB")
    
    # Generate comprehensive report
    print("\n" + "=" * 50)
    print(calculator.generate_report(6, 9))
    
    # Create visualizations
    print("\nGenerating plots...")
    calculator.plot_insertion_loss_spectrum(6, 9)
    calculator.plot_insertion_loss_heatmap(500)
    
    # Create comparison DataFrame
    print("\nCreating comparison table...")
    diameters = [4, 6, 8, 10, 12, 14, 16]
    lengths = [3, 6, 9, 12]
    df = calculator.create_insertion_loss_dataframe(diameters, lengths)
    
    print("\nInsertion Loss Comparison Table (500 Hz):")
    print(df.pivot(index='Length_ft', columns='Diameter_in', values=500).round(1))
    
    print("\nAnalysis complete!")

if __name__ == "__main__":
    main() 