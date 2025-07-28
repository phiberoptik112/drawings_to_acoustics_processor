"""
PDF Viewer component using PyMuPDF for displaying architectural drawings
"""

import fitz  # PyMuPDF
from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                             QScrollArea, QPushButton, QSlider, QComboBox,
                             QMessageBox, QSizePolicy)
from PyQt5.QtCore import Qt, pyqtSignal, QRect
from PyQt5.QtGui import QPixmap, QImage, QPainter, QPen, QColor
import os


class PDFViewer(QWidget):
    """PDF viewer widget with zoom and page navigation"""
    
    # Signals
    coordinates_clicked = pyqtSignal(float, float)  # PDF coordinates clicked
    scale_changed = pyqtSignal(float)  # Zoom scale changed
    
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
        
        self.init_ui()
        
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
        self.pdf_label.setStyleSheet("border: 1px solid #ccc; background-color: white;")
        self.pdf_label.mousePressEvent = self.mouse_press_event
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
        toolbar.setStyleSheet("background-color: #ecf0f1; padding: 5px;")
        layout = QHBoxLayout()
        
        # Page navigation
        self.prev_btn = QPushButton("◀ Prev")
        self.prev_btn.clicked.connect(self.previous_page)
        self.prev_btn.setEnabled(False)
        
        self.next_btn = QPushButton("Next ▶")
        self.next_btn.clicked.connect(self.next_page)
        self.next_btn.setEnabled(False)
        
        self.page_label = QLabel("Page: 0/0")
        
        # Zoom controls
        zoom_label = QLabel("Zoom:")
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
            
    def next_page(self):
        """Go to next page"""
        if self.pdf_document and self.current_page < len(self.pdf_document) - 1:
            self.current_page += 1
            self.update_page_navigation()
            self.render_page()
            
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
            # Get click position relative to PDF image
            click_x = event.x()
            click_y = event.y()
            
            # Convert to PDF coordinates
            pdf_x = click_x / self.zoom_factor
            pdf_y = click_y / self.zoom_factor
            
            # Emit signal with PDF coordinates
            self.coordinates_clicked.emit(pdf_x, pdf_y)
            
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