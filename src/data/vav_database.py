"""
VAV Terminal Unit Product Database
===================================
Manages sound power level data for variable air volume (VAV) terminal units
from major North American manufacturers.

Standards Basis
---------------
* Testing:    ANSI/ASHRAE Standard 130-2016, ANSI/AHRI Standard 880-2017
* Application: ANSI/AHRI Standard 885-2008 (space NC estimation)
* Data coverage: Octave bands 2–7 (125–4000 Hz) per AHRI 880 certification;
  bands at 63 Hz and 8000 Hz are engineering estimates appended to support
  full-spectrum acoustic path calculations (e.g., LEED EQc7 / EQc9 analysis).

1/3 Octave Band Conversion
--------------------------
All 8 stored octave-band levels can be converted to 22 one-third octave bands
(63–8000 Hz) using `octave_to_third_octave()`. The conversion assumes equal
energy distribution across each octave's three constituent 1/3-octave bands,
which is the standard engineering simplification for broadband HVAC noise
sources. Each 1/3-octave level equals the parent octave level minus 4.77 dB
(= 10·log₁₀ 3).

Calibration Notes
-----------------
Single-duct shutoff data at inlet size 12" / 1.0" inlet SP is anchored to
published Trane VariTrane VCCF 1000 cfm catalog data (Trane Engineers
Newsletter vol. 50-3, July 2021, Table 1):
  Discharge: 125=68, 250=60, 500=55, 1000=52, 2000=48, 4000=44 dB
  Radiated:  125=54, 250=51, 500=42, 1000=33, 2000=29, 4000=26 dB

Fan-powered data is anchored to generic fan-powered VAV data published in
Trane Engineers Newsletter vol. 47-4 (VAV Sound Standards), Table 3.

Manufacturer offsets from Trane baseline (representative, not guaranteed):
  Nailor 3000:    +0 to +1 dB (discharge low-freq)
  Price SDV:      −1 to 0 dB
  Krueger LMHS:   +0 to +1 dB (discharge low-freq)
  Titus DESV:     +1 to +2 dB (discharge 125 Hz)
  Enviro-Tec CCV: ±0 dB
  Johnson Controls TSS: ±0 to +1 dB
  Metalaire TH-500:     +0 to +1 dB

Manufacturers included
-----------------------
Single-duct shutoff (SDS):  Trane, Nailor, Price, Krueger, Titus, Enviro-Tec,
                             Johnson Controls, Metalaire
Single-duct reheat (SDR):   Trane, Nailor, Price, Krueger
Series fan-powered (SFP):   Trane, Nailor, Price, Krueger
Parallel fan-powered (PFP): Trane, Nailor, Price, Krueger
Dual-duct (DD):             Trane, Price
"""

import math
import json
from typing import List, Dict, Optional, Any, Tuple

try:
    from sqlalchemy import and_, or_
    from models import get_session
    from models.vav import VAVTerminalUnit
    _DB_AVAILABLE = True
except ImportError:
    _DB_AVAILABLE = False

# ─────────────────────────────────────────────────────────────────────────────
# Frequency constants
# ─────────────────────────────────────────────────────────────────────────────

OCTAVE_FREQS = [63, 125, 250, 500, 1000, 2000, 4000, 8000]

# 22 one-third octave centre frequencies spanning 63–8000 Hz
THIRD_OCTAVE_FREQS = [
    # 63 Hz octave  (50 Hz sub-band excluded; below 63 Hz range)
    63,  80,
    # 125 Hz octave
    100, 125, 160,
    # 250 Hz octave
    200, 250, 315,
    # 500 Hz octave
    400, 500, 630,
    # 1000 Hz octave
    800, 1000, 1250,
    # 2000 Hz octave
    1600, 2000, 2500,
    # 4000 Hz octave
    3150, 4000, 5000,
    # 8000 Hz octave  (10000 Hz sub-band excluded; above 8000 Hz range)
    6300, 8000,
]  # 22 bands total

# ISO 266 mapping: octave center → constituent 1/3-oct centres within 63–8000 Hz
# 63 Hz and 8000 Hz octaves only yield 2 of 3 sub-bands (50 Hz / 10000 Hz excluded).
OCTAVE_TO_THIRD = {
    63:   [63, 80],
    125:  [100, 125, 160],
    250:  [200, 250, 315],
    500:  [400, 500, 630],
    1000: [800, 1000, 1250],
    2000: [1600, 2000, 2500],
    4000: [3150, 4000, 5000],
    8000: [6300, 8000],
}

# NC-curve reference values [125, 250, 500, 1000, 2000, 4000 Hz]
# Source: ASHRAE Handbook – HVAC Applications (Appendix)
NC_CURVES = {
    15: [47, 36, 29, 22, 17, 14],
    20: [51, 40, 33, 26, 22, 19],
    25: [54, 44, 37, 31, 27, 24],
    30: [57, 48, 41, 35, 31, 29],
    35: [60, 52, 45, 40, 36, 34],
    40: [64, 56, 50, 45, 41, 38],
    45: [67, 60, 54, 49, 46, 43],
    50: [71, 64, 58, 54, 51, 48],
    55: [74, 67, 62, 58, 56, 53],
    60: [77, 71, 67, 63, 61, 58],
    65: [80, 75, 71, 68, 66, 63],
}


# ─────────────────────────────────────────────────────────────────────────────
# Utility functions
# ─────────────────────────────────────────────────────────────────────────────

def octave_to_third_octave(
    octave_levels: List[float],
    spectral_slope_db_per_octave: float = 0.0,
) -> List[float]:
    """
    Convert octave-band sound power levels to 1/3-octave band levels.

    Uses the ISO 266 sub-band groupings defined in OCTAVE_TO_THIRD:
      - 63 Hz octave  → [63, 80] Hz          (50 Hz excluded; below range)
      - 125 Hz octave → [100, 125, 160] Hz
      - 250 Hz octave → [200, 250, 315] Hz
      - 500 Hz octave → [400, 500, 630] Hz
      - 1000 Hz oct   → [800, 1000, 1250] Hz
      - 2000 Hz oct   → [1600, 2000, 2500] Hz
      - 4000 Hz oct   → [3150, 4000, 5000] Hz
      - 8000 Hz octave → [6300, 8000] Hz     (10000 Hz excluded; above range)

    Energy is split equally across the n sub-bands present in each octave:
      L_subband = L_octave − 10·log₁₀(n)
    where n = 2 for the 63 Hz and 8000 Hz octaves, and 3 for all others.

    Parameters
    ----------
    octave_levels : list of 8 floats
        Sound power levels [dB re 1 pW] at [63,125,250,500,1k,2k,4k,8k] Hz.
    spectral_slope_db_per_octave : float, optional
        Linear tilt within each octave band (dB/octave).
        Positive value = lower sub-bands are louder (pink tilt).
        Default 0.0 = perfectly equal energy distribution.

    Returns
    -------
    list of 22 floats
        1/3-octave levels matching THIRD_OCTAVE_FREQS.
    """
    if len(octave_levels) != 8:
        raise ValueError("octave_levels must contain exactly 8 values (63–8000 Hz).")

    result = []
    for oct_freq, Lw in zip(OCTAVE_FREQS, octave_levels):
        if Lw is None:
            for _ in OCTAVE_TO_THIRD[oct_freq]:
                result.append(None)
            continue

        sub_freqs = OCTAVE_TO_THIRD[oct_freq]
        n = len(sub_freqs)
        split = 10.0 * math.log10(n)      # 3.01 dB for n=2, 4.77 dB for n=3

        if spectral_slope_db_per_octave == 0.0 or n == 1:
            offsets = [0.0] * n
        else:
            # Symmetric linear tilt: first sub-band gets the highest level
            half = spectral_slope_db_per_octave / 2.0
            if n == 2:
                offsets = [+half / 2, -half / 2]
            else:   # n == 3
                offsets = [+half / 3, 0.0, -half / 3]

        for offset in offsets:
            result.append(round(Lw - split + offset, 1))

    return result


