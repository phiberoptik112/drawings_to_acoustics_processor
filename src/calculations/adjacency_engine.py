"""
Adjacency Engine - Automatic detection of HVAC noise risk adjacencies.

Identifies situations where HVAC paths or noise sources carrying significant noise
are in close physical proximity to noise-sensitive occupied spaces.

All geometry operates on PDF-native coordinates (points, 1pt = 1/72 inch).
"""

import json
import math
import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional, Dict, Tuple

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Data Structures
# ---------------------------------------------------------------------------

@dataclass
class PartitionEdge:
    boundary_id: int
    space_id: int
    space_name: str
    floor_label: Optional[str]
    start_x: float
    start_y: float
    end_x: float
    end_y: float
    length_ft: float
    centroid_x: float
    centroid_y: float


@dataclass
class HVACPolylineSegment:
    path_id: int
    path_name: str
    floor_label: Optional[str]
    start_x: float
    start_y: float
    end_x: float
    end_y: float
    calculated_nc: Optional[float]
    path_type: str


@dataclass
class SpaceAdjacency:
    space_a_id: int
    space_a_name: str
    space_b_id: int
    space_b_name: str
    closest_edge_a: PartitionEdge
    closest_edge_b: PartitionEdge
    gap_distance_ft: float
    shared_length_ft: float
    classification: str
    floor_label: str
    adjacency_direction: str


@dataclass
class HVACSpaceProximity:
    path_id: int
    path_name: str
    path_type: str
    space_id: int
    space_name: str
    closest_path_segment: HVACPolylineSegment
    closest_space_edge: PartitionEdge
    gap_distance_ft: float
    classification: str
    calculated_nc: Optional[float]
    risk_flag: bool
    adjacency_direction: str


@dataclass
class PointSourceSpaceProximity:
    source_id: int
    source_name: str
    placement_type: str
    space_id: int
    space_name: str
    floor_label: Optional[str]
    gap_distance_ft: float
    closest_space_edge: PartitionEdge
    lw_spectrum: Optional[dict]
    calculated_lp_spectrum: Optional[dict]
    calculated_nc: Optional[float]
    risk_flag: bool
    adjacency_direction: str


@dataclass
class AdjacencyResults:
    drawing_id: int
    page_number: int
    computed_at: str
    warnings: List[str] = field(default_factory=list)
    space_adjacencies: List[SpaceAdjacency] = field(default_factory=list)
    hvac_proximities: List[HVACSpaceProximity] = field(default_factory=list)
    point_source_proximities: List[PointSourceSpaceProximity] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Coordinate Conversion
# ---------------------------------------------------------------------------

def parse_scale_to_drawing_inches_per_real_foot(scale_string: str) -> Optional[float]:
    """Parse a scale string and return drawing inches per real foot.

    Supports:
    - Architectural: '1/8"=1\\'0"', '1/4"=1\\'0"', '3/16"=1\\'0"'
    - Ratio: '1:100', '1:48'
    """
    if not scale_string:
        return None

    scale_string = scale_string.strip()
    scale_string = scale_string.replace("\u2018", "'").replace("\u2019", "'")
    scale_string = scale_string.replace("\u201c", '"').replace("\u201d", '"')

    if '=' in scale_string:
        try:
            left, right = scale_string.split('=', 1)
            drawing_inches = _parse_dimension_inches(left.strip())
            real_inches = _parse_dimension_inches(right.strip())
            if drawing_inches and real_inches and real_inches > 0:
                real_feet = real_inches / 12.0
                return drawing_inches / real_feet
        except Exception:
            pass

    elif ':' in scale_string:
        try:
            parts = scale_string.split(':')
            num = float(parts[0])
            den = float(parts[1])
            if num > 0 and den > 0:
                # 1:48 means 1 drawing unit = 48 real units
                # At scale 1:48 with drawing in inches: 1 inch = 4 feet => 0.25 in/ft
                # Assume drawing units are inches, real units are inches
                return (num / den) * 12.0
        except Exception:
            pass

    return None


