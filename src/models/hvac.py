"""
HVAC models - components, paths, and segments for mechanical noise analysis
"""

import json
from sqlalchemy import Column, Integer, String, DateTime, Text, ForeignKey, Float, Boolean
from sqlalchemy.orm import relationship
from datetime import datetime
from typing import List, Dict, Optional
from .database import Base


class HVACComponent(Base):
    """HVAC Component model for equipment placed on drawings"""
    __tablename__ = 'hvac_components'
    
    id = Column(Integer, primary_key=True)
    project_id = Column(Integer, ForeignKey('projects.id'), nullable=False)
    drawing_id = Column(Integer, ForeignKey('drawings.id'), nullable=False)
    name = Column(String(255), nullable=False)
    component_type = Column(String(50), nullable=False)  # 'ahu', 'vav', 'diffuser', 'custom', etc.
    custom_type_label = Column(String(100))  # User-defined label when component_type='custom'
    
    # Position on drawing (pixels)
    x_position = Column(Float, nullable=False)
    y_position = Column(Float, nullable=False)
    
    # Page number for multi-page PDFs (nullable for backward compatibility with existing data)
    page_number = Column(Integer, default=1)
    
    # Acoustic properties
    noise_level = Column(Float)  # Base noise level in dB(A)
    cfm = Column(Float)  # Air flow rate in CFM
    # Junction behavior preferences (component-level)
    # For components acting as 90° branch takeoffs, allow user override of which
    # junction spectrum to use in path calculations: 'auto' | 'main' | 'branch'
    branch_takeoff_choice = Column(String(20))
    
    # Elbow-specific fields (turning vanes and lining)
    has_turning_vanes = Column(Boolean, default=False)
    vane_chord_length = Column(Float)  # Chord length of typical vane (inches)
    num_vanes = Column(Integer)  # Number of turning vanes
    lining_thickness = Column(Float)  # Lining thickness (inches)
    pressure_drop = Column(Float)  # Pressure drop across elbow (in. w.g.)
    
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
    
    def to_dict(self):
        """Convert component to dictionary for JSON serialization"""
        return {
            'id': self.id,
            'project_id': self.project_id,
            'drawing_id': self.drawing_id,
            'page_number': self.page_number,
            'name': self.name,
            'component_type': self.component_type,
            'custom_type_label': self.custom_type_label,
            'x_position': self.x_position,
            'y_position': self.y_position,
            'noise_level': self.noise_level,
            'cfm': self.cfm,
            'branch_takeoff_choice': self.branch_takeoff_choice,
            'has_turning_vanes': self.has_turning_vanes,
            'vane_chord_length': self.vane_chord_length,
            'num_vanes': self.num_vanes,
            'lining_thickness': self.lining_thickness,
            'pressure_drop': self.pressure_drop,
            'is_silencer': self.is_silencer,
            'silencer_type': self.silencer_type,
            'target_noise_reduction': self.target_noise_reduction,
            'frequency_requirements': self.frequency_requirements,
            'space_constraints': self.space_constraints,
            'selected_product_id': self.selected_product_id,
            'created_date': self.created_date.isoformat() if self.created_date else None,
        }


