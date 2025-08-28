"""
HVAC models - components, paths, and segments for mechanical noise analysis
"""

from sqlalchemy import Column, Integer, String, DateTime, Text, ForeignKey, Float, Boolean
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
    cfm = Column(Float)  # Air flow rate in CFM
    
    # Silencer-specific fields
    is_silencer = Column(Boolean, default=False)
    silencer_type = Column(String(50))  # 'reactive', 'dissipative', 'hybrid'
    target_noise_reduction = Column(Float)  # dB reduction target
    frequency_requirements = Column(Text)   # JSON frequency band requirements
    space_constraints = Column(Text)        # JSON space limitations
    selected_product_id = Column(Integer, ForeignKey('silencer_products.id'))
    
    created_date = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    project = relationship("Project", back_populates="hvac_components")
    drawing = relationship("Drawing", back_populates="hvac_components")
    segments_from = relationship("HVACSegment", foreign_keys="HVACSegment.from_component_id", back_populates="from_component")
    segments_to = relationship("HVACSegment", foreign_keys="HVACSegment.to_component_id", back_populates="to_component")
    selected_product = relationship("SilencerProduct", back_populates="components")
    
    def __repr__(self):
        return f"<HVACComponent(id={self.id}, name='{self.name}', type='{self.component_type}')>"


class HVACPath(Base):
    """HVAC Path model for complete air paths from source to terminal"""
    __tablename__ = 'hvac_paths'
    
    id = Column(Integer, primary_key=True)
    project_id = Column(Integer, ForeignKey('projects.id'), nullable=False)
    target_space_id = Column(Integer, ForeignKey('spaces.id'))
    primary_source_id = Column(Integer, ForeignKey('hvac_components.id'))  # Optional selection of source component
    name = Column(String(255), nullable=False)
    description = Column(Text)
    
    # Path type
    path_type = Column(String(50), default='supply')  # 'supply', 'return', 'exhaust'
    
    # Calculated noise
    calculated_noise = Column(Float)  # Final noise level at terminal
    calculated_nc = Column(Float)     # NC rating
    
    created_date = Column(DateTime, default=datetime.utcnow)
    modified_date = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Receiver analysis preferences (per-path)
    receiver_distance_ft = Column(Float)  # Preferred receiver distance (ft) for Eq27
    receiver_method = Column(String(50))  # 'single' or 'distributed'
    
    # Relationships
    project = relationship("Project", back_populates="hvac_paths")
    target_space = relationship("Space", back_populates="hvac_paths")
    primary_source = relationship("HVACComponent")
    segments = relationship("HVACSegment", back_populates="hvac_path", cascade="all, delete-orphan", order_by="HVACSegment.segment_order")
    placement_analyses = relationship("SilencerPlacementAnalysis", back_populates="hvac_path", cascade="all, delete-orphan")
    
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
    duct_width = Column(Float)    # inches (rectangular width or circular diameter fallback)
    duct_height = Column(Float)   # inches (rectangular height)
    diameter = Column(Float)      # inches (circular)
    duct_shape = Column(String(20), default='rectangular')  # 'rectangular', 'round'
    duct_type = Column(String(50), default='sheet_metal')   # Material type
    insulation = Column(String(50))  # Lining material type
    lining_thickness = Column(Float) # Lining thickness in inches
    
    # Flow properties
    flow_rate = Column(Float)        # CFM flow rate through segment
    flow_velocity = Column(Float)    # FPM velocity through segment
    
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
    quantity = Column(Integer, default=1)
    position_on_segment = Column(Float)  # Distance from start of segment (feet)
    noise_adjustment = Column(Float)     # +/- dB contribution
    
    # Relationships
    segment = relationship("HVACSegment", back_populates="fittings")
    
    def __repr__(self):
        return f"<SegmentFitting(id={self.id}, type='{self.fitting_type}', adjustment={self.noise_adjustment})>"


