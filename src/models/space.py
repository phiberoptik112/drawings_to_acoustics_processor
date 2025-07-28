"""
Space model - represents rooms/spaces for acoustic analysis
"""

from sqlalchemy import Column, Integer, String, DateTime, Text, ForeignKey, Float
from sqlalchemy.orm import relationship
from datetime import datetime
from .database import Base


class Space(Base):
    """Space model for storing room/space information"""
    __tablename__ = 'spaces'
    
    id = Column(Integer, primary_key=True)
    project_id = Column(Integer, ForeignKey('projects.id'), nullable=False)
    name = Column(String(255), nullable=False)
    description = Column(Text)
    
    # Geometry (calculated from drawing)
    floor_area = Column(Float)      # square feet
    ceiling_height = Column(Float)  # feet
    volume = Column(Float)          # cubic feet
    wall_area = Column(Float)       # square feet (calculated)
    
    # Acoustic properties
    target_rt60 = Column(Float, default=0.8)     # Target RT60 in seconds
    calculated_rt60 = Column(Float)              # Calculated RT60
    
    # Surface materials (for RT60 calculation)
    ceiling_material = Column(String(100))
    wall_material = Column(String(100))
    floor_material = Column(String(100))
    
    # HVAC noise
    calculated_nc = Column(Float)  # Calculated NC rating
    
    created_date = Column(DateTime, default=datetime.utcnow)
    modified_date = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    project = relationship("Project", back_populates="spaces")
    room_boundaries = relationship("RoomBoundary", back_populates="space", cascade="all, delete-orphan")
    hvac_paths = relationship("HVACPath", back_populates="target_space")
    
    def __repr__(self):
        return f"<Space(id={self.id}, name='{self.name}', project_id={self.project_id})>"
    
    def calculate_volume(self):
        """Calculate volume from floor area and ceiling height"""
        if self.floor_area and self.ceiling_height:
            self.volume = self.floor_area * self.ceiling_height
    
    def calculate_wall_area(self, perimeter):
        """Calculate wall area from perimeter and ceiling height"""
        if perimeter and self.ceiling_height:
            self.wall_area = perimeter * self.ceiling_height
    
    def to_dict(self):
        """Convert space to dictionary"""
        return {
            'id': self.id,
            'project_id': self.project_id,
            'name': self.name,
            'description': self.description,
            'floor_area': self.floor_area,
            'ceiling_height': self.ceiling_height,
            'volume': self.volume,
            'wall_area': self.wall_area,
            'target_rt60': self.target_rt60,
            'calculated_rt60': self.calculated_rt60,
            'ceiling_material': self.ceiling_material,
            'wall_material': self.wall_material,
            'floor_material': self.floor_material,
            'calculated_nc': self.calculated_nc
        }


class RoomBoundary(Base):
    """Room boundary model for storing rectangle boundaries on drawings"""
    __tablename__ = 'room_boundaries'
    
    id = Column(Integer, primary_key=True)
    space_id = Column(Integer, ForeignKey('spaces.id'), nullable=False)
    drawing_id = Column(Integer, ForeignKey('drawings.id'), nullable=False)
    
    # Rectangle coordinates in drawing pixels
    x_position = Column(Float, nullable=False)  # Top-left X
    y_position = Column(Float, nullable=False)  # Top-left Y
    width = Column(Float, nullable=False)       # Width in pixels
    height = Column(Float, nullable=False)      # Height in pixels
    
    # Calculated real-world dimensions
    calculated_area = Column(Float)  # Square feet based on scale
    
    # Relationships
    space = relationship("Space", back_populates="room_boundaries")
    drawing = relationship("Drawing", back_populates="room_boundaries")
    
    def __repr__(self):
        return f"<RoomBoundary(id={self.id}, space_id={self.space_id}, drawing_id={self.drawing_id})>"