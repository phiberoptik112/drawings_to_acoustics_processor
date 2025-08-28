"""
End Reflection Loss (ERL) calculations based on ASHRAE 2015 Applications Handbook, Chapter 48.

Implements:
- Effective diameter for rectangular ducts: D = sqrt(4A / pi)
- Table 28 ERL values (flush termination) with linear interpolation across diameter and frequency
- Simplified ERL equation (Cunefare & Michaud 2008):
  ERL_dB = 10 * log10(1 + (a1 * D * f / c) ** a2)

Notes
- For the equation, D and c must use consistent units. Defaults assume D in feet and c ~ 1125 ft/s.
- Table 28 uses duct diameters in inches and octave-band mid-frequencies: 63, 125, 250, 500, 1000 Hz.
- Per ASHRAE, a1, a2 for terminations:
  - flush: a1 = 0.7, a2 = 2
  - free space: a1 = 1.0, a2 = 2

This module provides a CLI to compute ERL for common inputs.
"""

from __future__ import annotations

import argparse
import math
from dataclasses import dataclass
from typing import Iterable, List, Literal, Sequence, Tuple, Union, Optional

import numpy as np


# --------------------------------------------------------------------------------------
# Data: Table 28 (Flush termination) ERL [dB] for octave-band mid frequencies
# Diameters are in inches. Frequencies are in Hz.
# Source: End-Reflection-Loss_2015-ASHRAE-Applications-Handbook.md
# --------------------------------------------------------------------------------------

TABLE28_FREQUENCIES_HZ: Tuple[int, ...] = (63, 125, 250, 500, 1000)
TABLE28_DIAMETERS_IN: Tuple[int, ...] = (
    6, 8, 10, 12, 16, 20, 24, 28, 32, 36, 48, 72
)

# Rows correspond to TABLE28_DIAMETERS_IN order; columns to TABLE28_FREQUENCIES_HZ order
TABLE28_ERL_DB: Tuple[Tuple[int, ...], ...] = (
    (18, 12, 7, 3, 1),   # 6 in
    (15, 10, 5, 2, 1),   # 8 in
    (14, 8, 4, 1, 0),    # 10 in
    (12, 7, 3, 1, 0),    # 12 in
    (10, 5, 2, 1, 0),    # 16 in
    (8, 4, 1, 0, 0),     # 20 in
    (7, 3, 1, 0, 0),     # 24 in
    (6, 2, 1, 0, 0),     # 28 in
    (5, 2, 1, 0, 0),     # 32 in
    (4, 2, 0, 0, 0),     # 36 in
    (3, 1, 0, 0, 0),     # 48 in
    (1, 0, 0, 0, 0),     # 72 in
)


# --------------------------------------------------------------------------------------
# Utilities
# --------------------------------------------------------------------------------------

def compute_effective_diameter_from_area(area: float) -> float:
    """Compute effective diameter from cross-sectional area using D = sqrt(4A / pi).

    Parameters
    - area: Cross-sectional area in the same squared units as desired diameter units.

    Returns
    - Effective diameter in the same linear units as sqrt(area).
    """
    if area <= 0:
        raise ValueError("Area must be positive")
    return math.sqrt(4.0 * area / math.pi)


def compute_effective_diameter_rectangular(
    width: float,
    height: float,
) -> float:
    """Compute effective diameter for a rectangular duct from its width and height.

    Inputs must be in consistent units (e.g., inches or feet). The output diameter
    will be in the same units as the inputs.
    """
    if width <= 0 or height <= 0:
        raise ValueError("Width and height must be positive")
    area = width * height
    return compute_effective_diameter_from_area(area)


def _linear_interpolate(x: float, x0: float, y0: float, x1: float, y1: float) -> float:
    if x1 == x0:
        return float(y0)
    t = (x - x0) / (x1 - x0)
    return float(y0 + t * (y1 - y0))


def _find_bracketing_indices(values: Sequence[float], x: float) -> Tuple[int, int]:
    """Find indices i, j such that values[i] <= x <= values[j] with j = max(i, i+1).

    If x is outside the range, returns the nearest clamped pair (i == j at endpoint).
    """
    if x <= values[0]:
        return 0, 0
    if x >= values[-1]:
        last = len(values) - 1
        return last, last
    for i in range(len(values) - 1):
        if values[i] <= x <= values[i + 1]:
            return i, i + 1
    # Fallback (should not be reached due to clamps above)
    last = len(values) - 1
    return last, last


