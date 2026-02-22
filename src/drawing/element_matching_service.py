"""
Element Matching Service

Provides robust, isolated element matching strategies for the drawing overlay system.
Handles database element to overlay element matching with proper error isolation and fallback mechanisms.
"""

import logging
from typing import Dict, List, Any, Optional, Set, Tuple, Union, Protocol
from enum import Enum
from dataclasses import dataclass, field
import time

from .coordinate_normalizer import CoordinateNormalizer

logger = logging.getLogger(__name__)


class MatchingStrategy(Enum):
    """Available element matching strategies"""
    DATABASE_ID = "database_id"
    ELEMENT_ID = "element_id"
    COORDINATE_BASED = "coordinate_based"
    HYBRID_FUZZY = "hybrid_fuzzy"


@dataclass
class MatchingResult:
    """Result of element matching operation"""
    success: bool
    matched_element: Optional[Dict[str, Any]] = None
    strategy_used: Optional[MatchingStrategy] = None
    confidence: float = 0.0
    error_message: Optional[str] = None
    debug_info: Dict[str, Any] = field(default_factory=dict)


@dataclass
class MatchingContext:
    """Context information for element matching"""
    available_elements: List[Dict[str, Any]]
    element_indexes: Dict[str, Dict[str, Any]]
    coordinate_tolerance: float = 10.0
    zoom_tolerance: float = 0.1
    performance_mode: bool = False


class ElementMatchingStrategy(Protocol):
    """Protocol for element matching strategies"""

    def match(
        self,
        target_element: Dict[str, Any],
        context: MatchingContext
    ) -> MatchingResult:
        """Match target element against available elements"""
        ...

    def get_priority(self) -> int:
        """Get strategy priority (lower = higher priority)"""
        ...


class DatabaseIdMatcher(ElementMatchingStrategy):
    """Matches elements using database IDs with high confidence"""

    def __init__(self, normalizer: CoordinateNormalizer):
        self.normalizer = normalizer

    def match(
        self,
        target_element: Dict[str, Any],
        context: MatchingContext
    ) -> MatchingResult:
        """Match using database ID with validation"""
        try:
            db_id = target_element.get('db_id')
            if not db_id:
                return MatchingResult(
                    success=False,
                    error_message="No database ID available",
                    debug_info={'strategy': 'database_id', 'has_db_id': False}
                )

            # Look for element with matching database ID
            for element in context.available_elements:
                if element.get('db_id') == db_id:
                    # Validate coordinate proximity for additional confidence
                    coord_match = self._validate_coordinate_proximity(
                        target_element, element, context.coordinate_tolerance
                    )

                    confidence = 0.95 if coord_match else 0.80

                    return MatchingResult(
                        success=True,
                        matched_element=element,
                        strategy_used=MatchingStrategy.DATABASE_ID,
                        confidence=confidence,
                        debug_info={
                            'strategy': 'database_id',
                            'db_id': db_id,
                            'coordinate_match': coord_match,
                            'confidence': confidence
                        }
                    )

            return MatchingResult(
                success=False,
                error_message=f"No element found with database ID: {db_id}",
                debug_info={'strategy': 'database_id', 'db_id': db_id, 'found': False}
            )

        except Exception as e:
            logger.error(f"Database ID matching failed: {e}")
            return MatchingResult(
                success=False,
                error_message=f"Database ID matching error: {str(e)}",
                debug_info={'strategy': 'database_id', 'exception': str(e)}
            )

    def get_priority(self) -> int:
        return 1

    def _validate_coordinate_proximity(
        self,
        target: Dict[str, Any],
        candidate: Dict[str, Any],
        tolerance: float
    ) -> bool:
        """Validate that coordinates are reasonably close"""
        try:
            return self.normalizer.coordinates_match(target, candidate, tolerance)
        except Exception:
            return False


