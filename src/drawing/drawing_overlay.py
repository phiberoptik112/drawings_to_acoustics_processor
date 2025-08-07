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
        self.visible_paths = {}  # Visible HVAC paths {path_id: path_data}
        self.path_element_mapping = {}  # Maps path_id to {components: [], segments: []}
        
        # UI state
        self.show_measurements = True
        self.show_grid = False
        self.path_only_mode = False  # Show only elements belonging to visible paths
        
        # Connect signals
        self.tool_manager.element_created.connect(self.handle_element_created)
        
    def set_scale_manager(self, scale_manager):
        """Set the scale manager for coordinate conversion"""
        self.scale_manager = scale_manager
        
    def set_tool(self, tool_type):
        """Set the active drawing tool"""
        self.tool_manager.set_tool(tool_type)
        
        # If switching to segment tool, update available components
        if tool_type == ToolType.SEGMENT:
            self.update_segment_tool_components()
        
    def set_component_type(self, component_type):
        """Set component type for component tool"""
        self.tool_manager.set_component_type(component_type)
    
    def update_segment_tool_components(self):
        """Update the segment tool with current available components and segments"""
        print(f"DEBUG: Updating segment tool with {len(self.components)} components and {len(self.segments)} segments")
        for i, comp in enumerate(self.components):
            print(f"DEBUG: Component {i}: {comp.get('component_type', 'unknown')} at ({comp.get('x', 0)}, {comp.get('y', 0)})")
        for i, seg in enumerate(self.segments):
            print(f"DEBUG: Segment {i}: from_component={seg.get('from_component') is not None}, to_component={seg.get('to_component') is not None}")
        self.tool_manager.set_available_components(self.components)
        self.tool_manager.set_available_segments(self.segments)
        
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
            print(f"DEBUG: mouseReleaseEvent - pos: ({point.x()}, {point.y()})")
            print(f"DEBUG: mouseReleaseEvent - calling finish_tool")
            self.tool_manager.finish_tool(point)
            print(f"DEBUG: mouseReleaseEvent - calling cancel_tool")
            self.tool_manager.cancel_tool()
            self.update()
            
    def keyPressEvent(self, event):
        """Handle key press events"""
        if event.key() == Qt.Key_Escape:
            self.tool_manager.cancel_tool()
            self.update()
            
    def handle_element_created(self, element_data):
        """Handle new drawing element creation"""
        element_type = element_data.get('type')
        
        print(f"DEBUG: handle_element_created called with type: {element_type}")
        
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
            print(f"DEBUG: Added rectangle, total rectangles: {len(self.rectangles)}")
            
        elif element_type == 'component':
            self.components.append(element_data)
            print(f"DEBUG: Added component, total components: {len(self.components)}")
            # Update segment tool with new component
            self.update_segment_tool_components()
            
        elif element_type == 'segment':
            print(f"DEBUG: Processing segment with from_component={element_data.get('from_component') is not None}, to_component={element_data.get('to_component') is not None}")
            # Add real-world length calculation
            length_real = self.scale_manager.pixels_to_real(element_data['length_pixels'])
            element_data.update({
                'length_real': length_real,
                'length_formatted': self.scale_manager.format_distance(length_real)
            })
            
            self.segments.append(element_data)
            print(f"DEBUG: Added segment, total segments: {len(self.segments)}")
            
            # Update segment tool with new segments
            self.update_segment_tool_components()
            
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
        for rect_data in self.rectangles:
            bounds = rect_data['bounds']
            
            # Handle both QRect objects and dictionary representations
            if isinstance(bounds, dict):
                # Convert dictionary back to QRect
                rect = QRect(bounds['x'], bounds['y'], bounds['width'], bounds['height'])
            else:
                # Already a QRect object
                rect = bounds
            
            # Differentiate between regular rectangles and converted spaces
            is_space = rect_data.get('converted_to_space', False)
            
            if is_space:
                # Green for spaces that are already converted
                pen = QPen(QColor(34, 139, 34), 3, Qt.SolidLine)  # Forest green
                brush = QBrush(QColor(34, 139, 34, 40))
            else:
                # Blue for regular rectangles
                pen = QPen(QColor(0, 120, 215), 2, Qt.SolidLine)
                brush = QBrush(QColor(0, 120, 215, 30))
            
            painter.setPen(pen)
            painter.setBrush(brush)
            painter.drawRect(rect)
            
            # Draw label
            center_x = rect.center().x()
            center_y = rect.center().y()
            
            if is_space:
                # Show space name for converted spaces
                space_name = rect_data.get('space_name', 'Space')
                area_text = rect_data.get('area_formatted', f"{rect_data.get('area_real', 0):.0f} sf")
                
                painter.setPen(QPen(Qt.black))
                painter.setFont(QFont("Arial", 9, QFont.Bold))
                
                # Draw space name above area
                painter.drawText(center_x - 40, center_y - 8, space_name)
                painter.setFont(QFont("Arial", 8))
                painter.drawText(center_x - 30, center_y + 8, area_text)
            else:
                # Show area for regular rectangles
                area_text = rect_data.get('area_formatted', f"{rect_data.get('area_real', 0):.0f} sf")
                
                painter.setPen(QPen(Qt.black))
                painter.setFont(QFont("Arial", 10, QFont.Bold))
                painter.drawText(center_x - 30, center_y, area_text)
            
    def draw_components(self, painter):
        """Draw HVAC components"""
        for comp_data in self.components:
            # Check if this component belongs to a hidden path
            if self.is_component_hidden_by_path(comp_data):
                continue
            
            # In path-only mode, only draw components that belong to visible paths
            if self.path_only_mode and not self.is_component_part_of_visible_path(comp_data):
                print(f"DEBUG: Skipping component {comp_data.get('component_type')} at ({comp_data.get('x')}, {comp_data.get('y')}) - not in visible path (path-only mode)")
                continue
                
            # print(f"DEBUG: Drawing component {comp_data.get('component_type')} at ({comp_data.get('x')}, {comp_data.get('y')})")
            x, y = comp_data['x'], comp_data['y']
            comp_type = comp_data['component_type']
            size = 24
            
            # Draw component shape based on type
            if comp_type in ['ahu', 'coil']:
                # Rectangle for equipment
                pen = QPen(QColor(220, 100, 50), 2, Qt.SolidLine)
                brush = QBrush(QColor(220, 100, 50, 100))
                painter.setPen(pen)
                painter.setBrush(brush)
                painter.drawRect(x - size//2, y - size//2, size, size)
            elif comp_type == 'elbow':
                # L-shaped elbow for direction changes
                pen = QPen(QColor(100, 100, 100), 3, Qt.SolidLine)
                brush = QBrush(QColor(100, 100, 100, 50))
                painter.setPen(pen)
                painter.setBrush(brush)
                
                # Draw L-shape
                half_size = size // 2
                painter.drawLine(x - half_size, y, x + half_size, y)  # Horizontal line
                painter.drawLine(x, y - half_size, x, y + half_size)  # Vertical line
                
                # Draw connection points
                painter.setBrush(QBrush(QColor(255, 255, 0, 150)))
                painter.drawEllipse(x - half_size - 3, y - 3, 6, 6)  # Left connection
                painter.drawEllipse(x - 3, y - half_size - 3, 6, 6)  # Top connection
                painter.drawEllipse(x + half_size - 3, y - 3, 6, 6)  # Right connection
                painter.drawEllipse(x - 3, y + half_size - 3, 6, 6)  # Bottom connection
            elif comp_type == 'branch':
                # T-shaped branch for flow distribution
                pen = QPen(QColor(150, 75, 0), 3, Qt.SolidLine)
                brush = QBrush(QColor(150, 75, 0, 50))
                painter.setPen(pen)
                painter.setBrush(brush)
                
                # Draw T-shape
                half_size = size // 2
                painter.drawLine(x - half_size, y, x + half_size, y)  # Horizontal line (main duct)
                painter.drawLine(x, y - half_size, x, y + half_size)  # Vertical line (branch)
                
                # Draw connection points
                painter.setBrush(QBrush(QColor(255, 255, 0, 150)))
                painter.drawEllipse(x - half_size - 3, y - 3, 6, 6)  # Left connection (main)
                painter.drawEllipse(x + half_size - 3, y - 3, 6, 6)  # Right connection (main)
                painter.drawEllipse(x - 3, y - half_size - 3, 6, 6)  # Top connection (branch)
                painter.drawEllipse(x - 3, y + half_size - 3, 6, 6)  # Bottom connection (branch)
            else:
                # Circle for terminals
                pen = QPen(QColor(220, 100, 50), 2, Qt.SolidLine)
                brush = QBrush(QColor(220, 100, 50, 100))
                painter.setPen(pen)
                painter.setBrush(brush)
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
            # Check if this segment belongs to a hidden path
            if self.is_segment_hidden_by_path(seg_data):
                continue
            
            # In path-only mode, only draw segments that belong to visible paths
            if self.path_only_mode and not self.is_segment_part_of_visible_path(seg_data):
                print(f"DEBUG: Skipping segment from ({seg_data.get('start_x')}, {seg_data.get('start_y')}) to ({seg_data.get('end_x')}, {seg_data.get('end_y')}) - not in visible path (path-only mode)")
                continue
                
            # print(f"DEBUG: Drawing segment from ({seg_data.get('start_x')}, {seg_data.get('start_y')}) to ({seg_data.get('end_x')}, {seg_data.get('end_y')})")
            start_x, start_y = seg_data['start_x'], seg_data['start_y']
            end_x, end_y = seg_data['end_x'], seg_data['end_y']
            
            painter.drawLine(start_x, start_y, end_x, end_y)
            
            # Draw length label
            mid_x = (start_x + end_x) // 2
            mid_y = (start_y + end_y) // 2
            
            length_text = seg_data.get('length_formatted', f"{seg_data.get('length_real', 0):.1f} ft")
            
            painter.setPen(QPen(Qt.black))
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
            
            painter.setPen(QPen(Qt.black))
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
    
    def draw_paths(self, painter):
        """Draw visible HVAC paths"""
        if not self.visible_paths:
            return
            
        for path_id, path_data in self.visible_paths.items():
            self.draw_single_path(painter, path_id, path_data)
    
    def draw_single_path(self, painter, path_id: int, path_data: dict):
        """Draw a single HVAC path with its components and connections"""
        try:
            path_name = path_data.get('name', f'Path {path_id}')
            segments = path_data.get('segments', [])
            
            if not segments:
                return
            
            # Use distinctive colors for paths
            path_colors = [
                QColor(255, 100, 100),  # Red
                QColor(100, 255, 100),  # Green  
                QColor(100, 100, 255),  # Blue
                QColor(255, 255, 100),  # Yellow
                QColor(255, 100, 255),  # Magenta
                QColor(100, 255, 255),  # Cyan
            ]
            
            color = path_colors[path_id % len(path_colors)]
            pen = QPen(color, 4, Qt.SolidLine)
            painter.setPen(pen)
            
            # Draw path segments as thick lines
            for segment in segments:
                from_component = segment.get('from_component')
                to_component = segment.get('to_component')
                
                if from_component and to_component:
                    from_x = from_component.get('x_position', from_component.get('x', 0))
                    from_y = from_component.get('y_position', from_component.get('y', 0))
                    to_x = to_component.get('x_position', to_component.get('x', 0))
                    to_y = to_component.get('y_position', to_component.get('y', 0))
                    
                    painter.drawLine(from_x, from_y, to_x, to_y)
                    
                    # Draw arrows to show direction
                    self.draw_arrow(painter, from_x, from_y, to_x, to_y, color)
            
            # Draw path label at the first component
            if segments:
                first_segment = segments[0]
                from_component = first_segment.get('from_component')
                if from_component:
                    label_x = from_component.get('x_position', from_component.get('x', 0))
                    label_y = from_component.get('y_position', from_component.get('y', 0))
                    
                    # Draw path name with background
                    font = QFont("Arial", 10, QFont.Bold)
                    painter.setFont(font)
                    
                    # Semi-transparent background for readability
                    text_rect = painter.fontMetrics().boundingRect(path_name)
                    bg_rect = text_rect.adjusted(-4, -2, 4, 2)
                    bg_rect.moveTopLeft(QPoint(label_x + 20, label_y - 25))
                    
                    painter.fillRect(bg_rect, QColor(255, 255, 255, 200))
                    painter.setPen(QPen(Qt.black))
                    painter.drawText(label_x + 20, label_y - 10, path_name)
                    
        except Exception as e:
            print(f"Error drawing path {path_id}: {e}")
    
    def draw_arrow(self, painter, from_x: int, from_y: int, to_x: int, to_y: int, color: QColor):
        """Draw a directional arrow on a line segment"""
        import math
        
        # Calculate line length and angle
        dx = to_x - from_x
        dy = to_y - from_y
        length = math.sqrt(dx*dx + dy*dy)
        
        if length < 20:  # Don't draw arrows on very short segments
            return
            
        # Calculate arrow position (at 70% along the line)
        arrow_pos_x = from_x + int(0.7 * dx)
        arrow_pos_y = from_y + int(0.7 * dy)
        
        # Calculate arrow head
        angle = math.atan2(dy, dx)
        arrow_length = 12
        arrow_angle = math.pi / 6  # 30 degrees
        
        # Arrow head points
        ax1 = arrow_pos_x - arrow_length * math.cos(angle - arrow_angle)
        ay1 = arrow_pos_y - arrow_length * math.sin(angle - arrow_angle)
        ax2 = arrow_pos_x - arrow_length * math.cos(angle + arrow_angle)
        ay2 = arrow_pos_y - arrow_length * math.sin(angle + arrow_angle)
        
        # Draw arrow head
        pen = QPen(color, 2, Qt.SolidLine)
        painter.setPen(pen)
        painter.drawLine(arrow_pos_x, arrow_pos_y, int(ax1), int(ay1))
        painter.drawLine(arrow_pos_x, arrow_pos_y, int(ax2), int(ay2))
            
    def clear_all_elements(self):
        """Clear all drawn elements"""
        # Cancel any active tool first
        self.tool_manager.cancel_tool()
        
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
        """Get all elements data with proper structure"""
        print(f"DEBUG: get_elements_data - Returning {len(self.components)} components and {len(self.segments)} segments")
        
        # Debug: Print segment details
        for i, seg in enumerate(self.segments):
            print(f"DEBUG: Segment {i} in overlay: from_component={seg.get('from_component') is not None}, to_component={seg.get('to_component') is not None}")
            if seg.get('from_component'):
                print(f"DEBUG:   From: {seg['from_component'].get('component_type', 'unknown')} at ({seg['from_component'].get('x', 0)}, {seg['from_component'].get('y', 0)})")
            if seg.get('to_component'):
                print(f"DEBUG:   To: {seg['to_component'].get('component_type', 'unknown')} at ({seg['to_component'].get('x', 0)}, {seg['to_component'].get('y', 0)})")
        
        return {
            'rectangles': self.rectangles.copy(),
            'components': self.components.copy(),
            'segments': self.segments.copy(),
            'measurements': self.measurements.copy()
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
    
    # Path visualization methods
    def show_path(self, path_id: int, path_data: dict):
        """Show a specific HVAC path on the drawing overlay"""
        self.visible_paths[path_id] = path_data
        self.update()
    
    def hide_path(self, path_id: int):
        """Hide a specific HVAC path from the drawing overlay"""
        self.visible_paths.pop(path_id, None)
        self.update()
    
    def clear_all_paths(self):
        """Clear all visible paths"""
        self.visible_paths.clear()
        self.update()
    
    def register_path_elements(self, path_id: int, components: list, segments: list):
        """Register which components and segments belong to a path"""
        self.path_element_mapping[path_id] = {
            'components': components.copy(),
            'segments': segments.copy()
        }
        print(f"DEBUG: Path {path_id} registered with {len(components)} components and {len(segments)} segments")
        print(f"DEBUG: Current path mappings: {list(self.path_element_mapping.keys())}")
    
    def unregister_path_elements(self, path_id: int):
        """Remove path element mapping"""
        self.path_element_mapping.pop(path_id, None)
    
    def is_component_hidden_by_path(self, comp_data: dict) -> bool:
        """Check if a component should be hidden because its path is hidden"""
        # Check if this component belongs to any registered path
        for path_id, mapping in self.path_element_mapping.items():
            for path_comp in mapping['components']:
                # Compare by position since components might not have unique IDs
                if (comp_data.get('x') == path_comp.get('x') and 
                    comp_data.get('y') == path_comp.get('y') and
                    comp_data.get('component_type') == path_comp.get('component_type')):
                    # This component belongs to a path, check if path is hidden
                    is_hidden = path_id not in self.visible_paths
                    if is_hidden:
                        print(f"DEBUG: Hiding component {comp_data.get('component_type')} at ({comp_data.get('x')}, {comp_data.get('y')}) - path {path_id} not in visible_paths {list(self.visible_paths.keys())}")
                    else:
                        print(f"DEBUG: Showing component {comp_data.get('component_type')} at ({comp_data.get('x')}, {comp_data.get('y')}) - path {path_id} is in visible_paths {list(self.visible_paths.keys())}")
                    return is_hidden
        return False
    
    def is_segment_hidden_by_path(self, seg_data: dict) -> bool:
        """Check if a segment should be hidden because its path is hidden"""
        # Check if this segment belongs to any registered path
        for path_id, mapping in self.path_element_mapping.items():
            for path_seg in mapping['segments']:
                # Compare by start/end positions since segments might not have unique IDs
                if (seg_data.get('start_x') == path_seg.get('start_x') and 
                    seg_data.get('start_y') == path_seg.get('start_y') and
                    seg_data.get('end_x') == path_seg.get('end_x') and
                    seg_data.get('end_y') == path_seg.get('end_y')):
                    # This segment belongs to a path, check if path is hidden
                    is_hidden = path_id not in self.visible_paths
                    if is_hidden:
                        print(f"DEBUG: Hiding segment from ({seg_data.get('start_x')}, {seg_data.get('start_y')}) to ({seg_data.get('end_x')}, {seg_data.get('end_y')}) - path {path_id} not in visible_paths {list(self.visible_paths.keys())}")
                    else:
                        print(f"DEBUG: Showing segment from ({seg_data.get('start_x')}, {seg_data.get('start_y')}) to ({seg_data.get('end_x')}, {seg_data.get('end_y')}) - path {path_id} is in visible_paths {list(self.visible_paths.keys())}")
                    return is_hidden
        return False
    
    def is_component_part_of_visible_path(self, comp_data: dict) -> bool:
        """Check if a component belongs to any visible path"""
        for path_id, mapping in self.path_element_mapping.items():
            if path_id in self.visible_paths:  # Only check visible paths
                for path_comp in mapping['components']:
                    if (comp_data.get('x') == path_comp.get('x') and 
                        comp_data.get('y') == path_comp.get('y') and
                        comp_data.get('component_type') == path_comp.get('component_type')):
                        return True
        return False
    
    def is_segment_part_of_visible_path(self, seg_data: dict) -> bool:
        """Check if a segment belongs to any visible path"""
        for path_id, mapping in self.path_element_mapping.items():
            if path_id in self.visible_paths:  # Only check visible paths
                for path_seg in mapping['segments']:
                    if (seg_data.get('start_x') == path_seg.get('start_x') and 
                        seg_data.get('start_y') == path_seg.get('start_y') and
                        seg_data.get('end_x') == path_seg.get('end_x') and
                        seg_data.get('end_y') == path_seg.get('end_y')):
                        return True
        return False