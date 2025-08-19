"""
Idempotent migration: ensure polygon_points column exists on room_boundaries.
"""
from sqlalchemy import inspect, Column, Text
from sqlalchemy.exc import OperationalError
from .database import engine


def ensure_space_polygon_schema():
	if engine is None:
		return
	try:
		inspector = inspect(engine)
		cols = [c['name'] for c in inspector.get_columns('room_boundaries')]
		if 'polygon_points' in cols:
			return
		# Add column
		with engine.connect() as conn:
			conn.execute("ALTER TABLE room_boundaries ADD COLUMN polygon_points TEXT")
	except OperationalError:
		# SQLite older versions may error if column exists; ignore
		pass
	except Exception as e:
		print(f"Warning: ensure_space_polygon_schema failed: {e}")