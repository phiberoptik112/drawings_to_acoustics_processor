"""
Mechanical data models: project-level Mechanical Units and generic Noise Sources
"""

from sqlalchemy import Column, Integer, String, DateTime, Text, ForeignKey, Float
from sqlalchemy.orm import relationship
from datetime import datetime

from .database import Base


class MechanicalUnit(Base):
    """Project-level mechanical equipment record (e.g., AHU, RTU, EF, VAV).

    These units are not drawing placements. They represent the mechanical
    schedule imported from drawings/specs and can be referenced by HVAC paths.
    """

    __tablename__ = "mechanical_units"

    id = Column(Integer, primary_key=True)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=False)

    name = Column(String(255), nullable=False)  # Tag or identifier (e.g., AHU-1)
    unit_type = Column(String(100))             # AHU, RTU, EF, VAV, etc.
    manufacturer = Column(String(200))
    model_number = Column(String(100))

    airflow_cfm = Column(Float)                 # Design supply CFM
    external_static_inwg = Column(Float)        # External static pressure (in. w.g.)
    power_kw = Column(Float)

    notes = Column(Text)
    created_date = Column(DateTime, default=datetime.utcnow)

    # Optional frequency-band sound power previews (JSON with 8-band values)
    # Keys typically: [63, 125, 250, 500, 1000, 2000, 4000, 8000]
    inlet_levels_json = Column(Text)     # JSON-serialized dict/list
    radiated_levels_json = Column(Text)
    outlet_levels_json = Column(Text)
    # Arbitrary properties captured during imports
    extra_json = Column(Text)

    # Relationships
    project = relationship("Project", back_populates="mechanical_units")

    def __repr__(self) -> str:  # pragma: no cover - for debug readability
        return (
            f"<MechanicalUnit(id={self.id}, name='{self.name}', type='{self.unit_type}', "
            f"cfm={self.airflow_cfm})>"
        )
    
    def to_dict(self):
        """Convert mechanical unit to dictionary for JSON serialization"""
        return {
            'id': self.id,
            'project_id': self.project_id,
            'name': self.name,
            'unit_type': self.unit_type,
            'manufacturer': self.manufacturer,
            'model_number': self.model_number,
            'airflow_cfm': self.airflow_cfm,
            'external_static_inwg': self.external_static_inwg,
            'power_kw': self.power_kw,
            'notes': self.notes,
            'created_date': self.created_date.isoformat() if self.created_date else None,
            'inlet_levels_json': self.inlet_levels_json,
            'radiated_levels_json': self.radiated_levels_json,
            'outlet_levels_json': self.outlet_levels_json,
            'extra_json': self.extra_json,
        }


class NoiseSource(Base):
    """Generic noise source attached to a project (e.g., generator, chiller room).

    Supports drawing placement for automatic adjacency proximity detection.
    """

    __tablename__ = "noise_sources"

    id = Column(Integer, primary_key=True)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=False)

    name = Column(String(255), nullable=False)
    source_type = Column(String(100))           # equipment, environmental, other
    base_noise_dba = Column(Float)              # Overall A-weighted level
    notes = Column(Text)
    created_date = Column(DateTime, default=datetime.utcnow)

    # Drawing placement fields
    drawing_id = Column(Integer, ForeignKey("drawings.id"), nullable=True)
    page_number = Column(Integer)
    pdf_x = Column(Float)
    pdf_y = Column(Float)
    pdf_page_width = Column(Float)
    pdf_page_height = Column(Float)
    floor_label = Column(String(100))
    placement_type = Column(String(20), default='unplaced')  # 'point' | 'boundary' | 'unplaced'

    # Octave-band sound power levels (Lw) as JSON: {"63":72.0, "125":75.0, ...}
    octave_bands_json = Column(Text)

    # Relationships
    project = relationship("Project", back_populates="noise_sources")

    def __repr__(self) -> str:  # pragma: no cover
        return f"<NoiseSource(id={self.id}, name='{self.name}', dBA={self.base_noise_dba}, placement='{self.placement_type}')>"

    def get_octave_bands(self):
        """Parse octave_bands_json into a dict of {freq_hz: lw_db}."""
        import json
        if not self.octave_bands_json:
            return None
        try:
            return {int(k): float(v) for k, v in json.loads(self.octave_bands_json).items()}
        except (json.JSONDecodeError, ValueError):
            return None

    def set_octave_bands(self, bands_dict):
        """Set octave_bands_json from a dict of {freq_hz: lw_db}."""
        import json
        if bands_dict is None:
            self.octave_bands_json = None
        else:
            self.octave_bands_json = json.dumps({str(k): v for k, v in bands_dict.items()})

    def to_dict(self):
        """Convert noise source to dictionary for JSON serialization"""
        return {
            'id': self.id,
            'project_id': self.project_id,
            'name': self.name,
            'source_type': self.source_type,
            'base_noise_dba': self.base_noise_dba,
            'notes': self.notes,
            'created_date': self.created_date.isoformat() if self.created_date else None,
            'drawing_id': self.drawing_id,
            'page_number': self.page_number,
            'pdf_x': self.pdf_x,
            'pdf_y': self.pdf_y,
            'floor_label': self.floor_label,
            'placement_type': self.placement_type,
            'octave_bands_json': self.octave_bands_json,
        }