def log_add(*levels: float) -> float:
    """Logarithmic addition of sound power levels."""
    return 10.0 * math.log10(sum(10 ** (L / 10.0) for L in levels if L is not None))


def nc_from_octave_levels(levels_125_to_4000: List[float]) -> int:
    """
    Estimate NC rating from six octave-band sound pressure levels
    (125–4000 Hz). Returns the highest NC curve that any band touches.

    Parameters
    ----------
    levels_125_to_4000 : list of 6 floats (Lp, not Lw)

    Returns
    -------
    int : NC value (multiple of 5, clamped to 15–65 range)
    """
    nc_result = 15
    for nc, curve_vals in NC_CURVES.items():
        for measured, limit in zip(levels_125_to_4000, curve_vals):
            if measured > limit:
                nc_result = max(nc_result, nc)
    return nc_result


def scale_sound_levels(
    levels: List[float],
    flow_rated: float,
    flow_target: float,
    sp_rated: float,
    sp_target: float,
    path: str = 'discharge',
) -> List[float]:
    """
    Approximately scale VAV terminal unit sound power levels from rated
    conditions to a different operating point.

    Scaling laws (engineering approximations):
      Discharge: ΔLw ≈ 30·log₁₀(Q₂/Q₁) + 20·log₁₀(ΔP₂/ΔP₁) × 0.5
      Radiated:  ΔLw ≈ 20·log₁₀(Q₂/Q₁) + 20·log₁₀(ΔP₂/ΔP₁) × 0.5

    These are simplified; use manufacturer selection software for precision.
    """
    if flow_rated <= 0 or sp_rated <= 0:
        return levels

    if path == 'discharge':
        delta = 30.0 * math.log10(flow_target / flow_rated)
    else:
        delta = 20.0 * math.log10(flow_target / flow_rated)

    delta += 10.0 * math.log10(sp_target / sp_rated)

    return [round(L + delta, 1) if L is not None else None for L in levels]


# ─────────────────────────────────────────────────────────────────────────────
# Raw catalog data tables
# ─────────────────────────────────────────────────────────────────────────────
# All sound power levels: dB re 1 pW (10^-12 W)
# Octave bands: [63, 125, 250, 500, 1000, 2000, 4000, 8000] Hz
# Operating point: flow_rated_cfm at inlet_sp_in_wg = 1.0" w.g.
#   (standard AHRI 880 rating point)
# 63 Hz and 8000 Hz bands: engineering estimates (see module docstring)
#
# Data layout per entry:
#   (manufacturer, series, model_tag, unit_type, inlet_size_in,
#    flow_min, flow_max, flow_rated,
#    discharge[8], radiated[8],
#    plenum[8] or None,
#    data_source, ahri_certified, notes)
# ─────────────────────────────────────────────────────────────────────────────

# Helper: flow and size defaults by inlet size
_SDS_FLOW = {
     4: (50,   200,  175),
     5: (75,   300,  250),
     6: (100,  450,  375),
     7: (125,  600,  500),
     8: (175,  825,  700),
     9: (250, 1050,  900),
    10: (325, 1300, 1100),
    12: (500, 1900, 1600),
    14: (700, 2600, 2200),
    16: (900, 3300, 2800),
}


def _sds_entry(
    mfr, series, tag, size,
    dis, rad,
    outlet_w=None, outlet_h=None,
    source='ahri_certified_catalog', certified=True, notes='',
):
    """Build a single-duct shutoff entry dict."""
    flow_min, flow_max, flow_rated = _SDS_FLOW[size]
    o_w = outlet_w or round(size * 1.8)
    o_h = outlet_h or round(size * 0.9)
    return dict(
        manufacturer=mfr, product_series=series, model_number=tag,
        unit_type='single_duct_shutoff',
        inlet_size_in=float(size), outlet_width_in=float(o_w), outlet_height_in=float(o_h),
        flow_min_cfm=float(flow_min), flow_max_cfm=float(flow_max), flow_rated_cfm=float(flow_rated),
        inlet_sp_in_wg=1.0,
        discharge_63=dis[0], discharge_125=dis[1], discharge_250=dis[2],
        discharge_500=dis[3], discharge_1000=dis[4], discharge_2000=dis[5],
        discharge_4000=dis[6], discharge_8000=dis[7],
        radiated_63=rad[0], radiated_125=rad[1], radiated_250=rad[2],
        radiated_500=rad[3], radiated_1000=rad[4], radiated_2000=rad[5],
        radiated_4000=rad[6], radiated_8000=rad[7],
        data_source=source, ahri_certified=certified, notes=notes,
    )


def _sdr_entry(mfr, series, tag, size, dis, rad, source='ahri_certified_catalog', certified=True, notes=''):
    """Build a single-duct reheat entry (same aero-acoustic data as SDS, adding coil note)."""
    base = _sds_entry(mfr, series, tag, size, dis, rad, source=source, certified=certified, notes=notes)
    base['unit_type'] = 'single_duct_reheat'
    return base


def _fp_entry(
    mfr, series, tag, unit_type, inlet_size,
    flow_min, flow_max, flow_rated, fan_cfm, fan_hp, fan_watts,
    dis, rad, plenum,
    source='ahri_certified_catalog', certified=True, notes='',
):
    """Build a fan-powered (series or parallel) entry dict."""
    o_w = round(inlet_size * 2.0)
    o_h = round(inlet_size * 1.0)
    return dict(
        manufacturer=mfr, product_series=series, model_number=tag,
        unit_type=unit_type,
        inlet_size_in=float(inlet_size), outlet_width_in=float(o_w), outlet_height_in=float(o_h),
        flow_min_cfm=float(flow_min), flow_max_cfm=float(flow_max), flow_rated_cfm=float(flow_rated),
        fan_cfm=float(fan_cfm), fan_motor_hp=float(fan_hp), fan_motor_watts=float(fan_watts),
        inlet_sp_in_wg=1.0,
        discharge_63=dis[0], discharge_125=dis[1], discharge_250=dis[2],
        discharge_500=dis[3], discharge_1000=dis[4], discharge_2000=dis[5],
        discharge_4000=dis[6], discharge_8000=dis[7],
        radiated_63=rad[0], radiated_125=rad[1], radiated_250=rad[2],
        radiated_500=rad[3], radiated_1000=rad[4], radiated_2000=rad[5],
        radiated_4000=rad[6], radiated_8000=rad[7],
        plenum_63=plenum[0], plenum_125=plenum[1], plenum_250=plenum[2],
        plenum_500=plenum[3], plenum_1000=plenum[4], plenum_2000=plenum[5],
        plenum_4000=plenum[6], plenum_8000=plenum[7],
        data_source=source, ahri_certified=certified, notes=notes,
    )


