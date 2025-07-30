"""
Enhanced RT60 calculation models - Surface management and frequency-dependent analysis
"""

from sqlalchemy import Column, Integer, String, DateTime, Text, ForeignKey, Float, Boolean
from sqlalchemy.orm import relationship
from datetime import datetime
from .database import Base


class SurfaceCategory(Base):
    """Surface categories for organized material selection"""
    __tablename__ = 'surface_categories'
    
    id = Column(Integer, primary_key=True)
    name = Column(String(50), nullable=False, unique=True)  # 'walls', 'ceilings', 'floors', etc.
    description = Column(Text)
    created_date = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    surface_types = relationship("SurfaceType", back_populates="category")
    acoustic_materials = relationship("AcousticMaterial", back_populates="category")
    
    def __repr__(self):
        return f"<SurfaceCategory(id={self.id}, name='{self.name}')>"


class SurfaceType(Base):
    """Surface types within categories (Primary Wall, Secondary Wall, etc.)"""
    __tablename__ = 'surface_types'
    
    id = Column(Integer, primary_key=True)
    name = Column(String(100), nullable=False)  # 'Primary Wall', 'Secondary Wall', etc.
    category_id = Column(Integer, ForeignKey('surface_categories.id'), nullable=False)
    default_calculation_method = Column(String(50), default='perimeter_height')  # 'perimeter_height', 'manual', 'percentage'
    description = Column(Text)
    created_date = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    category = relationship("SurfaceCategory", back_populates="surface_types")
    surface_instances = relationship("RoomSurfaceInstance", back_populates="surface_type")
    
    def __repr__(self):
        return f"<SurfaceType(id={self.id}, name='{self.name}', category_id={self.category_id})>"


class AcousticMaterial(Base):
    """Enhanced acoustic materials with frequency-dependent absorption coefficients"""
    __tablename__ = 'acoustic_materials'
    
    id = Column(Integer, primary_key=True)
    name = Column(String(200), nullable=False)
    category_id = Column(Integer, ForeignKey('surface_categories.id'))
    manufacturer = Column(String(200))
    product_code = Column(String(100))
    description = Column(Text)
    
    # Frequency-dependent absorption coefficients
    absorption_125 = Column(Float, default=0.0)
    absorption_250 = Column(Float, default=0.0)
    absorption_500 = Column(Float, default=0.0)
    absorption_1000 = Column(Float, default=0.0)
    absorption_2000 = Column(Float, default=0.0)
    absorption_4000 = Column(Float, default=0.0)
    
    # Calculated NRC (Noise Reduction Coefficient)
    nrc = Column(Float, default=0.0)
    
    # Material properties
    mounting_type = Column(String(50))  # 'direct', 'suspended', 'spaced'
    thickness = Column(String(50))
    source = Column(String(200))  # Data source reference
    
    # Metadata
    import_date = Column(DateTime, default=datetime.utcnow)
    created_date = Column(DateTime, default=datetime.utcnow)
    modified_date = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    category = relationship("SurfaceCategory", back_populates="acoustic_materials")
    surface_instances = relationship("RoomSurfaceInstance", back_populates="material")
    
    def __repr__(self):
        return f"<AcousticMaterial(id={self.id}, name='{self.name}', nrc={self.nrc})>"
    
    def calculate_nrc(self):
        """Calculate NRC from frequency coefficients (250, 500, 1000, 2000 Hz average)"""
        if all([self.absorption_250 is not None, self.absorption_500 is not None,
                self.absorption_1000 is not None, self.absorption_2000 is not None]):
            self.nrc = round((self.absorption_250 + self.absorption_500 + 
                            self.absorption_1000 + self.absorption_2000) / 4, 2)
        return self.nrc
    
    def get_absorption_by_frequency(self, frequency):
        """Get absorption coefficient for specific frequency"""
        freq_map = {
            125: self.absorption_125,
            250: self.absorption_250,
            500: self.absorption_500,
            1000: self.absorption_1000,
            2000: self.absorption_2000,
            4000: self.absorption_4000
        }
        return freq_map.get(frequency, 0.0)
    
    def to_dict(self):
        """Convert to dictionary for API/JSON serialization"""
        return {
            'id': self.id,
            'name': self.name,
            'category_id': self.category_id,
            'manufacturer': self.manufacturer,
            'product_code': self.product_code,
            'description': self.description,
            'absorption_coefficients': {
                125: self.absorption_125,
                250: self.absorption_250,
                500: self.absorption_500,
                1000: self.absorption_1000,
                2000: self.absorption_2000,
                4000: self.absorption_4000
            },
            'nrc': self.nrc,
            'mounting_type': self.mounting_type,
            'thickness': self.thickness,
            'source': self.source
        }


