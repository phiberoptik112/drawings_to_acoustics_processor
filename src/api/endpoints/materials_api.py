"""
Materials Service

API service for accessing the acoustic materials database.
"""

from typing import Dict, List, Optional, Any

from src.api.schemas.common import OCTAVE_BANDS_6, APIError, ErrorCode
from src.api.schemas.material_schemas import (
    MaterialSearchRequest,
    MaterialSearchResponse,
    MaterialDetailRequest,
    MaterialDetailResponse,
    CategoryListResponse,
    MaterialInfo,
    CategoryInfo,
)


class MaterialsService:
    """
    Materials database service for LLM agentic workflows.

    Provides access to the full acoustic materials database (1,339+ materials)
    with search, filtering, and detail retrieval.

    All methods are stateless and return complete material data.
    """

    def __init__(self):
        """Initialize the materials service."""
        self._materials_db = None
        self._category_cache = None

    def _get_materials_db(self) -> Dict:
        """Lazy load the materials database."""
        if self._materials_db is None:
            try:
                from src.data.materials_database import get_all_materials
                self._materials_db = get_all_materials()
            except ImportError:
                from src.data.materials import STANDARD_MATERIALS
                self._materials_db = STANDARD_MATERIALS
        return self._materials_db

    def _build_material_info(self, key: str, material: Dict) -> MaterialInfo:
        """Convert raw material data to MaterialInfo."""
        # Extract absorption coefficients
        coefficients = {}
        if 'coefficients' in material:
            raw_coeffs = material['coefficients']
            for freq in OCTAVE_BANDS_6:
                freq_str = str(freq)
                if freq_str in raw_coeffs:
                    coefficients[freq] = raw_coeffs[freq_str]
                elif freq in raw_coeffs:
                    coefficients[freq] = raw_coeffs[freq]

        # Fill missing with NRC
        nrc = material.get('nrc', material.get('absorption_coeff', 0.1))
        for freq in OCTAVE_BANDS_6:
            if freq not in coefficients:
                coefficients[freq] = nrc

        return MaterialInfo(
            key=key,
            name=material.get('name', key),
            category=material.get('category', 'unknown'),
            nrc=nrc,
            absorption_coefficients=coefficients,
            description=material.get('description'),
            manufacturer=material.get('manufacturer'),
        )

    def search_materials(self, request: MaterialSearchRequest) -> MaterialSearchResponse:
        """
        Search the materials database.

        Args:
            request: Search request with filters

        Returns:
            MaterialSearchResponse with matching materials
        """
        try:
            materials_db = self._get_materials_db()
            results = []

            # Apply filters
            for key, material in materials_db.items():
                # Text search
                if request.search_text:
                    search_lower = request.search_text.lower()
                    name = material.get('name', '').lower()
                    desc = material.get('description', '').lower()
                    category = material.get('category', '').lower()

                    if not (search_lower in name or search_lower in desc or search_lower in category):
                        continue

                # Category filter
                if request.category:
                    mat_category = material.get('category', '').lower()
                    if request.category.lower() not in mat_category:
                        continue

                # NRC filters
                nrc = material.get('nrc', material.get('absorption_coeff', 0))
                if request.min_nrc is not None and nrc < request.min_nrc:
                    continue
                if request.max_nrc is not None and nrc > request.max_nrc:
                    continue

                # Frequency-specific absorption filter
                if request.min_absorption_at_frequency:
                    coeffs = material.get('coefficients', {})
                    passes_filter = True
                    for freq, min_val in request.min_absorption_at_frequency.items():
                        freq_str = str(freq)
                        coeff = coeffs.get(freq_str, coeffs.get(freq, nrc))
                        if coeff < min_val:
                            passes_filter = False
                            break
                    if not passes_filter:
                        continue

                results.append(self._build_material_info(key, material))

            # Sort by NRC (highest first)
            results.sort(key=lambda m: m.nrc, reverse=True)

            # Apply pagination
            total_count = len(results)
            paginated = results[request.offset:request.offset + request.limit]
            has_more = request.offset + len(paginated) < total_count

            return MaterialSearchResponse(
                status="success",
                materials=paginated,
                total_count=total_count,
                limit=request.limit,
                offset=request.offset,
                has_more=has_more,
            )

        except Exception as e:
            return MaterialSearchResponse(
                status="error",
                error=APIError(
                    error_code=ErrorCode.CALCULATION_ERROR,
                    error_message=f"Material search failed: {str(e)}",
                    suggestion="Check search parameters and try again"
                )
            )

    def get_material(self, request: MaterialDetailRequest) -> MaterialDetailResponse:
        """
        Get detailed information about a specific material.

        Args:
            request: Request with material key

        Returns:
            MaterialDetailResponse with material info
        """
        try:
            materials_db = self._get_materials_db()

            if request.material_key not in materials_db:
                return MaterialDetailResponse(
                    status="not_found",
                    error=APIError(
                        error_code=ErrorCode.MATERIAL_NOT_FOUND,
                        error_message=f"Material '{request.material_key}' not found",
                        suggestion="Use search_materials() to find valid material keys"
                    )
                )

            material = materials_db[request.material_key]
            material_info = self._build_material_info(request.material_key, material)

            return MaterialDetailResponse(
                status="success",
                material=material_info,
            )

        except Exception as e:
            return MaterialDetailResponse(
                status="error",
                error=APIError(
                    error_code=ErrorCode.CALCULATION_ERROR,
                    error_message=f"Material lookup failed: {str(e)}",
                    suggestion="Check material key and try again"
                )
            )

    def list_categories(self) -> CategoryListResponse:
        """
        List all material categories with counts.

        Returns:
            CategoryListResponse with category information
        """
        try:
            materials_db = self._get_materials_db()

            # Count materials per category
            category_counts = {}
            for material in materials_db.values():
                category = material.get('category', 'unknown').lower()
                category_counts[category] = category_counts.get(category, 0) + 1

            # Build category info list
            category_descriptions = {
                "ceiling": "Ceiling tiles, panels, and acoustic clouds",
                "wall": "Wall panels, fabric systems, and acoustic treatments",
                "floor": "Carpet, flooring, and floor treatments",
                "panels": "Acoustic panels and baffles",
                "doors": "Acoustic doors and door seals",
                "windows": "Acoustic windows and glazing",
                "fabric": "Fabric-wrapped panels and curtains",
                "foam": "Acoustic foam and absorption materials",
            }

            categories = []
            for name, count in sorted(category_counts.items(), key=lambda x: -x[1]):
                categories.append(CategoryInfo(
                    name=name,
                    display_name=name.replace('_', ' ').title(),
                    material_count=count,
                    description=category_descriptions.get(name, f"Materials in the {name} category"),
                ))

            return CategoryListResponse(
                status="success",
                categories=categories,
                total_materials=len(materials_db),
            )

        except Exception as e:
            return CategoryListResponse(
                status="error",
                error=APIError(
                    error_code=ErrorCode.CALCULATION_ERROR,
                    error_message=f"Category listing failed: {str(e)}",
                    suggestion="Try again"
                )
            )

    def get_all_material_keys(self) -> List[str]:
        """
        Get all valid material keys.

        Returns:
            List of material keys
        """
        return list(self._get_materials_db().keys())

    def get_schema(self) -> Dict[str, Any]:
        """Return JSON schema for this service's endpoints."""
        return {
            "search_materials": {
                "description": "Search the materials database with filters",
                "input": "MaterialSearchRequest",
                "output": "MaterialSearchResponse",
                "optional_fields": [
                    "search_text",
                    "category",
                    "min_nrc",
                    "max_nrc",
                    "min_absorption_at_frequency",
                    "limit (default 50)",
                    "offset (default 0)"
                ]
            },
            "get_material": {
                "description": "Get detailed information about a specific material",
                "input": "MaterialDetailRequest",
                "output": "MaterialDetailResponse",
                "required_fields": ["material_key"]
            },
            "list_categories": {
                "description": "List all material categories with counts",
                "input": "None",
                "output": "CategoryListResponse"
            }
        }
