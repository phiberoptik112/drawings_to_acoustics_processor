"""
Drawing Elements - Models for storing drawn elements from the overlay system
"""

from sqlalchemy import Column, Integer, String, DateTime, Text, ForeignKey, Float, JSON
from sqlalchemy.orm import relationship
from datetime import datetime
from .database import Base


class DrawingElement(Base):
    """Base model for storing drawing elements from the overlay"""
    __tablename__ = 'drawing_elements'
    
    id = Column(Integer, primary_key=True)
    drawing_id = Column(Integer, ForeignKey('drawings.id'), nullable=False)
    project_id = Column(Integer, ForeignKey('projects.id'), nullable=False)
    
    # Element identification
    element_type = Column(String(50), nullable=False)  # 'rectangle', 'component', 'segment', 'measurement'
    element_name = Column(String(255))  # Optional name/label
    
    # Position and geometry (in pixels)
    x_position = Column(Float)
    y_position = Column(Float)
    width = Column(Float)
    height = Column(Float)
    
    # Additional coordinates for lines/segments
    end_x_position = Column(Float)
    end_y_position = Column(Float)
    
    # Real-world measurements
    area_real = Column(Float)     # Square feet/meters
    length_real = Column(Float)   # Feet/meters
    volume_real = Column(Float)   # Cubic feet/meters
    
    # Element-specific properties stored as JSON
    properties = Column(JSON)  # Store element-specific data as JSON
    
    # Metadata
    created_date = Column(DateTime, default=datetime.utcnow)
    modified_date = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    drawing = relationship("Drawing", backref="drawing_elements")
    project = relationship("Project", backref="drawing_elements")
    
    def __repr__(self):
        return f"<DrawingElement(id={self.id}, type='{self.element_type}', drawing_id={self.drawing_id})>"
    
    def to_dict(self):
        """Convert to dictionary for overlay reconstruction"""
        data = {
            'id': self.id,
            'type': self.element_type,
            'name': self.element_name,
            'x': self.x_position,
            'y': self.y_position,
            'width': self.width,
            'height': self.height,
            'end_x': self.end_x_position,
            'end_y': self.end_y_position,
            'area_real': self.area_real,
            'length_real': self.length_real,
            'volume_real': self.volume_real,
            'created_date': self.created_date.isoformat() if self.created_date else None,
            'modified_date': self.modified_date.isoformat() if self.modified_date else None
        }
        
        # Add properties if they exist
        if self.properties:
            data.update(self.properties)
            
        return data
    
    @classmethod
    def from_overlay_data(cls, drawing_id, project_id, element_data):
        """Create DrawingElement from overlay element data"""
        element_type = element_data.get('type', 'unknown')
        
        # Extract common properties
        element = cls(
            drawing_id=drawing_id,
            project_id=project_id,
            element_type=element_type,
            x_position=element_data.get('x'),
            y_position=element_data.get('y'),
            width=element_data.get('width'),
            height=element_data.get('height'),
            area_real=element_data.get('area_real'),
            length_real=element_data.get('length_real')
        )
        
        # Type-specific properties
        if element_type == 'rectangle':
            element.element_name = f"Rectangle {element_data.get('area_formatted', '')}"
            element.properties = {
                'bounds': {
                    'x': element_data.get('x'),
                    'y': element_data.get('y'),
                    'width': element_data.get('width'),
                    'height': element_data.get('height')
                },
                'area_formatted': element_data.get('area_formatted'),
                'width_real': element_data.get('width_real'),
                'height_real': element_data.get('height_real')
            }
            
        elif element_type == 'component':
            component_type = element_data.get('component_type', 'unknown')
            element.element_name = f"{component_type.upper()}"
            element.properties = {
                'component_type': component_type,
                'position': {
                    'x': element_data.get('x'),
                    'y': element_data.get('y')
                }
            }
            
        elif element_type == 'segment':
            element.element_name = f"Segment {element_data.get('length_formatted', '')}"
            element.end_x_position = element_data.get('end_x')
            element.end_y_position = element_data.get('end_y')
            element.properties = {
                'start_x': element_data.get('start_x'),
                'start_y': element_data.get('start_y'),
                'end_x': element_data.get('end_x'),
                'end_y': element_data.get('end_y'),
                'length_pixels': element_data.get('length_pixels'),
                'length_formatted': element_data.get('length_formatted'),
                'from_component': element_data.get('from_component'),
                'to_component': element_data.get('to_component')
            }
            
        elif element_type == 'measurement':
            element.element_name = f"Measurement {element_data.get('length_formatted', '')}"
            element.end_x_position = element_data.get('end_x')
            element.end_y_position = element_data.get('end_y')
            element.properties = {
                'start_x': element_data.get('start_x'),
                'start_y': element_data.get('start_y'),
                'end_x': element_data.get('end_x'),
                'end_y': element_data.get('end_y'),
                'length_pixels': element_data.get('length_pixels'),
                'length_formatted': element_data.get('length_formatted')
            }
            
        return element


