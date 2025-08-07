"""
Receiver Room Sound Correction Calculations (Shultz Method)
Based on ASHRAE 2015 Applications Handbook Chapter 48: Noise and Vibration Control

This script implements calculations for:
1. Single point source sound pressure levels in rooms < 15,000 ft³ (Equations 26 & 27)
2. Single point source sound pressure levels in rooms 15,000-150,000 ft³ (Equation 28)
3. Distributed ceiling array sound pressure levels (Equation 29)

Author: HVAC Acoustics Calculator
Date: 2024
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from typing import Tuple, Dict, List, Optional, Union
import warnings
from scipy.interpolate import interp1d

# Set up plotting style
plt.style.use('seaborn-v0_8')
sns.set_palette("husl")

class ReceiverRoomSoundCorrection:
    """
    Calculator for receiver room sound correction using Shultz method.
    Based on ASHRAE 2015 Applications Handbook Chapter 48.
    """
    
    def __init__(self):
        """Initialize the calculator with ASHRAE reference data."""
        self._initialize_table_35_data()  # Values for A in Equation (27)
        self._initialize_table_36_data()  # Values for B in Equation (27)
        self._initialize_table_37_data()  # Values for C in Equation (28)
        self._initialize_table_38_data()  # Values for D in Equation (29)
        
        # Standard octave band frequencies
        self.frequencies = [63, 125, 250, 500, 1000, 2000, 4000, 8000]
        
    def _initialize_table_35_data(self):
        """Initialize Table 35: Values for A in Equation (27)."""
        # Data from Table 35: Values for A in Equation (26)
        # Format: room_volume: [63, 125, 250, 500, 1000, 2000, 4000] Hz
        self.table_35_data = {
            1500: [4, 3, 2, 1, 0, -1, -2],
            2500: [3, 2, 1, 0, -1, -2, -3],
            4000: [2, 1, 0, -1, -2, -3, -4],
            6000: [1, 0, -1, -2, -3, -4, -5],
            10000: [0, -1, -2, -3, -4, -5, -6],
            15000: [-1, -2, -3, -4, -5, -6, -7]
        }
        
    def _initialize_table_36_data(self):
        """Initialize Table 36: Values for B in Equation (27)."""
        # Data from Table 36: Values for B in Equation (26)
        # Format: distance: B_value
        self.table_36_data = {
            3: 5, 4: 6, 5: 7, 6: 8, 8: 9, 10: 10, 13: 11, 16: 12, 20: 13
        }
        
    def _initialize_table_37_data(self):
        """Initialize Table 37: Values for C in Equation (28)."""
        # Data from Table 37: Values for C in Equation (28)
        # Format: distance: [63, 125, 250, 500, 1000, 2000, 4000] Hz
        self.table_37_data = {
            3: [5, 5, 6, 6, 6, 7, 10],
            4: [6, 7, 7, 7, 8, 9, 12],
            5: [7, 8, 8, 8, 9, 11, 14],
            6: [8, 9, 9, 9, 10, 12, 16],
            8: [9, 10, 10, 11, 12, 14, 18],
            10: [10, 11, 12, 12, 13, 16, 20],
            13: [11, 12, 13, 13, 15, 18, 22],
            16: [12, 13, 14, 15, 16, 19, 24],
            20: [13, 15, 15, 16, 17, 20, 26],
            25: [14, 16, 16, 17, 19, 22, 28],
            32: [15, 17, 17, 18, 20, 23, 30]
        }
        
    def _initialize_table_38_data(self):
        """Initialize Table 38: Values for D in Equation (29)."""
        # Data from Table 38: Values for D in Equation (29)
        # Format: (ceiling_height_range, floor_area_range): [63, 125, 250, 500, 1000, 2000, 4000] Hz
        self.table_38_data = {
            # Ceiling height 8 to 9 ft
            ('8-9', '100-150'): [2, 3, 4, 5, 6, 7, 8],
            ('8-9', '200-250'): [3, 4, 5, 6, 7, 8, 9],
            # Ceiling height 10 to 12 ft
            ('10-12', '100-150'): [4, 5, 6, 7, 8, 9, 10],
            ('10-12', '200-250'): [5, 6, 7, 8, 9, 10, 11],
            # Ceiling height 14 to 16 ft
            ('14-16', '100-150'): [7, 8, 9, 10, 11, 12, 13],
            ('14-16', '200-250'): [8, 9, 10, 11, 12, 13, 14]
        }
        
    def _interpolate_table_35(self, room_volume: float) -> List[float]:
        """
        Interpolate values for A from Table 35 based on room volume.
        
        Args:
            room_volume: Room volume in ft³
            
        Returns:
            List of A values for each frequency band
        """
        if room_volume <= 1500:
            return self.table_35_data[1500]
        elif room_volume >= 15000:
            return self.table_35_data[15000]
        
        volumes = sorted(self.table_35_data.keys())
        a_values = []
        
        for freq_idx in range(7):  # 7 frequency bands
            freq_values = [self.table_35_data[vol][freq_idx] for vol in volumes]
            interpolator = interp1d(volumes, freq_values, kind='linear', 
                                  bounds_error=False, fill_value='extrapolate')
            a_values.append(float(interpolator(room_volume)))
            
        return a_values
        
    def _interpolate_table_36(self, distance: float) -> float:
        """
        Interpolate values for B from Table 36 based on distance.
        
        Args:
            distance: Distance from sound source in ft
            
        Returns:
            B value
        """
        if distance <= 3:
            return self.table_36_data[3]
        elif distance >= 20:
            return self.table_36_data[20]
        
        distances = sorted(self.table_36_data.keys())
        b_values = [self.table_36_data[d] for d in distances]
        
        interpolator = interp1d(distances, b_values, kind='linear',
                               bounds_error=False, fill_value='extrapolate')
        return float(interpolator(distance))
        
    def _interpolate_table_37(self, distance: float) -> List[float]:
        """
        Interpolate values for C from Table 37 based on distance.
        
        Args:
            distance: Distance from sound source in ft
            
        Returns:
            List of C values for each frequency band
        """
        if distance <= 3:
            return self.table_37_data[3]
        elif distance >= 32:
            return self.table_37_data[32]
        
        distances = sorted(self.table_37_data.keys())
        c_values = []
        
        for freq_idx in range(7):  # 7 frequency bands
            freq_values = [self.table_37_data[d][freq_idx] for d in distances]
            interpolator = interp1d(distances, freq_values, kind='linear',
                                   bounds_error=False, fill_value='extrapolate')
            c_values.append(float(interpolator(distance)))
            
        return c_values
        
    def _get_table_38_key(self, ceiling_height: float, floor_area_per_diffuser: float) -> Tuple[str, str]:
        """
        Determine the appropriate key for Table 38 based on ceiling height and floor area.
        
        Args:
            ceiling_height: Ceiling height in ft
            floor_area_per_diffuser: Floor area per diffuser in ft²
            
        Returns:
            Tuple of (ceiling_height_range, floor_area_range)
        """
        # Determine ceiling height range
        if 8 <= ceiling_height <= 9:
            height_range = '8-9'
        elif 10 <= ceiling_height <= 12:
            height_range = '10-12'
        elif 14 <= ceiling_height <= 16:
            height_range = '14-16'
        else:
            # Default to 10-12 ft range for interpolation
            height_range = '10-12'
            
        # Determine floor area range
        if 100 <= floor_area_per_diffuser <= 150:
            area_range = '100-150'
        elif 200 <= floor_area_per_diffuser <= 250:
            area_range = '200-250'
        else:
            # Default to 100-150 ft² range for interpolation
            area_range = '100-150'
            
        return height_range, area_range
        
    def _interpolate_table_38(self, ceiling_height: float, floor_area_per_diffuser: float) -> List[float]:
        """
        Interpolate values for D from Table 38 based on ceiling height and floor area.
        
        Args:
            ceiling_height: Ceiling height in ft
            floor_area_per_diffuser: Floor area per diffuser in ft²
            
        Returns:
            List of D values for each frequency band
        """
        height_range, area_range = self._get_table_38_key(ceiling_height, floor_area_per_diffuser)
        
        # Check if exact match exists
        key = (height_range, area_range)
        if key in self.table_38_data:
            return self.table_38_data[key]
        
        # For now, return default values (can be enhanced with more sophisticated interpolation)
        # Default to 10-12 ft, 100-150 ft² range
        return self.table_38_data[('10-12', '100-150')]
        
    def calculate_single_source_small_room(self, lw: float, distance: float, room_volume: float, 
                                         frequency: float, method: str = 'equation_26') -> float:
        """
        Calculate sound pressure level for single point source in room < 15,000 ft³.
        
        Args:
            lw: Sound power level of sound source, dB (re 10^-12 W)
            distance: Distance from source to receiver, ft
            room_volume: Volume of room, ft³
            frequency: Frequency, Hz
            method: 'equation_26' or 'equation_27'
            
        Returns:
            Sound pressure level, dB (re 20 µPa)
        """
        if method == 'equation_26':
            # Lp = Lw – 10log r – 5log V – 3log f + 25
            lp = lw - 10 * np.log10(distance) - 5 * np.log10(room_volume) - 3 * np.log10(frequency) + 25
        elif method == 'equation_27':
            # Lp = Lw + A – B
            a_values = self._interpolate_table_35(room_volume)
            b_value = self._interpolate_table_36(distance)
            
            # Find the appropriate frequency band
            freq_idx = self._find_frequency_band(frequency)
            a_value = a_values[freq_idx]
            
            lp = lw + a_value - b_value
        else:
            raise ValueError("Method must be 'equation_26' or 'equation_27'")
            
        return lp
        
    def calculate_single_source_large_room(self, lw: float, distance: float, frequency: float) -> float:
        """
        Calculate sound pressure level for single point source in room 15,000-150,000 ft³.
        
        Args:
            lw: Sound power level of sound source, dB (re 10^-12 W)
            distance: Distance from source to receiver, ft
            frequency: Frequency, Hz
            
        Returns:
            Sound pressure level, dB (re 20 µPa)
        """
        # Lp = Lw – C – 5
        c_values = self._interpolate_table_37(distance)
        freq_idx = self._find_frequency_band(frequency)
        c_value = c_values[freq_idx]
        
        lp = lw - c_value - 5
        return lp
        
    def calculate_distributed_ceiling_array(self, lw_single: float, ceiling_height: float, 
                                          floor_area_per_diffuser: float, frequency: float) -> float:
        """
        Calculate sound pressure level for distributed ceiling array at 5 ft above floor.
        
        Args:
            lw_single: Sound power level of single diffuser in array, dB (re 10^-12 W)
            ceiling_height: Ceiling height in ft
            floor_area_per_diffuser: Floor area per diffuser in ft²
            frequency: Frequency, Hz
            
        Returns:
            Sound pressure level at 5 ft above floor, dB (re 20 µPa)
        """
        # Lp(5) = LW(s) – D
        d_values = self._interpolate_table_38(ceiling_height, floor_area_per_diffuser)
        freq_idx = self._find_frequency_band(frequency)
        d_value = d_values[freq_idx]
        
        lp_5 = lw_single - d_value
        return lp_5
        
    def _find_frequency_band(self, frequency: float) -> int:
        """
        Find the appropriate frequency band index for the given frequency.
        
        Args:
            frequency: Frequency in Hz
            
        Returns:
            Index of the frequency band
        """
        if frequency <= 63:
            return 0
        elif frequency <= 125:
            return 1
        elif frequency <= 250:
            return 2
        elif frequency <= 500:
            return 3
        elif frequency <= 1000:
            return 4
        elif frequency <= 2000:
            return 5
        else:
            return 6
            
    def calculate_octave_band_spectrum(self, lw_spectrum: List[float], distance: float, 
                                     room_volume: float, method: str = 'auto') -> Dict[str, List[float]]:
        """
        Calculate octave band sound pressure level spectrum.
        
        Args:
            lw_spectrum: Sound power level spectrum [63, 125, 250, 500, 1000, 2000, 4000] Hz
            distance: Distance from source to receiver, ft
            room_volume: Volume of room, ft³
            method: 'auto', 'equation_26', 'equation_27', or 'equation_28'
            
        Returns:
            Dictionary with frequency bands and corresponding sound pressure levels
        """
        if len(lw_spectrum) != 7:
            raise ValueError("lw_spectrum must have exactly 7 values for octave bands")
            
        lp_spectrum = []
        
        for i, (lw, freq) in enumerate(zip(lw_spectrum, self.frequencies)):
            if method == 'auto':
                if room_volume < 15000:
                    # Use equation 27 for small rooms (more practical)
                    lp = self.calculate_single_source_small_room(lw, distance, room_volume, freq, 'equation_27')
                else:
                    lp = self.calculate_single_source_large_room(lw, distance, freq)
            elif method == 'equation_26':
                lp = self.calculate_single_source_small_room(lw, distance, room_volume, freq, 'equation_26')
            elif method == 'equation_27':
                lp = self.calculate_single_source_small_room(lw, distance, room_volume, freq, 'equation_27')
            elif method == 'equation_28':
                lp = self.calculate_single_source_large_room(lw, distance, freq)
            else:
                raise ValueError("Method must be 'auto', 'equation_26', 'equation_27', or 'equation_28'")
                
            lp_spectrum.append(lp)
            
        return {
            'frequencies': self.frequencies,
            'sound_pressure_levels': lp_spectrum
        }
        
    def calculate_distributed_array_spectrum(self, lw_single_spectrum: List[float], 
                                           ceiling_height: float, 
                                           floor_area_per_diffuser: float) -> Dict[str, List[float]]:
        """
        Calculate octave band sound pressure level spectrum for distributed ceiling array.
        
        Args:
            lw_single_spectrum: Sound power level spectrum of single diffuser [63, 125, 250, 500, 1000, 2000, 4000] Hz
            ceiling_height: Ceiling height in ft
            floor_area_per_diffuser: Floor area per diffuser in ft²
            
        Returns:
            Dictionary with frequency bands and corresponding sound pressure levels
        """
        if len(lw_single_spectrum) != 7:
            raise ValueError("lw_single_spectrum must have exactly 7 values for octave bands")
            
        lp_spectrum = []
        
        for i, (lw_single, freq) in enumerate(zip(lw_single_spectrum, self.frequencies)):
            lp = self.calculate_distributed_ceiling_array(lw_single, ceiling_height, 
                                                        floor_area_per_diffuser, freq)
            lp_spectrum.append(lp)
            
        return {
            'frequencies': self.frequencies,
            'sound_pressure_levels': lp_spectrum
        }
        
    def create_comparison_dataframe(self, lw_spectrum: List[float], distance: float, 
                                  room_volume: float, ceiling_height: float = 10, 
                                  floor_area_per_diffuser: float = 150) -> pd.DataFrame:
        """
        Create a comparison dataframe showing different calculation methods.
        
        Args:
            lw_spectrum: Sound power level spectrum [63, 125, 250, 500, 1000, 2000, 4000] Hz
            distance: Distance from source to receiver, ft
            room_volume: Volume of room, ft³
            ceiling_height: Ceiling height in ft (for distributed array)
            floor_area_per_diffuser: Floor area per diffuser in ft² (for distributed array)
            
        Returns:
            DataFrame with comparison of different calculation methods
        """
        results = []
        
        for i, freq in enumerate(self.frequencies):
            lw = lw_spectrum[i]
            
            # Calculate using different methods
            if room_volume < 15000:
                eq26 = self.calculate_single_source_small_room(lw, distance, room_volume, freq, 'equation_26')
                eq27 = self.calculate_single_source_small_room(lw, distance, room_volume, freq, 'equation_27')
                eq28 = None
            else:
                eq26 = None
                eq27 = None
                eq28 = self.calculate_single_source_large_room(lw, distance, freq)
                
            # Distributed array calculation
            distributed = self.calculate_distributed_ceiling_array(lw, ceiling_height, 
                                                                 floor_area_per_diffuser, freq)
            
            results.append({
                'Frequency_Hz': freq,
                'Sound_Power_Level_dB': lw,
                'Equation_26_dB': eq26,
                'Equation_27_dB': eq27,
                'Equation_28_dB': eq28,
                'Distributed_Array_dB': distributed
            })
            
        return pd.DataFrame(results)
        
    def plot_spectrum_comparison(self, lw_spectrum: List[float], distance: float, 
                               room_volume: float, ceiling_height: float = 10, 
                               floor_area_per_diffuser: float = 150,
                               save_path: Optional[str] = None):
        """
        Plot spectrum comparison for different calculation methods.
        
        Args:
            lw_spectrum: Sound power level spectrum [63, 125, 250, 500, 1000, 2000, 4000] Hz
            distance: Distance from source to receiver, ft
            room_volume: Volume of room, ft³
            ceiling_height: Ceiling height in ft (for distributed array)
            floor_area_per_diffuser: Floor area per diffuser in ft² (for distributed array)
            save_path: Optional path to save the plot
        """
        df = self.create_comparison_dataframe(lw_spectrum, distance, room_volume, 
                                            ceiling_height, floor_area_per_diffuser)
        
        plt.figure(figsize=(12, 8))
        
        # Plot available methods
        if room_volume < 15000:
            plt.plot(df['Frequency_Hz'], df['Equation_26_dB'], 'o-', label='Equation 26', linewidth=2)
            plt.plot(df['Frequency_Hz'], df['Equation_27_dB'], 's-', label='Equation 27', linewidth=2)
        else:
            plt.plot(df['Frequency_Hz'], df['Equation_28_dB'], '^-', label='Equation 28', linewidth=2)
            
        plt.plot(df['Frequency_Hz'], df['Distributed_Array_dB'], 'd-', label='Distributed Array', linewidth=2)
        
        plt.xlabel('Frequency (Hz)')
        plt.ylabel('Sound Pressure Level (dB re 20 µPa)')
        plt.title(f'Receiver Room Sound Correction Comparison\n'
                 f'Room Volume: {room_volume:,.0f} ft³, Distance: {distance} ft')
        plt.legend()
        plt.grid(True, alpha=0.3)
        plt.xscale('log')
        plt.xticks(self.frequencies, [str(f) for f in self.frequencies])
        
        if save_path:
            plt.savefig(save_path, dpi=300, bbox_inches='tight')
            
        plt.tight_layout()
        plt.show()
        
    def generate_report(self, lw_spectrum: List[float], distance: float, room_volume: float,
                       ceiling_height: float = 10, floor_area_per_diffuser: float = 150) -> str:
        """
        Generate a comprehensive report of the calculations.
        
        Args:
            lw_spectrum: Sound power level spectrum [63, 125, 250, 500, 1000, 2000, 4000] Hz
            distance: Distance from source to receiver, ft
            room_volume: Volume of room, ft³
            ceiling_height: Ceiling height in ft (for distributed array)
            floor_area_per_diffuser: Floor area per diffuser in ft² (for distributed array)
            
        Returns:
            Formatted report string
        """
        df = self.create_comparison_dataframe(lw_spectrum, distance, room_volume, 
                                            ceiling_height, floor_area_per_diffuser)
        
        report = []
        report.append("=" * 80)
        report.append("RECEIVER ROOM SOUND CORRECTION CALCULATIONS (SHULTZ METHOD)")
        report.append("Based on ASHRAE 2015 Applications Handbook Chapter 48")
        report.append("=" * 80)
        report.append("")
        
        # Input parameters
        report.append("INPUT PARAMETERS:")
        report.append(f"  Room Volume: {room_volume:,.0f} ft³")
        report.append(f"  Distance from Source: {distance} ft")
        report.append(f"  Ceiling Height: {ceiling_height} ft")
        report.append(f"  Floor Area per Diffuser: {floor_area_per_diffuser} ft²")
        report.append("")
        
        # Sound power levels
        report.append("SOUND POWER LEVEL SPECTRUM:")
        for freq, lw in zip(self.frequencies, lw_spectrum):
            report.append(f"  {freq:4d} Hz: {lw:6.1f} dB")
        report.append("")
        
        # Results table
        report.append("RESULTS:")
        report.append("-" * 80)
        report.append(f"{'Freq':>6} {'Lw':>6} {'Eq26':>6} {'Eq27':>6} {'Eq28':>6} {'Dist':>6}")
        report.append(f"{'(Hz)':>6} {'(dB)':>6} {'(dB)':>6} {'(dB)':>6} {'(dB)':>6} {'(dB)':>6}")
        report.append("-" * 80)
        
        for _, row in df.iterrows():
            freq = int(row['Frequency_Hz'])
            lw = row['Sound_Power_Level_dB']
            eq26 = row['Equation_26_dB']
            eq27 = row['Equation_27_dB']
            eq28 = row['Equation_28_dB']
            dist = row['Distributed_Array_dB']
            
            eq26_str = f"{eq26:.1f}" if eq26 is not None else "  N/A"
            eq27_str = f"{eq27:.1f}" if eq27 is not None else "  N/A"
            eq28_str = f"{eq28:.1f}" if eq28 is not None else "  N/A"
            
            report.append(f"{freq:6d} {lw:6.1f} {eq26_str:>6} {eq27_str:>6} {eq28_str:>6} {dist:6.1f}")
            
        report.append("-" * 80)
        report.append("")
        
        # Summary
        report.append("SUMMARY:")
        if room_volume < 15000:
            report.append(f"  Room volume < 15,000 ft³: Use Equation 26 or 27 for single point sources")
            report.append(f"  Equation 26: Lp = Lw – 10log r – 5log V – 3log f + 25")
            report.append(f"  Equation 27: Lp = Lw + A – B")
        else:
            report.append(f"  Room volume ≥ 15,000 ft³: Use Equation 28 for single point sources")
            report.append(f"  Equation 28: Lp = Lw – C – 5")
            
        report.append(f"  Distributed Array: Lp(5) = LW(s) – D (at 5 ft above floor)")
        report.append("")
        
        # A-weighted levels (approximate)
        a_weights = [-26.2, -16.1, -8.6, -3.2, 0.0, 1.2, 1.0]
        a_weighted_levels = []
        
        for i, freq in enumerate(self.frequencies):
            if room_volume < 15000:
                lp = df.iloc[i]['Equation_27_dB']
            else:
                lp = df.iloc[i]['Equation_28_dB']
                
            if lp is not None:
                a_weighted = lp + a_weights[i]
                a_weighted_levels.append(a_weighted)
                
        if a_weighted_levels:
            # Logarithmic sum for A-weighted level
            a_weighted_sum = 10 * np.log10(sum(10**(level/10) for level in a_weighted_levels))
            report.append(f"  Approximate A-weighted Sound Pressure Level: {a_weighted_sum:.1f} dB(A)")
            
        report.append("=" * 80)
        
        return "\n".join(report)


def main():
    """Main function to demonstrate the calculator usage."""
    # Initialize calculator
    calculator = ReceiverRoomSoundCorrection()
    
    # Example parameters
    lw_spectrum = [85, 82, 78, 75, 72, 68, 65]  # Example sound power spectrum
    distance = 10  # ft
    room_volume = 8000  # ft³
    ceiling_height = 10  # ft
    floor_area_per_diffuser = 150  # ft²
    
    print("Receiver Room Sound Correction Calculator")
    print("=" * 50)
    
    # Generate report
    report = calculator.generate_report(lw_spectrum, distance, room_volume, 
                                      ceiling_height, floor_area_per_diffuser)
    print(report)
    
    # Create comparison plot
    calculator.plot_spectrum_comparison(lw_spectrum, distance, room_volume, 
                                      ceiling_height, floor_area_per_diffuser)
    
    # Example with large room
    print("\n" + "=" * 50)
    print("LARGE ROOM EXAMPLE (Volume = 50,000 ft³)")
    print("=" * 50)
    
    large_room_report = calculator.generate_report(lw_spectrum, distance, 50000, 
                                                 ceiling_height, floor_area_per_diffuser)
    print(large_room_report)


if __name__ == "__main__":
    main() 