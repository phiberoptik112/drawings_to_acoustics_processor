"""
Drawing model - represents PDF drawings in a project
"""

from sqlalchemy import Column, Integer, String, DateTime, Text, ForeignKey, Float
from sqlalchemy.orm import relationship
from datetime import datetime
from .database import Base


class Drawing(Base):
    """Drawing model for storing PDF drawings and their properties"""
    __tablename__ = 'drawings'
    
    id = Column(Integer, primary_key=True)
    project_id = Column(Integer, ForeignKey('projects.id'), nullable=False)
    name = Column(String(255), nullable=False)
    description = Column(Text)
    file_path = Column(String(1000), nullable=False)  # Path to PDF file
    
    # Scale information
    scale_ratio = Column(Float)  # Pixels per real-world unit
    scale_string = Column(String(50))  # e.g., "1:100"
    
    # Drawing properties
    page_number = Column(Integer, default=1)  # For multi-page PDFs
    width_pixels = Column(Float)   # PDF page width in pixels
    height_pixels = Column(Float)  # PDF page height in pixels
    
    created_date = Column(DateTime, default=datetime.utcnow)
    modified_date = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    project = relationship("Project", back_populates="drawings")
    spaces = relationship("Space", back_populates="drawing")  # Direct relationship to spaces
    room_boundaries = relationship("RoomBoundary", back_populates="drawing", cascade="all, delete-orphan")
    hvac_components = relationship("HVACComponent", back_populates="drawing", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<Drawing(id={self.id}, name='{self.name}', project_id={self.project_id})>"
    
    def get_space_count(self):
        """Get the number of spaces on this drawing"""
        return len(self.spaces)
    
    def get_space_names(self):
        """Get list of space names on this drawing"""
        return [space.name for space in self.spaces]
    
    def get_spaces_with_boundaries(self):
        """Get spaces that have room boundaries on this drawing"""
        spaces_with_boundaries = []
        for space in self.spaces:
            if space.get_room_boundaries_on_drawing(self.id):
                spaces_with_boundaries.append(space)
        return spaces_with_boundaries
    
    def to_dict(self):
        """Convert drawing to dictionary"""
        return {
            'id': self.id,
            'project_id': self.project_id,
            'name': self.name,
            'description': self.description,
            'file_path': self.file_path,
            'scale_ratio': self.scale_ratio,
            'scale_string': self.scale_string,
            'page_number': self.page_number,
            'width_pixels': self.width_pixels,
            'height_pixels': self.height_pixels,
            'space_count': self.get_space_count(),
            'space_names': self.get_space_names()
        }