"""
Optimum RT60 Data Loader - Parse and interpolate optimum reverberation time data
"""

import os
import csv
import numpy as np
from typing import Dict, List, Tuple, Optional

class OptimumRT60Loader:
    """Loader for optimum RT60 data from CSV files"""
    
    def __init__(self):
        self.data = None
        self.frequencies = [125, 250, 500, 1000, 2000, 4000]
        self.load_data()
    
    def get_csv_path(self) -> str:
        """Get path to the optimum_rt_speech.csv file"""
        current_dir = os.path.dirname(__file__)
        project_root = os.path.dirname(os.path.dirname(current_dir))
        return os.path.join(project_root, 'materials', 'optimum_rt_speech.csv')
    
    def load_data(self) -> None:
        """Load optimum RT60 data from CSV file"""
        csv_path = self.get_csv_path()
        
        if not os.path.exists(csv_path):
            print(f"Warning: Optimum RT60 CSV not found at {csv_path}")
            self.data = self.get_fallback_data()
            return
        
        try:
            self.data = []
            with open(csv_path, 'r') as file:
                csv_reader = csv.reader(file)
                
                # Skip header rows
                next(csv_reader)  # Skip first header
                next(csv_reader)  # Skip second header
                
                for row in csv_reader:
                    if len(row) >= 8:  # Ensure we have all columns
                        try:
                            # Parse volume (remove commas and convert to float)
                            volume_str = row[1].replace(',', '').replace(' ', '')
                            volume = float(volume_str)
                            
                            # Parse RT60 values for each frequency
                            rt60_values = {}
                            for i, freq in enumerate(self.frequencies):
                                rt60_values[freq] = float(row[2 + i])
                            
                            self.data.append({
                                'volume': volume,
                                'rt60_values': rt60_values
                            })
                            
                        except (ValueError, IndexError) as e:
                            print(f"Warning: Skipping invalid row in CSV: {row}")
                            continue
            
            # Sort by volume for interpolation
            self.data.sort(key=lambda x: x['volume'])
            print(f"Loaded {len(self.data)} optimum RT60 data points from CSV")
            
        except Exception as e:
            print(f"Error loading optimum RT60 data: {e}")
            self.data = self.get_fallback_data()
    
    def get_fallback_data(self) -> List[Dict]:
        """Provide fallback data if CSV is not available"""
        # Create some reasonable fallback data based on typical speech rooms
        volumes = [10000, 20000, 30000, 50000, 75000, 100000, 200000, 500000, 1000000]
        fallback_data = []
        
        for volume in volumes:
            # Approximate optimum RT60 values for speech rooms
            # These are rough estimates and should be replaced with actual data
            base_rt60 = 0.6 + 0.4 * np.log10(volume / 10000) / 2
            
            rt60_values = {}
            for freq in self.frequencies:
                # Lower frequencies typically have slightly higher RT60
                if freq <= 250:
                    multiplier = 1.2
                elif freq <= 500:
                    multiplier = 1.1
                else:
                    multiplier = 1.0
                
                rt60_values[freq] = base_rt60 * multiplier
            
            fallback_data.append({
                'volume': volume,
                'rt60_values': rt60_values
            })
        
        return fallback_data
    
    def get_optimum_rt60_for_volume(self, volume: float) -> Dict[int, float]:
        """
        Get optimum RT60 values for a specific room volume using interpolation
        
        Args:
            volume: Room volume in cubic feet
            
        Returns:
            Dict mapping frequency to optimum RT60 value
        """
        if not self.data or volume <= 0:
            return {freq: 0.8 for freq in self.frequencies}  # Default fallback
        
        # Find the two closest volume points for interpolation
        if volume <= self.data[0]['volume']:
            # Use the smallest volume data
            return self.data[0]['rt60_values'].copy()
        
        if volume >= self.data[-1]['volume']:
            # Use the largest volume data
            return self.data[-1]['rt60_values'].copy()
        
        # Find surrounding data points
        lower_point = None
        upper_point = None
        
        for i, point in enumerate(self.data):
            if point['volume'] <= volume:
                lower_point = point
            else:
                upper_point = point
                break
        
        if not upper_point:
            upper_point = self.data[-1]
        if not lower_point:
            lower_point = self.data[0]
        
        # Interpolate RT60 values for each frequency
        interpolated_values = {}
        
        for freq in self.frequencies:
            lower_rt60 = lower_point['rt60_values'][freq]
            upper_rt60 = upper_point['rt60_values'][freq]
            lower_vol = lower_point['volume']
            upper_vol = upper_point['volume']
            
            if upper_vol == lower_vol:
                interpolated_values[freq] = lower_rt60
            else:
                # Linear interpolation
                ratio = (volume - lower_vol) / (upper_vol - lower_vol)
                interpolated_values[freq] = lower_rt60 + ratio * (upper_rt60 - lower_rt60)
        
        return interpolated_values
    
    def get_volume_range(self) -> Tuple[float, float]:
        """Get the min and max volumes in the dataset"""
        if not self.data:
            return (10000, 1000000)  # Default range
        
        return (self.data[0]['volume'], self.data[-1]['volume'])
    
    def get_rt60_range(self) -> Tuple[float, float]:
        """Get the min and max RT60 values across all frequencies and volumes"""
        if not self.data:
            return (0.3, 1.5)  # Default range
        
        all_rt60_values = []
        for point in self.data:
            all_rt60_values.extend(point['rt60_values'].values())
        
        return (min(all_rt60_values), max(all_rt60_values))
    
    def get_frequencies(self) -> List[int]:
        """Get the list of frequencies in the dataset"""
        return self.frequencies.copy()


# Global instance for easy access
_optimum_loader = None

def get_optimum_rt60_loader() -> OptimumRT60Loader:
    """Get the global optimum RT60 loader instance"""
    global _optimum_loader
    if _optimum_loader is None:
        _optimum_loader = OptimumRT60Loader()
    return _optimum_loader

def get_optimum_rt60_for_volume(volume: float) -> Dict[int, float]:
    """Convenience function to get optimum RT60 for a volume"""
    loader = get_optimum_rt60_loader()
    return loader.get_optimum_rt60_for_volume(volume)