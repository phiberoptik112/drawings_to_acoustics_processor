"""
silencer_library.py
===================
Manufacturer silencer product catalog — insertion loss (IL) data in dB across
7 octave bands: 63, 125, 250, 500, 1000, 2000, 4000, 8000 Hz.

All IL values are Dynamic Insertion Loss (DIL) tested per ASTM E477 unless
noted as static (0 fpm / 0 m/s). Pressure drop (PD) is listed at the
rated test velocity.

Sources
-------
  - Vibro-Acoustics  : RD-HV.pdf, RD.pdf, RED-REFL-RENM.pdf,
                       Noise-Control-Catalog_WEB.pdf
                       (noisecontrol.vibro-acoustics.com)
  - Price Industries : rl_rm_rh_pd.pdf, pclpcmpch--circular-silencer-packless-catalog.pdf
                       (priceindustries.com)
  - IAC Acoustics    : IAC-HVAC-Duct-Silencers.pdf, UK-P2-DUC-0123 Duct Silencer Catalogue
                       (iac-australia.com.au, iacacoustics.global, iac-nordic.dk)
  - Ruskin           : SoundChek Model A / AM catalog

Notes on interpretation
-----------------------
  velocity_class  Short label for the silencer's design velocity range:
                    "ULV" = Ultra Low Velocity  (≤500 fpm / ≤2.5 m/s)
                    "LV"  = Low Velocity         (≤750 fpm)
                    "MV"  = Medium Velocity       (≤1250–1750 fpm)
                    "HV"  = High Velocity         (≤2000–2500 fpm)
                    "S","LFS","ES","LFM","L","MS","ML","LFL" = IAC type codes

  rated_velocity_fpm  Velocity at which the published IL was measured.
                      0 means static (no-flow) test.

  pressure_drop_in_wg  At rated_velocity_fpm. None = not published.

  silencer_type   "rectangular" | "elbow" | "circular_packless"

  length_in       Nominal silencer body length in inches.
                  IAC metric lengths converted: 900mm≈35", 1500mm≈59", 2100mm≈83", 3000mm≈118"

  self_noise_lw_1k  Sound power level (dB re 10⁻¹² W) at 1000 Hz octave band,
                    at rated velocity, at manufacturer's reference face area.
                    None = not published.

Usage
-----
  from data.silencer_library import get_silencer_catalog
  entries = get_silencer_catalog()   # list of dicts → seed SilencerCatalog table
"""

