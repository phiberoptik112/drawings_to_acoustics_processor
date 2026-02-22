"""
Element Matching Integration Layer

Provides backward-compatible integration layer for migrating the drawing overlay system
to use the new robust element matching service while preserving existing functionality.
"""

import logging
from typing import Dict, List, Any, Optional, Tuple, Set
from dataclasses import dataclass

from .coordinate_normalizer import CoordinateNormalizer
from .element_matching_service import ElementMatchingService, MatchingResult

logger = logging.getLogger(__name__)


@dataclass
class ElementLinkResult:
    """Result of element linking operation for backward compatibility"""
    success: bool
    linked_elements: List[Dict[str, Any]]
    failed_elements: List[Dict[str, Any]]
    performance_stats: Dict[str, Any]
    error_messages: List[str]


class LegacyElementMatcher:
    """
    Legacy-compatible element matching wrapper.

    Provides backward compatibility for existing drawing overlay code while
    gradually migrating to the new robust element matching system.
    """

    def __init__(self, matching_service: Optional[ElementMatchingService] = None):
        """
        Initialize legacy element matcher.

        Args:
            matching_service: Optional custom matching service
        """
        self.matching_service = matching_service or ElementMatchingService()
        self.coordinate_normalizer = self.matching_service.normalizer
        self._compatibility_mode = True

    def link_hvac_segments_to_components(
        self,
        segments_data: List[Dict[str, Any]],
        overlay_components: List[Dict[str, Any]],
        path_id: Optional[int] = None
    ) -> ElementLinkResult:
        """
        Legacy-compatible segment to component linking.

        Replaces the complex logic in drawing_overlay.py with robust matching.
        """
        try:
            linked_segments = []
            failed_segments = []
            error_messages = []
            performance_stats = {'segments_processed': 0, 'successful_links': 0}

            logger.info(f"Linking {len(segments_data)} segments to {len(overlay_components)} components")

            for segment in segments_data:
                performance_stats['segments_processed'] += 1

                try:
                    # Link from_component
                    from_result = self._link_segment_endpoint(
                        segment, 'from_component', overlay_components
                    )

                    # Link to_component
                    to_result = self._link_segment_endpoint(
                        segment, 'to_component', overlay_components
                    )

                    if from_result.success or to_result.success:
                        # Update segment with linked components
                        if from_result.success:
                            segment['from_component'] = from_result.matched_element
                        if to_result.success:
                            segment['to_component'] = to_result.matched_element

                        linked_segments.append(segment)
                        performance_stats['successful_links'] += 1

                        logger.debug(f"Successfully linked segment {segment.get('id', 'unknown')}")

                    else:
                        failed_segments.append(segment)
                        error_msg = f"Failed to link segment {segment.get('id', 'unknown')}: " \
                                  f"from_component: {from_result.error_message}, " \
                                  f"to_component: {to_result.error_message}"
                        error_messages.append(error_msg)

                except Exception as e:
                    logger.error(f"Exception linking segment: {e}")
                    failed_segments.append(segment)
                    error_messages.append(f"Exception linking segment: {str(e)}")

            return ElementLinkResult(
                success=len(linked_segments) > 0,
                linked_elements=linked_segments,
                failed_elements=failed_segments,
                performance_stats=performance_stats,
                error_messages=error_messages
            )

        except Exception as e:
            logger.error(f"Segment linking failed: {e}")
            return ElementLinkResult(
                success=False,
                linked_elements=[],
                failed_elements=segments_data,
                performance_stats={'error': str(e)},
                error_messages=[f"Linking failed: {str(e)}"]
            )

    def register_path_elements_robust(
        self,
        path_id: int,
        overlay_components: List[Dict[str, Any]],
        overlay_segments: List[Dict[str, Any]],
        db_components: List[Dict[str, Any]] = None,
        db_segments: List[Dict[str, Any]] = None
    ) -> ElementLinkResult:
        """
        Robustly register path elements using the new matching service.

        Replaces the fragile registration logic with isolated error handling.
        """
        try:
            all_matched_elements = []
            all_failed_elements = []
            error_messages = []

            # Match components
            if db_components:
                comp_result = self._match_elements_batch(
                    db_components, overlay_components, f"components for path {path_id}"
                )
                all_matched_elements.extend(comp_result.linked_elements)
                all_failed_elements.extend(comp_result.failed_elements)
                error_messages.extend(comp_result.error_messages)

            # Match segments
            if db_segments:
                seg_result = self._match_elements_batch(
                    db_segments, overlay_segments, f"segments for path {path_id}"
                )
                all_matched_elements.extend(seg_result.linked_elements)
                all_failed_elements.extend(seg_result.failed_elements)
                error_messages.extend(seg_result.error_messages)

            # Mark all matched elements as belonging to this path
            for element in all_matched_elements:
                if not isinstance(element.get('registered_path_ids'), set):
                    element['registered_path_ids'] = set()
                element['registered_path_ids'].add(path_id)

            performance_stats = {
                'total_elements': len(all_matched_elements) + len(all_failed_elements),
                'successful_matches': len(all_matched_elements),
                'failed_matches': len(all_failed_elements),
                'path_id': path_id
            }

            return ElementLinkResult(
                success=len(all_matched_elements) > 0,
                linked_elements=all_matched_elements,
                failed_elements=all_failed_elements,
                performance_stats=performance_stats,
                error_messages=error_messages
            )

        except Exception as e:
            logger.error(f"Path element registration failed: {e}")
            return ElementLinkResult(
                success=False,
                linked_elements=[],
                failed_elements=(db_components or []) + (db_segments or []),
                performance_stats={'error': str(e)},
                error_messages=[f"Registration failed: {str(e)}"]
            )

    def cleanup_orphaned_elements_safe(
        self,
        overlay_elements: List[Dict[str, Any]],
        protected_path_ids: Set[int]
    ) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
        """
        Safely clean up orphaned elements while protecting registered path elements.

        Args:
            overlay_elements: Elements to check for cleanup
            protected_path_ids: Path IDs that should be protected from cleanup

        Returns:
            Tuple of (elements_to_keep, elements_to_remove)
        """
        try:
            elements_to_keep = []
            elements_to_remove = []

            for element in overlay_elements:
                try:
                    # Check if element belongs to any protected path
                    element_path_ids = element.get('registered_path_ids', set())

                    if isinstance(element_path_ids, set) and element_path_ids:
                        # Has path registrations - check if any are protected
                        if element_path_ids.intersection(protected_path_ids):
                            elements_to_keep.append(element)
                        else:
                            elements_to_remove.append(element)
                    else:
                        # No path registration - safe to remove
                        elements_to_remove.append(element)

                except Exception as e:
                    logger.warning(f"Error checking element protection status: {e}")
                    # When in doubt, keep the element to avoid data loss
                    elements_to_keep.append(element)

            logger.info(f"Cleanup: keeping {len(elements_to_keep)}, removing {len(elements_to_remove)}")

            return elements_to_keep, elements_to_remove

        except Exception as e:
            logger.error(f"Safe cleanup failed: {e}")
            # On error, keep all elements to prevent data loss
            return overlay_elements, []

    def normalize_coordinates_batch(
        self,
        elements: List[Dict[str, Any]],
        target_zoom: float = 1.0
    ) -> List[Dict[str, Any]]:
        """
        Batch normalize coordinates for multiple elements.

        Provides backward compatibility while using the robust coordinate normalizer.
        """
        normalized_elements = []

        for element in elements:
            try:
                normalized_coords = self.coordinate_normalizer.normalize_element_coordinates(
                    element, target_zoom=target_zoom
                )

                if normalized_coords.is_valid:
                    # Update element with normalized coordinates
                    updated_element = element.copy()
                    updated_element.update({
                        'x': normalized_coords.x,
                        'y': normalized_coords.y,
                        'normalized_zoom': normalized_coords.normalized_zoom
                    })

                    if normalized_coords.width is not None:
                        updated_element['width'] = normalized_coords.width
                    if normalized_coords.height is not None:
                        updated_element['height'] = normalized_coords.height

                    normalized_elements.append(updated_element)
                else:
                    logger.warning(f"Failed to normalize element coordinates: {normalized_coords.error_message}")
                    # Keep original element as fallback
                    normalized_elements.append(element)

            except Exception as e:
                logger.error(f"Exception normalizing element: {e}")
                # Keep original element as fallback
                normalized_elements.append(element)

        return normalized_elements

    # Private helper methods

    def _link_segment_endpoint(
        self,
        segment: Dict[str, Any],
        endpoint_key: str,
        available_components: List[Dict[str, Any]]
    ) -> MatchingResult:
        """Link a segment endpoint to a component using robust matching"""
        try:
            endpoint_data = segment.get(endpoint_key)
            if not endpoint_data:
                return MatchingResult(
                    success=False,
                    error_message=f"No {endpoint_key} data in segment"
                )

            # Use the matching service to find the component
            result = self.matching_service.match_element(
                endpoint_data, available_components
            )

            if result.success:
                logger.debug(f"Linked {endpoint_key} using {result.strategy_used} strategy")

            return result

        except Exception as e:
            logger.error(f"Exception linking {endpoint_key}: {e}")
            return MatchingResult(
                success=False,
                error_message=f"Exception linking {endpoint_key}: {str(e)}"
            )

    def _match_elements_batch(
        self,
        target_elements: List[Dict[str, Any]],
        available_elements: List[Dict[str, Any]],
        context_name: str
    ) -> ElementLinkResult:
        """Match multiple elements using batch processing"""
        try:
            results = self.matching_service.batch_match_elements(
                target_elements, available_elements
            )

            linked_elements = []
            failed_elements = []
            error_messages = []

            for target, result in zip(target_elements, results):
                if result.success:
                    # Tag the matched overlay element with database info
                    matched_element = result.matched_element.copy()
                    matched_element['db_element'] = target
                    matched_element['match_confidence'] = result.confidence
                    matched_element['match_strategy'] = result.strategy_used.value if result.strategy_used else 'unknown'

                    linked_elements.append(matched_element)
                else:
                    failed_elements.append(target)
                    error_messages.append(f"{context_name}: {result.error_message}")

            performance_stats = {
                'context': context_name,
                'total_targets': len(target_elements),
                'successful_matches': len(linked_elements),
                'failed_matches': len(failed_elements),
                'match_rate_percent': len(linked_elements) / max(len(target_elements), 1) * 100
            }

            return ElementLinkResult(
                success=len(linked_elements) > 0,
                linked_elements=linked_elements,
                failed_elements=failed_elements,
                performance_stats=performance_stats,
                error_messages=error_messages
            )

        except Exception as e:
            logger.error(f"Batch matching failed for {context_name}: {e}")
            return ElementLinkResult(
                success=False,
                linked_elements=[],
                failed_elements=target_elements,
                performance_stats={'error': str(e)},
                error_messages=[f"Batch matching failed: {str(e)}"]
            )


