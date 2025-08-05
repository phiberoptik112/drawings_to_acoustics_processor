"""
RT60 Plot Widget - Real-time frequency response plotting for RT60 calculations
"""

import matplotlib
matplotlib.use('Qt5Agg')  # Use Qt backend for PySide6 compatibility

import matplotlib.pyplot as plt
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
import numpy as np

from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QSizePolicy
from PySide6.QtCore import Qt, Signal

from typing import Dict, List, Optional

# Import our data loader
try:
    from ..data.optimum_rt60_loader import get_optimum_rt60_loader
except ImportError:
    try:
        from data.optimum_rt60_loader import get_optimum_rt60_loader
    except ImportError:
        import sys
        import os
        sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
        from data.optimum_rt60_loader import get_optimum_rt60_loader


class RT60PlotWidget(QWidget):
    """Widget for displaying RT60 frequency response plots"""
    
    plot_clicked = Signal(float)  # Emitted when plot is clicked with frequency value
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        # Initialize data
        self.frequencies = [125, 250, 500, 1000, 2000, 4000]
        self.current_rt60_values = {}
        self.optimum_rt60_values = {}
        self.room_volume = 0
        
        # Get optimum data loader
        self.optimum_loader = get_optimum_rt60_loader()
        
        # Initialize UI
        self.init_ui()
        self.setup_plot()
        
        # Set default data
        self.update_optimum_rt60(10000)  # Default 10,000 cf room
    
    def init_ui(self):
        """Initialize the user interface"""
        layout = QVBoxLayout()
        
        # Title
        title_label = QLabel("RT60 Frequency Response")
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title_label.setStyleSheet("font-weight: bold; font-size: 14px; margin-bottom: 5px;")
        layout.addWidget(title_label)
        
        # Create matplotlib figure and canvas
        self.figure = Figure(figsize=(8, 6), dpi=100)
        self.canvas = FigureCanvas(self.figure)
        self.canvas.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        
        layout.addWidget(self.canvas)
        
        # Status label
        self.status_label = QLabel("Ready to plot RT60 data")
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.status_label.setStyleSheet("color: #7f8c8d; font-size: 10px; margin-top: 5px;")
        layout.addWidget(self.status_label)
        
        self.setLayout(layout)
    
    def setup_plot(self):
        """Set up the matplotlib plot"""
        # Clear the figure
        self.figure.clear()
        
        # Create subplot
        self.ax = self.figure.add_subplot(111)
        
        # Set up the plot style
        self.ax.set_xlabel('Frequency (Hz)', fontsize=12)
        self.ax.set_ylabel('RT60 (seconds)', fontsize=12)
        self.ax.set_title('Reverberation Time vs Frequency', fontsize=14, fontweight='bold')
        self.ax.grid(True, alpha=0.3)
        
        # Set logarithmic scale for frequency axis
        self.ax.set_xscale('log')
        self.ax.set_xlim(100, 5000)
        self.ax.set_ylim(0, 1.5)
        
        # Set frequency ticks
        self.ax.set_xticks(self.frequencies)
        self.ax.set_xticklabels([str(f) for f in self.frequencies])
        
        # Initialize empty plot lines
        self.optimum_line = None
        self.optimum_fill = None
        self.current_line = None
        
        # Set background color
        self.ax.set_facecolor('#fafafa')
        self.figure.patch.set_facecolor('white')
        
        # Tight layout
        self.figure.tight_layout()
        
        # Draw the canvas
        self.canvas.draw()
    
    def update_optimum_rt60(self, volume: float):
        """Update the optimum RT60 curve based on room volume"""
        self.room_volume = volume
        
        if volume <= 0:
            self.optimum_rt60_values = {}
            return
        
        # Get optimum RT60 values for this volume
        self.optimum_rt60_values = self.optimum_loader.get_optimum_rt60_for_volume(volume)
        
        # Update the status
        self.status_label.setText(f"Room Volume: {volume:,.0f} cf")
        
        # Redraw the plot
        self.update_plot()
    
    def update_current_rt60(self, rt60_values: Dict[int, float]):
        """Update the current RT60 values from calculations"""
        self.current_rt60_values = rt60_values.copy()
        self.update_plot()
    
    def update_plot(self):
        """Update the plot with current data"""
        # Clear previous plots
        if self.optimum_line:
            self.optimum_line.remove()
        if self.optimum_fill:
            self.optimum_fill.remove()
        if self.current_line:
            self.current_line.remove()
        
        # Plot optimum RT60 range (blue area)
        if self.optimum_rt60_values:
            optimum_values = [self.optimum_rt60_values.get(f, 0) for f in self.frequencies]
            
            # Create a range around the optimum values (±10%)
            optimum_upper = [v * 1.1 for v in optimum_values]
            optimum_lower = [v * 0.9 for v in optimum_values]
            
            # Plot the optimum range as a filled area
            self.optimum_fill = self.ax.fill_between(
                self.frequencies, optimum_lower, optimum_upper,
                alpha=0.3, color='#4472C4', label='Design Criteria'
            )
            
            # Plot the optimum line
            self.optimum_line, = self.ax.plot(
                self.frequencies, optimum_values,
                color='#4472C4', linewidth=2, marker='o', markersize=4,
                label='Optimum RT60'
            )
        
        # Plot current RT60 values (red line)
        if self.current_rt60_values:
            current_values = [self.current_rt60_values.get(f, 0) for f in self.frequencies]
            
            self.current_line, = self.ax.plot(
                self.frequencies, current_values,
                color='#C55A5A', linewidth=3, marker='s', markersize=6,
                label='RT60 w/ Treatment'
            )
        
        # Update legend
        self.ax.legend(loc='upper right', framealpha=0.9)
        
        # Adjust y-axis limits based on data
        all_values = []
        if self.optimum_rt60_values:
            all_values.extend(self.optimum_rt60_values.values())
        if self.current_rt60_values:
            all_values.extend(self.current_rt60_values.values())
        
        if all_values:
            min_val = min(all_values)
            max_val = max(all_values)
            margin = (max_val - min_val) * 0.2
            self.ax.set_ylim(max(0, min_val - margin), max_val + margin)
        
        # Redraw
        self.canvas.draw()
    
    def clear_current_rt60(self):
        """Clear the current RT60 data"""
        self.current_rt60_values = {}
        self.update_plot()
    
    def set_volume_and_update(self, volume: float):
        """Set room volume and update optimum curve"""
        self.update_optimum_rt60(volume)
    
    def get_current_status(self) -> str:
        """Get current status for display"""
        if not self.current_rt60_values:
            return "No RT60 data - select materials to calculate"
        
        if not self.optimum_rt60_values:
            return "No optimum data - set room volume"
        
        # Calculate average RT60 values
        avg_current = sum(self.current_rt60_values.values()) / len(self.current_rt60_values)
        avg_optimum = sum(self.optimum_rt60_values.values()) / len(self.optimum_rt60_values)
        
        # Check compliance
        tolerance = 0.1  # ±0.1 seconds tolerance
        meets_target = abs(avg_current - avg_optimum) <= tolerance
        
        status = "✅ MEETS TARGET" if meets_target else "❌ NEEDS ADJUSTMENT"
        return f"Average RT60: {avg_current:.2f}s | Target: {avg_optimum:.2f}s | {status}"
    
    def export_plot_data(self) -> Dict:
        """Export plot data for reports"""
        return {
            'frequencies': self.frequencies,
            'optimum_rt60': self.optimum_rt60_values,
            'current_rt60': self.current_rt60_values,
            'room_volume': self.room_volume,
            'status': self.get_current_status()
        }
    
    def save_plot_image(self, filename: str):
        """Save the current plot as an image"""
        try:
            self.figure.savefig(filename, dpi=300, bbox_inches='tight')
            return True
        except Exception as e:
            print(f"Error saving plot: {e}")
            return False


