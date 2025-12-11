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
        self.path_element_mapping: dict[int, dict] = {}
        
        # Protection flag to prevent clearing during save operations
        self._clearing_disabled = False
        
        # UI state
        self.show_measurements = True
        self.show_grid = False
        self.path_only_mode = False
        self._highlighted_path_id: Optional[int] = None

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
        
        # Connect signals
        self.tool_manager.element_created.connect(self.handle_element_created)
        
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
        # Provide lists to the segment tool
        self.tool_manager.set_available_components(self.components)
        self.tool_manager.set_available_segments(self.segments)

    def set_zoom_factor(self, zoom_factor: float):
        """Recompute on-screen coordinates from base geometry at given zoom."""
        try:
            if zoom_factor <= 0:
                return
            z = zoom_factor

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
        if event.buttons() & Qt.LeftButton:
            point = QPoint(event.x(), event.y())
            if self.tool_manager.current_tool_type == ToolType.SELECT:
                self._handle_select_move(point)
            else:
                self.tool_manager.update_tool(point)
            self.update()
            
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
            self.components.append(element_data)
            self.update_segment_tool_components()
            try:
                self.attach_component_to_nearby_segments(element_data, threshold_px=20)
            except Exception as e:
                print(f"DEBUG: attach_component_to_nearby_segments error: {e}")
            self._base_dirty = True
            
        elif element_type == 'segment':
            length_pixels = element_data.get('length_pixels', 0)
            try:
                length_real = self.scale_manager.pixels_to_real(length_pixels)
                element_data['length_real'] = length_real
                element_data['length_formatted'] = self.scale_manager.format_distance(length_real)
            except Exception:
                pass
            self.segments.append(element_data)
            self._base_dirty = True
            
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

        try:
            self._base_dirty = False
            self.set_zoom_factor(self._current_zoom_factor)
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
            
            # Filter out unsaved elements
            original_components_count = len(self.components)
            original_segments_count = len(self.segments)
            
            self.components = [c for c in self.components if id(c) in keep_components]
            self.segments = [s for s in self.segments if id(s) in keep_segments]
            
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
        for comp in self.components:
            # Visibility rules
            if self.path_only_mode:
                if not self._is_component_in_visible_path(comp):
                    continue
            else:
                has_reg = bool(self.path_element_mapping)
                if has_reg:
                    is_reg = self._is_component_registered_any_path(comp)
                    if not self.visible_paths:
                        if is_reg:
                            continue
                    else:
                        if is_reg and not self._is_component_in_visible_path(comp):
                            continue
            x = comp.get('x', 0)
            y = comp.get('y', 0)
            comp_type = comp.get('component_type', 'unknown')
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
            pen = QPen(color, 2)
            brush = QBrush(color)
            painter.setPen(pen)
            painter.setBrush(brush)
            painter.drawEllipse(x - 8, y - 8, 16, 16)
            painter.setPen(QPen(Qt.black))
            painter.setFont(QFont("Arial", 8))
            painter.drawText(x - 15, y + 25, comp_type)

    def draw_segments(self, painter):
        for seg in self.segments:
            if self.path_only_mode:
                if not self._is_segment_in_visible_path(seg):
                    continue
            else:
                has_reg = bool(self.path_element_mapping)
                if has_reg:
                    is_reg = self._is_segment_registered_any_path(seg)
                    if not self.visible_paths:
                        if is_reg:
                            continue
                    else:
                        if is_reg and not self._is_segment_in_visible_path(seg):
                            continue
            start_x = seg.get('start_x', 0)
            start_y = seg.get('start_y', 0)
            end_x = seg.get('end_x', 0)
            end_y = seg.get('end_y', 0)
            pen = QPen(QColor(255, 165, 0), 3)
            painter.setPen(pen)
            painter.drawLine(start_x, start_y, end_x, end_y)
            mid_x = (start_x + end_x) // 2
            mid_y = (start_y + end_y) // 2
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
        for path_id in self.visible_paths:
            mapping = self.path_element_mapping.get(path_id, {})
            if comp in mapping.get('components', []):
                        return True
        return False
    
    def _is_segment_in_visible_path(self, seg):
        for path_id in self.visible_paths:
            mapping = self.path_element_mapping.get(path_id, {})
            if seg in mapping.get('segments', []):
                        return True
        return False

    def _is_component_registered_any_path(self, comp):
        for mapping in self.path_element_mapping.values():
            if comp in mapping.get('components', []):
                return True
        return False

    def _is_segment_registered_any_path(self, seg):
        for mapping in self.path_element_mapping.values():
            if seg in mapping.get('segments', []):
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
            self._hit_target = {'type': 'segment', 'ref': hit_seg.get('segment'), 'endpoint': hit_seg.get('endpoint')}
            if self._select_modifiers & Qt.ControlModifier:
                if hit_seg in self._selected_segments:
                    self._selected_segments.remove(hit_seg)
                else:
                    self._selected_segments.append(hit_seg)
            else:
                self._selected_segments = [hit_seg]
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
        try:
            cx, cy = int(component.get('x', 0)), int(component.get('y', 0))
            for seg in self.segments:
                if seg.get('from_component') is component:
                    seg['start_x'] = cx
                    seg['start_y'] = cy
                if seg.get('to_component') is component:
                    seg['end_x'] = cx
                    seg['end_y'] = cy
                # If not attached but endpoint is close after move, attach and snap
                if seg.get('from_component') is None:
                    if self._is_near_point(seg.get('start_x', 0), seg.get('start_y', 0), cx, cy, self._snap_threshold_px):
                        seg['from_component'] = component
                        seg['start_x'] = cx
                        seg['start_y'] = cy
                if seg.get('to_component') is None:
                    if self._is_near_point(seg.get('end_x', 0), seg.get('end_y', 0), cx, cy, self._snap_threshold_px):
                        seg['to_component'] = component
                        seg['end_x'] = cx
                        seg['end_y'] = cy
                try:
                    self._recompute_segment_length(seg)
                except Exception:
                    pass
        except Exception:
            pass

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
        try:
            if endpoint == 'start':
                px, py = int(seg.get('start_x', 0)), int(seg.get('start_y', 0))
                comp = self._find_nearest_component(px, py, threshold)
                if comp is not None:
                    seg['from_component'] = comp
                    seg['start_x'] = int(comp.get('x', 0))
                    seg['start_y'] = int(comp.get('y', 0))
            elif endpoint == 'end':
                px, py = int(seg.get('end_x', 0)), int(seg.get('end_y', 0))
                comp = self._find_nearest_component(px, py, threshold)
                if comp is not None:
                    seg['to_component'] = comp
                    seg['end_x'] = int(comp.get('x', 0))
                    seg['end_y'] = int(comp.get('y', 0))
        except Exception:
            pass

    def _recompute_segment_length(self, seg: dict) -> None:
        from math import sqrt
        lp = sqrt((int(seg.get('end_x', 0)) - int(seg.get('start_x', 0))) ** 2 + (int(seg.get('end_y', 0)) - int(seg.get('start_y', 0))) ** 2)
        seg['length_pixels'] = lp
        lr = self.scale_manager.pixels_to_real(lp)
        seg['length_real'] = lr
        seg['length_formatted'] = self.scale_manager.format_distance(lr)

    def _update_component_base_coordinates(self, component: dict) -> None:
        """Update base coordinates for a specific component to maintain zoom consistency"""
        try:
            cur_z = self._current_zoom_factor or 1.0
            comp_id = id(component)  # Use object identity since components might not have stable IDs
            
            # Find and update the component in base cache
            for i, bc in enumerate(self._base_components):
                if id(bc) == comp_id or self._components_match(bc, component):
                    self._base_components[i]['x'] = int(component.get('x', 0) / cur_z)
                    self._base_components[i]['y'] = int(component.get('y', 0) / cur_z)
                    if isinstance(component.get('position'), dict):
                        self._base_components[i]['position'] = {
                            'x': int(component['position'].get('x', 0) / cur_z),
                            'y': int(component['position'].get('y', 0) / cur_z),
                        }
                    break
        except Exception as e:
            print(f"DEBUG: Failed to update component base coordinates: {e}")

    def _update_segment_base_coordinates(self, segment: dict) -> None:
        """Update base coordinates for a specific segment to maintain zoom consistency"""
        try:
            cur_z = self._current_zoom_factor or 1.0
            seg_id = id(segment)  # Use object identity
            
            # Find and update the segment in base cache
            for i, bs in enumerate(self._base_segments):
                if id(bs) == seg_id or self._segments_match(bs, segment):
                    self._base_segments[i]['start_x'] = int(segment.get('start_x', 0) / cur_z)
                    self._base_segments[i]['start_y'] = int(segment.get('start_y', 0) / cur_z)
                    self._base_segments[i]['end_x'] = int(segment.get('end_x', 0) / cur_z)
                    self._base_segments[i]['end_y'] = int(segment.get('end_y', 0) / cur_z)
                    lp = segment.get('length_pixels', 0)
                    self._base_segments[i]['length_pixels'] = lp / cur_z if lp else 0
                    break
        except Exception as e:
            print(f"DEBUG: Failed to update segment base coordinates: {e}")

    def _components_match(self, comp1: dict, comp2: dict) -> bool:
        """Check if two components represent the same element"""
        return (comp1.get('component_type') == comp2.get('component_type') and
                abs(comp1.get('x', 0) - comp2.get('x', 0)) < 5 and
                abs(comp1.get('y', 0) - comp2.get('y', 0)) < 5)

    def _segments_match(self, seg1: dict, seg2: dict) -> bool:
        """Check if two segments represent the same element"""
        return (abs(seg1.get('start_x', 0) - seg2.get('start_x', 0)) < 5 and
                abs(seg1.get('start_y', 0) - seg2.get('start_y', 0)) < 5 and
                abs(seg1.get('end_x', 0) - seg2.get('end_x', 0)) < 5 and
                abs(seg1.get('end_y', 0) - seg2.get('end_y', 0)) < 5)

    # ---------------------- Utilities ----------------------
    def attach_component_to_nearby_segments(self, component, threshold_px=20):
        comp_x = component.get('x', 0)
        comp_y = component.get('y', 0)
        for seg in self.segments:
            start_x = seg.get('start_x', 0)
            start_y = seg.get('start_y', 0)
            end_x = seg.get('end_x', 0)
            end_y = seg.get('end_y', 0)
            start_dist = ((comp_x - start_x) ** 2 + (comp_y - start_y) ** 2) ** 0.5
            if start_dist <= threshold_px:
                seg['from_component'] = component
                continue
            end_dist = ((comp_x - end_x) ** 2 + (comp_y - end_y) ** 2) ** 0.5
            if end_dist <= threshold_px:
                seg['to_component'] = component

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
        """
        if path_id not in self.path_element_mapping:
            self.path_element_mapping[path_id] = {'components': [], 'segments': []}
        
        # Store references to the actual overlay element objects
        registered_components = []
        registered_segments = []
        
        # Register components by finding matching objects in our overlay
        for comp in (components or []):
            if comp in self.components:
                registered_components.append(comp)
            else:
                # Try to find matching component in overlay
                for overlay_comp in self.components:
                    if (overlay_comp.get('x') == comp.get('x') and 
                        overlay_comp.get('y') == comp.get('y') and
                        overlay_comp.get('component_type') == comp.get('component_type')):
                        registered_components.append(overlay_comp)
                        break
        
        # Register segments by finding matching objects in our overlay
        for seg in (segments or []):
            if seg in self.segments:
                registered_segments.append(seg)
            else:
                # Try to find matching segment in overlay
                for overlay_seg in self.segments:
                    if (abs(overlay_seg.get('start_x', 0) - seg.get('start_x', 0)) < 5 and
                        abs(overlay_seg.get('start_y', 0) - seg.get('start_y', 0)) < 5 and
                        abs(overlay_seg.get('end_x', 0) - seg.get('end_x', 0)) < 5 and
                        abs(overlay_seg.get('end_y', 0) - seg.get('end_y', 0)) < 5):
                        registered_segments.append(overlay_seg)
                        break
        
        self.path_element_mapping[path_id]['components'] = registered_components
        self.path_element_mapping[path_id]['segments'] = registered_segments
        
        print(f"DEBUG: Registered path {path_id} with {len(registered_components)} components and {len(registered_segments)} segments")
        print(f"DEBUG: Component IDs: {[id(c) for c in registered_components]}")
        print(f"DEBUG: Segment IDs: {[id(s) for s in registered_segments]}")
        
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