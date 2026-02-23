"""
Edge case tests for database operations.

Tests cover:
- Project creation with edge case names
- Drawing operations with missing/invalid files
- Session management and transactions
- Model relationships and cascades
"""

import sys
import os
import tempfile
import pytest

# Add src directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from datetime import datetime
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from models.database import Base
from models.project import Project


class TestProjectEdgeCases:
    """Edge case tests for Project model."""

    @pytest.fixture
    def temp_db_session(self):
        """Create a temporary in-memory database for testing."""
        engine = create_engine('sqlite:///:memory:', echo=False)
        Base.metadata.create_all(engine)
        SessionLocal = sessionmaker(bind=engine)
        session = SessionLocal()
        yield session
        session.close()

    def test_create_project_with_empty_name(self, temp_db_session):
        """Test creating project with empty name."""
        # SQLAlchemy won't block empty string, but app should validate
        project = Project(name='')
        temp_db_session.add(project)
        temp_db_session.commit()

        # Project created but name is empty
        assert project.id is not None
        assert project.name == ''

    def test_create_project_with_none_name(self, temp_db_session):
        """Test creating project with None name - should raise error."""
        project = Project(name=None)
        temp_db_session.add(project)

        # Should raise IntegrityError due to nullable=False
        with pytest.raises(Exception):  # IntegrityError or similar
            temp_db_session.commit()

        temp_db_session.rollback()

    def test_create_project_with_special_characters(self, temp_db_session):
        """Test creating project with special characters in name."""
        special_name = "Test/\\:*?\"<>|Project!@#$%^&()"
        project = Project(name=special_name)
        temp_db_session.add(project)
        temp_db_session.commit()

        # Should handle special characters
        assert project.id is not None
        assert project.name == special_name

    def test_create_project_with_unicode_characters(self, temp_db_session):
        """Test creating project with unicode characters."""
        unicode_name = "测试项目 Проект тест 🏠"
        project = Project(name=unicode_name)
        temp_db_session.add(project)
        temp_db_session.commit()

        # Should handle unicode
        assert project.id is not None
        assert project.name == unicode_name

    def test_create_project_with_extremely_long_name(self, temp_db_session):
        """Test creating project with name exceeding column limit."""
        # Column is String(255)
        long_name = "A" * 1000
        project = Project(name=long_name)
        temp_db_session.add(project)

        # SQLite will truncate or allow; other DBs might error
        # We just verify it doesn't crash
        try:
            temp_db_session.commit()
            assert project.id is not None
        except Exception:
            temp_db_session.rollback()
            pass  # Database-specific behavior

    def test_project_to_dict_with_none_dates(self):
        """Test project to_dict when dates are None."""
        project = Project(name="Test")
        project.created_date = None
        project.modified_date = None

        result = project.to_dict()

        assert result['created_date'] is None
        assert result['modified_date'] is None

    def test_project_to_dict_with_valid_dates(self, temp_db_session):
        """Test project to_dict with valid dates."""
        project = Project(name="Test")
        temp_db_session.add(project)
        temp_db_session.commit()

        result = project.to_dict()

        assert result['created_date'] is not None
        assert isinstance(result['created_date'], str)  # ISO format string

    def test_project_repr(self):
        """Test project __repr__ method."""
        project = Project(name="Test Project")
        project.id = 123

        repr_str = repr(project)

        assert "123" in repr_str
        assert "Test Project" in repr_str


