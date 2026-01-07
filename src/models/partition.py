"""
Partition models - represents partition assemblies and their assignments to spaces
for LEED Sound Transmission compliance documentation.
"""

from sqlalchemy import Column, Integer, String, DateTime, Text, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime
from .database import Base


class PartitionType(Base):
    """
    Partition type/assembly definition stored at project level.
    
    Examples:
    - K11: 5/8" GWB both sides, 3-5/8" metal studs, STC 50
    - P3: CMU partition with furring, STC 45
    """
    __tablename__ = 'partition_types'
    
    id = Column(Integer, primary_key=True)
    project_id = Column(Integer, ForeignKey('projects.id'), nullable=False)
    
    # Assembly identification
    assembly_id = Column(String(50), nullable=False)  # e.g., "K11", "P3"
    description = Column(Text)  # e.g., "5/8" GWB both sides, 3-5/8" metal studs"
    
    # STC rating
    stc_rating = Column(Integer)  # e.g., 50
    
    # Data source reference
    source_document = Column(String(255))  # e.g., "A6.1", "Partition Schedule"
    notes = Column(Text)
    
    created_date = Column(DateTime, default=datetime.utcnow)
    modified_date = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    project = relationship("Project", back_populates="partition_types")
    space_partitions = relationship("SpacePartition", back_populates="partition_type",
                                   cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<PartitionType(id={self.id}, assembly_id='{self.assembly_id}', stc={self.stc_rating})>"
    
    def to_dict(self):
        """Convert to dictionary for serialization"""
        return {
            'id': self.id,
            'project_id': self.project_id,
            'assembly_id': self.assembly_id,
            'description': self.description,
            'stc_rating': self.stc_rating,
            'source_document': self.source_document,
            'notes': self.notes,
            'created_date': self.created_date.isoformat() if self.created_date else None,
            'modified_date': self.modified_date.isoformat() if self.modified_date else None,
        }


class PartitionScheduleDocument(Base):
    """
    Reference PDF document for partition schedule (project-level).
    
    This stores the reference to a PDF showing the project's interior partition
    details, which engineers can view when assigning partition types to spaces.
    """
    __tablename__ = 'partition_schedule_documents'
    
    id = Column(Integer, primary_key=True)
    project_id = Column(Integer, ForeignKey('projects.id'), nullable=False)
    
    name = Column(String(255), nullable=False)
    description = Column(Text)
    
    # File paths - support both external and project-managed PDFs
    file_path = Column(String(1000))  # External PDF path (original location)
    managed_file_path = Column(String(1000))  # Project-managed copy (optional)
    
    # Optional: specific page bookmark
    page_number = Column(Integer, default=1)
    
    created_date = Column(DateTime, default=datetime.utcnow)
    modified_date = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    project = relationship("Project", back_populates="partition_schedule_documents")
    
    def __repr__(self):
        return f"<PartitionScheduleDocument(id={self.id}, name='{self.name}')>"
    
    def get_display_path(self):
        """Get the preferred display path - use managed path if available, otherwise external"""
        return self.managed_file_path or self.file_path
    
    def has_valid_file(self):
        """Check if at least one file path exists"""
        import os
        if self.managed_file_path and os.path.exists(self.managed_file_path):
            return True
        if self.file_path and os.path.exists(self.file_path):
            return True
        return False
    
    def to_dict(self):
        """Convert to dictionary for serialization"""
        return {
            'id': self.id,
            'project_id': self.project_id,
            'name': self.name,
            'description': self.description,
            'file_path': self.file_path,
            'managed_file_path': self.managed_file_path,
            'page_number': self.page_number,
            'created_date': self.created_date.isoformat() if self.created_date else None,
            'modified_date': self.modified_date.isoformat() if self.modified_date else None,
        }


class SpacePartition(Base):
    """
    Individual partition assignment for a space.
    
    Each space can have multiple partitions (walls, floor, ceiling) each with
    their own assembly type and adjacent space requirements.
    """
    __tablename__ = 'space_partitions'
    
    id = Column(Integer, primary_key=True)
    space_id = Column(Integer, ForeignKey('spaces.id'), nullable=False)
    partition_type_id = Column(Integer, ForeignKey('partition_types.id'), nullable=True)
    
    # Assembly location in space
    assembly_location = Column(String(50))  # 'Wall', 'Floor', 'Ceiling'
    
    # Adjacent space information
    adjacent_space_type = Column(String(100))  # e.g., "Corridor", "Classroom"
    adjacent_space_id = Column(Integer, ForeignKey('spaces.id'), nullable=True)  # Optional link
    
    # STC requirements
    minimum_stc_required = Column(Integer)  # Minimum required STC
    
    # Override for actual STC (if different from partition_type)
    stc_rating_override = Column(Integer, nullable=True)
    
    # Compliance notes
    notes = Column(Text)
    
    created_date = Column(DateTime, default=datetime.utcnow)
    modified_date = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    space = relationship("Space", back_populates="partitions", foreign_keys=[space_id])
    partition_type = relationship("PartitionType", back_populates="space_partitions")
    adjacent_space = relationship("Space", foreign_keys=[adjacent_space_id])
    
    def __repr__(self):
        return f"<SpacePartition(id={self.id}, space_id={self.space_id}, location='{self.assembly_location}')>"
    
    @property
    def effective_stc_rating(self):
        """Get actual STC rating (override or from partition type)"""
        if self.stc_rating_override is not None:
            return self.stc_rating_override
        if self.partition_type:
            return self.partition_type.stc_rating
        return None
    
    @property
    def assembly_id(self):
        """Get assembly ID from partition type"""
        if self.partition_type:
            return self.partition_type.assembly_id
        return None
    
    @property
    def assembly_description(self):
        """Get assembly description from partition type"""
        if self.partition_type:
            return self.partition_type.description
        return None
    
    @property
    def is_compliant(self):
        """Check if partition meets minimum STC requirement"""
        stc = self.effective_stc_rating
        if stc is None or self.minimum_stc_required is None:
            return None
        return stc >= self.minimum_stc_required
    
    @property
    def compliance_status(self):
        """Get compliance status as string"""
        compliant = self.is_compliant
        if compliant is None:
            return "N/A"
        return "Yes" if compliant else "No"
    
    def to_dict(self):
        """Convert to dictionary for serialization"""
        return {
            'id': self.id,
            'space_id': self.space_id,
            'partition_type_id': self.partition_type_id,
            'assembly_location': self.assembly_location,
            'adjacent_space_type': self.adjacent_space_type,
            'adjacent_space_id': self.adjacent_space_id,
            'minimum_stc_required': self.minimum_stc_required,
            'stc_rating_override': self.stc_rating_override,
            'notes': self.notes,
            'created_date': self.created_date.isoformat() if self.created_date else None,
            'modified_date': self.modified_date.isoformat() if self.modified_date else None,
        }
    
    def to_leed_dict(self):
        """Convert to LEED export format dictionary"""
        return {
            'room_id': self.space.room_id if self.space else None,
            'assembly_id': self.assembly_id,
            'assembly_description': self.assembly_description,
            'assembly_location': self.assembly_location,
            'space_type': self.space.space_type if self.space else None,
            'adjacent_space_type': self.adjacent_space_type,
            'minimum_stc_required': self.minimum_stc_required,
            'stc_rating': self.effective_stc_rating,
            'compliance': self.compliance_status,
        }

