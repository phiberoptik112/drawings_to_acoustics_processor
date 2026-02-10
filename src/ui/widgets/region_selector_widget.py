"""
Region Selector Widget
---------------------
Interactive widget for selecting table regions from images/PDFs
with rectangle drawing, zoom/pan, and multi-region support.
"""

from __future__ import annotations

from typing import Optional, List, Tuple
from dataclasses import dataclass

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QSlider, QToolBar, QToolButton
)
from PySide6.QtCore import Qt, Signal, QRect, QPoint, QPointF
from PySide6.QtGui import (
    QPainter, QPen, QColor, QPixmap, QWheelEvent,
    QMouseEvent, QPaintEvent, QCursor, QTransform
)


@dataclass
class SelectionRect:
    """A selection rectangle in image coordinates"""
    x: int
    y: int
    width: int
    height: int
    label: str = "Selection"
    color: QColor = QColor(0, 255, 0)
    
    def to_qrect(self) -> QRect:
        return QRect(self.x, self.y, self.width, self.height)
    
    def contains_point(self, x: int, y: int, margin: int = 5) -> bool:
        """Check if point is inside rectangle with margin"""
        return (self.x - margin <= x <= self.x + self.width + margin and
                self.y - margin <= y <= self.y + self.height + margin)
    
    def get_handle_at_point(self, x: int, y: int, handle_size: int = 10) -> Optional[str]:
        """
        Check if point is on a resize handle.
        Returns: 'tl', 'tr', 'bl', 'br', 'edge', or None
        """
        # Corners
        if abs(x - self.x) <= handle_size and abs(y - self.y) <= handle_size:
            return 'tl'
        if abs(x - (self.x + self.width)) <= handle_size and abs(y - self.y) <= handle_size:
            return 'tr'
        if abs(x - self.x) <= handle_size and abs(y - (self.y + self.height)) <= handle_size:
            return 'bl'
        if abs(x - (self.x + self.width)) <= handle_size and abs(y - (self.y + self.height)) <= handle_size:
            return 'br'
        
        # Edges
        if self.contains_point(x, y, margin=handle_size):
            return 'edge'
        
        return None