# ---------------------------------------------------------------------------
# VIBRO-ACOUSTICS  —  RD-HV series
# Rectangular Dissipative, High Velocity (≤2000 fpm)
# F1–F9 = frequency class (F1 peaks at low freq, F9 peaks at high freq)
# IL at +2000 fpm forward flow  |  PD at 2000 fpm
# Source: RD-HV.pdf
# ---------------------------------------------------------------------------
_VA_RD_HV = [
    # F1 — peak attenuation at 1000 Hz, low-frequency emphasis
    dict(manufacturer="Vibro-Acoustics", series="RD-HV", model="RD-HV-F1",
         silencer_type="rectangular", length_in=36, velocity_class="HV",
         max_velocity_fpm=2000, rated_velocity_fpm=2000,
         il_63=2,  il_125=5,  il_250=9,  il_500=11,
         il_1000=13, il_2000=11, il_4000=10, il_8000=8,
         pressure_drop_in_wg=0.16, self_noise_lw_1k=None,
         source_document="RD-HV.pdf", notes="F1: low-freq emphasis, wide splitter"),
    dict(manufacturer="Vibro-Acoustics", series="RD-HV", model="RD-HV-F1",
         silencer_type="rectangular", length_in=60, velocity_class="HV",
         max_velocity_fpm=2000, rated_velocity_fpm=2000,
         il_63=4,  il_125=8,  il_250=14, il_500=17,
         il_1000=19, il_2000=15, il_4000=13, il_8000=10,
         pressure_drop_in_wg=0.22, self_noise_lw_1k=None,
         source_document="RD-HV.pdf", notes="F1: low-freq emphasis, wide splitter"),
    dict(manufacturer="Vibro-Acoustics", series="RD-HV", model="RD-HV-F1",
         silencer_type="rectangular", length_in=84, velocity_class="HV",
         max_velocity_fpm=2000, rated_velocity_fpm=2000,
         il_63=5,  il_125=11, il_250=20, il_500=23,
         il_1000=25, il_2000=18, il_4000=16, il_8000=13,
         pressure_drop_in_wg=0.28, self_noise_lw_1k=None,
         source_document="RD-HV.pdf", notes="F1: low-freq emphasis, wide splitter"),
    dict(manufacturer="Vibro-Acoustics", series="RD-HV", model="RD-HV-F1",
         silencer_type="rectangular", length_in=108, velocity_class="HV",
         max_velocity_fpm=2000, rated_velocity_fpm=2000,
         il_63=7,  il_125=14, il_250=25, il_500=29,
         il_1000=30, il_2000=21, il_4000=18, il_8000=15,
         pressure_drop_in_wg=0.34, self_noise_lw_1k=None,
         source_document="RD-HV.pdf", notes="F1: low-freq emphasis, wide splitter"),

    # F2
    dict(manufacturer="Vibro-Acoustics", series="RD-HV", model="RD-HV-F2",
         silencer_type="rectangular", length_in=36, velocity_class="HV",
         max_velocity_fpm=2000, rated_velocity_fpm=2000,
         il_63=2,  il_125=5,  il_250=9,  il_500=12,
         il_1000=13, il_2000=11, il_4000=10, il_8000=7,
         pressure_drop_in_wg=0.16, self_noise_lw_1k=None,
         source_document="RD-HV.pdf", notes=None),
    dict(manufacturer="Vibro-Acoustics", series="RD-HV", model="RD-HV-F2",
         silencer_type="rectangular", length_in=60, velocity_class="HV",
         max_velocity_fpm=2000, rated_velocity_fpm=2000,
         il_63=3,  il_125=7,  il_250=14, il_500=19,
         il_1000=19, il_2000=15, il_4000=13, il_8000=10,
         pressure_drop_in_wg=0.21, self_noise_lw_1k=None,
         source_document="RD-HV.pdf", notes=None),
    dict(manufacturer="Vibro-Acoustics", series="RD-HV", model="RD-HV-F2",
         silencer_type="rectangular", length_in=84, velocity_class="HV",
         max_velocity_fpm=2000, rated_velocity_fpm=2000,
         il_63=5,  il_125=10, il_250=19, il_500=26,
         il_1000=27, il_2000=20, il_4000=15, il_8000=12,
         pressure_drop_in_wg=0.28, self_noise_lw_1k=None,
         source_document="RD-HV.pdf", notes=None),
    dict(manufacturer="Vibro-Acoustics", series="RD-HV", model="RD-HV-F2",
         silencer_type="rectangular", length_in=108, velocity_class="HV",
         max_velocity_fpm=2000, rated_velocity_fpm=2000,
         il_63=6,  il_125=13, il_250=25, il_500=32,
         il_1000=34, il_2000=23, il_4000=17, il_8000=14,
         pressure_drop_in_wg=0.32, self_noise_lw_1k=None,
         source_document="RD-HV.pdf", notes=None),

    # F3
    dict(manufacturer="Vibro-Acoustics", series="RD-HV", model="RD-HV-F3",
         silencer_type="rectangular", length_in=36, velocity_class="HV",
         max_velocity_fpm=2000, rated_velocity_fpm=2000,
         il_63=3,  il_125=5,  il_250=8,  il_500=13,
         il_1000=14, il_2000=11, il_4000=9,  il_8000=6,
         pressure_drop_in_wg=0.16, self_noise_lw_1k=None,
         source_document="RD-HV.pdf", notes=None),
    dict(manufacturer="Vibro-Acoustics", series="RD-HV", model="RD-HV-F3",
         silencer_type="rectangular", length_in=60, velocity_class="HV",
         max_velocity_fpm=2000, rated_velocity_fpm=2000,
         il_63=3,  il_125=6,  il_250=13, il_500=22,
         il_1000=20, il_2000=16, il_4000=12, il_8000=9,
         pressure_drop_in_wg=0.21, self_noise_lw_1k=None,
         source_document="RD-HV.pdf", notes=None),
    dict(manufacturer="Vibro-Acoustics", series="RD-HV", model="RD-HV-F3",
         silencer_type="rectangular", length_in=84, velocity_class="HV",
         max_velocity_fpm=2000, rated_velocity_fpm=2000,
         il_63=6,  il_125=10, il_250=19, il_500=28,
         il_1000=29, il_2000=22, il_4000=15, il_8000=11,
         pressure_drop_in_wg=0.28, self_noise_lw_1k=None,
         source_document="RD-HV.pdf", notes=None),
    dict(manufacturer="Vibro-Acoustics", series="RD-HV", model="RD-HV-F3",
         silencer_type="rectangular", length_in=108, velocity_class="HV",
         max_velocity_fpm=2000, rated_velocity_fpm=2000,
         il_63=5,  il_125=13, il_250=24, il_500=36,
         il_1000=37, il_2000=25, il_4000=16, il_8000=13,
         pressure_drop_in_wg=0.30, self_noise_lw_1k=None,
         source_document="RD-HV.pdf", notes=None),

    # F4
    dict(manufacturer="Vibro-Acoustics", series="RD-HV", model="RD-HV-F4",
         silencer_type="rectangular", length_in=36, velocity_class="HV",
         max_velocity_fpm=2000, rated_velocity_fpm=2000,
         il_63=3,  il_125=5,  il_250=8,  il_500=14,
         il_1000=14, il_2000=11, il_4000=8,  il_8000=5,
         pressure_drop_in_wg=0.16, self_noise_lw_1k=None,
         source_document="RD-HV.pdf", notes=None),
    dict(manufacturer="Vibro-Acoustics", series="RD-HV", model="RD-HV-F4",
         silencer_type="rectangular", length_in=60, velocity_class="HV",
         max_velocity_fpm=2000, rated_velocity_fpm=2000,
         il_63=3,  il_125=6,  il_250=12, il_500=25,
         il_1000=21, il_2000=17, il_4000=12, il_8000=8,
         pressure_drop_in_wg=0.20, self_noise_lw_1k=None,
         source_document="RD-HV.pdf", notes=None),
    dict(manufacturer="Vibro-Acoustics", series="RD-HV", model="RD-HV-F4",
         silencer_type="rectangular", length_in=84, velocity_class="HV",
         max_velocity_fpm=2000, rated_velocity_fpm=2000,
         il_63=6,  il_125=10, il_250=18, il_500=31,
         il_1000=32, il_2000=23, il_4000=15, il_8000=10,
         pressure_drop_in_wg=0.28, self_noise_lw_1k=None,
         source_document="RD-HV.pdf", notes=None),
    dict(manufacturer="Vibro-Acoustics", series="RD-HV", model="RD-HV-F4",
         silencer_type="rectangular", length_in=108, velocity_class="HV",
         max_velocity_fpm=2000, rated_velocity_fpm=2000,
         il_63=4,  il_125=13, il_250=24, il_500=39,
         il_1000=40, il_2000=26, il_4000=15, il_8000=12,
         pressure_drop_in_wg=0.28, self_noise_lw_1k=None,
         source_document="RD-HV.pdf", notes=None),

    # F5
    dict(manufacturer="Vibro-Acoustics", series="RD-HV", model="RD-HV-F5",
         silencer_type="rectangular", length_in=36, velocity_class="HV",
         max_velocity_fpm=2000, rated_velocity_fpm=2000,
         il_63=3,  il_125=5,  il_250=8,  il_500=14,
         il_1000=16, il_2000=13, il_4000=9,  il_8000=6,
         pressure_drop_in_wg=0.16, self_noise_lw_1k=None,
         source_document="RD-HV.pdf", notes=None),
    dict(manufacturer="Vibro-Acoustics", series="RD-HV", model="RD-HV-F5",
         silencer_type="rectangular", length_in=60, velocity_class="HV",
         max_velocity_fpm=2000, rated_velocity_fpm=2000,
         il_63=3,  il_125=6,  il_250=11, il_500=23,
         il_1000=24, il_2000=19, il_4000=13, il_8000=9,
         pressure_drop_in_wg=0.21, self_noise_lw_1k=None,
         source_document="RD-HV.pdf", notes=None),
    dict(manufacturer="Vibro-Acoustics", series="RD-HV", model="RD-HV-F5",
         silencer_type="rectangular", length_in=84, velocity_class="HV",
         max_velocity_fpm=2000, rated_velocity_fpm=2000,
         il_63=6,  il_125=10, il_250=18, il_500=31,
         il_1000=36, il_2000=28, il_4000=18, il_8000=11,
         pressure_drop_in_wg=0.31, self_noise_lw_1k=None,
         source_document="RD-HV.pdf", notes=None),
    dict(manufacturer="Vibro-Acoustics", series="RD-HV", model="RD-HV-F5",
         silencer_type="rectangular", length_in=108, velocity_class="HV",
         max_velocity_fpm=2000, rated_velocity_fpm=2000,
         il_63=4,  il_125=13, il_250=22, il_500=38,
         il_1000=43, il_2000=31, il_4000=18, il_8000=13,
         pressure_drop_in_wg=0.29, self_noise_lw_1k=None,
         source_document="RD-HV.pdf", notes=None),

    # F6 — balanced mid-to-high frequency peak
    dict(manufacturer="Vibro-Acoustics", series="RD-HV", model="RD-HV-F6",
         silencer_type="rectangular", length_in=36, velocity_class="HV",
         max_velocity_fpm=2000, rated_velocity_fpm=2000,
         il_63=3,  il_125=4,  il_250=7,  il_500=13,
         il_1000=18, il_2000=14, il_4000=10, il_8000=6,
         pressure_drop_in_wg=0.16, self_noise_lw_1k=None,
         source_document="RD-HV.pdf", notes=None),
    dict(manufacturer="Vibro-Acoustics", series="RD-HV", model="RD-HV-F6",
         silencer_type="rectangular", length_in=60, velocity_class="HV",
         max_velocity_fpm=2000, rated_velocity_fpm=2000,
         il_63=3,  il_125=5,  il_250=11, il_500=22,
         il_1000=27, il_2000=21, il_4000=15, il_8000=10,
         pressure_drop_in_wg=0.21, self_noise_lw_1k=None,
         source_document="RD-HV.pdf", notes=None),
    dict(manufacturer="Vibro-Acoustics", series="RD-HV", model="RD-HV-F6",
         silencer_type="rectangular", length_in=84, velocity_class="HV",
         max_velocity_fpm=2000, rated_velocity_fpm=2000,
         il_63=6,  il_125=10, il_250=17, il_500=31,
         il_1000=41, il_2000=33, il_4000=21, il_8000=13,
         pressure_drop_in_wg=0.33, self_noise_lw_1k=None,
         source_document="RD-HV.pdf", notes=None),
    dict(manufacturer="Vibro-Acoustics", series="RD-HV", model="RD-HV-F6",
         silencer_type="rectangular", length_in=108, velocity_class="HV",
         max_velocity_fpm=2000, rated_velocity_fpm=2000,
         il_63=4,  il_125=12, il_250=21, il_500=37,
         il_1000=47, il_2000=36, il_4000=21, il_8000=15,
         pressure_drop_in_wg=0.31, self_noise_lw_1k=None,
         source_document="RD-HV.pdf", notes=None),

    # F7
    dict(manufacturer="Vibro-Acoustics", series="RD-HV", model="RD-HV-F7",
         silencer_type="rectangular", length_in=36, velocity_class="HV",
         max_velocity_fpm=2000, rated_velocity_fpm=2000,
         il_63=3,  il_125=4,  il_250=9,  il_500=16,
         il_1000=19, il_2000=15, il_4000=11, il_8000=7,
         pressure_drop_in_wg=0.16, self_noise_lw_1k=None,
         source_document="RD-HV.pdf", notes=None),
    dict(manufacturer="Vibro-Acoustics", series="RD-HV", model="RD-HV-F7",
         silencer_type="rectangular", length_in=60, velocity_class="HV",
         max_velocity_fpm=2000, rated_velocity_fpm=2000,
         il_63=3,  il_125=5,  il_250=13, il_500=26,
         il_1000=29, il_2000=23, il_4000=16, il_8000=11,
         pressure_drop_in_wg=0.22, self_noise_lw_1k=None,
         source_document="RD-HV.pdf", notes=None),
    dict(manufacturer="Vibro-Acoustics", series="RD-HV", model="RD-HV-F7",
         silencer_type="rectangular", length_in=84, velocity_class="HV",
         max_velocity_fpm=2000, rated_velocity_fpm=2000,
         il_63=6,  il_125=8,  il_250=21, il_500=38,
         il_1000=43, il_2000=36, il_4000=23, il_8000=15,
         pressure_drop_in_wg=0.36, self_noise_lw_1k=None,
         source_document="RD-HV.pdf", notes=None),
    dict(manufacturer="Vibro-Acoustics", series="RD-HV", model="RD-HV-F7",
         silencer_type="rectangular", length_in=108, velocity_class="HV",
         max_velocity_fpm=2000, rated_velocity_fpm=2000,
         il_63=4,  il_125=11, il_250=25, il_500=44,
         il_1000=48, il_2000=39, il_4000=24, il_8000=16,
         pressure_drop_in_wg=0.32, self_noise_lw_1k=None,
         source_document="RD-HV.pdf", notes=None),

    # F8 — high-frequency emphasis
    dict(manufacturer="Vibro-Acoustics", series="RD-HV", model="RD-HV-F8",
         silencer_type="rectangular", length_in=36, velocity_class="HV",
         max_velocity_fpm=2000, rated_velocity_fpm=2000,
         il_63=2,  il_125=3,  il_250=7,  il_500=14,
         il_1000=19, il_2000=16, il_4000=14, il_8000=11,
         pressure_drop_in_wg=0.18, self_noise_lw_1k=None,
         source_document="RD-HV.pdf", notes="F8: high-freq emphasis, narrow splitter"),
    dict(manufacturer="Vibro-Acoustics", series="RD-HV", model="RD-HV-F8",
         silencer_type="rectangular", length_in=60, velocity_class="HV",
         max_velocity_fpm=2000, rated_velocity_fpm=2000,
         il_63=4,  il_125=5,  il_250=13, il_500=24,
         il_1000=32, il_2000=24, il_4000=18, il_8000=14,
         pressure_drop_in_wg=0.27, self_noise_lw_1k=None,
         source_document="RD-HV.pdf", notes="F8: high-freq emphasis, narrow splitter"),
    dict(manufacturer="Vibro-Acoustics", series="RD-HV", model="RD-HV-F8",
         silencer_type="rectangular", length_in=84, velocity_class="HV",
         max_velocity_fpm=2000, rated_velocity_fpm=2000,
         il_63=6,  il_125=7,  il_250=18, il_500=35,
         il_1000=44, il_2000=33, il_4000=23, il_8000=17,
         pressure_drop_in_wg=0.36, self_noise_lw_1k=None,
         source_document="RD-HV.pdf", notes="F8: high-freq emphasis, narrow splitter"),
    dict(manufacturer="Vibro-Acoustics", series="RD-HV", model="RD-HV-F8",
         silencer_type="rectangular", length_in=108, velocity_class="HV",
         max_velocity_fpm=2000, rated_velocity_fpm=2000,
         il_63=8,  il_125=9,  il_250=24, il_500=45,
         il_1000=55, il_2000=42, il_4000=27, il_8000=21,
         pressure_drop_in_wg=0.45, self_noise_lw_1k=None,
         source_document="RD-HV.pdf", notes="F8: high-freq emphasis, narrow splitter"),

    # F9 — maximum high-frequency attenuation
    dict(manufacturer="Vibro-Acoustics", series="RD-HV", model="RD-HV-F9",
         silencer_type="rectangular", length_in=36, velocity_class="HV",
         max_velocity_fpm=2000, rated_velocity_fpm=2000,
         il_63=3,  il_125=3,  il_250=7,  il_500=14,
         il_1000=25, il_2000=19, il_4000=14, il_8000=8,
         pressure_drop_in_wg=0.16, self_noise_lw_1k=None,
         source_document="RD-HV.pdf", notes="F9: maximum HF, narrowest splitter"),
    dict(manufacturer="Vibro-Acoustics", series="RD-HV", model="RD-HV-F9",
         silencer_type="rectangular", length_in=60, velocity_class="HV",
         max_velocity_fpm=2000, rated_velocity_fpm=2000,
         il_63=4,  il_125=5,  il_250=10, il_500=22,
         il_1000=38, il_2000=29, il_4000=19, il_8000=13,
         pressure_drop_in_wg=0.24, self_noise_lw_1k=None,
         source_document="RD-HV.pdf", notes="F9: maximum HF, narrowest splitter"),
    dict(manufacturer="Vibro-Acoustics", series="RD-HV", model="RD-HV-F9",
         silencer_type="rectangular", length_in=84, velocity_class="HV",
         max_velocity_fpm=2000, rated_velocity_fpm=2000,
         il_63=6,  il_125=8,  il_250=19, il_500=39,
         il_1000=55, il_2000=49, il_4000=32, il_8000=20,
         pressure_drop_in_wg=0.44, self_noise_lw_1k=None,
         source_document="RD-HV.pdf", notes="F9: maximum HF, narrowest splitter"),
    dict(manufacturer="Vibro-Acoustics", series="RD-HV", model="RD-HV-F9",
         silencer_type="rectangular", length_in=108, velocity_class="HV",
         max_velocity_fpm=2000, rated_velocity_fpm=2000,
         il_63=4,  il_125=10, il_250=19, il_500=41,
         il_1000=55, il_2000=52, il_4000=32, il_8000=21,
         pressure_drop_in_wg=0.36, self_noise_lw_1k=None,
         source_document="RD-HV.pdf", notes="F9: maximum HF, narrowest splitter"),
]