def _parse_dimension_inches(dim_str: str) -> Optional[float]:
    """Parse a dimension string into total inches."""
    dim_str = dim_str.strip()
    total = 0.0

    if "'" in dim_str:
        parts = dim_str.split("'")
        feet_str = parts[0].strip()
        if feet_str:
            total += float(feet_str) * 12.0
        if len(parts) > 1:
            inches_part = parts[1].replace('"', '').strip()
            if inches_part:
                total += _parse_fraction(inches_part)
    elif '"' in dim_str:
        inches_str = dim_str.replace('"', '').strip()
        total = _parse_fraction(inches_str)
    else:
        total = _parse_fraction(dim_str)

    return total if total > 0 else None


def _parse_fraction(s: str) -> float:
    """Parse a number that may contain fractions like '1/8' or '1 1/2'."""
    s = s.strip()
    if not s:
        return 0.0
    if '/' in s:
        if ' ' in s:
            whole, frac = s.split(' ', 1)
            num, den = frac.split('/')
            return float(whole) + float(num) / float(den)
        else:
            num, den = s.split('/')
            return float(num) / float(den)
    return float(s)


def pdf_pts_to_feet(pts_distance: float, scale_string: str) -> Optional[float]:
    """Convert a distance in PDF points to real-world feet using the drawing scale.

    PDF points: 1pt = 1/72 inch on paper.
    """
    scale_factor = parse_scale_to_drawing_inches_per_real_foot(scale_string)
    if not scale_factor or scale_factor <= 0:
        return None
    drawing_inches = pts_distance / 72.0
    return drawing_inches / scale_factor


# ---------------------------------------------------------------------------
# Core Geometry
# ---------------------------------------------------------------------------

def _clamp(val: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, val))


def point_to_seg_distance(px: float, py: float,
                          sx1: float, sy1: float,
                          sx2: float, sy2: float) -> float:
    """Minimum distance from point (px,py) to segment (sx1,sy1)-(sx2,sy2)."""
    dx = sx2 - sx1
    dy = sy2 - sy1
    len_sq = dx * dx + dy * dy
    if len_sq == 0:
        return math.hypot(px - sx1, py - sy1)
    t = _clamp(((px - sx1) * dx + (py - sy1) * dy) / len_sq, 0.0, 1.0)
    proj_x = sx1 + t * dx
    proj_y = sy1 + t * dy
    return math.hypot(px - proj_x, py - proj_y)


def seg_to_seg_distance(ax1: float, ay1: float, ax2: float, ay2: float,
                        bx1: float, by1: float, bx2: float, by2: float) -> float:
    """Minimum distance between two line segments in 2D."""
    # Check all four endpoint-to-segment distances plus segment intersection
    d1 = point_to_seg_distance(ax1, ay1, bx1, by1, bx2, by2)
    d2 = point_to_seg_distance(ax2, ay2, bx1, by1, bx2, by2)
    d3 = point_to_seg_distance(bx1, by1, ax1, ay1, ax2, ay2)
    d4 = point_to_seg_distance(bx2, by2, ax1, ay1, ax2, ay2)
    min_d = min(d1, d2, d3, d4)

    # Check actual segment intersection (distance = 0)
    if _segments_intersect(ax1, ay1, ax2, ay2, bx1, by1, bx2, by2):
        return 0.0

    return min_d


def _segments_intersect(ax1, ay1, ax2, ay2, bx1, by1, bx2, by2) -> bool:
    """Check if two segments intersect using cross-product method."""
    def cross(ox, oy, ax, ay, bx, by):
        return (ax - ox) * (by - oy) - (ay - oy) * (bx - ox)

    d1 = cross(bx1, by1, bx2, by2, ax1, ay1)
    d2 = cross(bx1, by1, bx2, by2, ax2, ay2)
    d3 = cross(ax1, ay1, ax2, ay2, bx1, by1)
    d4 = cross(ax1, ay1, ax2, ay2, bx2, by2)

    if ((d1 > 0 and d2 < 0) or (d1 < 0 and d2 > 0)) and \
       ((d3 > 0 and d4 < 0) or (d3 < 0 and d4 > 0)):
        return True

    # Collinear cases
    if d1 == 0 and _on_segment(bx1, by1, bx2, by2, ax1, ay1):
        return True
    if d2 == 0 and _on_segment(bx1, by1, bx2, by2, ax2, ay2):
        return True
    if d3 == 0 and _on_segment(ax1, ay1, ax2, ay2, bx1, by1):
        return True
    if d4 == 0 and _on_segment(ax1, ay1, ax2, ay2, bx2, by2):
        return True

    return False


