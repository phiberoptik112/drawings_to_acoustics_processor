"""
HelpMixin - Mixin class for easy help panel integration
"""

from typing import Optional, Dict, Set
from PySide6.QtWidgets import QWidget, QMainWindow, QDialog, QSplitter, QHBoxLayout
from PySide6.QtCore import Qt, QObject, QEvent
from PySide6.QtGui import QKeySequence, QShortcut

from .help_manager import HelpManager
from .help_panel import HelpPanelWidget


class HelpEventFilter(QObject):
    """
    Event filter that captures hover events on registered controls
    and notifies the help manager.
    """
    
    def __init__(self, help_manager: HelpManager, parent=None):
        super().__init__(parent)
        self._help_manager = help_manager
        self._control_map: Dict[int, str] = {}  # widget id -> control_id
        self._hovered_widget: Optional[int] = None
        
    def register_control(self, widget: QWidget, control_id: str) -> None:
        """
        Register a widget for hover help.
        
        Args:
            widget: The widget to monitor
            control_id: The help content identifier for this control
        """
        widget_id = id(widget)
        self._control_map[widget_id] = control_id
        widget.installEventFilter(self)
        
    def unregister_control(self, widget: QWidget) -> None:
        """
        Unregister a widget from hover help.
        
        Args:
            widget: The widget to stop monitoring
        """
        widget_id = id(widget)
        if widget_id in self._control_map:
            del self._control_map[widget_id]
            widget.removeEventFilter(self)
            
    def eventFilter(self, watched: QObject, event: QEvent) -> bool:
        """Filter events to detect hover."""
        widget_id = id(watched)
        
        if event.type() == QEvent.Enter:
            if widget_id in self._control_map:
                self._hovered_widget = widget_id
                control_id = self._control_map[widget_id]
                self._help_manager.notify_control_hover(control_id)
                
        elif event.type() == QEvent.Leave:
            if widget_id == self._hovered_widget:
                self._hovered_widget = None
                self._help_manager.clear_control_hover()
                
        return False  # Don't consume the event


class HelpMixin:
    """
    Mixin class that adds help panel functionality to windows and dialogs.
    
    Usage:
        class MyWindow(HelpMixin, QMainWindow):
            def init_ui(self):
                # ... existing code ...
                self.setup_help_panel("my_window")
                self.register_help_control(self.some_button, "some_button")
    """
    
    def setup_help_panel(self, context_id: str) -> HelpPanelWidget:
        """
        Set up the help panel for this window/dialog.
        
        This should be called during UI initialization, after the main
        layout/splitter has been created.
        
        Args:
            context_id: The help context identifier for this window
            
        Returns:
            The created HelpPanelWidget
        """
        self._help_context_id = context_id
        self._help_manager = HelpManager()
        self._help_event_filter = HelpEventFilter(self._help_manager, self)
        self._registered_controls: Set[int] = set()
        
        # Create the help panel
        self._help_panel = HelpPanelWidget(self)
        self._help_panel.set_context(context_id)
        
        # Set up F1 shortcut
        self._setup_help_shortcut()
        
        return self._help_panel
        
    def get_help_panel(self) -> Optional[HelpPanelWidget]:
        """Get the help panel widget if it exists."""
        return getattr(self, '_help_panel', None)
        
    def _setup_help_shortcut(self) -> None:
        """Set up the F1 keyboard shortcut to toggle help."""
        shortcut = QShortcut(QKeySequence(Qt.Key_F1), self)
        shortcut.activated.connect(self._toggle_help_panel)
        self._help_shortcut = shortcut
        
    def _toggle_help_panel(self) -> None:
        """Toggle the help panel visibility."""
        if hasattr(self, '_help_panel') and self._help_panel:
            self._help_panel.toggle_panel()
            
    def register_help_control(self, widget: QWidget, control_id: str) -> None:
        """
        Register a widget to show help on hover.
        
        Args:
            widget: The widget to register
            control_id: The control identifier matching the markdown content
        """
        if not hasattr(self, '_help_event_filter'):
            return
            
        widget_id = id(widget)
        if widget_id not in self._registered_controls:
            self._registered_controls.add(widget_id)
            self._help_event_filter.register_control(widget, control_id)
            
    def unregister_help_control(self, widget: QWidget) -> None:
        """
        Unregister a widget from help hover.
        
        Args:
            widget: The widget to unregister
        """
        if not hasattr(self, '_help_event_filter'):
            return
            
        widget_id = id(widget)
        if widget_id in self._registered_controls:
            self._registered_controls.discard(widget_id)
            self._help_event_filter.unregister_control(widget)
            
    def refresh_help_content(self) -> None:
        """Force refresh of help content from disk."""
        if hasattr(self, '_help_panel') and self._help_panel:
            self._help_panel.refresh_content()
            
    def set_help_context(self, context_id: str) -> None:
        """
        Change the help context.
        
        Args:
            context_id: New context identifier
        """
        self._help_context_id = context_id
        if hasattr(self, '_help_panel') and self._help_panel:
            self._help_panel.set_context(context_id)


def add_help_panel_to_layout(
    parent: QWidget,
    main_content: QWidget,
    context_id: str
) -> tuple:
    """
    Helper function to add a help panel to an existing layout.
    
    Creates a horizontal splitter with the main content on the left
    and the help panel on the right.
    
    Args:
        parent: The parent widget
        main_content: The main content widget to wrap
        context_id: The help context identifier
        
    Returns:
        Tuple of (splitter, help_panel)
    """
    # Create help panel
    help_panel = HelpPanelWidget(parent)
    help_panel.set_context(context_id)
    
    # Create splitter
    splitter = QSplitter(Qt.Horizontal, parent)
    splitter.addWidget(main_content)
    splitter.addWidget(help_panel)
    
    # Set stretch factors (main content gets priority)
    splitter.setStretchFactor(0, 1)
    splitter.setStretchFactor(1, 0)
    
    return splitter, help_panel