class RegionSelectorCanvas(QWidget):
    """
    Interactive canvas for selecting regions on an image with zoom and pan
    """
    
    region_selected = Signal(SelectionRect)  # Emitted when selection is complete
    regions_changed = Signal(list)  # Emitted when regions list changes
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumSize(400, 300)
        self.setMouseTracking(True)
        
        # Image data
        self.pixmap: Optional[QPixmap] = None
        self.transform = QTransform()
        self.zoom_level = 1.0
        self.pan_offset = QPoint(0, 0)
        
        # Selection state
        self.selections: List[SelectionRect] = []
        self.current_selection: Optional[SelectionRect] = None
        self.is_drawing = False
        self.is_panning = False
        self.is_resizing = False
        self.resize_handle: Optional[str] = None
        self.start_point: Optional[QPoint] = None
        self.last_mouse_pos: Optional[QPoint] = None
        
        # Interaction mode
        self.multi_select_enabled = False
        self.show_detected_regions = True
        
        # Detected regions (from auto-detection)
        self.detected_regions: List[SelectionRect] = []
        
        self.setFocusPolicy(Qt.StrongFocus)
    
    def set_pixmap(self, pixmap: QPixmap):
        """Set the image to display"""
        self.pixmap = pixmap
        self.zoom_level = 1.0
        self.pan_offset = QPoint(0, 0)
        self._fit_to_view()
        self.update()
    
    def _fit_to_view(self):
        """Fit image to widget size"""
        if not self.pixmap:
            return
        
        widget_rect = self.rect()
        image_size = self.pixmap.size()
        
        # Calculate scale to fit
        scale_x = widget_rect.width() / image_size.width()
        scale_y = widget_rect.height() / image_size.height()
        self.zoom_level = min(scale_x, scale_y) * 0.95  # 95% to leave margin
        
        # Center image
        scaled_width = image_size.width() * self.zoom_level
        scaled_height = image_size.height() * self.zoom_level
        self.pan_offset = QPoint(
            int((widget_rect.width() - scaled_width) / 2),
            int((widget_rect.height() - scaled_height) / 2)
        )
    
    def set_detected_regions(self, regions: List[SelectionRect]):
        """Set regions detected by auto-detection"""
        self.detected_regions = regions
        self.update()
    
    def clear_selections(self):
        """Clear all user selections"""
        self.selections.clear()
        self.current_selection = None
        self.regions_changed.emit(self.selections)
        self.update()
    
    def get_selections(self) -> List[SelectionRect]:
        """Get all selections in image coordinates"""
        return self.selections.copy()
    
    def zoom_in(self):
        """Zoom in by 20%"""
        self.zoom_level *= 1.2
        self.update()
    
    def zoom_out(self):
        """Zoom out by 20%"""
        self.zoom_level /= 1.2
        self.update()
    
    def fit_to_view(self):
        """Reset zoom to fit image"""
        self._fit_to_view()
        self.update()
    
    def _screen_to_image(self, screen_point: QPoint) -> Tuple[int, int]:
        """Convert screen coordinates to image coordinates"""
        if not self.pixmap:
            return (0, 0)
        
        # Account for zoom and pan
        image_x = int((screen_point.x() - self.pan_offset.x()) / self.zoom_level)
        image_y = int((screen_point.y() - self.pan_offset.y()) / self.zoom_level)
        
        # Clamp to image bounds
        image_x = max(0, min(image_x, self.pixmap.width()))
        image_y = max(0, min(image_y, self.pixmap.height()))
        
        return (image_x, image_y)
    
    def _image_to_screen(self, image_x: int, image_y: int) -> QPoint:
        """Convert image coordinates to screen coordinates"""
        screen_x = int(image_x * self.zoom_level + self.pan_offset.x())
        screen_y = int(image_y * self.zoom_level + self.pan_offset.y())
        return QPoint(screen_x, screen_y)
    
    def paintEvent(self, event: QPaintEvent):
        """Paint the canvas"""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setRenderHint(QPainter.SmoothPixmapTransform)
        
        # Fill background
        painter.fillRect(self.rect(), QColor(40, 40, 40))
        
        if not self.pixmap:
            painter.setPen(QColor(200, 200, 200))
            painter.drawText(self.rect(), Qt.AlignCenter, "No image loaded")
            return
        
        # Draw image with zoom and pan
        painter.translate(self.pan_offset)
        painter.scale(self.zoom_level, self.zoom_level)
        painter.drawPixmap(0, 0, self.pixmap)
        
        # Reset transform for overlays
        painter.resetTransform()
        
        # Draw detected regions (if enabled)
        if self.show_detected_regions:
            for region in self.detected_regions:
                self._draw_region(painter, region, dashed=True)
        
        # Draw user selections
        for selection in self.selections:
            self._draw_region(painter, selection, dashed=False)
        
        # Draw current selection being drawn
        if self.current_selection and self.is_drawing:
            self._draw_region(painter, self.current_selection, dashed=False, highlight=True)
    
    def _draw_region(self, painter: QPainter, region: SelectionRect, dashed: bool = False, highlight: bool = False):
        """Draw a selection region"""
        # Convert to screen coordinates
        screen_rect = QRect(
            int(region.x * self.zoom_level + self.pan_offset.x()),
            int(region.y * self.zoom_level + self.pan_offset.y()),
            int(region.width * self.zoom_level),
            int(region.height * self.zoom_level)
        )
        
        # Draw rectangle
        color = QColor(255, 255, 0) if highlight else region.color
        pen = QPen(color, 2)
        if dashed:
            pen.setStyle(Qt.DashLine)
        painter.setPen(pen)
        painter.drawRect(screen_rect)
        
        # Draw label
        label_bg = QColor(color)
        label_bg.setAlpha(180)
        painter.fillRect(
            screen_rect.x(),
            screen_rect.y() - 20,
            100,
            20,
            label_bg
        )
        painter.setPen(QColor(0, 0, 0))
        painter.drawText(
            screen_rect.x() + 5,
            screen_rect.y() - 5,
            region.label
        )
        
        # Draw resize handles if not drawing
        if not self.is_drawing and not dashed:
            self._draw_handles(painter, screen_rect)
    
    def _draw_handles(self, painter: QPainter, rect: QRect):
        """Draw resize handles on corners"""
        handle_size = 8
        painter.fillRect(rect.x() - handle_size//2, rect.y() - handle_size//2, handle_size, handle_size, QColor(255, 255, 255))
        painter.fillRect(rect.right() - handle_size//2, rect.y() - handle_size//2, handle_size, handle_size, QColor(255, 255, 255))
        painter.fillRect(rect.x() - handle_size//2, rect.bottom() - handle_size//2, handle_size, handle_size, QColor(255, 255, 255))
        painter.fillRect(rect.right() - handle_size//2, rect.bottom() - handle_size//2, handle_size, handle_size, QColor(255, 255, 255))
    
    def mousePressEvent(self, event: QMouseEvent):
        """Handle mouse press"""
        if not self.pixmap:
            return
        
        self.last_mouse_pos = event.pos()
        image_x, image_y = self._screen_to_image(event.pos())
        
        # Check if clicking on detected region
        if event.button() == Qt.LeftButton:
            for region in self.detected_regions:
                if region.contains_point(image_x, image_y):
                    # Select detected region
                    new_selection = SelectionRect(
                        region.x, region.y, region.width, region.height,
                        label="Selected", color=QColor(0, 255, 0)
                    )
                    if not self.multi_select_enabled:
                        self.selections.clear()
                    self.selections.append(new_selection)
                    self.region_selected.emit(new_selection)
                    self.regions_changed.emit(self.selections)
                    self.update()
                    return
            
            # Check if clicking on existing selection handle
            for selection in self.selections:
                handle = selection.get_handle_at_point(image_x, image_y, handle_size=10)
                if handle:
                    self.is_resizing = True
                    self.resize_handle = handle
                    self.current_selection = selection
                    return
            
            # Start new selection
            self.is_drawing = True
            self.start_point = QPoint(image_x, image_y)
            self.current_selection = SelectionRect(
                image_x, image_y, 0, 0,
                label=f"Region {len(self.selections) + 1}",
                color=QColor(0, 255, 0)
            )
        
        elif event.button() == Qt.MiddleButton:
            # Pan mode
            self.is_panning = True
            self.setCursor(Qt.ClosedHandCursor)
    
    def mouseMoveEvent(self, event: QMouseEvent):
        """Handle mouse move"""
        if not self.pixmap:
            return
        
        image_x, image_y = self._screen_to_image(event.pos())
        
        # Update cursor based on hover
        if not self.is_drawing and not self.is_panning:
            cursor_set = False
            for selection in self.selections:
                handle = selection.get_handle_at_point(image_x, image_y, handle_size=10)
                if handle == 'tl' or handle == 'br':
                    self.setCursor(Qt.SizeFDiagCursor)
                    cursor_set = True
                    break
                elif handle == 'tr' or handle == 'bl':
                    self.setCursor(Qt.SizeBDiagCursor)
                    cursor_set = True
                    break
                elif handle == 'edge':
                    self.setCursor(Qt.SizeAllCursor)
                    cursor_set = True
                    break
            
            if not cursor_set:
                self.setCursor(Qt.CrossCursor)
        
        # Handle drawing
        if self.is_drawing and self.current_selection and self.start_point:
            # Update selection rectangle
            x1, y1 = self.start_point.x(), self.start_point.y()
            x2, y2 = image_x, image_y
            
            self.current_selection.x = min(x1, x2)
            self.current_selection.y = min(y1, y2)
            self.current_selection.width = abs(x2 - x1)
            self.current_selection.height = abs(y2 - y1)
            self.update()
        
        # Handle panning
        elif self.is_panning and self.last_mouse_pos:
            delta = event.pos() - self.last_mouse_pos
            self.pan_offset += delta
            self.last_mouse_pos = event.pos()
            self.update()
        
        # Handle resizing
        elif self.is_resizing and self.current_selection:
            # Implement resize logic based on resize_handle
            if self.resize_handle == 'br':
                self.current_selection.width = image_x - self.current_selection.x
                self.current_selection.height = image_y - self.current_selection.y
            elif self.resize_handle == 'tl':
                new_width = self.current_selection.x + self.current_selection.width - image_x
                new_height = self.current_selection.y + self.current_selection.height - image_y
                self.current_selection.x = image_x
                self.current_selection.y = image_y
                self.current_selection.width = new_width
                self.current_selection.height = new_height
            # Add more handle cases as needed
            self.update()
    
    def mouseReleaseEvent(self, event: QMouseEvent):
        """Handle mouse release"""
        if event.button() == Qt.LeftButton:
            if self.is_drawing and self.current_selection:
                # Finalize selection if it has valid size
                if self.current_selection.width > 10 and self.current_selection.height > 10:
                    if not self.multi_select_enabled:
                        self.selections.clear()
                    self.selections.append(self.current_selection)
                    self.region_selected.emit(self.current_selection)
                    self.regions_changed.emit(self.selections)
                
                self.is_drawing = False
                self.current_selection = None
                self.start_point = None
                self.update()
            
            elif self.is_resizing:
                self.is_resizing = False
                self.resize_handle = None
                self.regions_changed.emit(self.selections)
                self.update()
        
        elif event.button() == Qt.MiddleButton:
            self.is_panning = False
            self.setCursor(Qt.CrossCursor)
    
    def wheelEvent(self, event: QWheelEvent):
        """Handle mouse wheel for zooming"""
        if not self.pixmap:
            return
        
        # Zoom towards mouse position
        zoom_factor = 1.1 if event.angleDelta().y() > 0 else 0.9
        old_zoom = self.zoom_level
        self.zoom_level *= zoom_factor
        
        # Clamp zoom
        self.zoom_level = max(0.1, min(self.zoom_level, 10.0))
        
        # Adjust pan to zoom towards cursor
        mouse_pos = event.position().toPoint()
        self.pan_offset = QPoint(
            int(mouse_pos.x() - (mouse_pos.x() - self.pan_offset.x()) * self.zoom_level / old_zoom),
            int(mouse_pos.y() - (mouse_pos.y() - self.pan_offset.y()) * self.zoom_level / old_zoom)
        )
        
        self.update()
        event.accept()


class RegionSelectorWidget(QWidget):
    """
    Complete region selector widget with toolbar and canvas
    """
    
    regions_selected = Signal(list)  # Emitted when selections are finalized
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.canvas = RegionSelectorCanvas()
        self.canvas.regions_changed.connect(self._on_regions_changed)
        self._build_ui()
    
    def _build_ui(self):
        """Build the widget UI"""
        layout = QVBoxLayout()
        
        # Toolbar
        toolbar = QWidget()
        toolbar_layout = QHBoxLayout()
        toolbar_layout.setContentsMargins(0, 0, 0, 0)
        
        # Zoom controls
        zoom_out_btn = QPushButton("−")
        zoom_out_btn.setMaximumWidth(30)
        zoom_out_btn.clicked.connect(self.canvas.zoom_out)
        toolbar_layout.addWidget(zoom_out_btn)
        
        self.zoom_label = QLabel("100%")
        self.zoom_label.setMinimumWidth(50)
        toolbar_layout.addWidget(self.zoom_label)
        
        zoom_in_btn = QPushButton("+")
        zoom_in_btn.setMaximumWidth(30)
        zoom_in_btn.clicked.connect(self.canvas.zoom_in)
        toolbar_layout.addWidget(zoom_in_btn)
        
        fit_btn = QPushButton("Fit")
        fit_btn.clicked.connect(self.canvas.fit_to_view)
        toolbar_layout.addWidget(fit_btn)
        
        toolbar_layout.addSpacing(20)
        
        # Clear button
        clear_btn = QPushButton("Clear Selection")
        clear_btn.clicked.connect(self.canvas.clear_selections)
        toolbar_layout.addWidget(clear_btn)
        
        toolbar_layout.addStretch()
        
        # Multi-select toggle
        self.multi_select_check = QPushButton("Multi-Select: OFF")
        self.multi_select_check.setCheckable(True)
        self.multi_select_check.toggled.connect(self._toggle_multi_select)
        toolbar_layout.addWidget(self.multi_select_check)
        
        toolbar.setLayout(toolbar_layout)
        layout.addWidget(toolbar)
        
        # Canvas
        layout.addWidget(self.canvas, 1)
        
        # Status bar
        self.status_label = QLabel("Draw a rectangle to select a region, or click a detected region")
        layout.addWidget(self.status_label)
        
        self.setLayout(layout)
    
    def set_pixmap(self, pixmap: QPixmap):
        """Set the image to display"""
        self.canvas.set_pixmap(pixmap)
    
    def set_detected_regions(self, regions: List[SelectionRect]):
        """Set detected regions"""
        self.canvas.set_detected_regions(regions)
    
    def get_selections(self) -> List[SelectionRect]:
        """Get current selections"""
        return self.canvas.get_selections()
    
    def _toggle_multi_select(self, checked: bool):
        """Toggle multi-select mode"""
        self.canvas.multi_select_enabled = checked
        self.multi_select_check.setText(f"Multi-Select: {'ON' if checked else 'OFF'}")
    
    def _on_regions_changed(self, regions: List[SelectionRect]):
        """Update status when regions change"""
        count = len(regions)
        if count == 0:
            self.status_label.setText("Draw a rectangle to select a region, or click a detected region")
        elif count == 1:
            self.status_label.setText(f"1 region selected")
        else:
            self.status_label.setText(f"{count} regions selected")
        
        self.regions_selected.emit(regions)