# ---------------------------------------------------------------------------
# VIBRO-ACOUSTICS  —  RD-ULV series
# Rectangular Dissipative, Ultra-Low Velocity (≤500 fpm)
# IL at +500 fpm forward flow  |  PD at 500 fpm
# Source: RD.pdf
# Note: self-noise at 500 fpm, 5 ft² face area:
#   55/39/31/29/33/31/25/30 dB (63→8k Hz)
# ---------------------------------------------------------------------------
_VA_RD_ULV = [
    # F1
    dict(manufacturer="Vibro-Acoustics", series="RD-ULV", model="RD-ULV-F1",
         silencer_type="rectangular", length_in=36, velocity_class="ULV",
         max_velocity_fpm=500, rated_velocity_fpm=500,
         il_63=7,  il_125=14, il_250=19, il_500=18,
         il_1000=25, il_2000=23, il_4000=18, il_8000=16,
         pressure_drop_in_wg=0.12, self_noise_lw_1k=33,
         source_document="RD.pdf", notes="Self-noise ref: 5 ft² face"),
    dict(manufacturer="Vibro-Acoustics", series="RD-ULV", model="RD-ULV-F1",
         silencer_type="rectangular", length_in=60, velocity_class="ULV",
         max_velocity_fpm=500, rated_velocity_fpm=500,
         il_63=9,  il_125=18, il_250=28, il_500=28,
         il_1000=38, il_2000=30, il_4000=24, il_8000=20,
         pressure_drop_in_wg=0.16, self_noise_lw_1k=33,
         source_document="RD.pdf", notes="Self-noise ref: 5 ft² face"),
    dict(manufacturer="Vibro-Acoustics", series="RD-ULV", model="RD-ULV-F1",
         silencer_type="rectangular", length_in=84, velocity_class="ULV",
         max_velocity_fpm=500, rated_velocity_fpm=500,
         il_63=11, il_125=21, il_250=37, il_500=38,
         il_1000=50, il_2000=38, il_4000=30, il_8000=24,
         pressure_drop_in_wg=0.20, self_noise_lw_1k=33,
         source_document="RD.pdf", notes="Self-noise ref: 5 ft² face"),
    dict(manufacturer="Vibro-Acoustics", series="RD-ULV", model="RD-ULV-F1",
         silencer_type="rectangular", length_in=108, velocity_class="ULV",
         max_velocity_fpm=500, rated_velocity_fpm=500,
         il_63=13, il_125=24, il_250=46, il_500=46,
         il_1000=55, il_2000=46, il_4000=36, il_8000=28,
         pressure_drop_in_wg=0.24, self_noise_lw_1k=33,
         source_document="RD.pdf", notes="Self-noise ref: 5 ft² face"),

    # F2
    dict(manufacturer="Vibro-Acoustics", series="RD-ULV", model="RD-ULV-F2",
         silencer_type="rectangular", length_in=36, velocity_class="ULV",
         max_velocity_fpm=500, rated_velocity_fpm=500,
         il_63=7,  il_125=13, il_250=19, il_500=19,
         il_1000=26, il_2000=23, il_4000=18, il_8000=15,
         pressure_drop_in_wg=0.12, self_noise_lw_1k=33,
         source_document="RD.pdf", notes=None),
    dict(manufacturer="Vibro-Acoustics", series="RD-ULV", model="RD-ULV-F2",
         silencer_type="rectangular", length_in=60, velocity_class="ULV",
         max_velocity_fpm=500, rated_velocity_fpm=500,
         il_63=9,  il_125=16, il_250=27, il_500=31,
         il_1000=41, il_2000=33, il_4000=24, il_8000=19,
         pressure_drop_in_wg=0.16, self_noise_lw_1k=33,
         source_document="RD.pdf", notes=None),
    dict(manufacturer="Vibro-Acoustics", series="RD-ULV", model="RD-ULV-F2",
         silencer_type="rectangular", length_in=84, velocity_class="ULV",
         max_velocity_fpm=500, rated_velocity_fpm=500,
         il_63=12, il_125=21, il_250=36, il_500=41,
         il_1000=53, il_2000=43, il_4000=31, il_8000=23,
         pressure_drop_in_wg=0.20, self_noise_lw_1k=33,
         source_document="RD.pdf", notes=None),
    dict(manufacturer="Vibro-Acoustics", series="RD-ULV", model="RD-ULV-F2",
         silencer_type="rectangular", length_in=108, velocity_class="ULV",
         max_velocity_fpm=500, rated_velocity_fpm=500,
         il_63=13, il_125=24, il_250=44, il_500=46,
         il_1000=55, il_2000=51, il_4000=37, il_8000=27,
         pressure_drop_in_wg=0.24, self_noise_lw_1k=33,
         source_document="RD.pdf", notes=None),

    # F3 — 108" only published
    dict(manufacturer="Vibro-Acoustics", series="RD-ULV", model="RD-ULV-F3",
         silencer_type="rectangular", length_in=108, velocity_class="ULV",
         max_velocity_fpm=500, rated_velocity_fpm=500,
         il_63=13, il_125=23, il_250=43, il_500=46,
         il_1000=55, il_2000=55, il_4000=37, il_8000=26,
         pressure_drop_in_wg=0.24, self_noise_lw_1k=33,
         source_document="RD.pdf", notes="108\" only published for F3"),

    # F4 — 108" only published
    dict(manufacturer="Vibro-Acoustics", series="RD-ULV", model="RD-ULV-F4",
         silencer_type="rectangular", length_in=108, velocity_class="ULV",
         max_velocity_fpm=500, rated_velocity_fpm=500,
         il_63=13, il_125=22, il_250=41, il_500=46,
         il_1000=55, il_2000=55, il_4000=38, il_8000=24,
         pressure_drop_in_wg=0.24, self_noise_lw_1k=33,
         source_document="RD.pdf", notes="108\" only published for F4"),

    # F5 — 108" only published
    dict(manufacturer="Vibro-Acoustics", series="RD-ULV", model="RD-ULV-F5",
         silencer_type="rectangular", length_in=108, velocity_class="ULV",
         max_velocity_fpm=500, rated_velocity_fpm=500,
         il_63=13, il_125=23, il_250=40, il_500=46,
         il_1000=55, il_2000=55, il_4000=42, il_8000=27,
         pressure_drop_in_wg=0.24, self_noise_lw_1k=33,
         source_document="RD.pdf", notes="108\" only published for F5"),
]

# ---------------------------------------------------------------------------
# VIBRO-ACOUSTICS  —  RFMB-MV series
# Rectangular Film MoldBlock, Medium Velocity (≤1250 fpm)
# IL at +1250 fpm forward flow  |  F2 variant
# Source: Noise-Control-Catalog_WEB.pdf
# ---------------------------------------------------------------------------
_VA_RFMB = [
    dict(manufacturer="Vibro-Acoustics", series="RFMB-MV", model="RFMB-MV-F2",
         silencer_type="rectangular", length_in=36, velocity_class="MV",
         max_velocity_fpm=1250, rated_velocity_fpm=1250,
         il_63=3,  il_125=5,  il_250=12, il_500=16,
         il_1000=16, il_2000=16, il_4000=13, il_8000=8,
         pressure_drop_in_wg=None, self_noise_lw_1k=None,
         source_document="Noise-Control-Catalog_WEB.pdf",
         notes="Film-lined media; moisture-resistant"),
    dict(manufacturer="Vibro-Acoustics", series="RFMB-MV", model="RFMB-MV-F2",
         silencer_type="rectangular", length_in=60, velocity_class="MV",
         max_velocity_fpm=1250, rated_velocity_fpm=1250,
         il_63=6,  il_125=8,  il_250=17, il_500=20,
         il_1000=24, il_2000=26, il_4000=16, il_8000=9,
         pressure_drop_in_wg=None, self_noise_lw_1k=None,
         source_document="Noise-Control-Catalog_WEB.pdf",
         notes="Film-lined media; moisture-resistant"),
    dict(manufacturer="Vibro-Acoustics", series="RFMB-MV", model="RFMB-MV-F2",
         silencer_type="rectangular", length_in=84, velocity_class="MV",
         max_velocity_fpm=1250, rated_velocity_fpm=1250,
         il_63=8,  il_125=10, il_250=22, il_500=24,
         il_1000=32, il_2000=36, il_4000=19, il_8000=9,
         pressure_drop_in_wg=None, self_noise_lw_1k=None,
         source_document="Noise-Control-Catalog_WEB.pdf",
         notes="Film-lined media; moisture-resistant"),
    dict(manufacturer="Vibro-Acoustics", series="RFMB-MV", model="RFMB-MV-F2",
         silencer_type="rectangular", length_in=108, velocity_class="MV",
         max_velocity_fpm=1250, rated_velocity_fpm=1250,
         il_63=9,  il_125=14, il_250=30, il_500=31,
         il_1000=42, il_2000=42, il_4000=23, il_8000=11,
         pressure_drop_in_wg=None, self_noise_lw_1k=None,
         source_document="Noise-Control-Catalog_WEB.pdf",
         notes="Film-lined media; moisture-resistant"),
]

