"""
Rectangular Elbows Acoustic Calculations
Based on ASHRAE 2015 Applications Handbook Chapter 48: Noise and Vibration Control

This script implements calculations for:
1. Unlined and lined square elbows without turning vanes (Table 22)
2. Unlined radiused elbows (Table 23)
3. Unlined and lined square elbows with turning vanes (Table 24)

The quantity fw is the midfrequency of the octave band times the width of the elbow.
f = center frequency (kHz), w = width (inches)

Author: HVAC Acoustics Calculator
Date: 2024
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from typing import Tuple, Dict, List, Optional, Union
import warnings

# Set up plotting style
plt.style.use('seaborn-v0_8')
sns.set_palette("husl")

class RectangularElbowsCalculator:
    """
    Calculator for rectangular elbows insertion loss based on ASHRAE standards.
    """
    
    def __init__(self):
        """Initialize the calculator with ASHRAE reference data."""
        self._initialize_table_22_data()
        self._initialize_table_23_data()
        self._initialize_table_24_data()
        self._initialize_octave_bands()
        
    def _initialize_table_22_data(self):
        """Initialize Table 22: Unlined and Lined Square Elbows Without Turning Vanes."""
        # Data from Table 22: Insertion Loss of Unlined and Lined Square Elbows Without Turning Vanes
        # Format: (fw_min, fw_max): (unlined_loss, lined_loss)
        self.table_22_data = {
            (0, 1.9): (0, 0),
            (1.9, 3.8): (1, 1),
            (3.8, 7.5): (5, 6),
            (7.5, 15): (8, 11),
            (15, 30): (4, 10),
            (30, float('inf')): (3, 10)
        }
        
    def _initialize_table_23_data(self):
        """Initialize Table 23: Unlined Radiused Elbows."""
        # Data from Table 23: Insertion Loss of Radiused Elbows
        # Format: (fw_min, fw_max): insertion_loss
        self.table_23_data = {
            (0, 1.9): 0,
            (1.9, 3.8): 1,
            (3.8, 7.5): 6,
            (7.5, float('inf')): 11
        }
        
    def _initialize_table_24_data(self):
        """Initialize Table 24: Unlined and Lined Square Elbows with Turning Vanes."""
        # Data from Table 24: Insertion Loss of Unlined and Lined Square Elbows with Turning Vanes
        # Format: (fw_min, fw_max): (unlined_loss, lined_loss)
        self.table_24_data = {
            (0, 1.9): (0, 0),
            (1.9, 3.8): (1, 1),
            (3.8, 7.5): (4, 4),
            (7.5, 15): (6, 7),
            (15, float('inf')): (4, 10)
        }
        
    def _initialize_octave_bands(self):
        """Initialize standard octave band center frequencies."""
        self.octave_bands = [63, 125, 250, 500, 1000, 2000, 4000, 8000]  # Hz
        self.octave_bands_khz = [f/1000 for f in self.octave_bands]  # kHz
        
    def calculate_fw_product(self, frequency: float, width: float) -> float:
        """
        Calculate the fw product (frequency × width).
        
        Args:
            frequency: Frequency in Hz
            width: Width of the elbow in inches
            
        Returns:
            fw product (frequency in kHz × width in inches)
        """
        frequency_khz = frequency / 1000  # Convert Hz to kHz
        return frequency_khz * width
        
    def get_table_22_insertion_loss(self, frequency: float, width: float, 
                                   lined: bool = False) -> float:
        """
        Get insertion loss for unlined and lined square elbows without turning vanes (Table 22).
        
        Args:
            frequency: Frequency in Hz
            width: Width of the elbow in inches
            lined: True for lined elbows, False for unlined
            
        Returns:
            Insertion loss in dB
        """
        fw = self.calculate_fw_product(frequency, width)
        
        for (fw_min, fw_max), (unlined_loss, lined_loss) in self.table_22_data.items():
            if fw_min <= fw < fw_max:
                return lined_loss if lined else unlined_loss
                
        return 0  # Default case
        
    def get_table_23_insertion_loss(self, frequency: float, width: float) -> float:
        """
        Get insertion loss for unlined radiused elbows (Table 23).
        
        Args:
            frequency: Frequency in Hz
            width: Width of the elbow in inches
            
        Returns:
            Insertion loss in dB
        """
        fw = self.calculate_fw_product(frequency, width)
        
        for (fw_min, fw_max), insertion_loss in self.table_23_data.items():
            if fw_min <= fw < fw_max:
                return insertion_loss
                
        return 0  # Default case
        
    def get_table_24_insertion_loss(self, frequency: float, width: float, 
                                   lined: bool = False) -> float:
        """
        Get insertion loss for unlined and lined square elbows with turning vanes (Table 24).
        
        Args:
            frequency: Frequency in Hz
            width: Width of the elbow in inches
            lined: True for lined elbows, False for unlined
            
        Returns:
            Insertion loss in dB
        """
        fw = self.calculate_fw_product(frequency, width)
        
        for (fw_min, fw_max), (unlined_loss, lined_loss) in self.table_24_data.items():
            if fw_min <= fw < fw_max:
                return lined_loss if lined else unlined_loss
                
        return 0  # Default case
        
    def calculate_elbow_insertion_loss(self, frequency: float, width: float, 
                                     elbow_type: str = 'square_no_vanes', 
                                     lined: bool = False) -> float:
        """
        Calculate insertion loss for rectangular elbows based on type.
        
        Args:
            frequency: Frequency in Hz
            width: Width of the elbow in inches
            elbow_type: Type of elbow ('square_no_vanes', 'radiused', 'square_with_vanes')
            lined: True for lined elbows (only applies to square elbows)
            
        Returns:
            Insertion loss in dB
        """
        if elbow_type == 'square_no_vanes':
            return self.get_table_22_insertion_loss(frequency, width, lined)
        elif elbow_type == 'radiused':
            return self.get_table_23_insertion_loss(frequency, width)
        elif elbow_type == 'square_with_vanes':
            return self.get_table_24_insertion_loss(frequency, width, lined)
        else:
            raise ValueError(f"Unknown elbow type: {elbow_type}. "
                           f"Valid types: 'square_no_vanes', 'radiused', 'square_with_vanes'")
            
    def calculate_spectrum_insertion_loss(self, width: float, 
                                        elbow_type: str = 'square_no_vanes', 
                                        lined: bool = False) -> Dict[str, float]:
        """
        Calculate insertion loss across all octave bands for a given elbow.
        
        Args:
            width: Width of the elbow in inches
            elbow_type: Type of elbow ('square_no_vanes', 'radiused', 'square_with_vanes')
            lined: True for lined elbows (only applies to square elbows)
            
        Returns:
            Dictionary with frequency bands as keys and insertion loss values as values
        """
        results = {}
        
        for freq in self.octave_bands:
            insertion_loss = self.calculate_elbow_insertion_loss(freq, width, elbow_type, lined)
            results[f"{freq} Hz"] = insertion_loss
            
        return results
        
    def compare_elbow_types(self, width: float, lined: bool = False) -> pd.DataFrame:
        """
        Compare insertion loss across all elbow types for a given width.
        
        Args:
            width: Width of the elbow in inches
            lined: True for lined elbows (only applies to square elbows)
            
        Returns:
            DataFrame with comparison results
        """
        data = []
        
        for freq in self.octave_bands:
            row = {'Frequency (Hz)': freq}
            
            # Square elbows without turning vanes
            row['Square No Vanes (Unlined)'] = self.calculate_elbow_insertion_loss(
                freq, width, 'square_no_vanes', False)
            row['Square No Vanes (Lined)'] = self.calculate_elbow_insertion_loss(
                freq, width, 'square_no_vanes', True)
            
            # Radiused elbows
            row['Radiused'] = self.calculate_elbow_insertion_loss(
                freq, width, 'radiused')
            
            # Square elbows with turning vanes
            row['Square With Vanes (Unlined)'] = self.calculate_elbow_insertion_loss(
                freq, width, 'square_with_vanes', False)
            row['Square With Vanes (Lined)'] = self.calculate_elbow_insertion_loss(
                freq, width, 'square_with_vanes', True)
            
            data.append(row)
            
        return pd.DataFrame(data)
        
    def create_insertion_loss_dataframe(self, widths: List[float], 
                                      elbow_type: str = 'square_no_vanes', 
                                      lined: bool = False) -> pd.DataFrame:
        """
        Create a DataFrame with insertion loss values for multiple widths.
        
        Args:
            widths: List of elbow widths in inches
            elbow_type: Type of elbow ('square_no_vanes', 'radiused', 'square_with_vanes')
            lined: True for lined elbows (only applies to square elbows)
            
        Returns:
            DataFrame with insertion loss values
        """
        data = []
        
        for width in widths:
            spectrum = self.calculate_spectrum_insertion_loss(width, elbow_type, lined)
            row = {'Width (inches)': width}
            row.update(spectrum)
            data.append(row)
            
        return pd.DataFrame(data)
        
    def plot_insertion_loss_comparison(self, width: float, 
                                     save_path: Optional[str] = None):
        """
        Plot insertion loss comparison for all elbow types.
        
        Args:
            width: Width of the elbow in inches
            save_path: Optional path to save the plot
        """
        df = self.compare_elbow_types(width)
        
        plt.figure(figsize=(12, 8))
        
        # Plot each elbow type
        elbow_types = ['Square No Vanes (Unlined)', 'Square No Vanes (Lined)', 
                      'Radiused', 'Square With Vanes (Unlined)', 'Square With Vanes (Lined)']
        
        for elbow_type in elbow_types:
            plt.plot(df['Frequency (Hz)'], df[elbow_type], 
                    marker='o', linewidth=2, markersize=6, label=elbow_type)
        
        plt.xlabel('Frequency (Hz)')
        plt.ylabel('Insertion Loss (dB)')
        plt.title(f'Rectangular Elbow Insertion Loss Comparison\nWidth = {width} inches')
        plt.legend(bbox_to_anchor=(1.05, 1), loc='upper left')
        plt.grid(True, alpha=0.3)
        plt.xscale('log')
        plt.xticks(self.octave_bands, [str(f) for f in self.octave_bands])
        
        plt.tight_layout()
        
        if save_path:
            plt.savefig(save_path, dpi=300, bbox_inches='tight')
        
        plt.show()
        
    def plot_width_comparison(self, widths: List[float], 
                            elbow_type: str = 'square_no_vanes', 
                            lined: bool = False,
                            save_path: Optional[str] = None):
        """
        Plot insertion loss for different widths of the same elbow type.
        
        Args:
            widths: List of elbow widths in inches
            elbow_type: Type of elbow ('square_no_vanes', 'radiused', 'square_with_vanes')
            lined: True for lined elbows (only applies to square elbows)
            save_path: Optional path to save the plot
        """
        df = self.create_insertion_loss_dataframe(widths, elbow_type, lined)
        
        plt.figure(figsize=(12, 8))
        
        # Plot each width
        for _, row in df.iterrows():
            width = float(row['Width (inches)'])
            frequencies = [int(f.split()[0]) for f in row.index if f != 'Width (inches)']
            losses = [float(row[f'{f} Hz']) for f in frequencies]
            
            plt.plot(frequencies, losses, marker='o', linewidth=2, 
                    markersize=6, label=f'{width} inches')
        
        plt.xlabel('Frequency (Hz)')
        plt.ylabel('Insertion Loss (dB)')
        
        elbow_type_name = elbow_type.replace('_', ' ').title()
        lining_status = 'Lined' if lined else 'Unlined'
        plt.title(f'{elbow_type_name} - {lining_status}\nInsertion Loss vs Width')
        
        plt.legend(bbox_to_anchor=(1.05, 1), loc='upper left')
        plt.grid(True, alpha=0.3)
        plt.xscale('log')
        plt.xticks(self.octave_bands, [str(f) for f in self.octave_bands])
        
        plt.tight_layout()
        
        if save_path:
            plt.savefig(save_path, dpi=300, bbox_inches='tight')
        
        plt.show()
        
    def generate_report(self, width: float, elbow_type: str = 'square_no_vanes', 
                       lined: bool = False) -> str:
        """
        Generate a comprehensive report for elbow insertion loss calculations.
        
        Args:
            width: Width of the elbow in inches
            elbow_type: Type of elbow ('square_no_vanes', 'radiused', 'square_with_vanes')
            lined: True for lined elbows (only applies to square elbows)
            
        Returns:
            Formatted report string
        """
        spectrum = self.calculate_spectrum_insertion_loss(width, elbow_type, lined)
        
        report = f"""
