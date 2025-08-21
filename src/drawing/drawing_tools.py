"""
Drawing Tools - Rectangle and component drawing tools for the overlay system
"""

from enum import Enum
from PySide6.QtCore import Qt, QRect, QPoint, Signal, QObject
from PySide6.QtGui import QPen, QBrush, QColor, QPainter
from PySide6.QtWidgets import QWidget
import math


class ToolType(Enum):
    """Available drawing tools"""
    SELECT = "select"
    RECTANGLE = "rectangle"
    COMPONENT = "component"
    SEGMENT = "segment"
    MEASURE = "measure"
    POLYGON = "polygon"


class DrawingTool(QObject):
    """Base class for drawing tools"""
    
    finished = Signal(dict)  # Emitted when tool operation is complete
    updated = Signal()  # Emitted when tool state changes
    
    def __init__(self):
        super().__init__()
        self.active = False
        self.start_point = None
        self.current_point = None
        
    def start(self, point):
        """Start tool operation at given point"""
        self.active = True
        self.start_point = point
        self.current_point = point
        
    def update(self, point):
        """Update tool operation with current point"""
        if self.active:
            self.current_point = point
            self.updated.emit()
            
    def finish(self, point):
        """Finish tool operation at given point"""
        if self.active:
            self.current_point = point
            self.active = False
            result = self.get_result()
            if result:
                self.finished.emit(result)
                
    def cancel(self):
        """Cancel current tool operation"""
        self.active = False
        self.start_point = None
        self.current_point = None
        
    def get_result(self):
        """Get the result of the tool operation"""
        return {}
        
    def draw_preview(self, painter):
        """Draw preview of current tool operation"""
        pass


class RectangleTool(DrawingTool):
    """Tool for drawing rectangles (room boundaries)"""
    
    def __init__(self):
        super().__init__()
        self.pen = QPen(QColor(0, 120, 215), 2, Qt.SolidLine)
        self.brush = QBrush(QColor(0, 120, 215, 30))
        
    def get_result(self):
        """Get rectangle coordinates and dimensions"""
        if not self.start_point or not self.current_point:
            return None
            
        # Calculate rectangle bounds
        x1, y1 = self.start_point.x(), self.start_point.y()
        x2, y2 = self.current_point.x(), self.current_point.y()
        
        x = min(x1, x2)
        y = min(y1, y2)
        width = abs(x2 - x1)
        height = abs(y2 - y1)
        
        # Only return if rectangle has minimum size
        if width > 10 and height > 10:
            return {
                'type': 'rectangle',
                'x': x,
                'y': y,
                'width': width,
                'height': height,
                'bounds': QRect(x, y, width, height)
            }
        return None
        
    def draw_preview(self, painter):
        """Draw rectangle preview"""
        if self.active and self.start_point and self.current_point:
            painter.setPen(self.pen)
            painter.setBrush(self.brush)
            
            x1, y1 = self.start_point.x(), self.start_point.y()
            x2, y2 = self.current_point.x(), self.current_point.y()
            
            rect = QRect(QPoint(x1, y1), QPoint(x2, y2))
            painter.drawRect(rect.normalized())


class SelectionTool(DrawingTool):
    """Selection/edit tool. This tool itself does not create elements; it
    exists so that the overlay can detect SELECT mode via the tool manager.

    The overlay owns the selection logic and uses mouse events to perform
    hit-testing, box selection, and dragging. This class only provides an
    optional rubber-band preview rectangle when active in box-select mode.
    """

    def __init__(self):
        super().__init__()
        self.pen = QPen(QColor(255, 200, 0), 1, Qt.DashLine)
        self._box_select_mode = False

    def start(self, point):
        self.active = True
        self.start_point = point
        self.current_point = point
        # Overlay will decide whether this is a drag or a box; default to box
        self._box_select_mode = True

    def update(self, point):
        if self.active:
            self.current_point = point
            self.updated.emit()

    def finish(self, point):
        # Selection tool does not emit new elements; overlay will handle
        self.active = False
        self._box_select_mode = False

    def cancel(self):
        super().cancel()
        self._box_select_mode = False

    def draw_preview(self, painter):
        if self.active and self._box_select_mode and self.start_point and self.current_point:
            painter.setPen(self.pen)
            rect = QRect(self.start_point, self.current_point).normalized()
            painter.drawRect(rect)