def _on_segment(sx1, sy1, sx2, sy2, px, py) -> bool:
    """Check if point p lies on segment s (assuming collinear)."""
    return (min(sx1, sx2) <= px <= max(sx1, sx2) and
            min(sy1, sy2) <= py <= max(sy1, sy2))


def _compute_shared_length(edge_a: PartitionEdge, edge_b: PartitionEdge,
                           scale_string: str) -> float:
    """Compute the projected overlap length between two edges."""
    # Project both edges onto their dominant axis
    a_dx = edge_a.end_x - edge_a.start_x
    a_dy = edge_a.end_y - edge_a.start_y
    b_dx = edge_b.end_x - edge_b.start_x
    b_dy = edge_b.end_y - edge_b.start_y

    # Use whichever axis has the larger projection
    if abs(a_dx) + abs(b_dx) >= abs(a_dy) + abs(b_dy):
        # X-axis dominant
        a_min, a_max = sorted([edge_a.start_x, edge_a.end_x])
        b_min, b_max = sorted([edge_b.start_x, edge_b.end_x])
    else:
        # Y-axis dominant
        a_min, a_max = sorted([edge_a.start_y, edge_a.end_y])
        b_min, b_max = sorted([edge_b.start_y, edge_b.end_y])

    overlap = max(0, min(a_max, b_max) - max(a_min, b_min))
    result = pdf_pts_to_feet(overlap, scale_string)
    return result if result else 0.0


# ---------------------------------------------------------------------------
# Data Extraction
# ---------------------------------------------------------------------------

def extract_partition_edges(boundary, scale_string: str, space_name: str = "") -> List[PartitionEdge]:
    """Extract partition edges from a RoomBoundary record."""
    edges = []
    space_id = boundary.space_id
    floor_label = boundary.floor_label

    pdf_x = boundary.pdf_x
    pdf_y = boundary.pdf_y
    pdf_w = boundary.pdf_width
    pdf_h = boundary.pdf_height

    if pdf_x is None:
        # Fallback to legacy coords (which are base-zoom = PDF-native)
        pdf_x = boundary.x_position
        pdf_y = boundary.y_position
        pdf_w = boundary.width
        pdf_h = boundary.height

    if pdf_x is None:
        return edges

    # Check for polygon
    polygon_pts = None
    if boundary.pdf_polygon_pts:
        try:
            polygon_pts = json.loads(boundary.pdf_polygon_pts)
        except (json.JSONDecodeError, TypeError):
            pass
    elif boundary.polygon_points:
        try:
            polygon_pts = json.loads(boundary.polygon_points)
        except (json.JSONDecodeError, TypeError):
            pass

    if polygon_pts and len(polygon_pts) >= 3:
        for i in range(len(polygon_pts)):
            p1 = polygon_pts[i]
            p2 = polygon_pts[(i + 1) % len(polygon_pts)]
            sx, sy = float(p1.get('x', 0)), float(p1.get('y', 0))
            ex, ey = float(p2.get('x', 0)), float(p2.get('y', 0))
            length_pts = math.hypot(ex - sx, ey - sy)
            length_ft = pdf_pts_to_feet(length_pts, scale_string) or 0.0
            edges.append(PartitionEdge(
                boundary_id=boundary.id,
                space_id=space_id,
                space_name=space_name,
                floor_label=floor_label,
                start_x=sx, start_y=sy,
                end_x=ex, end_y=ey,
                length_ft=length_ft,
                centroid_x=(sx + ex) / 2.0,
                centroid_y=(sy + ey) / 2.0,
            ))
    else:
        # Rectangle: 4 edges (top, right, bottom, left)
        x, y, w, h = pdf_x, pdf_y, pdf_w, pdf_h
        corners = [
            (x, y, x + w, y),         # top
            (x + w, y, x + w, y + h), # right
            (x + w, y + h, x, y + h), # bottom
            (x, y + h, x, y),         # left
        ]
        for sx, sy, ex, ey in corners:
            length_pts = math.hypot(ex - sx, ey - sy)
            length_ft = pdf_pts_to_feet(length_pts, scale_string) or 0.0
            edges.append(PartitionEdge(
                boundary_id=boundary.id,
                space_id=space_id,
                space_name=space_name,
                floor_label=floor_label,
                start_x=sx, start_y=sy,
                end_x=ex, end_y=ey,
                length_ft=length_ft,
                centroid_x=(sx + ex) / 2.0,
                centroid_y=(sy + ey) / 2.0,
            ))

    return edges


