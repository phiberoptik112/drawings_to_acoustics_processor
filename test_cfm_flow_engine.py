#!/usr/bin/env python3
"""
Tests for CFM inheritance, flow propagation, and dialog CFM persistence.
"""

import os
import sys

# Add src directory to path
CURRENT_DIR = os.path.dirname(__file__)
SRC_DIR = os.path.join(CURRENT_DIR, 'src')
if SRC_DIR not in sys.path:
    sys.path.insert(0, SRC_DIR)

os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')


def _ensure_db():
    from models.database import initialize_database
    try:
        initialize_database()
    except Exception:
        pass


def test_passive_source_inherits_upstream_cfm():
    """Passive primary source should inherit CFM from upstream active component."""
    _ensure_db()
    from models.database import get_hvac_session
    from models.project import Project
    from models.drawing import Drawing
    from models.hvac import HVACComponent, HVACPath, HVACSegment
    from calculations.hvac_path_calculator import HVACPathCalculator

    os.environ['HVAC_DEBUG_EXPORT'] = '1'

    with get_hvac_session() as session:
        project = session.query(Project).first() or Project(name="Test Project CFM Inheritance")
        if project.id is None:
            session.add(project)
            session.flush()

        drawing = session.query(Drawing).filter_by(project_id=project.id).first() or Drawing(
            project_id=project.id, filename="test.pdf", file_path="/tmp/test.pdf"
        )
        if drawing.id is None:
            session.add(drawing)
            session.flush()

        # Active upstream component (fan) with 500 CFM
        fan = HVACComponent(
            project_id=project.id,
            drawing_id=drawing.id,
            name="RF 1-1",
            component_type="fan",
            cfm=500.0,
            x_position=0,
            y_position=0,
        )
        # Passive elbow as configured primary source with no CFM
        elbow = HVACComponent(
            project_id=project.id,
            drawing_id=drawing.id,
            name="ELBOW-1",
            component_type="elbow",
            cfm=None,
            x_position=10,
            y_position=0,
        )
        session.add_all([fan, elbow])
        session.flush()

        path = HVACPath(
            project_id=project.id,
            name="Fan to Elbow",
            description="Passive source inherits from fan",
            primary_source_id=elbow.id,
        )
        session.add(path)
        session.flush()

        seg = HVACSegment(
            hvac_path_id=path.id,
            from_component_id=fan.id,
            to_component_id=elbow.id,
            length=10.0,
            segment_order=1,
            duct_width=12.0,
            duct_height=8.0,
            duct_shape='rectangular',
            duct_type='sheet_metal',
        )
        session.add(seg)
        session.flush()

        calc = HVACPathCalculator(project.id)
        # Use internal builder to inspect source flow rate
        path_data = calc.build_path_data_from_db(path)
        assert path_data is not None, "Path data should be built"
        src = path_data.get('source_component') or {}
        assert 'flow_rate' in src, "Source component should include flow_rate"
        assert abs(float(src.get('flow_rate') or 0.0) - 500.0) < 1e-6, "Passive source should inherit 500 CFM"


def test_flow_propagation_monotonic_nonincreasing():
    """Linear path flow rates should be monotonically non-increasing across segments."""
    _ensure_db()
    from models.database import get_hvac_session
    from models.project import Project
    from models.drawing import Drawing
    from models.hvac import HVACComponent, HVACPath, HVACSegment
    from calculations.hvac_path_calculator import HVACPathCalculator

    with get_hvac_session() as session:
        project = session.query(Project).first() or Project(name="Test Project Flow Monotonic")
        if project.id is None:
            session.add(project)
            session.flush()

        drawing = session.query(Drawing).filter_by(project_id=project.id).first() or Drawing(
            project_id=project.id, filename="test2.pdf", file_path="/tmp/test2.pdf"
        )
        if drawing.id is None:
            session.add(drawing)
            session.flush()

        src = HVACComponent(
            project_id=project.id,
            drawing_id=drawing.id,
            name="SF-1",
            component_type="fan",
            cfm=1200.0,
            x_position=0,
            y_position=0,
        )
        t1 = HVACComponent(project_id=project.id, drawing_id=drawing.id, name="T1", component_type="diffuser", x_position=10, y_position=0)
        t2 = HVACComponent(project_id=project.id, drawing_id=drawing.id, name="T2", component_type="diffuser", x_position=20, y_position=0)
        session.add_all([src, t1, t2])
        session.flush()

        path = HVACPath(project_id=project.id, name="Monotonic Flow", primary_source_id=src.id)
        session.add(path)
        session.flush()

        s1 = HVACSegment(
            hvac_path_id=path.id,
            from_component_id=src.id,
            to_component_id=t1.id,
            length=20.0,
            segment_order=1,
            duct_width=12.0,
            duct_height=12.0,
            duct_shape='rectangular',
            duct_type='sheet_metal',
        )
        s2 = HVACSegment(
            hvac_path_id=path.id,
            from_component_id=t1.id,
            to_component_id=t2.id,
            length=30.0,
            segment_order=2,
            duct_width=12.0,
            duct_height=12.0,
            duct_shape='rectangular',
            duct_type='sheet_metal',
        )
        session.add_all([s1, s2])
        session.flush()

        calc = HVACPathCalculator(project.id)
        path_data = calc.build_path_data_from_db(path)
        assert path_data is not None
        segs = path_data.get('segments') or []
        flows = [float(sd.get('flow_rate') or 0.0) for sd in segs]
        assert len(flows) >= 2
        assert all(flows[i] <= flows[i-1] for i in range(1, len(flows))), f"Flows should be non-increasing, got {flows}"


def test_component_dialog_cfm_persistence():
    """HVACComponentDialog should persist CFM edits to the database."""
    _ensure_db()
    from PySide6.QtWidgets import QApplication
    app = QApplication.instance() or QApplication([])

    from models.database import get_hvac_session
    from models.project import Project
    from models.drawing import Drawing
    from models.hvac import HVACComponent
    from ui.dialogs.hvac_component_dialog import HVACComponentDialog

    with get_hvac_session() as session:
        project = session.query(Project).first() or Project(name="Test Project Dialog CFM")
        if project.id is None:
            session.add(project)
            session.flush()

        drawing = session.query(Drawing).filter_by(project_id=project.id).first() or Drawing(
            project_id=project.id, filename="test3.pdf", file_path="/tmp/test3.pdf"
        )
        if drawing.id is None:
            session.add(drawing)
            session.flush()

        comp = HVACComponent(
            project_id=project.id,
            drawing_id=drawing.id,
            name="Dialog-Comp-1",
            component_type="fan",
            cfm=0.0,
            x_position=0,
            y_position=0,
        )
        session.add(comp)
        session.flush()

        # Load component through dialog and update CFM
        dlg = HVACComponentDialog(component=comp)
        # Set a new CFM in the UI spin and apply
        dlg.cfm_spin.setValue(775.0)
        # Requery a session-bound component instance and apply changes
        db_comp = session.query(HVACComponent).filter(HVACComponent.id == comp.id).first()
        dlg.apply_changes_to_component(db_comp, session)
        session.commit()

        # Verify persistence
        session.refresh(db_comp)
        assert abs(float(db_comp.cfm or 0.0) - 775.0) < 1e-6, "Dialog should persist CFM to database"