class SilencerProduct(Base):
    """Model for silencer product database"""
    __tablename__ = 'silencer_products'
    
    id = Column(Integer, primary_key=True)
    manufacturer = Column(String(100), nullable=False)
    model_number = Column(String(100), nullable=False)
    silencer_type = Column(String(50), nullable=False)  # 'reactive', 'dissipative', 'hybrid'
    
    # Physical specifications
    length = Column(Float)  # inches
    width = Column(Float)   # inches
    height = Column(Float)  # inches
    weight = Column(Float)  # lbs
    
    # Performance specifications
    flow_rate_min = Column(Float)  # CFM
    flow_rate_max = Column(Float)  # CFM
    velocity_max = Column(Float)   # FPM
    
    # Insertion loss by frequency band (8-band)
    insertion_loss_63 = Column(Float)
    insertion_loss_125 = Column(Float)
    insertion_loss_250 = Column(Float)
    insertion_loss_500 = Column(Float)
    insertion_loss_1000 = Column(Float)
    insertion_loss_2000 = Column(Float)
    insertion_loss_4000 = Column(Float)
    insertion_loss_8000 = Column(Float)
    
    # Cost information
    cost_estimate = Column(Float)  # USD
    availability = Column(String(50))  # 'in_stock', 'lead_time', 'discontinued'
    
    created_date = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    components = relationship("HVACComponent", back_populates="selected_product")
    
    def __repr__(self):
        return f"<SilencerProduct(id={self.id}, manufacturer='{self.manufacturer}', model='{self.model_number}')>"


class SilencerPlacementAnalysis(Base):
    """Model for storing silencer placement analysis results"""
    __tablename__ = 'silencer_placement_analyses'
    
    id = Column(Integer, primary_key=True)
    path_id = Column(Integer, ForeignKey('hvac_paths.id'), nullable=False)
    
    # Analysis results
    critical_points = Column(Text)  # JSON critical noise points
    recommendations = Column(Text)  # JSON silencer recommendations
    frequency_analysis = Column(Text) # JSON frequency band analysis
    
    created_date = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    hvac_path = relationship("HVACPath", back_populates="placement_analyses")
    
    def __repr__(self):
        return f"<SilencerPlacementAnalysis(id={self.id}, path_id={self.path_id})>"


class HVACReceiverResult(Base):
    """Per-space HVAC receiver background noise results.

    Stores the combined 7-band sound pressure level at the receiver, along with
    NC rating and calculation parameters used by the receiver dialog.
    """
    __tablename__ = 'hvac_receiver_results'

    id = Column(Integer, primary_key=True)
    space_id = Column(Integer, ForeignKey('spaces.id'), nullable=False)
    calculation_date = Column(DateTime, default=datetime.utcnow)

    # Overall results
    target_nc = Column(Float)
    nc_rating = Column(Float)
    total_dba = Column(Float)
    meets_target = Column(Boolean, default=False)

    # Receiver spectrum (7 bands: 63..4000 Hz)
    lp_63 = Column(Float, default=0.0)
    lp_125 = Column(Float, default=0.0)
    lp_250 = Column(Float, default=0.0)
    lp_500 = Column(Float, default=0.0)
    lp_1000 = Column(Float, default=0.0)
    lp_2000 = Column(Float, default=0.0)
    lp_4000 = Column(Float, default=0.0)

    # Parameters used
    room_volume = Column(Float)
    distributed_ceiling_height = Column(Float)
    distributed_floor_area_per_diffuser = Column(Float)
    path_parameters_json = Column(Text)  # JSON: [{path_id, method, distance_ft}, ...]

    # Relationships
    space = relationship("Space", back_populates="receiver_results")

    def __repr__(self):
        return (
            f"<HVACReceiverResult(id={self.id}, space_id={self.space_id}, "
            f"nc={self.nc_rating}, dBA={self.total_dba})>"
        )