"""
Rectangular Duct Acoustic Calculations
Based on ASHRAE 2015 Applications Handbook Chapter 48: Noise and Vibration Control

This script implements calculations for:
1. Unlined rectangular sheet metal duct attenuation
2. 1-inch duct lining insertion loss
3. 2-inch duct lining attenuation

Author: HVAC Acoustics Calculator
Date: 2024
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from typing import Tuple, Dict, List, Optional
import warnings

# Set up plotting style
plt.style.use('seaborn-v0_8')
sns.set_palette("husl")

class RectangularDuctCalculator:
    """
    Calculator for rectangular duct acoustic properties based on ASHRAE standards.
    """
    
    def __init__(self):
        """Initialize the calculator with ASHRAE reference data."""
        self._initialize_unlined_data()
        self._initialize_1inch_lining_data()
        self._initialize_2inch_lining_data()
        
    def _initialize_unlined_data(self):
        """Initialize unlined rectangular duct data from Table 16."""
        # Data from Table 16: Unlined Rectangular Sheet Metal Ducts
        # Format: (width, height, P/A ratio, attenuation at 63 Hz)
        self.unlined_data = {
            (6, 6): {'P_A': 8.0, 'attenuation_63hz': 0.3},
            (12, 12): {'P_A': 4.0, 'attenuation_63hz': 0.4},
            (12, 24): {'P_A': 3.0, 'attenuation_63hz': 0.4},
            (24, 24): {'P_A': 2.0, 'attenuation_63hz': 0.3},
            (48, 48): {'P_A': 1.0, 'attenuation_63hz': 0.2},
            (72, 72): {'P_A': 0.7, 'attenuation_63hz': 0.1}
        }
        
    def _initialize_1inch_lining_data(self):
        """Initialize 1-inch duct lining insertion loss data from Table 17."""
        # Data from Table 17: 1-inch Duct Lining Insertion Loss at 125 Hz
        self.lining_1inch_data = {
            (6, 6): 0.6, (6, 10): 0.5, (6, 12): 0.5, (6, 18): 0.5,
            (8, 8): 0.5, (8, 12): 0.4, (8, 16): 0.4, (8, 24): 0.4,
            (10, 10): 0.4, (10, 16): 0.4, (10, 20): 0.3, (10, 30): 0.3,
            (12, 12): 0.4, (12, 18): 0.3, (12, 24): 0.3, (12, 36): 0.3,
            (15, 15): 0.3, (15, 22): 0.3, (15, 30): 0.3, (15, 45): 0.2,
            (18, 18): 0.3, (18, 28): 0.2, (18, 36): 0.2, (18, 54): 0.2,
            (24, 24): 0.2, (24, 36): 0.2, (24, 48): 0.2, (24, 72): 0.2,
            (30, 30): 0.2, (30, 45): 0.2, (30, 60): 0.2, (30, 90): 0.1,
            (36, 36): 0.2, (36, 54): 0.1, (36, 72): 0.1, (36, 108): 0.1,
            (42, 42): 0.2, (42, 64): 0.1, (42, 84): 0.1, (42, 126): 0.1,
            (48, 48): 0.1, (48, 72): 0.1, (48, 96): 0.1, (48, 144): 0.1
        }
        
    def _initialize_2inch_lining_data(self):
        """Initialize 2-inch duct lining attenuation data from Table 18."""
        # Data from Table 18: 2-inch Duct Lining Attenuation
        # Format: (width, height): [125, 250, 500, 1000, 2000, 4000, 8000] Hz
        self.lining_2inch_data = {
            (6, 6): [0.8, 2.9, 4.9, 7.2, 7.4, 4.3, 2.1],
            (6, 10): [0.7, 2.4, 4.4, 6.4, 6.1, 3.7, 1.8],
            (6, 12): [0.6, 2.3, 4.2, 6.2, 5.8, 3.6, 1.8],
            (6, 18): [0.6, 2.1, 4.0, 5.8, 5.2, 3.3, 1.6],
            (8, 8): [0.6, 2.3, 4.2, 6.2, 5.8, 3.6, 1.8],
            (8, 12): [0.6, 1.9, 3.9, 5.6, 4.9, 3.2, 1.6],
            (8, 16): [0.5, 1.8, 3.7, 5.4, 4.5, 3.0, 1.5],
            (8, 24): [0.5, 1.6, 3.5, 5.0, 4.1, 2.8, 1.4],
            (10, 10): [0.6, 1.9, 3.8, 5.5, 4.7, 3.1, 1.6],
            (10, 16): [0.5, 1.6, 3.4, 5.0, 4.0, 2.7, 1.4],
            (10, 20): [0.4, 1.5, 3.3, 4.8, 3.7, 2.6, 1.3],
            (10, 30): [0.4, 1.3, 3.1, 4.5, 3.3, 2.4, 1.2],
            (12, 12): [0.5, 1.6, 3.5, 5.0, 4.1, 2.8, 1.4],
            (12, 18): [0.4, 1.4, 3.2, 4.6, 3.5, 2.5, 1.3],
            (12, 24): [0.4, 1.3, 3.0, 4.3, 3.2, 2.3, 1.2],
            (12, 36): [0.4, 1.2, 2.9, 4.1, 2.9, 2.2, 1.1],
            (15, 15): [0.4, 1.3, 3.1, 4.5, 3.3, 2.4, 1.2],
            (15, 22): [0.4, 1.2, 2.9, 4.1, 2.9, 2.2, 1.1],
            (15, 30): [0.3, 1.1, 2.7, 3.9, 2.6, 2.0, 1.0],
            (15, 45): [0.3, 1.0, 2.6, 3.6, 2.4, 1.9, 1.0],
            (18, 18): [0.4, 1.2, 2.9, 4.1, 2.9, 2.2, 1.1],
            (18, 28): [0.3, 1.0, 2.6, 3.7, 2.4, 1.9, 1.0],
            (18, 36): [0.3, 0.9, 2.5, 3.5, 2.2, 1.8, 0.9],
            (18, 54): [0.3, 0.8, 2.3, 3.3, 2.0, 1.7, 0.9],
            (24, 24): [0.3, 0.9, 2.5, 3.5, 2.2, 1.8, 0.9],
            (24, 36): [0.3, 0.8, 2.3, 3.2, 1.9, 1.6, 0.8],
            (24, 48): [0.2, 0.7, 2.2, 3.0, 1.7, 1.5, 0.8],
            (24, 72): [0.2, 0.7, 2.0, 2.9, 1.6, 1.4, 0.7],
            (30, 30): [0.2, 0.8, 2.2, 3.1, 1.8, 1.6, 0.8],
            (30, 45): [0.2, 0.7, 2.0, 2.9, 1.6, 1.4, 0.7],
            (30, 60): [0.2, 0.6, 1.9, 2.7, 1.4, 1.3, 0.7],
            (30, 90): [0.2, 0.5, 1.8, 2.6, 1.3, 1.2, 0.6],
            (36, 36): [0.2, 0.7, 2.0, 2.9, 1.6, 1.4, 0.7],
            (36, 54): [0.2, 0.6, 1.9, 2.6, 1.3, 1.2, 0.6],
            (36, 72): [0.2, 0.5, 1.8, 2.5, 1.2, 1.2, 0.6],
            (36, 108): [0.2, 0.5, 1.7, 2.3, 1.1, 1.1, 0.6],
            (42, 42): [0.2, 0.6, 1.9, 2.6, 1.4, 1.3, 0.7],
            (42, 64): [0.2, 0.5, 1.7, 2.4, 1.2, 1.1, 0.6],
            (42, 84): [0.2, 0.5, 1.6, 2.3, 1.1, 1.1, 0.6],
            (42, 126): [0.1, 0.4, 1.6, 2.2, 1.0, 1.0, 0.5],
            (48, 48): [0.2, 0.5, 1.8, 2.5, 1.2, 1.2, 0.6],
            (48, 72): [0.2, 0.4, 1.6, 2.3, 1.0, 1.0, 0.5],
            (48, 96): [0.1, 0.4, 1.5, 2.1, 1.0, 1.0, 0.5],
            (48, 144): [0.1, 0.4, 1.5, 2.0, 0.9, 0.9, 0.5]
        }
        
        # Frequency bands for 2-inch lining data
        self.frequency_bands = [125, 250, 500, 1000, 2000, 4000, 8000]
    
    def calculate_p_a_ratio(self, width: float, height: float) -> float:
        """
        Calculate the perimeter-to-area ratio (P/A) for a rectangular duct.
        
        Args:
            width: Duct width in inches
            height: Duct height in inches
            
        Returns:
            P/A ratio in 1/ft
        """
        # Convert inches to feet
        width_ft = width / 12.0
        height_ft = height / 12.0
        
        # Calculate perimeter and area
        perimeter = 2 * (width_ft + height_ft)  # ft
        area = width_ft * height_ft  # ft²
        
        # P/A ratio in 1/ft
        p_a_ratio = perimeter / area
        
        return p_a_ratio
    
    def get_unlined_attenuation(self, width: float, height: float, 
                               length: float = 1.0) -> Dict[str, float]:
        """
        Get attenuation for unlined rectangular duct.
        
        Args:
            width: Duct width in inches
            height: Duct height in inches
            length: Duct length in feet (default: 1.0)
            
        Returns:
            Dictionary with P/A ratio and attenuation values
        """
        # Normalize dimensions (smaller dimension first)
        dim1, dim2 = min(width, height), max(width, height)
        duct_size = (dim1, dim2)
        
        # Check if exact size exists in data
        if duct_size in self.unlined_data:
            data = self.unlined_data[duct_size]
            attenuation = data['attenuation_63hz'] * length
            return {
                'duct_size': f"{dim1} x {dim2} in",
                'p_a_ratio': data['P_A'],
                'attenuation_63hz_db_ft': data['attenuation_63hz'],
                'total_attenuation_63hz_db': attenuation,
                'length_ft': length,
                'method': 'exact_match'
            }
        
        # Interpolate if size not in data
        return self._interpolate_unlined_attenuation(width, height, length)
    
    def _interpolate_unlined_attenuation(self, width: float, height: float, 
                                       length: float) -> Dict[str, float]:
        """
        Interpolate unlined attenuation for duct sizes not in reference data.
        
        Args:
            width: Duct width in inches
            height: Duct height in inches
            length: Duct length in feet
            
        Returns:
            Dictionary with interpolated values
        """
        # Calculate P/A ratio for the given dimensions
        p_a_ratio = self.calculate_p_a_ratio(width, height)
        
        # Find closest data points for interpolation
        p_a_values = [data['P_A'] for data in self.unlined_data.values()]
        atten_values = [data['attenuation_63hz'] for data in self.unlined_data.values()]
        
        # Simple linear interpolation based on P/A ratio
        if p_a_ratio <= min(p_a_values):
            attenuation = max(atten_values)
        elif p_a_ratio >= max(p_a_values):
            attenuation = min(atten_values)
        else:
            # Find the two closest P/A values
            sorted_data = sorted(self.unlined_data.items(), 
                               key=lambda x: x[1]['P_A'])
            
            for i in range(len(sorted_data) - 1):
                if (sorted_data[i][1]['P_A'] <= p_a_ratio <= 
                    sorted_data[i+1][1]['P_A']):
                    
                    p_a1, atten1 = sorted_data[i][1]['P_A'], sorted_data[i][1]['attenuation_63hz']
                    p_a2, atten2 = sorted_data[i+1][1]['P_A'], sorted_data[i+1][1]['attenuation_63hz']
                    
                    # Linear interpolation
                    attenuation = atten1 + (atten2 - atten1) * (p_a_ratio - p_a1) / (p_a2 - p_a1)
                    break
            else:
                # Fallback to nearest neighbor
                closest = min(self.unlined_data.items(), 
                            key=lambda x: abs(x[1]['P_A'] - p_a_ratio))
                attenuation = closest[1]['attenuation_63hz']
        
        total_attenuation = attenuation * length
        
        return {
            'duct_size': f"{width} x {height} in",
            'p_a_ratio': p_a_ratio,
            'attenuation_63hz_db_ft': attenuation,
            'total_attenuation_63hz_db': total_attenuation,
            'length_ft': length,
            'method': 'interpolated'
        }
    
    def get_1inch_lining_insertion_loss(self, width: float, height: float, 
                                      length: float = 1.0) -> Dict[str, float]:
        """
        Get insertion loss for 1-inch duct lining.
        
        Args:
            width: Duct width in inches
            height: Duct height in inches
            length: Duct length in feet (default: 1.0)
            
        Returns:
            Dictionary with insertion loss values
        """
        # Normalize dimensions
        dim1, dim2 = min(width, height), max(width, height)
        duct_size = (dim1, dim2)
        
        if duct_size in self.lining_1inch_data:
            insertion_loss_per_ft = self.lining_1inch_data[duct_size]
            total_insertion_loss = insertion_loss_per_ft * length
            
            return {
                'duct_size': f"{dim1} x {dim2} in",
                'insertion_loss_125hz_db_ft': insertion_loss_per_ft,
                'total_insertion_loss_125hz_db': total_insertion_loss,
                'length_ft': length,
                'method': 'exact_match'
            }
        
        # Interpolate if size not in data
        return self._interpolate_1inch_lining(width, height, length)
    
    def _interpolate_1inch_lining(self, width: float, height: float, 
                                length: float) -> Dict[str, float]:
        """
        Interpolate 1-inch lining insertion loss for duct sizes not in reference data.
        """
        # Find closest duct size for interpolation
        closest_size = min(self.lining_1inch_data.keys(),
                          key=lambda x: abs(x[0] - width) + abs(x[1] - height))
        
        insertion_loss_per_ft = self.lining_1inch_data[closest_size]
        total_insertion_loss = insertion_loss_per_ft * length
        
        return {
            'duct_size': f"{width} x {height} in",
            'insertion_loss_125hz_db_ft': insertion_loss_per_ft,
            'total_insertion_loss_125hz_db': total_insertion_loss,
            'length_ft': length,
            'method': 'interpolated',
            'closest_reference_size': f"{closest_size[0]} x {closest_size[1]} in"
        }
    
    def get_2inch_lining_attenuation(self, width: float, height: float, 
                                   length: float = 1.0) -> Dict[str, any]:
        """
        Get attenuation for 2-inch duct lining across all frequency bands.
        
        Args:
            width: Duct width in inches
            height: Duct height in inches
            length: Duct length in feet (default: 1.0)
            
        Returns:
            Dictionary with attenuation values for all frequency bands
        """
        # Normalize dimensions
        dim1, dim2 = min(width, height), max(width, height)
        duct_size = (dim1, dim2)
        
        if duct_size in self.lining_2inch_data:
            attenuation_per_ft = self.lining_2inch_data[duct_size]
            total_attenuation = [att * length for att in attenuation_per_ft]
            
            result = {
                'duct_size': f"{dim1} x {dim2} in",
                'length_ft': length,
                'method': 'exact_match',
                'frequency_bands_hz': self.frequency_bands.copy()
            }
            
            # Add per-foot and total attenuation for each frequency
            for i, freq in enumerate(self.frequency_bands):
                result[f'attenuation_{freq}hz_db_ft'] = attenuation_per_ft[i]
                result[f'total_attenuation_{freq}hz_db'] = total_attenuation[i]
            
            return result
        
        # Interpolate if size not in data
        return self._interpolate_2inch_lining(width, height, length)
    
    def _interpolate_2inch_lining(self, width: float, height: float, 
                                length: float) -> Dict[str, any]:
        """
        Interpolate 2-inch lining attenuation for duct sizes not in reference data.
        """
        # Find closest duct size for interpolation
        closest_size = min(self.lining_2inch_data.keys(),
                          key=lambda x: abs(x[0] - width) + abs(x[1] - height))
        
        attenuation_per_ft = self.lining_2inch_data[closest_size]
        total_attenuation = [att * length for att in attenuation_per_ft]
        
        result = {
            'duct_size': f"{width} x {height} in",
            'length_ft': length,
            'method': 'interpolated',
            'closest_reference_size': f"{closest_size[0]} x {closest_size[1]} in",
            'frequency_bands_hz': self.frequency_bands.copy()
        }
        
        # Add per-foot and total attenuation for each frequency
        for i, freq in enumerate(self.frequency_bands):
            result[f'attenuation_{freq}hz_db_ft'] = attenuation_per_ft[i]
            result[f'total_attenuation_{freq}hz_db'] = total_attenuation[i]
        
        return result
    
    def calculate_total_attenuation(self, width: float, height: float, 
                                  length: float = 1.0, 
                                  lining_type: str = 'unlined') -> Dict[str, any]:
        """
        Calculate total attenuation for a rectangular duct.
        
        Args:
            width: Duct width in inches
            height: Duct height in inches
            length: Duct length in feet
            lining_type: 'unlined', '1inch', or '2inch'
            
        Returns:
            Dictionary with comprehensive attenuation data
        """
        if lining_type == 'unlined':
            return self.get_unlined_attenuation(width, height, length)
        elif lining_type == '1inch':
            return self.get_1inch_lining_insertion_loss(width, height, length)
        elif lining_type == '2inch':
            return self.get_2inch_lining_attenuation(width, height, length)
        else:
            raise ValueError("lining_type must be 'unlined', '1inch', or '2inch'")
    
    def create_attenuation_dataframe(self, duct_sizes: List[Tuple[float, float]], 
                                   length: float = 1.0) -> pd.DataFrame:
        """
        Create a pandas DataFrame with attenuation data for multiple duct sizes.
        
        Args:
            duct_sizes: List of (width, height) tuples in inches
            length: Duct length in feet
            
        Returns:
            DataFrame with attenuation data
        """
        data = []
        
        for width, height in duct_sizes:
            # Unlined data
            unlined = self.get_unlined_attenuation(width, height, length)
            
            # 1-inch lining data
            lining_1inch = self.get_1inch_lining_insertion_loss(width, height, length)
            
            # 2-inch lining data
            lining_2inch = self.get_2inch_lining_attenuation(width, height, length)
            
            row = {
                'Duct_Size_in': f"{width} x {height}",
                'P_A_Ratio_1_ft': unlined['p_a_ratio'],
                'Unlined_63Hz_dB_ft': unlined['attenuation_63hz_db_ft'],
                'Unlined_63Hz_Total_dB': unlined['total_attenuation_63hz_db'],
                '1inch_Lining_125Hz_dB_ft': lining_1inch['insertion_loss_125hz_db_ft'],
                '1inch_Lining_125Hz_Total_dB': lining_1inch['total_insertion_loss_125hz_db']
            }
            
            # Add 2-inch lining data for all frequencies
            for freq in self.frequency_bands:
                row[f'2inch_Lining_{freq}Hz_dB_ft'] = lining_2inch[f'attenuation_{freq}hz_db_ft']
                row[f'2inch_Lining_{freq}Hz_Total_dB'] = lining_2inch[f'total_attenuation_{freq}hz_db']
            
            data.append(row)
        
        return pd.DataFrame(data)
    
    def plot_attenuation_comparison(self, width: float, height: float, 
                                  length: float = 1.0, 
                                  save_path: Optional[str] = None):
        """
        Create a comparison plot of attenuation for different lining types.
        
        Args:
            width: Duct width in inches
            height: Duct height in inches
            length: Duct length in feet
            save_path: Optional path to save the plot
        """
        # Get data for all lining types
        unlined = self.get_unlined_attenuation(width, height, length)
        lining_1inch = self.get_1inch_lining_insertion_loss(width, height, length)
        lining_2inch = self.get_2inch_lining_attenuation(width, height, length)
        
        # Prepare data for plotting
        frequencies = [63, 125] + self.frequency_bands
        unlined_values = [unlined['total_attenuation_63hz_db']] + [0] * (len(frequencies) - 1)
        lining_1inch_values = [0, lining_1inch['total_insertion_loss_125hz_db']] + [0] * (len(frequencies) - 2)
        lining_2inch_values = [0, 0] + [lining_2inch[f'total_attenuation_{freq}hz_db'] for freq in self.frequency_bands]
        
        # Create the plot
        plt.figure(figsize=(12, 8))
        
        plt.plot(frequencies, unlined_values, 'o-', label='Unlined', linewidth=2, markersize=8)
        plt.plot(frequencies, lining_1inch_values, 's-', label='1-inch Lining', linewidth=2, markersize=8)
        plt.plot(frequencies, lining_2inch_values, '^-', label='2-inch Lining', linewidth=2, markersize=8)
        
        plt.xlabel('Frequency (Hz)', fontsize=12)
        plt.ylabel('Attenuation (dB)', fontsize=12)
        plt.title(f'Rectangular Duct Attenuation Comparison\n{width}" x {height}" x {length} ft', 
                 fontsize=14, fontweight='bold')
        plt.grid(True, alpha=0.3)
        plt.legend(fontsize=11)
        plt.xscale('log')
        plt.xticks(frequencies, [str(f) for f in frequencies])
        
        # Add text box with duct information
        textstr = f'Duct Size: {width}" x {height}"\nLength: {length} ft\nP/A Ratio: {unlined["p_a_ratio"]:.2f} 1/ft'
        props = dict(boxstyle='round', facecolor='wheat', alpha=0.8)
        plt.text(0.02, 0.98, textstr, transform=plt.gca().transAxes, fontsize=10,
                verticalalignment='top', bbox=props)
        
        plt.tight_layout()
        
        if save_path:
            plt.savefig(save_path, dpi=300, bbox_inches='tight')
        
        plt.show()
    
    def generate_report(self, width: float, height: float, length: float = 1.0) -> str:
        """
        Generate a comprehensive text report for the duct calculations.
        
        Args:
            width: Duct width in inches
            height: Duct height in inches
            length: Duct length in feet
            
        Returns:
            Formatted report string
        """
        unlined = self.get_unlined_attenuation(width, height, length)
        lining_1inch = self.get_1inch_lining_insertion_loss(width, height, length)
        lining_2inch = self.get_2inch_lining_attenuation(width, height, length)
        
        report = f"""