# --------------------------------------------------------------------------------------
# ERL via Table 28 (Flush termination)
# --------------------------------------------------------------------------------------

def erl_from_table_flush(
    diameter_in: float,
    frequency_hz: float,
) -> float:
    """Compute ERL [dB] from Table 28 for a flush termination via bilinear interpolation.

    - diameter_in: duct diameter in inches (effective diameter for rectangular ducts)
    - frequency_hz: frequency in Hz (typically one of 63, 125, 250, 500, 1000)

    Behavior:
    - Clamps to the nearest boundary if inputs fall outside the tabulated range.
    - Performs linear interpolation across frequency and diameter.
    """
    diams = np.array(TABLE28_DIAMETERS_IN, dtype=float)
    freqs = np.array(TABLE28_FREQUENCIES_HZ, dtype=float)
    erl_table = np.array(TABLE28_ERL_DB, dtype=float)

    # Bracket indices for diameter and frequency
    i0, i1 = _find_bracketing_indices(diams, float(diameter_in))
    j0, j1 = _find_bracketing_indices(freqs, float(frequency_hz))

    # Interpolate in frequency at the two bracketing diameters
    e_i0_f0 = erl_table[i0, j0]
    e_i0_f1 = erl_table[i0, j1]
    e_i1_f0 = erl_table[i1, j0]
    e_i1_f1 = erl_table[i1, j1]

    f0 = freqs[j0]
    f1 = freqs[j1]
    e_i0_f = _linear_interpolate(frequency_hz, f0, e_i0_f0, f1, e_i0_f1)
    e_i1_f = _linear_interpolate(frequency_hz, f0, e_i1_f0, f1, e_i1_f1)

    # Interpolate across diameter
    d0 = diams[i0]
    d1 = diams[i1]
    e = _linear_interpolate(diameter_in, d0, e_i0_f, d1, e_i1_f)
    return float(e)


# --------------------------------------------------------------------------------------
# ERL via simplified equation (Cunefare & Michaud 2008)
# --------------------------------------------------------------------------------------

Termination = Literal["flush", "free"]


@dataclass(frozen=True)
class TerminationParams:
    a1: float
    a2: float


TERMINATION_TO_PARAMS = {
    "flush": TerminationParams(a1=0.7, a2=2.0),
    "free": TerminationParams(a1=1.0, a2=2.0),
}


def erl_from_equation(
    diameter: float,
    frequency_hz: float,
    *,
    speed_of_sound: float = 1125.33,
    diameter_units: Literal["ft", "in"] = "ft",
    termination: Termination = "flush",
) -> float:
    """Compute ERL [dB] using ERL = 10 * log10(1 + (a1 * D * f / c) ** a2).

    Parameters
    - diameter: duct diameter in feet (default) or inches if diameter_units == 'in'
    - frequency_hz: frequency in Hz
    - speed_of_sound: speed of sound in ft/s if diameter in feet (default 1125.33 ft/s)
    - diameter_units: 'ft' (default) or 'in'. If 'in', the value will be converted to feet
    - termination: 'flush' or 'free'
    """
    if termination not in TERMINATION_TO_PARAMS:
        raise ValueError(f"Unsupported termination '{termination}'. Use 'flush' or 'free'.")

    if diameter_units == "in":
        diameter_ft = diameter / 12.0
    elif diameter_units == "ft":
        diameter_ft = diameter
    else:
        raise ValueError("diameter_units must be 'ft' or 'in'")

    if diameter_ft <= 0:
        raise ValueError("Diameter must be positive")
    if frequency_hz <= 0:
        raise ValueError("Frequency must be positive")
    if speed_of_sound <= 0:
        raise ValueError("Speed of sound must be positive")

    params = TERMINATION_TO_PARAMS[termination]
    argument = params.a1 * diameter_ft * frequency_hz / speed_of_sound
    erl = 10.0 * math.log10(1.0 + (argument ** params.a2))
    return float(erl)


# --------------------------------------------------------------------------------------
# High-level helpers
# --------------------------------------------------------------------------------------

def compute_erl_table_flush_for_frequencies(
    diameter_in: float,
    frequencies_hz: Iterable[float],
) -> List[float]:
    return [erl_from_table_flush(diameter_in=diameter_in, frequency_hz=f) for f in frequencies_hz]