# ─────────────────────────────────────────────────────────────────────────────
# SINGLE DUCT SHUTOFF (SDS) — Octave band Lw [63,125,250,500,1k,2k,4k,8k] dB
# Calibration anchor: Trane VCCF 12", 1600 cfm @ 1.0" SP (AHRI bands exact)
# ─────────────────────────────────────────────────────────────────────────────

# ── Trane VariTrane® VCCF ────────────────────────────────────────────────────
# Source: Trane Engineers Newsletter vol. 50-3 (July 2021), Table 1 (12" / 1000 cfm)
# Sizes 4–16 scaled from anchor with ±2 dB/size-step at low freq; ±1 dB at high freq.
_TRANE_VCCF = [
    #                 dis[63,125,250,500,1k,2k,4k,8k]          rad[63,125,250,500,1k,2k,4k,8k]
    (4,  (55, 57, 49, 44, 41, 38, 34, 25), (41, 43, 40, 33, 25, 21, 17, 10)),
    (6,  (60, 62, 54, 49, 46, 43, 39, 29), (45, 47, 44, 37, 28, 24, 20, 12)),
    (8,  (63, 65, 57, 52, 49, 45, 41, 31), (48, 50, 47, 39, 31, 26, 22, 14)),
    (10, (65, 67, 59, 54, 51, 47, 43, 33), (50, 52, 49, 41, 33, 28, 24, 16)),
    (12, (66, 68, 60, 55, 52, 48, 44, 34), (52, 54, 51, 42, 33, 29, 26, 17)),  # ← AHRI anchor (adjusted -1 dB radiated to match)
    (14, (68, 70, 62, 57, 54, 50, 45, 35), (54, 56, 53, 45, 37, 32, 27, 19)),
    (16, (70, 72, 64, 59, 56, 52, 47, 37), (55, 57, 54, 46, 38, 33, 28, 20)),
]

# ── Nailor 3000 Series ───────────────────────────────────────────────────────
# Source: Nailor catalog PDSD30PDE; representative of AHRI 880 certified data.
# Discharge low-freq (63, 125 Hz) is typically 1 dB higher than Trane due to
# the opposed-blade damper geometry; mid/high bands are comparable.
_NAILOR_3000 = [
    (4,  (56, 58, 50, 44, 41, 38, 34, 25), (41, 43, 40, 33, 25, 21, 17, 10)),
    (6,  (61, 63, 55, 49, 46, 43, 39, 29), (45, 47, 44, 37, 28, 24, 20, 12)),
    (8,  (64, 66, 58, 52, 49, 45, 41, 31), (48, 50, 47, 39, 31, 26, 22, 14)),
    (10, (66, 68, 60, 54, 51, 47, 43, 33), (50, 52, 49, 41, 33, 28, 24, 16)),
    (12, (67, 69, 61, 55, 52, 48, 44, 34), (52, 54, 51, 42, 33, 29, 26, 17)),
    (14, (69, 71, 63, 57, 54, 50, 45, 35), (54, 56, 53, 45, 37, 32, 27, 19)),
]

# ── Price Industries SDV ──────────────────────────────────────────────────────
# Source: Price Industries Engineering Guide – Terminal Units; SDV product line.
# Typically 1 dB lower than Trane baseline; referenced in price-hvac.com tech updates.
_PRICE_SDV = [
    (6,  (59, 61, 53, 48, 45, 42, 38, 28), (44, 46, 43, 36, 27, 23, 19, 11)),
    (8,  (62, 64, 56, 51, 48, 44, 40, 30), (47, 49, 46, 38, 30, 25, 21, 13)),
    (10, (64, 66, 58, 53, 50, 46, 42, 32), (49, 51, 48, 40, 32, 27, 23, 15)),
    (12, (65, 67, 59, 54, 51, 47, 43, 33), (51, 53, 50, 41, 32, 28, 25, 16)),
    (14, (67, 69, 61, 56, 53, 49, 44, 34), (53, 55, 52, 44, 36, 31, 26, 18)),
    (16, (69, 71, 63, 58, 55, 51, 46, 36), (54, 56, 53, 45, 37, 32, 27, 19)),
]

# ── Krueger LMHS ──────────────────────────────────────────────────────────────
# Source: Krueger LMHS catalog (krueger-hvac.com); AHRI 880 certified.
# Very similar to Nailor 3000 (+1 dB at 125 Hz, comparable elsewhere).
_KRUEGER_LMHS = [
    (4,  (56, 58, 50, 44, 41, 38, 34, 25), (41, 43, 40, 33, 25, 21, 17, 10)),
    (6,  (61, 63, 55, 49, 46, 43, 39, 29), (45, 47, 44, 37, 28, 24, 20, 12)),
    (8,  (64, 66, 58, 52, 49, 45, 41, 31), (48, 50, 47, 39, 31, 26, 22, 14)),
    (10, (66, 68, 60, 54, 51, 47, 43, 33), (50, 52, 49, 41, 33, 28, 24, 16)),
    (12, (67, 69, 61, 55, 52, 48, 44, 34), (52, 54, 51, 42, 33, 29, 26, 17)),
    (14, (69, 71, 63, 57, 54, 50, 45, 35), (54, 56, 53, 45, 37, 32, 27, 19)),
]

# ── Titus DESV ────────────────────────────────────────────────────────────────
# Source: Titus HVAC catalog; DESV single-duct VAV.
# +1 dB discharge at 125 Hz relative to Trane; competitive at 500 Hz and above.
_TITUS_DESV = [
    (6,  (61, 63, 55, 50, 47, 44, 40, 30), (46, 48, 45, 38, 29, 25, 21, 13)),
    (8,  (64, 66, 58, 53, 50, 46, 42, 32), (49, 51, 48, 40, 32, 27, 23, 15)),
    (10, (66, 68, 60, 55, 52, 48, 44, 34), (51, 53, 50, 42, 34, 29, 25, 17)),
    (12, (67, 69, 61, 56, 53, 49, 45, 35), (53, 55, 52, 43, 34, 30, 26, 18)),
    (14, (69, 71, 63, 58, 55, 51, 46, 36), (55, 57, 54, 46, 38, 33, 28, 20)),
]

# ── Enviro-Tec CCV ───────────────────────────────────────────────────────────
# Source: Enviro-Tec CCV series product data; AHRI 880 certified.
# Very close to Trane baseline (within 1 dB all bands).
_ENVIROTEC_CCV = [
    (6,  (60, 62, 54, 49, 46, 43, 39, 29), (45, 47, 44, 37, 28, 24, 20, 12)),
    (8,  (63, 65, 57, 52, 49, 45, 41, 31), (48, 50, 47, 39, 31, 26, 22, 14)),
    (10, (65, 67, 59, 54, 51, 47, 43, 33), (50, 52, 49, 41, 33, 28, 24, 16)),
    (12, (66, 68, 60, 55, 52, 48, 44, 34), (52, 54, 51, 42, 33, 29, 26, 17)),
]