class RT60PlotContainer(QWidget):
    """Container widget with plot and materials summary"""
    
    # Signals
    materials_changed = Signal()  # Emitted when doors/windows change requiring RT60 recalculation
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.init_ui()
    
    def init_ui(self):
        """Initialize container UI"""
        layout = QVBoxLayout()
        
        # Create main splitter for plot and materials summary
        from PySide6.QtWidgets import QSplitter
        main_splitter = QSplitter(Qt.Orientation.Vertical)
        
        # Top section: RT60 Plot with controls
        plot_section = QWidget()
        plot_layout = QVBoxLayout()
        
        # Create the plot widget
        self.plot_widget = RT60PlotWidget()
        plot_layout.addWidget(self.plot_widget)
        
        # Control panel
        controls_layout = QHBoxLayout()
        
        # Volume display
        self.volume_label = QLabel("Volume: Not set")
        self.volume_label.setStyleSheet("font-weight: bold;")
        controls_layout.addWidget(self.volume_label)
        
        controls_layout.addStretch()
        
        # Status display
        self.status_display = QLabel("Ready")
        self.status_display.setStyleSheet("color: #2c3e50;")
        controls_layout.addWidget(self.status_display)
        
        plot_layout.addLayout(controls_layout)
        plot_section.setLayout(plot_layout)
        
        main_splitter.addWidget(plot_section)
        
        # Bottom section: Materials Summary
        try:
            from .materials_summary_widget import MaterialsSummaryWidget
            self.materials_summary = MaterialsSummaryWidget()
            self.materials_summary.doors_windows_changed.connect(self.on_materials_changed)
            main_splitter.addWidget(self.materials_summary)
        except ImportError as e:
            try:
                # Try alternative import for testing
                import sys
                import os
                current_dir = os.path.dirname(__file__)
                if current_dir not in sys.path:
                    sys.path.insert(0, current_dir)
                from materials_summary_widget import MaterialsSummaryWidget
                self.materials_summary = MaterialsSummaryWidget()
                self.materials_summary.doors_windows_changed.connect(self.on_materials_changed)
                main_splitter.addWidget(self.materials_summary)
            except ImportError:
                print(f"Warning: Could not import MaterialsSummaryWidget: {e}")
                # Create placeholder widget
                placeholder = QLabel("Materials Summary Widget not available")
                placeholder.setAlignment(Qt.AlignmentFlag.AlignCenter)
                placeholder.setStyleSheet("color: #7f8c8d; font-style: italic;")
                main_splitter.addWidget(placeholder)
                self.materials_summary = None
        
        # Set splitter proportions (70% plot, 30% materials summary)
        main_splitter.setSizes([490, 210]) 
        
        layout.addWidget(main_splitter)
        self.setLayout(layout)
    
    def update_volume(self, volume: float):
        """Update room volume"""
        self.plot_widget.set_volume_and_update(volume)
        self.volume_label.setText(f"Volume: {volume:,.0f} cf")
        self.update_status()
    
    def update_rt60_data(self, rt60_values: Dict[int, float]):
        """Update RT60 calculation data"""
        self.plot_widget.update_current_rt60(rt60_values)
        self.update_status()
    
    def update_materials_data(self, ceiling_materials: List[str], wall_materials: List[str], 
                            floor_materials: List[str], areas: Dict[str, float]):
        """Update materials summary with current material selections"""
        if self.materials_summary:
            self.materials_summary.update_materials_data(
                ceiling_materials, wall_materials, floor_materials, areas
            )
            
    def update_materials_data_detailed(self, ceiling_materials: List[str], wall_materials: List[str], 
                                     floor_materials: List[str], areas: Dict[str, float],
                                     ceiling_materials_data: List[Dict], wall_materials_data: List[Dict],
                                     floor_materials_data: List[Dict]):
        """Update materials summary with detailed material data including square footages"""
        if self.materials_summary:
            self.materials_summary.update_materials_data(
                ceiling_materials, wall_materials, floor_materials, areas,
                ceiling_materials_data, wall_materials_data, floor_materials_data
            )
    
    def get_doors_windows_data(self) -> List[Dict]:
        """Get doors/windows data from materials summary"""
        if self.materials_summary:
            return self.materials_summary.get_doors_windows_data()
        return []
    
    def on_materials_changed(self):
        """Handle materials summary changes - emit signal for RT60 recalculation"""
        # This will be connected to the parent dialog to trigger RT60 recalculation
        self.materials_changed.emit()
    
    def update_status(self):
        """Update status display"""
        status = self.plot_widget.get_current_status()
        self.status_display.setText(status)
    
    def clear_rt60_data(self):
        """Clear RT60 data"""
        self.plot_widget.clear_current_rt60()
        if self.materials_summary:
            self.materials_summary.clear_all_data()
        self.update_status()