"""
WallType model for user-defined wall type codes with STC ratings.

This model supports the LEED requirement for tracking wall/partition STC values.
Users read wall type codes from project drawings and assign STC values accordingly.
"""

from datetime import datetime
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey
from sqlalchemy.orm import relationship

from models.database import Base


class WallType(Base):
    """User-defined wall type codes with STC ratings.

    Users read wall type codes (e.g., W1, W2, P1) from project drawings
    and assign corresponding STC values. This is used for LEED acoustic
    certification to document partition performance.
    """
    __tablename__ = 'wall_types'

    id = Column(Integer, primary_key=True)
    project_id = Column(Integer, ForeignKey('projects.id'), nullable=False)

    # Wall type identification
    code = Column(String(50), nullable=False)  # e.g., "W1", "W2", "P1"
    description = Column(String(200))  # e.g., "GWB on metal stud"

    # Acoustic rating
    stc_rating = Column(Integer, nullable=False)  # STC value (typically 30-65)

    # Additional info
    notes = Column(Text)  # Optional notes about this wall type

    # Timestamps
    created_date = Column(DateTime, default=datetime.utcnow)
    modified_date = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    project = relationship("Project", back_populates="wall_types")

    def __repr__(self):
        return f"<WallType(id={self.id}, code='{self.code}', stc={self.stc_rating})>"

    def to_dict(self):
        """Convert to dictionary for serialization."""
        return {
            'id': self.id,
            'project_id': self.project_id,
            'code': self.code,
            'description': self.description,
            'stc_rating': self.stc_rating,
            'notes': self.notes,
            'created_date': self.created_date.isoformat() if self.created_date else None,
            'modified_date': self.modified_date.isoformat() if self.modified_date else None
        }

    @classmethod
    def from_dict(cls, data: dict, project_id: int) -> 'WallType':
        """Create WallType from dictionary."""
        return cls(
            project_id=project_id,
            code=data.get('code', ''),
            description=data.get('description'),
            stc_rating=data.get('stc_rating', 45),
            notes=data.get('notes')
        )
