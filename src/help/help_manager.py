"""
HelpManager - Central manager for loading and providing help content
"""

import os
import re
from pathlib import Path
from typing import Dict, Optional, Tuple
from PySide6.QtCore import QObject, Signal

try:
    import markdown
    MARKDOWN_AVAILABLE = True
except ImportError:
    MARKDOWN_AVAILABLE = False


class HelpManager(QObject):
    """
    Singleton manager for help content.
    
    Loads markdown files from the content directory and provides
    parsed HTML content for display in help panels.
    """
    
    _instance = None
    
    # Signals
    context_changed = Signal(str)  # Emits context_id when context changes
    control_help_changed = Signal(str, str)  # Emits (control_id, html_content)
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
            
        super().__init__()
        self._initialized = True
        
        # Cache for loaded content
        self._content_cache: Dict[str, str] = {}  # context_id -> raw markdown
        self._html_cache: Dict[str, str] = {}  # context_id -> rendered HTML
        self._control_cache: Dict[str, Dict[str, str]] = {}  # context_id -> {control_id -> html}
        
        # Current context
        self._current_context: Optional[str] = None
        
        # Content directory
        self._content_dir = Path(__file__).parent / "content"
        
        # Markdown converter
        if MARKDOWN_AVAILABLE:
            self._md = markdown.Markdown(
                extensions=['tables', 'fenced_code', 'toc'],
                output_format='html5'
            )
        else:
            self._md = None
            
    @property
    def content_dir(self) -> Path:
        """Get the content directory path."""
        return self._content_dir
        
    def set_context(self, context_id: str) -> None:
        """
        Set the current help context.
        
        Args:
            context_id: The context identifier (e.g., 'project_dashboard', 'drawing_interface')
        """
        if context_id != self._current_context:
            self._current_context = context_id
            self._load_context_content(context_id)
            self.context_changed.emit(context_id)
            
    def get_current_context(self) -> Optional[str]:
        """Get the current context ID."""
        return self._current_context
        
    def get_overview_html(self, context_id: Optional[str] = None) -> str:
        """
        Get the overview/general help HTML for a context.
        
        Args:
            context_id: The context to get help for. If None, uses current context.
            
        Returns:
            HTML string with the overview content.
        """
        ctx = context_id or self._current_context
        if not ctx:
            return self._default_overview_html()
            
        self._load_context_content(ctx)
        return self._html_cache.get(ctx, self._default_overview_html())
        
    def get_control_help_html(self, control_id: str, context_id: Optional[str] = None) -> str:
        """
        Get help HTML for a specific control.
        
        Args:
            control_id: The control identifier
            context_id: The context to look in. If None, uses current context.
            
        Returns:
            HTML string with the control help, or empty string if not found.
        """
        ctx = context_id or self._current_context
        if not ctx:
            return ""
            
        self._load_context_content(ctx)
        
        if ctx in self._control_cache:
            return self._control_cache[ctx].get(control_id, "")
        return ""
        
    def notify_control_hover(self, control_id: str) -> None:
        """
        Notify that a control is being hovered.
        
        Args:
            control_id: The control identifier
        """
        html = self.get_control_help_html(control_id)
        if html:
            self.control_help_changed.emit(control_id, html)
            
    def clear_control_hover(self) -> None:
        """Clear the control hover state."""
        self.control_help_changed.emit("", "")
        
    def _load_context_content(self, context_id: str) -> None:
        """
        Load and parse content for a context if not already cached.
        
        Args:
            context_id: The context identifier
        """
        if context_id in self._html_cache:
            return
            
        # Find the markdown file
        md_path = self._find_content_file(context_id)
        if not md_path or not md_path.exists():
            self._html_cache[context_id] = self._default_overview_html()
            self._control_cache[context_id] = {}
            return
            
        # Read the markdown content
        try:
            with open(md_path, 'r', encoding='utf-8') as f:
                content = f.read()
        except Exception as e:
            print(f"Error reading help file {md_path}: {e}")
            self._html_cache[context_id] = self._default_overview_html()
            self._control_cache[context_id] = {}
            return
            
        self._content_cache[context_id] = content
        
        # Parse the content
        overview_md, controls = self._parse_content(content)
        
        # Convert to HTML
        self._html_cache[context_id] = self._markdown_to_html(overview_md)
        
        # Convert control help to HTML
        self._control_cache[context_id] = {}
        for ctrl_id, ctrl_md in controls.items():
            self._control_cache[context_id][ctrl_id] = self._markdown_to_html(ctrl_md)
            
    def _find_content_file(self, context_id: str) -> Optional[Path]:
        """
        Find the markdown file for a context.
        
        Args:
            context_id: The context identifier
            
        Returns:
            Path to the markdown file, or None if not found.
        """
        # Check for direct file match
        direct_path = self._content_dir / f"{context_id}.md"
        if direct_path.exists():
            return direct_path
            
        # Check in dialogs subdirectory
        dialog_path = self._content_dir / "dialogs" / f"{context_id}.md"
        if dialog_path.exists():
            return dialog_path
            
        # Check with underscores converted to path separators
        parts = context_id.split('.')
        if len(parts) > 1:
            nested_path = self._content_dir / '/'.join(parts[:-1]) / f"{parts[-1]}.md"
            if nested_path.exists():
                return nested_path
                
        return None
        
    def _parse_content(self, content: str) -> Tuple[str, Dict[str, str]]:
        """
        Parse markdown content into overview and control sections.
        
        The format expected:
        # Title
        
        Overview content...
        
        ---
        
        ## Controls
        
        ### control_id
        Control help text...
        
        Args:
            content: Raw markdown content
            
        Returns:
            Tuple of (overview_markdown, {control_id: control_markdown})
        """
        # Split on the --- separator
        parts = re.split(r'\n---+\n', content, maxsplit=1)
        
        overview = parts[0].strip()
        controls: Dict[str, str] = {}
        
        if len(parts) > 1:
            controls_section = parts[1]
            
            # Find all ### headings and their content
            # Pattern matches ### heading and captures content until next ### or end
            pattern = r'###\s+(\S+)\s*\n(.*?)(?=###\s+\S+|\Z)'
            matches = re.findall(pattern, controls_section, re.DOTALL)
            
            for ctrl_id, ctrl_content in matches:
                controls[ctrl_id.strip()] = ctrl_content.strip()
                
        return overview, controls
        
    def _markdown_to_html(self, md_content: str) -> str:
        """
        Convert markdown to HTML.
        
        Args:
            md_content: Markdown content
            
        Returns:
            HTML string
        """
        if not md_content:
            return ""
            
        if self._md:
            self._md.reset()
            return self._md.convert(md_content)
        else:
            # Fallback: basic text display
            return f"<pre>{md_content}</pre>"
            
    def _default_overview_html(self) -> str:
        """Get default overview HTML when no content is available."""
        return """
        <h2>Help</h2>
        <p>No help content is available for this view.</p>
        <p>Hover over controls to see contextual help.</p>
        """
        
    def reload_content(self, context_id: Optional[str] = None) -> None:
        """
        Force reload of content from disk.
        
        Args:
            context_id: Specific context to reload, or None to reload all.
        """
        if context_id:
            self._content_cache.pop(context_id, None)
            self._html_cache.pop(context_id, None)
            self._control_cache.pop(context_id, None)
            self._load_context_content(context_id)
        else:
            self._content_cache.clear()
            self._html_cache.clear()
            self._control_cache.clear()
            if self._current_context:
                self._load_context_content(self._current_context)
                
    def get_available_contexts(self) -> list:
        """
        Get list of available help contexts.
        
        Returns:
            List of context IDs that have help content.
        """
        contexts = []
        
        if not self._content_dir.exists():
            return contexts
            
        # Find all .md files
        for md_file in self._content_dir.glob("*.md"):
            contexts.append(md_file.stem)
            
        # Check dialogs subdirectory
        dialogs_dir = self._content_dir / "dialogs"
        if dialogs_dir.exists():
            for md_file in dialogs_dir.glob("*.md"):
                contexts.append(md_file.stem)
                
        return contexts