# ---------------------------------------------------------------------------
# VIBRO-ACOUSTICS  —  Elbow silencers (RED / REFL / RENM)
# No standardised catalog IL tables; data is project-specific per geometry.
# Placeholder entry to expose type in UI — user must contact V-A for project data.
# Source: RED-REFL-RENM.pdf
# ---------------------------------------------------------------------------
_VA_ELBOW = [
    dict(manufacturer="Vibro-Acoustics", series="RED", model="RED (project-specific)",
         silencer_type="elbow", length_in=None, velocity_class="HV",
         max_velocity_fpm=2500, rated_velocity_fpm=None,
         il_63=None, il_125=None, il_250=None, il_500=None,
         il_1000=None, il_2000=None, il_4000=None, il_8000=None,
         pressure_drop_in_wg=None, self_noise_lw_1k=None,
         source_document="RED-REFL-RENM.pdf",
         notes="Dissipative elbow; IL is project-specific. Contact Vibro-Acoustics 1-800-565-8401."),
    dict(manufacturer="Vibro-Acoustics", series="REFL", model="REFL (project-specific)",
         silencer_type="elbow", length_in=None, velocity_class="MV",
         max_velocity_fpm=1500, rated_velocity_fpm=None,
         il_63=None, il_125=None, il_250=None, il_500=None,
         il_1000=None, il_2000=None, il_4000=None, il_8000=None,
         pressure_drop_in_wg=None, self_noise_lw_1k=None,
         source_document="RED-REFL-RENM.pdf",
         notes="Film-lined elbow; moisture resistant. IL is project-specific."),
    dict(manufacturer="Vibro-Acoustics", series="RENM", model="RENM (project-specific)",
         silencer_type="elbow", length_in=None, velocity_class="HV",
         max_velocity_fpm=2500, rated_velocity_fpm=None,
         il_63=None, il_125=None, il_250=None, il_500=None,
         il_1000=None, il_2000=None, il_4000=None, il_8000=None,
         pressure_drop_in_wg=None, self_noise_lw_1k=None,
         source_document="RED-REFL-RENM.pdf",
         notes="No-media reactive chamber elbow. IL is project-specific."),
]

# ---------------------------------------------------------------------------
# PRICE INDUSTRIES  —  RL series (Low Velocity, ≤750 fpm)
# Rectangular, static IL (0 fpm per ASTM E477-13), 24×24" test section
# PD at 500 fpm  |  Source: rl_rm_rh_pd.pdf
# Baffle designations: 1B=wide passage, 1D=medium, 1F=narrow, 6B/6D=6" baffles LF
# ---------------------------------------------------------------------------
_PI_RL = [
    # 1B splitter — lowest pressure drop
    dict(manufacturer="Price Industries", series="RL", model="RL/1B",
         silencer_type="rectangular", length_in=36, velocity_class="LV",
         max_velocity_fpm=750, rated_velocity_fpm=0,
         il_63=2,  il_125=3,  il_250=9,  il_500=20,
         il_1000=24, il_2000=19, il_4000=13, il_8000=12,
         pressure_drop_in_wg=0.03, self_noise_lw_1k=None,
         source_document="rl_rm_rh_pd.pdf", notes="PD at 500 fpm"),
    dict(manufacturer="Price Industries", series="RL", model="RL/1B",
         silencer_type="rectangular", length_in=60, velocity_class="LV",
         max_velocity_fpm=750, rated_velocity_fpm=0,
         il_63=4,  il_125=5,  il_250=15, il_500=30,
         il_1000=43, il_2000=35, il_4000=21, il_8000=14,
         pressure_drop_in_wg=0.03, self_noise_lw_1k=None,
         source_document="rl_rm_rh_pd.pdf", notes="PD at 500 fpm"),
    dict(manufacturer="Price Industries", series="RL", model="RL/1B",
         silencer_type="rectangular", length_in=84, velocity_class="LV",
         max_velocity_fpm=750, rated_velocity_fpm=0,
         il_63=5,  il_125=7,  il_250=19, il_500=37,
         il_1000=47, il_2000=41, il_4000=24, il_8000=16,
         pressure_drop_in_wg=0.04, self_noise_lw_1k=None,
         source_document="rl_rm_rh_pd.pdf", notes="PD at 500 fpm"),
    dict(manufacturer="Price Industries", series="RL", model="RL/1B",
         silencer_type="rectangular", length_in=108, velocity_class="LV",
         max_velocity_fpm=750, rated_velocity_fpm=0,
         il_63=6,  il_125=10, il_250=23, il_500=44,
         il_1000=51, il_2000=47, il_4000=28, il_8000=17,
         pressure_drop_in_wg=0.04, self_noise_lw_1k=None,
         source_document="rl_rm_rh_pd.pdf", notes="PD at 500 fpm"),

    # 1D splitter — medium density
    dict(manufacturer="Price Industries", series="RL", model="RL/1D",
         silencer_type="rectangular", length_in=36, velocity_class="LV",
         max_velocity_fpm=750, rated_velocity_fpm=0,
         il_63=4,  il_125=6,  il_250=15, il_500=28,
         il_1000=34, il_2000=28, il_4000=19, il_8000=14,
         pressure_drop_in_wg=0.06, self_noise_lw_1k=None,
         source_document="rl_rm_rh_pd.pdf", notes=None),
    dict(manufacturer="Price Industries", series="RL", model="RL/1D",
         silencer_type="rectangular", length_in=60, velocity_class="LV",
         max_velocity_fpm=750, rated_velocity_fpm=0,
         il_63=6,  il_125=10, il_250=20, il_500=40,
         il_1000=48, il_2000=45, il_4000=25, il_8000=20,
         pressure_drop_in_wg=0.08, self_noise_lw_1k=None,
         source_document="rl_rm_rh_pd.pdf", notes=None),
    dict(manufacturer="Price Industries", series="RL", model="RL/1D",
         silencer_type="rectangular", length_in=84, velocity_class="LV",
         max_velocity_fpm=750, rated_velocity_fpm=0,
         il_63=9,  il_125=13, il_250=28, il_500=44,
         il_1000=50, il_2000=50, il_4000=31, il_8000=24,
         pressure_drop_in_wg=0.08, self_noise_lw_1k=None,
         source_document="rl_rm_rh_pd.pdf", notes=None),
    dict(manufacturer="Price Industries", series="RL", model="RL/1D",
         silencer_type="rectangular", length_in=108, velocity_class="LV",
         max_velocity_fpm=750, rated_velocity_fpm=0,
         il_63=11, il_125=16, il_250=36, il_500=49,
         il_1000=52, il_2000=55, il_4000=37, il_8000=29,
         pressure_drop_in_wg=0.08, self_noise_lw_1k=None,
         source_document="rl_rm_rh_pd.pdf", notes=None),

    # 1F splitter — highest density, highest IL
    dict(manufacturer="Price Industries", series="RL", model="RL/1F",
         silencer_type="rectangular", length_in=36, velocity_class="LV",
         max_velocity_fpm=750, rated_velocity_fpm=0,
         il_63=6,  il_125=10, il_250=21, il_500=36,
         il_1000=43, il_2000=38, il_4000=25, il_8000=17,
         pressure_drop_in_wg=0.18, self_noise_lw_1k=None,
         source_document="rl_rm_rh_pd.pdf", notes="Narrow splitter spacing"),
    dict(manufacturer="Price Industries", series="RL", model="RL/1F",
         silencer_type="rectangular", length_in=60, velocity_class="LV",
         max_velocity_fpm=750, rated_velocity_fpm=0,
         il_63=8,  il_125=13, il_250=30, il_500=43,
         il_1000=48, il_2000=51, il_4000=47, il_8000=28,
         pressure_drop_in_wg=0.19, self_noise_lw_1k=None,
         source_document="rl_rm_rh_pd.pdf", notes="Narrow splitter spacing"),
    dict(manufacturer="Price Industries", series="RL", model="RL/1F",
         silencer_type="rectangular", length_in=84, velocity_class="LV",
         max_velocity_fpm=750, rated_velocity_fpm=0,
         il_63=12, il_125=17, il_250=34, il_500=48,
         il_1000=51, il_2000=53, il_4000=49, il_8000=34,
         pressure_drop_in_wg=0.21, self_noise_lw_1k=None,
         source_document="rl_rm_rh_pd.pdf", notes="Narrow splitter spacing"),
    dict(manufacturer="Price Industries", series="RL", model="RL/1F",
         silencer_type="rectangular", length_in=108, velocity_class="LV",
         max_velocity_fpm=750, rated_velocity_fpm=0,
         il_63=16, il_125=22, il_250=39, il_500=53,
         il_1000=53, il_2000=55, il_4000=52, il_8000=41,
         pressure_drop_in_wg=0.22, self_noise_lw_1k=None,
         source_document="rl_rm_rh_pd.pdf", notes="Narrow splitter spacing"),

    # 6B — 6-inch baffles, low-frequency optimised
    dict(manufacturer="Price Industries", series="RL", model="RL/6B",
         silencer_type="rectangular", length_in=36, velocity_class="LV",
         max_velocity_fpm=750, rated_velocity_fpm=0,
         il_63=2,  il_125=5,  il_250=11, il_500=16,
         il_1000=13, il_2000=9,  il_4000=7,  il_8000=8,
         pressure_drop_in_wg=None, self_noise_lw_1k=None,
         source_document="rl_rm_rh_pd.pdf", notes="6-inch baffles, LF emphasis"),
    dict(manufacturer="Price Industries", series="RL", model="RL/6B",
         silencer_type="rectangular", length_in=108, velocity_class="LV",
         max_velocity_fpm=750, rated_velocity_fpm=0,
         il_63=4,  il_125=14, il_250=29, il_500=37,
         il_1000=37, il_2000=20, il_4000=11, il_8000=10,
         pressure_drop_in_wg=None, self_noise_lw_1k=None,
         source_document="rl_rm_rh_pd.pdf", notes="6-inch baffles, LF emphasis"),

    # 6D — 6-inch baffles, medium density
    dict(manufacturer="Price Industries", series="RL", model="RL/6D",
         silencer_type="rectangular", length_in=36, velocity_class="LV",
         max_velocity_fpm=750, rated_velocity_fpm=0,
         il_63=4,  il_125=7,  il_250=15, il_500=20,
         il_1000=21, il_2000=15, il_4000=10, il_8000=10,
         pressure_drop_in_wg=None, self_noise_lw_1k=None,
         source_document="rl_rm_rh_pd.pdf", notes="6-inch baffles, medium density"),
    dict(manufacturer="Price Industries", series="RL", model="RL/6D",
         silencer_type="rectangular", length_in=108, velocity_class="LV",
         max_velocity_fpm=750, rated_velocity_fpm=0,
         il_63=9,  il_125=16, il_250=37, il_500=45,
         il_1000=48, il_2000=29, il_4000=18, il_8000=17,
         pressure_drop_in_wg=None, self_noise_lw_1k=None,
         source_document="rl_rm_rh_pd.pdf", notes="6-inch baffles, medium density"),
]