RECTANGULAR DUCT ACOUSTIC CALCULATIONS
=====================================

Duct Specifications:
- Dimensions: {width}" x {height}" x {length} ft
- Perimeter-to-Area Ratio: {unlined['p_a_ratio']:.2f} 1/ft
- Cross-sectional Area: {(width/12)*(height/12):.2f} ft²

UNLINED RECTANGULAR DUCT:
- Attenuation at 63 Hz: {unlined['attenuation_63hz_db_ft']:.2f} dB/ft
- Total Attenuation: {unlined['total_attenuation_63hz_db']:.2f} dB
- Method: {unlined['method']}

1-INCH DUCT LINING (Insertion Loss):
- Insertion Loss at 125 Hz: {lining_1inch['insertion_loss_125hz_db_ft']:.2f} dB/ft
- Total Insertion Loss: {lining_1inch['total_insertion_loss_125hz_db']:.2f} dB
- Method: {lining_1inch['method']}

2-INCH DUCT LINING (Attenuation):
"""
        
        for freq in self.frequency_bands:
            atten_per_ft = lining_2inch[f'attenuation_{freq}hz_db_ft']
            total_atten = lining_2inch[f'total_attenuation_{freq}hz_db']
            report += f"- {freq} Hz: {atten_per_ft:.2f} dB/ft ({total_atten:.2f} dB total)\n"
        
        report += f"- Method: {lining_2inch['method']}\n"
        
        if 'closest_reference_size' in lining_1inch:
            report += f"- Closest Reference Size: {lining_1inch['closest_reference_size']}\n"
        
        if 'closest_reference_size' in lining_2inch:
            report += f"- Closest Reference Size: {lining_2inch['closest_reference_size']}\n"
        
        report += """