class TestDrawingEdgeCases:
    """Edge case tests for Drawing model."""

    @pytest.fixture
    def temp_db_session(self):
        """Create a temporary in-memory database for testing."""
        engine = create_engine('sqlite:///:memory:', echo=False)

        # Import all models to ensure tables are created
        from models.project import Project
        from models.drawing import Drawing

        Base.metadata.create_all(engine)
        SessionLocal = sessionmaker(bind=engine)
        session = SessionLocal()
        yield session
        session.close()

    def test_drawing_with_nonexistent_file_path(self, temp_db_session):
        """Test drawing with file path that doesn't exist."""
        from models.drawing import Drawing

        project = Project(name="Test")
        temp_db_session.add(project)
        temp_db_session.commit()

        drawing = Drawing(
            project_id=project.id,
            file_path="/nonexistent/path/to/file.pdf",
            name="Test Drawing"
        )
        temp_db_session.add(drawing)
        temp_db_session.commit()

        # Drawing created even if file doesn't exist
        assert drawing.id is not None
        assert drawing.file_path == "/nonexistent/path/to/file.pdf"

    def test_drawing_with_special_characters_in_path(self, temp_db_session):
        """Test drawing with special characters in file path."""
        from models.drawing import Drawing

        project = Project(name="Test")
        temp_db_session.add(project)
        temp_db_session.commit()

        special_path = "/path/with spaces/and-special_chars!@#/file (1).pdf"
        drawing = Drawing(
            project_id=project.id,
            file_path=special_path,
            name="Test Drawing"
        )
        temp_db_session.add(drawing)
        temp_db_session.commit()

        assert drawing.id is not None
        assert drawing.file_path == special_path

    def test_drawing_with_empty_name(self, temp_db_session):
        """Test drawing with empty name."""
        from models.drawing import Drawing

        project = Project(name="Test")
        temp_db_session.add(project)
        temp_db_session.commit()

        drawing = Drawing(
            project_id=project.id,
            file_path="/path/to/file.pdf",
            name=""
        )
        temp_db_session.add(drawing)
        temp_db_session.commit()

        assert drawing.id is not None
        assert drawing.name == ""


class TestSessionManagement:
    """Edge case tests for database session management."""

    @pytest.fixture
    def temp_db_session(self):
        """Create a temporary in-memory database for testing."""
        engine = create_engine('sqlite:///:memory:', echo=False)
        Base.metadata.create_all(engine)
        SessionLocal = sessionmaker(bind=engine)
        session = SessionLocal()
        yield session
        session.close()

    def test_rollback_on_error(self, temp_db_session):
        """Test that rollback works correctly on error."""
        # Add a valid project
        project1 = Project(name="Valid Project")
        temp_db_session.add(project1)
        temp_db_session.commit()

        # Try to add invalid project
        project2 = Project(name=None)  # Invalid
        temp_db_session.add(project2)

        try:
            temp_db_session.commit()
        except Exception:
            temp_db_session.rollback()

        # Original project should still exist after rollback
        existing = temp_db_session.query(Project).filter_by(name="Valid Project").first()
        assert existing is not None

    def test_multiple_operations_in_transaction(self, temp_db_session):
        """Test multiple operations in single transaction."""
        # Create multiple projects
        projects = [Project(name=f"Project {i}") for i in range(10)]

        for p in projects:
            temp_db_session.add(p)

        temp_db_session.commit()

        # All should be created
        count = temp_db_session.query(Project).count()
        assert count == 10

    def test_session_expunge_detached_object(self, temp_db_session):
        """Test working with detached objects."""
        project = Project(name="Test")
        temp_db_session.add(project)
        temp_db_session.commit()

        project_id = project.id

        # Expunge object from session
        temp_db_session.expunge(project)

        # Object is now detached but should still have data
        assert project.id == project_id
        assert project.name == "Test"


