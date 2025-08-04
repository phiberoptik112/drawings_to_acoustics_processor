"""
Space model - represents rooms/spaces for acoustic analysis
"""

from sqlalchemy import Column, Integer, String, DateTime, Text, ForeignKey, Float, Enum
from sqlalchemy.orm import relationship
from datetime import datetime
from .database import Base
import enum
import math


class SurfaceType(enum.Enum):
    """Enum for surface types"""
    CEILING = "ceiling"
    WALL = "wall"
    FLOOR = "floor"


class SpaceSurfaceMaterial(Base):
    """Model for storing multiple materials per surface type in a space"""
    __tablename__ = 'space_surface_materials'
    
    id = Column(Integer, primary_key=True)
    space_id = Column(Integer, ForeignKey('spaces.id'), nullable=False)
    surface_type = Column(Enum(SurfaceType), nullable=False)
    material_key = Column(String(200), nullable=False)  # Reference to material in STANDARD_MATERIALS
    order_index = Column(Integer, default=0)  # For maintaining order of materials
    
    # Relationships
    space = relationship("Space", back_populates="surface_materials")
    
    def __repr__(self):
        return f"<SpaceSurfaceMaterial(space_id={self.space_id}, surface_type={self.surface_type.value}, material_key='{self.material_key}')>"


