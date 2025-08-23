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


class NoiseSource(Base):
    """Generic noise source attached to a project (e.g., generator, chiller room).

    Minimal fields for starting dB(A); octave bands can be added later.
    """

    __tablename__ = "noise_sources"

    id = Column(Integer, primary_key=True)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=False)

    name = Column(String(255), nullable=False)
    source_type = Column(String(100))           # equipment, environmental, other
    base_noise_dba = Column(Float)              # Overall A-weighted level
    notes = Column(Text)
    created_date = Column(DateTime, default=datetime.utcnow)

    # Relationships
    project = relationship("Project", back_populates="noise_sources")

    def __repr__(self) -> str:  # pragma: no cover
        return f"<NoiseSource(id={self.id}, name='{self.name}', dBA={self.base_noise_dba})>"


