"""
Material Graph Overlay Widget - Interactive frequency response visualization with material ranking
"""

from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                             QListWidget, QListWidgetItem, QSplitter, 
                             QGroupBox, QPushButton, QComboBox, QLineEdit,
                             QSpinBox, QCheckBox, QProgressBar, QTextEdit)
from PySide6.QtCore import Qt, Signal, QTimer, QThread
from PySide6.QtGui import QPainter, QPen, QBrush, QColor, QFont, QCursor
import math
from typing import Dict, List, Optional, Any

try:
    from ...data.material_search import MaterialSearchEngine
except ImportError:
    import sys
    import os
    current_dir = os.path.dirname(__file__)
    src_dir = os.path.dirname(os.path.dirname(current_dir))
    sys.path.insert(0, src_dir)
    from data.material_search import MaterialSearchEngine


class FrequencyResponseWidget(QWidget):
    """Interactive frequency response graph widget"""
    
    frequency_selected = Signal(int)  # Emitted when user selects a frequency
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumSize(400, 200)
        self.setMaximumHeight(250)
        
        # Data
        self.frequencies = [125, 250, 500, 1000, 2000, 4000]
        self.frequency_labels = ['125', '250', '500', '1K', '2K', '4K']
        self.current_rt60 = {}
        self.target_rt60 = {}
        self.selected_frequency = 1000
        self.hover_frequency = None
        
        # Visual settings
        self.margin = 40
        self.grid_color = QColor(200, 200, 200)
        self.current_color = QColor(255, 100, 100)  # Red
        self.target_color = QColor(100, 255, 100)   # Green
        self.problem_color = QColor(255, 200, 100)  # Orange
        self.selected_color = QColor(100, 100, 255) # Blue
        
        self.setMouseTracking(True)
        
    def set_rt60_data(self, current_rt60: Dict[int, float], target_rt60: float = 0.6):
        """Set RT60 data for visualization"""
        self.current_rt60 = current_rt60
        self.target_rt60 = {freq: target_rt60 for freq in self.frequencies}
        self.update()
        
    def set_selected_frequency(self, frequency: int):
        """Set the currently selected frequency"""
        if frequency in self.frequencies:
            self.selected_frequency = frequency
            self.update()
            
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        # Calculate drawing area
        width = self.width() - 2 * self.margin
        height = self.height() - 2 * self.margin
        
        if width <= 0 or height <= 0:
            return
            
        # Draw background
        painter.fillRect(self.rect(), QColor(250, 250, 250))
        
        # Draw grid
        self._draw_grid(painter, width, height)
        
        # Draw RT60 curves
        self._draw_rt60_curves(painter, width, height)
        
        # Draw frequency markers
        self._draw_frequency_markers(painter, width, height)
        
        # Draw legend
        self._draw_legend(painter)
        
    def _draw_grid(self, painter, width, height):
        """Draw grid lines"""
        painter.setPen(QPen(self.grid_color, 1))
        
        # Vertical lines (frequencies)
        for i, freq in enumerate(self.frequencies):
            x = self.margin + (i * width / (len(self.frequencies) - 1))
            painter.drawLine(x, self.margin, x, self.margin + height)
            
        # Horizontal lines (RT60 values)
        max_rt60 = 2.0
        for rt60 in [0.5, 1.0, 1.5, 2.0]:
            y = self.margin + height - (rt60 / max_rt60 * height)
            painter.drawLine(self.margin, y, self.margin + width, y)
            
    def _draw_rt60_curves(self, painter, width, height):
        """Draw current and target RT60 curves"""
        if not self.current_rt60:
            return
            
        max_rt60 = 2.0
        
        # Draw target RT60 line
        painter.setPen(QPen(self.target_color, 2, Qt.DashLine))
        target_value = list(self.target_rt60.values())[0] if self.target_rt60 else 0.6
        y_target = self.margin + height - (target_value / max_rt60 * height)
        painter.drawLine(self.margin, y_target, self.margin + width, y_target)
        
        # Draw current RT60 curve
        painter.setPen(QPen(self.current_color, 3))
        points = []
        
        for i, freq in enumerate(self.frequencies):
            x = self.margin + (i * width / (len(self.frequencies) - 1))
            rt60_value = self.current_rt60.get(freq, 0)
            y = self.margin + height - (min(rt60_value, max_rt60) / max_rt60 * height)
            points.append((x, y))
            
        # Draw the curve
        for i in range(len(points) - 1):
            painter.drawLine(points[i][0], points[i][1], points[i+1][0], points[i+1][1])
            
        # Draw data points and highlight problems
        for i, (freq, (x, y)) in enumerate(zip(self.frequencies, points)):
            current_val = self.current_rt60.get(freq, 0)
            target_val = self.target_rt60.get(freq, 0.6)
            
            # Highlight problem frequencies
            if abs(current_val - target_val) > 0.2:
                painter.setBrush(QBrush(self.problem_color))
                painter.setPen(QPen(self.problem_color, 2))
                painter.drawEllipse(x - 6, y - 6, 12, 12)
            
            # Highlight selected frequency
            if freq == self.selected_frequency:
                painter.setBrush(QBrush(self.selected_color))
                painter.setPen(QPen(self.selected_color, 3))
                painter.drawEllipse(x - 8, y - 8, 16, 16)
            else:
                painter.setBrush(QBrush(self.current_color))
                painter.setPen(QPen(self.current_color, 2))
                painter.drawEllipse(x - 4, y - 4, 8, 8)
                
    def _draw_frequency_markers(self, painter, width, height):
        """Draw frequency labels"""
        painter.setPen(QPen(Qt.black, 1))
        font = QFont()
        font.setPointSize(9)
        painter.setFont(font)
        
        for i, label in enumerate(self.frequency_labels):
            x = self.margin + (i * width / (len(self.frequencies) - 1))
            painter.drawText(x - 15, self.margin + height + 20, label)
            
        # Y-axis labels
        max_rt60 = 2.0
        for rt60 in [0.5, 1.0, 1.5, 2.0]:
            y = self.margin + height - (rt60 / max_rt60 * height)
            painter.drawText(5, y + 4, f"{rt60:.1f}s")
            
    def _draw_legend(self, painter):
        """Draw legend"""
        legend_x = self.width() - 120
        legend_y = 10
        
        painter.setPen(QPen(Qt.black, 1))
        font = QFont()
        font.setPointSize(8)
        painter.setFont(font)
        
        # Current RT60
        painter.setPen(QPen(self.current_color, 2))
        painter.drawLine(legend_x, legend_y, legend_x + 20, legend_y)
        painter.setPen(QPen(Qt.black, 1))
        painter.drawText(legend_x + 25, legend_y + 4, "Current")
        
        # Target RT60
        legend_y += 15
        painter.setPen(QPen(self.target_color, 2, Qt.DashLine))
        painter.drawLine(legend_x, legend_y, legend_x + 20, legend_y)
        painter.setPen(QPen(Qt.black, 1))
        painter.drawText(legend_x + 25, legend_y + 4, "Target")
        
        # Problem areas
        legend_y += 15
        painter.setBrush(QBrush(self.problem_color))
        painter.setPen(QPen(self.problem_color, 1))
        painter.drawEllipse(legend_x + 8, legend_y - 4, 8, 8)
        painter.setPen(QPen(Qt.black, 1))
        painter.drawText(legend_x + 25, legend_y + 4, "Problem")
        
    def mousePressEvent(self, event):
        """Handle mouse clicks to select frequency"""
        if event.button() == Qt.LeftButton:
            freq = self._get_frequency_at_position(event.position().x())
            if freq:
                self.selected_frequency = freq
                self.frequency_selected.emit(freq)
                self.update()
                
    def mouseMoveEvent(self, event):
        """Handle mouse movement for hover effects"""
        freq = self._get_frequency_at_position(event.position().x())
        if freq != self.hover_frequency:
            self.hover_frequency = freq
            if freq:
                self.setCursor(QCursor(Qt.PointingHandCursor))
            else:
                self.setCursor(QCursor(Qt.ArrowCursor))
                
    def _get_frequency_at_position(self, x):
        """Get frequency at mouse x position"""
        if x < self.margin or x > self.width() - self.margin:
            return None
            
        width = self.width() - 2 * self.margin
        relative_x = x - self.margin
        
        # Find closest frequency
        freq_spacing = width / (len(self.frequencies) - 1)
        freq_index = round(relative_x / freq_spacing)
        
        if 0 <= freq_index < len(self.frequencies):
            return self.frequencies[freq_index]
        return None


