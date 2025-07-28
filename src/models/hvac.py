"""
HVAC models - components, paths, and segments for mechanical noise analysis
"""

from sqlalchemy import Column, Integer, String, DateTime, Text, ForeignKey, Float
from sqlalchemy.orm import relationship
from datetime import datetime
from .database import Base


class HVACComponent(Base):
    """HVAC Component model for equipment placed on drawings"""
    __tablename__ = 'hvac_components'
    
    id = Column(Integer, primary_key=True)
    project_id = Column(Integer, ForeignKey('projects.id'), nullable=False)
    drawing_id = Column(Integer, ForeignKey('drawings.id'), nullable=False)
    name = Column(String(255), nullable=False)
    component_type = Column(String(50), nullable=False)  # 'ahu', 'vav', 'diffuser', etc.
    
    # Position on drawing (pixels)
    x_position = Column(Float, nullable=False)
    y_position = Column(Float, nullable=False)
    
    # Acoustic properties
    noise_level = Column(Float)  # Base noise level in dB(A)
    
    created_date = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    project = relationship("Project", back_populates="hvac_components")
    drawing = relationship("Drawing", back_populates="hvac_components")
    segments_from = relationship("HVACSegment", foreign_keys="HVACSegment.from_component_id", back_populates="from_component")
    segments_to = relationship("HVACSegment", foreign_keys="HVACSegment.to_component_id", back_populates="to_component")
    
    def __repr__(self):
        return f"<HVACComponent(id={self.id}, name='{self.name}', type='{self.component_type}')>"


class HVACPath(Base):
    """HVAC Path model for complete air paths from source to terminal"""
    __tablename__ = 'hvac_paths'
    
    id = Column(Integer, primary_key=True)
    project_id = Column(Integer, ForeignKey('projects.id'), nullable=False)
    target_space_id = Column(Integer, ForeignKey('spaces.id'))
    name = Column(String(255), nullable=False)
    description = Column(Text)
    
    # Path type
    path_type = Column(String(50), default='supply')  # 'supply', 'return', 'exhaust'
    
    # Calculated noise
    calculated_noise = Column(Float)  # Final noise level at terminal
    calculated_nc = Column(Float)     # NC rating
    
    created_date = Column(DateTime, default=datetime.utcnow)
    modified_date = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    project = relationship("Project", back_populates="hvac_paths")
    target_space = relationship("Space", back_populates="hvac_paths")
    segments = relationship("HVACSegment", back_populates="hvac_path", cascade="all, delete-orphan", order_by="HVACSegment.segment_order")
    
    def __repr__(self):
        return f"<HVACPath(id={self.id}, name='{self.name}', type='{self.path_type}')>"


class HVACSegment(Base):
    """HVAC Segment model for connections between components"""
    __tablename__ = 'hvac_segments'
    
    id = Column(Integer, primary_key=True)
    hvac_path_id = Column(Integer, ForeignKey('hvac_paths.id'), nullable=False)
    from_component_id = Column(Integer, ForeignKey('hvac_components.id'), nullable=False)
    to_component_id = Column(Integer, ForeignKey('hvac_components.id'), nullable=False)
    
    # Segment properties
    length = Column(Float, nullable=False)  # Length in feet (calculated from drawing)
    segment_order = Column(Integer, nullable=False)  # Order in path (1, 2, 3...)
    
    # Duct properties
    duct_width = Column(Float)    # inches
    duct_height = Column(Float)   # inches
    duct_shape = Column(String(20), default='rectangular')  # 'rectangular', 'round'
    duct_type = Column(String(50), default='sheet_metal')   # Material type
    insulation = Column(String(50))  # Insulation type
    
    # Calculated losses
    distance_loss = Column(Float)    # dB loss due to distance
    duct_loss = Column(Float)        # dB loss due to duct attenuation
    fitting_additions = Column(Float) # dB addition from fittings
    
    created_date = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    hvac_path = relationship("HVACPath", back_populates="segments")
    from_component = relationship("HVACComponent", foreign_keys=[from_component_id], back_populates="segments_from")
    to_component = relationship("HVACComponent", foreign_keys=[to_component_id], back_populates="segments_to")
    fittings = relationship("SegmentFitting", back_populates="segment", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<HVACSegment(id={self.id}, path_id={self.hvac_path_id}, order={self.segment_order})>"


class SegmentFitting(Base):
    """Fittings within HVAC segments (elbows, tees, etc.)"""
    __tablename__ = 'segment_fittings'
    
    id = Column(Integer, primary_key=True)
    segment_id = Column(Integer, ForeignKey('hvac_segments.id'), nullable=False)
    fitting_type = Column(String(50), nullable=False)  # 'elbow', 'tee', 'reducer', etc.
    position_on_segment = Column(Float)  # Distance from start of segment (feet)
    noise_adjustment = Column(Float)     # +/- dB contribution
    
    # Relationships
    segment = relationship("HVACSegment", back_populates="fittings")
    
    def __repr__(self):
        return f"<SegmentFitting(id={self.id}, type='{self.fitting_type}', adjustment={self.noise_adjustment})>"