class ComponentTool(DrawingTool):
    """Tool for placing HVAC components"""
    
    def __init__(self, component_type="ahu"):
        super().__init__()
        self.component_type = component_type
        self.component_size = 24  # Size in pixels
        self.pen = QPen(QColor(220, 100, 50), 2, Qt.SolidLine)
        self.brush = QBrush(QColor(220, 100, 50, 100))
        
    def set_component_type(self, component_type):
        """Set the type of component to place"""
        self.component_type = component_type
        
    def start(self, point):
        """Place component immediately on click"""
        self.start_point = point
        self.current_point = point
        self.active = True
        
    def finish(self, point):
        """Complete component placement"""
        if self.active:
            self.active = False
            result = {
                'type': 'component',
                'component_type': self.component_type,
                'x': point.x(),
                'y': point.y(),
                'position': {
                    'x': point.x(),
                    'y': point.y()
                }
            }
            self.finished.emit(result)
            
    def draw_preview(self, painter):
        """Draw component preview"""
        if self.current_point:
            painter.setPen(self.pen)
            painter.setBrush(self.brush)
            
            # Draw component as circle or square based on type
            x, y = self.current_point.x(), self.current_point.y()
            size = self.component_size
            
            if self.component_type in ['ahu', 'coil']:
                # Draw as rectangle for equipment
                rect = QRect(x - size//2, y - size//2, size, size)
                painter.drawRect(rect)
            elif self.component_type == 'elbow':
                # Draw as L-shaped elbow for direction changes
                painter.setPen(QPen(QColor(100, 100, 100), 3, Qt.SolidLine))
                painter.setBrush(QBrush(QColor(100, 100, 100, 50)))
                
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
            elif self.component_type == 'branch':
                # Draw as T-shaped branch for flow distribution
                painter.setPen(QPen(QColor(150, 75, 0), 3, Qt.SolidLine))
                painter.setBrush(QBrush(QColor(150, 75, 0, 50)))
                
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
                # Draw as circle for terminals
                painter.drawEllipse(x - size//2, y - size//2, size, size)
                
            # Add label
            painter.setPen(QPen(Qt.black))
            painter.drawText(x - 15, y + size//2 + 15, self.component_type.upper())


class SegmentTool(DrawingTool):
    """Tool for drawing duct segments between components"""
    
    def __init__(self):
        super().__init__()
        self.pen = QPen(QColor(50, 150, 50), 3, Qt.SolidLine)
        self.from_component = None
        self.to_component = None
        self.from_segment = None
        self.to_segment = None
        self.available_components = []  # List of components to connect to
        self.available_segments = []  # List of existing segments to connect to
        
    def set_available_components(self, components):
        """Set the list of available components to connect to"""
        self.available_components = components
        
    def set_available_segments(self, segments):
        """Set the list of available segments to connect to"""
        self.available_segments = segments
        
    def set_from_component(self, component):
        """Set the starting component for the segment"""
        self.from_component = component
        
    def find_nearby_component(self, point, max_distance=20):
        """Find a component near the given point"""
        if not self.available_components:
            print(f"DEBUG: No available components to connect to")
            return None
            
        print(f"DEBUG: Looking for component near point ({point.x()}, {point.y()})")
        print(f"DEBUG: Available components: {len(self.available_components)}")
        
        for i, component in enumerate(self.available_components):
            comp_x = component.get('x', 0)
            comp_y = component.get('y', 0)
            
            distance = math.sqrt((point.x() - comp_x)**2 + (point.y() - comp_y)**2)
            print(f"DEBUG: Component {i}: ({comp_x}, {comp_y}) - distance: {distance:.1f}")
            
            if distance <= max_distance:
                print(f"DEBUG: Found component at distance {distance:.1f}")
                return component
                
        print(f"DEBUG: No component found within {max_distance} pixels")
        return None
        
    def find_nearby_segment(self, point, max_distance=20):
        """Find a segment near the given point and infer any component at the endpoint.

        Returns a dictionary with:
        - 'segment': the segment dict
        - 'endpoint': 'start' | 'end'
        - 'distance': float
        - 'component': component dict at that endpoint if known
        - 'snap_x'/'snap_y': coordinates to snap the cursor to the endpoint
        """
        if not self.available_segments:
            print("DEBUG: No available segments to connect to")
            return None

        print(f"DEBUG: Looking for segment near point ({point.x()}, {point.y()})")
        print(f"DEBUG: Available segments: {len(self.available_segments)}")

        for i, segment in enumerate(self.available_segments):
            # Check distance to segment endpoints
            start_x = segment.get('start_x', 0)
            start_y = segment.get('start_y', 0)
            end_x = segment.get('end_x', 0)
            end_y = segment.get('end_y', 0)

            # Distance to start point
            start_distance = math.sqrt((point.x() - start_x) ** 2 + (point.y() - start_y) ** 2)
            # Distance to end point
            end_distance = math.sqrt((point.x() - end_x) ** 2 + (point.y() - end_y) ** 2)

            print(f"DEBUG: Segment {i}: start=({start_x}, {start_y}) end=({end_x}, {end_y})")
            print(f"DEBUG:   Start distance: {start_distance:.1f}, End distance: {end_distance:.1f}")

            if start_distance <= max_distance:
                component_at_endpoint = segment.get('from_component')
                print(
                    "DEBUG: Found segment at start point, distance "
                    f"{start_distance:.1f}; has_component={component_at_endpoint is not None}"
                )
                return {
                    'segment': segment,
                    'endpoint': 'start',
                    'distance': start_distance,
                    'component': component_at_endpoint,
                    'snap_x': start_x,
                    'snap_y': start_y,
                }
            if end_distance <= max_distance:
                component_at_endpoint = segment.get('to_component')
                print(
                    "DEBUG: Found segment at end point, distance "
                    f"{end_distance:.1f}; has_component={component_at_endpoint is not None}"
                )
                return {
                    'segment': segment,
                    'endpoint': 'end',
                    'distance': end_distance,
                    'component': component_at_endpoint,
                    'snap_x': end_x,
                    'snap_y': end_y,
                }

        print(f"DEBUG: No segment found within {max_distance} pixels")
        return None
        
    def start(self, point):
        """Start segment drawing - try to connect to nearby component or segment"""
        super().start(point)

        # Try to find a component at the start point
        self.from_component = self.find_nearby_component(point)

        # If no component found, try to find a segment endpoint; snap and infer component
        if not self.from_component:
            nearby_segment = self.find_nearby_segment(point)
            if nearby_segment:
                print("DEBUG: Starting segment from existing segment endpoint")
                self.from_segment = nearby_segment
                # Snap start point for clean geometry
                try:
                    self.start_point.setX(int(nearby_segment['snap_x']))
                    self.start_point.setY(int(nearby_segment['snap_y']))
                except Exception:
                    pass
                # If that endpoint is attached to a component, use it
                if nearby_segment.get('component') is not None:
                    self.from_component = nearby_segment['component']
                else:
                    # Re-check for a component at the snapped point
                    try:
                        snapped = QPoint(int(nearby_segment['snap_x']), int(nearby_segment['snap_y']))
                        alt_component = self.find_nearby_component(snapped)
                        if alt_component is not None:
                            print("DEBUG: Found component at snapped start point; using as from_component")
                            self.from_component = alt_component
                    except Exception:
                        pass
        
    def finish(self, point):
        """Finish segment drawing - try to connect to nearby component or segment"""
        print(f"DEBUG: SegmentTool.finish - method called, active: {self.active}")
        if self.active:
            print("DEBUG: SegmentTool.finish - tool is active, processing")
            self.current_point = point

            # Try to find a component at the end point
            self.to_component = self.find_nearby_component(point)

            # If no component found, try to find a segment endpoint; snap and infer component
            if not self.to_component:
                nearby_segment = self.find_nearby_segment(point)
                if nearby_segment:
                    print("DEBUG: Ending segment at existing segment endpoint")
                    self.to_segment = nearby_segment
                    # Snap end point for clean geometry
                    try:
                        self.current_point.setX(int(nearby_segment['snap_x']))
                        self.current_point.setY(int(nearby_segment['snap_y']))
                    except Exception:
                        pass
                    # If that endpoint is attached to a component, use it
                    if nearby_segment.get('component') is not None:
                        self.to_component = nearby_segment['component']
                    else:
                        # Re-check for a component at the snapped point
                        try:
                            snapped = QPoint(int(nearby_segment['snap_x']), int(nearby_segment['snap_y']))
                            alt_component = self.find_nearby_component(snapped)
                            if alt_component is not None:
                                print("DEBUG: Found component at snapped end point; using as to_component")
                                self.to_component = alt_component
                        except Exception:
                            pass

            self.active = False
            print("DEBUG: SegmentTool.finish - calling get_result()")
            result = self.get_result()
            print(f"DEBUG: SegmentTool.finish - result: {result is not None}")
            if result:
                print("DEBUG: SegmentTool.finish - emitting finished signal")
                self.finished.emit(result)
            else:
                print("DEBUG: SegmentTool.finish - no result to emit")
        else:
            print("DEBUG: SegmentTool.finish - tool is NOT active, skipping")
                
    def get_result(self):
        """Get segment information"""
        print(f"DEBUG: get_result - method called")
        if not self.start_point or not self.current_point:
            print(f"DEBUG: get_result - no start or current point")
            return None
            
        # Calculate length (with axis snapping)
        x1, y1 = self.start_point.x(), self.start_point.y()
        x2, y2 = self.current_point.x(), self.current_point.y()
        dx = x2 - x1
        dy = y2 - y1
        # Snap to axis if nearly horizontal/vertical (10px tolerance)
        if abs(dx) < 10 and abs(dy) >= 10:
            x2 = x1
        elif abs(dy) < 10 and abs(dx) >= 10:
            y2 = y1
        length_pixels = math.sqrt((x2 - x1)**2 + (y2 - y1)**2)
        
        print(f"DEBUG: get_result - length_pixels: {length_pixels}")
        
        if length_pixels > 10:  # Minimum segment length (reduced for precise connections)
            # Prevent self-connections
            if self.from_component and self.to_component:
                from_comp_id = f"{self.from_component.get('x', 0)}_{self.from_component.get('y', 0)}_{self.from_component.get('component_type', 'unknown')}"
                to_comp_id = f"{self.to_component.get('x', 0)}_{self.to_component.get('y', 0)}_{self.to_component.get('component_type', 'unknown')}"
                
                if from_comp_id == to_comp_id:
                    print(f"DEBUG: get_result - preventing self-connection")
                    return None
                else:
                    print(f"DEBUG: get_result - components are different, allowing connection")
            
            result = {
                'type': 'segment',
                'start_x': x1,
                'start_y': y1,
                'end_x': x2,
                'end_y': y2,
                'length_pixels': length_pixels,
                'from_component': self.from_component,
                'to_component': self.to_component
            }
            
            print(f"DEBUG: Segment result - from_component: {self.from_component is not None}, to_component: {self.to_component is not None}")
            if self.from_component:
                print(f"DEBUG: From component: {self.from_component.get('component_type', 'unknown')} at ({self.from_component.get('x', 0)}, {self.from_component.get('y', 0)})")
            if self.to_component:
                print(f"DEBUG: To component: {self.to_component.get('component_type', 'unknown')} at ({self.to_component.get('x', 0)}, {self.to_component.get('y', 0)})")
            
            print(f"DEBUG: get_result - returning valid segment result")
            return result
        else:
            print(f"DEBUG: get_result - segment too short ({length_pixels} pixels)")
        return None
        
    def draw_preview(self, painter):
        """Draw segment preview"""
        if self.active and self.start_point and self.current_point:
            painter.setPen(self.pen)
            painter.drawLine(self.start_point, self.current_point)
            
            # Draw detection radius around current point
            painter.setPen(QPen(QColor(255, 255, 0, 100), 1, Qt.DashLine))
            painter.setBrush(QBrush(QColor(255, 255, 0, 20)))
            painter.drawEllipse(self.current_point.x() - 20, self.current_point.y() - 20, 40, 40)
            
            # Draw connection indicators
            if self.from_component:
                painter.setPen(QPen(QColor(0, 255, 0), 2, Qt.SolidLine))
                painter.setBrush(QBrush(QColor(0, 255, 0, 100)))
                comp_x = self.from_component.get('x', 0)
                comp_y = self.from_component.get('y', 0)
                painter.drawEllipse(comp_x - 8, comp_y - 8, 16, 16)
            
            if self.to_component:
                painter.setPen(QPen(QColor(0, 255, 0), 2, Qt.SolidLine))
                painter.setBrush(QBrush(QColor(0, 255, 0, 100)))
                comp_x = self.to_component.get('x', 0)
                comp_y = self.to_component.get('y', 0)
                painter.drawEllipse(comp_x - 8, comp_y - 8, 16, 16)
            
            # Draw length label
            mid_x = (self.start_point.x() + self.current_point.x()) // 2
            mid_y = (self.start_point.y() + self.current_point.y()) // 2
            
            length_pixels = math.sqrt(
                (self.current_point.x() - self.start_point.x())**2 + 
                (self.current_point.y() - self.start_point.y())**2
            )
            
            painter.setPen(QPen(Qt.black))
            painter.drawText(mid_x + 5, mid_y - 5, f"{length_pixels:.0f}px")


class MeasureTool(DrawingTool):
    """Tool for measuring distances"""
    
    def __init__(self):
        super().__init__()
        self.pen = QPen(QColor(255, 0, 0), 2, Qt.DashLine)
        
    def get_result(self):
        """Get measurement result"""
        if not self.start_point or not self.current_point:
            return None
            
        x1, y1 = self.start_point.x(), self.start_point.y()
        x2, y2 = self.current_point.x(), self.current_point.y()
        length_pixels = math.sqrt((x2 - x1)**2 + (y2 - y1)**2)
        
        return {
            'type': 'measurement',
            'start_x': x1,
            'start_y': y1,
            'end_x': x2,
            'end_y': y2,
            'length_pixels': length_pixels
        }
        
    def draw_preview(self, painter):
        """Draw measurement preview"""
        if self.active and self.start_point and self.current_point:
            painter.setPen(self.pen)
            painter.drawLine(self.start_point, self.current_point)
            
            # Draw measurement points
            painter.setBrush(QBrush(QColor(255, 0, 0)))
            painter.drawEllipse(self.start_point.x() - 3, self.start_point.y() - 3, 6, 6)
            painter.drawEllipse(self.current_point.x() - 3, self.current_point.y() - 3, 6, 6)
            
            # Draw distance label
            mid_x = (self.start_point.x() + self.current_point.x()) // 2
            mid_y = (self.start_point.y() + self.current_point.y()) // 2
            
            length_pixels = math.sqrt(
                (self.current_point.x() - self.start_point.x())**2 + 
                (self.current_point.y() - self.start_point.y())**2
            )
            
            painter.setPen(QPen(Qt.red))
            painter.drawText(mid_x + 5, mid_y - 5, f"📏 {length_pixels:.0f}px")


class PolygonTool(DrawingTool):
    """Tool for drawing polygonal spaces by placing vertices"""

    def __init__(self):
        super().__init__()
        self.pen = QPen(QColor(0, 120, 215), 2, Qt.SolidLine)
        self.fill_brush = QBrush(QColor(0, 120, 215, 30))
        self.vertex_pen = QPen(QColor(0, 120, 215), 1, Qt.SolidLine)
        self.vertex_brush = QBrush(QColor(0, 120, 215))
        self.vertices = []  # list[QPoint]
        self._closed = False

    def start(self, point):
        self.active = True
        self.vertices = [QPoint(point.x(), point.y())]
        self.start_point = point
        self.current_point = point
        self._closed = False

    def add_vertex(self, point):
        if not self.active:
            self.start(point)
            return
        # Avoid duplicate consecutive points
        if self.vertices:
            last = self.vertices[-1]
            if last.x() == point.x() and last.y() == point.y():
                return
        self.vertices.append(QPoint(point.x(), point.y()))
        self.current_point = point
        self.updated.emit()

    def update(self, point):
        # For live preview of the last edge
        if self.active:
            self.current_point = point
            self.updated.emit()

    def cancel(self):
        super().cancel()
        self.vertices = []
        self._closed = False

    def _compute_bounds(self):
        if not self.vertices:
            return None
        xs = [p.x() for p in self.vertices]
        ys = [p.y() for p in self.vertices]
        x = min(xs)
        y = min(ys)
        w = max(1, max(xs) - x)
        h = max(1, max(ys) - y)
        return QRect(x, y, w, h)

    def get_result(self):
        # Only produce a result when we have a closed polygon with >= 3 vertices
        if not self.vertices or len(self.vertices) < 3:
            return None
        bounds = self._compute_bounds()
        # Serialize points
        points = [{'x': int(p.x()), 'y': int(p.y())} for p in self.vertices]
        return {
            'type': 'polygon',
            'points': points,
            'x': int(bounds.x()) if isinstance(bounds, QRect) else 0,
            'y': int(bounds.y()) if isinstance(bounds, QRect) else 0,
            'width': int(bounds.width()) if isinstance(bounds, QRect) else 0,
            'height': int(bounds.height()) if isinstance(bounds, QRect) else 0,
            'bounds': bounds
        }

    def finish(self, point):
        # Close and emit if valid
        if not self.active:
            return
        
        # Add the final point if it's not too close to the last vertex
        if point and self.vertices:
            last = self.vertices[-1]
            dx = point.x() - last.x()
            dy = point.y() - last.y()
            distance = (dx * dx + dy * dy) ** 0.5
            
            # If clicking close to first vertex, close the polygon
            if len(self.vertices) >= 3:
                first = self.vertices[0]
                dx_first = point.x() - first.x()
                dy_first = point.y() - first.y()
                distance_to_first = (dx_first * dx_first + dy_first * dy_first) ** 0.5
                
                if distance_to_first <= 15:  # Close tolerance
                    print("DEBUG: Closing polygon by snapping to first vertex")
                    self._closed = True
                else:
                    # Add final point if not too close to last
                    if distance > 5:
                        self.vertices.append(QPoint(point.x(), point.y()))
                        print(f"DEBUG: Added final vertex, total vertices: {len(self.vertices)}")
        
        self.active = False
        result = self.get_result()
        if result:
            print(f"DEBUG: PolygonTool emitting result with {len(result.get('points', []))} points")
            self.finished.emit(result)
        else:
            print("DEBUG: PolygonTool - no valid result to emit")

    def draw_preview(self, painter):
        if not self.active:
            return
        pts = self.vertices.copy()
        
        # Add preview line to current mouse position
        if self.current_point and len(pts) > 0:
            last = pts[-1]
            if last.x() != self.current_point.x() or last.y() != self.current_point.y():
                painter.setPen(QPen(QColor(0, 120, 215, 128), 1, Qt.DashLine))
                painter.drawLine(last, self.current_point)
                
                # Show closing line if near first vertex
                if len(pts) >= 3:
                    first = pts[0]
                    dx = self.current_point.x() - first.x()
                    dy = self.current_point.y() - first.y()
                    if (dx * dx + dy * dy) ** 0.5 <= 15:
                        painter.setPen(QPen(QColor(255, 0, 0), 2, Qt.SolidLine))
                        painter.drawLine(self.current_point, first)
        
        # Draw the polygon edges
        if len(pts) >= 2:
            painter.setPen(self.pen)
            for i in range(len(pts) - 1):
                painter.drawLine(pts[i], pts[i + 1])
                
        # If we have enough points, show filled preview
        if len(pts) >= 3:
            from PySide6.QtGui import QPolygon
            polygon = QPolygon(pts)
            painter.setPen(self.pen)
            painter.setBrush(self.fill_brush)
            painter.drawPolygon(polygon)
        
        # Draw vertices as circles
        painter.setPen(self.vertex_pen)
        painter.setBrush(self.vertex_brush)
        for i, p in enumerate(self.vertices):
            # First vertex is larger and red
            if i == 0 and len(self.vertices) >= 3:
                painter.setPen(QPen(QColor(255, 0, 0), 2))
                painter.setBrush(QBrush(QColor(255, 0, 0)))
                painter.drawEllipse(p.x() - 4, p.y() - 4, 8, 8)
            else:
                painter.setPen(self.vertex_pen)
                painter.setBrush(self.vertex_brush)
                painter.drawEllipse(p.x() - 3, p.y() - 3, 6, 6)

class DrawingToolManager(QObject):
    """Manages drawing tools and their state"""
    
    tool_changed = Signal(str)  # Current tool name
    element_created = Signal(dict)  # New element created
    
    def __init__(self):
        super().__init__()
        self.tools = {
            ToolType.SELECT: SelectionTool(),
            ToolType.RECTANGLE: RectangleTool(),
            ToolType.COMPONENT: ComponentTool(),
            ToolType.SEGMENT: SegmentTool(),
            ToolType.MEASURE: MeasureTool(),
            ToolType.POLYGON: PolygonTool()
        }
        
        self.current_tool_type = ToolType.RECTANGLE
        self.current_tool = self.tools[self.current_tool_type]
        
        # Connect tool signals
        for tool in self.tools.values():
            tool.finished.connect(self.element_created.emit)
            
    def set_tool(self, tool_type):
        """Set the active drawing tool"""
        if tool_type in self.tools:
            # Cancel current tool
            self.current_tool.cancel()
            
            # Switch tools
            self.current_tool_type = tool_type
            self.current_tool = self.tools[tool_type]
            self.tool_changed.emit(tool_type.value)
            
    def set_component_type(self, component_type):
        """Set component type for component tool"""
        if ToolType.COMPONENT in self.tools:
            self.tools[ToolType.COMPONENT].set_component_type(component_type)
    
    def set_available_components(self, components):
        """Set available components for segment tool"""
        if ToolType.SEGMENT in self.tools:
            self.tools[ToolType.SEGMENT].set_available_components(components)
            
    def set_available_segments(self, segments):
        """Set available segments for segment tool"""
        if ToolType.SEGMENT in self.tools:
            self.tools[ToolType.SEGMENT].set_available_segments(segments)
            
    def get_current_tool(self):
        """Get the current active tool"""
        return self.current_tool
        
    def start_tool(self, point):
        """Start current tool operation"""
        self.current_tool.start(point)
        
    def update_tool(self, point):
        """Update current tool operation"""
        self.current_tool.update(point)
        
    def finish_tool(self, point):
        """Finish current tool operation"""
        print(f"DEBUG: finish_tool - calling current_tool.finish({point.x()}, {point.y()})")
        self.current_tool.finish(point)
        
    def cancel_tool(self):
        """Cancel current tool operation"""
        self.current_tool.cancel()