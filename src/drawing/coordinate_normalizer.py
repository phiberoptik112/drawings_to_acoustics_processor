"""
Coordinate Normalization Utility

Centralizes all coordinate transformations and normalizations for the drawing overlay system.
Provides consistent, reliable coordinate handling with proper error handling and validation.
"""

import logging
from typing import Dict, List, Any, Optional, Tuple, Union
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class CoordinateTransform:
    """Represents a coordinate transformation with zoom factor and validation"""
    source_zoom: float
    target_zoom: float
    x_offset: float = 0.0
    y_offset: float = 0.0

    def __post_init__(self):
        if self.source_zoom <= 0:
            raise ValueError(f"Invalid source zoom: {self.source_zoom}")
        if self.target_zoom <= 0:
            raise ValueError(f"Invalid target zoom: {self.target_zoom}")


@dataclass
class NormalizedCoordinates:
    """Container for normalized coordinate data with metadata"""
    x: float
    y: float
    width: Optional[float] = None
    height: Optional[float] = None
    original_zoom: float = 1.0
    normalized_zoom: float = 1.0
    is_valid: bool = True
    error_message: Optional[str] = None


class CoordinateNormalizer:
    """
    Centralized coordinate normalization with error handling and caching.

    Handles all coordinate transformations between different zoom levels,
    provides validation, and ensures consistency across the drawing system.
    """

    def __init__(self, tolerance: float = 0.5):
        """
        Initialize coordinate normalizer.

        Args:
            tolerance: Coordinate matching tolerance in pixels
        """
        self.tolerance = tolerance
        self._transform_cache: Dict[str, CoordinateTransform] = {}
        self._coordinate_cache: Dict[str, NormalizedCoordinates] = {}

    def normalize_element_coordinates(
        self,
        element: Dict[str, Any],
        target_zoom: float = 1.0,
        use_cache: bool = True
    ) -> NormalizedCoordinates:
        """
        Normalize element coordinates to target zoom level.

        Args:
            element: Element dictionary with coordinate data
            target_zoom: Target zoom level for normalization
            use_cache: Whether to use cached results

        Returns:
            NormalizedCoordinates with normalized values or error information
        """
        try:
            if not self._validate_element_structure(element):
                return NormalizedCoordinates(
                    x=0, y=0, is_valid=False,
                    error_message="Invalid element structure"
                )

            # Get cache key for this normalization
            cache_key = self._get_cache_key(element, target_zoom)
            if use_cache and cache_key in self._coordinate_cache:
                return self._coordinate_cache[cache_key]

            # Extract coordinates with safe fallbacks
            x = self._safe_float_extract(element, 'x', 0.0)
            y = self._safe_float_extract(element, 'y', 0.0)
            width = self._safe_float_extract(element, 'width', None)
            height = self._safe_float_extract(element, 'height', None)

            # Get source zoom level
            source_zoom = self._extract_zoom_factor(element)

            # Create transformation
            transform = self._get_or_create_transform(source_zoom, target_zoom)

            # Apply transformation
            norm_coords = self._apply_transform(
                x, y, width, height, transform, source_zoom
            )

            # Cache result if successful
            if use_cache and norm_coords.is_valid:
                self._coordinate_cache[cache_key] = norm_coords

            return norm_coords

        except Exception as e:
            logger.error(f"Coordinate normalization failed: {e}")
            return NormalizedCoordinates(
                x=0, y=0, is_valid=False,
                error_message=f"Normalization error: {str(e)}"
            )

    def coordinates_match(
        self,
        coord1: Union[Dict[str, Any], NormalizedCoordinates],
        coord2: Union[Dict[str, Any], NormalizedCoordinates],
        tolerance: Optional[float] = None
    ) -> bool:
        """
        Check if two coordinate sets match within tolerance.

        Args:
            coord1: First coordinate set
            coord2: Second coordinate set
            tolerance: Override default tolerance

        Returns:
            True if coordinates match within tolerance
        """
        try:
            tol = tolerance or self.tolerance

            # Normalize both coordinates to same zoom level
            norm1 = self._normalize_for_comparison(coord1)
            norm2 = self._normalize_for_comparison(coord2)

            if not norm1.is_valid or not norm2.is_valid:
                return False

            # Check position match
            if (abs(norm1.x - norm2.x) > tol or
                abs(norm1.y - norm2.y) > tol):
                return False

            # Check dimension match if both have dimensions
            if (norm1.width is not None and norm2.width is not None and
                abs(norm1.width - norm2.width) > tol):
                return False

            if (norm1.height is not None and norm2.height is not None and
                abs(norm1.height - norm2.height) > tol):
                return False

            return True

        except Exception as e:
            logger.error(f"Coordinate matching failed: {e}")
            return False

    def denormalize_coordinates(
        self,
        normalized_coords: NormalizedCoordinates,
        target_zoom: float
    ) -> Dict[str, Any]:
        """
        Convert normalized coordinates back to target zoom level.

        Args:
            normalized_coords: Normalized coordinate data
            target_zoom: Target zoom level

        Returns:
            Dictionary with denormalized coordinate values
        """
        try:
            if not normalized_coords.is_valid:
                raise ValueError(f"Invalid normalized coordinates: {normalized_coords.error_message}")

            if target_zoom <= 0:
                raise ValueError(f"Invalid target zoom: {target_zoom}")

            # Calculate zoom ratio
            zoom_ratio = target_zoom / normalized_coords.normalized_zoom

            result = {
                'x': normalized_coords.x * zoom_ratio,
                'y': normalized_coords.y * zoom_ratio,
            }

            if normalized_coords.width is not None:
                result['width'] = normalized_coords.width * zoom_ratio

            if normalized_coords.height is not None:
                result['height'] = normalized_coords.height * zoom_ratio

            return result

        except Exception as e:
            logger.error(f"Coordinate denormalization failed: {e}")
            return {'x': 0, 'y': 0, 'error': str(e)}

    def clear_cache(self):
        """Clear coordinate and transform caches"""
        self._coordinate_cache.clear()
        self._transform_cache.clear()

    def get_cache_stats(self) -> Dict[str, int]:
        """Get cache statistics for debugging"""
        return {
            'coordinate_cache_size': len(self._coordinate_cache),
            'transform_cache_size': len(self._transform_cache)
        }

    # Private helper methods

    def _validate_element_structure(self, element: Dict[str, Any]) -> bool:
        """Validate element has required coordinate fields"""
        if not isinstance(element, dict):
            return False

        required_fields = ['x', 'y']
        return all(field in element for field in required_fields)

    def _safe_float_extract(
        self,
        element: Dict[str, Any],
        key: str,
        default: Optional[float]
    ) -> Optional[float]:
        """Safely extract float value from element with validation"""
        try:
            value = element.get(key, default)
            if value is None:
                return None
            return float(value)
        except (ValueError, TypeError):
            logger.warning(f"Invalid {key} value in element: {element.get(key)}")
            return default

    def _extract_zoom_factor(self, element: Dict[str, Any]) -> float:
        """Extract zoom factor from element with safe fallback"""
        zoom_fields = ['saved_zoom', 'zoom_factor', 'current_zoom']

        for field in zoom_fields:
            try:
                zoom = element.get(field)
                if zoom is not None:
                    zoom_val = float(zoom)
                    if zoom_val > 0:
                        return zoom_val
            except (ValueError, TypeError):
                continue

        return 1.0  # Safe default

    def _get_cache_key(self, element: Dict[str, Any], target_zoom: float) -> str:
        """Generate cache key for coordinate transformation"""
        elem_id = element.get('id', '')
        source_zoom = self._extract_zoom_factor(element)
        x = element.get('x', 0)
        y = element.get('y', 0)

        return f"{elem_id}_{source_zoom}_{target_zoom}_{x}_{y}"

    def _get_or_create_transform(
        self,
        source_zoom: float,
        target_zoom: float
    ) -> CoordinateTransform:
        """Get or create coordinate transform with caching"""
        cache_key = f"{source_zoom}_{target_zoom}"

        if cache_key not in self._transform_cache:
            self._transform_cache[cache_key] = CoordinateTransform(
                source_zoom=source_zoom,
                target_zoom=target_zoom
            )

        return self._transform_cache[cache_key]

    def _apply_transform(
        self,
        x: float,
        y: float,
        width: Optional[float],
        height: Optional[float],
        transform: CoordinateTransform,
        original_zoom: float
    ) -> NormalizedCoordinates:
        """Apply coordinate transformation with validation"""
        try:
            zoom_ratio = transform.target_zoom / transform.source_zoom

            norm_x = (x + transform.x_offset) * zoom_ratio
            norm_y = (y + transform.y_offset) * zoom_ratio
            norm_width = width * zoom_ratio if width is not None else None
            norm_height = height * zoom_ratio if height is not None else None

            return NormalizedCoordinates(
                x=norm_x,
                y=norm_y,
                width=norm_width,
                height=norm_height,
                original_zoom=original_zoom,
                normalized_zoom=transform.target_zoom,
                is_valid=True
            )

        except Exception as e:
            return NormalizedCoordinates(
                x=0, y=0, is_valid=False,
                error_message=f"Transform application failed: {str(e)}"
            )

    def _normalize_for_comparison(
        self,
        coords: Union[Dict[str, Any], NormalizedCoordinates]
    ) -> NormalizedCoordinates:
        """Normalize coordinates for comparison purposes"""
        if isinstance(coords, NormalizedCoordinates):
            return coords

        return self.normalize_element_coordinates(coords, target_zoom=1.0)


# Global instance for application-wide use
coordinate_normalizer = CoordinateNormalizer()