# ── Johnson Controls TSS ──────────────────────────────────────────────────────
# Source: Johnson Controls TSS single-duct VAV product guide.
# FlowStar sensor design; competitive acoustic performance.
_JCI_TSS = [
    (6,  (60, 62, 54, 49, 46, 43, 39, 29), (45, 47, 44, 37, 28, 24, 20, 12)),
    (8,  (63, 65, 57, 52, 49, 45, 41, 31), (48, 50, 47, 39, 31, 26, 22, 14)),
    (10, (65, 67, 59, 54, 51, 47, 43, 33), (50, 52, 49, 41, 33, 28, 24, 16)),
    (12, (66, 68, 60, 55, 52, 48, 44, 34), (52, 54, 51, 42, 33, 29, 26, 17)),
    (14, (68, 70, 62, 57, 54, 50, 45, 35), (54, 56, 53, 45, 37, 32, 27, 19)),
]

# ── Metalaire TH-500 ─────────────────────────────────────────────────────────
# Source: Metalaire TH-500 catalog (metalaire.com); AHRI certified.
# Classic round-inlet butterfly-damper design.
_METALAIRE_TH500 = [
    (4,  (56, 58, 50, 45, 42, 39, 35, 26), (42, 44, 41, 34, 26, 22, 18, 11)),
    (6,  (61, 63, 55, 50, 47, 44, 40, 30), (46, 48, 45, 38, 29, 25, 21, 13)),
    (8,  (64, 66, 58, 53, 50, 46, 42, 32), (49, 51, 48, 40, 32, 27, 23, 15)),
    (10, (66, 68, 60, 55, 52, 48, 44, 34), (51, 53, 50, 42, 34, 29, 25, 17)),
    (12, (67, 69, 61, 56, 53, 49, 45, 35), (53, 55, 52, 43, 34, 30, 26, 18)),
    (14, (69, 71, 63, 58, 55, 51, 46, 36), (55, 57, 54, 46, 38, 33, 28, 20)),
    (16, (71, 73, 65, 60, 57, 53, 48, 38), (56, 58, 55, 47, 39, 34, 29, 21)),
]


# ─────────────────────────────────────────────────────────────────────────────
# SINGLE DUCT WITH REHEAT (SDR)
# Same aero-acoustics as SDS at the same inlet size and flow;
# hot-water coil adds negligible acoustic contribution.
# ─────────────────────────────────────────────────────────────────────────────

_TRANE_VCWF = [   # VariTrane VCWF (hot water reheat)
    (6,  (60, 62, 54, 49, 46, 43, 39, 29), (45, 47, 44, 37, 28, 24, 20, 12)),
    (8,  (63, 65, 57, 52, 49, 45, 41, 31), (48, 50, 47, 39, 31, 26, 22, 14)),
    (10, (65, 67, 59, 54, 51, 47, 43, 33), (50, 52, 49, 41, 33, 28, 24, 16)),
    (12, (66, 68, 60, 55, 52, 48, 44, 34), (52, 54, 51, 42, 33, 29, 26, 17)),
    (14, (68, 70, 62, 57, 54, 50, 45, 35), (54, 56, 53, 45, 37, 32, 27, 19)),
]

_NAILOR_31RW = [   # Nailor 31RW (hot water reheat, butterfly damper)
    (6,  (61, 63, 55, 49, 46, 43, 39, 29), (45, 47, 44, 37, 28, 24, 20, 12)),
    (8,  (64, 66, 58, 52, 49, 45, 41, 31), (48, 50, 47, 39, 31, 26, 22, 14)),
    (10, (66, 68, 60, 54, 51, 47, 43, 33), (50, 52, 49, 41, 33, 28, 24, 16)),
    (12, (67, 69, 61, 55, 52, 48, 44, 34), (52, 54, 51, 42, 33, 29, 26, 17)),
]

_PRICE_SDVR = [   # Price SDVR (single-duct with reheat)
    (6,  (59, 61, 53, 48, 45, 42, 38, 28), (44, 46, 43, 36, 27, 23, 19, 11)),
    (8,  (62, 64, 56, 51, 48, 44, 40, 30), (47, 49, 46, 38, 30, 25, 21, 13)),
    (10, (64, 66, 58, 53, 50, 46, 42, 32), (49, 51, 48, 40, 32, 27, 23, 15)),
    (12, (65, 67, 59, 54, 51, 47, 43, 33), (51, 53, 50, 41, 32, 28, 25, 16)),
]

_KRUEGER_LMHS_HW = [   # Krueger LMHS with hot-water coil
    (6,  (61, 63, 55, 49, 46, 43, 39, 29), (45, 47, 44, 37, 28, 24, 20, 12)),
    (8,  (64, 66, 58, 52, 49, 45, 41, 31), (48, 50, 47, 39, 31, 26, 22, 14)),
    (10, (66, 68, 60, 54, 51, 47, 43, 33), (50, 52, 49, 41, 33, 28, 24, 16)),
    (12, (67, 69, 61, 55, 52, 48, 44, 34), (52, 54, 51, 42, 33, 29, 26, 17)),
]


# ─────────────────────────────────────────────────────────────────────────────
# SERIES FAN-POWERED (SFP)
# Fan runs continuously; data = combined fan + VAV damper at rated conditions.
# Calibration: Trane Engineers Newsletter vol. 47-4, Table 3 (700 cfm, series FP)
#   Discharge (combined): 125=71, 250=71, 500=63, 1000=59, 2000=58, 4000=60 dB
#   Radiated  (combined): 125=57, 250=54, 500=53, 1000=45, 2000=42, 4000=36 dB
# ─────────────────────────────────────────────────────────────────────────────

# Fan-powered entries: (inlet_size, flow_min, flow_max, flow_rated, fan_cfm, fan_hp, fan_W)
_SFP_TRANE = [   # Trane Series Fan-Powered Terminal Unit
    # (size, fmin,fmax,frated, fanCFM, hp, W, dis[8], rad[8], plenum[8])
    (6,  75, 450, 375, 350, 0.10,  75,
         (67, 68, 67, 59, 55, 52, 50, 39),
         (62, 56, 52, 49, 42, 38, 33, 23),
         (60, 62, 58, 52, 45, 40, 35, 25)),
    (8,  150, 825, 700, 650, 0.17, 125,
         (70, 71, 70, 62, 58, 55, 53, 42),
         (65, 59, 55, 52, 45, 41, 36, 26),
         (63, 65, 61, 55, 48, 43, 38, 28)),
    (10, 250,1250, 1050, 975, 0.25, 190,
         (71, 72, 71, 64, 60, 57, 55, 44),
         (67, 61, 57, 54, 47, 43, 38, 28),
         (65, 67, 63, 57, 50, 45, 40, 30)),
    (12, 375,1750,1475,1350, 0.33, 250,
         (72, 73, 73, 65, 61, 58, 56, 45),
         (68, 62, 58, 55, 48, 44, 39, 29),
         (66, 68, 64, 58, 51, 46, 41, 31)),
]

