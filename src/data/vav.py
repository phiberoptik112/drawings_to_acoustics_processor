"""
VAV Terminal Unit SQLAlchemy models.

Sound power data follows AHRI Standard 880 / ASHRAE Standard 130 testing protocols.
Octave band coverage: 63–8000 Hz (8 bands).
  - Bands 125–4000 Hz: directly from AHRI 880 certified catalog data
  - Band 63 Hz:  estimated/extrapolated (not required by AHRI 880 for VAV terminals)
  - Band 8000 Hz: estimated/extrapolated (not required by AHRI 880 for VAV terminals)

Two fundamental sound paths are stored per product:
  - Discharge: sound emitted from the unit outlet, travelling downstream through ductwork
  - Radiated:  sound transmitted through the casing walls into the ceiling plenum or space
  - Plenum (fan-powered units only): sound from the secondary air inlet opening

All levels are sound POWER (Lw), dB re 1 pW (10^-12 W).
Reference standard: ANSI/AHRI 880-2017, ANSI/ASHRAE 130-2016.
"""

from datetime import datetime
from sqlalchemy import Column, Integer, Float, String, Boolean, Text, DateTime
from models import Base


class VAVTerminalUnit(Base):
    """
    VAV terminal unit product database.

    Stores octave-band sound power level data for both discharge and radiated
    sound paths at a defined operating point (rated_flow_cfm, inlet_sp_in_wg).

    Unit types
    ----------
    single_duct_shutoff   – Standard pressure-independent VAV, no reheat
    single_duct_reheat    – Single duct with hot-water or electric reheat coil
    series_fan_powered    – Fan runs continuously; constant discharge volume
    parallel_fan_powered  – Fan cycles on at low primary flow; variable discharge
    dual_duct             – Hot and cold deck inlets, mixing box
    """
    __tablename__ = 'vav_terminal_units'

    id = Column(Integer, primary_key=True)

    # ── Identity ─────────────────────────────────────────────────────────────
    manufacturer     = Column(String(100), nullable=False)
    product_series   = Column(String(100), nullable=False)
    model_number     = Column(String(100), nullable=False)
    unit_type        = Column(String(50),  nullable=False)

    # ── Physical specifications ───────────────────────────────────────────────
    inlet_size_in    = Column(Float, nullable=False)   # round inlet diameter, inches
    outlet_width_in  = Column(Float)                   # rectangular outlet width
    outlet_height_in = Column(Float)                   # rectangular outlet height

    # ── Airflow specifications ────────────────────────────────────────────────
    flow_min_cfm     = Column(Float)   # minimum controllable airflow, CFM
    flow_max_cfm     = Column(Float)   # maximum rated airflow, CFM
    flow_rated_cfm   = Column(Float)   # airflow at which acoustic data is reported
    inlet_sp_in_wg   = Column(Float)   # inlet static pressure for acoustic data, in. w.g.

    # ── Fan-powered unit additional specs ────────────────────────────────────
    fan_cfm          = Column(Float)   # induced / secondary airflow, CFM (FP units)
    fan_motor_hp     = Column(Float)   # fan motor rated horsepower (FP units)
    fan_motor_watts  = Column(Float)   # fan motor input watts (FP units)

    # ── Discharge sound power levels (dB re 1 pW), octave bands 63–8000 Hz ──
    # AHRI 880 certified bands: 125, 250, 500, 1000, 2000, 4000 Hz
    # Estimated bands:          63, 8000 Hz
    discharge_63     = Column(Float)
    discharge_125    = Column(Float)
    discharge_250    = Column(Float)
    discharge_500    = Column(Float)
    discharge_1000   = Column(Float)
    discharge_2000   = Column(Float)
    discharge_4000   = Column(Float)
    discharge_8000   = Column(Float)

    # ── Radiated sound power levels (dB re 1 pW), octave bands 63–8000 Hz ───
    radiated_63      = Column(Float)
    radiated_125     = Column(Float)
    radiated_250     = Column(Float)
    radiated_500     = Column(Float)
    radiated_1000    = Column(Float)
    radiated_2000    = Column(Float)
    radiated_4000    = Column(Float)
    radiated_8000    = Column(Float)

    # ── Plenum / secondary-inlet sound (fan-powered units only) ──────────────
    # Sound path from the open plenum inlet back into the return-air plenum
    plenum_63        = Column(Float, nullable=True)
    plenum_125       = Column(Float, nullable=True)
    plenum_250       = Column(Float, nullable=True)
    plenum_500       = Column(Float, nullable=True)
    plenum_1000      = Column(Float, nullable=True)
    plenum_2000      = Column(Float, nullable=True)
    plenum_4000      = Column(Float, nullable=True)
    plenum_8000      = Column(Float, nullable=True)

    # ── Data provenance ───────────────────────────────────────────────────────
    data_source      = Column(String(200))  # 'ahri_certified_catalog', 'engineering_guide', 'estimated'
    ahri_certified   = Column(Boolean, default=False)
    notes            = Column(Text)

    created_date     = Column(DateTime, default=datetime.utcnow)

    # ── Convenience properties ────────────────────────────────────────────────
    @property
    def discharge_octave_bands(self):
        """Return discharge Lw as a list [63, 125, 250, 500, 1000, 2000, 4000, 8000] Hz."""
        return [
            self.discharge_63, self.discharge_125, self.discharge_250, self.discharge_500,
            self.discharge_1000, self.discharge_2000, self.discharge_4000, self.discharge_8000,
        ]

    @property
    def radiated_octave_bands(self):
        """Return radiated Lw as a list [63, 125, 250, 500, 1000, 2000, 4000, 8000] Hz."""
        return [
            self.radiated_63, self.radiated_125, self.radiated_250, self.radiated_500,
            self.radiated_1000, self.radiated_2000, self.radiated_4000, self.radiated_8000,
        ]

    @property
    def plenum_octave_bands(self):
        """Return plenum Lw as a list (None values for non-FP units)."""
        return [
            self.plenum_63, self.plenum_125, self.plenum_250, self.plenum_500,
            self.plenum_1000, self.plenum_2000, self.plenum_4000, self.plenum_8000,
        ]

    def __repr__(self):
        return (
            f"<VAVTerminalUnit(id={self.id}, mfr='{self.manufacturer}', "
            f"series='{self.product_series}', size={self.inlet_size_in}\", "
            f"type='{self.unit_type}', flow={self.flow_rated_cfm} cfm)>"
        )