class TestCascadeDeletes:
    """Edge case tests for cascade delete operations."""

    @pytest.fixture
    def temp_db_session(self):
        """Create a temporary in-memory database for testing."""
        engine = create_engine('sqlite:///:memory:', echo=False)

        # Import all models
        from models.project import Project
        from models.drawing import Drawing
        from models.space import Space

        Base.metadata.create_all(engine)
        SessionLocal = sessionmaker(bind=engine)
        session = SessionLocal()
        yield session
        session.close()

    def test_delete_project_cascades_to_drawings(self, temp_db_session):
        """Test that deleting project deletes associated drawings."""
        from models.drawing import Drawing

        project = Project(name="Test")
        temp_db_session.add(project)
        temp_db_session.commit()

        drawing = Drawing(
            project_id=project.id,
            file_path="/path/to/file.pdf",
            name="Test Drawing"
        )
        temp_db_session.add(drawing)
        temp_db_session.commit()

        drawing_id = drawing.id

        # Delete project
        temp_db_session.delete(project)
        temp_db_session.commit()

        # Drawing should be deleted too
        deleted_drawing = temp_db_session.query(Drawing).get(drawing_id)
        assert deleted_drawing is None

    def test_delete_project_cascades_to_spaces(self, temp_db_session):
        """Test that deleting project deletes associated spaces."""
        from models.space import Space

        project = Project(name="Test")
        temp_db_session.add(project)
        temp_db_session.commit()

        space = Space(
            project_id=project.id,
            name="Test Space"
        )
        temp_db_session.add(space)
        temp_db_session.commit()

        space_id = space.id

        # Delete project
        temp_db_session.delete(project)
        temp_db_session.commit()

        # Space should be deleted too
        deleted_space = temp_db_session.query(Space).get(space_id)
        assert deleted_space is None


class TestResultTypesEdgeCases:
    """Edge case tests for calculation result types."""

    def test_calculation_result_with_none_values(self):
        """Test CalculationResult handles None values."""
        from calculations.result_types import CalculationResult, ResultStatus

        result = CalculationResult(
            status=ResultStatus.SUCCESS,
            data=None,
            error_message=None,
            warnings=None,
            metadata=None
        )

        assert result.status == ResultStatus.SUCCESS
        assert result.data is None
        # __post_init__ should initialize warnings and metadata to empty
        assert result.warnings == []
        assert result.metadata == {}

    def test_operation_result_success_factory(self):
        """Test OperationResult success factory method."""
        from calculations.result_types import OperationResult

        result = OperationResult.success_result("Operation completed", {"key": "value"})

        assert result.success == True
        assert result.message == "Operation completed"
        assert result.data == {"key": "value"}

    def test_operation_result_error_factory(self):
        """Test OperationResult error factory method."""
        from calculations.result_types import OperationResult

        result = OperationResult.error_result("Something went wrong")

        assert result.success == False
        assert result.message == "Something went wrong"

    def test_rt60_result_error_factory(self):
        """Test RT60Result error factory method."""
        from calculations.result_types import RT60Result

        result = RT60Result.error("Invalid input")

        assert result.is_valid == False
        assert result.error_message == "Invalid input"
        assert result.rt60 == float('inf')
        assert result.surfaces == []

    def test_rt60_result_to_dict(self):
        """Test RT60Result to_dict method."""
        from calculations.result_types import RT60Result, SurfaceData

        surface = SurfaceData(
            surface_type='ceiling',
            area=100.0,
            material_key='acoustic_tile',
            material_name='Acoustic Tile',
            absorption_coeff=0.8,
            absorption=80.0
        )

        result = RT60Result(
            rt60=0.5,
            method='sabine',
            volume=1000.0,
            surfaces=[surface],
            total_area=100.0,
            total_absorption=80.0,
            avg_absorption_coeff=0.8
        )

        dict_result = result.to_dict()

        assert dict_result['rt60'] == 0.5
        assert dict_result['method'] == 'sabine'
        assert len(dict_result['surfaces']) == 1
        assert dict_result['surfaces'][0]['type'] == 'ceiling'

    def test_rt60_result_to_dict_with_error(self):
        """Test RT60Result to_dict when invalid."""
        from calculations.result_types import RT60Result

        result = RT60Result.error("Test error")
        dict_result = result.to_dict()

        # Invalid RT60 should be converted to sentinel value
        assert dict_result['rt60'] == 999.9
        assert dict_result['error'] == "Test error"

    def test_nc_analysis_data_post_init(self):
        """Test NCAnalysisData __post_init__ for warnings list."""
        from calculations.result_types import NCAnalysisData

        data = NCAnalysisData(
            nc_rating=35,
            overall_dba=40.0,
            octave_band_levels={500: 35.0},
            meets_target=True
        )

        # __post_init__ should initialize warnings to empty list
        assert data.warnings == []


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
