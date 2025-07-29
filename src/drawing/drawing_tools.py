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
                'position': point
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
        
    def set_from_component(self, component):
        """Set the starting component for the segment"""
        self.from_component = component
        
    def get_result(self):
        """Get segment information"""
        if not self.start_point or not self.current_point:
            return None
            
        # Calculate length
        x1, y1 = self.start_point.x(), self.start_point.y()
        x2, y2 = self.current_point.x(), self.current_point.y()
        length_pixels = math.sqrt((x2 - x1)**2 + (y2 - y1)**2)
        
        if length_pixels > 20:  # Minimum segment length
            return {
                'type': 'segment',
                'start_x': x1,
                'start_y': y1,
                'end_x': x2,
                'end_y': y2,
                'length_pixels': length_pixels,
                'from_component': self.from_component,
                'to_component': self.to_component
            }
        return None
        
    def draw_preview(self, painter):
        """Draw segment preview"""
        if self.active and self.start_point and self.current_point:
            painter.setPen(self.pen)
            painter.drawLine(self.start_point, self.current_point)
            
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


class DrawingToolManager(QObject):
    """Manages drawing tools and their state"""
    
    tool_changed = Signal(str)  # Current tool name
    element_created = Signal(dict)  # New element created
    
    def __init__(self):
        super().__init__()
        self.tools = {
            ToolType.RECTANGLE: RectangleTool(),
            ToolType.COMPONENT: ComponentTool(),
            ToolType.SEGMENT: SegmentTool(),
            ToolType.MEASURE: MeasureTool()
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
        self.current_tool.finish(point)
        
    def cancel_tool(self):
        """Cancel current tool operation"""
        self.current_tool.cancel()