def extract_hvac_polyline(path, components_by_id: Dict) -> List[HVACPolylineSegment]:
    """Extract polyline segments from an HVACPath via its segment chain."""
    segments_out = []
    path_name = path.name or f"Path {path.id}"
    path_type = path.path_type or 'supply'
    calculated_nc = path.calculated_nc

    for seg in (path.segments or []):
        from_comp = components_by_id.get(seg.from_component_id)
        to_comp = components_by_id.get(seg.to_component_id)
        if not from_comp or not to_comp:
            continue

        # Use pdf_x/pdf_y; fallback to x_position/y_position
        fx = from_comp.pdf_x if from_comp.pdf_x is not None else from_comp.x_position
        fy = from_comp.pdf_y if from_comp.pdf_y is not None else from_comp.y_position
        tx = to_comp.pdf_x if to_comp.pdf_x is not None else to_comp.x_position
        ty = to_comp.pdf_y if to_comp.pdf_y is not None else to_comp.y_position

        if fx is None or fy is None or tx is None or ty is None:
            continue

        floor_label = from_comp.floor_label or to_comp.floor_label

        segments_out.append(HVACPolylineSegment(
            path_id=path.id,
            path_name=path_name,
            floor_label=floor_label,
            start_x=float(fx), start_y=float(fy),
            end_x=float(tx), end_y=float(ty),
            calculated_nc=calculated_nc,
            path_type=path_type,
        ))

    return segments_out


# ---------------------------------------------------------------------------
# Adjacency Engine
# ---------------------------------------------------------------------------