class RoomSurfaceInstance(Base):
    """Individual surface instances within rooms (multiple instances per surface type)"""
    __tablename__ = 'room_surface_instances'
    
    id = Column(Integer, primary_key=True)
    space_id = Column(Integer, ForeignKey('spaces.id'), nullable=False)
    surface_type_id = Column(Integer, ForeignKey('surface_types.id'), nullable=False)
    material_id = Column(Integer, ForeignKey('acoustic_materials.id'))
    
    # Instance identification
    instance_name = Column(String(200), nullable=False)  # 'Primary Wall #1', 'Primary Wall #2', etc.
    instance_number = Column(Integer, default=1)
    
    # Area calculations
    calculated_area = Column(Float, default=0.0)  # Auto-calculated area
    manual_area = Column(Float, default=0.0)      # User override area
    use_manual_area = Column(Boolean, default=False)
    area_calculation_notes = Column(Text)
    
    # Metadata
    created_date = Column(DateTime, default=datetime.utcnow)
    modified_date = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    space = relationship("Space", back_populates="surface_instances")
    surface_type = relationship("SurfaceType", back_populates="surface_instances")
    material = relationship("AcousticMaterial", back_populates="surface_instances")
    
    def __repr__(self):
        return f"<RoomSurfaceInstance(id={self.id}, space_id={self.space_id}, name='{self.instance_name}')>"
    
    @property
    def effective_area(self):
        """Get the effective area (manual override or calculated)"""
        return self.manual_area if self.use_manual_area else self.calculated_area
    
    def calculate_absorption_by_frequency(self, frequency):
        """Calculate absorption for this surface at specific frequency"""
        if not self.material:
            return 0.0
        
        absorption_coeff = self.material.get_absorption_by_frequency(frequency)
        return self.effective_area * absorption_coeff
    
    def to_dict(self):
        """Convert to dictionary"""
        return {
            'id': self.id,
            'space_id': self.space_id,
            'surface_type_id': self.surface_type_id,
            'material_id': self.material_id,
            'instance_name': self.instance_name,
            'instance_number': self.instance_number,
            'calculated_area': self.calculated_area,
            'manual_area': self.manual_area,
            'use_manual_area': self.use_manual_area,
            'effective_area': self.effective_area,
            'area_calculation_notes': self.area_calculation_notes,
            'surface_type_name': self.surface_type.name if self.surface_type else None,
            'material_name': self.material.name if self.material else None
        }