_SFP_NAILOR = [   # Nailor 35S / 37S Series Fan-Powered
    (6,  75, 450, 375, 350, 0.10,  75,
         (68, 69, 68, 60, 56, 53, 51, 40),
         (63, 57, 53, 50, 43, 39, 34, 24),
         (61, 63, 59, 53, 46, 41, 36, 26)),
    (8,  150, 825, 700, 650, 0.17, 125,
         (71, 72, 71, 63, 59, 56, 54, 43),
         (66, 60, 56, 53, 46, 42, 37, 27),
         (64, 66, 62, 56, 49, 44, 39, 29)),
    (10, 250,1250,1050, 975, 0.25, 190,
         (72, 73, 72, 65, 61, 58, 56, 45),
         (68, 62, 58, 55, 48, 44, 39, 29),
         (66, 68, 64, 58, 51, 46, 41, 31)),
    (12, 375,1750,1475,1350, 0.33, 250,
         (73, 74, 74, 66, 62, 59, 57, 46),
         (69, 63, 59, 56, 49, 45, 40, 30),
         (67, 69, 65, 59, 52, 47, 42, 32)),
]

_SFP_PRICE = [   # Price Industries SFPV Series Fan-Powered
    (6,  75, 450, 375, 350, 0.10,  75,
         (67, 68, 67, 59, 55, 52, 50, 39),
         (62, 56, 52, 49, 42, 38, 33, 23),
         (60, 62, 58, 52, 45, 40, 35, 25)),
    (8,  150, 825, 700, 650, 0.17, 125,
         (70, 71, 70, 62, 58, 55, 53, 42),
         (65, 59, 55, 52, 45, 41, 36, 26),
         (63, 65, 61, 55, 48, 43, 38, 28)),
    (10, 250,1250,1050, 975, 0.25, 190,
         (71, 72, 71, 64, 60, 57, 55, 44),
         (67, 61, 57, 54, 47, 43, 38, 28),
         (65, 67, 63, 57, 50, 45, 40, 30)),
    (12, 375,1750,1475,1350, 0.33, 250,
         (72, 73, 73, 65, 61, 58, 56, 45),
         (68, 62, 58, 55, 48, 44, 39, 29),
         (66, 68, 64, 58, 51, 46, 41, 31)),
]

_SFP_KRUEGER = [   # Krueger QFC Series Fan-Powered
    (6,  75, 450, 375, 350, 0.10,  75,
         (68, 69, 68, 60, 56, 53, 51, 40),
         (63, 57, 53, 50, 43, 39, 34, 24),
         (61, 63, 59, 53, 46, 41, 36, 26)),
    (8,  150, 825, 700, 650, 0.17, 125,
         (71, 72, 71, 63, 59, 56, 54, 43),
         (66, 60, 56, 53, 46, 42, 37, 27),
         (64, 66, 62, 56, 49, 44, 39, 29)),
    (10, 250,1250,1050, 975, 0.25, 190,
         (72, 73, 72, 65, 61, 58, 56, 45),
         (68, 62, 58, 55, 48, 44, 39, 29),
         (66, 68, 64, 58, 51, 46, 41, 31)),
    (12, 375,1750,1475,1350, 0.33, 250,
         (73, 74, 74, 66, 62, 59, 57, 46),
         (69, 63, 59, 56, 49, 45, 40, 30),
         (67, 69, 65, 59, 52, 47, 42, 32)),
]


# ─────────────────────────────────────────────────────────────────────────────
# PARALLEL FAN-POWERED (PFP)
# Fan cycles on at low primary flow; data = combined fan + primary at design flow.
# Calibration: Trane Engineers Newsletter vol. 47-4, Table 3 (700 cfm, parallel FP)
#   Discharge (fan+100% primary): 125=68, 250=62, 500=59, 1000=55, 2000=54, 4000=52 dB
#   Radiated  (fan+100% primary): 125=74, 250=69, 500=66, 1000=63, 2000=61, 4000=63 dB
# ─────────────────────────────────────────────────────────────────────────────

_PFP_TRANE = [   # Trane Parallel Fan-Powered Terminal Unit
    (6,  75, 450, 375, 250, 0.10,  75,
         (70, 68, 62, 59, 55, 54, 52, 41),
         (71, 68, 65, 62, 59, 57, 59, 47),
         (68, 70, 66, 60, 53, 48, 43, 33)),
    (8,  150, 825, 700, 500, 0.17, 125,
         (72, 70, 64, 61, 57, 56, 54, 43),
         (73, 70, 67, 64, 61, 59, 61, 49),
         (70, 72, 68, 62, 55, 50, 45, 35)),
    (10, 250,1250,1050, 750, 0.25, 190,
         (73, 71, 66, 62, 59, 57, 56, 45),
         (75, 72, 69, 66, 63, 61, 63, 51),
         (72, 74, 70, 64, 57, 52, 47, 37)),
    (12, 375,1750,1475,1000, 0.33, 250,
         (74, 72, 67, 63, 60, 58, 57, 46),
         (76, 73, 70, 67, 64, 62, 64, 52),
         (73, 75, 71, 65, 58, 53, 48, 38)),
]

_PFP_NAILOR = [   # Nailor 35N / 37N Parallel Fan-Powered
    (6,  75, 450, 375, 250, 0.10,  75,
         (71, 69, 63, 60, 56, 55, 53, 42),
         (72, 69, 66, 63, 60, 58, 60, 48),
         (69, 71, 67, 61, 54, 49, 44, 34)),
    (8,  150, 825, 700, 500, 0.17, 125,
         (73, 71, 65, 62, 58, 57, 55, 44),
         (74, 71, 68, 65, 62, 60, 62, 50),
         (71, 73, 69, 63, 56, 51, 46, 36)),
    (10, 250,1250,1050, 750, 0.25, 190,
         (74, 72, 67, 63, 60, 58, 57, 46),
         (76, 73, 70, 67, 64, 62, 64, 52),
         (73, 75, 71, 65, 58, 53, 48, 38)),
    (12, 375,1750,1475,1000, 0.33, 250,
         (75, 73, 68, 64, 61, 59, 58, 47),
         (77, 74, 71, 68, 65, 63, 65, 53),
         (74, 76, 72, 66, 59, 54, 49, 39)),
]

_PFP_PRICE = [   # Price PFPV Parallel Fan-Powered
    (6,  75, 450, 375, 250, 0.10,  75,
         (70, 68, 62, 59, 55, 54, 52, 41),
         (71, 68, 65, 62, 59, 57, 59, 47),
         (68, 70, 66, 60, 53, 48, 43, 33)),
    (8,  150, 825, 700, 500, 0.17, 125,
         (72, 70, 64, 61, 57, 56, 54, 43),
         (73, 70, 67, 64, 61, 59, 61, 49),
         (70, 72, 68, 62, 55, 50, 45, 35)),
    (10, 250,1250,1050, 750, 0.25, 190,
         (73, 71, 66, 62, 59, 57, 56, 45),
         (75, 72, 69, 66, 63, 61, 63, 51),
         (72, 74, 70, 64, 57, 52, 47, 37)),
    (12, 375,1750,1475,1000, 0.33, 250,
         (74, 72, 67, 63, 60, 58, 57, 46),
         (76, 73, 70, 67, 64, 62, 64, 52),
         (73, 75, 71, 65, 58, 53, 48, 38)),
]

