"""
Path Element Card - Clickable card representing one element in an HVAC path

This widget displays a single element (source, segment, component, receiver) 
in the path analysis panel with noise levels and attenuation values.
"""

from PySide6.QtWidgets import (
    QFrame, QVBoxLayout, QHBoxLayout, QLabel, QSizePolicy
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont, QColor


class PathElementCard(QFrame):
    """Clickable card representing one element in the HVAC path"""
    
    # Signals for interaction
    hovered = Signal(object, str)  # element_id (can be int or None), element_type
    unhovered = Signal()
    clicked = Signal(object, str)  # element_id, element_type
    edit_requested = Signal(object, str)  # element_id, element_type (double-click)
    
    def __init__(
        self, 
        element_type: str,
        name: str,
        noise_level: float = None,
        attenuation: float = None,
        nc_rating: int = None,
        element_id: object = None,
        extra_info: dict = None,
        parent=None
    ):
        super().__init__(parent)
        self.element_id = element_id
        self.element_type = element_type
        self.name = name
        self.noise_level = noise_level
        self.attenuation = attenuation
        self.nc_rating = nc_rating
        self.extra_info = extra_info or {}
        
        self._is_highlighted = False
        self._is_selected = False
        
        self._init_ui()
        self._apply_style()
        
    def _init_ui(self):
        """Initialize the card UI"""
        self.setFrameStyle(QFrame.Box | QFrame.Raised)
        self.setCursor(Qt.PointingHandCursor)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Minimum)
        self.setMinimumHeight(60)
        
        layout = QVBoxLayout()
        layout.setContentsMargins(10, 8, 10, 8)
        layout.setSpacing(4)
        
        # Header row with icon and name
        header_layout = QHBoxLayout()
        header_layout.setSpacing(8)
        
        # Icon
        icon_label = QLabel(self._get_icon())
        icon_label.setFont(QFont("Segoe UI Emoji", 14))
        header_layout.addWidget(icon_label)
        
        # Name (bold)
        self.name_label = QLabel(self.name)
        self.name_label.setFont(QFont("Arial", 10, QFont.Bold))
        self.name_label.setWordWrap(True)
        header_layout.addWidget(self.name_label, 1)
        
        layout.addLayout(header_layout)
        
        # Details section
        details_layout = QVBoxLayout()
        details_layout.setContentsMargins(28, 0, 0, 0)  # Indent under icon
        details_layout.setSpacing(2)
        
        # Extra info (dimensions, length, etc.)
        if self.extra_info:
            info_parts = []
            if 'dimensions' in self.extra_info:
                info_parts.append(self.extra_info['dimensions'])
            if 'length' in self.extra_info:
                info_parts.append(f"{self.extra_info['length']:.1f} ft")
            if 'lining' in self.extra_info and self.extra_info['lining']:
                info_parts.append("Lined")
            if 'shape' in self.extra_info:
                info_parts.append(self.extra_info['shape'])
            
            if info_parts:
                info_label = QLabel(" • ".join(info_parts))
                info_label.setStyleSheet("color: #666; font-size: 9px;")
                details_layout.addWidget(info_label)
        
        # Noise level
        if self.noise_level is not None:
            noise_text = f"Noise: {self.noise_level:.1f} dB(A)"
            if self.element_type == 'source':
                noise_text = f"PWL: {self.noise_level:.1f} dB(A)"
            elif self.element_type == 'receiver':
                noise_text = f"Terminal: {self.noise_level:.1f} dB(A)"
            
            noise_label = QLabel(noise_text)
            noise_label.setStyleSheet("color: #333;")
            details_layout.addWidget(noise_label)
        
        # Attenuation (for segments/components)
        if self.attenuation is not None:
            att_color = "#2196F3" if self.attenuation < 0 else "#FF9800"
            att_label = QLabel(f"Attenuation: {self.attenuation:+.1f} dB")
            att_label.setStyleSheet(f"color: {att_color}; font-weight: bold;")
            details_layout.addWidget(att_label)
        
        # NC Rating (for receiver)
        if self.nc_rating is not None:
            nc_color = self._get_nc_color()
            nc_label = QLabel(f"NC-{self.nc_rating}")
            nc_label.setFont(QFont("Arial", 11, QFont.Bold))
            nc_label.setStyleSheet(f"color: {nc_color};")
            details_layout.addWidget(nc_label)
            
            # Add pass/fail indicator if target is available
            target_nc = self.extra_info.get('target_nc')
            if target_nc is not None:
                if self.nc_rating <= target_nc:
                    status = f"✅ PASS (Target: NC-{target_nc})"
                    status_color = "#4CAF50"
                else:
                    status = f"❌ FAIL (Target: NC-{target_nc})"
                    status_color = "#F44336"
                status_label = QLabel(status)
                status_label.setStyleSheet(f"color: {status_color}; font-weight: bold;")
                details_layout.addWidget(status_label)
        
        layout.addLayout(details_layout)
        self.setLayout(layout)
    
    def _get_icon(self) -> str:
        """Get emoji icon for element type"""
        icons = {
            'source': '🔊',
            'ahu': '🔊',
            'fan': '🔊',
            'mechanical_unit': '🔊',
            'segment': '━━',
            'duct': '━━',
            'elbow': '↪️',
            'tee': '⊥',
            'branch': '⊥',
            'silencer': '🔇',
            'diffuser': '💨',
            'grille': '💨',
            'terminal': '💨',
            'receiver': '🏠',
            'space': '🏠',
            'damper': '▬',
            'flex': '〰️',
            'takeoff': '↗️',
        }
        return icons.get(self.element_type.lower(), '•')
    
    def _get_nc_color(self) -> str:
        """Get color based on NC rating"""
        if self.nc_rating is None:
            return "#333"
        if self.nc_rating <= 25:
            return "#4CAF50"  # Green - excellent
        elif self.nc_rating <= 35:
            return "#8BC34A"  # Light green - good
        elif self.nc_rating <= 40:
            return "#FFC107"  # Yellow - acceptable
        elif self.nc_rating <= 45:
            return "#FF9800"  # Orange - marginal
        else:
            return "#F44336"  # Red - fail
    
    def _apply_style(self):
        """Apply visual style based on state"""
        if self._is_selected:
            bg_color = "#bbdefb"
            border_color = "#1976D2"
            border_width = 3
        elif self._is_highlighted:
            bg_color = "#e3f2fd"
            border_color = "#2196F3"
            border_width = 2
        else:
            bg_color = "#ffffff"
            border_color = "#ddd"
            border_width = 1
        
        # Special colors for different element types
        if self.element_type in ('source', 'ahu', 'fan', 'mechanical_unit'):
            if not self._is_highlighted and not self._is_selected:
                bg_color = "#fff3e0"  # Light orange
        elif self.element_type in ('receiver', 'space'):
            if not self._is_highlighted and not self._is_selected:
                bg_color = "#e8f5e9"  # Light green
        
        self.setStyleSheet(f"""
            PathElementCard {{
                background-color: {bg_color};
                border: {border_width}px solid {border_color};
                border-radius: 6px;
                color: #333;
            }}
            PathElementCard QLabel {{
                color: #333;
                background-color: transparent;
            }}
        """)
    
    def set_highlighted(self, highlighted: bool):
        """Set highlight state (for hover effects)"""
        self._is_highlighted = highlighted
        self._apply_style()
    
    def set_selected(self, selected: bool):
        """Set selected state"""
        self._is_selected = selected
        self._apply_style()
    
    def enterEvent(self, event):
        """Handle mouse enter"""
        self._is_highlighted = True
        self._apply_style()
        self.hovered.emit(self.element_id, self.element_type)
        super().enterEvent(event)
    
    def leaveEvent(self, event):
        """Handle mouse leave"""
        self._is_highlighted = False
        self._apply_style()
        self.unhovered.emit()
        super().leaveEvent(event)
    
    def mousePressEvent(self, event):
        """Handle mouse click"""
        if event.button() == Qt.LeftButton:
            self.clicked.emit(self.element_id, self.element_type)
        super().mousePressEvent(event)
    
    def mouseDoubleClickEvent(self, event):
        """Handle double-click to edit"""
        if event.button() == Qt.LeftButton:
            self.edit_requested.emit(self.element_id, self.element_type)
        super().mouseDoubleClickEvent(event)


