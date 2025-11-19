"""
Drawing Location Model - Tracks where spaces and HVAC paths are located in drawings
"""

from sqlalchemy import Column, Integer, String, ForeignKey, Float, Enum
from sqlalchemy.orm import relationship
from datetime import datetime
from .database import Base
import enum


class LocationType(enum.Enum):
    """Type of element being bookmarked"""
    SPACE = "space"
    HVAC_PATH = "hvac_path"
    ROOM_BOUNDARY = "room_boundary"
    HVAC_COMPONENT = "hvac_component"


class DrawingLocation(Base):
    """Model for bookmarking element locations in drawing sets"""
    __tablename__ = 'drawing_locations'

    id = Column(Integer, primary_key=True)

    # What is being bookmarked
    location_type = Column(Enum(LocationType), nullable=False)
    element_id = Column(Integer, nullable=False)  # ID of the space/path/etc
    element_name = Column(String(255))  # Cached name for quick display

    # Where it is located
    drawing_set_id = Column(Integer, ForeignKey('drawing_sets.id'), nullable=True)
    drawing_id = Column(Integer, ForeignKey('drawings.id'), nullable=False)
    page_number = Column(Integer, default=1)

    # Visual center point for navigation (in drawing coordinates)
    center_x = Column(Float)
    center_y = Column(Float)

    # Bounding box for highlighting (optional)
    bbox_x1 = Column(Float)
    bbox_y1 = Column(Float)
    bbox_x2 = Column(Float)
    bbox_y2 = Column(Float)

    # Relationships
    drawing_set = relationship("DrawingSet")
    drawing = relationship("Drawing")

    def __repr__(self):
        return f"<DrawingLocation(type={self.location_type.value}, element_id={self.element_id}, drawing_id={self.drawing_id}, page={self.page_number})>"

    @property
    def has_bbox(self):
        """Check if this location has bounding box coordinates"""
        return all([self.bbox_x1, self.bbox_y1, self.bbox_x2, self.bbox_y2])

    def get_drawing_name(self):
        """Safely get drawing name without triggering lazy load"""
        try:
            return self.drawing.name if self.drawing else f"Drawing ID {self.drawing_id}"
        except:
            return f"Drawing ID {self.drawing_id}"

    def get_drawing_set_name(self):
        """Safely get drawing set name without triggering lazy load"""
        try:
            return self.drawing_set.name if self.drawing_set else None
        except:
            return None

    def to_dict(self):
        """Convert to dictionary for easy display"""
        return {
            'id': self.id,
            'location_type': self.location_type.value if self.location_type else None,
            'element_id': self.element_id,
            'element_name': self.element_name,
            'drawing_set_id': self.drawing_set_id,
            'drawing_id': self.drawing_id,
            'page_number': self.page_number,
            'center_x': self.center_x,
            'center_y': self.center_y,
            'has_bbox': self.has_bbox
        }

    def get_location_label(self):
        """Get a human-readable location label"""
        parts = []

        if self.drawing_set and hasattr(self.drawing_set, 'name'):
            parts.append(f"Set: {self.drawing_set.name}")

        if self.drawing and hasattr(self.drawing, 'name'):
            parts.append(f"Dwg: {self.drawing.name}")

        if self.page_number and self.page_number > 1:
            parts.append(f"Page {self.page_number}")

        return " | ".join(parts) if parts else "Unknown Location"