class AdjacencyEngine:
    """Computes space-to-space and HVAC-to-space proximity relationships."""

    def __init__(self, project_id: int):
        self.project_id = project_id
        self._cache: Dict[Tuple[int, int], AdjacencyResults] = {}

    def run_for_page(self, drawing_id: int, page_number: int) -> AdjacencyResults:
        """Run full adjacency analysis for one drawing page."""
        from models import get_session
        from models.space import RoomBoundary, Space
        from models.hvac import HVACComponent, HVACPath, HVACSegment
        from models.mechanical import NoiseSource
        from models.drawing import Drawing, DrawingPage
        from models.project import Project
        from sqlalchemy.orm import selectinload

        results = AdjacencyResults(
            drawing_id=drawing_id,
            page_number=page_number,
            computed_at=datetime.utcnow().isoformat(),
        )

        session = get_session()
        try:
            # Load project settings
            project = session.query(Project).filter_by(id=self.project_id).first()
            if not project:
                results.warnings.append("Project not found.")
                return results

            near_min_ft = (getattr(project, 'adjacency_near_min_in', None) or 6.0) / 12.0
            near_max_ft = getattr(project, 'adjacency_near_max_ft', None) or 3.0

            # Load drawing for scale_string
            drawing = session.query(Drawing).filter_by(id=drawing_id).first()
            if not drawing:
                results.warnings.append("Drawing not found.")
                return results

            scale_string = drawing.scale_string
            if not scale_string:
                results.warnings.append("Drawing has no scale_string set. Distance calculations may be inaccurate.")

            # Load DrawingPage for floor label
            dp = session.query(DrawingPage).filter_by(
                drawing_id=drawing_id, page_number=page_number
            ).first()
            page_floor_label = dp.floor_label if dp else None

            # Load room boundaries on this page
            boundaries = session.query(RoomBoundary).filter_by(
                drawing_id=drawing_id, page_number=page_number
            ).all()

            # Load spaces for name lookup
            space_ids = {b.space_id for b in boundaries}
            spaces = {s.id: s for s in session.query(Space).filter(Space.id.in_(space_ids)).all()} if space_ids else {}

            # Extract partition edges
            all_edges: Dict[int, List[PartitionEdge]] = {}  # space_id -> edges
            for b in boundaries:
                space = spaces.get(b.space_id)
                space_name = space.name if space else f"Space {b.space_id}"
                edges = extract_partition_edges(b, scale_string or "1:1", space_name)
                if edges:
                    all_edges.setdefault(b.space_id, []).extend(edges)

            # --- Same-floor space-to-space proximity ---
            space_id_list = list(all_edges.keys())
            for i in range(len(space_id_list)):
                for j in range(i + 1, len(space_id_list)):
                    sid_a = space_id_list[i]
                    sid_b = space_id_list[j]
                    edges_a = all_edges[sid_a]
                    edges_b = all_edges[sid_b]

                    min_dist = float('inf')
                    best_ea = None
                    best_eb = None

                    for ea in edges_a:
                        for eb in edges_b:
                            d = seg_to_seg_distance(
                                ea.start_x, ea.start_y, ea.end_x, ea.end_y,
                                eb.start_x, eb.start_y, eb.end_x, eb.end_y
                            )
                            if d < min_dist:
                                min_dist = d
                                best_ea = ea
                                best_eb = eb

                    if best_ea is None:
                        continue

                    gap_ft = pdf_pts_to_feet(min_dist, scale_string or "1:1") or 0.0

                    if gap_ft > near_max_ft:
                        continue  # 'remote' — skip

                    if gap_ft < near_min_ft:
                        classification = 'shared'
                    else:
                        classification = 'near'

                    shared_length = 0.0
                    if classification == 'shared':
                        shared_length = _compute_shared_length(best_ea, best_eb, scale_string or "1:1")

                    space_a = spaces.get(sid_a)
                    space_b = spaces.get(sid_b)
                    results.space_adjacencies.append(SpaceAdjacency(
                        space_a_id=sid_a,
                        space_a_name=space_a.name if space_a else f"Space {sid_a}",
                        space_b_id=sid_b,
                        space_b_name=space_b.name if space_b else f"Space {sid_b}",
                        closest_edge_a=best_ea,
                        closest_edge_b=best_eb,
                        gap_distance_ft=gap_ft,
                        shared_length_ft=shared_length,
                        classification=classification,
                        floor_label=page_floor_label or "",
                        adjacency_direction='same_floor',
                    ))

            # --- HVAC-to-space proximity ---
            hvac_paths = session.query(HVACPath).options(
                selectinload(HVACPath.segments)
            ).filter_by(project_id=self.project_id).all()

            # Build component lookup
            page_components = session.query(HVACComponent).filter_by(
                drawing_id=drawing_id, page_number=page_number
            ).all()
            components_by_id = {c.id: c for c in page_components}

            # Also load all project components for path reconstruction
            all_components = session.query(HVACComponent).filter_by(
                project_id=self.project_id
            ).all()
            all_comps_by_id = {c.id: c for c in all_components}

            for path in hvac_paths:
                polyline = extract_hvac_polyline(path, all_comps_by_id)
                if not polyline:
                    continue

                # Filter to segments on this page (by floor_label or by component membership)
                page_segments = [
                    ps for ps in polyline
                    if ps.start_x is not None and (
                        ps.floor_label == page_floor_label or
                        any(c.id in components_by_id for c in [])  # fallback
                    )
                ]
                # Simpler: check if segment endpoints are from components on this page
                page_segments = []
                for ps in polyline:
                    for seg in (path.segments or []):
                        if seg.from_component_id in components_by_id or seg.to_component_id in components_by_id:
                            page_segments.append(ps)
                            break

                if not page_segments:
                    continue

                # Find minimum distance from each path to each space
                for sid, edges in all_edges.items():
                    min_dist = float('inf')
                    best_ps = None
                    best_edge = None

                    for ps in page_segments:
                        for edge in edges:
                            d = seg_to_seg_distance(
                                ps.start_x, ps.start_y, ps.end_x, ps.end_y,
                                edge.start_x, edge.start_y, edge.end_x, edge.end_y
                            )
                            if d < min_dist:
                                min_dist = d
                                best_ps = ps
                                best_edge = edge

                    if best_ps is None:
                        continue

                    gap_ft = pdf_pts_to_feet(min_dist, scale_string or "1:1") or 0.0
                    if gap_ft > near_max_ft:
                        continue

                    if gap_ft < near_min_ft:
                        classification = 'shared'
                    else:
                        classification = 'near'

                    risk_flag = (
                        best_ps.calculated_nc is not None and
                        classification in ('shared', 'near')
                    )

                    space = spaces.get(sid)
                    results.hvac_proximities.append(HVACSpaceProximity(
                        path_id=path.id,
                        path_name=path.name or f"Path {path.id}",
                        path_type=path.path_type or 'supply',
                        space_id=sid,
                        space_name=space.name if space else f"Space {sid}",
                        closest_path_segment=best_ps,
                        closest_space_edge=best_edge,
                        gap_distance_ft=gap_ft,
                        classification=classification,
                        calculated_nc=best_ps.calculated_nc,
                        risk_flag=risk_flag,
                        adjacency_direction='same_floor',
                    ))

            # --- Point source to space proximity ---
            noise_sources = session.query(NoiseSource).filter(
                NoiseSource.project_id == self.project_id,
                NoiseSource.placement_type != 'unplaced',
                NoiseSource.drawing_id == drawing_id,
                NoiseSource.page_number == page_number,
            ).all()

            for source in noise_sources:
                if source.placement_type == 'point' and source.pdf_x is not None:
                    for sid, edges in all_edges.items():
                        min_dist = float('inf')
                        best_edge = None
                        for edge in edges:
                            d = point_to_seg_distance(
                                source.pdf_x, source.pdf_y,
                                edge.start_x, edge.start_y, edge.end_x, edge.end_y
                            )
                            if d < min_dist:
                                min_dist = d
                                best_edge = edge

                        if best_edge is None:
                            continue

                        gap_ft = pdf_pts_to_feet(min_dist, scale_string or "1:1") or 0.0
                        if gap_ft > near_max_ft:
                            continue

                        # Shultz calculation
                        lp_spectrum = None
                        calc_nc = None
                        lw_bands = source.get_octave_bands()
                        if lw_bands:
                            lp_spectrum, calc_nc = self._compute_shultz(
                                lw_bands, gap_ft, sid, session
                            )

                        if gap_ft < near_min_ft:
                            classification = 'shared'
                        else:
                            classification = 'near'

                        risk_flag = (
                            calc_nc is not None and
                            classification in ('shared', 'near')
                        )

                        space = spaces.get(sid)
                        results.point_source_proximities.append(PointSourceSpaceProximity(
                            source_id=source.id,
                            source_name=source.name,
                            placement_type=source.placement_type,
                            space_id=sid,
                            space_name=space.name if space else f"Space {sid}",
                            floor_label=source.floor_label,
                            gap_distance_ft=gap_ft,
                            closest_space_edge=best_edge,
                            lw_spectrum=lw_bands,
                            calculated_lp_spectrum=lp_spectrum,
                            calculated_nc=calc_nc,
                            risk_flag=risk_flag,
                            adjacency_direction='same_floor',
                        ))

                elif source.placement_type == 'boundary':
                    # Boundary source: find linked RoomBoundary
                    linked_boundaries = [
                        b for b in boundaries if b.noise_source_id == source.id
                    ]
                    if not linked_boundaries:
                        continue
                    source_edges = []
                    for lb in linked_boundaries:
                        source_edges.extend(
                            extract_partition_edges(lb, scale_string or "1:1", source.name)
                        )
                    if not source_edges:
                        continue

                    # Compare source boundary edges to all other space edges
                    linked_space_ids = {lb.space_id for lb in linked_boundaries}
                    for sid, edges in all_edges.items():
                        if sid in linked_space_ids:
                            continue  # Don't compute adjacency to self

                        min_dist = float('inf')
                        best_edge = None
                        for se in source_edges:
                            for edge in edges:
                                d = seg_to_seg_distance(
                                    se.start_x, se.start_y, se.end_x, se.end_y,
                                    edge.start_x, edge.start_y, edge.end_x, edge.end_y
                                )
                                if d < min_dist:
                                    min_dist = d
                                    best_edge = edge

                        if best_edge is None:
                            continue

                        gap_ft = pdf_pts_to_feet(min_dist, scale_string or "1:1") or 0.0
                        if gap_ft > near_max_ft:
                            continue

                        lp_spectrum = None
                        calc_nc = None
                        lw_bands = source.get_octave_bands()
                        if lw_bands:
                            lp_spectrum, calc_nc = self._compute_shultz(
                                lw_bands, gap_ft, sid, session
                            )

                        if gap_ft < near_min_ft:
                            classification = 'shared'
                        else:
                            classification = 'near'

                        risk_flag = (
                            calc_nc is not None and
                            classification in ('shared', 'near')
                        )

                        space = spaces.get(sid)
                        results.point_source_proximities.append(PointSourceSpaceProximity(
                            source_id=source.id,
                            source_name=source.name,
                            placement_type='boundary',
                            space_id=sid,
                            space_name=space.name if space else f"Space {sid}",
                            floor_label=source.floor_label,
                            gap_distance_ft=gap_ft,
                            closest_space_edge=best_edge,
                            lw_spectrum=lw_bands,
                            calculated_lp_spectrum=lp_spectrum,
                            calculated_nc=calc_nc,
                            risk_flag=risk_flag,
                            adjacency_direction='same_floor',
                        ))

            # --- Cross-floor vertical adjacency ---
            self._compute_cross_floor(
                session, drawing, page_number, page_floor_label,
                boundaries, spaces, all_edges, scale_string, near_min_ft, near_max_ft, results
            )

        except Exception as e:
            logger.error(f"Adjacency engine error: {e}", exc_info=True)
            results.warnings.append(f"Engine error: {str(e)}")
        finally:
            session.close()

        self._cache[(drawing_id, page_number)] = results
        return results

    def _compute_shultz(self, lw_bands: dict, gap_ft: float, space_id: int, session) -> Tuple[Optional[dict], Optional[float]]:
        """Run Shultz receiver room correction and NC rating."""
        try:
            from calculations.receiver_room_sound_correction_calculations import ReceiverRoomSoundCorrection
            from calculations.nc_rating_analyzer import NCRatingAnalyzer
            from models.space import Space

            space = session.query(Space).filter_by(id=space_id).first()
            room_volume = (space.volume or 1000.0) if space else 1000.0

            # Build 7-band spectrum (63-4000 Hz) for Shultz
            freqs_7 = [63, 125, 250, 500, 1000, 2000, 4000]
            lw_spectrum_7 = [lw_bands.get(f, 0.0) for f in freqs_7]

            calc = ReceiverRoomSoundCorrection()
            result = calc.calculate_octave_band_spectrum(
                lw_spectrum=lw_spectrum_7,
                distance=max(gap_ft, 1.0),
                room_volume=room_volume,
            )

            lp_levels = result.get('sound_pressure_levels', [])
            if not lp_levels:
                return None, None

            # Pad to 8 bands for NC (add 8kHz estimate: -3dB from 4kHz)
            lp_8band = list(lp_levels)
            if len(lp_8band) == 7:
                lp_8band.append(lp_8band[-1] - 3.0)

            analyzer = NCRatingAnalyzer()
            nc = analyzer.determine_nc_rating(lp_8band)

            lp_dict = {str(f): lp_levels[i] for i, f in enumerate(freqs_7) if i < len(lp_levels)}
            return lp_dict, nc

        except Exception as e:
            logger.debug(f"Shultz calculation failed: {e}")
            return None, None

    def _compute_cross_floor(self, session, drawing, page_number, page_floor_label,
                             boundaries, spaces, all_edges, scale_string,
                             near_min_ft, near_max_ft, results: AdjacencyResults):
        """Compute vertical (floor/ceiling) adjacencies between this page and adjacent floors."""
        from models.drawing import DrawingPage
        from models.space import RoomBoundary, Space

        if not page_floor_label:
            return  # Can't do cross-floor without floor labels

        # Find adjacent floor pages in the same drawing
        all_pages = session.query(DrawingPage).filter_by(
            drawing_id=drawing.id
        ).all()

        other_pages = [p for p in all_pages if p.page_number != page_number and p.floor_label]
        if not other_pages:
            return

        # Check scale compatibility
        for other_page in other_pages:
            # For cross-floor, both pages must share the same drawing (same scale_string)
            other_boundaries = session.query(RoomBoundary).filter_by(
                drawing_id=drawing.id, page_number=other_page.page_number
            ).all()

            if not other_boundaries:
                continue

            other_space_ids = {b.space_id for b in other_boundaries}
            other_spaces = {
                s.id: s for s in session.query(Space).filter(Space.id.in_(other_space_ids)).all()
            } if other_space_ids else {}

            # Check bounding-box XY overlap between boundaries on different floors
            for b_this in boundaries:
                this_x = b_this.pdf_x if b_this.pdf_x is not None else b_this.x_position
                this_y = b_this.pdf_y if b_this.pdf_y is not None else b_this.y_position
                this_w = b_this.pdf_width if b_this.pdf_width is not None else b_this.width
                this_h = b_this.pdf_height if b_this.pdf_height is not None else b_this.height

                if this_x is None:
                    continue

                for b_other in other_boundaries:
                    other_x = b_other.pdf_x if b_other.pdf_x is not None else b_other.x_position
                    other_y = b_other.pdf_y if b_other.pdf_y is not None else b_other.y_position
                    other_w = b_other.pdf_width if b_other.pdf_width is not None else b_other.width
                    other_h = b_other.pdf_height if b_other.pdf_height is not None else b_other.height

                    if other_x is None:
                        continue

                    # Compute bounding box overlap
                    overlap_x = max(0, min(this_x + this_w, other_x + other_w) - max(this_x, other_x))
                    overlap_y = max(0, min(this_y + this_h, other_y + other_h) - max(this_y, other_y))

                    if overlap_x <= 0 or overlap_y <= 0:
                        continue

                    # Convert overlap area to sq ft
                    overlap_w_ft = pdf_pts_to_feet(overlap_x, scale_string or "1:1") or 0.0
                    overlap_h_ft = pdf_pts_to_feet(overlap_y, scale_string or "1:1") or 0.0
                    overlap_area = overlap_w_ft * overlap_h_ft

                    if overlap_area <= 0:
                        continue

                    space_this = spaces.get(b_this.space_id)
                    space_other = other_spaces.get(b_other.space_id)

                    # Create placeholder edges for the result
                    edge_this = PartitionEdge(
                        boundary_id=b_this.id, space_id=b_this.space_id,
                        space_name=space_this.name if space_this else "",
                        floor_label=page_floor_label,
                        start_x=this_x, start_y=this_y,
                        end_x=this_x + this_w, end_y=this_y,
                        length_ft=overlap_w_ft,
                        centroid_x=this_x + this_w / 2, centroid_y=this_y + this_h / 2,
                    )
                    edge_other = PartitionEdge(
                        boundary_id=b_other.id, space_id=b_other.space_id,
                        space_name=space_other.name if space_other else "",
                        floor_label=other_page.floor_label,
                        start_x=other_x, start_y=other_y,
                        end_x=other_x + other_w, end_y=other_y,
                        length_ft=overlap_w_ft,
                        centroid_x=other_x + other_w / 2, centroid_y=other_y + other_h / 2,
                    )

                    results.space_adjacencies.append(SpaceAdjacency(
                        space_a_id=b_this.space_id,
                        space_a_name=space_this.name if space_this else f"Space {b_this.space_id}",
                        space_b_id=b_other.space_id,
                        space_b_name=space_other.name if space_other else f"Space {b_other.space_id}",
                        closest_edge_a=edge_this,
                        closest_edge_b=edge_other,
                        gap_distance_ft=0.0,  # floor/ceiling = 0 gap (directly above/below)
                        shared_length_ft=overlap_area,  # repurpose as overlap area for floor/ceiling
                        classification='shared',
                        floor_label=page_floor_label,
                        adjacency_direction='floor_ceiling',
                    ))

    def get_for_space(self, space_id: int) -> Optional[AdjacencyResults]:
        """Return cached results that include the given space_id."""
        for results in self._cache.values():
            all_space_ids = set()
            for sa in results.space_adjacencies:
                all_space_ids.add(sa.space_a_id)
                all_space_ids.add(sa.space_b_id)
            for hp in results.hvac_proximities:
                all_space_ids.add(hp.space_id)
            for ps in results.point_source_proximities:
                all_space_ids.add(ps.space_id)
            if space_id in all_space_ids:
                return results
        return None

    def invalidate(self, drawing_id: int, page_number: int) -> None:
        """Remove cached results for a page."""
        self._cache.pop((drawing_id, page_number), None)