RECTANGULAR ELBOW INSERTION LOSS REPORT
=======================================

Elbow Specifications:
- Type: {elbow_type.replace('_', ' ').title()}
- Width: {width} inches
- Lining: {'Yes' if lined else 'No'}

Insertion Loss by Frequency Band:
"""
        
        total_loss = 0
        for freq, loss in spectrum.items():
            report += f"- {freq}: {loss:.1f} dB\n"
            total_loss += loss
            
        report += f"""
Summary:
- Average Insertion Loss: {total_loss/len(spectrum):.1f} dB
- Total Insertion Loss: {total_loss:.1f} dB
- Frequency Range: 63 Hz - 8000 Hz
- Number of Frequency Bands: {len(spectrum)}

Notes:
- Calculations based on ASHRAE 2015 Applications Handbook Chapter 48
- fw product = frequency (kHz) × width (inches)
- For lined elbows, duct lining must extend at least 2 duct widths beyond the elbow
"""
        
        return report
        
    def validate_inputs(self, frequency: float, width: float) -> bool:
        """
        Validate input parameters.
        
        Args:
            frequency: Frequency in Hz
            width: Width of the elbow in inches
            
        Returns:
            True if inputs are valid, False otherwise
        """
        if frequency <= 0:
            warnings.warn("Frequency must be positive")
            return False
        if width <= 0:
            warnings.warn("Width must be positive")
            return False
        if frequency > 20000:  # Reasonable upper limit
            warnings.warn("Frequency seems unusually high")
            return False
        if width > 100:  # Reasonable upper limit
            warnings.warn("Width seems unusually large")
            return False
            
        return True


def main():
    """Main function to demonstrate the calculator usage."""
    # Initialize calculator
    calculator = RectangularElbowsCalculator()
    
    # Example calculations
    print("RECTANGULAR ELBOWS INSERTION LOSS CALCULATOR")
    print("=" * 50)
    
    # Test parameters
    test_width = 12.0  # inches
    test_frequency = 1000  # Hz
    
    print(f"\nTest Parameters:")
    print(f"Width: {test_width} inches")
    print(f"Frequency: {test_frequency} Hz")
    print(f"fw product: {calculator.calculate_fw_product(test_frequency, test_width):.2f}")
    
    # Calculate insertion loss for different elbow types
    print(f"\nInsertion Loss Results:")
    print(f"Square elbows without vanes (unlined): "
          f"{calculator.calculate_elbow_insertion_loss(test_frequency, test_width, 'square_no_vanes', False):.1f} dB")
    print(f"Square elbows without vanes (lined): "
          f"{calculator.calculate_elbow_insertion_loss(test_frequency, test_width, 'square_no_vanes', True):.1f} dB")
    print(f"Radiused elbows: "
          f"{calculator.calculate_elbow_insertion_loss(test_frequency, test_width, 'radiused'):.1f} dB")
    print(f"Square elbows with vanes (unlined): "
          f"{calculator.calculate_elbow_insertion_loss(test_frequency, test_width, 'square_with_vanes', False):.1f} dB")
    print(f"Square elbows with vanes (lined): "
          f"{calculator.calculate_elbow_insertion_loss(test_frequency, test_width, 'square_with_vanes', True):.1f} dB")
    
    # Generate comparison table
    print(f"\nComplete Spectrum Comparison (Width = {test_width} inches):")
    comparison_df = calculator.compare_elbow_types(test_width)
    print(comparison_df.to_string(index=False))
    
    # Generate report
    print(f"\nDetailed Report:")
    report = calculator.generate_report(test_width, 'square_no_vanes', True)
    print(report)
    
    # Create plots
    print(f"\nGenerating plots...")
    calculator.plot_insertion_loss_comparison(test_width)
    
    # Test different widths
    widths = [6, 12, 24, 48]
    calculator.plot_width_comparison(widths, 'square_no_vanes', False)
    
    print(f"\nCalculation complete!")


if __name__ == "__main__":
    main() 