# ---------------------------------------------------------------------------
# PRICE INDUSTRIES  —  RM series (Medium Velocity, ≤1750 fpm)
# Static IL (0 fpm)  |  PD at 1750 fpm  |  Source: rl_rm_rh_pd.pdf
# ---------------------------------------------------------------------------
_PI_RM = [
    dict(manufacturer="Price Industries", series="RM", model="RM/1B",
         silencer_type="rectangular", length_in=36, velocity_class="MV",
         max_velocity_fpm=1750, rated_velocity_fpm=0,
         il_63=1,  il_125=3,  il_250=8,  il_500=19,
         il_1000=26, il_2000=20, il_4000=15, il_8000=14,
         pressure_drop_in_wg=0.19, self_noise_lw_1k=None,
         source_document="rl_rm_rh_pd.pdf", notes="PD at 1750 fpm"),
    dict(manufacturer="Price Industries", series="RM", model="RM/1B",
         silencer_type="rectangular", length_in=60, velocity_class="MV",
         max_velocity_fpm=1750, rated_velocity_fpm=0,
         il_63=3,  il_125=5,  il_250=13, il_500=27,
         il_1000=34, il_2000=29, il_4000=20, il_8000=16,
         pressure_drop_in_wg=0.23, self_noise_lw_1k=None,
         source_document="rl_rm_rh_pd.pdf", notes="PD at 1750 fpm"),
    dict(manufacturer="Price Industries", series="RM", model="RM/1B",
         silencer_type="rectangular", length_in=84, velocity_class="MV",
         max_velocity_fpm=1750, rated_velocity_fpm=0,
         il_63=4,  il_125=7,  il_250=18, il_500=36,
         il_1000=42, il_2000=37, il_4000=24, il_8000=18,
         pressure_drop_in_wg=0.28, self_noise_lw_1k=None,
         source_document="rl_rm_rh_pd.pdf", notes="PD at 1750 fpm"),
    dict(manufacturer="Price Industries", series="RM", model="RM/1B",
         silencer_type="rectangular", length_in=108, velocity_class="MV",
         max_velocity_fpm=1750, rated_velocity_fpm=0,
         il_63=6,  il_125=9,  il_250=22, il_500=45,
         il_1000=50, il_2000=46, il_4000=29, il_8000=21,
         pressure_drop_in_wg=0.32, self_noise_lw_1k=None,
         source_document="rl_rm_rh_pd.pdf", notes="PD at 1750 fpm"),

    dict(manufacturer="Price Industries", series="RM", model="RM/1D",
         silencer_type="rectangular", length_in=36, velocity_class="MV",
         max_velocity_fpm=1750, rated_velocity_fpm=0,
         il_63=2,  il_125=5,  il_250=12, il_500=23,
         il_1000=32, il_2000=28, il_4000=20, il_8000=16,
         pressure_drop_in_wg=None, self_noise_lw_1k=None,
         source_document="rl_rm_rh_pd.pdf", notes=None),
    dict(manufacturer="Price Industries", series="RM", model="RM/1D",
         silencer_type="rectangular", length_in=108, velocity_class="MV",
         max_velocity_fpm=1750, rated_velocity_fpm=0,
         il_63=11, il_125=13, il_250=32, il_500=53,
         il_1000=54, il_2000=55, il_4000=39, il_8000=27,
         pressure_drop_in_wg=0.56, self_noise_lw_1k=None,
         source_document="rl_rm_rh_pd.pdf", notes="PD at 1750 fpm"),

    dict(manufacturer="Price Industries", series="RM", model="RM/1F",
         silencer_type="rectangular", length_in=36, velocity_class="MV",
         max_velocity_fpm=1750, rated_velocity_fpm=0,
         il_63=3,  il_125=7,  il_250=16, il_500=27,
         il_1000=38, il_2000=37, il_4000=25, il_8000=18,
         pressure_drop_in_wg=None, self_noise_lw_1k=None,
         source_document="rl_rm_rh_pd.pdf", notes=None),
    dict(manufacturer="Price Industries", series="RM", model="RM/1F",
         silencer_type="rectangular", length_in=108, velocity_class="MV",
         max_velocity_fpm=1750, rated_velocity_fpm=0,
         il_63=16, il_125=26, il_250=35, il_500=53,
         il_1000=52, il_2000=55, il_4000=53, il_8000=34,
         pressure_drop_in_wg=1.95, self_noise_lw_1k=None,
         source_document="rl_rm_rh_pd.pdf",
         notes="PD at 1750 fpm; narrow splitter, high PD"),
]

