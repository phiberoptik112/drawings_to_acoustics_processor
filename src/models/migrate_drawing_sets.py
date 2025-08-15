"""
Database migrations for drawing sets comparison features.

Ensures that legacy databases gain the new tables and columns required for
drawing sets management and comparison functionality.
"""

from typing import List, Tuple
from sqlalchemy import text
from datetime import datetime

from .database import get_session, Base
from .drawing_sets import DrawingSet


def _get_existing_tables(session) -> List[str]:
	"""Get list of existing tables in the database"""
	result = session.execute(text("SELECT name FROM sqlite_master WHERE type='table'"))
	return [row[0] for row in result.fetchall()]


def _get_existing_columns(session, table_name: str) -> List[str]:
	"""Get list of existing columns in a table"""
	result = session.execute(text(f"PRAGMA table_info({table_name})"))
	return [row[1] for row in result.fetchall()]  # column name is at index 1


def _ensure_columns(session, table: str, columns: List[Tuple[str, str]]):
	"""
	Ensure the given columns exist on the table.

	Args:
		session: SQLAlchemy session
		table: table name
		columns: list of (column_name, column_sql_type_default_clause)
				  e.g., ("drawing_set_id", "INTEGER")
	"""
	existing = set(_get_existing_columns(session, table))
	for name, type_clause in columns:
		if name not in existing:
			session.execute(text(f"ALTER TABLE {table} ADD COLUMN {name} {type_clause}"))


def _create_default_drawing_sets(session):
	"""Create default drawing sets for existing projects with drawings"""
	# Get all projects that have drawings but no drawing sets
	projects_with_drawings = session.execute(text(
		"""
		SELECT DISTINCT p.id, p.name 
		FROM projects p 
		INNER JOIN drawings d ON p.id = d.project_id 
		WHERE p.id NOT IN (SELECT DISTINCT project_id FROM drawing_sets)
		"""
	)).fetchall()
	
	for project_id, _project_name in projects_with_drawings:
		# Create a default "Legacy" drawing set for existing drawings
		default_set = DrawingSet(
			project_id=project_id,
			name="Legacy Drawings",
			phase_type="Legacy",
			description="Automatically created for existing drawings",
			is_active=True,
			created_date=datetime.utcnow()
		)
		session.add(default_set)
		session.flush()  # Get the ID
		
		# Assign all unassigned drawings to this set
		session.execute(text(
			"""
			UPDATE drawings 
			SET drawing_set_id = :set_id 
			WHERE project_id = :project_id 
			AND (drawing_set_id IS NULL OR drawing_set_id = 0)
			"""
		), {"set_id": default_set.id, "project_id": project_id})


def ensure_drawing_sets_schema():
	"""Run idempotent schema updates for drawing sets functionality."""
	session = get_session()
	try:
		existing_tables = set(_get_existing_tables(session))
		
		# Ensure all models are registered
		from . import project, drawing, space, hvac, rt60_models, mechanical, drawing_sets  # noqa: F401
		
		# Create new tables if they don't exist
		Base.metadata.create_all(bind=session.get_bind())
		
		# Add drawing_set_id column to existing drawings table
		if 'drawings' in existing_tables:
			_ensure_columns(session, "drawings", [
				("drawing_set_id", "INTEGER")
			])
		
		# Create default drawing sets for existing projects
		if 'drawing_sets' in _get_existing_tables(session):
			count = session.execute(text("SELECT COUNT(*) FROM drawing_sets")).scalar()
			if count == 0:
				_create_default_drawing_sets(session)
		
		session.commit()
	except Exception as e:
		session.rollback()
		print(f"Drawing sets migration failed: {e}")
		raise
	finally:
		session.close()