"""
PDF Viewer component using PyMuPDF for displaying architectural drawings
"""

import fitz  # PyMuPDF
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                             QScrollArea, QPushButton, QSlider, QComboBox,
                             QMessageBox, QSizePolicy, QRubberBand)
from PySide6.QtCore import Qt, Signal, QRect, QPoint, QSize, QTimer
from PySide6.QtGui import QPixmap, QImage, QPainter, QPen, QColor
import os


class PDFViewer(QWidget):
    """PDF viewer widget with zoom and page navigation"""
    
    # Signals
    coordinates_clicked = Signal(float, float)  # PDF coordinates clicked
    screen_coordinates_clicked = Signal(float, float)  # Screen pixel coordinates clicked
    scale_changed = Signal(float)  # Zoom scale changed
    page_changed = Signal(int)  # Page number changed
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.pdf_document = None
        self.current_page = 0
        self.zoom_factor = 1.0
        self.pdf_path = None
        
        # Page properties
        self.page_width = 0
        self.page_height = 0
        self.pixmap = None
        # Selection state
        self._rubber_band = None
        self._origin = QPoint()
        self.selection_rect_pdf = None  # (x0,y0,x1,y1) in PDF coords at 100%
        
        self.init_ui()
        self.selection_mode = 'free'  # 'free' | 'column' | 'row'
        
    def init_ui(self):
        """Initialize the user interface"""
        layout = QVBoxLayout()
        
        # Toolbar
        toolbar = self.create_toolbar()
        layout.addWidget(toolbar)
        
        # Scroll area for PDF display
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setAlignment(Qt.AlignCenter)
        
        # PDF display label
        self.pdf_label = QLabel()
        self.pdf_label.setAlignment(Qt.AlignCenter)
        # Dark-friendly canvas border; keep PDF rendering neutral
        self.pdf_label.setStyleSheet("border: 1px solid #3a3a3a; background-color: #1e1e1e;")
        self.pdf_label.mousePressEvent = self.mouse_press_event
        self.pdf_label.mouseMoveEvent = self.mouse_move_event
        self.pdf_label.mouseReleaseEvent = self.mouse_release_event
        self.pdf_label.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        
        self.scroll_area.setWidget(self.pdf_label)
        layout.addWidget(self.scroll_area)
        
        # Status bar
        self.status_label = QLabel("No PDF loaded")
        self.status_label.setStyleSheet("color: #7f8c8d; font-size: 10px; margin: 5px;")
        layout.addWidget(self.status_label)
        
        self.setLayout(layout)
        
    def create_toolbar(self):
        """Create the PDF viewer toolbar"""
        toolbar = QWidget()
        # Dark mode toolbar background
        toolbar.setStyleSheet("background-color: #2a2a2a; padding: 5px; border: 1px solid #3a3a3a;")
        layout = QHBoxLayout()
        
        # Page navigation
        self.prev_btn = QPushButton("◀ Prev")
        self.prev_btn.clicked.connect(self.previous_page)
        self.prev_btn.setEnabled(False)
        
        self.next_btn = QPushButton("Next ▶")
        self.next_btn.clicked.connect(self.next_page)
        self.next_btn.setEnabled(False)
        
        self.page_label = QLabel("Page: 0/0")
        self.page_label.setStyleSheet("color: #e0e0e0;")
        
        # Zoom controls
        zoom_label = QLabel("Zoom:")
        zoom_label.setStyleSheet("color: #e0e0e0;")
        self.zoom_slider = QSlider(Qt.Horizontal)
        self.zoom_slider.setRange(25, 400)  # 25% to 400%
        self.zoom_slider.setValue(100)
        self.zoom_slider.setMaximumWidth(150)
        self.zoom_slider.valueChanged.connect(self.zoom_changed)
        
        self.zoom_combo = QComboBox()
        self.zoom_combo.addItems(["25%", "50%", "75%", "100%", "125%", "150%", "200%", "300%", "Fit Width", "Fit Page"])
        self.zoom_combo.setCurrentText("100%")
        self.zoom_combo.currentTextChanged.connect(self.zoom_preset_changed)
        
        # Zoom buttons
        zoom_in_btn = QPushButton("🔍+")
        zoom_in_btn.clicked.connect(self.zoom_in)
        zoom_in_btn.setMaximumWidth(40)
        
        zoom_out_btn = QPushButton("🔍-")
        zoom_out_btn.clicked.connect(self.zoom_out)
        zoom_out_btn.setMaximumWidth(40)
        
        # Layout toolbar
        layout.addWidget(self.prev_btn)
        layout.addWidget(self.next_btn)
        layout.addWidget(self.page_label)
        layout.addStretch()
        layout.addWidget(zoom_label)
        layout.addWidget(zoom_out_btn)
        layout.addWidget(self.zoom_slider)
        layout.addWidget(zoom_in_btn)
        layout.addWidget(self.zoom_combo)
        
        toolbar.setLayout(layout)
        return toolbar
        
    def load_pdf(self, pdf_path):
        """Load a PDF file"""
        try:
            if not os.path.exists(pdf_path):
                raise FileNotFoundError(f"PDF file not found: {pdf_path}")
                
            self.pdf_document = fitz.open(pdf_path)
            self.pdf_path = pdf_path
            self.current_page = 0
            
            # Update UI
            self.update_page_navigation()
            self.render_page()
            
            # Emit page changed signal for initial page
            self.page_changed.emit(self.current_page)
            
            self.status_label.setText(f"Loaded: {os.path.basename(pdf_path)} ({len(self.pdf_document)} pages)")
            
            return True
            
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to load PDF:\n{str(e)}")
            return False
            
    def render_page(self):
        """Render the current PDF page"""
        if not self.pdf_document or self.current_page >= len(self.pdf_document):
            return
            
        try:
            # Get the page
            page = self.pdf_document[self.current_page]
            
            # Create transformation matrix for zoom
            mat = fitz.Matrix(self.zoom_factor, self.zoom_factor)
            
            # Render page to pixmap
            pix = page.get_pixmap(matrix=mat)
            
            # Store page dimensions at current zoom
            self.page_width = pix.width
            self.page_height = pix.height
            
            # Convert to QImage
            img_data = pix.tobytes("ppm")
            qimg = QImage.fromData(img_data)
            
            # Convert to QPixmap and display
            self.pixmap = QPixmap.fromImage(qimg)
            self.pdf_label.setPixmap(self.pixmap)
            self.pdf_label.resize(self.pixmap.size())
            
            # Update status
            zoom_percent = int(self.zoom_factor * 100)
            self.status_label.setText(f"Page {self.current_page + 1}/{len(self.pdf_document)} - {zoom_percent}% - {self.page_width}x{self.page_height}")
            
        except Exception as e:
            QMessageBox.warning(self, "Warning", f"Failed to render page:\n{str(e)}")
            
    def update_page_navigation(self):
        """Update page navigation controls"""
        if not self.pdf_document:
            self.prev_btn.setEnabled(False)
            self.next_btn.setEnabled(False)
            self.page_label.setText("Page: 0/0")
            return
            
        total_pages = len(self.pdf_document)
        self.prev_btn.setEnabled(self.current_page > 0)
        self.next_btn.setEnabled(self.current_page < total_pages - 1)
        self.page_label.setText(f"Page: {self.current_page + 1}/{total_pages}")
        
    def previous_page(self):
        """Go to previous page"""
        if self.current_page > 0:
            self.current_page -= 1
            self.update_page_navigation()
            self.render_page()
            self.page_changed.emit(self.current_page)
            
    def next_page(self):
        """Go to next page"""
        if self.pdf_document and self.current_page < len(self.pdf_document) - 1:
            self.current_page += 1
            self.update_page_navigation()
            self.render_page()
            self.page_changed.emit(self.current_page)
            
    def zoom_in(self):
        """Zoom in by 25%"""
        new_zoom = min(self.zoom_factor * 1.25, 4.0)  # Max 400%
        self.set_zoom(new_zoom)
        
    def zoom_out(self):
        """Zoom out by 25%"""
        new_zoom = max(self.zoom_factor * 0.8, 0.25)  # Min 25%
        self.set_zoom(new_zoom)
        
    def set_zoom(self, zoom_factor):
        """Set specific zoom factor"""
        self.zoom_factor = zoom_factor
        
        # Update slider
        zoom_percent = int(zoom_factor * 100)
        self.zoom_slider.setValue(zoom_percent)
        
        # Update combo if it's a standard value
        if f"{zoom_percent}%" in [self.zoom_combo.itemText(i) for i in range(self.zoom_combo.count())]:
            self.zoom_combo.setCurrentText(f"{zoom_percent}%")
        else:
            self.zoom_combo.setCurrentText("Custom")
            
        self.render_page()
        self.scale_changed.emit(zoom_factor)
        
    def zoom_changed(self, value):
        """Handle zoom slider change"""
        zoom_factor = value / 100.0
        if abs(self.zoom_factor - zoom_factor) > 0.01:  # Avoid recursive calls
            self.zoom_factor = zoom_factor
            self.render_page()
            self.scale_changed.emit(zoom_factor)
            
    def zoom_preset_changed(self, text):
        """Handle zoom preset combo change"""
        if text.endswith("%"):
            try:
                zoom_percent = int(text[:-1])
                self.set_zoom(zoom_percent / 100.0)
            except ValueError:
                pass
        elif text == "Fit Width":
            self.fit_width()
        elif text == "Fit Page":
            self.fit_page()
            
    def fit_width(self):
        """Fit PDF to width of viewer"""
        if not self.pdf_document:
            return
            
        # Get page dimensions at 100% zoom
        page = self.pdf_document[self.current_page]
        rect = page.rect
        
        # Calculate zoom to fit width
        available_width = self.scroll_area.viewport().width() - 20  # Margin
        zoom_factor = available_width / rect.width
        
        self.set_zoom(zoom_factor)
        
    def fit_page(self):
        """Fit entire page in viewer"""
        if not self.pdf_document:
            return
            
        # Get page dimensions at 100% zoom
        page = self.pdf_document[self.current_page]
        rect = page.rect
        
        # Calculate zoom to fit both width and height
        available_width = self.scroll_area.viewport().width() - 20
        available_height = self.scroll_area.viewport().height() - 20
        
        zoom_width = available_width / rect.width
        zoom_height = available_height / rect.height
        zoom_factor = min(zoom_width, zoom_height)
        
        self.set_zoom(zoom_factor)
        
    def mouse_press_event(self, event):
        """Handle mouse press on PDF"""
        if event.button() == Qt.LeftButton and self.pixmap:
            # Get click position relative to PDF image (screen pixel coordinates)
            screen_x = event.x()
            screen_y = event.y()
            
            # Convert to PDF coordinates (normalized to 100% zoom)
            pdf_x = screen_x / self.zoom_factor
            pdf_y = screen_y / self.zoom_factor
            
            # Emit both coordinate systems
            self.coordinates_clicked.emit(pdf_x, pdf_y)  # For PDF-based operations
            self.screen_coordinates_clicked.emit(screen_x, screen_y)  # For scale calculations
            # Start selection rectangle
            if self._rubber_band is None:
                self._rubber_band = QRubberBand(QRubberBand.Rectangle, self.pdf_label)
            self._origin = QPoint(screen_x, screen_y)
            # Start with a 1x1 rectangle at the origin
            self._rubber_band.setGeometry(QRect(self._origin, QSize(1, 1)))
            self._rubber_band.show()
            
    def mouse_move_event(self, event):
        if self._rubber_band and self.pixmap:
            current = QPoint(event.x(), event.y())
            rect = QRect(self._origin, current).normalized()
            self._rubber_band.setGeometry(rect)

    def mouse_release_event(self, event):
        if self._rubber_band and self.pixmap:
            rect = self._rubber_band.geometry()
            # Convert to PDF coords (normalize by zoom)
            x0 = rect.left() / self.zoom_factor
            y0 = rect.top() / self.zoom_factor
            x1 = rect.right() / self.zoom_factor
            y1 = rect.bottom() / self.zoom_factor
            # Constrain selection to row or column if mode requests
            try:
                page = self.pdf_document[self.current_page]
                width = page.rect.width
                height = page.rect.height
            except Exception:
                page = None
                width = height = None
            if self.selection_mode == 'column' and height is not None:
                y0, y1 = 0.0, float(height)
            elif self.selection_mode == 'row' and width is not None:
                x0, x1 = 0.0, float(width)
            self.selection_rect_pdf = (x0, y0, x1, y1)
            # Notify listeners that a selection is available
            try:
                # Reuse screen_coordinates_clicked to avoid new signal explosion
                self.screen_coordinates_clicked.emit(rect.left(), rect.top())
            except Exception:
                pass
            # Show constrained overlay rectangle (adjusted) for visual feedback
            # Convert constrained PDF rect back to widget pixels
            sx0 = int(x0 * self.zoom_factor)
            sy0 = int(y0 * self.zoom_factor)
            sx1 = int(x1 * self.zoom_factor)
            sy1 = int(y1 * self.zoom_factor)
            overlay_rect = QRect(QPoint(sx0, sy0), QPoint(sx1, sy1)).normalized()
            self._rubber_band.setGeometry(overlay_rect)
            self._rubber_band.show()
            # Auto-hide after a short delay to avoid leftover bands
            QTimer.singleShot(1200, self._rubber_band.hide)

    # Public API
    def set_selection_mode(self, mode: str):
        if mode not in ('free', 'column', 'row'):
            mode = 'free'
        self.selection_mode = mode
        # Update status label
        try:
            self.status_label.setText(f"Page {self.current_page + 1}/{len(self.pdf_document)} - {int(self.zoom_factor*100)}% - mode: {self.selection_mode}")
        except Exception:
            pass

    def get_page_dimensions(self):
        """Get current page dimensions in PDF units"""
        if not self.pdf_document:
            return 0, 0
            
        page = self.pdf_document[self.current_page]
        rect = page.rect
        return rect.width, rect.height
        
    def close_pdf(self):
        """Close the current PDF"""
        if self.pdf_document:
            self.pdf_document.close()
            self.pdf_document = None
            self.pdf_path = None
            self.current_page = 0
            self.pdf_label.clear()
            self.pdf_label.setText("No PDF loaded")
            self.status_label.setText("No PDF loaded")
            self.update_page_navigation()
         
    def zoom_to_rect(self, x: int, y: int, w: int, h: int, padding_ratio: float = 0.15) -> None:
        """Zoom and scroll to fit the given PDF-space rectangle in view.
        The coordinates (x, y, w, h) are in PDF units at 100% zoom.
        """
        try:
            if not self.pdf_document or w is None or h is None:
                return
            # Guard against zero-sized rectangles
            w = max(int(w), 1)
            h = max(int(h), 1)
            # Compute padded rectangle size
            pad_w = int(w * (1.0 + 2.0 * padding_ratio))
            pad_h = int(h * (1.0 + 2.0 * padding_ratio))
            # Available viewport
            vp_w = max(1, self.scroll_area.viewport().width() - 20)
            vp_h = max(1, self.scroll_area.viewport().height() - 20)
            # Determine zoom to fit padded rect
            zoom_width = vp_w / float(pad_w)
            zoom_height = vp_h / float(pad_h)
            new_zoom = max(0.25, min(4.0, min(zoom_width, zoom_height)))
            # Apply zoom (emits scale_changed and renders page)
            self.set_zoom(new_zoom)
            # Center on the rect center at current zoom
            cx_pdf = x + (w // 2)
            cy_pdf = y + (h // 2)
            self.center_on_point(cx_pdf, cy_pdf)
        except Exception:
            # Fail silently in UI helper
            pass
         
    def center_on_point(self, x: int, y: int) -> None:
        """Scroll to center the given PDF-space point (x, y) with the current zoom."""
        try:
            if not self.pdf_document:
                return
            # Convert to screen pixels with current zoom
            sx = int(x * self.zoom_factor)
            sy = int(y * self.zoom_factor)
            # Center inside viewport
            hbar = self.scroll_area.horizontalScrollBar()
            vbar = self.scroll_area.verticalScrollBar()
            vp_w = self.scroll_area.viewport().width()
            vp_h = self.scroll_area.viewport().height()
            target_x = max(0, sx - vp_w // 2)
            target_y = max(0, sy - vp_h // 2)
            hbar.setValue(target_x)
            vbar.setValue(target_y)
        except Exception:
            # Best-effort only
            pass