# Compatibility functions for direct replacement of problematic overlay methods

def safe_register_path_elements(
    path_id: int,
    overlay_components: List[Dict[str, Any]],
    overlay_segments: List[Dict[str, Any]],
    db_components: List[Dict[str, Any]] = None,
    db_segments: List[Dict[str, Any]] = None,
    matcher: Optional[LegacyElementMatcher] = None
) -> ElementLinkResult:
    """
    Drop-in replacement for problematic path element registration.

    Can be used to replace the complex logic in drawing_overlay.py with minimal changes.
    """
    if matcher is None:
        matcher = LegacyElementMatcher()

    return matcher.register_path_elements_robust(
        path_id, overlay_components, overlay_segments, db_components, db_segments
    )


def safe_link_segments_to_components(
    segments_data: List[Dict[str, Any]],
    overlay_components: List[Dict[str, Any]],
    path_id: Optional[int] = None,
    matcher: Optional[LegacyElementMatcher] = None
) -> ElementLinkResult:
    """
    Drop-in replacement for problematic segment linking logic.

    Can be used to replace the complex logic in drawing_overlay.py with minimal changes.
    """
    if matcher is None:
        matcher = LegacyElementMatcher()

    return matcher.link_hvac_segments_to_components(segments_data, overlay_components, path_id)


# Global instance for application-wide use
legacy_element_matcher = LegacyElementMatcher()