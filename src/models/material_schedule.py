"""
Material Schedule model - represents material/finishes schedules associated with drawing sets
"""

from sqlalchemy import Column, Integer, String, DateTime, Text, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime
from .database import Base


class MaterialSchedule(Base):
    """Material Schedule model for storing material/finishes schedule PDFs per drawing set"""
    __tablename__ = 'material_schedules'
    
    id = Column(Integer, primary_key=True)
    drawing_set_id = Column(Integer, ForeignKey('drawing_sets.id'), nullable=False)
    name = Column(String(255), nullable=False)
    description = Column(Text)
    
    # File paths - support both external and project-managed PDFs
    file_path = Column(String(1000))  # External PDF path (original location)
    managed_file_path = Column(String(1000))  # Project-managed copy (optional)
    
    # Schedule classification
    schedule_type = Column(String(100), default='finishes')  # 'finishes', 'materials', 'acoustic_treatments', etc.
    
    created_date = Column(DateTime, default=datetime.utcnow)
    modified_date = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    drawing_set = relationship("DrawingSet", back_populates="material_schedules")
    
    def __repr__(self):
        return f"<MaterialSchedule(id={self.id}, name='{self.name}', drawing_set_id={self.drawing_set_id})>"
    
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