class PathArrow(QFrame):
    """Simple arrow widget to connect path elements"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedHeight(24)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        
        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        
        arrow_label = QLabel("│\n▼")
        arrow_label.setAlignment(Qt.AlignCenter)
        arrow_label.setStyleSheet("color: #666; font-size: 10px;")
        layout.addWidget(arrow_label)
        
        self.setLayout(layout)


class PathResultsSummary(QFrame):
    """Summary widget showing overall path results"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFrameStyle(QFrame.Box | QFrame.Sunken)
        self.setStyleSheet("""
            PathResultsSummary {
                background-color: #f5f5f5;
                border: 1px solid #ddd;
                border-radius: 4px;
                color: #333;
            }
            PathResultsSummary QLabel {
                color: #333;
                background-color: transparent;
            }
        """)
        
        self._init_ui()
    
    def _init_ui(self):
        layout = QVBoxLayout()
        layout.setContentsMargins(10, 8, 10, 8)
        layout.setSpacing(4)
        
        # Title
        title = QLabel("SUMMARY")
        title.setFont(QFont("Arial", 9, QFont.Bold))
        title.setStyleSheet("color: #666;")
        layout.addWidget(title)
        
        # Placeholder labels
        self.source_label = QLabel("Source: --")
        self.terminal_label = QLabel("Terminal: --")
        self.attenuation_label = QLabel("Total Attenuation: --")
        self.nc_label = QLabel("NC Rating: --")
        self.status_label = QLabel("")
        
        for label in [self.source_label, self.terminal_label, 
                      self.attenuation_label, self.nc_label]:
            label.setStyleSheet("color: #333;")
            layout.addWidget(label)
        
        self.status_label.setFont(QFont("Arial", 10, QFont.Bold))
        layout.addWidget(self.status_label)
        
        self.setLayout(layout)
    
    def update_results(self, results: dict):
        """Update summary with calculation results"""
        if not results:
            self.source_label.setText("Source: --")
            self.terminal_label.setText("Terminal: --")
            self.attenuation_label.setText("Total Attenuation: --")
            self.nc_label.setText("NC Rating: --")
            self.status_label.setText("")
            return
        
        source_noise = results.get('source_noise', 0)
        terminal_noise = results.get('terminal_noise', 0)
        total_attenuation = results.get('total_attenuation', 0)
        nc_rating = results.get('nc_rating', 0)
        target_nc = results.get('target_nc')
        
        self.source_label.setText(f"Source: {source_noise:.1f} dB(A)")
        self.terminal_label.setText(f"Terminal: {terminal_noise:.1f} dB(A)")
        self.attenuation_label.setText(f"Total Attenuation: {total_attenuation:+.1f} dB")
        self.nc_label.setText(f"NC Rating: NC-{nc_rating:.0f}")
        
        if target_nc is not None:
            if nc_rating <= target_nc:
                self.status_label.setText(f"✅ PASS (Target: NC-{target_nc})")
                self.status_label.setStyleSheet("color: #4CAF50; font-weight: bold;")
            else:
                self.status_label.setText(f"❌ FAIL (Target: NC-{target_nc})")
                self.status_label.setStyleSheet("color: #F44336; font-weight: bold;")
        else:
            self.status_label.setText("")