class ElementIdMatcher(ElementMatchingStrategy):
    """Matches elements using element IDs with fallback validation"""

    def __init__(self, normalizer: CoordinateNormalizer):
        self.normalizer = normalizer

    def match(
        self,
        target_element: Dict[str, Any],
        context: MatchingContext
    ) -> MatchingResult:
        """Match using element ID with coordinate validation"""
        try:
            element_id = target_element.get('id')
            if not element_id:
                return MatchingResult(
                    success=False,
                    error_message="No element ID available",
                    debug_info={'strategy': 'element_id', 'has_element_id': False}
                )

            # Check element ID index first
            if element_id in context.element_indexes.get('by_element_id', {}):
                candidate = context.element_indexes['by_element_id'][element_id]

                # Validate coordinate match
                coord_match = self.normalizer.coordinates_match(
                    target_element, candidate, context.coordinate_tolerance
                )

                if coord_match:
                    return MatchingResult(
                        success=True,
                        matched_element=candidate,
                        strategy_used=MatchingStrategy.ELEMENT_ID,
                        confidence=0.85,
                        debug_info={
                            'strategy': 'element_id',
                            'element_id': element_id,
                            'coordinate_match': True,
                            'confidence': 0.85
                        }
                    )

            return MatchingResult(
                success=False,
                error_message=f"No valid match found for element ID: {element_id}",
                debug_info={'strategy': 'element_id', 'element_id': element_id, 'found': False}
            )

        except Exception as e:
            logger.error(f"Element ID matching failed: {e}")
            return MatchingResult(
                success=False,
                error_message=f"Element ID matching error: {str(e)}",
                debug_info={'strategy': 'element_id', 'exception': str(e)}
            )

    def get_priority(self) -> int:
        return 2


class CoordinateBasedMatcher(ElementMatchingStrategy):
    """Matches elements based on coordinate proximity"""

    def __init__(self, normalizer: CoordinateNormalizer):
        self.normalizer = normalizer

    def match(
        self,
        target_element: Dict[str, Any],
        context: MatchingContext
    ) -> MatchingResult:
        """Match using coordinate proximity with confidence scoring"""
        try:
            best_match = None
            best_confidence = 0.0
            best_distance = float('inf')

            target_coords = self.normalizer.normalize_element_coordinates(target_element)
            if not target_coords.is_valid:
                return MatchingResult(
                    success=False,
                    error_message=f"Invalid target coordinates: {target_coords.error_message}",
                    debug_info={'strategy': 'coordinate_based', 'invalid_coords': True}
                )

            # Search through available elements
            for candidate in context.available_elements:
                candidate_coords = self.normalizer.normalize_element_coordinates(candidate)
                if not candidate_coords.is_valid:
                    continue

                # Calculate distance
                distance = self._calculate_distance(target_coords, candidate_coords)

                if distance <= context.coordinate_tolerance:
                    # Calculate confidence based on proximity
                    confidence = max(0.1, 1.0 - (distance / context.coordinate_tolerance))

                    if confidence > best_confidence:
                        best_match = candidate
                        best_confidence = confidence
                        best_distance = distance

            if best_match:
                return MatchingResult(
                    success=True,
                    matched_element=best_match,
                    strategy_used=MatchingStrategy.COORDINATE_BASED,
                    confidence=best_confidence,
                    debug_info={
                        'strategy': 'coordinate_based',
                        'distance': best_distance,
                        'tolerance': context.coordinate_tolerance,
                        'confidence': best_confidence
                    }
                )

            return MatchingResult(
                success=False,
                error_message="No coordinate-based match found within tolerance",
                debug_info={
                    'strategy': 'coordinate_based',
                    'tolerance': context.coordinate_tolerance,
                    'candidates_checked': len(context.available_elements)
                }
            )

        except Exception as e:
            logger.error(f"Coordinate-based matching failed: {e}")
            return MatchingResult(
                success=False,
                error_message=f"Coordinate matching error: {str(e)}",
                debug_info={'strategy': 'coordinate_based', 'exception': str(e)}
            )

    def get_priority(self) -> int:
        return 3

    def _calculate_distance(self, coords1, coords2) -> float:
        """Calculate Euclidean distance between coordinates"""
        try:
            dx = coords1.x - coords2.x
            dy = coords1.y - coords2.y
            return (dx * dx + dy * dy) ** 0.5
        except Exception:
            return float('inf')


