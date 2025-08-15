"""
Project model - represents an acoustic analysis project
"""

from sqlalchemy import Column, Integer, String, DateTime, Text
from sqlalchemy.orm import relationship
from datetime import datetime
from .database import Base


class Project(Base):
    """Project model for storing acoustic analysis projects"""
    __tablename__ = 'projects'
    
    id = Column(Integer, primary_key=True)
    name = Column(String(255), nullable=False)
    description = Column(Text)
    location = Column(String(500))  # File system path
    created_date = Column(DateTime, default=datetime.utcnow)
    modified_date = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Default settings
    default_scale = Column(String(50), default="1:100")  # e.g., "1:100"
    default_units = Column(String(20), default="feet")   # "feet" or "meters"
    
    # Relationships
    drawings = relationship("Drawing", back_populates="project", cascade="all, delete-orphan")
    spaces = relationship("Space", back_populates="project", cascade="all, delete-orphan")
    hvac_paths = relationship("HVACPath", back_populates="project", cascade="all, delete-orphan")
    hvac_components = relationship("HVACComponent", back_populates="project", cascade="all, delete-orphan")
    # New: project-level mechanical schedule and noise sources
    mechanical_units = relationship("MechanicalUnit", back_populates="project", cascade="all, delete-orphan")
    noise_sources = relationship("NoiseSource", back_populates="project", cascade="all, delete-orphan")
    # Drawing sets and comparisons
    drawing_sets = relationship("DrawingSet", back_populates="project", cascade="all, delete-orphan")
    drawing_comparisons = relationship("DrawingComparison", back_populates="project", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<Project(id={self.id}, name='{self.name}')>"
    
    def to_dict(self):
        """Convert project to dictionary for JSON serialization"""
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'location': self.location,
            'created_date': self.created_date.isoformat() if self.created_date else None,
            'modified_date': self.modified_date.isoformat() if self.modified_date else None,
            'default_scale': self.default_scale,
            'default_units': self.default_units
        }