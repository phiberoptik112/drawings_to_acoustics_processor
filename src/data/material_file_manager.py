"""
Utilities for managing material schedule PDF files
"""

import os
import shutil
from pathlib import Path
from typing import Optional, Tuple


def get_material_schedules_folder(project_location: str) -> str:
    """
    Get the materials folder path for a project.
    Creates the folder if it doesn't exist.
    
    Args:
        project_location: Root path of the project
        
    Returns:
        Path to the materials folder
    """
    if not project_location:
        raise ValueError("Project location is required")
    
    materials_folder = os.path.join(project_location, "materials")
    
    # Create the folder if it doesn't exist
    os.makedirs(materials_folder, exist_ok=True)
    
    return materials_folder


def get_drawing_set_materials_folder(project_location: str, drawing_set_name: str) -> str:
    """
    Get the materials folder for a specific drawing set.
    Creates the folder if it doesn't exist.
    
    Args:
        project_location: Root path of the project
        drawing_set_name: Name of the drawing set
        
    Returns:
        Path to the drawing set's materials folder
    """
    materials_folder = get_material_schedules_folder(project_location)
    
    # Sanitize drawing set name for filesystem
    safe_name = "".join(c for c in drawing_set_name if c.isalnum() or c in (' ', '-', '_')).strip()
    safe_name = safe_name.replace(' ', '_')
    
    set_folder = os.path.join(materials_folder, safe_name)
    os.makedirs(set_folder, exist_ok=True)
    
    return set_folder


def copy_material_schedule_to_project(
    source_path: str, 
    project_location: str, 
    drawing_set_name: str,
    target_filename: Optional[str] = None
) -> Tuple[bool, str]:
    """
    Copy a material schedule PDF to the project's materials folder.
    
    Args:
        source_path: Path to the source PDF file
        project_location: Root path of the project
        drawing_set_name: Name of the drawing set
        target_filename: Optional custom filename (if None, uses source filename)
        
    Returns:
        Tuple of (success: bool, managed_path: str or error_message: str)
    """
    try:
        # Validate source file
        if not os.path.exists(source_path):
            return False, f"Source file not found: {source_path}"
        
        if not source_path.lower().endswith('.pdf'):
            return False, "File must be a PDF"
        
        # Get target folder
        target_folder = get_drawing_set_materials_folder(project_location, drawing_set_name)
        
        # Determine target filename
        if target_filename:
            if not target_filename.lower().endswith('.pdf'):
                target_filename += '.pdf'
        else:
            target_filename = os.path.basename(source_path)
        
        # Full target path
        target_path = os.path.join(target_folder, target_filename)
        
        # If target exists, make it unique
        if os.path.exists(target_path):
            base, ext = os.path.splitext(target_filename)
            counter = 1
            while os.path.exists(os.path.join(target_folder, f"{base}_{counter}{ext}")):
                counter += 1
            target_filename = f"{base}_{counter}{ext}"
            target_path = os.path.join(target_folder, target_filename)
        
        # Copy the file
        shutil.copy2(source_path, target_path)
        
        return True, target_path
        
    except Exception as e:
        return False, f"Failed to copy file: {str(e)}"


def validate_material_schedule_pdf(file_path: str) -> Tuple[bool, str]:
    """
    Validate that a material schedule file exists and is a valid PDF.
    
    Args:
        file_path: Path to the PDF file
        
    Returns:
        Tuple of (is_valid: bool, message: str)
    """
    if not file_path:
        return False, "No file path provided"
    
    if not os.path.exists(file_path):
        return False, f"File not found: {file_path}"
    
    if not file_path.lower().endswith('.pdf'):
        return False, "File must be a PDF"
    
    # Check file size (basic validation)
    try:
        file_size = os.path.getsize(file_path)
        if file_size == 0:
            return False, "File is empty"
        if file_size > 100 * 1024 * 1024:  # 100 MB limit
            return False, "File is too large (max 100 MB)"
    except Exception as e:
        return False, f"Cannot read file: {str(e)}"
    
    # Try to open with PyMuPDF to validate PDF structure
    try:
        import fitz  # PyMuPDF
        doc = fitz.open(file_path)
        page_count = len(doc)
        doc.close()
        
        if page_count == 0:
            return False, "PDF has no pages"
        
        return True, f"Valid PDF with {page_count} page(s)"
        
    except ImportError:
        # PyMuPDF not available, skip detailed validation
        return True, "PDF file (detailed validation not available)"
    except Exception as e:
        return False, f"Invalid PDF: {str(e)}"


def delete_managed_file(managed_path: str) -> Tuple[bool, str]:
    """
    Delete a managed material schedule file (but preserve external files).
    
    Args:
        managed_path: Path to the managed file
        
    Returns:
        Tuple of (success: bool, message: str)
    """
    try:
        if not managed_path:
            return True, "No managed file to delete"
        
        if not os.path.exists(managed_path):
            return True, "Managed file does not exist"
        
        os.remove(managed_path)
        return True, "Managed file deleted"
        
    except Exception as e:
        return False, f"Failed to delete managed file: {str(e)}"