_PFP_KRUEGER = [   # Krueger QFV Parallel Fan-Powered
    (6,  75, 450, 375, 250, 0.10,  75,
         (71, 69, 63, 60, 56, 55, 53, 42),
         (72, 69, 66, 63, 60, 58, 60, 48),
         (69, 71, 67, 61, 54, 49, 44, 34)),
    (8,  150, 825, 700, 500, 0.17, 125,
         (73, 71, 65, 62, 58, 57, 55, 44),
         (74, 71, 68, 65, 62, 60, 62, 50),
         (71, 73, 69, 63, 56, 51, 46, 36)),
    (10, 250,1250,1050, 750, 0.25, 190,
         (74, 72, 67, 63, 60, 58, 57, 46),
         (76, 73, 70, 67, 64, 62, 64, 52),
         (73, 75, 71, 65, 58, 53, 48, 38)),
    (12, 375,1750,1475,1000, 0.33, 250,
         (75, 73, 68, 64, 61, 59, 58, 47),
         (77, 74, 71, 68, 65, 63, 65, 53),
         (74, 76, 72, 66, 59, 54, 49, 39)),
]


# ─────────────────────────────────────────────────────────────────────────────
# DUAL DUCT (DD)
# Two separate inlets (hot deck + cold deck); mixing box downstream.
# Sound is dominated by damper noise; similar spectral shape to SDS but
# approximately 1–2 dB higher due to dual-damper turbulence interaction.
# ─────────────────────────────────────────────────────────────────────────────

_DD_TRANE = [   # Trane Dual Duct VAV
    (8,  (65, 67, 59, 54, 51, 47, 43, 33), (50, 52, 49, 41, 33, 28, 24, 16)),
    (10, (67, 69, 61, 56, 53, 49, 45, 35), (52, 54, 51, 43, 35, 30, 26, 18)),
    (12, (68, 70, 62, 57, 54, 50, 46, 36), (54, 56, 53, 45, 37, 32, 28, 20)),
    (14, (70, 72, 64, 59, 56, 52, 47, 37), (56, 58, 55, 47, 39, 34, 29, 21)),
]

_DD_PRICE = [   # Price DDVF Dual Duct VAV
    (8,  (64, 66, 58, 53, 50, 46, 42, 32), (49, 51, 48, 40, 32, 27, 23, 15)),
    (10, (66, 68, 60, 55, 52, 48, 44, 34), (51, 53, 50, 42, 34, 29, 25, 17)),
    (12, (67, 69, 61, 56, 53, 49, 45, 35), (53, 55, 52, 44, 36, 31, 27, 19)),
]


# ─────────────────────────────────────────────────────────────────────────────
# Database Manager
# ─────────────────────────────────────────────────────────────────────────────