class HybridFuzzyMatcher(ElementMatchingStrategy):
    """Fuzzy matching combining multiple attributes with scoring"""

    def __init__(self, normalizer: CoordinateNormalizer):
        self.normalizer = normalizer

    def match(
        self,
        target_element: Dict[str, Any],
        context: MatchingContext
    ) -> MatchingResult:
        """Fuzzy match using multiple element attributes"""
        try:
            best_match = None
            best_score = 0.0

            target_type = target_element.get('type', '')
            target_coords = self.normalizer.normalize_element_coordinates(target_element)

            for candidate in context.available_elements:
                score = self._calculate_fuzzy_score(
                    target_element, candidate, target_coords, target_type, context
                )

                if score > best_score and score > 0.6:  # Minimum threshold
                    best_match = candidate
                    best_score = score

            if best_match:
                return MatchingResult(
                    success=True,
                    matched_element=best_match,
                    strategy_used=MatchingStrategy.HYBRID_FUZZY,
                    confidence=best_score,
                    debug_info={
                        'strategy': 'hybrid_fuzzy',
                        'fuzzy_score': best_score,
                        'threshold': 0.6
                    }
                )

            return MatchingResult(
                success=False,
                error_message="No fuzzy match found above threshold",
                debug_info={
                    'strategy': 'hybrid_fuzzy',
                    'best_score': best_score,
                    'threshold': 0.6
                }
            )

        except Exception as e:
            logger.error(f"Fuzzy matching failed: {e}")
            return MatchingResult(
                success=False,
                error_message=f"Fuzzy matching error: {str(e)}",
                debug_info={'strategy': 'hybrid_fuzzy', 'exception': str(e)}
            )

    def get_priority(self) -> int:
        return 4

    def _calculate_fuzzy_score(
        self,
        target: Dict[str, Any],
        candidate: Dict[str, Any],
        target_coords,
        target_type: str,
        context: MatchingContext
    ) -> float:
        """Calculate fuzzy matching score"""
        try:
            score = 0.0

            # Type match (30% weight)
            if target_type and target_type == candidate.get('type', ''):
                score += 0.3

            # Coordinate proximity (50% weight)
            if target_coords.is_valid:
                candidate_coords = self.normalizer.normalize_element_coordinates(candidate)
                if candidate_coords.is_valid:
                    distance = ((target_coords.x - candidate_coords.x) ** 2 +
                              (target_coords.y - candidate_coords.y) ** 2) ** 0.5
                    if distance <= context.coordinate_tolerance:
                        proximity_score = 1.0 - (distance / context.coordinate_tolerance)
                        score += 0.5 * proximity_score

            # Dimension similarity (20% weight)
            if (target_coords.width and target_coords.height and
                candidate.get('width') and candidate.get('height')):
                width_ratio = min(target_coords.width, candidate['width']) / max(target_coords.width, candidate['width'])
                height_ratio = min(target_coords.height, candidate['height']) / max(target_coords.height, candidate['height'])
                dimension_score = (width_ratio + height_ratio) / 2
                score += 0.2 * dimension_score

            return min(score, 1.0)

        except Exception:
            return 0.0