class DrawingElementManager:
    """Manager class for saving/loading drawing elements"""
    
    def __init__(self, session_factory):
        self.get_session = session_factory
        
    def save_elements(self, drawing_id, project_id, overlay_data):
        """Save all drawing elements from overlay data"""
        try:
            session = self.get_session()
            
            # Clear existing elements for this drawing
            session.query(DrawingElement).filter(
                DrawingElement.drawing_id == drawing_id
            ).delete()
            
            # Save new elements
            elements_saved = 0
            
            for element_type, elements_list in overlay_data.items():
                if element_type in ['rectangles', 'components', 'segments', 'measurements']:
                    for element_data in elements_list:
                        # Skip measurements if they're temporary
                        if element_type == 'measurements' and not element_data.get('persistent', True):
                            continue
                            
                        # Create drawing element
                        drawing_element = DrawingElement.from_overlay_data(
                            drawing_id, project_id, element_data
                        )
                        
                        session.add(drawing_element)
                        elements_saved += 1
                        
            session.commit()
            session.close()
            
            return elements_saved
            
        except Exception as e:
            session.rollback()
            session.close()
            raise e
            
    def load_elements(self, drawing_id):
        """Load drawing elements for overlay reconstruction"""
        try:
            session = self.get_session()
            
            elements = session.query(DrawingElement).filter(
                DrawingElement.drawing_id == drawing_id
            ).order_by(DrawingElement.created_date).all()
            
            # Group elements by type for overlay
            overlay_data = {
                'rectangles': [],
                'components': [],
                'segments': [],
                'measurements': []
            }
            
            for element in elements:
                element_dict = element.to_dict()
                
                if element.element_type == 'rectangle':
                    overlay_data['rectangles'].append(element_dict)
                elif element.element_type == 'component':
                    overlay_data['components'].append(element_dict)
                elif element.element_type == 'segment':
                    overlay_data['segments'].append(element_dict)
                elif element.element_type == 'measurement':
                    overlay_data['measurements'].append(element_dict)
                    
            session.close()
            return overlay_data
            
        except Exception as e:
            session.close()
            raise e
            
    def delete_element(self, element_id):
        """Delete a specific drawing element"""
        try:
            session = self.get_session()
            
            element = session.query(DrawingElement).filter(
                DrawingElement.id == element_id
            ).first()
            
            if element:
                session.delete(element)
                session.commit()
                session.close()
                return True
            else:
                session.close()
                return False
                
        except Exception as e:
            session.rollback()
            session.close()
            raise e
            
    def get_drawing_summary(self, drawing_id):
        """Get summary statistics for a drawing"""
        try:
            session = self.get_session()
            
            # Count elements by type
            rectangles_count = session.query(DrawingElement).filter(
                DrawingElement.drawing_id == drawing_id,
                DrawingElement.element_type == 'rectangle'
            ).count()
            
            components_count = session.query(DrawingElement).filter(
                DrawingElement.drawing_id == drawing_id,
                DrawingElement.element_type == 'component'
            ).count()
            
            segments_count = session.query(DrawingElement).filter(
                DrawingElement.drawing_id == drawing_id,
                DrawingElement.element_type == 'segment'
            ).count()
            
            # Calculate totals
            total_area = session.query(
                session.func.sum(DrawingElement.area_real)
            ).filter(
                DrawingElement.drawing_id == drawing_id,
                DrawingElement.element_type == 'rectangle'
            ).scalar() or 0
            
            total_length = session.query(
                session.func.sum(DrawingElement.length_real)
            ).filter(
                DrawingElement.drawing_id == drawing_id,
                DrawingElement.element_type == 'segment'
            ).scalar() or 0
            
            session.close()
            
            return {
                'rectangles': rectangles_count,
                'components': components_count,
                'segments': segments_count,
                'total_area': total_area,
                'total_length': total_length
            }
            
        except Exception as e:
            session.close()
            raise e