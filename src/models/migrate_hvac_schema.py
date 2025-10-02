"""
Database migrations for HVAC-related schema changes.

Ensures that legacy databases gain newly added columns required by
`HVACComponent`, `HVACPath`, and `HVACSegment` models.
"""

from typing import Dict, List, Tuple
from sqlalchemy import text

from .database import get_session


def _get_existing_columns(session, table_name: str) -> List[str]:
    result = session.execute(text(f"PRAGMA table_info({table_name})"))
    return [row[1] for row in result.fetchall()]  # column name is at index 1


def _ensure_columns(session, table: str, columns: List[Tuple[str, str]]):
    """
    Ensure the given columns exist on the table.

    Args:
        session: SQLAlchemy session
        table: table name
        columns: list of (column_name, column_sql_type_default_clause)
                 e.g., ("is_silencer", "INTEGER DEFAULT 0")
    """
    existing = set(_get_existing_columns(session, table))
    for name, type_clause in columns:
        if name not in existing:
            session.execute(text(f"ALTER TABLE {table} ADD COLUMN {name} {type_clause}"))


def ensure_hvac_schema():
    """Run idempotent schema updates for HVAC tables if needed."""
    session = get_session()
    try:
        # hvac_components additions
        _ensure_columns(
            session,
            "hvac_components",
            [
                ("is_silencer", "INTEGER DEFAULT 0"),
                ("silencer_type", "TEXT"),
                ("target_noise_reduction", "REAL"),
                ("frequency_requirements", "TEXT"),
                ("space_constraints", "TEXT"),
                ("selected_product_id", "INTEGER"),
                # Junction preference for BRANCH_TAKEOFF_90 selection
                ("branch_takeoff_choice", "TEXT"),
            ],
        )

        # hvac_paths additions
        _ensure_columns(
            session,
            "hvac_paths",
            [
                ("description", "TEXT"),
                ("path_type", "TEXT DEFAULT 'supply'"),
                ("calculated_noise", "REAL"),
                ("calculated_nc", "REAL"),
                ("modified_date", "DATETIME"),
                # New association columns (idempotent)
                ("primary_source_id", "INTEGER"),
                # Receiver analysis preferences
                ("receiver_distance_ft", "REAL"),
                ("receiver_method", "TEXT"),
            ],
        )

        # hvac_segments additions
        _ensure_columns(
            session,
            "hvac_segments",
            [
                ("duct_width", "REAL"),
                ("duct_height", "REAL"),
                ("diameter", "REAL"),
                ("duct_shape", "TEXT DEFAULT 'rectangular'"),
                ("duct_type", "TEXT DEFAULT 'sheet_metal'"),
                ("insulation", "TEXT"),
                ("lining_thickness", "REAL"),
                ("distance_loss", "REAL"),
                ("duct_loss", "REAL"),
                ("fitting_additions", "REAL"),
            ],
        )

        # segment_fittings additions
        _ensure_columns(
            session,
            "segment_fittings",
            [
                ("quantity", "INTEGER DEFAULT 1"),
            ],
        )

        # Ensure mechanical tables exist (created by metadata.create_all), and
        # keep function idempotent for future mechanical columns.
        try:
            _ensure_columns(
                session,
                "mechanical_units",
                [
                    ("unit_type", "TEXT"),
                    ("manufacturer", "TEXT"),
                    ("model_number", "TEXT"),
                    ("airflow_cfm", "REAL"),
                    ("external_static_inwg", "REAL"),
                    ("power_kw", "REAL"),
                    ("notes", "TEXT"),
                    ("inlet_levels_json", "TEXT"),
                    ("radiated_levels_json", "TEXT"),
                    ("outlet_levels_json", "TEXT"),
                    ("extra_json", "TEXT"),
                ],
            )
            _ensure_columns(
                session,
                "noise_sources",
                [
                    ("source_type", "TEXT"),
                    ("base_noise_dba", "REAL"),
                    ("notes", "TEXT"),
                ],
            )
        except Exception:
            # If tables don't exist yet, metadata.create_all will create them.
            pass

        # hvac_receiver_results additions
        try:
            _ensure_columns(
                session,
                "hvac_receiver_results",
                [
                    ("space_id", "INTEGER"),
                    ("calculation_date", "DATETIME"),
                    ("target_nc", "REAL"),
                    ("nc_rating", "REAL"),
                    ("total_dba", "REAL"),
                    ("meets_target", "INTEGER DEFAULT 0"),
                    ("lp_63", "REAL"),
                    ("lp_125", "REAL"),
                    ("lp_250", "REAL"),
                    ("lp_500", "REAL"),
                    ("lp_1000", "REAL"),
                    ("lp_2000", "REAL"),
                    ("lp_4000", "REAL"),
                    ("room_volume", "REAL"),
                    ("distributed_ceiling_height", "REAL"),
                    ("distributed_floor_area_per_diffuser", "REAL"),
                    ("path_parameters_json", "TEXT"),
                ],
            )
        except Exception:
            # Table may not exist yet; it will be created on fresh DBs
            pass

        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


