"""
Path-type-aware selection of MechanicalUnit octave-band spectra for HVAC path noise.

Supply / exhaust: prefer outlet (duct discharge), then inlet, then radiated.
Return: prefer inlet (duct entry at equipment), then outlet, then radiated.

A per-component preference overrides the auto order by trying that origin first,
then falling through the auto sequence for the path type.
"""

from __future__ import annotations

import json
from typing import Any, List, Optional, Tuple

from .hvac_constants import FREQUENCY_BAND_LABELS, NUM_OCTAVE_BANDS

_JSON_ATTR_BY_ORIGIN = {
    "outlet": "outlet_levels_json",
    "inlet": "inlet_levels_json",
    "radiated": "radiated_levels_json",
}


def parse_mechanical_unit_json_to_bands(json_data: Optional[str]) -> Optional[List[float]]:
    """Parse MechanicalUnit *_levels_json text into an 8-band list, or None if missing/invalid."""
    if not json_data:
        return None
    try:
        data = json.loads(json_data)
    except Exception:
        return None
    octave_bands: Optional[List[float]] = None
    if hasattr(data, "get"):
        octave_bands = [float(data.get(k, 0) or 0) for k in FREQUENCY_BAND_LABELS]
    elif isinstance(data, list) and len(data) >= NUM_OCTAVE_BANDS:
        octave_bands = [float(x or 0) for x in data[:NUM_OCTAVE_BANDS]]
    if not octave_bands:
        return None
    return octave_bands


def _auto_origin_order(path_type: Optional[str]) -> List[str]:
    pt = (path_type or "supply").strip().lower()
    if pt == "return":
        return ["inlet", "outlet", "radiated"]
    return ["outlet", "inlet", "radiated"]


def spectrum_origin_sequence(path_type: Optional[str], preference: Optional[str]) -> List[str]:
    """Ordered origins to try: path-type auto order, optionally with user preference first."""
    pref = (preference or "auto").strip().lower()
    if pref not in ("auto", "inlet", "outlet", "radiated"):
        pref = "auto"
    base = _auto_origin_order(path_type)
    if pref == "auto":
        return list(base)
    return [pref] + [o for o in base if o != pref]


def mechanical_unit_spectrum_for_path(
    unit: Any,
    path_type: Optional[str] = None,
    preference: Optional[str] = None,
) -> Tuple[Optional[List[float]], Optional[str]]:
    """
    Pick the first usable octave-band spectrum from a MechanicalUnit row.

    Returns:
        (bands, origin_label) where origin_label is 'inlet'|'outlet'|'radiated' or None.
    """
    for origin in spectrum_origin_sequence(path_type, preference):
        attr = _JSON_ATTR_BY_ORIGIN[origin]
        raw = getattr(unit, attr, None)
        bands = parse_mechanical_unit_json_to_bands(raw)
        if bands:
            return bands, origin
    return None, None