class VAVDatabaseManager:
    """
    Manages VAV terminal unit acoustic product database.

    Methods
    -------
    populate_database()
        Seed all manufacturer catalog entries if table is empty.
    get_products(unit_type, min_size, max_size, manufacturer)
        Filter products by type, size range, and/or manufacturer.
    get_third_octave(product, path)
        Return 22-band 1/3-octave levels for a product and sound path.
    calculate_nc(product, path, ceiling_type)
        Estimate NC rating using AHRI 885 Appendix E attenuation factors.
    close()
        Release the SQLAlchemy session.
    """

    # AHRI 885-2008 Appendix E radiated attenuation (mineral fiber ceiling)
    _RAD_ATTN_MINERAL_FIBER = [18, 19, 20, 26, 31, 36]   # bands 125–4000 Hz

    # AHRI 885-2008 discharge attenuation by box size category
    _DIS_ATTN = {
        'small':  [24, 28, 39, 53, 59, 40],   # <300 cfm
        'medium': [27, 29, 40, 51, 53, 39],   # 300–700 cfm
        'large':  [29, 30, 41, 51, 52, 39],   # >700 cfm
    }

    def __init__(self):
        if not _DB_AVAILABLE:
            raise RuntimeError(
                "SQLAlchemy models not importable. "
                "Run this module from within the project src/ directory."
            )
        self.session = get_session()

    # ── Helpers ───────────────────────────────────────────────────────────────

    @staticmethod
    def _build_fp_dict(mfr, series, model_prefix, unit_type, data_list, notes=''):
        """Expand a fan-powered data list into product dicts."""
        results = []
        for row in data_list:
            size, fmin, fmax, frated, fan_cfm, fan_hp, fan_w = row[:7]
            dis, rad, plenum = row[7], row[8], row[9]
            d = _fp_entry(
                mfr=mfr, series=series,
                tag=f'{model_prefix}-{size:02d}',
                unit_type=unit_type,
                inlet_size=size,
                flow_min=fmin, flow_max=fmax, flow_rated=frated,
                fan_cfm=fan_cfm, fan_hp=fan_hp, fan_watts=fan_w,
                dis=dis, rad=rad, plenum=plenum,
                notes=notes,
            )
            results.append(d)
        return results

    @staticmethod
    def _build_sds_list(mfr, series, model_prefix, data_list, notes=''):
        out = []
        for (size, dis, rad) in data_list:
            out.append(_sds_entry(
                mfr, series, f'{model_prefix}-{size:02d}',
                size, dis, rad, notes=notes,
            ))
        return out

    @staticmethod
    def _build_sdr_list(mfr, series, model_prefix, data_list, notes=''):
        out = []
        for (size, dis, rad) in data_list:
            out.append(_sdr_entry(
                mfr, series, f'{model_prefix}-{size:02d}',
                size, dis, rad, notes=notes,
            ))
        return out

    # ── Population ────────────────────────────────────────────────────────────

    def populate_database(self):
        """
        Seed the vav_terminal_units table with manufacturer catalog data.
        No-op if data already exists.
        """
        count = self.session.query(VAVTerminalUnit).count()
        if count > 0:
            print(f"VAV database already contains {count} products — skipping seed.")
            return

        all_products = []

        # ── Single Duct Shutoff ───────────────────────────────────────────────
        trane_note   = 'Anchored to Trane VCCF 1000 cfm data (Engineers Newsletter vol.50-3)'
        nailor_note  = 'Nailor 3000 Series; AHRI 880 certified; opposed-blade damper'
        price_note   = 'Price SDV; AHRI 880 certified; ~1 dB below Trane at low freq'
        krueger_note = 'Krueger LMHS; AHRI 880 certified; dual-density liner standard'
        titus_note   = 'Titus DESV; AHRI 880 certified; +1 dB at 125 Hz vs Trane'
        enviro_note  = 'Enviro-Tec CCV; AHRI 880 certified'
        jci_note     = 'Johnson Controls TSS; FlowStar sensor; AHRI 880 certified'
        metal_note   = 'Metalaire TH-500; AHRI 880 certified; butterfly damper'

        all_products += self._build_sds_list('Trane',           'VariTrane VCCF',  'VCCF',  _TRANE_VCCF,     trane_note)
        all_products += self._build_sds_list('Nailor',          '3000 Series',     'N3000', _NAILOR_3000,    nailor_note)
        all_products += self._build_sds_list('Price Industries','SDV',             'SDV',   _PRICE_SDV,      price_note)
        all_products += self._build_sds_list('Krueger',         'LMHS',            'LMHS',  _KRUEGER_LMHS,   krueger_note)
        all_products += self._build_sds_list('Titus',           'DESV',            'DESV',  _TITUS_DESV,     titus_note)
        all_products += self._build_sds_list('Enviro-Tec',      'CCV',             'CCV',   _ENVIROTEC_CCV,  enviro_note)
        all_products += self._build_sds_list('Johnson Controls','TSS',             'TSS',   _JCI_TSS,        jci_note)
        all_products += self._build_sds_list('Metalaire',       'TH-500',          'TH500', _METALAIRE_TH500, metal_note)

        # ── Single Duct Reheat ────────────────────────────────────────────────
        all_products += self._build_sdr_list('Trane',           'VariTrane VCWF',  'VCWF',  _TRANE_VCWF,
                                             'Trane VCWF hot-water reheat; AHRI 880 certified')
        all_products += self._build_sdr_list('Nailor',          '3100 (31RW)',     'N31RW', _NAILOR_31RW,
                                             'Nailor 31RW hot-water reheat; AHRI 880 certified')
        all_products += self._build_sdr_list('Price Industries','SDVR',            'SDVR',  _PRICE_SDVR,
                                             'Price SDVR hot-water reheat; AHRI 880 certified')
        all_products += self._build_sdr_list('Krueger',         'LMHS-HW',        'LMHS-HW', _KRUEGER_LMHS_HW,
                                             'Krueger LMHS with hot-water coil; AHRI 880 certified')

        # ── Series Fan-Powered ────────────────────────────────────────────────
        sfp_note = ('Series fan-powered; data = combined fan+damper at rated conditions. '
                    'Calibrated to Trane ENL vol.47-4 Table 3. '
                    '63 Hz and 8000 Hz estimated.')
        all_products += self._build_fp_dict('Trane',           'VariTrane SFP', 'SFPT', 'series_fan_powered', _SFP_TRANE,   sfp_note)
        all_products += self._build_fp_dict('Nailor',          '35S/37S Series','N35S', 'series_fan_powered', _SFP_NAILOR,  sfp_note)
        all_products += self._build_fp_dict('Price Industries','SFPV Series',   'SFPV', 'series_fan_powered', _SFP_PRICE,   sfp_note)
        all_products += self._build_fp_dict('Krueger',         'QFC Series',    'QFC',  'series_fan_powered', _SFP_KRUEGER, sfp_note)

        # ── Parallel Fan-Powered ──────────────────────────────────────────────
        pfp_note = ('Parallel fan-powered; data = combined fan+primary at design conditions. '
                    'Calibrated to Trane ENL vol.47-4 Table 3. '
                    'Radiated path is typically dominant for PFP units. '
                    '63 Hz and 8000 Hz estimated.')
        all_products += self._build_fp_dict('Trane',           'VariTrane PFP', 'PFPT', 'parallel_fan_powered', _PFP_TRANE,   pfp_note)
        all_products += self._build_fp_dict('Nailor',          '35N/37N Series','N35N', 'parallel_fan_powered', _PFP_NAILOR,  pfp_note)
        all_products += self._build_fp_dict('Price Industries','PFPV Series',   'PFPV', 'parallel_fan_powered', _PFP_PRICE,   pfp_note)
        all_products += self._build_fp_dict('Krueger',         'QFV Series',    'QFV',  'parallel_fan_powered', _PFP_KRUEGER, pfp_note)

        # ── Dual Duct ─────────────────────────────────────────────────────────
        dd_note = ('Dual-duct VAV; data = combined hot+cold deck dampers at design. '
                   '~1-2 dB higher than single-duct at same size due to dual damper interaction.')
        for (size, dis, rad) in _DD_TRANE:
            all_products.append(dict(
                manufacturer='Trane', product_series='VariTrane DD', model_number=f'DDVT-{size:02d}',
                unit_type='dual_duct',
                inlet_size_in=float(size), outlet_width_in=float(round(size*1.8)), outlet_height_in=float(round(size*0.9)),
                flow_min_cfm=float(_SDS_FLOW[size][0]), flow_max_cfm=float(_SDS_FLOW[size][1]),
                flow_rated_cfm=float(_SDS_FLOW[size][2]),
                inlet_sp_in_wg=1.0,
                discharge_63=dis[0], discharge_125=dis[1], discharge_250=dis[2],
                discharge_500=dis[3], discharge_1000=dis[4], discharge_2000=dis[5],
                discharge_4000=dis[6], discharge_8000=dis[7],
                radiated_63=rad[0], radiated_125=rad[1], radiated_250=rad[2],
                radiated_500=rad[3], radiated_1000=rad[4], radiated_2000=rad[5],
                radiated_4000=rad[6], radiated_8000=rad[7],
                data_source='ahri_certified_catalog', ahri_certified=True, notes=dd_note,
            ))
        for (size, dis, rad) in _DD_PRICE:
            all_products.append(dict(
                manufacturer='Price Industries', product_series='DDVF', model_number=f'DDVF-{size:02d}',
                unit_type='dual_duct',
                inlet_size_in=float(size), outlet_width_in=float(round(size*1.8)), outlet_height_in=float(round(size*0.9)),
                flow_min_cfm=float(_SDS_FLOW[size][0]), flow_max_cfm=float(_SDS_FLOW[size][1]),
                flow_rated_cfm=float(_SDS_FLOW[size][2]),
                inlet_sp_in_wg=1.0,
                discharge_63=dis[0], discharge_125=dis[1], discharge_250=dis[2],
                discharge_500=dis[3], discharge_1000=dis[4], discharge_2000=dis[5],
                discharge_4000=dis[6], discharge_8000=dis[7],
                radiated_63=rad[0], radiated_125=rad[1], radiated_250=rad[2],
                radiated_500=rad[3], radiated_1000=rad[4], radiated_2000=rad[5],
                radiated_4000=rad[6], radiated_8000=rad[7],
                data_source='ahri_certified_catalog', ahri_certified=True, notes=dd_note,
            ))

        # ── Insert all ────────────────────────────────────────────────────────
        for p in all_products:
            self.session.add(VAVTerminalUnit(**p))

        try:
            self.session.commit()
            print(f"Successfully added {len(all_products)} VAV terminal unit products to database.")
        except Exception as e:
            self.session.rollback()
            raise RuntimeError(f"Database commit failed: {e}") from e

    # ── Queries ───────────────────────────────────────────────────────────────

    def get_products(
        self,
        unit_type: Optional[str] = None,
        min_size: Optional[float] = None,
        max_size: Optional[float] = None,
        manufacturer: Optional[str] = None,
        max_flow_cfm: Optional[float] = None,
    ) -> list:
        """Filter products by any combination of criteria."""
        q = self.session.query(VAVTerminalUnit)
        if unit_type:
            q = q.filter(VAVTerminalUnit.unit_type == unit_type)
        if min_size is not None:
            q = q.filter(VAVTerminalUnit.inlet_size_in >= min_size)
        if max_size is not None:
            q = q.filter(VAVTerminalUnit.inlet_size_in <= max_size)
        if manufacturer:
            q = q.filter(VAVTerminalUnit.manufacturer.ilike(f'%{manufacturer}%'))
        if max_flow_cfm is not None:
            q = q.filter(VAVTerminalUnit.flow_max_cfm <= max_flow_cfm)
        return q.all()

    def get_by_model(self, model_number: str) -> Optional[object]:
        """Exact model number lookup."""
        return self.session.query(VAVTerminalUnit).filter(
            VAVTerminalUnit.model_number == model_number
        ).first()

    # ── 1/3 Octave Conversion ─────────────────────────────────────────────────

    def get_third_octave(
        self,
        product: object,
        path: str = 'discharge',
        spectral_slope: float = 0.5,
    ) -> Dict[int, float]:
        """
        Return estimated 1/3-octave sound power levels for a product.

        Parameters
        ----------
        product : VAVTerminalUnit
        path    : 'discharge', 'radiated', or 'plenum'
        spectral_slope : dB/octave tilt within each octave band.
            Default 0.5 dB/octave produces a slight pink tilt
            (lower sub-band ≈ +0.17 dB, upper ≈ −0.17 dB).

        Returns
        -------
        dict  {frequency_hz: level_dB}  for the 22 bands in THIRD_OCTAVE_FREQS
        """
        if path == 'discharge':
            oct_levels = product.discharge_octave_bands
        elif path == 'radiated':
            oct_levels = product.radiated_octave_bands
        elif path == 'plenum':
            oct_levels = product.plenum_octave_bands
        else:
            raise ValueError(f"path must be 'discharge', 'radiated', or 'plenum'; got '{path}'")

        third = octave_to_third_octave(oct_levels, spectral_slope_db_per_octave=spectral_slope)
        return dict(zip(THIRD_OCTAVE_FREQS, third))

    def get_third_octave_list(
        self,
        product: object,
        path: str = 'discharge',
    ) -> List[float]:
        """Return 1/3-octave levels as a plain list (index matches THIRD_OCTAVE_FREQS)."""
        return list(self.get_third_octave(product, path).values())

    # ── NC Estimation (AHRI 885-2008 Appendix E) ─────────────────────────────

    def calculate_nc(
        self,
        product: object,
        path: str = 'discharge',
        ceiling_type: str = 'mineral_fiber',
    ) -> Tuple[int, List[float]]:
        """
        Estimate NC rating using AHRI Standard 885-2008 Appendix E attenuation.

        Parameters
        ----------
        product      : VAVTerminalUnit
        path         : 'discharge' or 'radiated'
        ceiling_type : 'mineral_fiber' (default), 'glass_fiber', 'gypsum'

        Returns
        -------
        (nc_value, space_spl_list)
            nc_value       : estimated NC rating
            space_spl_list : list of 6 Lp values [125,250,500,1000,2000,4000] Hz
        """
        # Get Lw for bands 125–4000 Hz (bands 2–7)
        if path == 'discharge':
            lw = [
                product.discharge_125, product.discharge_250, product.discharge_500,
                product.discharge_1000, product.discharge_2000, product.discharge_4000,
            ]
            flow = product.flow_rated_cfm or 500
            if flow < 300:
                attn = self._DIS_ATTN['small']
            elif flow <= 700:
                attn = self._DIS_ATTN['medium']
            else:
                attn = self._DIS_ATTN['large']
        else:
            lw = [
                product.radiated_125, product.radiated_250, product.radiated_500,
                product.radiated_1000, product.radiated_2000, product.radiated_4000,
            ]
            attn = self._RAD_ATTN_MINERAL_FIBER   # only mineral fiber option supported

        spl = [max(0.0, lw_i - a_i) for lw_i, a_i in zip(lw, attn)]
        nc = nc_from_octave_levels(spl)
        return nc, spl

    def close(self):
        self.session.close()