class HVACPath(Base):
    """HVAC Path model for complete air paths from source to terminal"""
    __tablename__ = 'hvac_paths'
    
    id = Column(Integer, primary_key=True)
    project_id = Column(Integer, ForeignKey('projects.id'), nullable=False)
    target_space_id = Column(Integer, ForeignKey('spaces.id'))
    primary_source_id = Column(Integer, ForeignKey('hvac_components.id'))  # Optional selection of source component
    drawing_set_id = Column(Integer, ForeignKey('drawing_sets.id'), nullable=True)  # Drawing set association
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
    
    # Element sequence - JSON storing the ordered sequence of components and segments
    # Format: [{"type": "component", "id": 1}, {"type": "segment", "id": 1}, {"type": "component", "id": 2}, ...]
    element_sequence = Column(Text, nullable=True)
    
    # Relationships
    project = relationship("Project", back_populates="hvac_paths")
    target_space = relationship("Space", back_populates="hvac_paths")
    primary_source = relationship("HVACComponent")
    drawing_set = relationship("DrawingSet")
    segments = relationship("HVACSegment", back_populates="hvac_path", cascade="all, delete-orphan", order_by="HVACSegment.segment_order")
    placement_analyses = relationship("SilencerPlacementAnalysis", back_populates="hvac_path", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<HVACPath(id={self.id}, name='{self.name}', type='{self.path_type}')>"

    def get_drawing_locations(self):
        """Get all drawing locations where this HVAC path appears"""
        from models import get_session
        from models.drawing_location import DrawingLocation, LocationType
        from sqlalchemy.orm import joinedload

        session = get_session()
        try:
            locations = (
                session.query(DrawingLocation)
                .options(
                    joinedload(DrawingLocation.drawing_set),
                    joinedload(DrawingLocation.drawing)
                )
                .filter(
                    DrawingLocation.location_type == LocationType.HVAC_PATH,
                    DrawingLocation.element_id == self.id
                )
                .all()
            )
            return locations
        finally:
            session.close()

    def get_primary_location_label(self):
        """Get a summary of where this HVAC path is located"""
        locations = self.get_drawing_locations()

        if not locations:
            # Try to derive from segments using a fresh session to avoid detached instance errors
            # Only attempt if path has been saved (has an id)
            if self.id:
                try:
                    from models import get_session
                    from sqlalchemy.orm import joinedload
                    
                    session = get_session()
                    try:
                        # Query segments with component and drawing relationships eagerly loaded
                        first_seg = (
                            session.query(HVACSegment)
                            .options(
                                joinedload(HVACSegment.from_component).joinedload(HVACComponent.drawing)
                            )
                            .filter(HVACSegment.hvac_path_id == self.id)
                            .order_by(HVACSegment.segment_order)
                            .first()
                        )
                        
                        if first_seg and first_seg.from_component:
                            comp = first_seg.from_component
                            if comp.drawing:
                                return f"Dwg: {comp.drawing.name}"
                    finally:
                        session.close()
                except Exception:
                    # If session query fails, fall through to drawing_set fallback
                    pass

            if self.drawing_set:
                return f"Set: {self.drawing_set.name}" if hasattr(self.drawing_set, 'name') else "In drawing set"

            return "No location"

        # Return first location's label
        return locations[0].get_location_label()
    
    def to_dict(self):
        """Convert path to dictionary for JSON serialization"""
        return {
            'id': self.id,
            'project_id': self.project_id,
            'target_space_id': self.target_space_id,
            'primary_source_id': self.primary_source_id,
            'drawing_set_id': self.drawing_set_id,
            'name': self.name,
            'description': self.description,
            'path_type': self.path_type,
            'calculated_noise': self.calculated_noise,
            'calculated_nc': self.calculated_nc,
            'created_date': self.created_date.isoformat() if self.created_date else None,
            'modified_date': self.modified_date.isoformat() if self.modified_date else None,
            'receiver_distance_ft': self.receiver_distance_ft,
            'receiver_method': self.receiver_method,
            'element_sequence': self.element_sequence,
        }

    def get_element_sequence(self) -> List[Dict]:
        """
        Returns the ordered element sequence.
        If an explicit sequence is stored, returns it.
        Otherwise, computes the sequence from segment connectivity.
        """
        if self.element_sequence:
            try:
                return json.loads(self.element_sequence)
            except (json.JSONDecodeError, TypeError):
                pass
        return self._compute_sequence_from_segments()

    def set_element_sequence(self, sequence: List[Dict]):
        """
        Sets the element sequence from a list of dictionaries.
        Each dict should have 'type' ('component' or 'segment') and 'id' keys.
        """
        if sequence:
            self.element_sequence = json.dumps(sequence)
        else:
            self.element_sequence = None

    def _compute_sequence_from_segments(self) -> List[Dict]:
        """
        Builds element sequence from segment connectivity.
        Returns a list alternating between components and segments:
        [component, segment, component, segment, component, ...]
        """
        if not self.segments:
            return []
        
        sequence = []
        ordered_segments = sorted(self.segments, key=lambda s: s.segment_order or 0)
        
        seen_component_ids = set()
        
        for i, seg in enumerate(ordered_segments):
            # Add the from_component if not already added
            if seg.from_component_id and seg.from_component_id not in seen_component_ids:
                sequence.append({"type": "component", "id": seg.from_component_id})
                seen_component_ids.add(seg.from_component_id)
            
            # Add the segment
            sequence.append({"type": "segment", "id": seg.id})
            
            # Add the to_component if not already added
            if seg.to_component_id and seg.to_component_id not in seen_component_ids:
                sequence.append({"type": "component", "id": seg.to_component_id})
                seen_component_ids.add(seg.to_component_id)
        
        return sequence

    def get_ordered_components(self) -> List['HVACComponent']:
        """
        Returns components in their sequence order.
        Uses explicit sequence if available, otherwise computes from segments.
        """
        sequence = self.get_element_sequence()
        component_ids = [item['id'] for item in sequence if item.get('type') == 'component']
        
        # Build a map of component_id -> component for efficient lookup
        component_map = {}
        for seg in self.segments:
            if seg.from_component and seg.from_component.id not in component_map:
                component_map[seg.from_component.id] = seg.from_component
            if seg.to_component and seg.to_component.id not in component_map:
                component_map[seg.to_component.id] = seg.to_component
        
        # Return components in sequence order
        return [component_map[cid] for cid in component_ids if cid in component_map]

    def get_ordered_segments(self) -> List['HVACSegment']:
        """
        Returns segments in their sequence order.
        Uses explicit sequence if available, otherwise uses segment_order.
        """
        sequence = self.get_element_sequence()
        segment_ids = [item['id'] for item in sequence if item.get('type') == 'segment']
        
        if not segment_ids:
            # Fall back to segment_order
            return sorted(self.segments, key=lambda s: s.segment_order or 0)
        
        # Build a map of segment_id -> segment for efficient lookup
        segment_map = {seg.id: seg for seg in self.segments}
        
        # Return segments in sequence order
        return [segment_map[sid] for sid in segment_ids if sid in segment_map]

    def update_sequence_from_segments(self):
        """
        Recomputes and saves the element sequence from current segment connectivity.
        Call this after modifying segments to keep the sequence in sync.
        """
        sequence = self._compute_sequence_from_segments()
        self.set_element_sequence(sequence)

    def reorder_element(self, element_type: str, element_id: int, new_position: int) -> bool:
        """
        Moves an element to a new position in the sequence.
        Returns True if successful, False if the move would break connectivity.
        
        Note: For maintaining connectivity, components should stay adjacent to their
        connected segments. This method performs basic validation.
        """
        sequence = self.get_element_sequence()
        
        # Find current position
        current_pos = None
        for i, item in enumerate(sequence):
            if item.get('type') == element_type and item.get('id') == element_id:
                current_pos = i
                break
        
        if current_pos is None:
            return False
        
        # Remove from current position
        item = sequence.pop(current_pos)
        
        # Adjust new_position if needed after removal
        if new_position > current_pos:
            new_position -= 1
        
        # Clamp to valid range
        new_position = max(0, min(len(sequence), new_position))
        
        # Insert at new position
        sequence.insert(new_position, item)
        
        # Save the updated sequence
        self.set_element_sequence(sequence)
        return True

    def swap_elements(self, pos1: int, pos2: int) -> bool:
        """
        Swaps two elements in the sequence by position.
        Returns True if successful.
        """
        sequence = self.get_element_sequence()
        
        if pos1 < 0 or pos1 >= len(sequence) or pos2 < 0 or pos2 >= len(sequence):
            return False
        
        sequence[pos1], sequence[pos2] = sequence[pos2], sequence[pos1]
        self.set_element_sequence(sequence)
        return True


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
    
    def to_dict(self):
        """Convert segment to dictionary for JSON serialization"""
        return {
            'id': self.id,
            'hvac_path_id': self.hvac_path_id,
            'from_component_id': self.from_component_id,
            'to_component_id': self.to_component_id,
            'length': self.length,
            'segment_order': self.segment_order,
            'duct_width': self.duct_width,
            'duct_height': self.duct_height,
            'diameter': self.diameter,
            'duct_shape': self.duct_shape,
            'duct_type': self.duct_type,
            'insulation': self.insulation,
            'lining_thickness': self.lining_thickness,
            'flow_rate': self.flow_rate,
            'flow_velocity': self.flow_velocity,
            'distance_loss': self.distance_loss,
            'duct_loss': self.duct_loss,
            'fitting_additions': self.fitting_additions,
            'created_date': self.created_date.isoformat() if self.created_date else None,
        }


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
    
    def to_dict(self):
        """Convert fitting to dictionary for JSON serialization"""
        return {
            'id': self.id,
            'segment_id': self.segment_id,
            'fitting_type': self.fitting_type,
            'quantity': self.quantity,
            'position_on_segment': self.position_on_segment,
            'noise_adjustment': self.noise_adjustment,
        }


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
    
    def to_dict(self):
        """Convert receiver result to dictionary for JSON serialization"""
        return {
            'id': self.id,
            'space_id': self.space_id,
            'calculation_date': self.calculation_date.isoformat() if self.calculation_date else None,
            'target_nc': self.target_nc,
            'nc_rating': self.nc_rating,
            'total_dba': self.total_dba,
            'meets_target': self.meets_target,
            'lp_63': self.lp_63,
            'lp_125': self.lp_125,
            'lp_250': self.lp_250,
            'lp_500': self.lp_500,
            'lp_1000': self.lp_1000,
            'lp_2000': self.lp_2000,
            'lp_4000': self.lp_4000,
            'room_volume': self.room_volume,
            'distributed_ceiling_height': self.distributed_ceiling_height,
            'distributed_floor_area_per_diffuser': self.distributed_floor_area_per_diffuser,
            'path_parameters_json': self.path_parameters_json,
        }