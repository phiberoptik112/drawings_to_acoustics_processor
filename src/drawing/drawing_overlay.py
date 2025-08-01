"""
Drawing Overlay - Transparent overlay for drawing tools on top of PDF viewer
"""

from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel
from PySide6.QtCore import Qt, QPoint, Signal, QRect
from PySide6.QtGui import QPainter, QPen, QBrush, QColor, QFont
from drawing.drawing_tools import DrawingToolManager, ToolType
from drawing.scale_manager import ScaleManager


class DrawingOverlay(QWidget):
    """Transparent overlay widget for drawing on top of PDF"""
    
    # Signals
    element_created = Signal(dict)  # New drawing element created
    coordinates_clicked = Signal(float, float)  # Raw coordinates clicked
    measurement_taken = Signal(float, str)  # Measurement in real units
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        # Make overlay transparent
        self.setAttribute(Qt.WA_TransparentForMouseEvents, False)
        self.setStyleSheet("background-color: transparent;")
        
        # Initialize managers
        self.tool_manager = DrawingToolManager()
        self.scale_manager = ScaleManager()
        
        # Drawing elements storage
        self.rectangles = []  # Room boundaries
        self.components = []  # HVAC components
        self.segments = []    # Duct segments
        self.measurements = []  # Measurement lines
        
        # UI state
        self.show_measurements = True
        self.show_grid = False
        
        # Connect signals
        self.tool_manager.element_created.connect(self.handle_element_created)
        
    def set_scale_manager(self, scale_manager):
        """Set the scale manager for coordinate conversion"""
        self.scale_manager = scale_manager
        
    def set_tool(self, tool_type):
        """Set the active drawing tool"""
        self.tool_manager.set_tool(tool_type)
        
    def set_component_type(self, component_type):
        """Set component type for component tool"""
        self.tool_manager.set_component_type(component_type)
        
    def mousePressEvent(self, event):
        """Handle mouse press events"""
        if event.button() == Qt.LeftButton:
            point = QPoint(event.x(), event.y())
            
            # Emit raw coordinates
            self.coordinates_clicked.emit(event.x(), event.y())
            
            # Start tool operation
            self.tool_manager.start_tool(point)
            self.update()
            
    def mouseMoveEvent(self, event):
        """Handle mouse move events"""
        if event.buttons() & Qt.LeftButton:
            point = QPoint(event.x(), event.y())
            self.tool_manager.update_tool(point)
            self.update()
            
    def mouseReleaseEvent(self, event):
        """Handle mouse release events"""
        if event.button() == Qt.LeftButton:
            point = QPoint(event.x(), event.y())
            self.tool_manager.finish_tool(point)
            self.update()
            
    def keyPressEvent(self, event):
        """Handle key press events"""
        if event.key() == Qt.Key_Escape:
            self.tool_manager.cancel_tool()
            self.update()
            
    def handle_element_created(self, element_data):
        """Handle new drawing element creation"""
        element_type = element_data.get('type')
        
        if element_type == 'rectangle':
            # Add real-world calculations
            width_real = self.scale_manager.pixels_to_real(element_data['width'])
            height_real = self.scale_manager.pixels_to_real(element_data['height'])
            area_real = width_real * height_real
            
            element_data.update({
                'width_real': width_real,
                'height_real': height_real,
                'area_real': area_real,
                'area_formatted': self.scale_manager.format_area(area_real)
            })
            
            self.rectangles.append(element_data)
            
        elif element_type == 'component':
            self.components.append(element_data)
            
        elif element_type == 'segment':
            # Add real-world length calculation
            length_real = self.scale_manager.pixels_to_real(element_data['length_pixels'])
            element_data.update({
                'length_real': length_real,
                'length_formatted': self.scale_manager.format_distance(length_real)
            })
            
            self.segments.append(element_data)
            
        elif element_type == 'measurement':
            # Add real-world measurement
            length_real = self.scale_manager.pixels_to_real(element_data['length_pixels'])
            element_data.update({
                'length_real': length_real,
                'length_formatted': self.scale_manager.format_distance(length_real)
            })
            
            self.measurements.append(element_data)
            self.measurement_taken.emit(length_real, self.scale_manager.format_distance(length_real))
            
        # Emit the enhanced element data
        self.element_created.emit(element_data)
        self.update()
        
    def paintEvent(self, event):
        """Paint the overlay elements"""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        try:
            # Draw existing elements
            self.draw_rectangles(painter)
            self.draw_components(painter)
            self.draw_segments(painter)
            
            if self.show_measurements:
                self.draw_measurements(painter)
                
            if self.show_grid:
                self.draw_grid(painter)
                
            # Draw current tool preview
            current_tool = self.tool_manager.get_current_tool()
            if current_tool and current_tool.active:
                current_tool.draw_preview(painter)
        finally:
            painter.end()
            
    def draw_rectangles(self, painter):
        """Draw room boundary rectangles"""
        pen = QPen(QColor(0, 120, 215), 2, Qt.SolidLine)
        brush = QBrush(QColor(0, 120, 215, 30))
        
        painter.setPen(pen)
        painter.setBrush(brush)
        
        for rect_data in self.rectangles:
            bounds = rect_data['bounds']
            
            # Handle both QRect objects and dictionary representations
            if isinstance(bounds, dict):
                # Convert dictionary back to QRect
                rect = QRect(bounds['x'], bounds['y'], bounds['width'], bounds['height'])
            else:
                # Already a QRect object
                rect = bounds
                
            painter.drawRect(rect)
            
            # Draw area label
            center_x = rect.center().x()
            center_y = rect.center().y()
            
            area_text = rect_data.get('area_formatted', f"{rect_data.get('area_real', 0):.0f} sf")
            
            painter.setPen(QPen(Qt.black))
            painter.setFont(QFont("Arial", 10, QFont.Bold))
            painter.drawText(center_x - 30, center_y, area_text)
            
    def draw_components(self, painter):
        """Draw HVAC components"""
        pen = QPen(QColor(220, 100, 50), 2, Qt.SolidLine)
        brush = QBrush(QColor(220, 100, 50, 100))
        
        painter.setPen(pen)
        painter.setBrush(brush)
        
        for comp_data in self.components:
            x, y = comp_data['x'], comp_data['y']
            comp_type = comp_data['component_type']
            size = 24
            
            # Draw component shape
            if comp_type in ['ahu', 'coil']:
                # Rectangle for equipment
                painter.drawRect(x - size//2, y - size//2, size, size)
            else:
                # Circle for terminals
                painter.drawEllipse(x - size//2, y - size//2, size, size)
                
            # Draw label
            painter.setPen(QPen(Qt.black))
            painter.setFont(QFont("Arial", 8, QFont.Bold))
            painter.drawText(x - 15, y + size//2 + 15, comp_type.upper())
            
    def draw_segments(self, painter):
        """Draw duct segments"""
        pen = QPen(QColor(50, 150, 50), 3, Qt.SolidLine)
        painter.setPen(pen)
        
        for seg_data in self.segments:
            start_x, start_y = seg_data['start_x'], seg_data['start_y']
            end_x, end_y = seg_data['end_x'], seg_data['end_y']
            
            painter.drawLine(start_x, start_y, end_x, end_y)
            
            # Draw length label
            mid_x = (start_x + end_x) // 2
            mid_y = (start_y + end_y) // 2
            
            length_text = seg_data.get('length_formatted', f"{seg_data.get('length_real', 0):.1f} ft")
            
            painter.setPen(QPen(Qt.darkGreen))
            painter.setFont(QFont("Arial", 9))
            painter.drawText(mid_x + 5, mid_y - 5, length_text)
            
    def draw_measurements(self, painter):
        """Draw measurement lines"""
        pen = QPen(QColor(255, 0, 0), 2, Qt.DashLine)
        painter.setPen(pen)
        
        for meas_data in self.measurements:
            start_x, start_y = meas_data['start_x'], meas_data['start_y']
            end_x, end_y = meas_data['end_x'], meas_data['end_y']
            
            painter.drawLine(start_x, start_y, end_x, end_y)
            
            # Draw measurement points
            painter.setBrush(QBrush(QColor(255, 0, 0)))
            painter.drawEllipse(start_x - 3, start_y - 3, 6, 6)
            painter.drawEllipse(end_x - 3, end_y - 3, 6, 6)
            
            # Draw measurement label
            mid_x = (start_x + end_x) // 2
            mid_y = (start_y + end_y) // 2
            
            length_text = meas_data.get('length_formatted', f"{meas_data.get('length_real', 0):.1f} ft")
            
            painter.setPen(QPen(Qt.red))
            painter.setFont(QFont("Arial", 9, QFont.Bold))
            painter.drawText(mid_x + 5, mid_y - 10, f"📏 {length_text}")
            
    def draw_grid(self, painter):
        """Draw grid overlay for alignment"""
        if not self.show_grid:
            return
            
        pen = QPen(QColor(200, 200, 200, 100), 1, Qt.DotLine)
        painter.setPen(pen)
        
        # Draw grid at 50 pixel intervals
        grid_size = 50
        width = self.width()
        height = self.height()
        
        # Vertical lines
        for x in range(0, width, grid_size):
            painter.drawLine(x, 0, x, height)
            
        # Horizontal lines
        for y in range(0, height, grid_size):
            painter.drawLine(0, y, width, y)
            
    def clear_all_elements(self):
        """Clear all drawn elements"""
        self.rectangles.clear()
        self.components.clear()
        self.segments.clear()
        self.measurements.clear()
        self.update()
        
    def clear_measurements(self):
        """Clear only measurement lines"""
        self.measurements.clear()
        self.update()
        
    def toggle_measurements(self):
        """Toggle measurement display"""
        self.show_measurements = not self.show_measurements
        self.update()
        
    def toggle_grid(self):
        """Toggle grid display"""
        self.show_grid = not self.show_grid
        self.update()
        
    def get_elements_summary(self):
        """Get summary of all drawn elements"""
        return {
            'rectangles': len(self.rectangles),
            'components': len(self.components),
            'segments': len(self.segments),
            'measurements': len(self.measurements),
            'total_area': sum(rect.get('area_real', 0) for rect in self.rectangles),
            'total_duct_length': sum(seg.get('length_real', 0) for seg in self.segments)
        }
        
    def get_elements_data(self):
        """Get all element data for saving"""
        return {
            'rectangles': self.rectangles,
            'components': self.components,
            'segments': self.segments,
            'measurements': self.measurements
        }
        
    def load_elements_data(self, data):
        """Load element data from saved state"""
        # Load rectangles and reconstruct QRect objects
        rectangles = data.get('rectangles', [])
        for rect_data in rectangles:
            bounds = rect_data.get('bounds')
            if isinstance(bounds, dict):
                # Reconstruct QRect from dictionary
                rect_data['bounds'] = QRect(bounds['x'], bounds['y'], bounds['width'], bounds['height'])
        
        self.rectangles = rectangles
        self.components = data.get('components', [])
        self.segments = data.get('segments', [])
        self.measurements = data.get('measurements', [])
        self.update()