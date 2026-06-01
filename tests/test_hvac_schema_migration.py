"""Verify HVAC schema migration adds all HVACComponent columns."""

import os
import sqlite3
import tempfile

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

from models.migrate_hvac_schema import ensure_hvac_schema, _get_existing_columns


@pytest.fixture
def legacy_db_path():
    """Create a legacy-style database missing newer HVAC columns."""
    fd, db_path = tempfile.mkstemp(suffix=".db")
    os.close(fd)

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute(
        """
        CREATE TABLE hvac_components (
            id INTEGER PRIMARY KEY,
            project_id INTEGER NOT NULL,
            drawing_id INTEGER NOT NULL,
            name TEXT NOT NULL,
            component_type TEXT NOT NULL,
            custom_type_label TEXT,
            x_position REAL NOT NULL,
            y_position REAL NOT NULL,
            page_number INTEGER DEFAULT 1,
            noise_level REAL,
            branch_takeoff_choice TEXT,
            is_silencer INTEGER DEFAULT 0,
            silencer_type TEXT,
            target_noise_reduction REAL,
            frequency_requirements TEXT,
            space_constraints TEXT,
            selected_product_id INTEGER,
            created_date DATETIME
        )
        """
    )
    conn.commit()
    conn.close()

    yield db_path

    os.remove(db_path)


def test_ensure_hvac_schema_adds_junction_and_elbow_columns(monkeypatch, legacy_db_path):
    engine = create_engine(f"sqlite:///{legacy_db_path}")
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

    import models.database as db_module

    monkeypatch.setattr(db_module, "get_session", lambda: SessionLocal())
    monkeypatch.setattr(db_module, "SessionLocal", SessionLocal)
    monkeypatch.setattr(db_module, "engine", engine)

    ensure_hvac_schema()

    session = SessionLocal()
    try:
        columns = set(_get_existing_columns(session, "hvac_components"))
    finally:
        session.close()

    required = {
        "branch_duct_width",
        "branch_duct_height",
        "branch_duct_diameter",
        "branch_duct_shape",
        "main_duct_width",
        "main_duct_height",
        "main_duct_diameter",
        "main_duct_shape",
        "branch_cfm",
        "main_cfm",
        "mechanical_noise_origin",
        "has_turning_vanes",
        "vane_chord_length",
        "num_vanes",
        "lining_thickness",
        "pressure_drop",
        "position_on_path",
        "elbow_component_id",
        "cfm",
    }
    missing = required - columns
    assert not missing, f"Migration missing columns: {sorted(missing)}"

    session = SessionLocal()
    try:
        session.execute(text("SELECT branch_duct_width, main_cfm FROM hvac_components LIMIT 1"))
    finally:
        session.close()

    engine.dispose()