# ---------------------------------------------------------------------------
# PRICE INDUSTRIES  —  ERM series (Elbow silencers, ≤2500 fpm)
# Static IL (0 fpm)  |  Source: rl_rm_rh_pd.pdf
# ---------------------------------------------------------------------------
_PI_ERM = [
    dict(manufacturer="Price Industries", series="ERM", model="ERM/1B",
         silencer_type="elbow", length_in=36, velocity_class="HV",
         max_velocity_fpm=2500, rated_velocity_fpm=0,
         il_63=4,  il_125=8,  il_250=17, il_500=20,
         il_1000=30, il_2000=29, il_4000=24, il_8000=21,
         pressure_drop_in_wg=None, self_noise_lw_1k=None,
         source_document="rl_rm_rh_pd.pdf", notes="Elbow silencer; 90° turning vanes"),
    dict(manufacturer="Price Industries", series="ERM", model="ERM/1B",
         silencer_type="elbow", length_in=60, velocity_class="HV",
         max_velocity_fpm=2500, rated_velocity_fpm=0,
         il_63=6,  il_125=10, il_250=22, il_500=29,
         il_1000=38, il_2000=37, il_4000=31, il_8000=25,
         pressure_drop_in_wg=None, self_noise_lw_1k=None,
         source_document="rl_rm_rh_pd.pdf", notes="Elbow silencer; 90° turning vanes"),
    dict(manufacturer="Price Industries", series="ERM", model="ERM/1B",
         silencer_type="elbow", length_in=84, velocity_class="HV",
         max_velocity_fpm=2500, rated_velocity_fpm=0,
         il_63=9,  il_125=12, il_250=26, il_500=39,
         il_1000=45, il_2000=45, il_4000=38, il_8000=29,
         pressure_drop_in_wg=None, self_noise_lw_1k=None,
         source_document="rl_rm_rh_pd.pdf", notes="Elbow silencer; 90° turning vanes"),
    dict(manufacturer="Price Industries", series="ERM", model="ERM/1B",
         silencer_type="elbow", length_in=108, velocity_class="HV",
         max_velocity_fpm=2500, rated_velocity_fpm=0,
         il_63=11, il_125=14, il_250=31, il_500=48,
         il_1000=52, il_2000=53, il_4000=45, il_8000=33,
         pressure_drop_in_wg=None, self_noise_lw_1k=None,
         source_document="rl_rm_rh_pd.pdf", notes="Elbow silencer; 90° turning vanes"),

    dict(manufacturer="Price Industries", series="ERM", model="ERM/1D",
         silencer_type="elbow", length_in=36, velocity_class="HV",
         max_velocity_fpm=2500, rated_velocity_fpm=0,
         il_63=3,  il_125=7,  il_250=21, il_500=27,
         il_1000=41, il_2000=38, il_4000=29, il_8000=26,
         pressure_drop_in_wg=None, self_noise_lw_1k=None,
         source_document="rl_rm_rh_pd.pdf", notes=None),
    dict(manufacturer="Price Industries", series="ERM", model="ERM/1D",
         silencer_type="elbow", length_in=60, velocity_class="HV",
         max_velocity_fpm=2500, rated_velocity_fpm=0,
         il_63=6,  il_125=11, il_250=26, il_500=35,
         il_1000=45, il_2000=43, il_4000=37, il_8000=30,
         pressure_drop_in_wg=None, self_noise_lw_1k=None,
         source_document="rl_rm_rh_pd.pdf", notes=None),
    dict(manufacturer="Price Industries", series="ERM", model="ERM/1D",
         silencer_type="elbow", length_in=84, velocity_class="HV",
         max_velocity_fpm=2500, rated_velocity_fpm=0,
         il_63=9,  il_125=14, il_250=32, il_500=43,
         il_1000=49, il_2000=48, il_4000=44, il_8000=33,
         pressure_drop_in_wg=None, self_noise_lw_1k=None,
         source_document="rl_rm_rh_pd.pdf", notes=None),
    dict(manufacturer="Price Industries", series="ERM", model="ERM/1D",
         silencer_type="elbow", length_in=108, velocity_class="HV",
         max_velocity_fpm=2500, rated_velocity_fpm=0,
         il_63=12, il_125=18, il_250=38, il_500=51,
         il_1000=52, il_2000=53, il_4000=51, il_8000=37,
         pressure_drop_in_wg=None, self_noise_lw_1k=None,
         source_document="rl_rm_rh_pd.pdf", notes=None),

    dict(manufacturer="Price Industries", series="ERM", model="ERM/1F",
         silencer_type="elbow", length_in=36, velocity_class="HV",
         max_velocity_fpm=2500, rated_velocity_fpm=0,
         il_63=4,  il_125=14, il_250=25, il_500=37,
         il_1000=46, il_2000=44, il_4000=32, il_8000=27,
         pressure_drop_in_wg=None, self_noise_lw_1k=None,
         source_document="rl_rm_rh_pd.pdf", notes="Narrow splitter elbow"),
    dict(manufacturer="Price Industries", series="ERM", model="ERM/1F",
         silencer_type="elbow", length_in=60, velocity_class="HV",
         max_velocity_fpm=2500, rated_velocity_fpm=0,
         il_63=8,  il_125=17, il_250=33, il_500=41,
         il_1000=47, il_2000=48, il_4000=40, il_8000=33,
         pressure_drop_in_wg=None, self_noise_lw_1k=None,
         source_document="rl_rm_rh_pd.pdf", notes="Narrow splitter elbow"),
    dict(manufacturer="Price Industries", series="ERM", model="ERM/1F",
         silencer_type="elbow", length_in=84, velocity_class="HV",
         max_velocity_fpm=2500, rated_velocity_fpm=0,
         il_63=12, il_125=19, il_250=40, il_500=46,
         il_1000=49, il_2000=51, il_4000=48, il_8000=39,
         pressure_drop_in_wg=None, self_noise_lw_1k=None,
         source_document="rl_rm_rh_pd.pdf", notes="Narrow splitter elbow"),
    dict(manufacturer="Price Industries", series="ERM", model="ERM/1F",
         silencer_type="elbow", length_in=108, velocity_class="HV",
         max_velocity_fpm=2500, rated_velocity_fpm=0,
         il_63=16, il_125=22, il_250=47, il_500=50,
         il_1000=51, il_2000=54, il_4000=55, il_8000=45,
         pressure_drop_in_wg=None, self_noise_lw_1k=None,
         source_document="rl_rm_rh_pd.pdf", notes="Narrow splitter elbow"),
]

# ---------------------------------------------------------------------------
# PRICE INDUSTRIES  —  PCL / PCM / PCH series (Circular Packless Silencers)
# Reactive chamber design, no fibrous media (cleanroom / medical use)
# IL per ASTM E477-20  |  Source: pclpcmpch--circular-silencer-packless-catalog.pdf
# Casing S = 20×20", Casing B = 30×30" extended chamber
# PD at stated velocity
# ---------------------------------------------------------------------------
_PI_PCx = [
    # PCL — maximum IL configuration
    dict(manufacturer="Price Industries", series="PCL", model="PCL-8",
         silencer_type="circular_packless", length_in=36, velocity_class="LV",
         max_velocity_fpm=500, rated_velocity_fpm=500,
         il_63=18, il_125=12, il_250=21, il_500=28,
         il_1000=17, il_2000=17, il_4000=14, il_8000=12,
         pressure_drop_in_wg=0.12, self_noise_lw_1k=None,
         source_document="pclpcmpch--circular-silencer-packless-catalog.pdf",
         notes="8\" dia; reactive chambers; no media"),
    dict(manufacturer="Price Industries", series="PCL", model="PCL-8",
         silencer_type="circular_packless", length_in=60, velocity_class="LV",
         max_velocity_fpm=500, rated_velocity_fpm=500,
         il_63=25, il_125=15, il_250=28, il_500=33,
         il_1000=20, il_2000=19, il_4000=19, il_8000=16,
         pressure_drop_in_wg=0.13, self_noise_lw_1k=None,
         source_document="pclpcmpch--circular-silencer-packless-catalog.pdf",
         notes="8\" dia; 60\" length"),
    dict(manufacturer="Price Industries", series="PCL", model="PCL-12",
         silencer_type="circular_packless", length_in=36, velocity_class="LV",
         max_velocity_fpm=500, rated_velocity_fpm=500,
         il_63=14, il_125=9,  il_250=16, il_500=27,
         il_1000=17, il_2000=14, il_4000=13, il_8000=12,
         pressure_drop_in_wg=0.14, self_noise_lw_1k=None,
         source_document="pclpcmpch--circular-silencer-packless-catalog.pdf",
         notes="12\" dia"),
    dict(manufacturer="Price Industries", series="PCL", model="PCL-16",
         silencer_type="circular_packless", length_in=36, velocity_class="LV",
         max_velocity_fpm=500, rated_velocity_fpm=500,
         il_63=8,  il_125=7,  il_250=12, il_500=30,
         il_1000=14, il_2000=12, il_4000=12, il_8000=10,
         pressure_drop_in_wg=0.12, self_noise_lw_1k=None,
         source_document="pclpcmpch--circular-silencer-packless-catalog.pdf",
         notes="16\" dia"),

    # PCM — balanced IL / pressure drop
    dict(manufacturer="Price Industries", series="PCM", model="PCM-8",
         silencer_type="circular_packless", length_in=36, velocity_class="MV",
         max_velocity_fpm=750, rated_velocity_fpm=750,
         il_63=14, il_125=11, il_250=18, il_500=24,
         il_1000=13, il_2000=12, il_4000=10, il_8000=8,
         pressure_drop_in_wg=0.07, self_noise_lw_1k=None,
         source_document="pclpcmpch--circular-silencer-packless-catalog.pdf",
         notes="8\" dia; balanced design"),
    dict(manufacturer="Price Industries", series="PCM", model="PCM-12",
         silencer_type="circular_packless", length_in=36, velocity_class="MV",
         max_velocity_fpm=750, rated_velocity_fpm=0,
         il_63=13, il_125=6,  il_250=13, il_500=26,
         il_1000=12, il_2000=9,  il_4000=8,  il_8000=7,
         pressure_drop_in_wg=0.0, self_noise_lw_1k=None,
         source_document="pclpcmpch--circular-silencer-packless-catalog.pdf",
         notes="12\" dia; static test"),

    # PCH — lowest pressure drop
    dict(manufacturer="Price Industries", series="PCH", model="PCH-8",
         silencer_type="circular_packless", length_in=36, velocity_class="HV",
         max_velocity_fpm=1000, rated_velocity_fpm=1000,
         il_63=11, il_125=9,  il_250=16, il_500=23,
         il_1000=11, il_2000=12, il_4000=10, il_8000=8,
         pressure_drop_in_wg=0.05, self_noise_lw_1k=None,
         source_document="pclpcmpch--circular-silencer-packless-catalog.pdf",
         notes="8\" dia; lowest pressure drop configuration"),
    dict(manufacturer="Price Industries", series="PCH", model="PCH-16",
         silencer_type="circular_packless", length_in=36, velocity_class="HV",
         max_velocity_fpm=1000, rated_velocity_fpm=0,
         il_63=7,  il_125=2,  il_250=4,  il_500=18,
         il_1000=10, il_2000=7,  il_4000=7,  il_8000=6,
         pressure_drop_in_wg=0.0, self_noise_lw_1k=None,
         source_document="pclpcmpch--circular-silencer-packless-catalog.pdf",
         notes="16\" dia; static test"),
]