class RT60CalculationResult(Base):
    """Enhanced RT60 calculation results with frequency analysis and target tracking"""
    __tablename__ = 'rt60_calculation_results'
    
    id = Column(Integer, primary_key=True)
    space_id = Column(Integer, ForeignKey('spaces.id'), nullable=False)
    calculation_date = Column(DateTime, default=datetime.utcnow)
    
    # Target parameters
    target_rt60 = Column(Float, default=0.8)
    target_tolerance = Column(Float, default=0.1)
    room_type = Column(String(100))  # 'conference', 'office', 'classroom', etc.
    leed_compliance_required = Column(Boolean, default=False)
    
    # Calculation method
    calculation_method = Column(String(50), default='sabine')  # 'sabine' or 'eyring'
    room_volume = Column(Float)
    
    # Total absorption by frequency (sabins)
    total_sabines_125 = Column(Float, default=0.0)
    total_sabines_250 = Column(Float, default=0.0)
    total_sabines_500 = Column(Float, default=0.0)
    total_sabines_1000 = Column(Float, default=0.0)
    total_sabines_2000 = Column(Float, default=0.0)
    total_sabines_4000 = Column(Float, default=0.0)
    
    # Calculated RT60 by frequency (seconds)
    rt60_125 = Column(Float, default=0.0)
    rt60_250 = Column(Float, default=0.0)
    rt60_500 = Column(Float, default=0.0)
    rt60_1000 = Column(Float, default=0.0)
    rt60_2000 = Column(Float, default=0.0)
    rt60_4000 = Column(Float, default=0.0)
    
    # Target compliance by frequency
    meets_target_125 = Column(Boolean, default=False)
    meets_target_250 = Column(Boolean, default=False)
    meets_target_500 = Column(Boolean, default=False)
    meets_target_1000 = Column(Boolean, default=False)
    meets_target_2000 = Column(Boolean, default=False)
    meets_target_4000 = Column(Boolean, default=False)
    
    # Overall compliance
    overall_compliance = Column(Boolean, default=False)
    compliance_notes = Column(Text)
    
    # Summary statistics
    average_rt60 = Column(Float, default=0.0)  # Average across speech frequencies (250-4000)
    total_surface_area = Column(Float, default=0.0)
    average_absorption_coeff = Column(Float, default=0.0)
    
    # Relationships
    space = relationship("Space", back_populates="rt60_results")
    
    def __repr__(self):
        return f"<RT60CalculationResult(id={self.id}, space_id={self.space_id}, avg_rt60={self.average_rt60})>"
    
    def get_rt60_by_frequency(self, frequency):
        """Get RT60 value for specific frequency"""
        freq_map = {
            125: self.rt60_125,
            250: self.rt60_250,
            500: self.rt60_500,
            1000: self.rt60_1000,
            2000: self.rt60_2000,
            4000: self.rt60_4000
        }
        return freq_map.get(frequency, 0.0)
    
    def get_sabines_by_frequency(self, frequency):
        """Get total sabines for specific frequency"""
        freq_map = {
            125: self.total_sabines_125,
            250: self.total_sabines_250,
            500: self.total_sabines_500,
            1000: self.total_sabines_1000,
            2000: self.total_sabines_2000,
            4000: self.total_sabines_4000
        }
        return freq_map.get(frequency, 0.0)
    
    def check_frequency_compliance(self, frequency):
        """Check if frequency meets target compliance"""
        freq_map = {
            125: self.meets_target_125,
            250: self.meets_target_250,
            500: self.meets_target_500,
            1000: self.meets_target_1000,
            2000: self.meets_target_2000,
            4000: self.meets_target_4000
        }
        return freq_map.get(frequency, False)
    
    def calculate_average_rt60(self):
        """Calculate average RT60 across speech frequencies (250-4000 Hz)"""
        speech_frequencies = [self.rt60_250, self.rt60_500, self.rt60_1000, self.rt60_2000, self.rt60_4000]
        valid_values = [rt60 for rt60 in speech_frequencies if rt60 and rt60 > 0]
        
        if valid_values:
            self.average_rt60 = round(sum(valid_values) / len(valid_values), 2)
        else:
            self.average_rt60 = 0.0
        
        return self.average_rt60
    
    def update_compliance_status(self):
        """Update overall compliance based on individual frequency compliance"""
        frequency_compliance = [
            self.meets_target_125, self.meets_target_250, self.meets_target_500,
            self.meets_target_1000, self.meets_target_2000, self.meets_target_4000
        ]
        
        # Overall compliance requires all frequencies to meet target
        self.overall_compliance = all(frequency_compliance)
        
        # Generate compliance notes
        failed_frequencies = []
        if not self.meets_target_125: failed_frequencies.append('125Hz')
        if not self.meets_target_250: failed_frequencies.append('250Hz')
        if not self.meets_target_500: failed_frequencies.append('500Hz')
        if not self.meets_target_1000: failed_frequencies.append('1000Hz')
        if not self.meets_target_2000: failed_frequencies.append('2000Hz')
        if not self.meets_target_4000: failed_frequencies.append('4000Hz')
        
        if failed_frequencies:
            self.compliance_notes = f"Target not met at: {', '.join(failed_frequencies)}"
        else:
            self.compliance_notes = "All frequencies meet target RT60 ± tolerance"
    
    def to_dict(self):
        """Convert to dictionary for API/JSON serialization"""
        return {
            'id': self.id,
            'space_id': self.space_id,
            'calculation_date': self.calculation_date.isoformat() if self.calculation_date else None,
            'target_rt60': self.target_rt60,
            'target_tolerance': self.target_tolerance,
            'room_type': self.room_type,
            'leed_compliance_required': self.leed_compliance_required,
            'calculation_method': self.calculation_method,
            'room_volume': self.room_volume,
            'rt60_by_frequency': {
                125: self.rt60_125,
                250: self.rt60_250,
                500: self.rt60_500,
                1000: self.rt60_1000,
                2000: self.rt60_2000,
                4000: self.rt60_4000
            },
            'sabines_by_frequency': {
                125: self.total_sabines_125,
                250: self.total_sabines_250,
                500: self.total_sabines_500,
                1000: self.total_sabines_1000,
                2000: self.total_sabines_2000,
                4000: self.total_sabines_4000
            },
            'compliance_by_frequency': {
                125: self.meets_target_125,
                250: self.meets_target_250,
                500: self.meets_target_500,
                1000: self.meets_target_1000,
                2000: self.meets_target_2000,
                4000: self.meets_target_4000
            },
            'overall_compliance': self.overall_compliance,
            'compliance_notes': self.compliance_notes,
            'average_rt60': self.average_rt60,
            'total_surface_area': self.total_surface_area,
            'average_absorption_coeff': self.average_absorption_coeff
        }