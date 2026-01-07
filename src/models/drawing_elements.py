"""
Drawing Elements - Models for storing drawn elements from the overlay system
"""

from sqlalchemy import Column, Integer, String, DateTime, Text, ForeignKey, Float, JSON
from sqlalchemy.orm import relationship
from datetime import datetime
from .database import Base


class DrawingElement(Base):
	"""Base model for storing drawing elements from the overlay"""
	__tablename__ = 'drawing_elements'
	
	id = Column(Integer, primary_key=True)
	drawing_id = Column(Integer, ForeignKey('drawings.id'), nullable=False)
	project_id = Column(Integer, ForeignKey('projects.id'), nullable=False)
	
	# Element identification
	element_type = Column(String(50), nullable=False)  # 'rectangle', 'component', 'segment', 'measurement'
	element_name = Column(String(255))  # Optional name/label
	page_number = Column(Integer, default=1)  # PDF page number where element exists
	
	# HVAC Path linkage - allows direct association of visual elements with paths
	hvac_path_id = Column(Integer, ForeignKey('hvac_paths.id'), nullable=True)
	hvac_segment_id = Column(Integer, ForeignKey('hvac_segments.id'), nullable=True)
	hvac_component_id = Column(Integer, ForeignKey('hvac_components.id'), nullable=True)
	
	# Position and geometry (in pixels)
	x_position = Column(Float)
	y_position = Column(Float)
	width = Column(Float)
	height = Column(Float)
	
	# Additional coordinates for lines/segments
	end_x_position = Column(Float)
	end_y_position = Column(Float)
	
	# Real-world measurements
	area_real = Column(Float)     # Square feet/meters
	length_real = Column(Float)   # Feet/meters
	volume_real = Column(Float)   # Cubic feet/meters
	
	# Element-specific properties stored as JSON
	properties = Column(JSON)  # Store element-specific data as JSON
	
	# Metadata
	created_date = Column(DateTime, default=datetime.utcnow)
	modified_date = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
	
	# Relationships
	drawing = relationship("Drawing", backref="drawing_elements")
	project = relationship("Project", backref="drawing_elements")
	hvac_path = relationship("HVACPath", backref="drawing_elements")
	hvac_segment = relationship("HVACSegment", backref="drawing_elements")
	hvac_component = relationship("HVACComponent", backref="drawing_elements")
	
	def __repr__(self):
		return f"<DrawingElement(id={self.id}, type='{self.element_type}', drawing_id={self.drawing_id})>"
	
	def to_dict(self):
		"""Convert to dictionary for overlay reconstruction"""
		data = {
			'id': self.id,
			'type': self.element_type,
			'name': self.element_name,
			'page_number': self.page_number,
			'x': self.x_position,
			'y': self.y_position,
			'width': self.width,
			'height': self.height,
			'end_x': self.end_x_position,
			'end_y': self.end_y_position,
			'area_real': self.area_real,
			'length_real': self.length_real,
			'volume_real': self.volume_real,
			'created_date': self.created_date.isoformat() if self.created_date else None,
			'modified_date': self.modified_date.isoformat() if self.modified_date else None,
			# HVAC linkage fields
			'hvac_path_id': self.hvac_path_id,
			'hvac_segment_id': self.hvac_segment_id,
			'hvac_component_id': self.hvac_component_id,
			'db_path_id': self.hvac_path_id,  # Alias for overlay compatibility
			'db_segment_id': self.hvac_segment_id,  # Alias for overlay compatibility
			'db_component_id': self.hvac_component_id,  # Alias for overlay compatibility
		}
		
		# Add properties if they exist
		if self.properties:
			data.update(self.properties)
			
		return data
	
	@classmethod
	def from_overlay_data(cls, drawing_id, project_id, element_data, page_number=1,
						  hvac_path_id=None, hvac_segment_id=None, hvac_component_id=None):
		"""Create DrawingElement from overlay element data
		
		Args:
			drawing_id: ID of the drawing this element belongs to
			project_id: ID of the project
			element_data: Dict with overlay element properties
			page_number: PDF page number
			hvac_path_id: Optional ID of linked HVACPath
			hvac_segment_id: Optional ID of linked HVACSegment
			hvac_component_id: Optional ID of linked HVACComponent
		"""
		element_type = element_data.get('type', 'unknown')
		
		# Check for HVAC IDs in element_data as fallback (overlay may pass them here)
		hvac_path_id = hvac_path_id or element_data.get('hvac_path_id') or element_data.get('db_path_id')
		hvac_segment_id = hvac_segment_id or element_data.get('hvac_segment_id') or element_data.get('db_segment_id')
		hvac_component_id = hvac_component_id or element_data.get('hvac_component_id') or element_data.get('db_component_id')
		
		# Extract common properties
		element = cls(
			drawing_id=drawing_id,
			project_id=project_id,
			element_type=element_type,
			page_number=page_number,
			x_position=element_data.get('x'),
			y_position=element_data.get('y'),
			width=element_data.get('width'),
			height=element_data.get('height'),
			area_real=element_data.get('area_real'),
			length_real=element_data.get('length_real'),
			hvac_path_id=hvac_path_id,
			hvac_segment_id=hvac_segment_id,
			hvac_component_id=hvac_component_id
		)
		
		# Type-specific properties
		saved_zoom = element_data.get('saved_zoom')

		if element_type == 'rectangle':
			element.element_name = f"Rectangle {element_data.get('area_formatted', '')}"
			element.properties = {
				'bounds': {
					'x': element_data.get('x'),
					'y': element_data.get('y'),
					'width': element_data.get('width'),
					'height': element_data.get('height')
				},
				'area_formatted': element_data.get('area_formatted'),
				'width_real': element_data.get('width_real'),
				'height_real': element_data.get('height_real'),
				'saved_zoom': saved_zoom,
				# Preserve space-related flags for cleanup on space deletion
				'converted_to_space': element_data.get('converted_to_space', False),
				'space_id': element_data.get('space_id'),
				'space_name': element_data.get('space_name'),
				'boundary_id': element_data.get('boundary_id'),
			}
		elif element_type == 'polygon':
			element.element_name = f"Polygon {element_data.get('area_formatted', '')}"
			element.properties = {
				'points': element_data.get('points', []),
				'bounds': {
					'x': element_data.get('x'),
					'y': element_data.get('y'),
					'width': element_data.get('width'),
					'height': element_data.get('height')
				},
				'area_formatted': element_data.get('area_formatted'),
				'perimeter_real': element_data.get('perimeter_real'),
				'saved_zoom': saved_zoom,
				# Preserve space-related flags for cleanup on space deletion
				'converted_to_space': element_data.get('converted_to_space', False),
				'space_id': element_data.get('space_id'),
				'space_name': element_data.get('space_name'),
				'boundary_id': element_data.get('boundary_id'),
			}
		elif element_type == 'component':
			component_type = element_data.get('component_type', 'unknown')
			element.element_name = f"{component_type.upper()}"
			element.properties = {
				'component_type': component_type,
				'position': {
					'x': element_data.get('x'),
					'y': element_data.get('y')
				},
				'saved_zoom': saved_zoom
			}
		elif element_type == 'segment':
			element.element_name = f"Segment {element_data.get('length_formatted', '')}"
			element.end_x_position = element_data.get('end_x')
			element.end_y_position = element_data.get('end_y')
			element.properties = {
				'start_x': element_data.get('start_x'),
				'start_y': element_data.get('start_y'),
				'end_x': element_data.get('end_x'),
				'end_y': element_data.get('end_y'),
				'length_pixels': element_data.get('length_pixels'),
				'length_formatted': element_data.get('length_formatted'),
				'from_component': element_data.get('from_component'),
				'to_component': element_data.get('to_component'),
				'saved_zoom': saved_zoom
			}
		elif element_type == 'measurement':
			element.element_name = f"Measurement {element_data.get('length_formatted', '')}"
			element.end_x_position = element_data.get('end_x')
			element.end_y_position = element_data.get('end_y')
			element.properties = {
				'start_x': element_data.get('start_x'),
				'start_y': element_data.get('start_y'),
				'end_x': element_data.get('end_x'),
				'end_y': element_data.get('end_y'),
				'length_pixels': element_data.get('length_pixels'),
				'length_formatted': element_data.get('length_formatted'),
				'saved_zoom': saved_zoom
			}
		
		return element