# ---------------------------------------------------------------------------
# IAC ACOUSTICS  —  Quiet-Duct rectangular series
# Test per ASTM E477 / ISO 7235, NVLAP-accredited lab
# Reference test section: 600×600 mm; IL at +5 m/s (~1000 fpm) forward flow
# Lengths: 900mm≈35", 1500mm≈59", 2100mm≈83", 3000mm≈118"
# PD: N/m² converted to in.wg (1 N/m² = 0.00401 in.wg)
# Self-noise Lw ref: 0.37 m² face area
# ---------------------------------------------------------------------------
_IAC_QD = [
    # Type S — Standard (industry benchmark splitter geometry)
    dict(manufacturer="IAC Acoustics", series="Quiet-Duct S", model="QD-S-900",
         silencer_type="rectangular", length_in=35, velocity_class="S",
         max_velocity_fpm=1000, rated_velocity_fpm=1000,
         il_63=5,  il_125=9,  il_250=15, il_500=30,
         il_1000=37, il_2000=35, il_4000=27, il_8000=17,
         pressure_drop_in_wg=0.09, self_noise_lw_1k=46,
         source_document="IAC-HVAC-Duct-Silencers.pdf",
         notes="900mm length; self-noise at 0.37m² face"),
    dict(manufacturer="IAC Acoustics", series="Quiet-Duct S", model="QD-S-1500",
         silencer_type="rectangular", length_in=59, velocity_class="S",
         max_velocity_fpm=1000, rated_velocity_fpm=1000,
         il_63=7,  il_125=17, il_250=23, il_500=42,
         il_1000=46, il_2000=46, il_4000=40, il_8000=25,
         pressure_drop_in_wg=0.10, self_noise_lw_1k=46,
         source_document="IAC-HVAC-Duct-Silencers.pdf",
         notes="1500mm length; self-noise at 0.37m² face"),
    dict(manufacturer="IAC Acoustics", series="Quiet-Duct S", model="QD-S-2100",
         silencer_type="rectangular", length_in=83, velocity_class="S",
         max_velocity_fpm=1000, rated_velocity_fpm=1000,
         il_63=9,  il_125=18, il_250=31, il_500=47,
         il_1000=49, il_2000=47, il_4000=45, il_8000=34,
         pressure_drop_in_wg=0.13, self_noise_lw_1k=46,
         source_document="IAC-HVAC-Duct-Silencers.pdf",
         notes="2100mm length; self-noise at 0.37m² face"),
    dict(manufacturer="IAC Acoustics", series="Quiet-Duct S", model="QD-S-3000",
         silencer_type="rectangular", length_in=118, velocity_class="S",
         max_velocity_fpm=1000, rated_velocity_fpm=1000,
         il_63=12, il_125=22, il_250=41, il_500=49,
         il_1000=52, il_2000=50, il_4000=49, il_8000=44,
         pressure_drop_in_wg=0.12, self_noise_lw_1k=46,
         source_document="IAC-HVAC-Duct-Silencers.pdf",
         notes="3000mm length; self-noise at 0.37m² face"),

    # Type LFS — Superior Low Frequency performance
    dict(manufacturer="IAC Acoustics", series="Quiet-Duct LFS", model="QD-LFS-900",
         silencer_type="rectangular", length_in=35, velocity_class="LFS",
         max_velocity_fpm=1000, rated_velocity_fpm=1000,
         il_63=9,  il_125=12, il_250=22, il_500=28,
         il_1000=27, il_2000=21, il_4000=18, il_8000=14,
         pressure_drop_in_wg=0.14, self_noise_lw_1k=45,
         source_document="IAC-HVAC-Duct-Silencers.pdf",
         notes="900mm length; LF emphasis, thick baffles"),
    dict(manufacturer="IAC Acoustics", series="Quiet-Duct LFS", model="QD-LFS-1500",
         silencer_type="rectangular", length_in=59, velocity_class="LFS",
         max_velocity_fpm=1000, rated_velocity_fpm=1000,
         il_63=12, il_125=19, il_250=31, il_500=36,
         il_1000=40, il_2000=27, il_4000=22, il_8000=16,
         pressure_drop_in_wg=0.16, self_noise_lw_1k=45,
         source_document="IAC-HVAC-Duct-Silencers.pdf",
         notes="1500mm length"),
    dict(manufacturer="IAC Acoustics", series="Quiet-Duct LFS", model="QD-LFS-2100",
         silencer_type="rectangular", length_in=83, velocity_class="LFS",
         max_velocity_fpm=1000, rated_velocity_fpm=1000,
         il_63=12, il_125=23, il_250=37, il_500=44,
         il_1000=45, il_2000=33, il_4000=25, il_8000=17,
         pressure_drop_in_wg=0.16, self_noise_lw_1k=45,
         source_document="IAC-HVAC-Duct-Silencers.pdf",
         notes="2100mm length"),
    dict(manufacturer="IAC Acoustics", series="Quiet-Duct LFS", model="QD-LFS-3000",
         silencer_type="rectangular", length_in=118, velocity_class="LFS",
         max_velocity_fpm=1000, rated_velocity_fpm=1000,
         il_63=17, il_125=28, il_250=47, il_500=52,
         il_1000=53, il_2000=47, il_4000=35, il_8000=23,
         pressure_drop_in_wg=0.18, self_noise_lw_1k=45,
         source_document="IAC-HVAC-Duct-Silencers.pdf",
         notes="3000mm length; strongest LF in IAC line"),

    # Type ES — Energy Saver (same acoustics as S, lower PD)
    dict(manufacturer="IAC Acoustics", series="Quiet-Duct ES", model="QD-ES-1500",
         silencer_type="rectangular", length_in=59, velocity_class="S",
         max_velocity_fpm=1000, rated_velocity_fpm=1000,
         il_63=7,  il_125=12, il_250=19, il_500=37,
         il_1000=51, il_2000=49, il_4000=35, il_8000=23,
         pressure_drop_in_wg=0.08, self_noise_lw_1k=None,
         source_document="IAC-HVAC-Duct-Silencers.pdf",
         notes="1500mm; streamlined nose reduces PD ~20%"),
    dict(manufacturer="IAC Acoustics", series="Quiet-Duct ES", model="QD-ES-2100",
         silencer_type="rectangular", length_in=83, velocity_class="S",
         max_velocity_fpm=1000, rated_velocity_fpm=1000,
         il_63=7,  il_125=16, il_250=31, il_500=50,
         il_1000=53, il_2000=52, il_4000=46, il_8000=32,
         pressure_drop_in_wg=0.10, self_noise_lw_1k=None,
         source_document="IAC-HVAC-Duct-Silencers.pdf",
         notes="2100mm"),
    dict(manufacturer="IAC Acoustics", series="Quiet-Duct ES", model="QD-ES-3000",
         silencer_type="rectangular", length_in=118, velocity_class="S",
         max_velocity_fpm=1000, rated_velocity_fpm=1000,
         il_63=9,  il_125=25, il_250=41, il_500=52,
         il_1000=51, il_2000=54, il_4000=49, il_8000=37,
         pressure_drop_in_wg=0.12, self_noise_lw_1k=None,
         source_document="IAC-HVAC-Duct-Silencers.pdf",
         notes="3000mm"),

    # Type LFM — Low Frequency Medium
    dict(manufacturer="IAC Acoustics", series="Quiet-Duct LFM", model="QD-LFM-1500",
         silencer_type="rectangular", length_in=59, velocity_class="LFS",
         max_velocity_fpm=1000, rated_velocity_fpm=1000,
         il_63=8,  il_125=13, il_250=23, il_500=29,
         il_1000=28, il_2000=17, il_4000=14, il_8000=13,
         pressure_drop_in_wg=0.12, self_noise_lw_1k=None,
         source_document="IAC-HVAC-Duct-Silencers.pdf",
         notes="1500mm; medium-thickness LF baffle"),
    dict(manufacturer="IAC Acoustics", series="Quiet-Duct LFM", model="QD-LFM-3000",
         silencer_type="rectangular", length_in=118, velocity_class="LFS",
         max_velocity_fpm=1000, rated_velocity_fpm=1000,
         il_63=15, il_125=22, il_250=39, il_500=50,
         il_1000=50, il_2000=28, il_4000=21, il_8000=16,
         pressure_drop_in_wg=0.16, self_noise_lw_1k=None,
         source_document="IAC-HVAC-Duct-Silencers.pdf",
         notes="3000mm"),

    # Type L — Lowest pressure drop
    dict(manufacturer="IAC Acoustics", series="Quiet-Duct L", model="QD-L-900",
         silencer_type="rectangular", length_in=35, velocity_class="S",
         max_velocity_fpm=1000, rated_velocity_fpm=0,
         il_63=3,  il_125=5,  il_250=9,  il_500=15,
         il_1000=22, il_2000=21, il_4000=13, il_8000=9,
         pressure_drop_in_wg=0.02, self_noise_lw_1k=None,
         source_document="IAC-HVAC-Duct-Silencers.pdf",
         notes="900mm; static IL; open baffle design"),
    dict(manufacturer="IAC Acoustics", series="Quiet-Duct L", model="QD-L-1500",
         silencer_type="rectangular", length_in=59, velocity_class="S",
         max_velocity_fpm=1000, rated_velocity_fpm=0,
         il_63=5,  il_125=8,  il_250=14, il_500=23,
         il_1000=31, il_2000=34, il_4000=17, il_8000=12,
         pressure_drop_in_wg=0.03, self_noise_lw_1k=None,
         source_document="IAC-HVAC-Duct-Silencers.pdf",
         notes="1500mm; static IL; lowest PD in IAC line"),

    # Type SM — Slow air Medium density (≤2.5 m/s)
    dict(manufacturer="IAC Acoustics", series="Quiet-Duct SM", model="QD-SM-1500",
         silencer_type="rectangular", length_in=59, velocity_class="ULV",
         max_velocity_fpm=500, rated_velocity_fpm=1000,
         il_63=6,  il_125=15, il_250=21, il_500=40,
         il_1000=45, il_2000=42, il_4000=34, il_8000=21,
         pressure_drop_in_wg=0.08, self_noise_lw_1k=None,
         source_document="IAC-HVAC-Duct-Silencers.pdf",
         notes="1500mm; max 2.5 m/s face velocity"),

    # Type MS — Medium Slow
    dict(manufacturer="IAC Acoustics", series="Quiet-Duct MS", model="QD-MS-1500",
         silencer_type="rectangular", length_in=59, velocity_class="S",
         max_velocity_fpm=1000, rated_velocity_fpm=1000,
         il_63=4,  il_125=9,  il_250=17, il_500=34,
         il_1000=42, il_2000=33, il_4000=22, il_8000=14,
         pressure_drop_in_wg=0.08, self_noise_lw_1k=None,
         source_document="IAC-HVAC-Duct-Silencers.pdf",
         notes="1500mm; medium-slow profile"),

    # Type ML — Medium Low
    dict(manufacturer="IAC Acoustics", series="Quiet-Duct ML", model="QD-ML-1500",
         silencer_type="rectangular", length_in=59, velocity_class="S",
         max_velocity_fpm=1000, rated_velocity_fpm=1000,
         il_63=4,  il_125=7,  il_250=14, il_500=30,
         il_1000=30, il_2000=20, il_4000=13, il_8000=10,
         pressure_drop_in_wg=0.06, self_noise_lw_1k=None,
         source_document="IAC-HVAC-Duct-Silencers.pdf",
         notes="1500mm; medium-low baffle density"),

    # Type LFL — Low Frequency Low
    dict(manufacturer="IAC Acoustics", series="Quiet-Duct LFL", model="QD-LFL-1500",
         silencer_type="rectangular", length_in=59, velocity_class="LFS",
         max_velocity_fpm=1000, rated_velocity_fpm=1000,
         il_63=6,  il_125=10, il_250=17, il_500=24,
         il_1000=25, il_2000=14, il_4000=12, il_8000=11,
         pressure_drop_in_wg=0.08, self_noise_lw_1k=None,
         source_document="IAC-HVAC-Duct-Silencers.pdf",
         notes="1500mm; low-profile LF baffle"),
]

