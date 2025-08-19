from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel
from PySide6.QtCore import Qt, QPoint, Signal, QRect
from PySide6.QtGui import QPainter, QPen, QBrush, QColor, QFont
from drawing.drawing_tools import DrawingToolManager, ToolType
from drawing.scale_manager import ScaleManager


class DrawingOverlay(QWidget):
	"""Transparent overlay widget for drawing on top of PDF"""
	
	# Signals
	element_created = Signal(dict)  # New drawing element created
	coordinates_clicked = Signal(float, float)  # Raw coordinates clicked
	measurement_taken = Signal(float, str)  # Measurement in real units
	# Emitted when user double-clicks on a component or segment element
	element_double_clicked = Signal(dict)
	
	def __init__(self, parent=None):
		super().__init__(parent)
		
		# Make overlay transparent
		self.setAttribute(Qt.WA_TransparentForMouseEvents, False)
		self.setStyleSheet("background-color: transparent;")
		
		# Initialize managers
		self.tool_manager = DrawingToolManager()
		self.scale_manager = ScaleManager()
		self._current_zoom_factor = 1.0  # Tracks last applied zoom for coordinate scaling
		# Base (100% zoom) geometry to avoid cumulative scaling drift
		self._base_rectangles = []
		self._base_polygons = []
		self._base_components = []
		self._base_segments = []
		self._base_measurements = []
		# Track whether base caches must be rebuilt from live geometry
		self._base_dirty = True
		
		# Drawing elements storage
		self.rectangles = []  # Room boundaries
		self.polygons = []    # Polygonal spaces
		self.components = []  # HVAC components
		self.segments = []    # Duct segments
		self.measurements = []  # Measurement lines
		self.visible_paths = {}  # Visible HVAC paths {path_id: path_data}
		self.path_element_mapping = {}  # Maps path_id to {components: [], segments: []}
		
		# UI state
		self.show_measurements = True
		self.show_grid = False
		self.path_only_mode = False  # Show only elements belonging to visible paths
		self._highlighted_path_id = None
		
		# Selection/edit state (used when ToolType.SELECT is active)
		self._selection_rect = None  # QRect while box-selecting
		self._selected_components = []
		self._selected_segments = []
		self._drag_active = False
		self._drag_last_point = None
		# When dragging a segment endpoint, keep which endpoint is grabbed
		# {'type': 'segment', 'ref': seg_dict, 'endpoint': 'start'|'end'|None}
		self._hit_target = None
		self._select_modifiers = Qt.NoModifier
		
		# Connect signals
		self.tool_manager.element_created.connect(self.handle_element_created)
		
	def set_scale_manager(self, scale_manager):
		"""Set the scale manager for coordinate conversion"""
		self.scale_manager = scale_manager
		
	def set_tool(self, tool_type):
		"""Set the active drawing tool"""
		self.tool_manager.set_tool(tool_type)
		
		# If switching to segment tool, update available components
		if tool_type == ToolType.SEGMENT:
			self.update_segment_tool_components()
		# Leaving edit mode clears selection
		if tool_type != ToolType.SELECT:
			self._clear_selection()
		
	def set_component_type(self, component_type):
		"""Set component type for component tool"""
		self.tool_manager.set_component_type(component_type)
	
	def update_segment_tool_components(self):
		"""Update the segment tool with current available components and segments"""
		print(f"DEBUG: Updating segment tool with {len(self.components)} components and {len(self.segments)} segments")
		for i, comp in enumerate(self.components):
			print(f"DEBUG: Component {i}: {comp.get('component_type', 'unknown')} at ({comp.get('x', 0)}, {comp.get('y', 0)})")
		for i, seg in enumerate(self.segments):
			print(f"DEBUG: Segment {i}: from_component={seg.get('from_component') is not None}, to_component={seg.get('to_component') is not None}")
		self.tool_manager.set_available_components(self.components)
		self.tool_manager.set_available_segments(self.segments)

	def set_zoom_factor(self, zoom_factor: float):
		"""Project stored base geometry to the new zoom factor.

		We keep base coordinates normalized to 100% zoom. When zoom changes,
		we recompute all on-screen coordinates from the base to avoid drift.
		"""
		try:
			if zoom_factor <= 0:
				return
			z = zoom_factor

			# Build or refresh base geometry from current elements when caches are empty or marked dirty
			if self._base_dirty or not (self._base_rectangles or self._base_polygons or self._base_components or self._base_segments or self._base_measurements):
				cur_z = self._current_zoom_factor or 1.0
				# Reset caches
				self._base_rectangles = []
				self._base_polygons = []
				self._base_components = []
				self._base_segments = []
				self._base_measurements = []

				# Rectangles
				for r in self.rectangles:
					b = r.get('bounds')
					# Normalize bounds into dict form at base scale
					if isinstance(b, dict):
						base_bounds = {
							'x': int(b.get('x', 0) / cur_z),
							'y': int(b.get('y', 0) / cur_z),
							'width': int(b.get('width', 0) / cur_z),
							'height': int(b.get('height', 0) / cur_z),
						}
					elif isinstance(b, QRect):
						base_bounds = {
							'x': int(b.x() / cur_z),
							'y': int(b.y() / cur_z),
							'width': int(b.width() / cur_z),
							'height': int(b.height() / cur_z),
						}
					else:
						base_bounds = None

					self._base_rectangles.append({
						**r,
						'x': int(r.get('x', 0) / cur_z),
						'y': int(r.get('y', 0) / cur_z),
						'width': int(r.get('width', 0) / cur_z),
						'height': int(r.get('height', 0) / cur_z),
						'bounds': base_bounds or r.get('bounds')
					})

				# Components
				for c in self.components:
					bc = c.copy()
					bc['x'] = int(c.get('x', 0) / cur_z)
					bc['y'] = int(c.get('y', 0) / cur_z)
					if isinstance(c.get('position'), dict):
						bc['position'] = {
							'x': int(c['position'].get('x', 0) / cur_z),
							'y': int(c['position'].get('y', 0) / cur_z),
						}
					self._base_components.append(bc)

				# Segments
				for s in self.segments:
					bs = s.copy()
					bs['start_x'] = int(s.get('start_x', 0) / cur_z)
					bs['start_y'] = int(s.get('start_y', 0) / cur_z)
					bs['end_x'] = int(s.get('end_x', 0) / cur_z)
					bs['end_y'] = int(s.get('end_y', 0) / cur_z)
					lp = s.get('length_pixels', None)
					bs['length_pixels'] = (lp if lp is not None else 0) / cur_z
					self._base_segments.append(bs)

				# Measurements
				for m in self.measurements:
					bm = m.copy()
					bm['start_x'] = int(m.get('start_x', 0) / cur_z)
					bm['start_y'] = int(m.get('start_y', 0) / cur_z)
					bm['end_x'] = int(m.get('end_x', 0) / cur_z)
					bm['end_y'] = int(m.get('end_y', 0) / cur_z)
					lp = m.get('length_pixels', None)
					bm['length_pixels'] = (lp if lp is not None else 0) / cur_z
					self._base_measurements.append(bm)

				# Polygons
				for poly in self.polygons:
					bp = poly.copy()
					pts = []
					for p in poly.get('points', []) or []:
						pts.append({'x': int(p.get('x', 0) / cur_z), 'y': int(p.get('y', 0) / cur_z)})
					bp['points'] = pts
					b = poly.get('bounds')
					if isinstance(b, dict):
						bp['bounds'] = {
							'x': int(b.get('x', 0) / cur_z),
							'y': int(b.get('y', 0) / cur_z),
							'width': int(b.get('width', 0) / cur_z),
							'height': int(b.get('height', 0) / cur_z),
						}
					self._base_polygons.append(bp)

			# Helper distance
			def _len_px(x1, y1, x2, y2) -> float:
				dx, dy = x2 - x1, y2 - y1
				return (dx * dx + dy * dy) ** 0.5

			# Project base → current
			for i, br in enumerate(self._base_rectangles):
				if i < len(self.rectangles):
					r = self.rectangles[i]
					r['x'] = int(br.get('x', 0) * z)
					r['y'] = int(br.get('y', 0) * z)
					r['width'] = int(br.get('width', 0) * z)
					r['height'] = int(br.get('height', 0) * z)
					b = br.get('bounds')
					if isinstance(b, dict):
						from PySide6.QtCore import QRect as _QRect
						r['bounds'] = _QRect(
							int(b.get('x', 0) * z),
							int(b.get('y', 0) * z),
							int(b.get('width', 0) * z),
							int(b.get('height', 0) * z),
						)

			for i, bc in enumerate(self._base_components):
				if i < len(self.components):
					c = self.components[i]
					c['x'] = int(bc.get('x', 0) * z)
					c['y'] = int(bc.get('y', 0) * z)
					if isinstance(c.get('position'), dict) and isinstance(bc.get('position'), dict):
						c['position']['x'] = int(bc['position'].get('x', 0) * z)
						c['position']['y'] = int(bc['position'].get('y', 0) * z)

			for i, bs in enumerate(self._base_segments):
				if i < len(self.segments):
					s = self.segments[i]
					s['start_x'] = int(bs.get('start_x', 0) * z)
					s['start_y'] = int(bs.get('start_y', 0) * z)
					s['end_x'] = int(bs.get('end_x', 0) * z)
					s['end_y'] = int(bs.get('end_y', 0) * z)
					lp = _len_px(s['start_x'], s['start_y'], s['end_x'], s['end_y'])
					s['length_pixels'] = lp
					try:
						lr = self.scale_manager.pixels_to_real(lp)
						s['length_real'] = lr
						s['length_formatted'] = self.scale_manager.format_distance(lr)
					except Exception:
						pass

			for i, bm in enumerate(self._base_measurements):
				if i < len(self.measurements):
					m = self.measurements[i]
					m['start_x'] = int(bm.get('start_x', 0) * z)
					m['start_y'] = int(bm.get('start_y', 0) * z)
					m['end_x'] = int(bm.get('end_x', 0) * z)
					m['end_y'] = int(bm.get('end_y', 0) * z)
					lp = _len_px(m['start_x'], m['start_y'], m['end_x'], m['end_y'])
					m['length_pixels'] = lp
					try:
						lr = self.scale_manager.pixels_to_real(lp)
						m['length_real'] = lr
						m['length_formatted'] = self.scale_manager.format_distance(lr)
					except Exception:
						pass

			# Polygons
			for i, bp in enumerate(self._base_polygons):
				if i < len(self.polygons):
					p = self.polygons[i]
					b = bp.get('bounds')
					if isinstance(b, dict):
						from PySide6.QtCore import QRect as _QRect
						p['bounds'] = _QRect(
							int(b.get('x', 0) * z),
							int(b.get('y', 0) * z),
							int(b.get('width', 0) * z),
							int(b.get('height', 0) * z),
						)
					scaled_pts = []
					for pt in bp.get('points', []) or []:
						scaled_pts.append({'x': int(pt.get('x', 0) * z), 'y': int(pt.get('y', 0) * z)})
					p['points'] = scaled_pts

			self._current_zoom_factor = zoom_factor
			self.update_segment_tool_components()
			self.update()
		except Exception as e:
			print(f"DEBUG: set_zoom_factor error: {e}")

	def compute_path_bounding_rect(self, path_id: int):
		"""Compute a QRect bounding all registered elements for the given path in current screen pixels.
		Returns None if the path has no registered elements.
		"""
		try:
			mapping = self.path_element_mapping.get(path_id)
			if not mapping:
				return None
			xs = []
			ys = []
			xe = []
			ye = []
			# Components
			for comp in mapping.get('components', []):
				xs.append(int(comp.get('x', 0)))
				ys.append(int(comp.get('y', 0)))
			# Segments
			for seg in mapping.get('segments', []):
				xs.append(int(seg.get('start_x', 0)))
				ys.append(int(seg.get('start_y', 0)))
				xe.append(int(seg.get('end_x', 0)))
				ye.append(int(seg.get('end_y', 0)))
			all_x = xs + xe
			all_y = ys + ye
			if not all_x or not all_y:
				return None
			min_x = min(all_x)
			max_x = max(all_x)
			min_y = min(all_y)
			max_y = max(all_y)
			from PySide6.QtCore import QRect as _QRect
			return _QRect(min_x, min_y, max(1, max_x - min_x), max(1, max_y - min_y))
		except Exception:
			return None
	
	def set_highlighted_path(self, path_id: int | None) -> None:
		"""Set which path should be visually emphasized in paint routines."""
		self._highlighted_path_id = path_id
		self.update()
		
	def mousePressEvent(self, event):
		"""Handle mouse press events"""
		if event.button() == Qt.LeftButton:
			point = QPoint(event.x(), event.y())
			
			# Emit raw coordinates
			self.coordinates_clicked.emit(event.x(), event.y())
			
			# Start tool or selection depending on tool type
			if self.tool_manager.current_tool_type == ToolType.SELECT:
				self._select_modifiers = event.modifiers()
				self._handle_select_press(point)
			else:
				# Start or extend tool operation
				if self.tool_manager.current_tool_type == ToolType.POLYGON:
					tool = self.tool_manager.get_current_tool()
					if not getattr(tool, 'active', False) or not getattr(tool, 'vertices', []):
						self.tool_manager.start_tool(point)
					else:
						try:
							tool.add_vertex(point)
						except Exception:
							pass
				else:
					# Start tool operation
					self.tool_manager.start_tool(point)
			self.update()
		
	def mouseMoveEvent(self, event):
		"""Handle mouse move events"""
		if event.buttons() & Qt.LeftButton:
			point = QPoint(event.x(), event.y())
			if self.tool_manager.current_tool_type == ToolType.SELECT:
				self._handle_select_move(point)
			else:
				self.tool_manager.update_tool(point)
			self.update()
		
	def mouseReleaseEvent(self, event):
		"""Handle mouse release events"""
		if event.button() == Qt.LeftButton:
			point = QPoint(event.x(), event.y())
			print(f"DEBUG: mouseReleaseEvent - pos: ({point.x()}, {point.y()})")
			print(f"DEBUG: mouseReleaseEvent - calling finish_tool")
			if self.tool_manager.current_tool_type == ToolType.SELECT:
				self._handle_select_release(point)
				self._select_modifiers = Qt.NoModifier
			elif self.tool_manager.current_tool_type == ToolType.POLYGON:
				# Don't finish polygon on mouse release
				pass
			else:
				self.tool_manager.finish_tool(point)
			print(f"DEBUG: mouseReleaseEvent - calling cancel_tool")
			if self.tool_manager.current_tool_type != ToolType.POLYGON:
				self.tool_manager.cancel_tool()
			self.update()

	def mouseDoubleClickEvent(self, event):
		"""Handle element double-clicks to trigger edit dialogs upstream."""
		try:
			if event.button() == Qt.LeftButton:
				point = QPoint(event.x(), event.y())
				# If in polygon drawing mode, finish polygon
				if self.tool_manager.current_tool_type == ToolType.POLYGON:
					self.tool_manager.finish_tool(point)
					self.tool_manager.cancel_tool()
					return
				# Prefer segment (endpoints or line), then component
				hit = self._hit_test_segment(point)
				if hit is not None:
					seg = hit.get('segment')
					if isinstance(seg, dict):
						seg.setdefault('type', 'segment')
						self.element_double_clicked.emit(seg)
						return
				comp = self._hit_test_component(point)
				if comp is not None and isinstance(comp, dict):
					comp.setdefault('type', 'component')
					self.element_double_clicked.emit(comp)
					return
		finally:
			super().mouseDoubleClickEvent(event)
		
	def keyPressEvent(self, event):
		"""Handle key press events"""
		if event.key() == Qt.Key_Escape:
			self.tool_manager.cancel_tool()
			# Clear selection if in edit mode
			if self.tool_manager.current_tool_type == ToolType.SELECT:
				self._clear_selection()
			self.update()
		
	def handle_element_created(self, element_data):
		"""Handle new drawing element creation"""
		element_type = element_data.get('type')
		
		print(f"DEBUG: handle_element_created called with type: {element_type}")
		
		if element_type == 'rectangle':
			# Add real-world calculations
			width_real = self.scale_manager.pixels_to_real(element_data['width'])
			height_real = self.scale_manager.pixels_to_real(element_data['height'])
			area_real = width_real * height_real
			
			element_data.update({
				'width_real': width_real,
				'height_real': height_real,
				'area_real': area_real,
				'area_formatted': self.scale_manager.format_area(area_real)
			})
			
			self.rectangles.append(element_data)
			print(f"DEBUG: Added rectangle, total rectangles: {len(self.rectangles)}")
			self._base_dirty = True
			
		elif element_type == 'polygon':
			try:
				from calculations.geometry import compute_polygon_metrics
				points = element_data.get('points') or []
				metrics = compute_polygon_metrics(points, getattr(self.scale_manager, 'scale_ratio', 1.0))
				area_real = metrics.get('area_real', 0.0)
				perim_real = metrics.get('perimeter_real', 0.0)
				element_data.update({
					'area_real': area_real,
					'perimeter_real': perim_real,
					'area_formatted': self.scale_manager.format_area(area_real)
				})
			except Exception as e:
				print(f"DEBUG: polygon metrics error: {e}")
			self.polygons.append(element_data)
			print(f"DEBUG: Added polygon, total polygons: {len(self.polygons)}")
			self._base_dirty = True
			
		elif element_type == 'component':
			self.components.append(element_data)
			print(f"DEBUG: Added component, total components: {len(self.components)}")
			# Update segment tool with new component
			self.update_segment_tool_components()
			# Attempt to connect this component to any nearby segment endpoints
			try:
				self.attach_component_to_nearby_segments(element_data, threshold_px=20)
			except Exception as e:
				print(f"DEBUG: attach_component_to_nearby_segments error: {e}")
			self._base_dirty = True
			
		elif element_type == 'segment':
			# Add real-world calculations
			length_pixels = element_data.get('length_pixels', 0)
			try:
				length_real = self.scale_manager.pixels_to_real(length_pixels)
				element_data['length_real'] = length_real
				element_data['length_formatted'] = self.scale_manager.format_distance(length_real)
			except Exception:
				pass
			self.segments.append(element_data)
			print(f"DEBUG: Added segment, total segments: {len(self.segments)}")
			self._base_dirty = True
			
		elif element_type == 'measurement':
			# Add real-world calculations
			length_pixels = element_data.get('length_pixels', 0)
			try:
				length_real = self.scale_manager.pixels_to_real(length_pixels)
				element_data['length_real'] = length_real
				element_data['length_formatted'] = self.scale_manager.format_distance(length_real)
			except Exception:
				pass
			self.measurements.append(element_data)
			self.measurement_taken.emit(length_real, self.scale_manager.format_distance(length_real))
			
		# Emit the enhanced element data
		self.element_created.emit(element_data)
		self.update()
		
	def paintEvent(self, event):
		"""Paint the overlay elements"""
		painter = QPainter(self)
		painter.setRenderHint(QPainter.Antialiasing)
		
		try:
			# Draw existing elements
			self.draw_rectangles(painter)
			self.draw_polygons(painter)
			self.draw_components(painter)
			self.draw_segments(painter)
			
			if self.show_measurements:
				self.draw_measurements(painter)
				
			if self.show_grid:
				self.draw_grid(painter)
				
			# Draw current tool preview
			current_tool = self.tool_manager.get_current_tool()
			if current_tool and current_tool.active:
				current_tool.draw_preview(painter)
			# Draw selection visuals
			self._draw_selection(painter)
			# Optional highlight pass for focused path
			if self._highlighted_path_id is not None and self._highlighted_path_id in self.path_element_mapping:
				try:
					mapping = self.path_element_mapping[self._highlighted_path_id]
					pen = QPen(QColor(255, 215, 0))
					pen.setWidth(3)
					painter.setPen(pen)
					for seg in mapping.get('segments', []):
						painter.drawLine(int(seg.get('start_x', 0)), int(seg.get('start_y', 0)), int(seg.get('end_x', 0)), int(seg.get('end_y', 0)))
					for comp in mapping.get('components', []):
						painter.drawEllipse(int(comp.get('x', 0)) - 6, int(comp.get('y', 0)) - 6, 12, 12)
				except Exception:
					pass
		except Exception as e:
			print(f"Error drawing overlay: {e}")
			
	def draw_rectangles(self, painter):
		"""Draw room boundary rectangles"""
		for rect_data in self.rectangles:
			bounds = rect_data['bounds']
			
			# Handle both QRect objects and dictionary representations
			if isinstance(bounds, dict):
				# Convert dictionary back to QRect
				rect = QRect(bounds['x'], bounds['y'], bounds['width'], bounds['height'])
			else:
				# Already a QRect object
				rect = bounds
			
			# Differentiate between regular rectangles and converted spaces
			is_space = rect_data.get('converted_to_space', False)
			
			if is_space:
				# Green for spaces that are already converted
				pen = QPen(QColor(34, 139, 34), 3, Qt.SolidLine)  # Forest green
				brush = QBrush(QColor(34, 139, 34, 40))
			else:
				# Blue for regular rectangles
				pen = QPen(QColor(0, 120, 215), 2, Qt.SolidLine)
				brush = QBrush(QColor(0, 120, 215, 30))
			
			painter.setPen(pen)
			painter.setBrush(brush)
			painter.drawRect(rect)
			
			# Draw label
			center_x = rect.center().x()
			center_y = rect.center().y()
			
			if is_space:
				# Show space name for converted spaces
				space_name = rect_data.get('space_name', 'Space')
				area_text = rect_data.get('area_formatted', f"{rect_data.get('area_real', 0):.0f} sf")
				
				painter.setPen(QPen(Qt.black))
				painter.setFont(QFont("Arial", 9, QFont.Bold))
				
				# Draw space name above area
				painter.drawText(center_x - 40, center_y - 8, space_name)
				painter.setFont(QFont("Arial", 8))
				painter.drawText(center_x - 30, center_y + 8, area_text)

	def draw_polygons(self, painter):
		"""Draw polygonal room boundaries"""
		from PySide6.QtGui import QPolygon
		for poly in self.polygons:
			pts = poly.get('points') or []
			if len(pts) < 3:
				continue
			qpts = []
			for p in pts:
				qpts.append(QPoint(int(p.get('x', 0)), int(p.get('y', 0))))
			polygon = QPolygon(qpts)
			is_space = poly.get('converted_to_space', False)
			if is_space:
				pen = QPen(QColor(34, 139, 34), 3, Qt.SolidLine)
				brush = QBrush(QColor(34, 139, 34, 40))
			else:
				pen = QPen(QColor(0, 120, 215), 2, Qt.SolidLine)
				brush = QBrush(QColor(0, 120, 215, 30))
			painter.setPen(pen)
			painter.setBrush(brush)
			painter.drawPolygon(polygon)
			# centroid
			try:
				cx = sum(p.x() for p in polygon) // polygon.count()
				cy = sum(p.y() for p in polygon) // polygon.count()
			except Exception:
				b = poly.get('bounds')
				if isinstance(b, QRect):
					cx, cy = b.center().x(), b.center().y()
				else:
					cx, cy = qpts[0].x(), qpts[0].y()
			area_text = poly.get('area_formatted', f"{int(poly.get('area_real', 0) or 0)} sf")
			if is_space:
				space_name = poly.get('space_name', 'Space')
				painter.setPen(QPen(Qt.black))
				painter.setFont(QFont("Arial", 9, QFont.Bold))
				painter.drawText(cx - 40, cy - 8, space_name)
				painter.setFont(QFont("Arial", 8))
				painter.drawText(cx - 30, cy + 8, area_text)
			else:
				painter.setPen(QPen(Qt.black))
				painter.setFont(QFont("Arial", 8))
				painter.drawText(cx - 30, cy + 8, area_text)

	def get_elements_summary(self):
		"""Get summary of all drawn elements"""
		return {
			'rectangles': len(self.rectangles),
			'polygons': len(self.polygons),
			'components': len(self.components),
			'segments': len(self.segments),
			'measurements': len(self.measurements),
			'total_area': sum(rect.get('area_real', 0) for rect in self.rectangles) + sum(poly.get('area_real', 0) for poly in self.polygons),
			'total_duct_length': sum(seg.get('length_real', 0) for seg in self.segments)
		}

	def get_elements_data(self):
		"""Get all elements data with proper structure"""
		# Include current zoom so persistence can normalize back to base
		for lst in (self.rectangles, self.polygons, self.components, self.segments, self.measurements):
			for item in lst:
				item['saved_zoom'] = self._current_zoom_factor
		return {
			'rectangles': self.rectangles.copy(),
			'polygons': self.polygons.copy(),
			'components': self.components.copy(),
			'segments': self.segments.copy(),
			'measurements': self.measurements.copy()
		}

	def load_elements_data(self, data):
		"""Load element data from saved state"""
		# Reset base caches when loading persisted elements
		self._base_rectangles = []
		self._base_polygons = []
		self._base_components = []
		self._base_segments = []
		self._base_measurements = []

		# Load rectangles and reconstruct QRect objects
		rectangles = data.get('rectangles', [])
		for rect_data in rectangles:
			bounds = rect_data.get('bounds')
			if isinstance(bounds, dict):
				# Reconstruct QRect from dictionary
				rect_data['bounds'] = QRect(bounds['x'], bounds['y'], bounds['width'], bounds['height'])
			# Normalize into base geometry using any saved zoom factor
			try:
				z = rect_data.get('saved_zoom') or 1.0
				self._base_rectangles.append({
					**rect_data,
					'x': int(rect_data.get('x', 0) / z),
					'y': int(rect_data.get('y', 0) / z),
					'width': int(rect_data.get('width', 0) / z),
					'height': int(rect_data.get('height', 0) / z)
				})
			except Exception:
				pass
		self.rectangles = rectangles

		# Load polygons and normalize base geometry
		self.polygons = data.get('polygons', [])
		try:
			for poly in self.polygons:
				z = poly.get('saved_zoom') or 1.0
				bp = poly.copy()
				pts = []
				for p in poly.get('points', []) or []:
					pts.append({
						'x': int(p.get('x', 0) / z),
						'y': int(p.get('y', 0) / z),
					})
				bp['points'] = pts
				b = poly.get('bounds')
				if isinstance(b, dict):
					bp['bounds'] = {
						'x': int(b.get('x', 0) / z),
						'y': int(b.get('y', 0) / z),
						'width': int(b.get('width', 0) / z),
						'height': int(b.get('height', 0) / z),
					}
				self._base_polygons.append(bp)
		except Exception:
			pass
		self.components = data.get('components', [])
		self.segments = data.get('segments', [])
		self.measurements = data.get('measurements', [])

		# Build base caches for components/segments/measurements
		try:
			for comp in self.components:
				z = comp.get('saved_zoom') or 1.0
				bc = comp.copy()
				bc['x'] = int(comp.get('x', 0) / z)
				bc['y'] = int(comp.get('y', 0) / z)
				self._base_components.append(bc)
			for seg in self.segments:
				z = seg.get('saved_zoom') or 1.0
				bs = seg.copy()
				bs['start_x'] = int(seg.get('start_x', 0) / z)
				bs['start_y'] = int(seg.get('start_y', 0) / z)
				bs['end_x'] = int(seg.get('end_x', 0) / z)
				bs['end_y'] = int(seg.get('end_y', 0) / z)
				self._base_segments.append(bs)
			for meas in self.measurements:
				z = meas.get('saved_zoom') or 1.0
				bm = meas.copy()
				bm['start_x'] = int(meas.get('start_x', 0) / z)
				bm['start_y'] = int(meas.get('start_y', 0) / z)
				bm['end_x'] = int(meas.get('end_x', 0) / z)
				bm['end_y'] = int(meas.get('end_y', 0) / z)
				self._base_measurements.append(bm)
		except Exception:
			pass

		# After loading, project to current zoom factor so display matches
		try:
			# Base was rebuilt from saved data; mark clean and project to current
			self._base_dirty = False
			self.set_zoom_factor(self._current_zoom_factor)
		except Exception:
			pass
		self.update()