class DrawingElementManager:
	"""Manager class for saving/loading drawing elements"""
	
	def __init__(self, session_factory):
		self.get_session = session_factory
		
	def save_elements(self, drawing_id, project_id, overlay_data, page_number=1):
		"""Save all drawing elements from overlay data for a specific page"""
		try:
			session = self.get_session()
			
			# Clear existing elements for this drawing and page
			session.query(DrawingElement).filter(
				DrawingElement.drawing_id == drawing_id,
				DrawingElement.page_number == page_number
			).delete()
			
			# Save new elements
			elements_saved = 0
			
			for element_type, elements_list in overlay_data.items():
				if element_type in ['rectangles', 'polygons', 'components', 'segments', 'measurements']:
					for element_data in elements_list:
						# Skip measurements if they're temporary
						if element_type == 'measurements' and not element_data.get('persistent', True):
							continue
							
						# Create drawing element
						drawing_element = DrawingElement.from_overlay_data(
							drawing_id, project_id, element_data, page_number
						)
						
						session.add(drawing_element)
						elements_saved += 1
			
			session.commit()
			session.close()
			
			return elements_saved
			
		except Exception as e:
			session.rollback()
			session.close()
			raise e
			
	def load_elements(self, drawing_id, page_number=1):
		"""Load drawing elements for overlay reconstruction for a specific page"""
		try:
			session = self.get_session()
			
			elements = session.query(DrawingElement).filter(
				DrawingElement.drawing_id == drawing_id,
				DrawingElement.page_number == page_number
			).order_by(DrawingElement.created_date).all()
			
			# Group elements by type for overlay
			overlay_data = {
				'rectangles': [],
				'polygons': [],
				'components': [],
				'segments': [],
				'measurements': []
			}
			
			for element in elements:
				element_dict = element.to_dict()
				
				if element.element_type == 'rectangle':
					overlay_data['rectangles'].append(element_dict)
				elif element.element_type == 'polygon':
					overlay_data['polygons'].append(element_dict)
				elif element.element_type == 'component':
					overlay_data['components'].append(element_dict)
				elif element.element_type == 'segment':
					overlay_data['segments'].append(element_dict)
				elif element.element_type == 'measurement':
					overlay_data['measurements'].append(element_dict)
					
			session.close()
			return overlay_data
			
		except Exception as e:
			session.close()
			raise e
			
	def delete_element(self, element_id):
		"""Delete a specific drawing element"""
		try:
			session = self.get_session()
			
			element = session.query(DrawingElement).filter(
				DrawingElement.id == element_id
			).first()
			
			if element:
				session.delete(element)
				session.commit()
				session.close()
				return True
			else:
				session.close()
				return False
				
		except Exception as e:
			session.rollback()
			session.close()
			raise e
			
	def get_drawing_summary(self, drawing_id):
		"""Get summary statistics for a drawing"""
		try:
			session = self.get_session()
			
			# Count elements by type
			rectangles_count = session.query(DrawingElement).filter(
				DrawingElement.drawing_id == drawing_id,
				DrawingElement.element_type == 'rectangle'
			).count()
			
			components_count = session.query(DrawingElement).filter(
				DrawingElement.drawing_id == drawing_id,
				DrawingElement.element_type == 'component'
			).count()
			
			segments_count = session.query(DrawingElement).filter(
				DrawingElement.drawing_id == drawing_id,
				DrawingElement.element_type == 'segment'
			).count()
			
			# Calculate totals
			total_area = session.query(
				session.func.sum(DrawingElement.area_real)
			).filter(
				DrawingElement.drawing_id == drawing_id,
				DrawingElement.element_type == 'rectangle'
			).scalar() or 0
			
			total_length = session.query(
				session.func.sum(DrawingElement.length_real)
			).filter(
				DrawingElement.drawing_id == drawing_id,
				DrawingElement.element_type == 'segment'
			).scalar() or 0
			
			session.close()
			
			return {
				'rectangles': rectangles_count,
				'components': components_count,
				'segments': segments_count,
				'total_area': total_area,
				'total_length': total_length
			}
			
		except Exception as e:
			session.close()
			raise e
	
	def load_elements_for_path(self, hvac_path_id, drawing_id=None, page_number=None):
		"""Load drawing elements linked to a specific HVAC path.
		
		Args:
			hvac_path_id: ID of the HVACPath to load elements for
			drawing_id: Optional - filter to only elements on this drawing
			page_number: Optional - filter to only elements on this page
			
		Returns:
			Dict with 'components' and 'segments' lists for overlay reconstruction
		"""
		try:
			session = self.get_session()
			
			# Build query with required filter
			query = session.query(DrawingElement).filter(
				DrawingElement.hvac_path_id == hvac_path_id
			)
			
			# Add optional drawing filter
			if drawing_id is not None:
				query = query.filter(DrawingElement.drawing_id == drawing_id)
			
			# Add optional page filter
			if page_number is not None:
				query = query.filter(DrawingElement.page_number == page_number)
			
			elements = query.order_by(DrawingElement.created_date).all()
			
			# Group elements by type
			result = {
				'components': [],
				'segments': []
			}
			
			for element in elements:
				element_dict = element.to_dict()
				
				if element.element_type == 'component':
					result['components'].append(element_dict)
				elif element.element_type == 'segment':
					result['segments'].append(element_dict)
					
			session.close()
			return result
			
		except Exception as e:
			session.close()
			raise e
	
	def save_path_elements(self, drawing_id, project_id, hvac_path_id, components, segments, page_number=1):
		"""Save drawing elements linked to an HVAC path.
		
		This method saves component and segment overlay elements and links them
		to the specified HVAC path for later retrieval.
		
		Args:
			drawing_id: ID of the drawing
			project_id: ID of the project
			hvac_path_id: ID of the HVACPath to link elements to
			components: List of component element dicts from overlay
			segments: List of segment element dicts from overlay
			page_number: PDF page number
			
		Returns:
			Number of elements saved
		"""
		try:
			session = self.get_session()
			
			elements_saved = 0
			
			# Save components
			for comp_data in (components or []):
				# Ensure type is set
				comp_data['type'] = 'component'
				
				element = DrawingElement.from_overlay_data(
					drawing_id, project_id, comp_data, page_number,
					hvac_path_id=hvac_path_id,
					hvac_component_id=comp_data.get('db_component_id') or comp_data.get('hvac_component_id')
				)
				session.add(element)
				elements_saved += 1
			
			# Save segments
			for seg_data in (segments or []):
				# Ensure type is set
				seg_data['type'] = 'segment'
				
				element = DrawingElement.from_overlay_data(
					drawing_id, project_id, seg_data, page_number,
					hvac_path_id=hvac_path_id,
					hvac_segment_id=seg_data.get('db_segment_id') or seg_data.get('hvac_segment_id')
				)
				session.add(element)
				elements_saved += 1
			
			session.commit()
			session.close()
			
			return elements_saved
			
		except Exception as e:
			session.rollback()
			session.close()
			raise e
	
	def delete_path_elements(self, hvac_path_id):
		"""Delete all drawing elements linked to a specific HVAC path.
		
		Args:
			hvac_path_id: ID of the HVACPath whose elements to delete
			
		Returns:
			Number of elements deleted
		"""
		try:
			session = self.get_session()
			
			deleted = session.query(DrawingElement).filter(
				DrawingElement.hvac_path_id == hvac_path_id
			).delete()
			
			session.commit()
			session.close()
			
			return deleted
			
		except Exception as e:
			session.rollback()
			session.close()
			raise e
	
	def update_element_path_link(self, element_id, hvac_path_id=None, hvac_segment_id=None, hvac_component_id=None):
		"""Update HVAC linkage for an existing drawing element.
		
		Args:
			element_id: ID of the DrawingElement to update
			hvac_path_id: New HVACPath ID (or None to clear)
			hvac_segment_id: New HVACSegment ID (or None to clear)
			hvac_component_id: New HVACComponent ID (or None to clear)
			
		Returns:
			True if updated, False if element not found
		"""
		try:
			session = self.get_session()
			
			element = session.query(DrawingElement).filter(
				DrawingElement.id == element_id
			).first()
			
			if element:
				element.hvac_path_id = hvac_path_id
				element.hvac_segment_id = hvac_segment_id
				element.hvac_component_id = hvac_component_id
				session.commit()
				session.close()
				return True
			else:
				session.close()
				return False
				
		except Exception as e:
			session.rollback()
			session.close()
			raise e
	
	def get_path_drawings(self, hvac_path_id):
		"""Get list of drawings that contain elements for a specific HVAC path.
		
		This is useful for showing which drawings a path appears on, especially
		for paths that may span multiple drawings.
		
		Args:
			hvac_path_id: ID of the HVACPath to find drawings for
			
		Returns:
			List of tuples (drawing_id, page_number, element_count) for each
			drawing/page combination that has elements for this path
		"""
		try:
			session = self.get_session()
			
			from sqlalchemy import func
			
			# Query distinct drawing_id/page_number combinations with counts
			results = session.query(
				DrawingElement.drawing_id,
				DrawingElement.page_number,
				func.count(DrawingElement.id).label('element_count')
			).filter(
				DrawingElement.hvac_path_id == hvac_path_id
			).group_by(
				DrawingElement.drawing_id,
				DrawingElement.page_number
			).all()
			
			session.close()
			
			# Convert to list of tuples
			return [(r.drawing_id, r.page_number, r.element_count) for r in results]
			
		except Exception as e:
			session.close()
			raise e
	
	def path_has_elements_on_drawing(self, hvac_path_id, drawing_id, page_number=None):
		"""Check if a path has any elements on a specific drawing/page.
		
		Args:
			hvac_path_id: ID of the HVACPath to check
			drawing_id: ID of the Drawing to check
			page_number: Optional page number to check (if None, checks all pages)
			
		Returns:
			True if path has elements on this drawing/page, False otherwise
		"""
		try:
			session = self.get_session()
			
			query = session.query(DrawingElement).filter(
				DrawingElement.hvac_path_id == hvac_path_id,
				DrawingElement.drawing_id == drawing_id
			)
			
			if page_number is not None:
				query = query.filter(DrawingElement.page_number == page_number)
			
			exists = query.first() is not None
			
			session.close()
			return exists
			
		except Exception as e:
			session.close()
			raise e