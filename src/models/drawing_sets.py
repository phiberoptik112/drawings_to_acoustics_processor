"""
Models for Drawing Sets and Drawing Set Comparisons
"""

from sqlalchemy import Column, Integer, String, DateTime, Text, ForeignKey, Boolean, Float
from sqlalchemy.orm import relationship
from datetime import datetime
from .database import Base


class DrawingSet(Base):
    """Drawing set model for grouping drawings by design phase"""
    __tablename__ = 'drawing_sets'
    
    id = Column(Integer, primary_key=True)
    project_id = Column(Integer, ForeignKey('projects.id'), nullable=False)
    name = Column(String(255), nullable=False)
    phase_type = Column(String(50), nullable=False)  # 'DD', 'SD', 'CD', 'Final', 'Legacy', etc.
    description = Column(Text)
    is_active = Column(Boolean, default=False)  # Current working set
    created_date = Column(DateTime, default=datetime.utcnow)
    modified_date = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    project = relationship("Project", back_populates="drawing_sets")
    drawings = relationship("Drawing", back_populates="drawing_set")
    comparisons_base = relationship(
        "DrawingComparison",
        foreign_keys="DrawingComparison.base_set_id",
        back_populates="base_set",
    )
    comparisons_compare = relationship(
        "DrawingComparison",
        foreign_keys="DrawingComparison.compare_set_id",
        back_populates="compare_set",
    )
    material_schedules = relationship("MaterialSchedule", back_populates="drawing_set", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<DrawingSet(id={self.id}, name='{self.name}', phase='{self.phase_type}')>"
    
    def to_dict(self):
        """Convert drawing set to dictionary for JSON serialization"""
        return {
            'id': self.id,
            'project_id': self.project_id,
            'name': self.name,
            'phase_type': self.phase_type,
            'description': self.description,
            'is_active': self.is_active,
            'created_date': self.created_date.isoformat() if self.created_date else None,
            'modified_date': self.modified_date.isoformat() if self.modified_date else None,
        }


class DrawingComparison(Base):
    """Model for storing drawing set comparison results"""
    __tablename__ = 'drawing_comparisons'
    
    id = Column(Integer, primary_key=True)
    project_id = Column(Integer, ForeignKey('projects.id'), nullable=False)
    base_set_id = Column(Integer, ForeignKey('drawing_sets.id'), nullable=False)
    compare_set_id = Column(Integer, ForeignKey('drawing_sets.id'), nullable=False)
    comparison_date = Column(DateTime, default=datetime.utcnow)
    comparison_results = Column(Text)  # JSON summary of comparison results
    notes = Column(Text)
    
    # Analysis metadata
    total_changes = Column(Integer, default=0)
    critical_changes = Column(Integer, default=0)
    acoustic_impact_score = Column(Float)
    
    # Relationships
    project = relationship("Project", back_populates="drawing_comparisons")
    base_set = relationship("DrawingSet", foreign_keys=[base_set_id], back_populates="comparisons_base")
    compare_set = relationship("DrawingSet", foreign_keys=[compare_set_id], back_populates="comparisons_compare")
    change_items = relationship("ChangeItem", back_populates="comparison", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<DrawingComparison(id={self.id}, base_set={self.base_set_id}, compare_set={self.compare_set_id})>"
    
    def to_dict(self):
        """Convert drawing comparison to dictionary for JSON serialization"""
        return {
            'id': self.id,
            'project_id': self.project_id,
            'base_set_id': self.base_set_id,
            'compare_set_id': self.compare_set_id,
            'comparison_date': self.comparison_date.isoformat() if self.comparison_date else None,
            'comparison_results': self.comparison_results,
            'notes': self.notes,
            'total_changes': self.total_changes,
            'critical_changes': self.critical_changes,
            'acoustic_impact_score': self.acoustic_impact_score,
        }


class ChangeItem(Base):
    """Model for individual change items detected in comparison"""
    __tablename__ = 'change_items'
    
    id = Column(Integer, primary_key=True)
    comparison_id = Column(Integer, ForeignKey('drawing_comparisons.id'), nullable=False)
    element_type = Column(String(50), nullable=False)  # 'space', 'hvac_component', 'hvac_path', 'room_boundary'
    change_type = Column(String(50), nullable=False)   # 'added', 'removed', 'modified', 'moved'
    
    # Element references (may be null for additions/deletions)
    base_element_id = Column(Integer)  # ID in base set (null for additions)
    compare_element_id = Column(Integer)  # ID in compare set (null for deletions)
    
    # Change details stored as JSON
    change_details = Column(Text)  # Specific changes, coordinates, properties
    acoustic_impact = Column(Text)  # RT60/noise impact analysis JSON
    severity = Column(String(20), default='medium')  # 'low', 'medium', 'high', 'critical'
    
    # Position for UI display
    drawing_id = Column(Integer, ForeignKey('drawings.id'))
    x_position = Column(Float)
    y_position = Column(Float)
    
    # Change metrics
    area_change = Column(Float)  # For space changes, area difference in sq ft
    position_delta = Column(Float)  # Distance moved for repositioned elements
    
    created_date = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    comparison = relationship("DrawingComparison", back_populates="change_items")
    drawing = relationship("Drawing")
    
    def __repr__(self):
        return f"<ChangeItem(id={self.id}, type='{self.element_type}', change='{self.change_type}')>"
    
    def to_dict(self):
        """Convert change item to dictionary for JSON serialization"""
        return {
            'id': self.id,
            'comparison_id': self.comparison_id,
            'element_type': self.element_type,
            'change_type': self.change_type,
            'base_element_id': self.base_element_id,
            'compare_element_id': self.compare_element_id,
            'change_details': self.change_details,
            'acoustic_impact': self.acoustic_impact,
            'severity': self.severity,
            'drawing_id': self.drawing_id,
            'x_position': self.x_position,
            'y_position': self.y_position,
            'area_change': self.area_change,
            'position_delta': self.position_delta,
            'created_date': self.created_date.isoformat() if self.created_date else None,
        }