class MaterialListWidget(QListWidget):
    """Custom list widget for materials with frequency-specific data"""
    
    material_selected = Signal(dict)  # Emitted when material is selected
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.materials = []
        self.current_frequency = 1000
        
        self.itemClicked.connect(self._on_item_clicked)
        
    def update_materials(self, materials: List[Dict], frequency: int):
        """Update material list for specific frequency"""
        self.materials = materials
        self.current_frequency = frequency
        self.clear()
        
        for i, material in enumerate(materials[:20]):  # Show top 20
            item = QListWidgetItem()
            
            # Get absorption at current frequency
            freq_str = str(frequency)
            if 'coefficients' in material and freq_str in material['coefficients']:
                absorption = material['coefficients'][freq_str]
            else:
                absorption = material.get('absorption_at_frequency', material.get('absorption_coeff', 0))
                
            # Format item text
            name = material['name'][:40] + '...' if len(material['name']) > 40 else material['name']
            nrc = material.get('nrc', 0)
            item_text = f"{i+1:2d}. {name}\n    α@{frequency}Hz: {absorption:.2f} | NRC: {nrc:.2f}"
            
            item.setText(item_text)
            item.setData(Qt.UserRole, material)
            
            # Color coding based on performance
            if absorption >= 0.8:
                item.setBackground(QColor(200, 255, 200))  # Green - excellent
            elif absorption >= 0.5:
                item.setBackground(QColor(255, 255, 200))  # Yellow - good
            elif absorption >= 0.2:
                item.setBackground(QColor(255, 230, 200))  # Orange - fair
            else:
                item.setBackground(QColor(255, 200, 200))  # Red - poor
                
            self.addItem(item)
            
    def _on_item_clicked(self, item):
        """Handle item selection"""
        material = item.data(Qt.UserRole)
        if material:
            self.material_selected.emit(material)