def compute_erl_equation_for_frequencies(
    diameter: float,
    frequencies_hz: Iterable[float],
    *,
    speed_of_sound: float = 1125.33,
    diameter_units: Literal["ft", "in"] = "ft",
    termination: Termination = "flush",
) -> List[float]:
    return [
        erl_from_equation(
            diameter=diameter,
            frequency_hz=f,
            speed_of_sound=speed_of_sound,
            diameter_units=diameter_units,
            termination=termination,
        )
        for f in frequencies_hz
    ]


# --------------------------------------------------------------------------------------
# CLI
# --------------------------------------------------------------------------------------

DEFAULT_OCTAVE_FREQS = [63, 125, 250, 500, 1000]


def _parse_frequencies(arg: Optional[str]) -> List[float]:
    if arg is None or arg.strip().lower() in {"octave", "default"}:
        return list(DEFAULT_OCTAVE_FREQS)
    # parse comma-separated numbers
    parts = [p.strip() for p in arg.split(",")]
    freqs: List[float] = []
    for p in parts:
        if not p:
            continue
        freqs.append(float(p))
    if not freqs:
        raise ValueError("No valid frequencies parsed")
    return freqs


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Compute duct end reflection loss (ERL) via table (flush) or simplified equation.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )

    parser.add_argument(
        "--method",
        choices=["table", "equation"],
        default="equation",
        help="Computation method",
    )

    # Geometry options
    geom = parser.add_argument_group("Geometry")
    geom.add_argument("--circular-diameter", type=float, help="Circular duct diameter value")
    geom.add_argument("--rect-width", type=float, help="Rectangular duct width")
    geom.add_argument("--rect-height", type=float, help="Rectangular duct height")
    geom.add_argument(
        "--units",
        choices=["in", "ft"],
        default="in",
        help="Units for geometry inputs (diameter, width, height)",
    )

    # Frequencies
    parser.add_argument(
        "--frequencies",
        type=str,
        default="octave",
        help="Comma-separated list of frequencies in Hz, or 'octave' for [63,125,250,500,1000]",
    )

    # Equation-only options
    parser.add_argument(
        "--termination",
        choices=["flush", "free"],
        default="flush",
        help="Termination type (equation method only)",
    )
    parser.add_argument(
        "--speed-of-sound",
        type=float,
        default=1125.33,
        help="Speed of sound (ft/s). Must be consistent with 'units' if using equation method.",
    )

    return parser


def _resolve_effective_diameter(units: Literal["in", "ft"], circular_diameter: Optional[float], rect_w: Optional[float], rect_h: Optional[float]) -> Tuple[float, Literal["in", "ft"]]:
    """Return (effective_diameter, units) based on provided geometry.

    - If circular_diameter is provided, use it directly.
    - Else, require rect_w and rect_h to compute effective diameter.
    """
    if circular_diameter is not None:
        return float(circular_diameter), units
    if rect_w is not None and rect_h is not None:
        d = compute_effective_diameter_rectangular(rect_w, rect_h)
        return float(d), units
    raise ValueError("Provide either --circular-diameter or both --rect-width and --rect-height")


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_arg_parser()
    args = parser.parse_args(argv)

    try:
        freqs = _parse_frequencies(args.frequencies)
        diameter_value, diameter_units = _resolve_effective_diameter(
            args.units, args.circular_diameter, args.rect_width, args.rect_height
        )

        if args.method == "table":
            if diameter_units != "in":
                # Table is defined in inches. Convert if needed.
                diameter_in = diameter_value * (12.0 if diameter_units == "ft" else 1.0)
            else:
                diameter_in = diameter_value
            erls = compute_erl_table_flush_for_frequencies(diameter_in, freqs)
            method_desc = "Table 28 (flush)"
        else:
            # Equation
            erls = compute_erl_equation_for_frequencies(
                diameter=diameter_value,
                frequencies_hz=freqs,
                speed_of_sound=args.speed_of_sound,
                diameter_units=diameter_units,
                termination=args.termination,
            )
            method_desc = f"Equation ({args.termination})"

        # Output
        print(f"Method: {method_desc}")
        print(f"Effective diameter: {diameter_value:.4g} {diameter_units}")
        print("Frequency (Hz), ERL (dB)")
        for f, e in zip(freqs, erls):
            print(f"{f:.6g}, {e:.6g}")

        return 0
    except Exception as exc:  # noqa: BLE001 - allow broad for CLI
        print(f"Error: {exc}")
        return 1


if __name__ == "__main__":  # pragma: no cover - CLI entry point
    raise SystemExit(main())

