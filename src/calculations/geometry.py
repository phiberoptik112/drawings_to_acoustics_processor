"""
Geometry utilities for drawing tools

Provides polygon area and perimeter calculations and helpers to convert
pixel-based measurements into real-world units using a known scale ratio.
"""

from typing import List, Dict, Tuple


def _polygon_area_pixels(points: List[Tuple[float, float]]) -> float:
	"""Compute the signed area in pixel^2 using the shoelace formula.
	Returns absolute area.
	"""
	if len(points) < 3:
		return 0.0
	area2 = 0.0
	for i in range(len(points)):
		x1, y1 = points[i]
		x2, y2 = points[(i + 1) % len(points)]
		area2 += (x1 * y2) - (x2 * y1)
	return abs(area2) / 2.0


def _polygon_perimeter_pixels(points: List[Tuple[float, float]]) -> float:
	"""Compute polygon perimeter length in pixels."""
	if len(points) < 2:
		return 0.0
	import math
	perim = 0.0
	for i in range(len(points)):
		x1, y1 = points[i]
		x2, y2 = points[(i + 1) % len(points)]
		dx = x2 - x1
		dy = y2 - y1
		perim += math.hypot(dx, dy)
	return perim


def compute_polygon_metrics(points: List[Dict[str, float]], scale_ratio: float) -> Dict[str, float]:
	"""Compute real-world area and perimeter for a polygon.

	- points: list of {'x': px, 'y': py}
	- scale_ratio: pixels per real unit (from ScaleManager.scale_ratio)

	Returns: {'area_real': float, 'perimeter_real': float}
	"""
	if not points or len(points) < 3 or not scale_ratio or scale_ratio <= 0:
		return {'area_real': 0.0, 'perimeter_real': 0.0}
	pts = [(float(p.get('x', 0.0)), float(p.get('y', 0.0))) for p in points]
	area_px2 = _polygon_area_pixels(pts)
	perim_px = _polygon_perimeter_pixels(pts)
	# Convert: linear px -> real via divide by scale_ratio
	# Area: px^2 -> real^2 via divide by scale_ratio^2
	area_real = area_px2 / (scale_ratio * scale_ratio)
	perimeter_real = perim_px / scale_ratio
	return {'area_real': area_real, 'perimeter_real': perimeter_real}


