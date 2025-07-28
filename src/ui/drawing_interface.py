"""
Drawing Interface - PDF viewer with drawing overlay tools
(Placeholder for Phase 2 implementation)
"""

from PyQt5.QtWidgets import QMainWindow, QLabel, QVBoxLayout, QWidget
from PyQt5.QtCore import Qt


class DrawingInterface(QMainWindow):
    """Drawing interface for PDF viewing and drawing tools"""
    
    def __init__(self, drawing_id, project_id):
        super().__init__()
        self.drawing_id = drawing_id
        self.project_id = project_id
        self.init_ui()
        
    def init_ui(self):
        """Initialize the user interface"""
        self.setWindowTitle(f"Drawing Interface - Drawing ID: {self.drawing_id}")
        self.setGeometry(200, 200, 1000, 700)
        
        # Placeholder content
        central_widget = QWidget()
        layout = QVBoxLayout()
        
        placeholder_label = QLabel("Drawing Interface\n\nThis will be implemented in Phase 2 with:\n\n"
                                  "• PDF viewer with PyMuPDF\n"
                                  "• Drawing overlay system\n"
                                  "• Rectangle tool for rooms\n"
                                  "• Component placement tools\n"
                                  "• Segment drawing tools\n"
                                  "• Scale management")
        placeholder_label.setAlignment(Qt.AlignCenter)
        placeholder_label.setStyleSheet("font-size: 14px; color: #7f8c8d; padding: 50px;")
        
        layout.addWidget(placeholder_label)
        central_widget.setLayout(layout)
        self.setCentralWidget(central_widget)