"""
Path Sequence Widget - Displays and allows reordering of HVAC path elements

This widget shows the ordered sequence of components and segments in an HVAC path,
with controls for manual reordering and auto-ordering based on connectivity.
"""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QListWidget, QListWidgetItem,
    QPushButton, QLabel, QFrame, QAbstractItemView, QSizePolicy,
    QMessageBox
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont, QIcon, QColor, QDrag
from typing import List, Dict, Optional, Any


class PathSequenceItem(QListWidgetItem):
    """Custom list item for path elements with type and id info"""
    
    def __init__(self, element_type: str, element_id: int, display_name: str, 
                 extra_info: Dict = None):
        super().__init__()
        self.element_type = element_type
        self.element_id = element_id
        self.display_name = display_name
        self.extra_info = extra_info or {}
        
        # Set display text
        icon = self._get_icon()
        self.setText(f"{icon}  {display_name}")
        
        # Set background color based on type
        self._apply_style()
    
    def _get_icon(self) -> str:
        """Get emoji icon for element type"""
        if self.element_type == 'silencer':
            return '🔇'
        if self.element_type == 'component':
            comp_type = self.extra_info.get('component_type', '').lower()
            icons = {
                'ahu': '🔊',
                'fan': '🔊',
                'mechanical_unit': '🔊',
                'diffuser': '💨',
                'grille': '💨',
                'terminal': '💨',
                'vav': '📦',
                'silencer': '🔇',
                'damper': '▬',
                'elbow': '↪️',
                'tee': '⊥',
                'flex': '〰️',
                'takeoff': '↗️',
            }
            return icons.get(comp_type, '🔲')
        elif self.element_type == 'segment':
            return '━━'
        return '•'
    
    def _apply_style(self):
        """Apply visual style based on element type"""
        self.setForeground(QColor('#333333'))
        
        if self.element_type == 'silencer':
            self.setBackground(QColor('#f3e5f5'))  # Light purple for silencers
        elif self.element_type == 'component':
            comp_type = self.extra_info.get('component_type', '').lower()
            if comp_type in ('ahu', 'fan', 'mechanical_unit'):
                self.setBackground(QColor('#fff3e0'))  # Light orange for sources
            elif comp_type in ('diffuser', 'grille', 'terminal'):
                self.setBackground(QColor('#e8f5e9'))  # Light green for terminals
            else:
                self.setBackground(QColor('#e3f2fd'))  # Light blue for other components
        elif self.element_type == 'segment':
            self.setBackground(QColor('#f5f5f5'))  # Light gray for segments
    
    def to_dict(self) -> Dict:
        """Convert to dictionary for sequence storage"""
        return {
            'type': self.element_type,
            'id': self.element_id
        }