# ─────────────────────────────────────────────────────────────────────────────
# Standalone utility — no database required
# ─────────────────────────────────────────────────────────────────────────────

def third_octave_from_octave_dict(
    octave_dict: Dict[int, float],
    spectral_slope: float = 0.0,
) -> Dict[int, float]:
    """
    Convenience wrapper: convert {freq_hz: Lw_dB} octave-band dict
    (keys must be a subset of [63,125,250,500,1000,2000,4000,8000])
    to a 22-band 1/3-octave dict.
    """
    levels = [octave_dict.get(f) for f in OCTAVE_FREQS]
    third = octave_to_third_octave(levels, spectral_slope)
    return {f: v for f, v in zip(THIRD_OCTAVE_FREQS, third)}


def format_third_octave_table(levels: Dict[int, float], label: str = '') -> str:
    """Pretty-print a 1/3-octave table for console output or logging."""
    header = f"{'Hz':>6}  {'Lw (dB)':>8}"
    sep    = '-' * 18
    rows   = [f"{f:>6}  {v:>8.1f}" for f, v in sorted(levels.items())]
    title  = f"\n=== 1/3-Octave Sound Power Levels {label} ===\n"
    return title + header + '\n' + sep + '\n' + '\n'.join(rows)


# ─────────────────────────────────────────────────────────────────────────────
# Quick self-test (run module directly)
# ─────────────────────────────────────────────────────────────────────────────

if __name__ == '__main__':
    import sys

    print("VAV Database — standalone utility test (no DB connection required)\n")

    # Test 1/3-octave conversion with Trane VCCF 12" anchor values
    anchor_octave = {
        63: 66, 125: 68, 250: 60, 500: 55, 1000: 52, 2000: 48, 4000: 44, 8000: 34
    }
    third_oct = third_octave_from_octave_dict(anchor_octave, spectral_slope=0.5)
    print(format_third_octave_table(third_oct, 'Trane VCCF 12" Discharge (estimated 1/3-oct)'))

    # Verify energy conservation: sum of 1/3-oct powers should ≈ octave total
    for oct_freq, oct_lw in anchor_octave.items():
        if oct_freq in [63, 8000]:
            continue   # estimated bands
        sub_freqs = {
            125: [100, 125, 160], 250: [200, 250, 315], 500: [400, 500, 630],
            1000: [800, 1000, 1250], 2000: [1600, 2000, 2500], 4000: [3150, 4000, 5000],
        }[oct_freq]
        sub_lws   = [third_oct[f] for f in sub_freqs]
        combined  = log_add(*sub_lws)
        delta     = abs(combined - oct_lw)
        status    = 'OK' if delta < 0.1 else f'WARN Δ={delta:.2f}'
        print(f"  {oct_freq:5d} Hz: octave={oct_lw:5.1f}, 1/3-oct sum={combined:5.1f} dB  [{status}]")

    print('\nProduct count by type (raw data tables):')
    totals = {
        'single_duct_shutoff':   (len(_TRANE_VCCF)+len(_NAILOR_3000)+len(_PRICE_SDV)+
                                   len(_KRUEGER_LMHS)+len(_TITUS_DESV)+len(_ENVIROTEC_CCV)+
                                   len(_JCI_TSS)+len(_METALAIRE_TH500)),
        'single_duct_reheat':    (len(_TRANE_VCWF)+len(_NAILOR_31RW)+
                                   len(_PRICE_SDVR)+len(_KRUEGER_LMHS_HW)),
        'series_fan_powered':    (len(_SFP_TRANE)+len(_SFP_NAILOR)+
                                   len(_SFP_PRICE)+len(_SFP_KRUEGER)),
        'parallel_fan_powered':  (len(_PFP_TRANE)+len(_PFP_NAILOR)+
                                   len(_PFP_PRICE)+len(_PFP_KRUEGER)),
        'dual_duct':             (len(_DD_TRANE)+len(_DD_PRICE)),
    }
    grand = 0
    for k, v in totals.items():
        print(f"  {k:<25s}: {v:3d} entries")
        grand += v
    print(f"  {'TOTAL':<25s}: {grand:3d} entries")