class Space(Base):
    """Space model for storing room/space information"""
    __tablename__ = 'spaces'
    
    id = Column(Integer, primary_key=True)
    project_id = Column(Integer, ForeignKey('projects.id'), nullable=False)
    drawing_id = Column(Integer, ForeignKey('drawings.id'), nullable=True)  # Direct reference to drawing
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
    drawing = relationship("Drawing", back_populates="spaces")  # Direct relationship to drawing
    room_boundaries = relationship("RoomBoundary", back_populates="space", cascade="all, delete-orphan")
    hvac_paths = relationship("HVACPath", back_populates="target_space")
    
    # Enhanced RT60 relationships
    surface_instances = relationship("RoomSurfaceInstance", back_populates="space", cascade="all, delete-orphan")
    rt60_results = relationship("RT60CalculationResult", back_populates="space", cascade="all, delete-orphan")
    
    # New surface materials relationship
    surface_materials = relationship("SpaceSurfaceMaterial", back_populates="space", cascade="all, delete-orphan", order_by="SpaceSurfaceMaterial.order_index")
    
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
    
    def get_latest_rt60_result(self):
        """Get the most recent RT60 calculation result"""
        if self.rt60_results:
            return max(self.rt60_results, key=lambda r: r.calculation_date)
        return None
    
    def get_total_surface_area(self):
        """Calculate total surface area from all surface instances"""
        return sum(instance.effective_area for instance in self.surface_instances)
    
    def get_surfaces_by_category(self, category_name):
        """Get surface instances filtered by category"""
        return [instance for instance in self.surface_instances 
                if instance.surface_type and instance.surface_type.category 
                and instance.surface_type.category.name == category_name]
    
    def calculate_perimeter(self):
        """Calculate perimeter from room boundaries (assumes rectangular room)"""
        if not self.room_boundaries:
            return 0.0
        
        # Use the first boundary to estimate perimeter
        boundary = self.room_boundaries[0]
        # Convert pixel dimensions to real dimensions using boundary's calculated area
        if boundary.calculated_area and boundary.width and boundary.height:
            # Assuming rectangular: area = width * height, perimeter = 2 * (width + height)
            aspect_ratio = boundary.width / boundary.height
            width_real = (boundary.calculated_area * aspect_ratio) ** 0.5
            height_real = boundary.calculated_area / width_real
            return 2 * (width_real + height_real)
        
        return 0.0
    
    def get_surface_materials(self, surface_type):
        """Get all materials for a specific surface type"""
        if isinstance(surface_type, str):
            surface_type = SurfaceType(surface_type)
        
        return [sm.material_key for sm in self.surface_materials 
                if sm.surface_type == surface_type]
    
    def set_surface_materials(self, surface_type, material_keys, session=None):
        """Set materials for a specific surface type"""
        if isinstance(surface_type, str):
            surface_type = SurfaceType(surface_type)
        
        # Remove existing materials for this surface type
        existing_materials = [sm for sm in self.surface_materials 
                            if sm.surface_type == surface_type]
        for sm in existing_materials:
            if session:
                session.delete(sm)
            else:
                self.surface_materials.remove(sm)
        
        # Add new materials
        for i, material_key in enumerate(material_keys):
            new_material = SpaceSurfaceMaterial(
                space_id=self.id,
                surface_type=surface_type,
                material_key=material_key,
                order_index=i
            )
            self.surface_materials.append(new_material)
    
    def get_ceiling_materials(self):
        """Get ceiling materials (convenience method)"""
        return self.get_surface_materials(SurfaceType.CEILING)
    
    def get_wall_materials(self):
        """Get wall materials (convenience method)"""
        return self.get_surface_materials(SurfaceType.WALL)
    
    def get_floor_materials(self):
        """Get floor materials (convenience method)"""
        return self.get_surface_materials(SurfaceType.FLOOR)
    
    def migrate_legacy_materials(self, session=None):
        """Migrate legacy single materials to new multiple materials system"""
        # Only migrate if we have legacy materials and no new materials
        if not self.surface_materials:
            migrations = []
            
            if self.ceiling_material:
                migrations.append((SurfaceType.CEILING, [self.ceiling_material]))
            if self.wall_material:
                migrations.append((SurfaceType.WALL, [self.wall_material]))
            if self.floor_material:
                migrations.append((SurfaceType.FLOOR, [self.floor_material]))
            
            for surface_type, materials in migrations:
                self.set_surface_materials(surface_type, materials, session)
    
    def get_average_absorption_coefficient(self, surface_type, materials_db=None):
        """Get average absorption coefficient for a surface type with multiple materials"""
        from data.materials import STANDARD_MATERIALS
        if materials_db is None:
            materials_db = STANDARD_MATERIALS
            
        materials = self.get_surface_materials(surface_type)
        if not materials:
            return 0.0
            
        total_coeff = 0.0
        valid_materials = 0
        
        for material_key in materials:
            if material_key in materials_db:
                material = materials_db[material_key]
                coeff = material.get('nrc', material['absorption_coeff'])
                total_coeff += coeff
                valid_materials += 1
                
        return total_coeff / valid_materials if valid_materials > 0 else 0.0
    
    def get_drawing_name(self):
        """Get the name of the associated drawing"""
        return self.drawing.name if self.drawing else "No Drawing"
    
    def get_primary_room_boundary(self):
        """Get the primary room boundary (first one) for this space"""
        return self.room_boundaries[0] if self.room_boundaries else None
        
    def get_room_boundaries_on_drawing(self, drawing_id):
        """Get room boundaries for this space on a specific drawing"""
        return [rb for rb in self.room_boundaries if rb.drawing_id == drawing_id]
        
    def set_drawing_from_boundaries(self, session=None):
        """Set drawing_id based on the most common drawing in room boundaries"""
        if not self.room_boundaries:
            return
            
        # Count boundaries per drawing
        drawing_counts = {}
        for boundary in self.room_boundaries:
            drawing_id = boundary.drawing_id
            drawing_counts[drawing_id] = drawing_counts.get(drawing_id, 0) + 1
        
        # Set to the drawing with the most boundaries
        if drawing_counts:
            most_common_drawing = max(drawing_counts.items(), key=lambda x: x[1])[0]
            self.drawing_id = most_common_drawing
    
    def get_hvac_paths(self):
        """Get all HVAC paths that serve this space"""
        return [path for path in self.hvac_paths]
    
    def calculate_mechanical_background_noise(self):
        """Calculate mechanical background noise from HVAC paths serving this space"""
        from calculations.noise_calculator import NoiseCalculator
        
        if not self.hvac_paths:
            return {
                'nc_rating': None,
                'sound_pressure_levels': {},
                'paths_analyzed': 0,
                'error': 'No HVAC paths found serving this space'
            }
        
        calculator = NoiseCalculator()
        total_noise_levels = {}
        paths_analyzed = 0
        
        # Calculate noise from each HVAC path
        for path in self.hvac_paths:
            try:
                # Convert path to calculation format
                path_data = {
                    'source_component': {
                        'type': path.source_component_type or 'ahu',
                        'noise_level': path.source_noise_level or 80.0
                    },
                    'segments': [],
                    'terminal_component': {
                        'type': path.terminal_component_type or 'diffuser',
                        'noise_level': path.terminal_noise_level or 30.0
                    }
                }
                
                # Add segments
                for segment in path.segments:
                    segment_data = {
                        'length': segment.length or 0,
                        'duct_size': f"{segment.width}x{segment.height}" if segment.width and segment.height else "12x12",
                        'fittings': []
                    }
                    
                    # Add fittings
                    for fitting in segment.fittings:
                        fitting_data = {
                            'type': fitting.fitting_type,
                            'quantity': fitting.quantity or 1
                        }
                        segment_data['fittings'].append(fitting_data)
                    
                    path_data['segments'].append(segment_data)
                
                # Calculate noise for this path
                path_results = calculator.calculate_hvac_path_noise(path_data)
                
                if path_results.get('success') and 'terminal_sound_levels' in path_results:
                    # Add to total noise levels (energy sum)
                    terminal_levels = path_results['terminal_sound_levels']
                    for freq, level in terminal_levels.items():
                        if freq not in total_noise_levels:
                            total_noise_levels[freq] = 0
                        # Convert dB to energy, sum, convert back
                        total_noise_levels[freq] += 10 ** (level / 10)
                    
                    paths_analyzed += 1
                    
            except Exception as e:
                print(f"Error calculating noise for path {path.id}: {e}")
                continue
        
        # Convert total energy back to dB
        final_sound_levels = {}
        for freq, energy in total_noise_levels.items():
            final_sound_levels[freq] = 10 * math.log10(energy) if energy > 0 else 0
        
        # Calculate NC rating
        nc_rating = None
        if final_sound_levels:
            try:
                from calculations.nc_rating_analyzer import OctaveBandData
                octave_data = OctaveBandData(
                    freq_63=final_sound_levels.get(63, 0),
                    freq_125=final_sound_levels.get(125, 0),
                    freq_250=final_sound_levels.get(250, 0),
                    freq_500=final_sound_levels.get(500, 0),
                    freq_1000=final_sound_levels.get(1000, 0),
                    freq_2000=final_sound_levels.get(2000, 0),
                    freq_4000=final_sound_levels.get(4000, 0),
                    freq_8000=final_sound_levels.get(8000, 0)
                )
                nc_results = calculator.nc_analyzer.analyze_nc_rating(octave_data)
                nc_rating = nc_results.get('nc_rating')
                
            except Exception as e:
                print(f"Error calculating NC rating: {e}")
        
        return {
            'nc_rating': nc_rating,
            'sound_pressure_levels': final_sound_levels,
            'paths_analyzed': paths_analyzed,
            'success': True
        }
    
    def get_mechanical_noise_status(self):
        """Get a summary of mechanical background noise status"""
        noise_results = self.calculate_mechanical_background_noise()
        
        if not noise_results.get('success'):
            return {
                'status': 'no_hvac',
                'message': 'No HVAC systems serving this space',
                'nc_rating': None,
                'color': '#95a5a6'  # Gray
            }
        
        nc_rating = noise_results.get('nc_rating')
        paths_count = noise_results.get('paths_analyzed', 0)
        
        if nc_rating is None:
            return {
                'status': 'calculation_error',
                'message': f'Error calculating noise from {paths_count} HVAC paths',
                'nc_rating': None,
                'color': '#e74c3c'  # Red
            }
        
        # Determine status based on typical space requirements
        if nc_rating <= 25:
            status = 'excellent'
            color = '#27ae60'  # Green
            message = f'NC {nc_rating} - Excellent for quiet spaces'
        elif nc_rating <= 35:
            status = 'good'  
            color = '#2ecc71'  # Light green
            message = f'NC {nc_rating} - Good for most spaces'
        elif nc_rating <= 45:
            status = 'acceptable'
            color = '#f39c12'  # Orange
            message = f'NC {nc_rating} - Acceptable for general use'
        else:
            status = 'loud'
            color = '#e74c3c'  # Red
            message = f'NC {nc_rating} - May be too loud for quiet activities'
        
        return {
            'status': status,
            'message': message,
            'nc_rating': nc_rating,
            'paths_analyzed': paths_count,
            'color': color
        }

    def to_dict(self):
        """Convert space to dictionary"""
        # Get materials using new system, fallback to legacy fields
        ceiling_materials = self.get_ceiling_materials() or ([self.ceiling_material] if self.ceiling_material else [])
        wall_materials = self.get_wall_materials() or ([self.wall_material] if self.wall_material else [])
        floor_materials = self.get_floor_materials() or ([self.floor_material] if self.floor_material else [])
        
        # Get mechanical noise status
        noise_status = self.get_mechanical_noise_status()
        
        return {
            'id': self.id,
            'project_id': self.project_id,
            'drawing_id': self.drawing_id,
            'drawing_name': self.get_drawing_name(),
            'name': self.name,
            'description': self.description,
            'floor_area': self.floor_area,
            'ceiling_height': self.ceiling_height,
            'volume': self.volume,
            'wall_area': self.wall_area,
            'target_rt60': self.target_rt60,
            'calculated_rt60': self.calculated_rt60,
            # Legacy single material fields for backward compatibility
            'ceiling_material': self.ceiling_material,
            'wall_material': self.wall_material,
            'floor_material': self.floor_material,
            # New multiple materials fields
            'ceiling_materials': ceiling_materials,
            'wall_materials': wall_materials,
            'floor_materials': floor_materials,
            'calculated_nc': self.calculated_nc,
            # Mechanical background noise
            'mechanical_noise_status': noise_status,
            'mechanical_nc_rating': noise_status.get('nc_rating'),
            'hvac_paths_count': len(self.get_hvac_paths()),
            # Other properties
            'total_surface_area': self.get_total_surface_area(),
            'perimeter': self.calculate_perimeter(),
            'latest_rt60_result': self.get_latest_rt60_result().to_dict() if self.get_latest_rt60_result() else None
        }


class RoomBoundary(Base):
    """Room boundary model for storing rectangle boundaries on drawings"""
    __tablename__ = 'room_boundaries'
    
    id = Column(Integer, primary_key=True)
    space_id = Column(Integer, ForeignKey('spaces.id'), nullable=False)
    drawing_id = Column(Integer, ForeignKey('drawings.id'), nullable=False)
    page_number = Column(Integer, default=1)  # PDF page number where boundary exists
    
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