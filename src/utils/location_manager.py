"""
Location Manager - Utilities for managing drawing locations and bookmarks
"""

from models import get_session
from models.drawing_location import DrawingLocation, LocationType
from models.space import Space, RoomBoundary
from models.hvac import HVACPath, HVACComponent, HVACSegment
from sqlalchemy.orm import selectinload


class LocationManager:
    """Manages drawing locations for spaces and HVAC paths"""

    @staticmethod
    def create_or_update_space_location(space_id, drawing_id, drawing_set_id=None, page_number=1):
        """Create or update location bookmark for a space"""
        session = get_session()
        try:
            space = session.query(Space).filter(Space.id == space_id).first()
            if not space:
                return None

            # Try to get center point from room boundaries
            center_x, center_y, bbox = LocationManager._calculate_space_bounds(space)

            # Check if location already exists
            existing = (
                session.query(DrawingLocation)
                .filter(
                    DrawingLocation.location_type == LocationType.SPACE,
                    DrawingLocation.element_id == space_id,
                    DrawingLocation.drawing_id == drawing_id
                )
                .first()
            )

            if existing:
                # Update existing
                existing.element_name = space.name
                existing.drawing_set_id = drawing_set_id
                existing.page_number = page_number
                existing.center_x = center_x
                existing.center_y = center_y
                if bbox:
                    existing.bbox_x1, existing.bbox_y1, existing.bbox_x2, existing.bbox_y2 = bbox
                location = existing
            else:
                # Create new
                location = DrawingLocation(
                    location_type=LocationType.SPACE,
                    element_id=space_id,
                    element_name=space.name,
                    drawing_set_id=drawing_set_id,
                    drawing_id=drawing_id,
                    page_number=page_number,
                    center_x=center_x,
                    center_y=center_y
                )
                if bbox:
                    location.bbox_x1, location.bbox_y1, location.bbox_x2, location.bbox_y2 = bbox

                session.add(location)

            session.commit()
            return location
        finally:
            session.close()

    @staticmethod
    def create_or_update_hvac_path_location(path_id, drawing_id, drawing_set_id=None, page_number=1):
        """Create or update location bookmark for an HVAC path"""
        session = get_session()
        try:
            path = (
                session.query(HVACPath)
                .options(selectinload(HVACPath.segments).selectinload(HVACSegment.from_component))
                .filter(HVACPath.id == path_id)
                .first()
            )
            if not path:
                return None

            # Try to get center point from path components
            center_x, center_y, bbox = LocationManager._calculate_path_bounds(path)

            # Check if location already exists
            existing = (
                session.query(DrawingLocation)
                .filter(
                    DrawingLocation.location_type == LocationType.HVAC_PATH,
                    DrawingLocation.element_id == path_id,
                    DrawingLocation.drawing_id == drawing_id
                )
                .first()
            )

            if existing:
                # Update existing
                existing.element_name = path.name
                existing.drawing_set_id = drawing_set_id
                existing.page_number = page_number
                existing.center_x = center_x
                existing.center_y = center_y
                if bbox:
                    existing.bbox_x1, existing.bbox_y1, existing.bbox_x2, existing.bbox_y2 = bbox
                location = existing
            else:
                # Create new
                location = DrawingLocation(
                    location_type=LocationType.HVAC_PATH,
                    element_id=path_id,
                    element_name=path.name,
                    drawing_set_id=drawing_set_id,
                    drawing_id=drawing_id,
                    page_number=page_number,
                    center_x=center_x,
                    center_y=center_y
                )
                if bbox:
                    location.bbox_x1, location.bbox_y1, location.bbox_x2, location.bbox_y2 = bbox

                session.add(location)

            session.commit()
            return location
        finally:
            session.close()

    @staticmethod
    def get_locations_by_drawing_set(drawing_set_id):
        """Get all locations in a drawing set, grouped by drawing and page"""
        session = get_session()
        try:
            from sqlalchemy.orm import selectinload

            locations = (
                session.query(DrawingLocation)
                .options(selectinload(DrawingLocation.drawing))
                .filter(DrawingLocation.drawing_set_id == drawing_set_id)
                .order_by(DrawingLocation.drawing_id, DrawingLocation.page_number)
                .all()
            )

            # Group by drawing and page
            grouped = {}
            for loc in locations:
                key = (loc.drawing_id, loc.page_number)
                if key not in grouped:
                    drawing_name = loc.drawing.name if loc.drawing else "Unknown"
                    grouped[key] = {
                        'drawing_id': loc.drawing_id,
                        'drawing_name': drawing_name,
                        'page_number': loc.page_number,
                        'spaces': [],
                        'hvac_paths': []
                    }

                if loc.location_type == LocationType.SPACE:
                    grouped[key]['spaces'].append(loc)
                elif loc.location_type == LocationType.HVAC_PATH:
                    grouped[key]['hvac_paths'].append(loc)

            return grouped
        finally:
            session.close()

    @staticmethod
    def get_all_locations_for_project(project_id):
        """Get all locations for a project"""
        session = get_session()
        try:
            from sqlalchemy.orm import selectinload
            from models.drawing_sets import DrawingSet

            locations = (
                session.query(DrawingLocation)
                .join(DrawingLocation.drawing)
                .options(
                    selectinload(DrawingLocation.drawing),
                    selectinload(DrawingLocation.drawing_set)
                )
                .filter(DrawingLocation.drawing.has(project_id=project_id))
                .order_by(DrawingLocation.drawing_set_id, DrawingLocation.drawing_id, DrawingLocation.page_number)
                .all()
            )

            return locations
        finally:
            session.close()

    @staticmethod
    def auto_sync_space_locations(space_id):
        """Automatically sync space locations from room boundaries"""
        session = get_session()
        try:
            space = (
                session.query(Space)
                .options(selectinload(Space.room_boundaries))
                .filter(Space.id == space_id)
                .first()
            )

            if not space or not space.room_boundaries:
                return []

            locations = []
            for boundary in space.room_boundaries:
                loc = LocationManager.create_or_update_space_location(
                    space_id=space_id,
                    drawing_id=boundary.drawing_id,
                    drawing_set_id=space.drawing_set_id if space.drawing_set_id else None,
                    page_number=boundary.page_number if boundary.page_number else 1
                )
                if loc:
                    locations.append(loc)

            return locations
        finally:
            session.close()

    @staticmethod
    def auto_sync_path_locations(path_id):
        """Automatically sync HVAC path locations from components"""
        session = get_session()
        try:
            path = (
                session.query(HVACPath)
                .options(
                    selectinload(HVACPath.segments).selectinload(HVACSegment.from_component),
                    selectinload(HVACPath.segments).selectinload(HVACSegment.to_component)
                )
                .filter(HVACPath.id == path_id)
                .first()
            )

            if not path or not path.segments:
                return []

            # Find unique drawings from components
            drawings = set()
            for segment in path.segments:
                if segment.from_component and segment.from_component.drawing_id:
                    drawings.add(segment.from_component.drawing_id)
                if segment.to_component and segment.to_component.drawing_id:
                    drawings.add(segment.to_component.drawing_id)

            locations = []
            for drawing_id in drawings:
                loc = LocationManager.create_or_update_hvac_path_location(
                    path_id=path_id,
                    drawing_id=drawing_id,
                    drawing_set_id=path.drawing_set_id if path.drawing_set_id else None,
                    page_number=1  # Default to page 1
                )
                if loc:
                    locations.append(loc)

            return locations
        finally:
            session.close()

    @staticmethod
    def _calculate_space_bounds(space):
        """Calculate center point and bounding box for a space"""
        if not space.room_boundaries:
            return None, None, None

        # Use first boundary for now (could be enhanced to use all)
        boundary = space.room_boundaries[0]

        center_x = boundary.x_position + (boundary.width / 2)
        center_y = boundary.y_position + (boundary.height / 2)

        bbox = (
            boundary.x_position,
            boundary.y_position,
            boundary.x_position + boundary.width,
            boundary.y_position + boundary.height
        )

        return center_x, center_y, bbox

    @staticmethod
    def _calculate_path_bounds(path):
        """Calculate center point and bounding box for an HVAC path"""
        if not path.segments:
            return None, None, None

        # Collect all component positions
        x_coords = []
        y_coords = []

        for segment in path.segments:
            if segment.from_component:
                x_coords.append(segment.from_component.x_position)
                y_coords.append(segment.from_component.y_position)
            if segment.to_component:
                x_coords.append(segment.to_component.x_position)
                y_coords.append(segment.to_component.y_position)

        if not x_coords or not y_coords:
            return None, None, None

        # Calculate center as midpoint of bounds
        min_x, max_x = min(x_coords), max(x_coords)
        min_y, max_y = min(y_coords), max(y_coords)

        center_x = (min_x + max_x) / 2
        center_y = (min_y + max_y) / 2

        bbox = (min_x, min_y, max_x, max_y)

        return center_x, center_y, bbox

    @staticmethod
    def delete_locations_for_element(element_type, element_id):
        """Delete all location bookmarks for an element"""
        session = get_session()
        try:
            session.query(DrawingLocation).filter(
                DrawingLocation.location_type == element_type,
                DrawingLocation.element_id == element_id
            ).delete()
            session.commit()
        finally:
            session.close()