class MaterialSearchThread(QThread):
    """Background thread for material searching"""
    
    results_ready = Signal(list)
    
    def __init__(self, search_engine, search_type, **kwargs):
        super().__init__()
        self.search_engine = search_engine
        self.search_type = search_type
        self.kwargs = kwargs
        
    def run(self):
        try:
            if self.search_type == 'frequency':
                results = self.search_engine.search_by_frequency_absorption(**self.kwargs)
            elif self.search_type == 'treatment':
                results = self.search_engine.rank_materials_for_treatment_gap(**self.kwargs)
            elif self.search_type == 'text':
                results = self.search_engine.search_materials_by_text(**self.kwargs)
            else:
                results = []
                
            self.results_ready.emit(results)
        except Exception as e:
            print(f"Search error: {e}")
            self.results_ready.emit([])


class MaterialGraphOverlay(QWidget):
    """Main widget combining frequency graph and material search"""
    
    material_selected = Signal(dict)  # Emitted when user selects a material
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.search_engine = MaterialSearchEngine()
        self.current_space_data = {}
        self.search_thread = None
        
        self.init_ui()
        
    def init_ui(self):
        """Initialize user interface"""
        layout = QVBoxLayout()
        
        # Controls
        controls_layout = QHBoxLayout()
        
        controls_layout.addWidget(QLabel("Search:"))
        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText("Search materials...")
        self.search_edit.textChanged.connect(self._on_search_text_changed)
        controls_layout.addWidget(self.search_edit)
        
        controls_layout.addWidget(QLabel("Category:"))
        self.category_combo = QComboBox()
        self.category_combo.addItems(["All", "Ceiling", "Wall", "Floor"])
        self.category_combo.currentTextChanged.connect(self._on_category_changed)
        controls_layout.addWidget(self.category_combo)
        
        self.treatment_mode_cb = QCheckBox("Treatment Mode")
        self.treatment_mode_cb.setToolTip("Find materials to solve RT60 problems")
        self.treatment_mode_cb.toggled.connect(self._on_treatment_mode_toggled)
        controls_layout.addWidget(self.treatment_mode_cb)
        
        controls_layout.addStretch()
        layout.addLayout(controls_layout)
        
        # Main content area
        splitter = QSplitter(Qt.Horizontal)
        
        # Left side - Frequency graph
        left_widget = QWidget()
        left_layout = QVBoxLayout()
        
        left_layout.addWidget(QLabel("Frequency Response Analysis"))
        self.frequency_widget = FrequencyResponseWidget()
        self.frequency_widget.frequency_selected.connect(self._on_frequency_selected)
        left_layout.addWidget(self.frequency_widget)
        
        # Search progress
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        left_layout.addWidget(self.progress_bar)
        
        left_widget.setLayout(left_layout)
        splitter.addWidget(left_widget)
        
        # Right side - Material list
        right_widget = QWidget()
        right_layout = QVBoxLayout()
        
        self.results_label = QLabel("Material Search Results")
        right_layout.addWidget(self.results_label)
        
        self.material_list = MaterialListWidget()
        self.material_list.material_selected.connect(self._on_material_selected)
        right_layout.addWidget(self.material_list)
        
        # Material details
        self.material_details = QTextEdit()
        self.material_details.setMaximumHeight(120)
        self.material_details.setReadOnly(True)
        right_layout.addWidget(self.material_details)
        
        # Action buttons
        button_layout = QHBoxLayout()
        self.apply_btn = QPushButton("Apply Material")
        self.apply_btn.setEnabled(False)
        self.apply_btn.clicked.connect(self._apply_selected_material)
        button_layout.addWidget(self.apply_btn)
        
        self.compare_btn = QPushButton("Compare")
        self.compare_btn.setEnabled(False)
        button_layout.addWidget(self.compare_btn)
        
        button_layout.addStretch()
        right_layout.addLayout(button_layout)
        
        right_widget.setLayout(right_layout)
        splitter.addWidget(right_widget)
        
        # Set splitter proportions
        splitter.setSizes([300, 400])
        layout.addWidget(splitter)
        
        self.setLayout(layout)
        
        # Initialize with default frequency
        self._search_materials_at_frequency(1000)
        
    def set_space_data(self, space_data: Dict):
        """Set current space data for analysis"""
        self.current_space_data = space_data
        
        # Update frequency graph if RT60 data available
        if 'rt60_by_frequency' in space_data:
            target_rt60 = space_data.get('target_rt60', 0.6)
            self.frequency_widget.set_rt60_data(space_data['rt60_by_frequency'], target_rt60)
        
        # Update search if in treatment mode
        if self.treatment_mode_cb.isChecked():
            self._search_treatment_materials()
            
    def _on_frequency_selected(self, frequency):
        """Handle frequency selection from graph"""
        if self.treatment_mode_cb.isChecked():
            self._search_treatment_materials(frequency)
        else:
            self._search_materials_at_frequency(frequency)
            
    def _on_search_text_changed(self):
        """Handle text search changes"""
        if not self.treatment_mode_cb.isChecked():
            text = self.search_edit.text().strip()
            if text:
                self._search_materials_by_text(text)
            else:
                self._search_materials_at_frequency(self.frequency_widget.selected_frequency)
                
    def _on_category_changed(self):
        """Handle category filter changes"""
        if self.treatment_mode_cb.isChecked():
            self._search_treatment_materials()
        else:
            self._search_materials_at_frequency(self.frequency_widget.selected_frequency)
            
    def _on_treatment_mode_toggled(self, enabled):
        """Handle treatment mode toggle"""
        if enabled:
            self._search_treatment_materials()
        else:
            self._search_materials_at_frequency(self.frequency_widget.selected_frequency)
            
    def _on_material_selected(self, material):
        """Handle material selection"""
        self.selected_material = material
        self.apply_btn.setEnabled(True)
        self.compare_btn.setEnabled(True)
        
        # Show material details
        self._show_material_details(material)
        
    def _search_materials_at_frequency(self, frequency):
        """Search materials by frequency absorption"""
        category = self._get_selected_category()
        self._start_search('frequency', frequency=frequency, category=category, limit=50)
        
    def _search_materials_by_text(self, query):
        """Search materials by text"""
        category = self._get_selected_category()
        self._start_search('text', query=query, category=category, limit=50)
        
    def _search_treatment_materials(self, frequency=None):
        """Search materials for treatment purposes"""
        if not self.current_space_data:
            return
            
        if frequency is None:
            frequency = self.frequency_widget.selected_frequency
            
        # Get RT60 data
        rt60_by_freq = self.current_space_data.get('rt60_by_frequency', {})
        current_rt60 = rt60_by_freq.get(frequency, self.current_space_data.get('rt60', 1.0))
        target_rt60 = self.current_space_data.get('target_rt60', 0.6)
        volume = self.current_space_data.get('volume', 1000)
        
        # Estimate available surface area (simplified)
        surface_area = self.current_space_data.get('floor_area', 500)
        
        category = self._get_selected_category()
        
        self._start_search('treatment',
                         current_rt60=current_rt60,
                         target_rt60=target_rt60,
                         frequency=frequency,
                         volume=volume,
                         surface_area=surface_area,
                         category=category,
                         limit=30)
        
    def _start_search(self, search_type, **kwargs):
        """Start background search"""
        if self.search_thread and self.search_thread.isRunning():
            self.search_thread.terminate()
            
        self.progress_bar.setVisible(True)
        self.progress_bar.setRange(0, 0)  # Indeterminate
        
        self.search_thread = MaterialSearchThread(self.search_engine, search_type, **kwargs)
        self.search_thread.results_ready.connect(self._on_search_results)
        self.search_thread.start()
        
    def _on_search_results(self, results):
        """Handle search results"""
        self.progress_bar.setVisible(False)
        
        frequency = self.frequency_widget.selected_frequency
        self.material_list.update_materials(results, frequency)
        
        # Update results label
        category = self._get_selected_category()
        mode = "Treatment" if self.treatment_mode_cb.isChecked() else "Frequency"
        self.results_label.setText(f"{mode} Search Results ({len(results)} materials) - {frequency}Hz")
        
    def _get_selected_category(self):
        """Get selected category filter"""
        category_text = self.category_combo.currentText().lower()
        return category_text if category_text != 'all' else None
        
    def _show_material_details(self, material):
        """Show detailed material information"""
        name = material['name']
        nrc = material.get('nrc', 0)
        category = material.get('category', 'Unknown')
        
        # Frequency response
        details = f"<b>{name}</b><br>"
        details += f"Category: {category.title()}<br>"
        details += f"NRC: {nrc:.2f}<br><br>"
        
        details += "<b>Frequency Response:</b><br>"
        if 'coefficients' in material:
            for freq in [125, 250, 500, 1000, 2000, 4000]:
                coeff = material['coefficients'].get(str(freq), 0)
                details += f"{freq}Hz: {coeff:.2f} "
                if freq == 1000:
                    details += "<br>"
        
        # Treatment effectiveness
        if 'treatment_score' in material:
            score = material['treatment_score']
            details += f"<br><b>Treatment Score:</b> {score:.2f}"
            
        if 'potential_absorption' in material:
            absorption = material['potential_absorption']
            details += f"<br><b>Potential Absorption:</b> {absorption:.1f} sabins"
            
        self.material_details.setHtml(details)
        
    def _apply_selected_material(self):
        """Apply selected material"""
        if hasattr(self, 'selected_material'):
            self.material_selected.emit(self.selected_material)