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
            ],
        )

        # hvac_segments additions
        _ensure_columns(
            session,
            "hvac_segments",
            [
                ("duct_width", "REAL"),
                ("duct_height", "REAL"),
                ("duct_shape", "TEXT DEFAULT 'rectangular'"),
                ("duct_type", "TEXT DEFAULT 'sheet_metal'"),
                ("insulation", "TEXT"),
                ("distance_loss", "REAL"),
                ("duct_loss", "REAL"),
                ("fitting_additions", "REAL"),
            ],
        )

        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


