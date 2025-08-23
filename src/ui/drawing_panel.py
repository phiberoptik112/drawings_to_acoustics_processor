from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QCheckBox
from PySide6.QtCore import Qt, Signal

from models import get_session, Drawing, Project, DrawingElementManager
from drawing import PDFViewer, DrawingOverlay, ScaleManager


class DrawingPanel(QWidget):
	"""Embeddable drawing panel hosting PDFViewer and DrawingOverlay.
	Provides APIs to load drawings and focus/highlight HVAC paths.
	"""

	finished = Signal()
	paths_updated = Signal()

	def __init__(self, project_id: int, parent=None):
		super().__init__(parent)
		self.project_id = project_id
		self.project = None
		self.drawing_id = None
		self.drawing = None
		self.element_manager = DrawingElementManager(get_session)
		self.scale_manager = ScaleManager()
		self.pdf_viewer = None
		self.drawing_overlay = None
		self.current_page_number = 1
		self._base_scale_ratio = 1.0
		self._link_selection_enabled = True
		self._last_focused_path_id = None

		self._load_project()
		self._init_ui()
		self._setup_connections()

	def _load_project(self):
		try:
			session = get_session()
			self.project = session.query(Project).filter(Project.id == self.project_id).first()
			session.close()
		except Exception:
			self.project = None

	def _init_ui(self):
		layout = QVBoxLayout()
		# Top micro-toolbar for panel-specific toggles
		top_bar = QHBoxLayout()
		self.path_only_chk = QCheckBox("Path Only")
		self.path_only_chk.setToolTip("Hide all drawing elements except those belonging to visible paths")
		self.path_only_chk.stateChanged.connect(self._on_path_only_changed)
		top_bar.addWidget(self.path_only_chk)
		top_bar.addStretch()
		layout.addLayout(top_bar)

		# Viewer + overlay
		self.pdf_viewer = PDFViewer()
		self.drawing_overlay = DrawingOverlay()
		self.drawing_overlay.set_scale_manager(self.scale_manager)

		container = QWidget()
		container_layout = QVBoxLayout()
		container_layout.setContentsMargins(0, 0, 0, 0)
		container_layout.addWidget(self.pdf_viewer)
		container.setLayout(container_layout)

		# Overlay is parented to the PDF label to float over the pixmap
		self.drawing_overlay.setParent(self.pdf_viewer.pdf_label)

		layout.addWidget(container)
		self.setLayout(layout)

	def _setup_connections(self):
		if self.pdf_viewer:
			self.pdf_viewer.scale_changed.connect(self._on_zoom_changed)
			self.pdf_viewer.page_changed.connect(self._on_page_changed)

	def _on_path_only_changed(self, state):
		try:
			self.set_path_only_mode(bool(state == Qt.Checked))
		except Exception:
			pass

	def _on_zoom_changed(self, zoom_factor: float):
		self._update_overlay_geometry()
		try:
			self.scale_manager.scale_ratio = self._base_scale_ratio * (self.pdf_viewer.zoom_factor or 1.0)
			if self.drawing_overlay:
				self.drawing_overlay.set_zoom_factor(self.pdf_viewer.zoom_factor)
		except Exception:
			pass

	def _on_page_changed(self, page_index: int):
		self.current_page_number = (page_index + 1)
		self._update_overlay_geometry()
		self._load_saved_elements()

	def _update_overlay_geometry(self):
		if self.pdf_viewer and self.pdf_viewer.pixmap and self.drawing_overlay:
			label = self.pdf_viewer.pdf_label
			pixmap = self.pdf_viewer.pixmap
			try:
				self.drawing_overlay.resize(pixmap.size())
				offset_x = max((label.width() - pixmap.width()) // 2, 0)
				offset_y = max((label.height() - pixmap.height()) // 2, 0)
				self.drawing_overlay.move(offset_x, offset_y)
			except Exception:
				self.drawing_overlay.move(0, 0)
			# Update page dimensions on the scale manager
			w, h = self.pdf_viewer.get_page_dimensions()
			self.scale_manager.set_page_dimensions(w, h)

	def _load_saved_elements(self):
		if not self.drawing or not self.drawing_overlay:
			return
		try:
			overlay_data = self.element_manager.load_elements(self.drawing.id, self.current_page_number)
			if any(overlay_data.values()):
				self.drawing_overlay.load_elements_data(overlay_data)
			# Always also load space rectangles for this page
			self._load_space_rectangles()
		except Exception:
			pass

	def _load_space_rectangles(self):
		if not self.drawing:
			return
		try:
			session = get_session()
			from models.space import RoomBoundary
			boundaries = session.query(RoomBoundary).filter(
				RoomBoundary.drawing_id == self.drawing.id,
				RoomBoundary.page_number == self.current_page_number
			).all()
			space_rectangles = []
			for boundary in boundaries:
				space_name = boundary.space.name if boundary.space else f"Space {boundary.space_id}"
				rect_data = {
					'type': 'rectangle',
					'bounds': {
						'x': int(boundary.x_position),
						'y': int(boundary.y_position),
						'width': int(boundary.width),
						'height': int(boundary.height)
					},
					'x': int(boundary.x_position),
					'y': int(boundary.y_position),
					'width': int(boundary.width),
					'height': int(boundary.height),
					'area_real': boundary.calculated_area or 0,
					'area_formatted': f"{boundary.calculated_area:.0f} sf" if boundary.calculated_area else "0 sf",
					'space_id': boundary.space_id,
					'space_name': space_name,
					'boundary_id': boundary.id,
					'converted_to_space': True,
					'width_real': self.scale_manager.pixels_to_real(boundary.width) if self.scale_manager else boundary.width / 50,
					'height_real': self.scale_manager.pixels_to_real(boundary.height) if self.scale_manager else boundary.height / 50
				}
				space_rectangles.append(rect_data)
			session.close()
			if space_rectangles:
				self.drawing_overlay.rectangles.extend(space_rectangles)
				self.drawing_overlay.update()
		except Exception:
			pass

	# Public API
	def load_drawing(self, drawing_id: int) -> None:
		"""Load a drawing by id into the embedded viewer."""
		try:
			if drawing_id == self.drawing_id:
				return
			session = get_session()
			self.drawing = session.query(Drawing).filter(Drawing.id == drawing_id).first()
			session.close()
			if not self.drawing or not self.drawing.file_path:
				return
			self.drawing_id = drawing_id
			title = f"{self.drawing.name}"
			# Load PDF and overlay
			if self.pdf_viewer.load_pdf(self.drawing.file_path):
				self._update_overlay_geometry()
				# Set scale
				if self.drawing and self.drawing.scale_string:
					self.scale_manager.set_scale_from_string(self.drawing.scale_string)
					self._base_scale_ratio = self.scale_manager.scale_ratio
					self.scale_manager.scale_ratio = self._base_scale_ratio * (self.pdf_viewer.zoom_factor or 1.0)
				# Load saved elements and paths
				self._load_saved_elements()
		except Exception:
			pass

	def ensure_path_registered(self, path_id: int) -> bool:
		"""Ensure overlay has element mapping for a path by matching DB segments to drawn elements."""
		try:
			if path_id in self.drawing_overlay.path_element_mapping:
				return True
			session = get_session()
			from models.hvac import HVACPath
			path = session.query(HVACPath).filter(HVACPath.id == path_id).first()
			session.close()
			if not path:
				return False
			overlay_data = self.drawing_overlay.get_elements_data()
			drawing_components = overlay_data.get('components', [])
			drawing_segments = overlay_data.get('segments', [])
			path_components = []
			path_segments = []
			for segment in getattr(path, 'segments', []) or []:
				if segment.from_component:
					for comp in drawing_components:
						if (comp.get('x') == segment.from_component.x_position and comp.get('y') == segment.from_component.y_position and comp.get('component_type') == segment.from_component.component_type):
							if comp not in path_components:
								path_components.append(comp)
				if segment.to_component:
					for comp in drawing_components:
						if (comp.get('x') == segment.to_component.x_position and comp.get('y') == segment.to_component.y_position and comp.get('component_type') == segment.to_component.component_type):
							if comp not in path_components:
								path_components.append(comp)
				if segment.from_component and segment.to_component:
					for seg in drawing_segments:
						fc = seg.get('from_component')
						tc = seg.get('to_component')
						if fc and tc and fc.get('x') == segment.from_component.x_position and fc.get('y') == segment.from_component.y_position and tc.get('x') == segment.to_component.x_position and tc.get('y') == segment.to_component.y_position:
							if seg not in path_segments:
								path_segments.append(seg)
			if path_components or path_segments:
				self.drawing_overlay.register_path_elements(path_id, path_components, path_segments)
				return True
			return False
		except Exception:
			return False

	def set_path_only_mode(self, enabled: bool) -> None:
		self.drawing_overlay.path_only_mode = bool(enabled)
		self.drawing_overlay.update()

	def center_on_rect(self, x: int, y: int, w: int, h: int, padding_ratio: float = 0.15) -> None:
		if self.pdf_viewer:
			self.pdf_viewer.zoom_to_rect(x, y, w, h, padding_ratio)

	def clear_focus(self) -> None:
		self.drawing_overlay.set_highlighted_path(None)
		self.drawing_overlay.update()

	def display_path(self, path_id: int, *, center: bool = True, highlight: bool = True, exclusive: bool = True) -> bool:
		"""Focus and optionally center/highlight a path. Returns True if displayed."""
		if not self.ensure_path_registered(path_id):
			return False
		# Show this path and optionally make it exclusive
		if exclusive:
			self.drawing_overlay.visible_paths.clear()
		self.drawing_overlay.visible_paths[path_id] = True
		# Highlight
		if highlight:
			self.drawing_overlay.set_highlighted_path(path_id)
		# Center if possible using overlay bounding rect (convert current pixel rect to PDF rect base before calling viewer)
		if center:
			rect = self.drawing_overlay.compute_path_bounding_rect(path_id)
			if rect is not None:
				# Convert on-screen pixels to PDF (100%) units by dividing by current zoom
				zf = self.pdf_viewer.zoom_factor or 1.0
				x = int(rect.x() / zf)
				y = int(rect.y() / zf)
				w = int(rect.width() / zf)
				h = int(rect.height() / zf)
				self.pdf_viewer.zoom_to_rect(x, y, w, h, padding_ratio=0.15)
		self.drawing_overlay.update()
		self._last_focused_path_id = path_id
		return True

	# Alias
	def focus_path(self, path_id: int, *, center: bool = True, highlight: bool = True, exclusive: bool = True) -> bool:
		return self.display_path(path_id, center=center, highlight=highlight, exclusive=exclusive)