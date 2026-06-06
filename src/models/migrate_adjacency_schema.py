"""
Database migrations for adjacency detection schema.

Adds:
- drawing_pages table (floor/level assignment per PDF page)
- PDF-native coordinate columns on room_boundaries, hvac_components, noise_sources
- Adjacency threshold columns on projects
"""

from typing import List, Tuple
from sqlalchemy import text

from .database import get_session


def _get_existing_tables(session) -> List[str]:
    result = session.execute(text("SELECT name FROM sqlite_master WHERE type='table'"))
    return [row[0] for row in result.fetchall()]


def _get_existing_columns(session, table_name: str) -> List[str]:
    result = session.execute(text(f"PRAGMA table_info({table_name})"))
    return [row[1] for row in result.fetchall()]


def _ensure_columns(session, table: str, columns: List[Tuple[str, str]]):
    existing_tables = set(_get_existing_tables(session))
    if table not in existing_tables:
        return

    existing = set(_get_existing_columns(session, table))
    for name, type_clause in columns:
        if name not in existing:
            session.execute(text(f"ALTER TABLE {table} ADD COLUMN {name} {type_clause}"))


def ensure_adjacency_schema():
    """Run idempotent schema updates for adjacency detection tables."""
    session = get_session()
    try:
        existing_tables = set(_get_existing_tables(session))

        # Create drawing_pages table if it doesn't exist
        if 'drawing_pages' not in existing_tables:
            session.execute(text("""
                CREATE TABLE drawing_pages (
                    id INTEGER PRIMARY KEY,
                    drawing_id INTEGER NOT NULL REFERENCES drawings(id),
                    page_number INTEGER NOT NULL,
                    floor_label TEXT,
                    is_typical INTEGER DEFAULT 0,
                    typical_for_floors TEXT,
                    pdf_page_width REAL,
                    pdf_page_height REAL
                )
            """))

        # room_boundaries: PDF-native columns
        _ensure_columns(session, "room_boundaries", [
            ("pdf_x", "REAL"),
            ("pdf_y", "REAL"),
            ("pdf_width", "REAL"),
            ("pdf_height", "REAL"),
            ("pdf_polygon_pts", "TEXT"),
            ("pdf_page_width", "REAL"),
            ("pdf_page_height", "REAL"),
            ("floor_label", "TEXT"),
            ("noise_source_id", "INTEGER"),
        ])

        # hvac_components: PDF-native columns
        _ensure_columns(session, "hvac_components", [
            ("pdf_x", "REAL"),
            ("pdf_y", "REAL"),
            ("pdf_page_width", "REAL"),
            ("pdf_page_height", "REAL"),
            ("floor_label", "TEXT"),
        ])

        # noise_sources: placement and octave-band columns
        _ensure_columns(session, "noise_sources", [
            ("drawing_id", "INTEGER"),
            ("page_number", "INTEGER"),
            ("pdf_x", "REAL"),
            ("pdf_y", "REAL"),
            ("pdf_page_width", "REAL"),
            ("pdf_page_height", "REAL"),
            ("floor_label", "TEXT"),
            ("placement_type", "TEXT DEFAULT 'unplaced'"),
            ("octave_bands_json", "TEXT"),
        ])

        # projects: adjacency threshold settings
        _ensure_columns(session, "projects", [
            ("adjacency_near_min_in", "REAL DEFAULT 6.0"),
            ("adjacency_near_max_ft", "REAL DEFAULT 3.0"),
        ])

        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