NOTES:
- Values based on ASHRAE 2015 Applications Handbook Chapter 48
- Applies to lightest gage sheet metal ducts per SMACNA standards
- Attenuation for lengths > 10 ft not well documented
- Low frequency breakout noise should be checked
"""
        
        return report


def main():
    """Example usage of the RectangularDuctCalculator class."""
    
    # Initialize calculator
    calc = RectangularDuctCalculator()
    
    # Example calculations
    print("=== RECTANGULAR DUCT CALCULATOR ===\n")
    
    # Test with a standard duct size
    width, height, length = 12, 24, 5.0
    
    print(f"Calculating for {width}\" x {height}\" x {length} ft duct:\n")
    
    # Get all calculations
    unlined = calc.get_unlined_attenuation(width, height, length)
    lining_1inch = calc.get_1inch_lining_insertion_loss(width, height, length)
    lining_2inch = calc.get_2inch_lining_attenuation(width, height, length)
    
    print("UNLINED DUCT:")
    print(f"  Attenuation at 63 Hz: {unlined['attenuation_63hz_db_ft']:.2f} dB/ft")
    print(f"  Total Attenuation: {unlined['total_attenuation_63hz_db']:.2f} dB")
    print(f"  P/A Ratio: {unlined['p_a_ratio']:.2f} 1/ft")
    
    print("\n1-INCH LINING:")
    print(f"  Insertion Loss at 125 Hz: {lining_1inch['insertion_loss_125hz_db_ft']:.2f} dB/ft")
    print(f"  Total Insertion Loss: {lining_1inch['total_insertion_loss_125hz_db']:.2f} dB")
    
    print("\n2-INCH LINING:")
    for freq in calc.frequency_bands:
        atten = lining_2inch[f'attenuation_{freq}hz_db_ft']
        total = lining_2inch[f'total_attenuation_{freq}hz_db']
        print(f"  {freq} Hz: {atten:.2f} dB/ft ({total:.2f} dB total)")
    
    # Create comparison plot
    print("\nGenerating comparison plot...")
    calc.plot_attenuation_comparison(width, height, length)
    
    # Generate comprehensive report
    print("\nGenerating detailed report...")
    report = calc.generate_report(width, height, length)
    print(report)
    
    # Create DataFrame for multiple duct sizes
    print("Creating comparison table for multiple duct sizes...")
    duct_sizes = [(6, 6), (12, 12), (12, 24), (24, 24), (48, 48)]
    df = calc.create_attenuation_dataframe(duct_sizes, length=1.0)
    print(df.to_string(index=False))


if __name__ == "__main__":
    main() 