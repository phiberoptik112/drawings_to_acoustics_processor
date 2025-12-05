"""
Drawing model - represents PDF drawings in a project
"""

import os
from sqlalchemy import Column, Integer, String, DateTime, Text, ForeignKey, Float
from sqlalchemy.orm import relationship
from datetime import datetime
from .database import Base


def get_project_base_directory():
    """Get the base directory for project data storage.
    
    Returns the standard project data directory that all relative paths
    should be resolved against.
    """
    return os.path.expanduser("~/Documents/AcousticAnalysis")


class Drawing(Base):
    """Drawing model for storing PDF drawings and their properties"""
    __tablename__ = 'drawings'
    
    id = Column(Integer, primary_key=True)
    project_id = Column(Integer, ForeignKey('projects.id'), nullable=False)
    name = Column(String(255), nullable=False)
    description = Column(Text)
    file_path = Column(String(1000), nullable=False)  # Path to PDF file (may be relative or absolute)
    
    # Scale information
    scale_ratio = Column(Float)  # Pixels per real-world unit
    scale_string = Column(String(50))  # e.g., "1:100"
    
    # Drawing properties
    page_number = Column(Integer, default=1)  # For multi-page PDFs
    width_pixels = Column(Float)   # PDF page width in pixels
    height_pixels = Column(Float)  # PDF page height in pixels
    
    # Link to drawing set (optional)
    drawing_set_id = Column(Integer, ForeignKey('drawing_sets.id'), nullable=True)
    
    created_date = Column(DateTime, default=datetime.utcnow)
    modified_date = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    project = relationship("Project", back_populates="drawings")
    spaces = relationship("Space", back_populates="drawing")  # Direct relationship to spaces
    room_boundaries = relationship("RoomBoundary", back_populates="drawing", cascade="all, delete-orphan")
    hvac_components = relationship("HVACComponent", back_populates="drawing", cascade="all, delete-orphan")
    drawing_set = relationship("DrawingSet", back_populates="drawings")
    
    def __repr__(self):
        return f"<Drawing(id={self.id}, name='{self.name}', project_id={self.project_id})>"
    
    def get_space_count(self):
        """Get the number of spaces on this drawing"""
        return len(self.spaces)
    
    def get_space_names(self):
        """Get list of space names on this drawing"""
        return [space.name for space in self.spaces]
    
    def get_spaces_with_boundaries(self):
        """Get spaces that have room boundaries on this drawing"""
        spaces_with_boundaries = []
        for space in self.spaces:
            if space.get_room_boundaries_on_drawing(self.id):
                spaces_with_boundaries.append(space)
        return spaces_with_boundaries
    
    def to_dict(self):
        """Convert drawing to dictionary"""
        return {
            'id': self.id,
            'project_id': self.project_id,
            'name': self.name,
            'description': self.description,
            'file_path': self.file_path,
            'absolute_file_path': self.get_absolute_file_path(),
            'scale_ratio': self.scale_ratio,
            'scale_string': self.scale_string,
            'page_number': self.page_number,
            'width_pixels': self.width_pixels,
            'height_pixels': self.height_pixels,
            'space_count': self.get_space_count(),
            'space_names': self.get_space_names()
        }
    
    def get_absolute_file_path(self, base_directory=None):
        """Get the absolute file path to the PDF.
        
        Resolves relative paths against the base directory. If the stored path
        is already absolute and exists, it is returned as-is. If the path is
        relative, it is resolved against the base directory.
        
        Args:
            base_directory: Optional base directory for resolution. 
                          Defaults to the project data directory.
                          
        Returns:
            Absolute path to the file (may not exist)
        """
        if not self.file_path:
            return None
            
        # If already absolute and exists, return as-is
        if os.path.isabs(self.file_path) and os.path.exists(self.file_path):
            return self.file_path
        
        # Try to resolve against base directory
        base_dir = base_directory or get_project_base_directory()
        
        # If stored path is relative, resolve it
        if not os.path.isabs(self.file_path):
            resolved_path = os.path.join(base_dir, self.file_path)
            if os.path.exists(resolved_path):
                return os.path.abspath(resolved_path)
        
        # Try project-specific subdirectory
        project_dir = os.path.join(base_dir, f"project_{self.project_id}")
        if os.path.isdir(project_dir):
            project_path = os.path.join(project_dir, os.path.basename(self.file_path))
            if os.path.exists(project_path):
                return os.path.abspath(project_path)
        
        # Try drawings subdirectory
        drawings_dir = os.path.join(base_dir, "drawings")
        if os.path.isdir(drawings_dir):
            drawings_path = os.path.join(drawings_dir, os.path.basename(self.file_path))
            if os.path.exists(drawings_path):
                return os.path.abspath(drawings_path)
        
        # Return the original path (even if it doesn't exist)
        if os.path.isabs(self.file_path):
            return self.file_path
        
        return os.path.abspath(os.path.join(base_dir, self.file_path))
    
    def file_exists(self):
        """Check if the PDF file exists at the resolved path.
        
        Returns:
            True if the file exists, False otherwise
        """
        abs_path = self.get_absolute_file_path()
        return abs_path is not None and os.path.exists(abs_path)
    
    def try_locate_file(self, search_directories=None):
        """Try to locate the PDF file in various locations.
        
        Searches common directories for the file by name if the stored path
        doesn't exist. This helps recover from moved or relocated files.
        
        Args:
            search_directories: Optional list of directories to search.
                              Defaults to common project locations.
                              
        Returns:
            Tuple of (found_path, found) where found_path is the absolute path
            if found (or None) and found is a boolean.
        """
        if not self.file_path:
            return None, False
        
        # First check if file exists at stored/resolved path
        abs_path = self.get_absolute_file_path()
        if abs_path and os.path.exists(abs_path):
            return abs_path, True
        
        # Get filename for searching
        filename = os.path.basename(self.file_path)
        
        # Build search directories
        base_dir = get_project_base_directory()
        default_search = [
            base_dir,
            os.path.join(base_dir, "drawings"),
            os.path.join(base_dir, f"project_{self.project_id}"),
            os.path.expanduser("~/Documents"),
            os.path.expanduser("~/Downloads"),
        ]
        
        if search_directories:
            default_search = list(search_directories) + default_search
        
        # Search for file
        for search_dir in default_search:
            if not os.path.isdir(search_dir):
                continue
            
            candidate = os.path.join(search_dir, filename)
            if os.path.exists(candidate):
                return os.path.abspath(candidate), True
            
            # Also check subdirectories one level deep
            try:
                for subdir in os.listdir(search_dir):
                    subdir_path = os.path.join(search_dir, subdir)
                    if os.path.isdir(subdir_path):
                        candidate = os.path.join(subdir_path, filename)
                        if os.path.exists(candidate):
                            return os.path.abspath(candidate), True
            except OSError:
                pass
        
        return None, False
    
    def update_file_path(self, new_path, make_relative=True, base_directory=None):
        """Update the stored file path.
        
        Optionally converts the path to be relative to the base directory
        for better portability across machines.
        
        Args:
            new_path: The new absolute path to the PDF file
            make_relative: If True, convert to relative path if possible
            base_directory: Base directory for relative path calculation
            
        Returns:
            The path that was stored (may be relative or absolute)
        """
        if not new_path:
            self.file_path = new_path
            return new_path
        
        abs_path = os.path.abspath(new_path)
        
        if make_relative:
            base_dir = base_directory or get_project_base_directory()
            
            # Check if path is under the base directory
            try:
                rel_path = os.path.relpath(abs_path, base_dir)
                # Only use relative path if it doesn't go up too many directories
                if not rel_path.startswith('..') or rel_path.count('..') <= 2:
                    self.file_path = rel_path
                    return rel_path
            except ValueError:
                # On Windows, relpath fails if paths are on different drives
                pass
        
        # Store absolute path
        self.file_path = abs_path
        return abs_path
    
    @staticmethod
    def make_path_relative(absolute_path, base_directory=None):
        """Convert an absolute path to a project-relative path.
        
        Static method for use when creating new drawings.
        
        Args:
            absolute_path: The absolute path to convert
            base_directory: Base directory for relative path calculation
            
        Returns:
            Relative path if possible, otherwise the absolute path
        """
        if not absolute_path:
            return absolute_path
        
        abs_path = os.path.abspath(absolute_path)
        base_dir = base_directory or get_project_base_directory()
        
        try:
            rel_path = os.path.relpath(abs_path, base_dir)
            # Only use relative path if it doesn't go up too many directories
            if not rel_path.startswith('..') or rel_path.count('..') <= 2:
                return rel_path
        except ValueError:
            pass
        
        return abs_path