class PathSequenceWidget(QWidget):
    """
    Widget for displaying and reordering HVAC path elements.
    
    Shows the sequence: Component -> Segment -> Component -> Segment -> ...
    Allows drag-drop reordering and has up/down buttons.
    """
    
    # Signals
    sequence_changed = Signal(list)  # Emits new sequence when changed
    element_selected = Signal(str, int)  # Emits (element_type, element_id) when selected
    element_double_clicked = Signal(str, int)  # For edit requests
    silencer_removed = Signal(int)  # Emits component_id of removed silencer
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        # Data storage
        self.components_map: Dict[int, Dict] = {}  # component_id -> component data
        self.segments_map: Dict[int, Dict] = {}    # segment_id -> segment data
        
        self._init_ui()
    
    def _init_ui(self):
        """Initialize the widget UI"""
        # Set base stylesheet for proper text contrast
        self.setStyleSheet("""
            PathSequenceWidget {
                background-color: #f5f5f5;
            }
            PathSequenceWidget QLabel {
                color: #333;
                background-color: transparent;
            }
            PathSequenceWidget QPushButton {
                background-color: #e0e0e0;
                color: #333;
                border: 1px solid #ccc;
                border-radius: 3px;
                padding: 4px 8px;
            }
            PathSequenceWidget QPushButton:hover {
                background-color: #d0d0d0;
            }
            PathSequenceWidget QPushButton:disabled {
                background-color: #f0f0f0;
                color: #999;
            }
        """)
        
        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)
        
        # Header with title
        header_layout = QHBoxLayout()
        title_label = QLabel("Path Element Sequence")
        title_label.setFont(QFont("Arial", 10, QFont.Bold))
        header_layout.addWidget(title_label)
        header_layout.addStretch()
        
        # Auto-order button
        self.auto_order_btn = QPushButton("Auto-Order")
        self.auto_order_btn.setToolTip("Automatically order elements based on connectivity")
        self.auto_order_btn.clicked.connect(self._on_auto_order)
        self.auto_order_btn.setFixedWidth(90)
        header_layout.addWidget(self.auto_order_btn)
        
        layout.addLayout(header_layout)
        
        # Main content with list and buttons
        content_layout = QHBoxLayout()
        content_layout.setSpacing(8)
        
        # List widget with drag-drop
        self.list_widget = QListWidget()
        self.list_widget.setDragDropMode(QAbstractItemView.InternalMove)
        self.list_widget.setDefaultDropAction(Qt.MoveAction)
        self.list_widget.setSelectionMode(QAbstractItemView.SingleSelection)
        self.list_widget.setMinimumHeight(200)
        self.list_widget.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        
        # Style the list widget - explicitly set colors for proper contrast
        self.list_widget.setStyleSheet("""
            QListWidget {
                border: 1px solid #ddd;
                border-radius: 4px;
                background-color: #ffffff;
                color: #333;
            }
            QListWidget::item {
                padding: 8px;
                border-bottom: 1px solid #eee;
                color: #333;
            }
            QListWidget::item:selected {
                background-color: #bbdefb;
                color: #333;
            }
            QListWidget::item:hover {
                background-color: #e3f2fd;
                color: #333;
            }
        """)
        
        # Connect list signals
        self.list_widget.itemSelectionChanged.connect(self._on_selection_changed)
        self.list_widget.itemDoubleClicked.connect(self._on_item_double_clicked)
        self.list_widget.model().rowsMoved.connect(self._on_rows_moved)
        
        content_layout.addWidget(self.list_widget, 1)
        
        # Buttons panel
        buttons_layout = QVBoxLayout()
        buttons_layout.setSpacing(4)
        
        self.move_up_btn = QPushButton("▲ Up")
        self.move_up_btn.setToolTip("Move selected element up")
        self.move_up_btn.clicked.connect(self._on_move_up)
        self.move_up_btn.setFixedWidth(70)
        self.move_up_btn.setEnabled(False)
        buttons_layout.addWidget(self.move_up_btn)
        
        self.move_down_btn = QPushButton("▼ Down")
        self.move_down_btn.setToolTip("Move selected element down")
        self.move_down_btn.clicked.connect(self._on_move_down)
        self.move_down_btn.setFixedWidth(70)
        self.move_down_btn.setEnabled(False)
        buttons_layout.addWidget(self.move_down_btn)
        
        buttons_layout.addSpacing(16)
        
        self.move_top_btn = QPushButton("⬆ Top")
        self.move_top_btn.setToolTip("Move selected element to top")
        self.move_top_btn.clicked.connect(self._on_move_top)
        self.move_top_btn.setFixedWidth(70)
        self.move_top_btn.setEnabled(False)
        buttons_layout.addWidget(self.move_top_btn)
        
        self.move_bottom_btn = QPushButton("⬇ Bottom")
        self.move_bottom_btn.setToolTip("Move selected element to bottom")
        self.move_bottom_btn.clicked.connect(self._on_move_bottom)
        self.move_bottom_btn.setFixedWidth(70)
        self.move_bottom_btn.setEnabled(False)
        buttons_layout.addWidget(self.move_bottom_btn)
        
        buttons_layout.addSpacing(16)
        
        self.remove_silencer_btn = QPushButton("✕ Remove")
        self.remove_silencer_btn.setToolTip("Remove selected silencer from path")
        self.remove_silencer_btn.clicked.connect(self._on_remove_silencer)
        self.remove_silencer_btn.setFixedWidth(70)
        self.remove_silencer_btn.setEnabled(False)
        self.remove_silencer_btn.setStyleSheet("""
            QPushButton {
                background-color: #ffcdd2;
                color: #b71c1c;
                border: 1px solid #ef9a9a;
                border-radius: 3px;
                padding: 4px 8px;
            }
            QPushButton:hover { background-color: #ef9a9a; }
            QPushButton:disabled { background-color: #f0f0f0; color: #999; border: 1px solid #ccc; }
        """)
        buttons_layout.addWidget(self.remove_silencer_btn)
        
        buttons_layout.addStretch()
        content_layout.addLayout(buttons_layout)
        
        layout.addLayout(content_layout)
        
        # Info label
        self.info_label = QLabel("Drag items or use buttons to reorder")
        self.info_label.setStyleSheet("color: #666; font-size: 9px; background-color: transparent;")
        layout.addWidget(self.info_label)
        
        self.setLayout(layout)
    
    def set_data(self, components: List[Dict], segments: List[Dict], 
                 sequence: List[Dict] = None):
        """
        Set the component and segment data, optionally with an explicit sequence.
        
        Args:
            components: List of component dictionaries with 'id', 'name', 'component_type'
            segments: List of segment dictionaries with 'id', 'from_component_id', 'to_component_id'
            sequence: Optional explicit sequence, or None to compute from segments
        """
        # Store data in maps
        self.components_map = {c.get('id'): c for c in components if c.get('id')}
        self.segments_map = {s.get('id'): s for s in segments if s.get('id')}
        
        # Get or compute sequence
        if sequence:
            self._populate_from_sequence(sequence)
        else:
            # Compute sequence from segments
            computed_sequence = self._compute_sequence_from_segments(segments)
            self._populate_from_sequence(computed_sequence)
    
    def _compute_sequence_from_segments(self, segments: List[Dict]) -> List[Dict]:
        """Compute element sequence from segment connectivity"""
        if not segments:
            return []
        
        sequence = []
        # Sort segments by segment_order if available
        ordered_segments = sorted(segments, key=lambda s: s.get('segment_order', 0))
        
        seen_component_ids = set()
        
        for seg in ordered_segments:
            from_id = seg.get('from_component_id')
            to_id = seg.get('to_component_id')
            seg_id = seg.get('id')
            
            # Add from_component if not already added
            if from_id and from_id not in seen_component_ids:
                sequence.append({'type': 'component', 'id': from_id})
                seen_component_ids.add(from_id)
            
            # Add segment
            if seg_id:
                sequence.append({'type': 'segment', 'id': seg_id})
            
            # Add to_component if not already added
            if to_id and to_id not in seen_component_ids:
                sequence.append({'type': 'component', 'id': to_id})
                seen_component_ids.add(to_id)
        
        return sequence
    
    def _populate_from_sequence(self, sequence: List[Dict]):
        """Populate the list widget from a sequence"""
        self.list_widget.clear()
        
        for item in sequence:
            element_type = item.get('type')
            element_id = item.get('id')
            
            if element_type == 'component':
                comp_data = self.components_map.get(element_id)
                if comp_data:
                    display_name = comp_data.get('name', f'Component {element_id}')
                    extra_info = {
                        'component_type': comp_data.get('component_type', ''),
                        'custom_type_label': comp_data.get('custom_type_label'),
                        'noise_level': comp_data.get('noise_level'),
                    }
                    list_item = PathSequenceItem('component', element_id, display_name, extra_info)
                    self.list_widget.addItem(list_item)
            
            elif element_type == 'silencer':
                comp_data = self.components_map.get(element_id)
                if comp_data:
                    display_name = comp_data.get('name', f'Silencer {element_id}')
                    extra_info = {
                        'component_type': 'silencer',
                        'selected_product_id': comp_data.get('selected_product_id'),
                        'silencer_model': comp_data.get('silencer_model', ''),
                    }
                    list_item = PathSequenceItem('silencer', element_id, display_name, extra_info)
                    self.list_widget.addItem(list_item)
            
            elif element_type == 'segment':
                seg_data = self.segments_map.get(element_id)
                if seg_data:
                    length = seg_data.get('length', 0)
                    shape = seg_data.get('duct_shape', 'rectangular')
                    
                    from_id = seg_data.get('from_component_id')
                    to_id = seg_data.get('to_component_id')
                    from_name = self.components_map.get(from_id, {}).get('name', '?')
                    to_name = self.components_map.get(to_id, {}).get('name', '?')
                    
                    display_name = f"Segment: {from_name} → {to_name} ({length:.1f} ft)"
                    extra_info = {
                        'length': length,
                        'shape': shape,
                        'from_component_id': from_id,
                        'to_component_id': to_id,
                    }
                    list_item = PathSequenceItem('segment', element_id, display_name, extra_info)
                    self.list_widget.addItem(list_item)
        
        self._update_button_states()
    
    def get_sequence(self) -> List[Dict]:
        """Get the current sequence as a list of dictionaries"""
        sequence = []
        for i in range(self.list_widget.count()):
            item = self.list_widget.item(i)
            if isinstance(item, PathSequenceItem):
                sequence.append(item.to_dict())
        return sequence
    
    def _update_button_states(self):
        """Update button enabled states based on selection"""
        selected = self.list_widget.currentItem()
        has_selection = selected is not None
        current_row = self.list_widget.currentRow()
        count = self.list_widget.count()
        
        self.move_up_btn.setEnabled(has_selection and current_row > 0)
        self.move_top_btn.setEnabled(has_selection and current_row > 0)
        self.move_down_btn.setEnabled(has_selection and current_row < count - 1)
        self.move_bottom_btn.setEnabled(has_selection and current_row < count - 1)
        
        is_silencer = (
            has_selection
            and isinstance(selected, PathSequenceItem)
            and selected.element_type == 'silencer'
        )
        self.remove_silencer_btn.setEnabled(is_silencer)
    
    def _on_selection_changed(self):
        """Handle selection change in list"""
        self._update_button_states()
        
        current = self.list_widget.currentItem()
        if isinstance(current, PathSequenceItem):
            self.element_selected.emit(current.element_type, current.element_id)
    
    def _on_item_double_clicked(self, item: QListWidgetItem):
        """Handle double-click on item"""
        if isinstance(item, PathSequenceItem):
            self.element_double_clicked.emit(item.element_type, item.element_id)
    
    def _on_rows_moved(self, parent, start, end, destination, row):
        """Handle drag-drop row move"""
        self._emit_sequence_changed()
    
    def _on_move_up(self):
        """Move selected item up"""
        current_row = self.list_widget.currentRow()
        if current_row > 0:
            item = self.list_widget.takeItem(current_row)
            self.list_widget.insertItem(current_row - 1, item)
            self.list_widget.setCurrentRow(current_row - 1)
            self._emit_sequence_changed()
    
    def _on_move_down(self):
        """Move selected item down"""
        current_row = self.list_widget.currentRow()
        if current_row < self.list_widget.count() - 1:
            item = self.list_widget.takeItem(current_row)
            self.list_widget.insertItem(current_row + 1, item)
            self.list_widget.setCurrentRow(current_row + 1)
            self._emit_sequence_changed()
    
    def _on_move_top(self):
        """Move selected item to top"""
        current_row = self.list_widget.currentRow()
        if current_row > 0:
            item = self.list_widget.takeItem(current_row)
            self.list_widget.insertItem(0, item)
            self.list_widget.setCurrentRow(0)
            self._emit_sequence_changed()
    
    def _on_move_bottom(self):
        """Move selected item to bottom"""
        current_row = self.list_widget.currentRow()
        if current_row < self.list_widget.count() - 1:
            item = self.list_widget.takeItem(current_row)
            self.list_widget.insertItem(self.list_widget.count(), item)
            self.list_widget.setCurrentRow(self.list_widget.count() - 1)
            self._emit_sequence_changed()
    
    def _on_auto_order(self):
        """Auto-order elements based on connectivity, preserving silencer positions"""
        segments = list(self.segments_map.values())
        if not segments:
            return
        
        # Capture existing silencer entries and their relative positions
        old_sequence = self.get_sequence()
        silencer_positions = {}
        for i, item in enumerate(old_sequence):
            if item['type'] == 'silencer':
                prev_item = old_sequence[i - 1] if i > 0 else None
                silencer_positions[item['id']] = prev_item
        
        base_sequence = self._compute_sequence_from_segments(segments)
        
        # Re-insert silencers after the same preceding element
        for sil_id, prev_item in silencer_positions.items():
            insert_idx = len(base_sequence)
            if prev_item:
                for j, entry in enumerate(base_sequence):
                    if entry['type'] == prev_item['type'] and entry['id'] == prev_item['id']:
                        insert_idx = j + 1
                        break
            base_sequence.insert(insert_idx, {'type': 'silencer', 'id': sil_id})
        
        self._populate_from_sequence(base_sequence)
        self._emit_sequence_changed()
        self.info_label.setText("Sequence reordered based on connectivity")
    
    def insert_silencer_at(self, row: int, component_id: int, silencer_data: Dict):
        """Insert a silencer element after the given row index.
        
        Args:
            row: Row index after which to insert (-1 to append at end)
            component_id: The HVACComponent id for this silencer
            silencer_data: Dict with 'name', 'selected_product_id', 'silencer_model', etc.
        """
        self.components_map[component_id] = silencer_data
        
        display_name = silencer_data.get('name', f'Silencer {component_id}')
        extra_info = {
            'component_type': 'silencer',
            'selected_product_id': silencer_data.get('selected_product_id'),
            'silencer_model': silencer_data.get('silencer_model', ''),
        }
        list_item = PathSequenceItem('silencer', component_id, display_name, extra_info)
        
        insert_row = row + 1 if row >= 0 else self.list_widget.count()
        self.list_widget.insertItem(insert_row, list_item)
        self.list_widget.setCurrentRow(insert_row)
        self._emit_sequence_changed()
    
    def _on_remove_silencer(self):
        """Remove the selected silencer from the sequence"""
        current = self.list_widget.currentItem()
        if not isinstance(current, PathSequenceItem) or current.element_type != 'silencer':
            return
        
        component_id = current.element_id
        row = self.list_widget.currentRow()
        self.list_widget.takeItem(row)
        
        if component_id in self.components_map:
            del self.components_map[component_id]
        
        self.silencer_removed.emit(component_id)
        self._emit_sequence_changed()
    
    def _emit_sequence_changed(self):
        """Emit the sequence_changed signal with current sequence"""
        sequence = self.get_sequence()
        self.sequence_changed.emit(sequence)
        self._update_button_states()
    
    def highlight_element(self, element_type: str, element_id: int):
        """Highlight a specific element in the list"""
        for i in range(self.list_widget.count()):
            item = self.list_widget.item(i)
            if isinstance(item, PathSequenceItem):
                if item.element_type == element_type and item.element_id == element_id:
                    self.list_widget.setCurrentItem(item)
                    self.list_widget.scrollToItem(item)
                    break
    
    def clear(self):
        """Clear all data"""
        self.list_widget.clear()
        self.components_map.clear()
        self.segments_map.clear()
        self._update_button_states()


