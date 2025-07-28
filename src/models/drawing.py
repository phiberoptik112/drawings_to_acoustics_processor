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
    room_boundaries = relationship("RoomBoundary", back_populates="drawing", cascade="all, delete-orphan")
    hvac_components = relationship("HVACComponent", back_populates="drawing", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<Drawing(id={self.id}, name='{self.name}', project_id={self.project_id})>"
    
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
            'height_pixels': self.height_pixels
        }