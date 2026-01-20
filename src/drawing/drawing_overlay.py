from typing import Union, Optional
from PySide6.QtWidgets import QWidget
from PySide6.QtCore import Qt, QPoint, Signal, QRect
from PySide6.QtGui import QPainter, QPen, QBrush, QColor, QFont
from drawing.drawing_tools import DrawingToolManager, ToolType
from drawing.scale_manager import ScaleManager


class DrawingOverlay(QWidget):
    """Transparent overlay widget for drawing on top of PDF"""
    
    # Signals
    element_created = Signal(dict)            # New drawing element created
    coordinates_clicked = Signal(float, float)  # Raw coordinates clicked
    measurement_taken = Signal(float, str)    # Measurement in real units
    element_double_clicked = Signal(dict)     # Emitted on double-click of an element
    space_clicked = Signal(dict)              # Emitted when a saved space is clicked
    element_hovered = Signal(object, str)     # Emitted when hovering over an element (id, type)
    element_unhovered = Signal()              # Emitted when leaving an element
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        # Make overlay transparent
        self.setAttribute(Qt.WA_TransparentForMouseEvents, False)
        self.setStyleSheet("background-color: transparent;")
        
        # Managers
        self.tool_manager = DrawingToolManager()
        self.scale_manager = ScaleManager()

        # Zoom/base caches
        self._current_zoom_factor = 1.0
        self._base_rectangles: list[dict] = []
        self._base_polygons: list[dict] = []
        self._base_components: list[dict] = []
        self._base_segments: list[dict] = []
        self._base_measurements: list[dict] = []
        self._base_dirty = True
        
        # Elements
        self.rectangles: list[dict] = []
        self.polygons: list[dict] = []
        self.components: list[dict] = []
        self.segments: list[dict] = []
        self.measurements: list[dict] = []
        self.visible_paths: dict[int, bool] = {}
        self.hidden_paths: set[int] = set()  # Paths explicitly hidden by user
        self.path_element_mapping: dict[int, dict] = {}
        
        # Protection flag to prevent clearing during save operations
        self._clearing_disabled = False
        
        # UI state
        self.show_measurements = True
        self.show_grid = False
        self.path_only_mode = False
        self._highlighted_path_id: Optional[int] = None
        
        # Element highlighting for analysis panel integration
        self._highlighted_element_id: Optional[object] = None
        self._highlighted_element_type: Optional[str] = None
        self._selected_analysis_element_id: Optional[object] = None
        self._selected_analysis_element_type: Optional[str] = None

        # Selection/drag state
        self._selection_rect: Optional[QRect] = None
        self._selected_components: list[dict] = []
        self._selected_segments: list[dict] = []
        self._drag_active = False
        self._drag_last_point: Optional[QPoint] = None
        # {'type': 'segment'|'component', 'ref': dict, 'endpoint': 'start'|'end'|None}
        self._hit_target: Optional[dict] = None
        self._select_modifiers = Qt.NoModifier
        # Snapping threshold in pixels
        self._snap_threshold_px: int = 20
        
        # Element ID counter for unique identification
        self._element_id_counter: int = 0
        
        # Connect signals
        self.tool_manager.element_created.connect(self.handle_element_created)
    
    def _generate_element_id(self) -> str:
        """Generate a unique element ID for components and segments."""
        self._element_id_counter += 1
        return f"elem_{self._element_id_counter}"
        
    def set_scale_manager(self, scale_manager):
        self.scale_manager = scale_manager
        
    def set_tool(self, tool_type):
        self.tool_manager.set_tool(tool_type)
        if tool_type == ToolType.SEGMENT:
            self.update_segment_tool_components()
        if tool_type != ToolType.SELECT:
            self._clear_selection()
        
    def set_component_type(self, component_type):
        self.tool_manager.set_component_type(component_type)
    
    def update_segment_tool_components(self):
        """Provide visible components to snapping logic."""
        # In path_only_mode, filter to only components in visible paths
        if self.path_only_mode:
            visible_components = [
                c for c in self.components
                if self._is_component_in_visible_path(c)
            ]
            self.tool_manager.set_available_components(visible_components)
        else:
            # In normal mode, provide all components
            self.tool_manager.set_available_components(self.components)

        self.tool_manager.set_available_segments(self.segments)

    def set_zoom_factor(self, zoom_factor: float):
        """Recompute on-screen coordinates from base geometry at given zoom."""
        try:
            if zoom_factor <= 0:
                return
            z = zoom_factor

            # #region agent log
            import json; open('/Users/jakepfitsch/Documents/drawings_to_acoustics_processor/.cursor/debug.log', 'a').write(json.dumps({'location': 'drawing_overlay.py:set_zoom_factor:entry', 'message': 'set_zoom_factor called', 'data': {'new_zoom': zoom_factor, 'current_zoom': self._current_zoom_factor, 'base_dirty': self._base_dirty, 'num_components': len(self.components), 'num_base_components': len(self._base_components)}, 'timestamp': __import__('time').time()*1000, 'sessionId': 'debug-session', 'hypothesisId': 'H1,H2,H3'}) + '\n')
            # #endregion

            # Build base caches when dirty/empty
            if self._base_dirty or not (self._base_rectangles or self._base_polygons or self._base_components or self._base_segments or self._base_measurements):
                cur_z = self._current_zoom_factor or 1.0
                self._base_rectangles = []
                self._base_polygons = []
                self._base_components = []
                self._base_segments = []
                self._base_measurements = []

                # Rectangles
                for r in self.rectangles:
                    b = r.get('bounds')
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

                # Components - use saved_zoom if available, else cur_z
                # #region agent log
                _comp_samples_before = [{'x': c.get('x'), 'y': c.get('y'), 'saved_zoom': c.get('saved_zoom'), 'type': c.get('component_type')} for c in self.components[:3]] if self.components else []
                import json; open('/Users/jakepfitsch/Documents/drawings_to_acoustics_processor/.cursor/debug.log', 'a').write(json.dumps({'location': 'drawing_overlay.py:set_zoom_factor:base_rebuild', 'message': 'Rebuilding base cache from current coords', 'data': {'cur_z_for_division': cur_z, 'sample_components_before': _comp_samples_before}, 'timestamp': __import__('time').time()*1000, 'sessionId': 'debug-session', 'hypothesisId': 'H1,H3'}) + '\n')
                # #endregion
                for c in self.components:
                    elem_z = c.get('saved_zoom') or cur_z
                    if elem_z <= 0:
                        elem_z = 1.0  # Prevent division by zero or negative
                    bc = c.copy()
                    bc['x'] = int(c.get('x', 0) / elem_z)
                    bc['y'] = int(c.get('y', 0) / elem_z)
                    if isinstance(c.get('position'), dict):
                        bc['position'] = {
                            'x': int(c['position'].get('x', 0) / elem_z),
                            'y': int(c['position'].get('y', 0) / elem_z),
                        }
                    self._base_components.append(bc)

                # Segments - use saved_zoom if available, else cur_z
                for s in self.segments:
                    elem_z = s.get('saved_zoom') or cur_z
                    bs = s.copy()
                    bs['start_x'] = int(s.get('start_x', 0) / elem_z)
                    bs['start_y'] = int(s.get('start_y', 0) / elem_z)
                    bs['end_x'] = int(s.get('end_x', 0) / elem_z)
                    bs['end_y'] = int(s.get('end_y', 0) / elem_z)
                    lp = s.get('length_pixels', None)
                    bs['length_pixels'] = (lp if lp is not None else 0) / elem_z
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
                    _old_x, _old_y = c.get('x'), c.get('y')
                    c['x'] = int(bc.get('x', 0) * z)
                    c['y'] = int(bc.get('y', 0) * z)
                    if isinstance(c.get('position'), dict) and isinstance(bc.get('position'), dict):
                        c['position']['x'] = int(bc['position'].get('x', 0) * z)
                        c['position']['y'] = int(bc['position'].get('y', 0) * z)
                    # #region agent log
                    if i < 3:
                        import json; open('/Users/jakepfitsch/Documents/drawings_to_acoustics_processor/.cursor/debug.log', 'a').write(json.dumps({'location': 'drawing_overlay.py:set_zoom_factor:projection', 'message': f'Component {i} coords after projection', 'data': {'old_x': _old_x, 'old_y': _old_y, 'base_x': bc.get('x'), 'base_y': bc.get('y'), 'new_x': c['x'], 'new_y': c['y'], 'zoom': z, 'drift_x': c['x'] - _old_x if _old_x else 0, 'drift_y': c['y'] - _old_y if _old_y else 0}, 'timestamp': __import__('time').time()*1000, 'sessionId': 'debug-session', 'hypothesisId': 'H1'}) + '\n')
                    # #endregion

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
        try:
            mapping = self.path_element_mapping.get(path_id)
            if not mapping:
                return None
            xs, ys, xe, ye = [], [], [], []
            for comp in mapping.get('components', []):
                xs.append(int(comp.get('x', 0)))
                ys.append(int(comp.get('y', 0)))
            for seg in mapping.get('segments', []):
                xs.append(int(seg.get('start_x', 0)))
                ys.append(int(seg.get('start_y', 0)))
                xe.append(int(seg.get('end_x', 0)))
                ye.append(int(seg.get('end_y', 0)))
            all_x = xs + xe
            all_y = ys + ye
            if not all_x or not all_y:
                return None
            min_x, max_x = min(all_x), max(all_x)
            min_y, max_y = min(all_y), max(all_y)
            from PySide6.QtCore import QRect as _QRect
            return _QRect(min_x, min_y, max(1, max_x - min_x), max(1, max_y - min_y))
        except Exception:
            return None
    
    def set_highlighted_path(self, path_id: Optional[int]) -> None:
        self._highlighted_path_id = path_id
        self.update()
    
    # ---------------------- Element Highlighting (Analysis Panel) ----------------------
    
    def set_highlighted_element(self, element_id: object, element_type: str) -> None:
        """Highlight a specific element for analysis panel integration.
        
        Args:
            element_id: The database ID of the element (can be int or None)
            element_type: Type of element ('segment', 'component', 'source', 'receiver', etc.)
        """
        self._highlighted_element_id = element_id
        self._highlighted_element_type = element_type
        self.update()
    
    def clear_highlighted_element(self) -> None:
        """Clear the highlighted element."""
        self._highlighted_element_id = None
        self._highlighted_element_type = None
        self.update()
    
    def set_selected_element(self, element_id: object, element_type: str) -> None:
        """Select a specific element for analysis panel integration.
        
        Args:
            element_id: The database ID of the element
            element_type: Type of element
        """
        self._selected_analysis_element_id = element_id
        self._selected_analysis_element_type = element_type
        self.update()
    
    def clear_selected_element(self) -> None:
        """Clear the selected analysis element."""
        self._selected_analysis_element_id = None
        self._selected_analysis_element_type = None
        self.update()
    
    def _is_element_highlighted(self, element: dict, element_type: str) -> bool:
        """Check if an element should be drawn with highlight styling."""
        if self._highlighted_element_id is None:
            return False
        
        # Get element ID (could be 'id', 'db_id', or other)
        elem_id = element.get('id') or element.get('db_id')
        if elem_id is None:
            return False
        
        return elem_id == self._highlighted_element_id
    
    def _is_element_selected(self, element: dict, element_type: str) -> bool:
        """Check if an element should be drawn with selection styling."""
        if self._selected_analysis_element_id is None:
            return False
        
        elem_id = element.get('id') or element.get('db_id')
        if elem_id is None:
            return False
        
        return elem_id == self._selected_analysis_element_id
        
    # ---------------------- Mouse/keyboard events ----------------------
    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            point = QPoint(event.x(), event.y())
            self.coordinates_clicked.emit(event.x(), event.y())
            
            # Check for space click first when in SELECT mode
            if self.tool_manager.current_tool_type == ToolType.SELECT:
                space_hit = self._hit_test_space(point)
                if space_hit:
                    # Emit signal for space selection
                    self.space_clicked.emit(space_hit['data'])
                    self.update()
                    return
                
                self._select_modifiers = event.modifiers()
                self._handle_select_press(point)
            else:
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
                    self.tool_manager.start_tool(point)
            self.update()
            
    def mouseMoveEvent(self, event):
        point = QPoint(event.x(), event.y())
        
        # Handle hover detection for analysis panel integration
        if not (event.buttons() & Qt.LeftButton):
            self._handle_hover_detection(point)
        
        if event.buttons() & Qt.LeftButton:
            if self.tool_manager.current_tool_type == ToolType.SELECT:
                self._handle_select_move(point)
            else:
                self.tool_manager.update_tool(point)
            self.update()
    
    def _handle_hover_detection(self, point: QPoint):
        """Detect which element is being hovered and emit signals for analysis panel."""
        # Check components first
        comp = self._hit_test_component(point)
        if comp is not None and isinstance(comp, dict):
            elem_id = comp.get('id') or comp.get('db_id')
            if elem_id:
                self.element_hovered.emit(elem_id, 'component')
                return
        
        # Check segments
        hit = self._hit_test_segment(point)
        if hit is not None:
            seg = hit.get('segment')
            if isinstance(seg, dict):
                elem_id = seg.get('id') or seg.get('db_id')
                if elem_id:
                    self.element_hovered.emit(elem_id, 'segment')
                    return
        
        # Nothing hovered - emit unhover signal
        self.element_unhovered.emit()
            
    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton:
            point = QPoint(event.x(), event.y())
            if self.tool_manager.current_tool_type == ToolType.SELECT:
                self._handle_select_release(point)
                self._select_modifiers = Qt.NoModifier
            elif self.tool_manager.current_tool_type == ToolType.POLYGON:
                # Do not finish polygon on simple release
                pass
            else:
                self.tool_manager.finish_tool(point)
            if self.tool_manager.current_tool_type != ToolType.POLYGON:
                self.tool_manager.cancel_tool()
            self.update()

    def mouseDoubleClickEvent(self, event):
        try:
            if event.button() == Qt.LeftButton:
                point = QPoint(event.x(), event.y())
                if self.tool_manager.current_tool_type == ToolType.POLYGON:
                    self.tool_manager.finish_tool(point)
                    self.tool_manager.cancel_tool()
                    return
                # Prefer component first; if none, then segment
                comp = self._hit_test_component(point)
                if comp is not None and isinstance(comp, dict):
                    comp.setdefault('type', 'component')
                    self.element_double_clicked.emit(comp)
                    return
                hit = self._hit_test_segment(point)
                if hit is not None:
                    seg = hit.get('segment')
                    if isinstance(seg, dict):
                        seg.setdefault('type', 'segment')
                        self.element_double_clicked.emit(seg)
                        return
        finally:
            super().mouseDoubleClickEvent(event)
            
    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Escape:
            self.tool_manager.cancel_tool()
            if self.tool_manager.current_tool_type == ToolType.SELECT:
                self._clear_selection()
            self.update()
            
    # ---------------------- Element lifecycle ----------------------
    def handle_element_created(self, element_data):
        element_type = element_data.get('type')
        if element_type == 'rectangle':
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
            self._base_dirty = True

        elif element_type == 'polygon':
            try:
                from calculations.geometry import compute_polygon_metrics
                points = element_data.get('points') or []
                scale_ratio = getattr(self.scale_manager, 'scale_ratio', 1.0)
                metrics = compute_polygon_metrics(points, scale_ratio)
                area_real = metrics.get('area_real', 0.0)
                perim_real = metrics.get('perimeter_real', 0.0)
                element_data.update({
                    'area_real': area_real,
                    'perimeter_real': perim_real,
                    'area_formatted': self.scale_manager.format_area(area_real),
                    'saved_zoom': self._current_zoom_factor
                })
            except Exception as e:
                print(f"DEBUG: polygon metrics error: {e}")
            self.polygons.append(element_data)
            self._base_dirty = True
            
        elif element_type == 'component':
            # Assign unique element ID if not already present
            if '_element_id' not in element_data:
                element_data['_element_id'] = self._generate_element_id()
            self.components.append(element_data)
            self.update_segment_tool_components()
            try:
                self.attach_component_to_nearby_segments(element_data, threshold_px=20)
            except Exception as e:
                print(f"DEBUG: attach_component_to_nearby_segments error: {e}")
            self._base_dirty = True
            print(f"DEBUG: Created component with ID {element_data['_element_id']} at ({element_data.get('x')}, {element_data.get('y')})")
            
        elif element_type == 'segment':
            # Assign unique element ID if not already present
            if '_element_id' not in element_data:
                element_data['_element_id'] = self._generate_element_id()

            # Capture stable endpoint identifiers for robust relinking after reload.
            try:
                from_comp = element_data.get('from_component')
                if isinstance(from_comp, dict):
                    element_data.setdefault('from_element_id', from_comp.get('_element_id'))
                    element_data.setdefault('from_db_component_id', from_comp.get('db_component_id') or from_comp.get('hvac_component_id'))
                to_comp = element_data.get('to_component')
                if isinstance(to_comp, dict):
                    element_data.setdefault('to_element_id', to_comp.get('_element_id'))
                    element_data.setdefault('to_db_component_id', to_comp.get('db_component_id') or to_comp.get('hvac_component_id'))
            except Exception:
                pass

            length_pixels = element_data.get('length_pixels', 0)
            try:
                length_real = self.scale_manager.pixels_to_real(length_pixels)
                element_data['length_real'] = length_real
                element_data['length_formatted'] = self.scale_manager.format_distance(length_real)
            except Exception:
                pass
            self.segments.append(element_data)
            self._base_dirty = True
            print(f"DEBUG: Created segment with ID {element_data['_element_id']} from ({element_data.get('start_x')}, {element_data.get('start_y')}) to ({element_data.get('end_x')}, {element_data.get('end_y')})")
            
        elif element_type == 'measurement':
            length_pixels = element_data.get('length_pixels', 0)
            try:
                length_real = self.scale_manager.pixels_to_real(length_pixels)
                element_data['length_real'] = length_real
                element_data['length_formatted'] = self.scale_manager.format_distance(length_real)
            except Exception:
                length_real = 0
            self.measurements.append(element_data)
            try:
                self.measurement_taken.emit(length_real, self.scale_manager.format_distance(length_real))
            except Exception:
                pass
            
        self.element_created.emit(element_data)
        self.update()
        
    # ---------------------- Painting ----------------------
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        try:
            self.draw_rectangles(painter)
            self.draw_polygons(painter)
            self.draw_components(painter)
            self.draw_segments(painter)
            if self.show_measurements:
                self.draw_measurements(painter)
            if self.show_grid:
                self.draw_grid(painter)
            current_tool = self.tool_manager.get_current_tool()
            if current_tool and current_tool.active:
                current_tool.draw_preview(painter)
            self._draw_selection(painter)
            if self._highlighted_path_id is not None and self._highlighted_path_id in self.path_element_mapping:
                try:
                    mapping = self.path_element_mapping[self._highlighted_path_id]
                    pen = QPen(QColor(255, 215, 0))
                    pen.setWidth(3)
                    painter.setPen(pen)
                    for seg in mapping.get('segments', []):
                        painter.drawLine(int(seg.get('start_x', 0)), int(seg.get('start_y', 0)), int(seg.get('end_x', 0)), int(seg.get('end_y', 0)))
                    # Do not draw components here to avoid intercepting double-click hit tests visually
                except Exception:
                    pass
        except Exception as e:
            print(f"Error drawing overlay: {e}")
            
    def draw_rectangles(self, painter):
        for rect_data in self.rectangles:
            bounds = rect_data['bounds']
            if isinstance(bounds, dict):
                rect = QRect(bounds['x'], bounds['y'], bounds['width'], bounds['height'])
            else:
                rect = bounds
            is_space = rect_data.get('converted_to_space', False)
            if is_space:
                pen = QPen(QColor(34, 139, 34), 3, Qt.SolidLine)
                brush = QBrush(QColor(34, 139, 34, 40))
            else:
                pen = QPen(QColor(0, 120, 215), 2, Qt.SolidLine)
                brush = QBrush(QColor(0, 120, 215, 30))
            painter.setPen(pen)
            painter.setBrush(brush)
            painter.drawRect(rect)
            center_x = rect.center().x()
            center_y = rect.center().y()
            if is_space:
                space_name = rect_data.get('space_name', 'Space')
                area_text = rect_data.get('area_formatted', f"{rect_data.get('area_real', 0):.0f} sf")
                painter.setPen(QPen(Qt.black))
                painter.setFont(QFont("Arial", 9, QFont.Bold))
                painter.drawText(center_x - 40, center_y - 8, space_name)
                painter.setFont(QFont("Arial", 8))
                painter.drawText(center_x - 30, center_y + 8, area_text)

    def draw_polygons(self, painter):
        from PySide6.QtGui import QPolygon
        for poly in self.polygons:
            pts = poly.get('points') or []
            if len(pts) < 3:
                continue
            qpts = [QPoint(int(p.get('x', 0)), int(p.get('y', 0))) for p in pts]
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
        return {
            'rectangles': len(self.rectangles),
            'polygons': len(self.polygons),
            'components': len(self.components),
            'segments': len(self.segments),
            'measurements': len(self.measurements),
            'total_area': sum(r.get('area_real', 0) for r in self.rectangles) + sum(p.get('area_real', 0) for p in self.polygons),
            'total_duct_length': sum(seg.get('length_real', 0) for seg in self.segments),
        }
    
    def get_elements_data(self):
        for lst in (self.rectangles, self.polygons, self.components, self.segments, self.measurements):
            for item in lst:
                item['saved_zoom'] = self._current_zoom_factor
        return {
            'rectangles': self.rectangles.copy(),
            'polygons': self.polygons.copy(),
            'components': self.components.copy(),
            'segments': self.segments.copy(),
            'measurements': self.measurements.copy(),
        }
        
    def load_elements_data(self, data):
        # Reset base caches
        self._base_rectangles = []
        self._base_polygons = []
        self._base_components = []
        self._base_segments = []
        self._base_measurements = []

        # Rectangles
        rectangles = data.get('rectangles', [])
        for rect_data in rectangles:
            bounds = rect_data.get('bounds')
            if isinstance(bounds, dict):
                rect_data['bounds'] = QRect(bounds['x'], bounds['y'], bounds['width'], bounds['height'])
            try:
                z = rect_data.get('saved_zoom') or 1.0
                self._base_rectangles.append({
                    **rect_data,
                    'x': int(rect_data.get('x', 0) / z),
                    'y': int(rect_data.get('y', 0) / z),
                    'width': int(rect_data.get('width', 0) / z),
                    'height': int(rect_data.get('height', 0) / z),
                })
            except Exception:
                pass
        self.rectangles = rectangles

        # Polygons
        self.polygons = data.get('polygons', [])
        try:
            for poly in self.polygons:
                z = poly.get('saved_zoom') or 1.0
                bp = poly.copy()
                pts = []
                for p in poly.get('points', []) or []:
                    pts.append({'x': int(p.get('x', 0) / z), 'y': int(p.get('y', 0) / z)})
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

        # Components/segments/measurements
        self.components = data.get('components', [])
        self.segments = data.get('segments', [])
        self.measurements = data.get('measurements', [])

        # Ensure components have a usable/stable element id for in-memory linking
        # and relink segment endpoint component references to canonical component dicts.
        try:
            import time
            start_time = time.time()
            print("\n=== ELEMENT MATCHING DEBUG: Starting Element ID Assignment ===")
            print(f"DEBUG: Processing {len(self.components or [])} components for element ID assignment")

            # Assign deterministic element IDs when possible (DB-backed), else generate.
            for i, comp in enumerate(self.components or []):
                if not isinstance(comp, dict):
                    print(f"DEBUG: Component {i} is not a dict, skipping: {type(comp)}")
                    continue

                existing_elem_id = comp.get('_element_id')
                db_id = comp.get('db_component_id') or comp.get('hvac_component_id')
                comp_id = comp.get('id')
                comp_type = comp.get('component_type', 'unknown')
                comp_pos = f"({comp.get('x', 0)}, {comp.get('y', 0)})"

                print(f"DEBUG: Component {i} [{comp_type}] at {comp_pos}:")
                print(f"  - Existing element_id: {existing_elem_id}")
                print(f"  - DB ID: {db_id}")
                print(f"  - Component ID: {comp_id}")

                if existing_elem_id:
                    print(f"  -> SKIPPED: Already has element_id '{existing_elem_id}'")
                    continue

                if db_id is not None:
                    new_elem_id = f"dbcomp_{db_id}"
                    comp['_element_id'] = new_elem_id
                    print(f"  -> ASSIGNED DB-based element_id: '{new_elem_id}'")
                elif comp_id is not None:
                    new_elem_id = f"de_{comp_id}"
                    comp['_element_id'] = new_elem_id
                    print(f"  -> ASSIGNED component-based element_id: '{new_elem_id}'")
                else:
                    new_elem_id = self._generate_element_id()
                    comp['_element_id'] = new_elem_id
                    print(f"  -> ASSIGNED generated element_id: '{new_elem_id}'")

            # Index components for fast lookup
            print("\n=== ELEMENT MATCHING DEBUG: Building Component Indexes ===")
            index_by_elem_id: dict[str, dict] = {}
            index_by_db_id: dict[object, dict] = {}

            for i, comp in enumerate(self.components or []):
                if not isinstance(comp, dict):
                    print(f"DEBUG: Index - Component {i} not dict, skipping")
                    continue

                eid = comp.get('_element_id')
                db_id = comp.get('db_component_id') or comp.get('hvac_component_id')
                comp_type = comp.get('component_type', 'unknown')

                if eid:
                    index_by_elem_id[str(eid)] = comp
                    print(f"DEBUG: Index - Added to elem_id index: '{eid}' -> {comp_type}")

                if db_id is not None:
                    index_by_db_id[db_id] = comp
                    print(f"DEBUG: Index - Added to db_id index: '{db_id}' -> {comp_type}")

                if not eid and db_id is None:
                    print(f"DEBUG: Index - WARNING: Component {i} [{comp_type}] has no indexable IDs")

            print(f"DEBUG: Index - Built elem_id index with {len(index_by_elem_id)} entries")
            print(f"DEBUG: Index - Built db_id index with {len(index_by_db_id)} entries")
            print(f"DEBUG: Index - elem_id keys: {list(index_by_elem_id.keys())}")
            print(f"DEBUG: Index - db_id keys: {list(index_by_db_id.keys())}")

            indexing_time = time.time()
            print(f"DEBUG: PERFORMANCE - Element ID assignment and indexing took {(indexing_time - start_time)*1000:.1f}ms")

            def _extract_endpoint_ids(seg: dict, key_prefix: str) -> tuple[Optional[str], Optional[object]]:
                """Return (element_id, db_component_id) for endpoint."""
                seg_desc = f"{seg.get('start_x', 0)},{seg.get('start_y', 0)} -> {seg.get('end_x', 0)},{seg.get('end_y', 0)}"
                print(f"DEBUG: Extracting {key_prefix} endpoint IDs for segment [{seg_desc}]")

                elem_id = seg.get(f"{key_prefix}_element_id")
                db_id = seg.get(f"{key_prefix}_db_component_id")
                print(f"  - Direct {key_prefix}_element_id: {elem_id}")
                print(f"  - Direct {key_prefix}_db_component_id: {db_id}")

                # Back-compat: pull from embedded component dict if present
                embedded = seg.get(f"{key_prefix}_component")
                if isinstance(embedded, dict):
                    print(f"  - Found embedded {key_prefix}_component: {embedded.get('component_type', 'unknown')}")
                    if elem_id is None:
                        elem_id = embedded.get('_element_id')
                        print(f"  - Extracted element_id from embedded: {elem_id}")
                    if db_id is None:
                        db_id = embedded.get('db_component_id') or embedded.get('hvac_component_id')
                        print(f"  - Extracted db_id from embedded: {db_id}")
                else:
                    print(f"  - No embedded {key_prefix}_component found")

                # Normalize element id to string to match index
                elem_id_str = str(elem_id) if elem_id is not None else None
                print(f"  -> Final normalized IDs: elem_id='{elem_id_str}', db_id='{db_id}'")
                return elem_id_str, db_id

            def _resolve_component_for_endpoint(seg: dict, key_prefix: str) -> Optional[dict]:
                seg_desc = f"{seg.get('start_x', 0)},{seg.get('start_y', 0)} -> {seg.get('end_x', 0)},{seg.get('end_y', 0)}"
                print(f"\nDEBUG: Resolving {key_prefix} endpoint for segment [{seg_desc}]")

                elem_id_str, db_id = _extract_endpoint_ids(seg, key_prefix)

                # Strategy 1: Element ID lookup
                if elem_id_str and elem_id_str in index_by_elem_id:
                    resolved = index_by_elem_id[elem_id_str]
                    comp_type = resolved.get('component_type', 'unknown')
                    comp_pos = f"({resolved.get('x', 0)}, {resolved.get('y', 0)})"
                    print(f"  -> STRATEGY 1 SUCCESS: Element ID lookup '{elem_id_str}' -> {comp_type} at {comp_pos}")
                    return resolved
                elif elem_id_str:
                    print(f"  -> STRATEGY 1 FAILED: Element ID '{elem_id_str}' not found in index")
                else:
                    print(f"  -> STRATEGY 1 SKIPPED: No element ID available")

                # Strategy 2: DB ID lookup
                if db_id is not None and db_id in index_by_db_id:
                    resolved = index_by_db_id[db_id]
                    comp_type = resolved.get('component_type', 'unknown')
                    comp_pos = f"({resolved.get('x', 0)}, {resolved.get('y', 0)})"
                    print(f"  -> STRATEGY 2 SUCCESS: DB ID lookup '{db_id}' -> {comp_type} at {comp_pos}")
                    return resolved
                elif db_id is not None:
                    print(f"  -> STRATEGY 2 FAILED: DB ID '{db_id}' not found in index")
                else:
                    print(f"  -> STRATEGY 2 SKIPPED: No DB ID available")

                # Strategy 3: Coordinate/type matching (last resort)
                embedded = seg.get(f"{key_prefix}_component")
                if isinstance(embedded, dict):
                    emb_type = embedded.get('component_type', 'unknown')
                    emb_pos = f"({embedded.get('x', 0)}, {embedded.get('y', 0)})"
                    print(f"  -> STRATEGY 3: Coordinate matching for embedded {emb_type} at {emb_pos}")

                    match_attempts = 0
                    for c in (self.components or []):
                        if isinstance(c, dict):
                            match_attempts += 1
                            if self._components_match(c, embedded):
                                comp_type = c.get('component_type', 'unknown')
                                comp_pos = f"({c.get('x', 0)}, {c.get('y', 0)})"
                                print(f"    -> STRATEGY 3 SUCCESS: Coordinate match after {match_attempts} attempts -> {comp_type} at {comp_pos}")
                                return c
                    print(f"    -> STRATEGY 3 FAILED: No coordinate match after {match_attempts} attempts")
                else:
                    print(f"  -> STRATEGY 3 SKIPPED: No embedded component for coordinate matching")

                print(f"  -> ALL STRATEGIES FAILED: No component found for {key_prefix} endpoint")
                return None

            print(f"\n=== ELEMENT MATCHING DEBUG: Processing {len(self.segments or [])} segments ===\n")

            for seg_idx, seg in enumerate(self.segments or []):
                if not isinstance(seg, dict):
                    print(f"DEBUG: Segment {seg_idx} is not a dict, skipping")
                    continue

                seg_desc = f"{seg.get('start_x', 0)},{seg.get('start_y', 0)} -> {seg.get('end_x', 0)},{seg.get('end_y', 0)}"
                print(f"\n--- Processing Segment {seg_idx} [{seg_desc}] ---")

                # Resolve canonical endpoint components
                print("\n** Resolving FROM endpoint **")
                from_canon = _resolve_component_for_endpoint(seg, 'from')
                if from_canon is not None:
                    print(f"DEBUG: FROM endpoint resolved successfully")
                    seg['from_component'] = from_canon
                    seg['from_element_id'] = from_canon.get('_element_id')
                    seg['from_db_component_id'] = from_canon.get('db_component_id') or from_canon.get('hvac_component_id')

                    # Keep coordinates consistent with the linked component
                    try:
                        old_start_x = seg.get('start_x', 0)
                        old_start_y = seg.get('start_y', 0)
                        new_start_x = int(from_canon.get('x', seg.get('start_x', 0)))
                        new_start_y = int(from_canon.get('y', seg.get('start_y', 0)))

                        seg['start_x'] = new_start_x
                        seg['start_y'] = new_start_y

                        if old_start_x != new_start_x or old_start_y != new_start_y:
                            print(f"  -> COORDINATE SYNC: start ({old_start_x}, {old_start_y}) -> ({new_start_x}, {new_start_y})")
                        else:
                            print(f"  -> COORDINATE SYNC: start coordinates unchanged ({new_start_x}, {new_start_y})")
                    except Exception as e:
                        print(f"  -> COORDINATE SYNC ERROR: Failed to sync start coordinates: {e}")
                else:
                    print(f"DEBUG: FROM endpoint resolution failed")

                print("\n** Resolving TO endpoint **")
                to_canon = _resolve_component_for_endpoint(seg, 'to')
                if to_canon is not None:
                    print(f"DEBUG: TO endpoint resolved successfully")
                    seg['to_component'] = to_canon
                    seg['to_element_id'] = to_canon.get('_element_id')
                    seg['to_db_component_id'] = to_canon.get('db_component_id') or to_canon.get('hvac_component_id')

                    try:
                        old_end_x = seg.get('end_x', 0)
                        old_end_y = seg.get('end_y', 0)
                        new_end_x = int(to_canon.get('x', seg.get('end_x', 0)))
                        new_end_y = int(to_canon.get('y', seg.get('end_y', 0)))

                        seg['end_x'] = new_end_x
                        seg['end_y'] = new_end_y

                        if old_end_x != new_end_x or old_end_y != new_end_y:
                            print(f"  -> COORDINATE SYNC: end ({old_end_x}, {old_end_y}) -> ({new_end_x}, {new_end_y})")
                        else:
                            print(f"  -> COORDINATE SYNC: end coordinates unchanged ({new_end_x}, {new_end_y})")
                    except Exception as e:
                        print(f"  -> COORDINATE SYNC ERROR: Failed to sync end coordinates: {e}")
                else:
                    print(f"DEBUG: TO endpoint resolution failed")

                # Summary for this segment
                final_desc = f"{seg.get('start_x', 0)},{seg.get('start_y', 0)} -> {seg.get('end_x', 0)},{seg.get('end_y', 0)}"
                from_status = "LINKED" if from_canon else "UNLINKED"
                to_status = "LINKED" if to_canon else "UNLINKED"
                print(f"DEBUG: Segment {seg_idx} final state: [{final_desc}] FROM:{from_status} TO:{to_status}")

            segment_processing_time = time.time()
            print(f"DEBUG: PERFORMANCE - Segment processing took {(segment_processing_time - indexing_time)*1000:.1f}ms")
        except Exception as e:
            import traceback
            print(f"DEBUG: CRITICAL ERROR - Segment/component relink on load failed: {e}")
            print(f"DEBUG: Full traceback:")
            traceback.print_exc()
            print(f"DEBUG: Attempting to continue with partial element matching...")

            # Try to provide partial state information for debugging
            try:
                print(f"DEBUG: Current state - Components: {len(self.components or [])}, Segments: {len(self.segments or [])}")
                if hasattr(self, 'components') and self.components:
                    comp_types = [c.get('component_type', 'unknown') if isinstance(c, dict) else str(type(c)) for c in self.components[:3]]
                    print(f"DEBUG: Sample component types: {comp_types}")
            except Exception as debug_e:
                print(f"DEBUG: Could not gather state information: {debug_e}")

        print("\n=== ELEMENT MATCHING DEBUG: Building Base Element Cache ===\n")
        try:
            # Build base components cache with zoom normalization
            print(f"DEBUG: Processing {len(self.components)} components for base cache")
            for i, comp in enumerate(self.components):
                if not isinstance(comp, dict):
                    print(f"DEBUG: Base cache - Component {i} not dict, skipping")
                    continue

                z = comp.get('saved_zoom') or 1.0
                bc = comp.copy()
                orig_x, orig_y = comp.get('x', 0), comp.get('y', 0)
                bc['x'] = int(orig_x / z)
                bc['y'] = int(orig_y / z)
                self._base_components.append(bc)

                comp_type = comp.get('component_type', 'unknown')
                elem_id = comp.get('_element_id', 'none')
                print(f"DEBUG: Base cache - Component {i} [{comp_type}] elem_id:{elem_id} zoom:{z} coords:({orig_x},{orig_y})->({bc['x']},{bc['y']})")

            # Build base segments cache with zoom normalization
            print(f"DEBUG: Processing {len(self.segments)} segments for base cache")
            for i, seg in enumerate(self.segments):
                if not isinstance(seg, dict):
                    print(f"DEBUG: Base cache - Segment {i} not dict, skipping")
                    continue

                z = seg.get('saved_zoom') or 1.0
                bs = seg.copy()
                orig_coords = (seg.get('start_x', 0), seg.get('start_y', 0), seg.get('end_x', 0), seg.get('end_y', 0))
                bs['start_x'] = int(orig_coords[0] / z)
                bs['start_y'] = int(orig_coords[1] / z)
                bs['end_x'] = int(orig_coords[2] / z)
                bs['end_y'] = int(orig_coords[3] / z)
                self._base_segments.append(bs)

                elem_id = seg.get('_element_id', 'none')
                new_coords = (bs['start_x'], bs['start_y'], bs['end_x'], bs['end_y'])
                print(f"DEBUG: Base cache - Segment {i} elem_id:{elem_id} zoom:{z} coords:{orig_coords}->{new_coords}")

            # Build base measurements cache with zoom normalization
            print(f"DEBUG: Processing {len(self.measurements)} measurements for base cache")
            for i, meas in enumerate(self.measurements):
                if not isinstance(meas, dict):
                    print(f"DEBUG: Base cache - Measurement {i} not dict, skipping")
                    continue

                z = meas.get('saved_zoom') or 1.0
                bm = meas.copy()
                orig_coords = (meas.get('start_x', 0), meas.get('start_y', 0), meas.get('end_x', 0), meas.get('end_y', 0))
                bm['start_x'] = int(orig_coords[0] / z)
                bm['start_y'] = int(orig_coords[1] / z)
                bm['end_x'] = int(orig_coords[2] / z)
                bm['end_y'] = int(orig_coords[3] / z)
                self._base_measurements.append(bm)

                elem_id = meas.get('_element_id', 'none')
                new_coords = (bm['start_x'], bm['start_y'], bm['end_x'], bm['end_y'])
                print(f"DEBUG: Base cache - Measurement {i} elem_id:{elem_id} zoom:{z} coords:{orig_coords}->{new_coords}")

            print(f"DEBUG: Base cache built - {len(self._base_components)} components, {len(self._base_segments)} segments, {len(self._base_measurements)} measurements")

            base_cache_time = time.time()
            print(f"DEBUG: PERFORMANCE - Base cache construction took {(base_cache_time - segment_processing_time)*1000:.1f}ms")
        except Exception as e:
            import traceback
            print(f"DEBUG: CRITICAL ERROR - Base cache construction failed: {e}")
            print(f"DEBUG: Full traceback:")
            traceback.print_exc()

        try:
            print(f"\nDEBUG: Setting zoom factor to {self._current_zoom_factor}")
            self._base_dirty = False
            self.set_zoom_factor(self._current_zoom_factor)
            total_time = time.time()
            print(f"DEBUG: PERFORMANCE - Total element matching time: {(total_time - start_time)*1000:.1f}ms")
            print(f"DEBUG: Element matching and initialization completed successfully")
        except Exception as e:
            import traceback
            print(f"DEBUG: CRITICAL ERROR - Zoom factor setting failed: {e}")
            print(f"DEBUG: Full traceback:")
            traceback.print_exc()
            print(f"DEBUG: Attempting to continue with default zoom...")

        # State consistency validation
        self._validate_element_state_consistency()

        # Generate comprehensive debug report
        self.generate_element_matching_debug_report()

        print("\n=== ELEMENT MATCHING DEBUG: Element Matching Process Complete ===\n")

        # Relink any segment endpoints that lost their component references during reload
        print("DEBUG: Starting post-load segment endpoint relinking...")
        try:
            self.relink_all_segment_endpoints(threshold_px=20)
        except Exception:
            pass
        
        self.update()
    
    # ---------------------- Mutations/clears ----------------------
    def clear_all_elements(self):
        self.rectangles.clear()
        self.polygons.clear()
        self.components.clear()
        self.segments.clear()
        self.measurements.clear()
        self._base_rectangles.clear()
        self._base_polygons.clear()
        self._base_components.clear()
        self._base_segments.clear()
        self._base_measurements.clear()
        self._base_dirty = True
        self.update()
    
    def clear_unsaved_elements(self):
        try:
            # Skip clearing if temporarily disabled (e.g., during save operations)
            if self._clearing_disabled:
                print("DEBUG: Clearing disabled, skipping clear_unsaved_elements")
                return
            
            # Preserve elements registered to any saved path; clear only transient ones
            # NOTE: Use registration matching (IDs/coords) instead of object identity,
            # because overlay elements can be reloaded into new dict instances.
            keep_components = set()
            keep_segments = set()
            
            print(f"DEBUG: clear_unsaved_elements - Current paths in mapping: {list(self.path_element_mapping.keys())}")
            
            for path_id, mapping in self.path_element_mapping.items():
                path_components = mapping.get('components', []) or []
                path_segments = mapping.get('segments', []) or []
                
                print(f"DEBUG: Path {path_id} has {len(path_components)} components and {len(path_segments)} segments")
                
                for c in path_components:
                    keep_components.add(id(c))
                    print(f"DEBUG: Keeping component {id(c)} for path {path_id}")
                for s in path_segments:
                    keep_segments.add(id(s))
                    print(f"DEBUG: Keeping segment {id(s)} for path {path_id}")

            print(f"DEBUG: Before clearing - {len(self.components)} components, {len(self.segments)} segments")
            print(f"DEBUG: Keeping {len(keep_components)} components, {len(keep_segments)} segments")
            
            # Filter out unsaved elements using registration matching
            original_components_count = len(self.components)
            original_segments_count = len(self.segments)
            components_before = list(self.components)
            segments_before = list(self.segments)
            
            def _matches_any_segment_endpoint(comp: dict, tol: float = 8.0) -> bool:
                try:
                    cx = float(comp.get("x") or 0)
                    cy = float(comp.get("y") or 0)
                except Exception:
                    return False
                for seg in segments_before:
                    try:
                        sx = float(seg.get("start_x") or 0)
                        sy = float(seg.get("start_y") or 0)
                        ex = float(seg.get("end_x") or 0)
                        ey = float(seg.get("end_y") or 0)
                    except Exception:
                        continue
                    if (abs(cx - sx) <= tol and abs(cy - sy) <= tol) or (abs(cx - ex) <= tol and abs(cy - ey) <= tol):
                        return True
                return False

            self.components = [
                c for c in self.components
                if self._is_component_registered_any_path(c) or _matches_any_segment_endpoint(c)
            ]
            self.segments = [s for s in self.segments if self._is_segment_registered_any_path(s)]
            
            # Recompute keep counts based on matching (for logging)
            keep_components = {id(c) for c in self.components}
            keep_segments = {id(s) for s in self.segments}
            
            print(f"DEBUG: After clearing - {len(self.components)} components ({original_components_count - len(self.components)} removed)")
            print(f"DEBUG: After clearing - {len(self.segments)} segments ({original_segments_count - len(self.segments)} removed)")

            # Do not touch rectangles/polygons; measurements have their own clearer
            self._base_components.clear()
            self._base_segments.clear()
            self._base_dirty = True
            self.update_segment_tool_components()
            self.update()
        except Exception as e:
            print(f"ERROR in clear_unsaved_elements: {e}")
            # Fallback: keep state as-is to avoid losing data on error
            self.update()

    def _clear_selection(self):
        self._selected_components.clear()
        self._selected_segments.clear()
        self._selection_rect = None
        self._drag_active = False
        self._drag_last_point = None
        self._hit_target = None
        self.update()
    
    # ---------------------- Drawing primitives ----------------------
    def draw_components(self, painter):
        drawn_count = 0
        skipped_count = 0
        for comp in self.components:
            # Visibility rules:
            # - path_only_mode: ONLY show components in visible paths (strict filtering)
            # - normal mode: show all EXCEPT components in hidden_paths
            if self.path_only_mode:
                if not self._is_component_in_visible_path(comp):
                    skipped_count += 1
                    continue
            elif self.hidden_paths:
                # Check if this component belongs to a hidden path
                if self._is_component_in_hidden_path(comp):
                    skipped_count += 1
                    continue
            # Show the component
            drawn_count += 1
            x = comp.get('x', 0)
            y = comp.get('y', 0)
            comp_type = comp.get('component_type', 'unknown')
            
            # Check for highlighting from analysis panel
            is_highlighted = self._is_element_highlighted(comp, 'component')
            is_selected = self._is_element_selected(comp, 'component')
            
            # Determine base color
            if comp_type == 'fan':
                color = QColor(255, 100, 100)
            elif comp_type == 'grille':
                color = QColor(100, 255, 100)
            elif comp_type == 'branch':
                color = QColor(100, 100, 255)
            elif comp_type == 'elbow':
                color = QColor(255, 255, 100)
            else:
                color = QColor(150, 150, 150)
            
            # Apply highlighting/selection styling
            if is_selected:
                # Selected: larger, with bright cyan outline
                pen = QPen(QColor(0, 188, 212), 4)
                brush = QBrush(color)
                size = 14
            elif is_highlighted:
                # Highlighted: pulsing effect with bright outline
                pen = QPen(QColor(33, 150, 243), 3)
                brush = QBrush(color.lighter(120))
                size = 12
            else:
                pen = QPen(color, 2)
                brush = QBrush(color)
                size = 8
            
            painter.setPen(pen)
            painter.setBrush(brush)
            painter.drawEllipse(x - size, y - size, size * 2, size * 2)
            
            # Draw text
            painter.setPen(QPen(Qt.black))
            painter.setFont(QFont("Arial", 8))
            painter.drawText(x - 15, y + 25, comp_type)
            
            # Draw highlight ring for selected elements
            if is_selected:
                painter.setPen(QPen(QColor(0, 188, 212, 128), 2, Qt.DashLine))
                painter.setBrush(Qt.NoBrush)
                painter.drawEllipse(x - size - 4, y - size - 4, (size + 4) * 2, (size + 4) * 2)

    def draw_segments(self, painter):
        drawn_count = 0
        skipped_count = 0
        for seg in self.segments:
            # Visibility rules (same as components):
            # - path_only_mode: ONLY show segments in visible paths (strict filtering)
            # - normal mode: show all EXCEPT segments in hidden_paths
            if self.path_only_mode:
                if not self._is_segment_in_visible_path(seg):
                    skipped_count += 1
                    continue
            elif self.hidden_paths:
                # Check if this segment belongs to a hidden path
                if self._is_segment_in_hidden_path(seg):
                    skipped_count += 1
                    continue
            # Show the segment
            drawn_count += 1
            start_x = seg.get('start_x', 0)
            start_y = seg.get('start_y', 0)
            end_x = seg.get('end_x', 0)
            end_y = seg.get('end_y', 0)
            
            # Check for highlighting from analysis panel
            is_highlighted = self._is_element_highlighted(seg, 'segment')
            is_selected = self._is_element_selected(seg, 'segment')
            
            # Apply styling based on state
            if is_selected:
                # Selected: thick cyan line
                pen = QPen(QColor(0, 188, 212), 6)
            elif is_highlighted:
                # Highlighted: bright blue, slightly thicker
                pen = QPen(QColor(33, 150, 243), 5)
            else:
                # Default orange
                pen = QPen(QColor(255, 165, 0), 3)
            
            painter.setPen(pen)
            painter.drawLine(start_x, start_y, end_x, end_y)
            
            # Draw midpoint marker for highlighted/selected segments
            mid_x = (start_x + end_x) // 2
            mid_y = (start_y + end_y) // 2
            
            if is_highlighted or is_selected:
                marker_color = QColor(0, 188, 212) if is_selected else QColor(33, 150, 243)
                painter.setPen(QPen(marker_color, 2))
                painter.setBrush(QBrush(marker_color))
                painter.drawEllipse(mid_x - 4, mid_y - 4, 8, 8)
            
            # Draw length text
            length_text = seg.get('length_formatted', f"{seg.get('length_real', 0):.1f} ft")
            painter.setPen(QPen(Qt.black))
            painter.setFont(QFont("Arial", 8))
            painter.drawText(mid_x - 15, mid_y - 5, length_text)

    def draw_measurements(self, painter):
        for meas in self.measurements:
            start_x = meas.get('start_x', 0)
            start_y = meas.get('start_y', 0)
            end_x = meas.get('end_x', 0)
            end_y = meas.get('end_y', 0)
            pen = QPen(QColor(255, 0, 255), 2)
            painter.setPen(pen)
            painter.drawLine(start_x, start_y, end_x, end_y)
            mid_x = (start_x + end_x) // 2
            mid_y = (start_y + end_y) // 2
            length_text = meas.get('length_formatted', f"{meas.get('length_real', 0):.1f} ft")
            painter.setPen(QPen(Qt.black))
            painter.setFont(QFont("Arial", 8))
            painter.drawText(mid_x - 15, mid_y - 5, length_text)

    def _is_component_in_visible_path(self, comp):
        """Check if component is in a visible path using ID or coordinate matching.
        
        Uses a priority-based matching approach:
        1. DB component ID (most reliable for saved paths)
        2. Element ID (reliable for session-created elements)
        3. Coordinate/type matching (fallback for reloaded elements)
        """
        comp_db_id = comp.get('db_component_id') or comp.get('hvac_component_id')
        comp_elem_id = comp.get('_element_id')
        
        for path_id in self.visible_paths:
            mapping = self.path_element_mapping.get(path_id, {})
            for registered_comp in mapping.get('components', []):
                # Priority 1: DB component ID match (survives reload)
                reg_db_id = registered_comp.get('db_component_id') or registered_comp.get('hvac_component_id')
                if comp_db_id and reg_db_id and comp_db_id == reg_db_id:
                    return True
                
                # Priority 2: Element ID match (session-stable)
                if comp_elem_id and registered_comp.get('_element_id') == comp_elem_id:
                    return True
                
                # Priority 3: Coordinate/type matching (works after reload)
                if self._components_match(comp, registered_comp):
                    return True
        return False
    
    def _is_segment_in_visible_path(self, seg):
        """Check if segment is in a visible path using ID or coordinate matching.
        
        Uses a priority-based matching approach:
        1. DB segment ID (most reliable for saved paths)
        2. Element ID (reliable for session-created elements)
        3. Coordinate matching (fallback for reloaded elements)
        """
        seg_db_id = seg.get('db_segment_id') or seg.get('hvac_segment_id')
        seg_elem_id = seg.get('_element_id')
        
        for path_id in self.visible_paths:
            mapping = self.path_element_mapping.get(path_id, {})
            for registered_seg in mapping.get('segments', []):
                # Priority 1: DB segment ID match (survives reload)
                reg_db_id = registered_seg.get('db_segment_id') or registered_seg.get('hvac_segment_id')
                if seg_db_id and reg_db_id and seg_db_id == reg_db_id:
                    return True
                
                # Priority 2: Element ID match (session-stable)
                if seg_elem_id and registered_seg.get('_element_id') == seg_elem_id:
                    return True
                
                # Priority 3: Coordinate matching (works after reload)
                if self._segments_match(seg, registered_seg):
                    return True
        return False

    def _is_component_in_hidden_path(self, comp):
        """Check if component should be hidden due to hidden paths.

        Rule: hide only if the component is registered to at least one hidden path
        AND is not registered to any non-hidden path. This prevents shared
        components from disappearing when a different path is hidden.

        Uses priority-based matching:
        1. DB component ID (survives reload)
        2. Element ID (session-stable)
        3. Coordinate/type matching (fallback)
        """
        comp_db_id = comp.get('db_component_id') or comp.get('hvac_component_id')
        comp_elem_id = comp.get('_element_id')
        hidden_match = False
        visible_match = False

        for path_id, mapping in self.path_element_mapping.items():
            for registered_comp in mapping.get('components', []):
                matched = False
                
                # Priority 1: DB component ID match (survives reload)
                reg_db_id = registered_comp.get('db_component_id') or registered_comp.get('hvac_component_id')
                if comp_db_id and reg_db_id and comp_db_id == reg_db_id:
                    matched = True
                
                # Priority 2: Element ID match (session-stable)
                elif comp_elem_id and registered_comp.get('_element_id') == comp_elem_id:
                    matched = True
                
                # Priority 3: Coordinate/type matching (works after reload)
                elif self._components_match(comp, registered_comp):
                    matched = True
                
                if matched:
                    if path_id in self.hidden_paths:
                        hidden_match = True
                    else:
                        visible_match = True

        should_hide = hidden_match and not visible_match
        return should_hide

    def _is_segment_in_hidden_path(self, seg):
        """Check if segment should be hidden due to hidden paths.

        Rule: hide only if the segment is registered to at least one hidden path
        AND is not registered to any non-hidden path. This prevents shared
        segments from disappearing when a different path is hidden.

        Uses priority-based matching:
        1. DB segment ID (survives reload)
        2. Element ID (session-stable)
        3. Coordinate matching (fallback)
        """
        seg_db_id = seg.get('db_segment_id') or seg.get('hvac_segment_id')
        seg_elem_id = seg.get('_element_id')
        hidden_match = False
        visible_match = False

        for path_id, mapping in self.path_element_mapping.items():
            for registered_seg in mapping.get('segments', []):
                matched = False
                
                # Priority 1: DB segment ID match (survives reload)
                reg_db_id = registered_seg.get('db_segment_id') or registered_seg.get('hvac_segment_id')
                if seg_db_id and reg_db_id and seg_db_id == reg_db_id:
                    matched = True
                
                # Priority 2: Element ID match (session-stable)
                elif seg_elem_id and registered_seg.get('_element_id') == seg_elem_id:
                    matched = True
                
                # Priority 3: Coordinate matching (works after reload)
                elif self._segments_match(seg, registered_seg):
                    matched = True
                
                if matched:
                    if path_id in self.hidden_paths:
                        hidden_match = True
                    else:
                        visible_match = True

        return hidden_match and not visible_match

    def _is_component_registered_any_path(self, comp):
        """Check if component is registered to any path using priority-based matching.
        
        Uses:
        1. DB component ID (survives reload)
        2. Element ID (session-stable)
        3. Coordinate/type matching (fallback)
        """
        comp_db_id = comp.get('db_component_id') or comp.get('hvac_component_id')
        comp_elem_id = comp.get('_element_id')
        
        for mapping in self.path_element_mapping.values():
            for registered_comp in mapping.get('components', []):
                # Priority 1: DB component ID match
                reg_db_id = registered_comp.get('db_component_id') or registered_comp.get('hvac_component_id')
                if comp_db_id and reg_db_id and comp_db_id == reg_db_id:
                    return True
                
                # Priority 2: Element ID match
                if comp_elem_id and registered_comp.get('_element_id') == comp_elem_id:
                    return True
                
                # Priority 3: Coordinate/type matching
                if self._components_match(comp, registered_comp):
                    return True
        return False

    def _is_segment_registered_any_path(self, seg):
        """Check if segment is registered to any path using priority-based matching.
        
        Uses:
        1. DB segment ID (survives reload)
        2. Element ID (session-stable)
        3. Coordinate matching (fallback)
        """
        seg_db_id = seg.get('db_segment_id') or seg.get('hvac_segment_id')
        seg_elem_id = seg.get('_element_id')
        
        for mapping in self.path_element_mapping.values():
            for registered_seg in mapping.get('segments', []):
                # Priority 1: DB segment ID match
                reg_db_id = registered_seg.get('db_segment_id') or registered_seg.get('hvac_segment_id')
                if seg_db_id and reg_db_id and seg_db_id == reg_db_id:
                    return True
                
                # Priority 2: Element ID match
                if seg_elem_id and registered_seg.get('_element_id') == seg_elem_id:
                    return True
                
                # Priority 3: Coordinate matching
                if self._segments_match(seg, registered_seg):
                    return True
        return False

    def _draw_selection(self, painter):
        if self._selection_rect:
            pen = QPen(QColor(100, 100, 255), 1, Qt.DashLine)
            brush = QBrush(QColor(100, 100, 255, 30))
            painter.setPen(pen)
            painter.setBrush(brush)
            painter.drawRect(self._selection_rect)
        for comp in self._selected_components:
            x = comp.get('x', 0)
            y = comp.get('y', 0)
            pen = QPen(QColor(255, 255, 0), 3)
            painter.setPen(pen)
            painter.setBrush(QBrush(Qt.NoBrush))
            painter.drawEllipse(x - 12, y - 12, 24, 24)
        for seg in self._selected_segments:
            start_x = seg.get('start_x', 0)
            start_y = seg.get('start_y', 0)
            end_x = seg.get('end_x', 0)
            end_y = seg.get('end_y', 0)
            pen = QPen(QColor(255, 255, 0), 5)
            painter.setPen(pen)
            painter.drawLine(start_x, start_y, end_x, end_y)

    # ---------------------- Select/drag handlers ----------------------
    def _handle_select_press(self, point):
        hit_comp = self._hit_test_component(point)
        hit_seg = self._hit_test_segment(point)
        if hit_comp:
            self._drag_active = True
            self._drag_last_point = point
            self._hit_target = {'type': 'component', 'ref': hit_comp}
            if self._select_modifiers & Qt.ControlModifier:
                if hit_comp in self._selected_components:
                    self._selected_components.remove(hit_comp)
                else:
                    self._selected_components.append(hit_comp)
            else:
                self._selected_components = [hit_comp]
                self._selected_segments.clear()
        elif hit_seg:
            self._drag_active = True
            self._drag_last_point = point
            # Extract the raw segment dict from hit result
            raw_seg = hit_seg.get('segment')
            self._hit_target = {'type': 'segment', 'ref': raw_seg, 'endpoint': hit_seg.get('endpoint')}
            if self._select_modifiers & Qt.ControlModifier:
                # Use raw segment dict for selection (consistent format)
                if raw_seg in self._selected_segments:
                    self._selected_segments.remove(raw_seg)
                else:
                    self._selected_segments.append(raw_seg)
            else:
                # Store raw segment dict (consistent format)
                self._selected_segments = [raw_seg]
                self._selected_components.clear()
        else:
            if not (self._select_modifiers & Qt.ControlModifier):
                self._selected_components.clear()
                self._selected_segments.clear()
            self._selection_rect = QRect(point, point)

    def _handle_select_move(self, point):
        if self._selection_rect:
            self._selection_rect.setBottomRight(point)
            return
        if self._drag_active and self._drag_last_point is not None:
            dx = point.x() - self._drag_last_point.x()
            dy = point.y() - self._drag_last_point.y()
            self._drag_last_point = point
            if self._hit_target and self._hit_target.get('type') == 'component':
                for comp in (self._selected_components or [self._hit_target.get('ref')]):
                    if not isinstance(comp, dict):
                        continue
                    comp['x'] = int(comp.get('x', 0)) + dx
                    comp['y'] = int(comp.get('y', 0)) + dy
                    pos = comp.get('position')
                    if isinstance(pos, dict):
                        pos['x'] = int(pos.get('x', 0)) + dx
                        pos['y'] = int(pos.get('y', 0)) + dy
                    self._update_segments_for_component_move(comp)
                    # Immediately update base coordinates for moved component
                    self._update_component_base_coordinates(comp)
            elif self._hit_target and self._hit_target.get('type') == 'segment':
                seg = self._hit_target.get('ref')
                endpoint = self._hit_target.get('endpoint')
                if isinstance(seg, dict):
                    if endpoint == 'start' or endpoint is None:
                        seg['start_x'] = int(seg.get('start_x', 0)) + dx
                        seg['start_y'] = int(seg.get('start_y', 0)) + dy
                        # Snap start endpoint to nearest component if within threshold
                        self._snap_segment_endpoint_to_component(seg, 'start', self._snap_threshold_px)
                    if endpoint == 'end' or endpoint is None:
                        seg['end_x'] = int(seg.get('end_x', 0)) + dx
                        seg['end_y'] = int(seg.get('end_y', 0)) + dy
                        # Snap end endpoint to nearest component if within threshold
                        self._snap_segment_endpoint_to_component(seg, 'end', self._snap_threshold_px)
                    try:
                        self._recompute_segment_length(seg)
                    except Exception:
                        pass
                    # Update base coordinates for moved segment
                    self._update_segment_base_coordinates(seg)
            self.update()

    def _handle_select_release(self, point):
        if self._selection_rect:
            rect = self._selection_rect.normalized()
            for comp in self.components:
                comp_point = QPoint(comp.get('x', 0), comp.get('y', 0))
                if rect.contains(comp_point):
                    if comp not in self._selected_components:
                        self._selected_components.append(comp)
            for seg in self.segments:
                start_point = QPoint(seg.get('start_x', 0), seg.get('start_y', 0))
                end_point = QPoint(seg.get('end_x', 0), seg.get('end_y', 0))
                if rect.contains(start_point) or rect.contains(end_point):
                    if seg not in self._selected_segments:
                        self._selected_segments.append(seg)
            self._selection_rect = None
        self._drag_active = False
        self._drag_last_point = None
        self._hit_target = None
        self._base_dirty = True
        self.update()

    def _hit_test_component(self, point):
        for comp in self.components:
            comp_x = comp.get('x', 0)
            comp_y = comp.get('y', 0)
            if abs(point.x() - comp_x) <= 16 and abs(point.y() - comp_y) <= 16:
                return comp
        return None

    def _hit_test_segment(self, point):
        for seg in self.segments:
            start_x = seg.get('start_x', 0)
            start_y = seg.get('start_y', 0)
            end_x = seg.get('end_x', 0)
            end_y = seg.get('end_y', 0)
            tolerance = 8
            if abs(point.x() - start_x) <= tolerance and abs(point.y() - start_y) <= tolerance:
                return {'segment': seg, 'endpoint': 'start'}
            if abs(point.x() - end_x) <= tolerance and abs(point.y() - end_y) <= tolerance:
                return {'segment': seg, 'endpoint': 'end'}
            min_x, max_x = min(start_x, end_x) - tolerance, max(start_x, end_x) + tolerance
            min_y, max_y = min(start_y, end_y) - tolerance, max(start_y, end_y) + tolerance
            if min_x <= point.x() <= max_x and min_y <= point.y() <= max_y:
                return {'segment': seg, 'endpoint': None}
        return None

    def _hit_test_space(self, point):
        """Test if point hits a saved space (rectangle or polygon with converted_to_space=True)"""
        # Check rectangles first
        for rect in self.rectangles:
            if rect.get('converted_to_space'):
                bounds = rect.get('bounds')
                if isinstance(bounds, QRect) and bounds.contains(point):
                    return {'type': 'rectangle', 'data': rect}
                elif isinstance(bounds, dict):
                    # Handle dict bounds
                    x = bounds.get('x', 0)
                    y = bounds.get('y', 0)
                    w = bounds.get('width', 0)
                    h = bounds.get('height', 0)
                    if x <= point.x() <= x + w and y <= point.y() <= y + h:
                        return {'type': 'rectangle', 'data': rect}
        
        # Check polygons
        for poly in self.polygons:
            if poly.get('converted_to_space'):
                points = poly.get('points', [])
                if self._point_in_polygon(point, points):
                    return {'type': 'polygon', 'data': poly}
        
        return None

    def _point_in_polygon(self, point, polygon_points):
        """Check if a point is inside a polygon using ray casting algorithm"""
        if not polygon_points or len(polygon_points) < 3:
            return False
        
        px, py = point.x(), point.y()
        n = len(polygon_points)
        inside = False
        
        j = n - 1
        for i in range(n):
            xi = polygon_points[i].get('x', 0)
            yi = polygon_points[i].get('y', 0)
            xj = polygon_points[j].get('x', 0)
            yj = polygon_points[j].get('y', 0)
            
            if ((yi > py) != (yj > py)) and (px < (xj - xi) * (py - yi) / (yj - yi) + xi):
                inside = not inside
            j = i
        
        return inside

    def _update_segments_for_component_move(self, component):
        """Update all segments connected to a component when it moves.
        
        Uses ID-based matching for robust reference tracking, falling back to
        identity comparison and coordinate matching.
        """
        try:
            cx, cy = int(component.get('x', 0)), int(component.get('y', 0))
            comp_id = component.get('_element_id')
            comp_db_id = component.get('db_component_id') or component.get('hvac_component_id')

            updated_count = 0
            
            for seg in self.segments:
                from_comp = seg.get('from_component')
                to_comp = seg.get('to_component')
                changed = False

                # NOTE: During component drag, we must only move endpoints that are already
                # connected to the dragged component. Do NOT opportunistically attach new
                # segment endpoints, and do NOT use coordinate-based matching here (too
                # permissive and can cause unrelated segments to "snap" to the dragged component).

                # Prefer segment endpoint IDs if present (most stable across reloads).
                seg_from_elem_id = seg.get('from_element_id')
                seg_to_elem_id = seg.get('to_element_id')
                seg_from_db_id = seg.get('from_db_component_id')
                seg_to_db_id = seg.get('to_db_component_id')
                
                # Check if segment start is connected to this component
                is_from_connected = False
                if comp_id and seg_from_elem_id == comp_id:
                    is_from_connected = True
                elif comp_db_id and seg_from_db_id == comp_db_id:
                    is_from_connected = True
                elif from_comp is not None:
                    # Try element ID match first
                    if comp_id and from_comp.get('_element_id') == comp_id:
                        is_from_connected = True
                    # Try DB component ID match
                    else:
                        from_db_id = from_comp.get('db_component_id') or from_comp.get('hvac_component_id')
                        if comp_db_id and from_db_id and from_db_id == comp_db_id:
                            is_from_connected = True
                    # Fall back to identity check (only if objects are canonical)
                    if not is_from_connected and from_comp is component:
                        is_from_connected = True
                
                if is_from_connected:
                    seg['from_component'] = component
                    if comp_id:
                        seg['from_element_id'] = comp_id
                    if comp_db_id:
                        seg['from_db_component_id'] = comp_db_id
                    seg['start_x'] = cx
                    seg['start_y'] = cy
                    print(f"DEBUG: Updated segment start to component ({cx}, {cy})")
                    changed = True
                
                # Check if segment end is connected to this component
                is_to_connected = False
                if comp_id and seg_to_elem_id == comp_id:
                    is_to_connected = True
                elif comp_db_id and seg_to_db_id == comp_db_id:
                    is_to_connected = True
                elif to_comp is not None:
                    # Try element ID match first
                    if comp_id and to_comp.get('_element_id') == comp_id:
                        is_to_connected = True
                    # Try DB component ID match
                    else:
                        to_db_id = to_comp.get('db_component_id') or to_comp.get('hvac_component_id')
                        if comp_db_id and to_db_id and to_db_id == comp_db_id:
                            is_to_connected = True
                    # Fall back to identity check (only if objects are canonical)
                    if not is_to_connected and to_comp is component:
                        is_to_connected = True
                
                if is_to_connected:
                    seg['to_component'] = component
                    if comp_id:
                        seg['to_element_id'] = comp_id
                    if comp_db_id:
                        seg['to_db_component_id'] = comp_db_id
                    seg['end_x'] = cx
                    seg['end_y'] = cy
                    print(f"DEBUG: Updated segment end to component ({cx}, {cy})")
                    changed = True
                
                try:
                    if changed:
                        self._recompute_segment_length(seg)
                except Exception:
                    pass
                if changed:
                    updated_count += 1
            print(f"DEBUG: _update_segments_for_component_move updated {updated_count} segment(s) for component move")
        except Exception as e:
            print(f"DEBUG: Error in _update_segments_for_component_move: {e}")

    def _is_near_point(self, x1: int, y1: int, x2: int, y2: int, threshold: int) -> bool:
        dx, dy = int(x1) - int(x2), int(y1) - int(y2)
        return (dx * dx + dy * dy) <= (threshold * threshold)

    def _find_nearest_component(self, x: int, y: int, threshold: int) -> dict | None:
        best = None
        best_d2 = threshold * threshold
        for comp in self.components:
            cx, cy = int(comp.get('x', 0)), int(comp.get('y', 0))
            dx, dy = cx - int(x), cy - int(y)
            d2 = dx * dx + dy * dy
            if d2 <= best_d2:
                best_d2 = d2
                best = comp
        return best

    def _snap_segment_endpoint_to_component(self, seg: dict, endpoint: str, threshold: int) -> None:
        """Snap a segment endpoint to a nearby component.
        
        Args:
            seg: Segment dict to modify
            endpoint: 'start' or 'end'
            threshold: Maximum distance in pixels to snap
        """
        try:
            if endpoint == 'start':
                px, py = int(seg.get('start_x', 0)), int(seg.get('start_y', 0))
                comp = self._find_nearest_component(px, py, threshold)
                if comp is not None:
                    old_x, old_y = seg.get('start_x', 0), seg.get('start_y', 0)
                    seg['from_component'] = comp
                    seg['start_x'] = int(comp.get('x', 0))
                    seg['start_y'] = int(comp.get('y', 0))
                    print(f"DEBUG: Snapped segment start from ({old_x}, {old_y}) to component at ({seg['start_x']}, {seg['start_y']})")
            elif endpoint == 'end':
                px, py = int(seg.get('end_x', 0)), int(seg.get('end_y', 0))
                comp = self._find_nearest_component(px, py, threshold)
                if comp is not None:
                    old_x, old_y = seg.get('end_x', 0), seg.get('end_y', 0)
                    seg['to_component'] = comp
                    seg['end_x'] = int(comp.get('x', 0))
                    seg['end_y'] = int(comp.get('y', 0))
                    print(f"DEBUG: Snapped segment end from ({old_x}, {old_y}) to component at ({seg['end_x']}, {seg['end_y']})")
        except Exception as e:
            print(f"DEBUG: Error in _snap_segment_endpoint_to_component: {e}")

    def _recompute_segment_length(self, seg: dict) -> None:
        from math import sqrt
        lp = sqrt((int(seg.get('end_x', 0)) - int(seg.get('start_x', 0))) ** 2 + (int(seg.get('end_y', 0)) - int(seg.get('start_y', 0))) ** 2)
        seg['length_pixels'] = lp
        lr = self.scale_manager.pixels_to_real(lp)
        seg['length_real'] = lr
        seg['length_formatted'] = self.scale_manager.format_distance(lr)

    def _update_component_base_coordinates(self, component: dict) -> None:
        """Update base coordinates for a specific component to maintain zoom consistency.
        
        Uses element ID for matching when available, falling back to object identity
        and coordinate-based matching.
        """
        try:
            cur_z = self._current_zoom_factor or 1.0
            elem_id = component.get('_element_id')  # Use element ID if available
            obj_id = id(component)  # Fallback to object identity
            
            # Find and update the component in base cache
            for i, bc in enumerate(self._base_components):
                matched = False
                # Try element ID match first
                if elem_id and bc.get('_element_id') == elem_id:
                    matched = True
                # Fall back to object identity
                elif id(bc) == obj_id:
                    matched = True
                # Fall back to coordinate/type match
                elif self._components_match(bc, component):
                    matched = True
                
                if matched:
                    self._base_components[i]['x'] = int(component.get('x', 0) / cur_z)
                    self._base_components[i]['y'] = int(component.get('y', 0) / cur_z)
                    # Propagate element ID to base cache if not already present
                    if elem_id and '_element_id' not in self._base_components[i]:
                        self._base_components[i]['_element_id'] = elem_id
                    if isinstance(component.get('position'), dict):
                        self._base_components[i]['position'] = {
                            'x': int(component['position'].get('x', 0) / cur_z),
                            'y': int(component['position'].get('y', 0) / cur_z),
                        }
                    break
        except Exception as e:
            print(f"DEBUG: Failed to update component base coordinates: {e}")

    def _update_segment_base_coordinates(self, segment: dict) -> None:
        """Update base coordinates for a specific segment to maintain zoom consistency.
        
        Uses element ID for matching when available, falling back to object identity
        and coordinate-based matching.
        """
        try:
            cur_z = self._current_zoom_factor or 1.0
            elem_id = segment.get('_element_id')  # Use element ID if available
            obj_id = id(segment)  # Fallback to object identity
            
            # Find and update the segment in base cache
            for i, bs in enumerate(self._base_segments):
                matched = False
                # Try element ID match first
                if elem_id and bs.get('_element_id') == elem_id:
                    matched = True
                # Fall back to object identity
                elif id(bs) == obj_id:
                    matched = True
                # Fall back to coordinate match
                elif self._segments_match(bs, segment):
                    matched = True
                
                if matched:
                    self._base_segments[i]['start_x'] = int(segment.get('start_x', 0) / cur_z)
                    self._base_segments[i]['start_y'] = int(segment.get('start_y', 0) / cur_z)
                    self._base_segments[i]['end_x'] = int(segment.get('end_x', 0) / cur_z)
                    self._base_segments[i]['end_y'] = int(segment.get('end_y', 0) / cur_z)
                    lp = segment.get('length_pixels', 0)
                    self._base_segments[i]['length_pixels'] = lp / cur_z if lp else 0
                    # Propagate element ID to base cache if not already present
                    if elem_id and '_element_id' not in self._base_segments[i]:
                        self._base_segments[i]['_element_id'] = elem_id
                    break
        except Exception as e:
            print(f"DEBUG: Failed to update segment base coordinates: {e}")

    def _components_match(self, comp1: dict, comp2: dict) -> bool:
        """Check if two components represent the same element.
        Normalizes coordinates to base (zoom=1.0) before comparison.
        """
        # Extract basic info for debugging
        type1 = comp1.get('component_type', 'unknown')
        type2 = comp2.get('component_type', 'unknown')
        elem_id1 = comp1.get('_element_id', 'none')
        elem_id2 = comp2.get('_element_id', 'none')

        print(f"    DEBUG: _components_match - Comparing {type1}[{elem_id1}] vs {type2}[{elem_id2}]")

        # Strategy 1: Component type check
        if type1 != type2:
            print(f"      -> MATCH FAILED: Different component types ({type1} != {type2})")
            return False
        print(f"      -> Component types match: {type1}")

        # Strategy 2: DB component ID matching
        db_id1 = comp1.get('db_component_id') or comp1.get('hvac_component_id')
        db_id2 = comp2.get('db_component_id') or comp2.get('hvac_component_id')
        print(f"      -> DB IDs: {db_id1} vs {db_id2}")

        if db_id1 and db_id2 and db_id1 == db_id2:
            print(f"      -> MATCH SUCCESS: DB ID match ({db_id1})")
            return True
        elif db_id1 and db_id2:
            print(f"      -> DB ID mismatch, continuing to coordinate check")
        else:
            print(f"      -> Missing DB IDs, using coordinate matching")

        # Strategy 3: Coordinate matching with normalization
        z1 = comp1.get('saved_zoom') or 1.0
        z2 = comp2.get('saved_zoom') or 1.0
        x1, y1 = comp1.get('x', 0), comp1.get('y', 0)
        x2, y2 = comp2.get('x', 0), comp2.get('y', 0)
        base_x1 = x1 / z1
        base_y1 = y1 / z1
        base_x2 = x2 / z2
        base_y2 = y2 / z2

        print(f"      -> Coordinate normalization:")
        print(f"         comp1: ({x1}, {y1}) / {z1} = ({base_x1:.1f}, {base_y1:.1f})")
        print(f"         comp2: ({x2}, {y2}) / {z2} = ({base_x2:.1f}, {base_y2:.1f})")

        dx = abs(base_x1 - base_x2)
        dy = abs(base_y1 - base_y2)
        print(f"      -> Distance: dx={dx:.1f}, dy={dy:.1f} (threshold=5.0)")

        coord_match = dx < 5 and dy < 5
        if coord_match:
            print(f"      -> MATCH SUCCESS: Coordinate match within tolerance")
        else:
            print(f"      -> MATCH FAILED: Coordinates too far apart")

        return coord_match

    def _validate_element_state_consistency(self):
        """Validate the consistency of element state after matching operations."""
        print("\n=== ELEMENT STATE CONSISTENCY VALIDATION ===")

        # Check component consistency
        print(f"DEBUG: Validating {len(self.components)} components...")
        component_issues = []

        for i, comp in enumerate(self.components):
            if not isinstance(comp, dict):
                component_issues.append(f"Component {i}: Not a dict ({type(comp)})")
                continue

            # Check required fields
            if not comp.get('component_type'):
                component_issues.append(f"Component {i}: Missing component_type")
            if comp.get('x') is None or comp.get('y') is None:
                component_issues.append(f"Component {i}: Missing coordinates")
            if not comp.get('_element_id'):
                component_issues.append(f"Component {i}: Missing _element_id")

            # Check coordinate consistency
            try:
                x, y = float(comp.get('x', 0)), float(comp.get('y', 0))
                if abs(x) > 50000 or abs(y) > 50000:  # Sanity check for extreme coordinates
                    component_issues.append(f"Component {i}: Extreme coordinates ({x}, {y})")
            except (ValueError, TypeError):
                component_issues.append(f"Component {i}: Invalid coordinate types")

        # Check segment consistency
        print(f"DEBUG: Validating {len(self.segments)} segments...")
        segment_issues = []

        for i, seg in enumerate(self.segments):
            if not isinstance(seg, dict):
                segment_issues.append(f"Segment {i}: Not a dict ({type(seg)})")
                continue

            # Check coordinates
            coord_keys = ['start_x', 'start_y', 'end_x', 'end_y']
            missing_coords = [key for key in coord_keys if seg.get(key) is None]
            if missing_coords:
                segment_issues.append(f"Segment {i}: Missing coordinates: {missing_coords}")

            # Check endpoint linking consistency
            from_comp = seg.get('from_component')
            to_comp = seg.get('to_component')

            if from_comp and from_comp not in self.components:
                segment_issues.append(f"Segment {i}: from_component not in overlay components list")
            if to_comp and to_comp not in self.components:
                segment_issues.append(f"Segment {i}: to_component not in overlay components list")

        # Check base cache consistency
        print(f"DEBUG: Validating base cache consistency...")
        cache_issues = []

        if len(self._base_components) != len(self.components):
            cache_issues.append(f"Base components cache size mismatch: {len(self._base_components)} vs {len(self.components)}")
        if len(self._base_segments) != len(self.segments):
            cache_issues.append(f"Base segments cache size mismatch: {len(self._base_segments)} vs {len(self.segments)}")

        # Check path mapping consistency
        print(f"DEBUG: Validating path element mappings...")
        mapping_issues = []

        for path_id, mapping in self.path_element_mapping.items():
            registered_comps = mapping.get('components', [])
            registered_segs = mapping.get('segments', [])

            # Check if registered elements are still in overlay
            for comp in registered_comps:
                if comp not in self.components:
                    mapping_issues.append(f"Path {path_id}: Registered component not in overlay")
            for seg in registered_segs:
                if seg not in self.segments:
                    mapping_issues.append(f"Path {path_id}: Registered segment not in overlay")

        # Report validation results
        total_issues = len(component_issues) + len(segment_issues) + len(cache_issues) + len(mapping_issues)

        if total_issues == 0:
            print("DEBUG: STATE VALIDATION PASSED - All elements consistent")
        else:
            print(f"\n!!! STATE VALIDATION FAILED - {total_issues} issues found !!!")

            if component_issues:
                print("\nComponent Issues:")
                for issue in component_issues[:5]:  # Limit output
                    print(f"  - {issue}")
                if len(component_issues) > 5:
                    print(f"  ... and {len(component_issues) - 5} more")

            if segment_issues:
                print("\nSegment Issues:")
                for issue in segment_issues[:5]:
                    print(f"  - {issue}")
                if len(segment_issues) > 5:
                    print(f"  ... and {len(segment_issues) - 5} more")

            if cache_issues:
                print("\nCache Issues:")
                for issue in cache_issues:
                    print(f"  - {issue}")

            if mapping_issues:
                print("\nMapping Issues:")
                for issue in mapping_issues:
                    print(f"  - {issue}")

        print("=== STATE CONSISTENCY VALIDATION COMPLETE ===\n")

    def _analyze_error_isolation_issues(self):
        """Analyze potential error isolation issues in element matching strategies."""
        print("\n=== ERROR ISOLATION ANALYSIS ===")

        # Analyze component matching strategy failures
        print("\nAnalyzing Component Matching Strategy Isolation:")

        strategy_failures = {
            'db_id_matches': 0,
            'element_id_matches': 0,
            'coordinate_matches': 0,
            'total_failures': 0
        }

        # Check how many components have each type of identifier
        db_id_components = 0
        elem_id_components = 0
        coord_only_components = 0

        for comp in self.components:
            if isinstance(comp, dict):
                has_db_id = bool(comp.get('db_component_id') or comp.get('hvac_component_id'))
                has_elem_id = bool(comp.get('_element_id'))
                has_coords = bool(comp.get('x') is not None and comp.get('y') is not None)

                if has_db_id:
                    db_id_components += 1
                if has_elem_id:
                    elem_id_components += 1
                if has_coords and not has_db_id and not has_elem_id:
                    coord_only_components += 1

        print(f"  Components with DB IDs: {db_id_components}/{len(self.components)}")
        print(f"  Components with Element IDs: {elem_id_components}/{len(self.components)}")
        print(f"  Components with coordinates only: {coord_only_components}/{len(self.components)}")

        # Analyze segment matching strategies
        print("\nAnalyzing Segment Matching Strategy Isolation:")

        db_id_segments = 0
        elem_id_segments = 0
        coord_only_segments = 0
        linked_segments = 0

        for seg in self.segments:
            if isinstance(seg, dict):
                has_db_id = bool(seg.get('db_segment_id') or seg.get('hvac_segment_id'))
                has_elem_id = bool(seg.get('_element_id'))
                has_coords = all(seg.get(k) is not None for k in ['start_x', 'start_y', 'end_x', 'end_y'])
                has_endpoints = bool(seg.get('from_component') or seg.get('to_component'))

                if has_db_id:
                    db_id_segments += 1
                if has_elem_id:
                    elem_id_segments += 1
                if has_coords and not has_db_id and not has_elem_id:
                    coord_only_segments += 1
                if has_endpoints:
                    linked_segments += 1

        print(f"  Segments with DB IDs: {db_id_segments}/{len(self.segments)}")
        print(f"  Segments with Element IDs: {elem_id_segments}/{len(self.segments)}")
        print(f"  Segments with coordinates only: {coord_only_segments}/{len(self.segments)}")
        print(f"  Segments with endpoint links: {linked_segments}/{len(self.segments)}")

        # Identify potential error cascade scenarios
        print("\nPotential Error Cascade Scenarios:")

        error_scenarios = []

        if coord_only_components > 0:
            error_scenarios.append(f"Risk: {coord_only_components} components rely solely on coordinate matching")
        if coord_only_segments > 0:
            error_scenarios.append(f"Risk: {coord_only_segments} segments rely solely on coordinate matching")
        if linked_segments < len(self.segments) * 0.8:  # Less than 80% linked
            unlinked_pct = (len(self.segments) - linked_segments) / len(self.segments) * 100
            error_scenarios.append(f"Risk: {unlinked_pct:.1f}% of segments are not linked to endpoint components")

        # Check for missing critical identifiers
        missing_elem_ids = len([c for c in self.components if isinstance(c, dict) and not c.get('_element_id')])
        if missing_elem_ids > 0:
            error_scenarios.append(f"Risk: {missing_elem_ids} components missing element IDs")

        missing_seg_elem_ids = len([s for s in self.segments if isinstance(s, dict) and not s.get('_element_id')])
        if missing_seg_elem_ids > 0:
            error_scenarios.append(f"Risk: {missing_seg_elem_ids} segments missing element IDs")

        # Check for coordinate normalization issues
        extreme_coords = 0
        for comp in self.components:
            if isinstance(comp, dict):
                x, y = comp.get('x', 0), comp.get('y', 0)
                zoom = comp.get('saved_zoom', 1.0)
                if abs(x) > 10000 or abs(y) > 10000 or zoom <= 0 or zoom > 10:
                    extreme_coords += 1
        if extreme_coords > 0:
            error_scenarios.append(f"Risk: {extreme_coords} components have extreme coordinates or zoom values")

        if error_scenarios:
            print("\n!!! POTENTIAL ERROR ISOLATION ISSUES FOUND !!!")
            for i, scenario in enumerate(error_scenarios, 1):
                print(f"  {i}. {scenario}")
        else:
            print("\n✓ No major error isolation issues detected")

        print("\n=== ERROR ISOLATION ANALYSIS COMPLETE ===\n")

    def generate_element_matching_debug_report(self):
        """Generate a comprehensive debug report for element matching."""
        print("\n" + "="*80)
        print("COMPREHENSIVE ELEMENT MATCHING DEBUG REPORT")
        print("="*80)

        print(f"\nOVERVIEW:")
        print(f"  Components: {len(self.components)}")
        print(f"  Segments: {len(self.segments)}")
        print(f"  Measurements: {len(self.measurements)}")
        print(f"  Path Mappings: {len(self.path_element_mapping)}")
        print(f"  Current Zoom: {self._current_zoom_factor}")

        # Run all validation and analysis
        self._validate_element_state_consistency()
        self._analyze_error_isolation_issues()

        print("\n" + "="*80)
        print("END OF ELEMENT MATCHING DEBUG REPORT")
        print("="*80 + "\n")

    def _segments_match(self, seg1: dict, seg2: dict) -> bool:
        """Check if two segments represent the same element.
        Normalizes coordinates to base (zoom=1.0) before comparison.
        """
        # First try matching by DB segment ID
        db_id1 = seg1.get('db_segment_id') or seg1.get('hvac_segment_id')
        db_id2 = seg2.get('db_segment_id') or seg2.get('hvac_segment_id')
        if db_id1 and db_id2 and db_id1 == db_id2:
            return True
        
        # Normalize to base coordinates for comparison
        z1 = seg1.get('saved_zoom') or 1.0
        z2 = seg2.get('saved_zoom') or 1.0
        
        base_sx1 = seg1.get('start_x', 0) / z1
        base_sy1 = seg1.get('start_y', 0) / z1
        base_ex1 = seg1.get('end_x', 0) / z1
        base_ey1 = seg1.get('end_y', 0) / z1
        
        base_sx2 = seg2.get('start_x', 0) / z2
        base_sy2 = seg2.get('start_y', 0) / z2
        base_ex2 = seg2.get('end_x', 0) / z2
        base_ey2 = seg2.get('end_y', 0) / z2
        
        return (abs(base_sx1 - base_sx2) < 5 and
                abs(base_sy1 - base_sy2) < 5 and
                abs(base_ex1 - base_ex2) < 5 and
                abs(base_ey1 - base_ey2) < 5)

    # ---------------------- Utilities ----------------------
    def relink_all_segment_endpoints(self, threshold_px: int = 20) -> int:
        """Relink all segment endpoints to nearby components.
        
        This should be called after loading elements from database to ensure
        segment endpoints are properly connected to components even if
        coordinates drifted slightly during save/reload cycles.
        
        Args:
            threshold_px: Maximum distance in pixels to snap endpoints to components
            
        Returns:
            Number of endpoints relinked
        """
        relinked_count = 0
        
        for seg in self.segments:
            # Check start endpoint
            if seg.get('from_component') is None:
                start_x = seg.get('start_x', 0)
                start_y = seg.get('start_y', 0)
                nearest_comp = self._find_nearest_component(start_x, start_y, threshold_px)
                if nearest_comp is not None:
                    seg['from_component'] = nearest_comp
                    seg['from_element_id'] = nearest_comp.get('_element_id')
                    seg['from_db_component_id'] = nearest_comp.get('db_component_id') or nearest_comp.get('hvac_component_id')
                    # Snap endpoint to component center
                    seg['start_x'] = int(nearest_comp.get('x', start_x))
                    seg['start_y'] = int(nearest_comp.get('y', start_y))
                    relinked_count += 1
            
            # Check end endpoint
            if seg.get('to_component') is None:
                end_x = seg.get('end_x', 0)
                end_y = seg.get('end_y', 0)
                nearest_comp = self._find_nearest_component(end_x, end_y, threshold_px)
                if nearest_comp is not None:
                    seg['to_component'] = nearest_comp
                    seg['to_element_id'] = nearest_comp.get('_element_id')
                    seg['to_db_component_id'] = nearest_comp.get('db_component_id') or nearest_comp.get('hvac_component_id')
                    # Snap endpoint to component center
                    seg['end_x'] = int(nearest_comp.get('x', end_x))
                    seg['end_y'] = int(nearest_comp.get('y', end_y))
                    relinked_count += 1
            
            # Recompute length if any endpoint was relinked
            if relinked_count > 0:
                try:
                    self._recompute_segment_length(seg)
                except Exception:
                    pass
        
        return relinked_count

    def attach_component_to_nearby_segments(self, component, threshold_px=20):
        """Attach a newly placed component to any nearby segment endpoints.
        
        This allows placing components after segments have been drawn, and the
        segments will automatically connect to the new component.
        """
        comp_x = component.get('x', 0)
        comp_y = component.get('y', 0)
        comp_id = component.get('_element_id', 'unknown')
        comp_db_id = component.get('db_component_id') or component.get('hvac_component_id')
        attached_count = 0
        
        for seg in self.segments:
            start_x = seg.get('start_x', 0)
            start_y = seg.get('start_y', 0)
            end_x = seg.get('end_x', 0)
            end_y = seg.get('end_y', 0)
            
            start_dist = ((comp_x - start_x) ** 2 + (comp_y - start_y) ** 2) ** 0.5
            if start_dist <= threshold_px and seg.get('from_component') is None:
                seg['from_component'] = component
                seg['from_element_id'] = comp_id
                if comp_db_id:
                    seg['from_db_component_id'] = comp_db_id
                # Also snap the segment endpoint to the component center
                seg['start_x'] = comp_x
                seg['start_y'] = comp_y
                attached_count += 1
                try:
                    self._recompute_segment_length(seg)
                except Exception:
                    pass
                continue
            
            end_dist = ((comp_x - end_x) ** 2 + (comp_y - end_y) ** 2) ** 0.5
            if end_dist <= threshold_px and seg.get('to_component') is None:
                seg['to_component'] = component
                seg['to_element_id'] = comp_id
                if comp_db_id:
                    seg['to_db_component_id'] = comp_db_id
                # Also snap the segment endpoint to the component center
                seg['end_x'] = comp_x
                seg['end_y'] = comp_y
                attached_count += 1
                try:
                    self._recompute_segment_length(seg)
                except Exception:
                    pass

    def draw_grid(self, painter):
        pen = QPen(QColor(200, 200, 200), 1, Qt.DotLine)
        painter.setPen(pen)
        for x in range(0, self.width(), 50):
            painter.drawLine(x, 0, x, self.height())
        for y in range(0, self.height(), 50):
            painter.drawLine(0, y, self.width(), y)

    def register_path_elements(self, path_id, components, segments):
        """Register components and segments as belonging to a saved path.

        This prevents them from being cleared by clear_unsaved_elements().
        Uses element IDs for reliable matching, falling back to coordinate matching.
        """
        import time
        registration_start_time = time.time()

        print(f"\n=== PATH ELEMENT REGISTRATION DEBUG: Path {path_id} ===\n")
        print(f"DEBUG: Registering {len(components or [])} components and {len(segments or [])} segments")

        if path_id not in self.path_element_mapping:
            self.path_element_mapping[path_id] = {'components': [], 'segments': []}
            print(f"DEBUG: Created new path mapping for {path_id}")
        else:
            print(f"DEBUG: Using existing path mapping for {path_id}")

        # Store references to the actual overlay element objects
        registered_components = []
        registered_segments = []

        print(f"\n--- Registering Components ---")
        # Register components by finding matching objects in our overlay
        for comp_idx, comp in enumerate(components or []):
            comp_type = comp.get('component_type', 'unknown')
            comp_pos = f"({comp.get('x', 0)}, {comp.get('y', 0)})"
            comp_elem_id = comp.get('_element_id')
            comp_db_id = comp.get('db_component_id') or comp.get('hvac_component_id')

            print(f"\nDEBUG: Component {comp_idx} - {comp_type} at {comp_pos}")
            print(f"  Element ID: {comp_elem_id}")
            print(f"  DB ID: {comp_db_id}")

            # Strategy 1: Direct reference check
            if comp in self.components:
                registered_components.append(comp)
                print(f"  -> STRATEGY 1 SUCCESS: Direct reference match")
                continue
            else:
                print(f"  -> STRATEGY 1 FAILED: Not in direct references")

            # Strategy 2: Element ID matching
            found = False
            if comp_elem_id:
                print(f"  -> STRATEGY 2: Searching by element ID '{comp_elem_id}'")
                for overlay_idx, overlay_comp in enumerate(self.components):
                    if overlay_comp.get('_element_id') == comp_elem_id:
                        registered_components.append(overlay_comp)
                        found = True
                        overlay_type = overlay_comp.get('component_type', 'unknown')
                        overlay_pos = f"({overlay_comp.get('x', 0)}, {overlay_comp.get('y', 0)})"
                        print(f"    -> STRATEGY 2 SUCCESS: Found overlay component {overlay_idx} [{overlay_type}] at {overlay_pos}")
                        break
                if not found:
                    print(f"    -> STRATEGY 2 FAILED: No element ID match found")
            else:
                print(f"  -> STRATEGY 2 SKIPPED: No element ID available")

            # Strategy 3: Coordinate/type matching
            if not found:
                print(f"  -> STRATEGY 3: Coordinate/type matching")
                match_attempts = 0
                for overlay_idx, overlay_comp in enumerate(self.components):
                    match_attempts += 1
                    if self._components_match(overlay_comp, comp):
                        registered_components.append(overlay_comp)
                        found = True
                        overlay_type = overlay_comp.get('component_type', 'unknown')
                        overlay_pos = f"({overlay_comp.get('x', 0)}, {overlay_comp.get('y', 0)})"
                        print(f"    -> STRATEGY 3 SUCCESS: Coordinate match after {match_attempts} attempts -> overlay {overlay_idx} [{overlay_type}] at {overlay_pos}")
                        break
                if not found:
                    print(f"    -> STRATEGY 3 FAILED: No coordinate match after {match_attempts} attempts")

            if not found:
                print(f"  -> ALL STRATEGIES FAILED: Could not find overlay match for {comp_type} at {comp_pos}")
                print(f"     Available overlay components: {len(self.components)} total")
                if len(self.components) <= 5:
                    for i, oc in enumerate(self.components):
                        oc_type = oc.get('component_type', 'unknown') if isinstance(oc, dict) else str(type(oc))
                        oc_pos = f"({oc.get('x', 0)}, {oc.get('y', 0)})" if isinstance(oc, dict) else "N/A"
                        oc_elem_id = oc.get('_element_id', 'none') if isinstance(oc, dict) else "N/A"
                        print(f"       [{i}] {oc_type} at {oc_pos} elem_id:{oc_elem_id}")

        print(f"\n--- Registering Segments ---")
        # Register segments by finding matching objects in our overlay
        for seg_idx, seg in enumerate(segments or []):
            seg_coords = f"{seg.get('start_x', 0)},{seg.get('start_y', 0)} -> {seg.get('end_x', 0)},{seg.get('end_y', 0)}"
            seg_elem_id = seg.get('_element_id')
            seg_db_id = seg.get('db_segment_id') or seg.get('hvac_segment_id')

            print(f"\nDEBUG: Segment {seg_idx} - [{seg_coords}]")
            print(f"  Element ID: {seg_elem_id}")
            print(f"  DB ID: {seg_db_id}")

            # Strategy 1: Direct reference check
            if seg in self.segments:
                registered_segments.append(seg)
                print(f"  -> STRATEGY 1 SUCCESS: Direct reference match")
                continue
            else:
                print(f"  -> STRATEGY 1 FAILED: Not in direct references")

            # Strategy 2: Element ID matching
            found = False
            if seg_elem_id:
                print(f"  -> STRATEGY 2: Searching by element ID '{seg_elem_id}'")
                for overlay_idx, overlay_seg in enumerate(self.segments):
                    if overlay_seg.get('_element_id') == seg_elem_id:
                        registered_segments.append(overlay_seg)
                        found = True
                        overlay_coords = f"{overlay_seg.get('start_x', 0)},{overlay_seg.get('start_y', 0)} -> {overlay_seg.get('end_x', 0)},{overlay_seg.get('end_y', 0)}"
                        print(f"    -> STRATEGY 2 SUCCESS: Found overlay segment {overlay_idx} [{overlay_coords}]")
                        break
                if not found:
                    print(f"    -> STRATEGY 2 FAILED: No element ID match found")
            else:
                print(f"  -> STRATEGY 2 SKIPPED: No element ID available")

            # Strategy 3: Coordinate matching
            if not found:
                print(f"  -> STRATEGY 3: Coordinate matching")
                match_attempts = 0
                for overlay_idx, overlay_seg in enumerate(self.segments):
                    match_attempts += 1
                    if self._segments_match(overlay_seg, seg):
                        registered_segments.append(overlay_seg)
                        found = True
                        overlay_coords = f"{overlay_seg.get('start_x', 0)},{overlay_seg.get('start_y', 0)} -> {overlay_seg.get('end_x', 0)},{overlay_seg.get('end_y', 0)}"
                        print(f"    -> STRATEGY 3 SUCCESS: Coordinate match after {match_attempts} attempts -> overlay {overlay_idx} [{overlay_coords}]")
                        break
                if not found:
                    print(f"    -> STRATEGY 3 FAILED: No coordinate match after {match_attempts} attempts")

            if not found:
                print(f"  -> ALL STRATEGIES FAILED: Could not find overlay match for segment [{seg_coords}]")
                print(f"     Available overlay segments: {len(self.segments)} total")
                if len(self.segments) <= 5:
                    for i, os in enumerate(self.segments):
                        if isinstance(os, dict):
                            os_coords = f"{os.get('start_x', 0)},{os.get('start_y', 0)} -> {os.get('end_x', 0)},{os.get('end_y', 0)}"
                            os_elem_id = os.get('_element_id', 'none')
                            print(f"       [{i}] {os_coords} elem_id:{os_elem_id}")
                        else:
                            print(f"       [{i}] {type(os)} (not dict)")

        # Store the registered elements
        self.path_element_mapping[path_id]['components'] = registered_components
        self.path_element_mapping[path_id]['segments'] = registered_segments

        print(f"\n--- Registration Summary ---")
        print(f"DEBUG: Path {path_id} registration complete:")
        print(f"  Components: {len(components or [])} requested -> {len(registered_components)} registered")
        print(f"  Segments: {len(segments or [])} requested -> {len(registered_segments)} registered")

        # Detailed element ID logging
        if registered_components:
            comp_details = []
            for i, c in enumerate(registered_components):
                elem_id = c.get('_element_id', f'obj_{id(c)}')
                comp_type = c.get('component_type', 'unknown')
                comp_details.append(f"{comp_type}[{elem_id}]")
            print(f"  Registered component details: {', '.join(comp_details)}")

        if registered_segments:
            seg_details = []
            for i, s in enumerate(registered_segments):
                elem_id = s.get('_element_id', f'obj_{id(s)}')
                coords = f"{s.get('start_x', 0)},{s.get('start_y', 0)}->{s.get('end_x', 0)},{s.get('end_y', 0)}"
                seg_details.append(f"[{coords}][{elem_id}]")
            print(f"  Registered segment details: {', '.join(seg_details)}")

        # Check for registration failures
        comp_failures = len(components or []) - len(registered_components)
        seg_failures = len(segments or []) - len(registered_segments)
        if comp_failures > 0 or seg_failures > 0:
            print(f"\n!!! REGISTRATION FAILURES DETECTED !!!")
            print(f"  Component failures: {comp_failures}")
            print(f"  Segment failures: {seg_failures}")
            print(f"  This may cause elements to be incorrectly cleared later!")

        # Add performance timing for registration
        registration_end_time = time.time()
        print(f"DEBUG: PERFORMANCE - Path {path_id} registration took {(registration_end_time - registration_start_time)*1000:.1f}ms")

        print(f"\n=== PATH ELEMENT REGISTRATION DEBUG: Complete ===\n")
        self.update()
    
    def disable_clearing_temporarily(self):
        """Disable clearing of unsaved elements temporarily (e.g., during save operations)"""
        self._clearing_disabled = True
        print("DEBUG: Clearing disabled")
    
    def enable_clearing(self):
        """Re-enable clearing of unsaved elements"""
        self._clearing_disabled = False
        print("DEBUG: Clearing re-enabled")

    def set_visible_paths(self, visible_path_ids):
        self.visible_paths = {pid: True for pid in visible_path_ids}
        self.update()

    def clear_path_registrations(self):
        self.path_element_mapping.clear()
        self.visible_paths.clear()
        self.update()

    def toggle_grid(self):
        self.show_grid = not self.show_grid
        self.update()

    def toggle_measurements(self):
        self.show_measurements = not self.show_measurements
        self.update()

    def clear_measurements(self):
        self.measurements.clear()
        self._base_measurements.clear()
        self._base_dirty = True
        self.update()