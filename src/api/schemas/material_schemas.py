"""
Material Lookup Schemas

Request and response dataclasses for material database access.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Literal, Optional, Any


@dataclass
class MaterialInfo:
    """Information about an acoustic material."""
    key: str
    name: str
    category: str
    nrc: float  # Noise Reduction Coefficient
    absorption_coefficients: Dict[int, float]  # {125: 0.2, 250: 0.3, ...}
    description: Optional[str] = None
    manufacturer: Optional[str] = None


@dataclass
class MaterialSearchRequest:
    """
    Request for searching the materials database.

    At least one search criterion should be provided.
    """
    # Text search
    search_text: Optional[str] = None

    # Category filter
    category: Optional[Literal["ceiling", "wall", "floor", "doors", "windows", "panels"]] = None

    # Property filters
    min_nrc: Optional[float] = None
    max_nrc: Optional[float] = None

    # Frequency-specific absorption threshold
    min_absorption_at_frequency: Optional[Dict[int, float]] = None  # {500: 0.5}

    # Pagination
    limit: int = 50
    offset: int = 0


@dataclass
class MaterialSearchResponse:
    """Response from material search."""
    status: Literal["success", "error"]

    # Results
    materials: List[MaterialInfo] = field(default_factory=list)
    total_count: int = 0

    # Pagination info
    limit: int = 50
    offset: int = 0
    has_more: bool = False

    # Error
    error: Optional[Any] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to JSON-serializable dictionary"""
        return {
            "status": self.status,
            "materials": [
                {
                    "key": m.key,
                    "name": m.name,
                    "category": m.category,
                    "nrc": m.nrc,
                    "absorption_coefficients": m.absorption_coefficients,
                    "description": m.description,
                    "manufacturer": m.manufacturer,
                }
                for m in self.materials
            ],
            "total_count": self.total_count,
            "limit": self.limit,
            "offset": self.offset,
            "has_more": self.has_more,
            "error": self.error.to_dict() if hasattr(self.error, 'to_dict') else self.error,
        }


@dataclass
class MaterialDetailRequest:
    """Request for material details by key."""
    material_key: str


@dataclass
class MaterialDetailResponse:
    """Response with material details."""
    status: Literal["success", "error", "not_found"]
    material: Optional[MaterialInfo] = None
    error: Optional[Any] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to JSON-serializable dictionary"""
        result = {"status": self.status}
        if self.material:
            result["material"] = {
                "key": self.material.key,
                "name": self.material.name,
                "category": self.material.category,
                "nrc": self.material.nrc,
                "absorption_coefficients": self.material.absorption_coefficients,
                "description": self.material.description,
                "manufacturer": self.material.manufacturer,
            }
        if self.error:
            result["error"] = self.error.to_dict() if hasattr(self.error, 'to_dict') else self.error
        return result


@dataclass
class CategoryInfo:
    """Information about a material category."""
    name: str
    display_name: str
    material_count: int
    description: str


@dataclass
class CategoryListResponse:
    """Response with material categories."""
    status: Literal["success", "error"]
    categories: List[CategoryInfo] = field(default_factory=list)
    total_materials: int = 0
    error: Optional[Any] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to JSON-serializable dictionary"""
        return {
            "status": self.status,
            "categories": [
                {
                    "name": c.name,
                    "display_name": c.display_name,
                    "material_count": c.material_count,
                    "description": c.description,
                }
                for c in self.categories
            ],
            "total_materials": self.total_materials,
            "error": self.error.to_dict() if hasattr(self.error, 'to_dict') else self.error,
        }