# ---------------------------------------------------------------------------
# RUSKIN  —  SoundChek series
# Rectangular, Net Insertion Loss, static (0 fpm) per ASTM E477
# Reference test section: 24×24"  |  Reference face area: 4 ft²
# Face area correction: ±3 dB per doubling/halving from 4 ft²
# Self-noise at ±2000 fpm (4 ft²): 62/60/58/56/54/60/62/64 dB (Model A)
# ---------------------------------------------------------------------------
_RUSKIN = [
    # Model A — Standard, ≤2000 fpm
    dict(manufacturer="Ruskin", series="SoundChek A", model="SC-A-36",
         silencer_type="rectangular", length_in=36, velocity_class="HV",
         max_velocity_fpm=2000, rated_velocity_fpm=0,
         il_63=5,  il_125=8,  il_250=18, il_500=29,
         il_1000=37, il_2000=33, il_4000=20, il_8000=13,
         pressure_drop_in_wg=0.37, self_noise_lw_1k=54,
         source_document="Ruskin_SoundChek.pdf",
         notes="PD at 1000 fpm; self-noise at 2000 fpm, 4 ft² face"),
    dict(manufacturer="Ruskin", series="SoundChek A", model="SC-A-60",
         silencer_type="rectangular", length_in=60, velocity_class="HV",
         max_velocity_fpm=2000, rated_velocity_fpm=0,
         il_63=6,  il_125=12, il_250=28, il_500=40,
         il_1000=48, il_2000=50, il_4000=31, il_8000=19,
         pressure_drop_in_wg=0.33, self_noise_lw_1k=54,
         source_document="Ruskin_SoundChek.pdf",
         notes="PD at 1000 fpm"),
    dict(manufacturer="Ruskin", series="SoundChek A", model="SC-A-84",
         silencer_type="rectangular", length_in=84, velocity_class="HV",
         max_velocity_fpm=2000, rated_velocity_fpm=0,
         il_63=9,  il_125=17, il_250=37, il_500=43,
         il_1000=49, il_2000=54, il_4000=41, il_8000=22,
         pressure_drop_in_wg=0.28, self_noise_lw_1k=54,
         source_document="Ruskin_SoundChek.pdf",
         notes="PD at 1000 fpm"),
    dict(manufacturer="Ruskin", series="SoundChek A", model="SC-A-120",
         silencer_type="rectangular", length_in=120, velocity_class="HV",
         max_velocity_fpm=2000, rated_velocity_fpm=0,
         il_63=10, il_125=23, il_250=49, il_500=56,
         il_1000=58, il_2000=59, il_4000=55, il_8000=30,
         pressure_drop_in_wg=0.24, self_noise_lw_1k=54,
         source_document="Ruskin_SoundChek.pdf",
         notes="PD at 1000 fpm; 120\" = longest standard length"),

    # Model AM — Medium velocity, ≤3000 fpm, lower pressure drop
    dict(manufacturer="Ruskin", series="SoundChek AM", model="SC-AM-36",
         silencer_type="rectangular", length_in=36, velocity_class="HV",
         max_velocity_fpm=3000, rated_velocity_fpm=0,
         il_63=4,  il_125=7,  il_250=15, il_500=21,
         il_1000=30, il_2000=28, il_4000=19, il_8000=14,
         pressure_drop_in_wg=0.14, self_noise_lw_1k=None,
         source_document="Ruskin_SoundChek.pdf",
         notes="PD at 1000 fpm; lower PD open-cell splitter"),
    dict(manufacturer="Ruskin", series="SoundChek AM", model="SC-AM-60",
         silencer_type="rectangular", length_in=60, velocity_class="HV",
         max_velocity_fpm=3000, rated_velocity_fpm=0,
         il_63=6,  il_125=11, il_250=21, il_500=31,
         il_1000=47, il_2000=38, il_4000=24, il_8000=17,
         pressure_drop_in_wg=0.12, self_noise_lw_1k=None,
         source_document="Ruskin_SoundChek.pdf",
         notes="PD at 1000 fpm"),
    dict(manufacturer="Ruskin", series="SoundChek AM", model="SC-AM-84",
         silencer_type="rectangular", length_in=84, velocity_class="HV",
         max_velocity_fpm=3000, rated_velocity_fpm=0,
         il_63=8,  il_125=16, il_250=27, il_500=37,
         il_1000=53, il_2000=49, il_4000=32, il_8000=22,
         pressure_drop_in_wg=0.11, self_noise_lw_1k=None,
         source_document="Ruskin_SoundChek.pdf",
         notes="PD at 1000 fpm"),
    dict(manufacturer="Ruskin", series="SoundChek AM", model="SC-AM-120",
         silencer_type="rectangular", length_in=120, velocity_class="HV",
         max_velocity_fpm=3000, rated_velocity_fpm=0,
         il_63=11, il_125=23, il_250=36, il_500=48,
         il_1000=65, il_2000=65, il_4000=42, il_8000=28,
         pressure_drop_in_wg=0.09, self_noise_lw_1k=None,
         source_document="Ruskin_SoundChek.pdf",
         notes="PD at 1000 fpm; 65 dB at 1-2kHz static — "
               "practical IL capped ~50-55 dB due to duct wall flanking"),
]

# ---------------------------------------------------------------------------
# Assemble the full catalog
# ---------------------------------------------------------------------------
SILENCER_CATALOG = (
    _VA_RD_HV
    + _VA_RD_ULV
    + _VA_RFMB
    + _VA_ELBOW
    + _PI_RL
    + _PI_RM
    + _PI_ERM
    + _PI_PCx
    + _IAC_QD
    + _RUSKIN
)


def to_silencer_product_dict(entry: dict) -> dict:
    """
    Map a raw catalog entry to a dict suitable for constructing a
    ``SilencerProduct`` model instance.

    Handles the key-name differences between the catalog format
    (``il_63``, ``model``, ``length_in``) and the database model
    (``insertion_loss_63``, ``model_number``, ``length``).
    """
    return {
        'manufacturer': entry['manufacturer'],
        'model_number': entry['model'],
        'silencer_type': entry['silencer_type'],
        'series': entry.get('series'),
        'length': entry.get('length_in'),
        'velocity_class': entry.get('velocity_class'),
        'max_velocity_fpm': entry.get('max_velocity_fpm'),
        'rated_velocity_fpm': entry.get('rated_velocity_fpm'),
        'velocity_max': entry.get('max_velocity_fpm'),
        'insertion_loss_63': entry.get('il_63'),
        'insertion_loss_125': entry.get('il_125'),
        'insertion_loss_250': entry.get('il_250'),
        'insertion_loss_500': entry.get('il_500'),
        'insertion_loss_1000': entry.get('il_1000'),
        'insertion_loss_2000': entry.get('il_2000'),
        'insertion_loss_4000': entry.get('il_4000'),
        'insertion_loss_8000': entry.get('il_8000'),
        'pressure_drop_in_wg': entry.get('pressure_drop_in_wg'),
        'self_noise_lw_1k': entry.get('self_noise_lw_1k'),
        'source_document': entry.get('source_document'),
        'notes': entry.get('notes'),
    }


def get_silencer_catalog():
    """
    Return the full silencer catalog as a list of dicts.

    Each dict uses the raw catalog key names (``il_63``, ``model``, etc.).
    To seed the database, map entries through ``to_silencer_product_dict``
    before passing them to ``SilencerProduct(**mapped)``::

        from data.silencer_library import get_silencer_catalog, to_silencer_product_dict
        from models.hvac import SilencerProduct

        def populate_silencer_catalog(session):
            if session.query(SilencerProduct).count() > 0:
                return
            for entry in get_silencer_catalog():
                session.add(SilencerProduct(**to_silencer_product_dict(entry)))
            session.commit()

    Returns
    -------
    list[dict]
    """
    return SILENCER_CATALOG


def get_catalog_by_type(silencer_type: str):
    """Filter catalog by silencer_type: 'rectangular', 'elbow', 'circular_packless'."""
    return [s for s in SILENCER_CATALOG if s["silencer_type"] == silencer_type]


def get_catalog_by_manufacturer(manufacturer: str):
    """Filter catalog by manufacturer name (case-insensitive partial match)."""
    mfr = manufacturer.lower()
    return [s for s in SILENCER_CATALOG if mfr in s["manufacturer"].lower()]


def get_il_array(entry: dict) -> list:
    """
    Return the 7-band IL array [63, 125, 250, 500, 1k, 2k, 4k, 8k] from a catalog dict.
    Returns a list of floats; None values indicate unpublished data.
    """
    return [
        entry["il_63"],  entry["il_125"], entry["il_250"], entry["il_500"],
        entry["il_1000"], entry["il_2000"], entry["il_4000"], entry["il_8000"],
    ]


def summarise_catalog():
    """Print a summary of catalog contents to stdout (useful for debugging)."""
    from collections import Counter
    print(f"\nTotal silencer entries: {len(SILENCER_CATALOG)}")
    mfr_counts = Counter(s["manufacturer"] for s in SILENCER_CATALOG)
    type_counts = Counter(s["silencer_type"] for s in SILENCER_CATALOG)
    print("\nBy manufacturer:")
    for mfr, n in sorted(mfr_counts.items()):
        print(f"  {mfr:<30} {n:>3} entries")
    print("\nBy type:")
    for t, n in sorted(type_counts.items()):
        print(f"  {t:<25} {n:>3} entries")


if __name__ == "__main__":
    summarise_catalog()