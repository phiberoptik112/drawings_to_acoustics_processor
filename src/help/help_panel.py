"""
HelpPanelWidget - Collapsible help panel widget
"""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTextBrowser, QFrame, QScrollArea, QSizePolicy, QSplitter
)
from PySide6.QtCore import Qt, Signal, QPropertyAnimation, QEasingCurve, Property
from PySide6.QtGui import QFont, QIcon

from .help_manager import HelpManager


class HelpPanelWidget(QWidget):
    """
    Collapsible help panel that displays contextual help content.
    
    Features:
    - Collapsible with smooth animation
    - Two sections: Page Overview and Control Info
    - Updates dynamically based on hover events
    - Styled for dark mode
    """
    
    # Signals
    visibility_changed = Signal(bool)  # Emitted when panel is shown/hidden
    
    # Panel width settings
    EXPANDED_WIDTH = 320
    COLLAPSED_WIDTH = 32
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        self._is_expanded = True
        self._help_manager = HelpManager()
        
        self.init_ui()
        self.setup_connections()
        self.apply_styles()
        
    def init_ui(self):
        """Initialize the user interface."""
        self.setMinimumWidth(self.COLLAPSED_WIDTH)
        self.setMaximumWidth(self.EXPANDED_WIDTH)
        
        # Main layout
        main_layout = QHBoxLayout()
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        
        # Toggle button (always visible)
        self.toggle_btn = QPushButton("?")
        self.toggle_btn.setFixedWidth(self.COLLAPSED_WIDTH)
        self.toggle_btn.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Expanding)
        self.toggle_btn.setToolTip("Toggle Help Panel (F1)")
        self.toggle_btn.clicked.connect(self.toggle_panel)
        main_layout.addWidget(self.toggle_btn)
        
        # Content container
        self.content_widget = QWidget()
        content_layout = QVBoxLayout()
        content_layout.setContentsMargins(8, 8, 8, 8)
        content_layout.setSpacing(8)
        
        # Header
        header_layout = QHBoxLayout()
        header_label = QLabel("Help")
        header_label.setFont(QFont("Arial", 12, QFont.Bold))
        header_layout.addWidget(header_label)
        header_layout.addStretch()
        content_layout.addLayout(header_layout)
        
        # Splitter for overview and control sections
        self.splitter = QSplitter(Qt.Vertical)
        
        # Overview section
        overview_container = QWidget()
        overview_layout = QVBoxLayout()
        overview_layout.setContentsMargins(0, 0, 0, 0)
        overview_layout.setSpacing(4)
        
        overview_header = QLabel("Overview")
        overview_header.setFont(QFont("Arial", 10, QFont.Bold))
        overview_header.setStyleSheet("color: #9cdcfe;")
        overview_layout.addWidget(overview_header)
        
        self.overview_browser = QTextBrowser()
        self.overview_browser.setOpenExternalLinks(True)
        self.overview_browser.setMinimumHeight(100)
        overview_layout.addWidget(self.overview_browser)
        
        overview_container.setLayout(overview_layout)
        self.splitter.addWidget(overview_container)
        
        # Control help section
        control_container = QWidget()
        control_layout = QVBoxLayout()
        control_layout.setContentsMargins(0, 0, 0, 0)
        control_layout.setSpacing(4)
        
        self.control_header = QLabel("Control Info")
        self.control_header.setFont(QFont("Arial", 10, QFont.Bold))
        self.control_header.setStyleSheet("color: #9cdcfe;")
        control_layout.addWidget(self.control_header)
        
        self.control_browser = QTextBrowser()
        self.control_browser.setOpenExternalLinks(True)
        self.control_browser.setMinimumHeight(80)
        self.control_browser.setHtml("<p style='color: #808080;'>Hover over a control for help</p>")
        control_layout.addWidget(self.control_browser)
        
        control_container.setLayout(control_layout)
        self.splitter.addWidget(control_container)
        
        # Set splitter proportions
        self.splitter.setSizes([200, 100])
        
        content_layout.addWidget(self.splitter)
        self.content_widget.setLayout(content_layout)
        main_layout.addWidget(self.content_widget)
        
        self.setLayout(main_layout)
        
        # Set initial size
        self.setFixedWidth(self.EXPANDED_WIDTH)
        
    def setup_connections(self):
        """Set up signal connections."""
        self._help_manager.context_changed.connect(self._on_context_changed)
        self._help_manager.control_help_changed.connect(self._on_control_help_changed)
        
    def apply_styles(self):
        """Apply dark mode styling."""
        self.setStyleSheet("""
            HelpPanelWidget {
                background-color: #252526;
                border-left: 1px solid #3c3c3c;
            }
            
            QPushButton {
                background-color: #2d2d30;
                color: #ffffff;
                border: none;
                font-size: 16px;
                font-weight: bold;
            }
            
            QPushButton:hover {
                background-color: #3e3e42;
            }
            
            QPushButton:pressed {
                background-color: #094771;
            }
            
            QTextBrowser {
                background-color: #1e1e1e;
                color: #d4d4d4;
                border: 1px solid #3c3c3c;
                border-radius: 4px;
                padding: 8px;
            }
            
            QLabel {
                color: #ffffff;
            }
            
            QSplitter::handle {
                background-color: #3c3c3c;
                height: 2px;
            }
        """)
        
        # Text browser styling for rendered HTML
        html_style = """
            body {
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
                font-size: 13px;
                line-height: 1.5;
                color: #d4d4d4;
            }
            h1 { color: #4ec9b0; font-size: 16px; margin: 0 0 8px 0; }
            h2 { color: #9cdcfe; font-size: 14px; margin: 12px 0 6px 0; }
            h3 { color: #dcdcaa; font-size: 13px; margin: 10px 0 4px 0; }
            p { margin: 6px 0; }
            code { 
                background-color: #2d2d30; 
                padding: 2px 4px; 
                border-radius: 3px;
                font-family: 'Consolas', 'Monaco', monospace;
            }
            pre {
                background-color: #2d2d30;
                padding: 8px;
                border-radius: 4px;
                overflow-x: auto;
            }
            ul, ol { margin: 6px 0; padding-left: 20px; }
            li { margin: 2px 0; }
            a { color: #3794ff; }
            table { border-collapse: collapse; width: 100%; }
            th, td { 
                border: 1px solid #3c3c3c; 
                padding: 4px 8px; 
                text-align: left;
            }
            th { background-color: #2d2d30; }
        """
        
        self._html_style = html_style
        
    def set_context(self, context_id: str) -> None:
        """
        Set the help context.
        
        Args:
            context_id: The context identifier
        """
        self._help_manager.set_context(context_id)
        
    def _on_context_changed(self, context_id: str) -> None:
        """Handle context change."""
        html = self._help_manager.get_overview_html(context_id)
        self._set_overview_html(html)
        self._clear_control_help()
        
    def _on_control_help_changed(self, control_id: str, html: str) -> None:
        """Handle control help change."""
        if control_id and html:
            self.control_header.setText(f"Control: {control_id}")
            self._set_control_html(html)
        else:
            self._clear_control_help()
            
    def _set_overview_html(self, html: str) -> None:
        """Set the overview browser content with styling."""
        styled_html = f"<style>{self._html_style}</style>{html}"
        self.overview_browser.setHtml(styled_html)
        
    def _set_control_html(self, html: str) -> None:
        """Set the control browser content with styling."""
        styled_html = f"<style>{self._html_style}</style>{html}"
        self.control_browser.setHtml(styled_html)
        
    def _clear_control_help(self) -> None:
        """Clear the control help section."""
        self.control_header.setText("Control Info")
        self.control_browser.setHtml(
            f"<style>{self._html_style}</style>"
            "<p style='color: #808080;'>Hover over a control for help</p>"
        )
        
    def toggle_panel(self) -> None:
        """Toggle the panel expansion state."""
        if self._is_expanded:
            self.collapse()
        else:
            self.expand()
            
    def expand(self) -> None:
        """Expand the panel."""
        if self._is_expanded:
            return
            
        self._is_expanded = True
        self.content_widget.show()
        self.setFixedWidth(self.EXPANDED_WIDTH)
        self.toggle_btn.setText("?")
        self.visibility_changed.emit(True)
        
    def collapse(self) -> None:
        """Collapse the panel."""
        if not self._is_expanded:
            return
            
        self._is_expanded = False
        self.content_widget.hide()
        self.setFixedWidth(self.COLLAPSED_WIDTH)
        self.toggle_btn.setText("?")
        self.visibility_changed.emit(False)
        
    def is_expanded(self) -> bool:
        """Check if the panel is expanded."""
        return self._is_expanded
        
    def refresh_content(self) -> None:
        """Force refresh of the current content."""
        ctx = self._help_manager.get_current_context()
        if ctx:
            self._help_manager.reload_content(ctx)
            html = self._help_manager.get_overview_html(ctx)
            self._set_overview_html(html)