class ElementMatchingService:
    """
    Main service for element matching with isolated strategies and error recovery.

    Provides robust element matching with fallback strategies, comprehensive error
    handling, and performance optimization for large element sets.
    """

    def __init__(self, coordinate_normalizer: CoordinateNormalizer = None):
        """
        Initialize element matching service.

        Args:
            coordinate_normalizer: Optional custom coordinate normalizer
        """
        self.normalizer = coordinate_normalizer or CoordinateNormalizer()
        self.strategies: List[ElementMatchingStrategy] = []
        self._initialize_strategies()

        # Performance and debug tracking
        self._match_stats = {
            'total_matches': 0,
            'successful_matches': 0,
            'strategy_usage': {strategy.value: 0 for strategy in MatchingStrategy}
        }

    def match_element(
        self,
        target_element: Dict[str, Any],
        available_elements: List[Dict[str, Any]],
        context_overrides: Optional[Dict[str, Any]] = None
    ) -> MatchingResult:
        """
        Match target element against available elements using best strategy.

        Args:
            target_element: Element to find match for
            available_elements: List of candidate elements
            context_overrides: Optional context parameter overrides

        Returns:
            MatchingResult with best match found or failure information
        """
        start_time = time.time()
        self._match_stats['total_matches'] += 1

        try:
            # Build matching context
            context = self._build_matching_context(available_elements, context_overrides)

            # Try strategies in priority order
            for strategy in self.strategies:
                try:
                    result = strategy.match(target_element, context)

                    if result.success:
                        self._update_success_stats(result.strategy_used)
                        result.debug_info['match_time_ms'] = (time.time() - start_time) * 1000
                        return result

                    # Log failed attempt for debugging
                    logger.debug(f"Strategy {strategy.__class__.__name__} failed: {result.error_message}")

                except Exception as e:
                    logger.error(f"Strategy {strategy.__class__.__name__} threw exception: {e}")
                    continue

            # No strategy succeeded
            return MatchingResult(
                success=False,
                error_message="All matching strategies failed",
                debug_info={
                    'strategies_tried': len(self.strategies),
                    'match_time_ms': (time.time() - start_time) * 1000,
                    'available_elements': len(available_elements)
                }
            )

        except Exception as e:
            logger.error(f"Element matching service failed: {e}")
            return MatchingResult(
                success=False,
                error_message=f"Service error: {str(e)}",
                debug_info={'exception': str(e)}
            )

    def batch_match_elements(
        self,
        target_elements: List[Dict[str, Any]],
        available_elements: List[Dict[str, Any]],
        context_overrides: Optional[Dict[str, Any]] = None
    ) -> List[MatchingResult]:
        """
        Efficiently match multiple elements using shared context.

        Args:
            target_elements: Elements to find matches for
            available_elements: Candidate elements
            context_overrides: Optional context overrides

        Returns:
            List of MatchingResult objects
        """
        results = []
        context = self._build_matching_context(available_elements, context_overrides)

        for target in target_elements:
            try:
                result = self._match_single_with_context(target, context)
                results.append(result)
            except Exception as e:
                logger.error(f"Batch matching failed for element: {e}")
                results.append(MatchingResult(
                    success=False,
                    error_message=f"Batch match error: {str(e)}"
                ))

        return results

    def get_matching_statistics(self) -> Dict[str, Any]:
        """Get matching performance statistics"""
        success_rate = (
            self._match_stats['successful_matches'] / max(self._match_stats['total_matches'], 1) * 100
        )

        return {
            'total_matches': self._match_stats['total_matches'],
            'successful_matches': self._match_stats['successful_matches'],
            'success_rate_percent': round(success_rate, 2),
            'strategy_usage': self._match_stats['strategy_usage'].copy(),
            'cache_stats': self.normalizer.get_cache_stats()
        }

    def reset_statistics(self):
        """Reset matching statistics"""
        self._match_stats = {
            'total_matches': 0,
            'successful_matches': 0,
            'strategy_usage': {strategy.value: 0 for strategy in MatchingStrategy}
        }

    # Private helper methods

    def _initialize_strategies(self):
        """Initialize matching strategies in priority order"""
        self.strategies = [
            DatabaseIdMatcher(self.normalizer),
            ElementIdMatcher(self.normalizer),
            CoordinateBasedMatcher(self.normalizer),
            HybridFuzzyMatcher(self.normalizer)
        ]

        # Sort by priority (lower number = higher priority)
        self.strategies.sort(key=lambda s: s.get_priority())

    def _build_matching_context(
        self,
        available_elements: List[Dict[str, Any]],
        overrides: Optional[Dict[str, Any]]
    ) -> MatchingContext:
        """Build matching context with element indexes"""

        # Build indexes for fast lookups
        element_indexes = {
            'by_element_id': {},
            'by_db_id': {}
        }

        for element in available_elements:
            if element.get('id'):
                element_indexes['by_element_id'][element['id']] = element
            if element.get('db_id'):
                element_indexes['by_db_id'][element['db_id']] = element

        # Apply overrides
        context_params = {
            'available_elements': available_elements,
            'element_indexes': element_indexes,
            'coordinate_tolerance': 10.0,
            'zoom_tolerance': 0.1,
            'performance_mode': False
        }

        if overrides:
            context_params.update(overrides)

        return MatchingContext(**context_params)

    def _match_single_with_context(
        self,
        target_element: Dict[str, Any],
        context: MatchingContext
    ) -> MatchingResult:
        """Match single element using existing context"""
        for strategy in self.strategies:
            try:
                result = strategy.match(target_element, context)
                if result.success:
                    self._update_success_stats(result.strategy_used)
                    return result
            except Exception as e:
                logger.error(f"Strategy {strategy.__class__.__name__} failed: {e}")
                continue

        return MatchingResult(
            success=False,
            error_message="All strategies failed for element"
        )

    def _update_success_stats(self, strategy_used: Optional[MatchingStrategy]):
        """Update success statistics"""
        self._match_stats['successful_matches'] += 1
        if strategy_used:
            self._match_stats['strategy_usage'][strategy_used.value] += 1


# Global service instance
element_matching_service = ElementMatchingService()