class PathSequenceDialog(QWidget):
    """
    A dialog-like widget for editing path sequence with save/cancel buttons.
    Can be embedded in other dialogs or used standalone.
    """
    
    sequence_saved = Signal(list)  # Emitted when sequence is saved
    cancelled = Signal()  # Emitted when cancelled
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._init_ui()
        self._original_sequence = []
    
    def _init_ui(self):
        # Set base stylesheet for proper text contrast
        self.setStyleSheet("""
            PathSequenceDialog {
                background-color: #f5f5f5;
            }
            PathSequenceDialog QWidget {
                background-color: #f5f5f5;
                color: #333;
            }
            PathSequenceDialog QLabel {
                color: #333;
                background-color: transparent;
            }
            PathSequenceDialog QPushButton {
                background-color: #e0e0e0;
                color: #333;
                border: 1px solid #ccc;
                border-radius: 3px;
                padding: 4px 8px;
            }
            PathSequenceDialog QPushButton:hover {
                background-color: #d0d0d0;
            }
        """)
        
        layout = QVBoxLayout()
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(10)
        
        # Sequence widget
        self.sequence_widget = PathSequenceWidget()
        layout.addWidget(self.sequence_widget, 1)
        
        # Buttons
        buttons_layout = QHBoxLayout()
        buttons_layout.addStretch()
        
        self.reset_btn = QPushButton("Reset")
        self.reset_btn.setToolTip("Reset to original sequence")
        self.reset_btn.clicked.connect(self._on_reset)
        buttons_layout.addWidget(self.reset_btn)
        
        self.cancel_btn = QPushButton("Cancel")
        self.cancel_btn.clicked.connect(self._on_cancel)
        buttons_layout.addWidget(self.cancel_btn)
        
        self.save_btn = QPushButton("Save Order")
        self.save_btn.setStyleSheet("""
            QPushButton {
                background-color: #1976D2;
                color: white;
                padding: 6px 16px;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #1565C0;
            }
        """)
        self.save_btn.clicked.connect(self._on_save)
        buttons_layout.addWidget(self.save_btn)
        
        layout.addLayout(buttons_layout)
        self.setLayout(layout)
    
    def set_data(self, components: List[Dict], segments: List[Dict], 
                 sequence: List[Dict] = None):
        """Set data and store original sequence for reset"""
        self.sequence_widget.set_data(components, segments, sequence)
        self._original_sequence = self.sequence_widget.get_sequence()
    
    def _on_reset(self):
        """Reset to original sequence"""
        if self._original_sequence:
            self.sequence_widget._populate_from_sequence(self._original_sequence)
    
    def _on_cancel(self):
        """Cancel without saving"""
        self.cancelled.emit()
    
    def _on_save(self):
        """Save the current sequence"""
        sequence = self.sequence_widget.get_sequence()
        self.sequence_saved.emit(sequence)
    
    def get_sequence(self) -> List[Dict]:
        """Get current sequence"""
        return self.sequence_widget.get_sequence()
