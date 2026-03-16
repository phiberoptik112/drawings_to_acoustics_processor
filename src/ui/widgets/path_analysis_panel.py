"""
Path Analysis Panel - Collapsible panel showing HVAC path calculation alongside drawing

This panel displays the path flow diagram with interactive cards that link
to the drawing overlay for visual correlation between physical path and calculations.
"""

from typing import Optional, Dict, List, Any
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QComboBox, QScrollArea, QFrame, QSizePolicy, QSplitter,
    QToolButton, QMessageBox, QTabWidget, QGroupBox,
    QTableWidget, QTableWidgetItem, QHeaderView
)
from PySide6.QtCore import Qt, Signal, QTimer
from PySide6.QtGui import QFont

from models import get_session
from models.hvac import HVACPath, HVACSegment, HVACComponent, SilencerProduct
from sqlalchemy.orm import selectinload

from .path_element_card import PathElementCard, PathArrow, PathResultsSummary
from .path_sequence_widget import PathSequenceWidget
from .nc_results_table import NCResultsTableWidget


class PathAnalysisPanel(QWidget):
    """Panel showing HVAC path calculation alongside drawing"""

    # Signals for drawing coordination
    element_hover_requested = Signal(object, str)  # element_id, element_type - highlight on drawing
    element_unhover_requested = Signal()  # clear highlight on drawing
    element_select_requested = Signal(object, str)  # element_id, element_type - select on drawing
    pan_to_element_requested = Signal(object, str)  # element_id, element_type - pan drawing to element
    path_changed = Signal(int)  # Emitted when path selection changes
    edit_element_requested = Signal(object, str)  # element_id, element_type - open edit dialog

    # Signals for silencer placement mode
    silencer_placement_requested = Signal(int, int, dict)  # path_id, component_id, silencer_data
    
    def __init__(self, project_id: int = None, parent=None):
        super().__init__(parent)
        self.project_id = project_id
        self.current_path_id: Optional[int] = None
        self.current_path: Optional[HVACPath] = None
        self.calculation_results: Optional[Dict] = None
        self._element_cards: List[PathElementCard] = []
        
        # Calculation engine
        self._path_calculator = None
        
        self._init_ui()
        self._load_paths()
    
    def _init_ui(self):
        """Initialize the panel UI"""
        self.setMinimumWidth(300)
        self.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Expanding)
        
        # Ensure light background and dark text for the entire panel and all child widgets
        self.setStyleSheet("""
            PathAnalysisPanel {
                background-color: #f5f5f5;
                color: #333;
            }
            PathAnalysisPanel QWidget {
                background-color: #f5f5f5;
                color: #333;
            }
            PathAnalysisPanel QLabel {
                color: #333;
                background-color: transparent;
            }
            PathAnalysisPanel QComboBox {
                background-color: white;
                color: #333;
                border: 1px solid #ccc;
                padding: 4px;
            }
            PathAnalysisPanel QComboBox QAbstractItemView {
                background-color: white;
                color: #333;
                selection-background-color: #bbdefb;
                selection-color: #333;
            }
            PathAnalysisPanel QComboBox::drop-down {
                border: none;
            }
            PathAnalysisPanel QPushButton, PathAnalysisPanel QToolButton {
                background-color: #e0e0e0;
                color: #333;
                border: 1px solid #ccc;
                border-radius: 3px;
                padding: 4px 8px;
            }
            PathAnalysisPanel QPushButton:hover, PathAnalysisPanel QToolButton:hover {
                background-color: #d0d0d0;
            }
            PathAnalysisPanel QPushButton:disabled {
                background-color: #f0f0f0;
                color: #999;
            }
            PathAnalysisPanel QFrame {
                background-color: #f5f5f5;
                color: #333;
            }
            PathAnalysisPanel QScrollArea {
                background-color: #fafafa;
            }
            PathAnalysisPanel QScrollArea QWidget {
                background-color: #fafafa;
                color: #333;
            }
        """)
        
        layout = QVBoxLayout()
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(8)
        
        # Header with collapse button and title
        header_layout = QHBoxLayout()
        
        self.collapse_btn = QToolButton()
        self.collapse_btn.setText("◀")
        self.collapse_btn.setToolTip("Collapse panel")
        self.collapse_btn.clicked.connect(self._toggle_collapse)
        header_layout.addWidget(self.collapse_btn)
        
        title_label = QLabel("Path Analysis")
        title_label.setFont(QFont("Arial", 11, QFont.Bold))
        header_layout.addWidget(title_label)
        header_layout.addStretch()
        
        layout.addLayout(header_layout)
        
        # Path selector
        selector_layout = QHBoxLayout()
        selector_layout.addWidget(QLabel("Path:"))
        
        self.path_selector = QComboBox()
        self.path_selector.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.path_selector.currentIndexChanged.connect(self._on_path_selection_changed)
        selector_layout.addWidget(self.path_selector, 1)
        
        self.recalc_btn = QPushButton("🔄")
        self.recalc_btn.setToolTip("Recalculate path")
        self.recalc_btn.setFixedWidth(32)
        self.recalc_btn.clicked.connect(self._recalculate_path)
        selector_layout.addWidget(self.recalc_btn)
        
        layout.addLayout(selector_layout)
        
        # Main content area with tabs
        self.content_widget = QWidget()
        content_layout = QVBoxLayout()
        content_layout.setContentsMargins(0, 0, 0, 0)
        
        # Tab widget for diagram and reordering views
        self.tabs = QTabWidget()
        self.tabs.setStyleSheet("""
            QTabWidget::pane {
                border: 1px solid #ccc;
                background-color: #fafafa;
                color: #333;
            }
            QTabWidget QWidget {
                background-color: #fafafa;
                color: #333;
            }
            QTabBar::tab {
                background-color: #e0e0e0;
                color: #333;
                padding: 6px 12px;
                border: 1px solid #ccc;
                border-bottom: none;
            }
            QTabBar::tab:selected {
                background-color: #fafafa;
                color: #333;
            }
            QTabBar::tab:hover {
                background-color: #d0d0d0;
                color: #333;
            }
        """)
        
        # Diagram tab
        diagram_widget = QWidget()
        diagram_tab_layout = QVBoxLayout()
        diagram_tab_layout.setContentsMargins(0, 0, 0, 0)
        
        # Scrollable diagram area
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll.setStyleSheet("""
            QScrollArea {
                border: none;
                background-color: #fafafa;
            }
            QScrollArea QWidget {
                background-color: #fafafa;
                color: #333;
            }
            QScrollArea QLabel {
                color: #333;
                background-color: transparent;
            }
        """)
        
        self.diagram_container = QWidget()
        self.diagram_layout = QVBoxLayout()
        self.diagram_layout.setContentsMargins(4, 4, 4, 4)
        self.diagram_layout.setSpacing(0)
        self.diagram_container.setLayout(self.diagram_layout)
        scroll.setWidget(self.diagram_container)
        diagram_tab_layout.addWidget(scroll, 1)
        diagram_widget.setLayout(diagram_tab_layout)
        
        self.tabs.addTab(diagram_widget, "Diagram")
        
        # Reorder tab
        reorder_widget = QWidget()
        reorder_tab_layout = QVBoxLayout()
        reorder_tab_layout.setContentsMargins(4, 4, 4, 4)

        # Sequence widget
        self.path_sequence_widget = PathSequenceWidget()
        self.path_sequence_widget.sequence_changed.connect(self._on_sequence_changed)
        self.path_sequence_widget.element_selected.connect(self._on_sequence_element_selected)
        self.path_sequence_widget.element_double_clicked.connect(self._on_sequence_element_double_clicked)
        self.path_sequence_widget.placement_requested.connect(self._on_silencer_placement_requested)
        self.path_sequence_widget.silencer_removed.connect(self._on_silencer_removed)
        reorder_tab_layout.addWidget(self.path_sequence_widget, 1)

        # Silencer insertion section
        silencer_group = QGroupBox("Insert Silencer")
        silencer_layout = QVBoxLayout()

        insert_btn_layout = QHBoxLayout()
        self.insert_silencer_btn = QPushButton("Insert Silencer After Selected")
        self.insert_silencer_btn.setToolTip(
            "Insert the selected silencer product into the path after the currently selected element"
        )
        self.insert_silencer_btn.setStyleSheet("""
            QPushButton {
                background-color: #7b1fa2;
                color: white;
                padding: 6px 16px;
                border-radius: 4px;
                font-weight: bold;
            }
            QPushButton:hover { background-color: #6a1b9a; }
            QPushButton:disabled { background-color: #ccc; color: #888; }
        """)
        self.insert_silencer_btn.clicked.connect(self._on_insert_silencer)
        insert_btn_layout.addWidget(self.insert_silencer_btn)
        insert_btn_layout.addStretch()
        silencer_layout.addLayout(insert_btn_layout)

        self.silencer_table = QTableWidget()
        self.silencer_table.setColumnCount(8)
        self.silencer_table.setHorizontalHeaderLabels([
            "Manufacturer", "Model", "Type", "Size (L\u00d7W\u00d7H)",
            "Flow Range (CFM)", "IL@500Hz", "IL@1kHz", "Cost"
        ])
        self.silencer_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.silencer_table.setSelectionMode(QTableWidget.SingleSelection)
        self.silencer_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.silencer_table.horizontalHeader().setStretchLastSection(True)
        self.silencer_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeToContents)
        self.silencer_table.setMinimumHeight(100)
        self.silencer_table.setMaximumHeight(160)
        self.silencer_table.setStyleSheet("""
            QTableWidget { border: 1px solid #ddd; background-color: #fff; color: #333; }
            QTableWidget::item:selected { background-color: #ce93d8; color: #333; }
            QHeaderView::section { background-color: #e1bee7; color: #333; padding: 4px; border: 1px solid #ccc; }
        """)
        silencer_layout.addWidget(self.silencer_table)

        silencer_group.setLayout(silencer_layout)
        reorder_tab_layout.addWidget(silencer_group)

        self._silencer_products = []
        self._populate_silencer_table()

        # Save order button
        save_layout = QHBoxLayout()
        save_layout.addStretch()

        self.save_order_btn = QPushButton("Save Order")
        self.save_order_btn.setToolTip("Save the new element order to the database")
        self.save_order_btn.setEnabled(False)
        self.save_order_btn.clicked.connect(self._save_element_order)
        self.save_order_btn.setStyleSheet("""
            QPushButton {
                background-color: #1976D2;
                color: white;
                padding: 6px 16px;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #1565C0;
            }
            QPushButton:disabled {
                background-color: #ccc;
                color: #666;
            }
        """)
        save_layout.addWidget(self.save_order_btn)
        reorder_tab_layout.addLayout(save_layout)

        reorder_widget.setLayout(reorder_tab_layout)
        self.tabs.addTab(reorder_widget, "Edit Path")

        # NC Results tab - shows cumulative octave band values
        nc_tab_widget = QWidget()
        nc_tab_layout = QVBoxLayout()
        nc_tab_layout.setContentsMargins(4, 4, 4, 4)

        # NC Results Table
        self.nc_results_table = NCResultsTableWidget(target_nc=35)
        self.nc_results_table.element_selected.connect(self._on_nc_element_selected)
        nc_tab_layout.addWidget(self.nc_results_table, 1)

        nc_tab_widget.setLayout(nc_tab_layout)
        self.tabs.addTab(nc_tab_widget, "NC Values")
        
        content_layout.addWidget(self.tabs, 1)
        
        # Results summary (always visible at bottom)
        self.results_summary = PathResultsSummary()
        content_layout.addWidget(self.results_summary)
        
        # Action buttons
        buttons_layout = QHBoxLayout()
        
        self.detail_btn = QPushButton("📊 Details")
        self.detail_btn.setToolTip("Show detailed calculation breakdown")
        self.detail_btn.clicked.connect(self._show_detailed_report)
        buttons_layout.addWidget(self.detail_btn)
        
        self.export_btn = QPushButton("📤 Export")
        self.export_btn.setToolTip("Export path analysis")
        self.export_btn.clicked.connect(self._export_analysis)
        buttons_layout.addWidget(self.export_btn)
        
        buttons_layout.addStretch()
        content_layout.addLayout(buttons_layout)
        
        self.content_widget.setLayout(content_layout)
        layout.addWidget(self.content_widget, 1)
        
        # Track if sequence has been modified
        self._sequence_modified = False
        
        self.setLayout(layout)
        
        # Show placeholder initially
        self._show_placeholder()
    
    def _toggle_collapse(self):
        """Toggle panel collapse state"""
        if self.content_widget.isVisible():
            self.content_widget.hide()
            self.collapse_btn.setText("▶")
            self.collapse_btn.setToolTip("Expand panel")
            self.setMaximumWidth(40)
        else:
            self.content_widget.show()
            self.collapse_btn.setText("◀")
            self.collapse_btn.setToolTip("Collapse panel")
            self.setMaximumWidth(16777215)  # Reset to default max
    
    def collapse(self):
        """Collapse the panel"""
        if self.content_widget.isVisible():
            self._toggle_collapse()
    
    def expand(self):
        """Expand the panel"""
        if not self.content_widget.isVisible():
            self._toggle_collapse()
    
    def set_project_id(self, project_id: int):
        """Set the project ID and reload paths"""
        self.project_id = project_id
        self._load_paths()
    
    def _load_paths(self):
        """Load available paths for the project"""
        self.path_selector.blockSignals(True)
        self.path_selector.clear()
        self.path_selector.addItem("-- Select Path --", None)
        
        if not self.project_id:
            self.path_selector.blockSignals(False)
            return
        
        try:
            session = get_session()
            paths = (
                session.query(HVACPath)
                .filter(HVACPath.project_id == self.project_id)
                .order_by(HVACPath.name)
                .all()
            )
            
            for path in paths:
                display_name = path.name or f"Path {path.id}"
                if path.target_space:
                    display_name += f" → {path.target_space.name}"
                self.path_selector.addItem(display_name, path.id)
            
            session.close()
        except Exception as e:
            print(f"DEBUG: Error loading paths: {e}")
        
        self.path_selector.blockSignals(False)
    
    def refresh_paths(self):
        """Refresh the paths list"""
        current_path_id = self.current_path_id
        self._load_paths()
        
        # Try to re-select the current path
        if current_path_id:
            for i in range(self.path_selector.count()):
                if self.path_selector.itemData(i) == current_path_id:
                    self.path_selector.setCurrentIndex(i)
                    break
    
    def set_path(self, path_id: int):
        """Load and display a specific path"""
        if path_id == self.current_path_id:
            return
        
        # Find and select in combo
        for i in range(self.path_selector.count()):
            if self.path_selector.itemData(i) == path_id:
                self.path_selector.setCurrentIndex(i)
                return
        
        # If not in combo, load directly
        self._load_path(path_id)
    
    def _on_path_selection_changed(self, index: int):
        """Handle path selection change"""
        path_id = self.path_selector.itemData(index)
        if path_id is None:
            self.current_path_id = None
            self.current_path = None
            self.calculation_results = None
            self._show_placeholder()
            return
        
        self._load_path(path_id)
    
    def _load_path(self, path_id: int):
        """Load path data and calculation results"""
        self.current_path_id = path_id
        
        try:
            session = get_session()
            path = (
                session.query(HVACPath)
                .options(
                    selectinload(HVACPath.target_space),
                    selectinload(HVACPath.segments).selectinload(HVACSegment.from_component),
                    selectinload(HVACPath.segments).selectinload(HVACSegment.to_component),
                    selectinload(HVACPath.segments).selectinload(HVACSegment.fittings),
                )
                .filter(HVACPath.id == path_id)
                .first()
            )
            
            if not path:
                session.close()
                self._show_placeholder("Path not found")
                return
            
            self.current_path = path
            
            # Get calculation results
            self._calculate_path(path)
            
            session.close()
            
            # Emit signal
            self.path_changed.emit(path_id)
            
        except Exception as e:
            print(f"DEBUG: Error loading path: {e}")
            import traceback
            traceback.print_exc()
            self._show_placeholder(f"Error loading path: {e}")
    
    def _calculate_path(self, path: HVACPath):
        """Calculate noise for the path"""
        try:
            # Lazy import calculator
            if self._path_calculator is None:
                from calculations.hvac_path_calculator import HVACPathCalculator
                self._path_calculator = HVACPathCalculator()
            
            result = self._path_calculator.calculate_path_noise(path.id)
            
            if result and result.calculation_valid:
                # Build results dict from PathCalculationResult
                self.calculation_results = {
                    'calculation_valid': True,
                    'source_noise': result.source_noise,
                    'terminal_noise': result.terminal_noise,
                    'total_attenuation': getattr(result, 'total_attenuation', None) or (result.source_noise - result.terminal_noise),
                    'nc_rating': result.nc_rating,
                    'target_nc': getattr(path.target_space, 'target_nc', None) if path.target_space else None,
                    'source_name': self._get_source_name(path),
                    'receiver_name': path.target_space.name if path.target_space else "Unknown",
                    'path_elements': result.segment_results if hasattr(result, 'segment_results') else [],
                    'warnings': result.warnings if hasattr(result, 'warnings') else [],
                }
            else:
                self.calculation_results = {
                    'calculation_valid': False,
                    'error': result.error_message if result else "Calculation failed"
                }
            
            self._rebuild_diagram()
            
        except Exception as e:
            print(f"DEBUG: Error calculating path: {e}")
            import traceback
            traceback.print_exc()
            self.calculation_results = {
                'calculation_valid': False,
                'error': str(e)
            }
            self._rebuild_diagram()
    
    def _get_source_name(self, path: HVACPath) -> str:
        """Get the source component name for a path"""
        # Try to use stored element sequence to find the first component
        sequence = None
        if hasattr(path, 'get_element_sequence'):
            try:
                sequence = path.get_element_sequence()
            except Exception:
                pass
        elif hasattr(path, 'element_sequence') and path.element_sequence:
            import json
            try:
                sequence = json.loads(path.element_sequence)
            except (json.JSONDecodeError, TypeError):
                pass
        
        if sequence:
            # Find first component in sequence and get its name
            for item in sequence:
                if item.get('type') == 'component':
                    comp_id = item.get('id')
                    # Find the component in segments
                    for seg in path.segments:
                        for comp in [seg.from_component, seg.to_component]:
                            if comp and comp.id == comp_id:
                                name = (getattr(comp, 'name', None) or getattr(comp, 'custom_type_label', None) or
                                        getattr(comp, 'component_type', None))
                                return name or "Unknown Source"
                    break
        
        # Fall back to first segment's from_component
        segments = getattr(path, 'segments', None)
        if not segments:
            return "Unknown Source"
        
        # Get the first segment's from_component
        try:
            first_segment = min(segments, key=lambda s: getattr(s, 'segment_order', 0) or 0)
            from_comp = getattr(first_segment, 'from_component', None)
            if from_comp:
                name = (getattr(from_comp, 'name', None) or getattr(from_comp, 'custom_type_label', None) or
                        getattr(from_comp, 'component_type', None))
                return name or "Unknown Source"
        except (ValueError, TypeError):
            pass
        
        return "Unknown Source"
    
    def _recalculate_path(self):
        """Recalculate the current path"""
        if self.current_path_id:
            self._load_path(self.current_path_id)
    
    def _show_placeholder(self, message: str = None):
        """Show placeholder when no path is selected"""
        self._clear_diagram()
        
        placeholder = QLabel(message or "Select a path to view analysis")
        placeholder.setAlignment(Qt.AlignCenter)
        placeholder.setStyleSheet("color: #666; padding: 40px; background-color: transparent;")
        self.diagram_layout.addWidget(placeholder)
        self.diagram_layout.addStretch()
        
        self.results_summary.update_results(None)
    
    def _clear_diagram(self):
        """Clear all elements from the diagram"""
        self._element_cards.clear()
        
        while self.diagram_layout.count():
            item = self.diagram_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
    
    def _rebuild_diagram(self):
        """Build the visual path diagram with calculation results"""
        self._clear_diagram()

        # Update sequence widget
        self._update_sequence_widget()

        # Update NC results table
        self._update_nc_results_table()

        if not self.calculation_results:
            self._show_placeholder("No calculation results")
            return
        
        if not self.calculation_results.get('calculation_valid', False):
            error_msg = self.calculation_results.get('error', 'Calculation failed')
            self._show_placeholder(f"⚠️ {error_msg}")
            return
        
        # Build path elements from current_path data
        if not self.current_path:
            self._show_placeholder("No path data")
            return
        
        # Source card
        source_card = PathElementCard(
            element_type="source",
            name=self.calculation_results.get('source_name', 'Source'),
            noise_level=self.calculation_results.get('source_noise', 0),
            element_id=self._get_source_component_id(),
            extra_info={'pwl': True}
        )
        self._connect_card_signals(source_card)
        self._element_cards.append(source_card)
        self.diagram_layout.addWidget(source_card)
        
        # Use stored element sequence if available, otherwise fall back to segment_order
        segments = self._get_ordered_segments()
        segment_results = self.calculation_results.get('path_elements', [])
        
        # Build a map of silencers that follow each element in the sequence
        # so we can render them between the segment/component cards
        silencers_after = {}  # (type, id) -> [silencer_component_ids]
        element_sequence = None
        if hasattr(self.current_path, 'get_element_sequence'):
            element_sequence = self.current_path.get_element_sequence()
        if element_sequence:
            for idx, item in enumerate(element_sequence):
                if item.get('type') in ('segment', 'component'):
                    key = (item['type'], item['id'])
                    following_silencers = []
                    for j in range(idx + 1, len(element_sequence)):
                        if element_sequence[j].get('type') == 'silencer':
                            following_silencers.append(element_sequence[j].get('id'))
                        else:
                            break
                    if following_silencers:
                        silencers_after[key] = following_silencers
        
        # Render silencers that follow the source component
        source_comp_id = self._get_source_component_id()
        self._render_silencer_cards(silencers_after.get(('component', source_comp_id), []))
        
        for i, segment in enumerate(segments):
            # Arrow
            self.diagram_layout.addWidget(PathArrow())
            
            # Get calculation result for this segment
            seg_result = None
            seg_id = getattr(segment, 'id', None)
            for sr in segment_results:
                if sr.get('segment_number') == (i + 1) or sr.get('segment_id') == seg_id:
                    seg_result = sr
                    break
            
            # Build segment card with defensive attribute access
            extra_info = {}
            duct_shape = getattr(segment, 'duct_shape', 'rectangular') or 'rectangular'
            if duct_shape == 'circular':
                diameter = getattr(segment, 'diameter', 0) or 0
                extra_info['dimensions'] = f"Ø{int(diameter)}\""
            else:
                w = int(getattr(segment, 'duct_width', 0) or 0)
                h = int(getattr(segment, 'duct_height', 0) or 0)
                extra_info['dimensions'] = f"{w}\"×{h}\""
            
            extra_info['length'] = getattr(segment, 'length', 0) or 0
            extra_info['shape'] = duct_shape
            # HVACSegment uses 'insulation' for lining material
            extra_info['lining'] = bool(getattr(segment, 'insulation', None) or getattr(segment, 'lining_thickness', None))
            
            noise_after = seg_result.get('noise_after', 0) if seg_result else None
            attenuation = seg_result.get('attenuation_dba', 0) if seg_result else None
            if attenuation is None and seg_result:
                attenuation = seg_result.get('total_attenuation', 0)
            
            segment_card = PathElementCard(
                element_type="segment",
                name=f"Segment {i + 1}",
                noise_level=noise_after,
                attenuation=attenuation if attenuation else None,
                element_id=seg_id,
                extra_info=extra_info
            )
            self._connect_card_signals(segment_card)
            self._element_cards.append(segment_card)
            self.diagram_layout.addWidget(segment_card)
            
            # Add fittings for this segment
            fittings = getattr(segment, 'fittings', None) or []
            for fitting in fittings:
                self.diagram_layout.addWidget(PathArrow())
                
                fitting_type = getattr(fitting, 'fitting_type', None) or 'fitting'
                fitting_card = PathElementCard(
                    element_type=fitting_type,
                    name=fitting_type.replace('_', ' ').title(),
                    attenuation=getattr(fitting, 'calculated_attenuation', None),
                    element_id=getattr(fitting, 'id', None),
                    extra_info={}
                )
                self._connect_card_signals(fitting_card)
                self._element_cards.append(fitting_card)
                self.diagram_layout.addWidget(fitting_card)
            
            # Render silencers that follow this segment in the element sequence
            self._render_silencer_cards(silencers_after.get(('segment', seg_id), []))
            
            # Add end component if not last segment
            to_comp = getattr(segment, 'to_component', None)
            if to_comp and i < len(segments) - 1:
                self.diagram_layout.addWidget(PathArrow())
                
                comp_type = getattr(to_comp, 'component_type', None) or 'component'
                comp_name = getattr(to_comp, 'name', None) or comp_type or 'Component'
                comp_card = PathElementCard(
                    element_type=comp_type,
                    name=comp_name,
                    element_id=getattr(to_comp, 'id', None),
                    extra_info={}
                )
                self._connect_card_signals(comp_card)
                self._element_cards.append(comp_card)
                self.diagram_layout.addWidget(comp_card)
                
                # Render silencers that follow this component in the element sequence
                self._render_silencer_cards(silencers_after.get(('component', to_comp.id), []))
        
        # Arrow to receiver
        self.diagram_layout.addWidget(PathArrow())
        
        # Receiver card
        target_nc = None
        if self.current_path.target_space:
            target_nc = getattr(self.current_path.target_space, 'target_nc', None)
        
        receiver_card = PathElementCard(
            element_type="receiver",
            name=self.calculation_results.get('receiver_name', 'Receiver'),
            noise_level=self.calculation_results.get('terminal_noise', 0),
            nc_rating=int(self.calculation_results.get('nc_rating', 0)),
            element_id=self.current_path.target_space_id,
            extra_info={'target_nc': target_nc}
        )
        self._connect_card_signals(receiver_card)
        self._element_cards.append(receiver_card)
        self.diagram_layout.addWidget(receiver_card)
        
        # Add stretch at bottom
        self.diagram_layout.addStretch()
        
        # Update summary
        self.results_summary.update_results({
            'source_noise': self.calculation_results.get('source_noise', 0),
            'terminal_noise': self.calculation_results.get('terminal_noise', 0),
            'total_attenuation': self.calculation_results.get('total_attenuation', 0),
            'nc_rating': self.calculation_results.get('nc_rating', 0),
            'target_nc': target_nc,
        })
    
    def _render_silencer_cards(self, silencer_ids: List[int]):
        """Render silencer PathElementCards for the given component IDs into the diagram."""
        if not silencer_ids:
            return
        session = get_session()
        for sil_id in silencer_ids:
            try:
                sil = session.query(HVACComponent).get(sil_id)
            except Exception:
                continue
            if not sil:
                continue
            self.diagram_layout.addWidget(PathArrow())
            sil_name = getattr(sil, 'name', None) or f"Silencer {sil.id}"
            extra_info = {
                'silencer_type': getattr(sil, 'silencer_type', '') or '',
            }
            product = getattr(sil, 'selected_product', None)
            if product:
                extra_info['product'] = getattr(product, 'model_name', '')
            sil_card = PathElementCard(
                element_type="silencer",
                name=sil_name,
                element_id=sil.id,
                extra_info=extra_info
            )
            self._connect_card_signals(sil_card)
            self._element_cards.append(sil_card)
            self.diagram_layout.addWidget(sil_card)
    
    def _get_ordered_segments(self) -> List[HVACSegment]:
        """Get segments in their proper order using stored sequence or segment_order"""
        if not self.current_path or not self.current_path.segments:
            return []
        
        # Try to use stored element sequence
        sequence = None
        if hasattr(self.current_path, 'get_element_sequence'):
            try:
                sequence = self.current_path.get_element_sequence()
            except Exception:
                pass
        elif hasattr(self.current_path, 'element_sequence') and self.current_path.element_sequence:
            import json
            try:
                sequence = json.loads(self.current_path.element_sequence)
            except (json.JSONDecodeError, TypeError):
                pass
        
        if sequence:
            # Build segment order from sequence
            segment_ids = [item['id'] for item in sequence if item.get('type') == 'segment']
            segment_map = {seg.id: seg for seg in self.current_path.segments}
            
            ordered = []
            for seg_id in segment_ids:
                if seg_id in segment_map:
                    ordered.append(segment_map[seg_id])
            
            # Add any remaining segments not in the sequence
            for seg in self.current_path.segments:
                if seg not in ordered:
                    ordered.append(seg)
            
            return ordered
        
        # Fall back to segment_order
        return sorted(self.current_path.segments, key=lambda s: s.segment_order or 0)
    
    def _get_source_component_id(self) -> Optional[int]:
        """Get the ID of the source component"""
        if not self.current_path:
            return None
        
        # Try to use stored element sequence to find the first component
        sequence = None
        if hasattr(self.current_path, 'get_element_sequence'):
            try:
                sequence = self.current_path.get_element_sequence()
            except Exception:
                pass
        elif hasattr(self.current_path, 'element_sequence') and self.current_path.element_sequence:
            import json
            try:
                sequence = json.loads(self.current_path.element_sequence)
            except (json.JSONDecodeError, TypeError):
                pass
        
        if sequence:
            # Find first component in sequence
            for item in sequence:
                if item.get('type') == 'component':
                    return item.get('id')
        
        # Fall back to first segment's from_component
        segments = getattr(self.current_path, 'segments', None)
        if not segments:
            return None
        
        try:
            first_segment = min(segments, key=lambda s: getattr(s, 'segment_order', 0) or 0)
            from_comp = getattr(first_segment, 'from_component', None)
            if from_comp:
                return getattr(from_comp, 'id', None)
        except (ValueError, TypeError):
            pass
        
        return None
    
    def _connect_card_signals(self, card: PathElementCard):
        """Connect signals for a path element card"""
        card.hovered.connect(self._on_card_hover)
        card.unhovered.connect(self._on_card_unhover)
        card.clicked.connect(self._on_card_clicked)
        card.edit_requested.connect(self._on_card_edit_requested)
    
    def _on_card_hover(self, element_id: object, element_type: str):
        """Handle card hover - highlight element on drawing"""
        self.element_hover_requested.emit(element_id, element_type)
    
    def _on_card_unhover(self):
        """Handle card unhover - clear highlight on drawing"""
        self.element_unhover_requested.emit()
    
    def _on_card_clicked(self, element_id: object, element_type: str):
        """Handle card click - select and pan to element on drawing"""
        self.element_select_requested.emit(element_id, element_type)
        self.pan_to_element_requested.emit(element_id, element_type)
    
    def _on_card_edit_requested(self, element_id: object, element_type: str):
        """Handle card double-click - open edit dialog"""
        self.edit_element_requested.emit(element_id, element_type)
    
    def highlight_element_card(self, element_id: object, element_type: str):
        """Highlight a card in the panel (called from drawing hover)"""
        for card in self._element_cards:
            if card.element_id == element_id:
                card.set_highlighted(True)
                # Scroll to make card visible
                self._scroll_to_card(card)
            else:
                card.set_highlighted(False)
    
    def clear_highlight(self):
        """Clear all card highlights"""
        for card in self._element_cards:
            card.set_highlighted(False)
    
    def _scroll_to_card(self, card: PathElementCard):
        """Scroll the diagram to show the specified card"""
        # Find the scroll area
        scroll_area = self.diagram_container.parent()
        if scroll_area and hasattr(scroll_area, 'ensureWidgetVisible'):
            scroll_area.ensureWidgetVisible(card)
    
    def _show_detailed_report(self):
        """Show detailed calculation breakdown"""
        if not self.current_path_id:
            QMessageBox.information(self, "No Path", "Please select a path first.")
            return
        
        try:
            from ui.dialogs.hvac_debug_dialog import HVACDebugDialog
            dialog = HVACDebugDialog(self, self.project_id, self.current_path_id)
            dialog.exec()
        except ImportError:
            QMessageBox.information(
                self, 
                "Detailed Report", 
                "Detailed debug dialog not available.\n\n"
                f"Path: {self.current_path.name if self.current_path else 'Unknown'}\n"
                f"Source: {self.calculation_results.get('source_noise', 0):.1f} dB(A)\n"
                f"Terminal: {self.calculation_results.get('terminal_noise', 0):.1f} dB(A)\n"
                f"NC Rating: NC-{self.calculation_results.get('nc_rating', 0):.0f}"
            )
    
    def _update_sequence_widget(self):
        """Update the path sequence widget with current path data"""
        if not hasattr(self, 'path_sequence_widget') or not self.current_path:
            return
        
        # Build component data
        components_data = []
        component_map = {}
        
        for seg in self.current_path.segments:
            for comp in [seg.from_component, seg.to_component]:
                if comp and comp.id not in component_map:
                    component_map[comp.id] = {
                        'id': comp.id,
                        'name': getattr(comp, 'name', None) or f"Component {comp.id}",
                        'component_type': getattr(comp, 'component_type', 'unknown'),
                        'noise_level': getattr(comp, 'noise_level', None),
                    }
                    components_data.append(component_map[comp.id])
        
        # Include silencer components from element_sequence (silencers are not
        # segment endpoints, so they must be loaded separately from the DB)
        pre_sequence = None
        if hasattr(self.current_path, 'get_element_sequence'):
            pre_sequence = self.current_path.get_element_sequence()
        elif hasattr(self.current_path, 'element_sequence') and self.current_path.element_sequence:
            import json as _json
            try:
                pre_sequence = _json.loads(self.current_path.element_sequence)
            except (ValueError, TypeError):
                pass
        
        if pre_sequence:
            session = get_session()
            for item in pre_sequence:
                if item.get('type') == 'silencer':
                    sil_id = item.get('id')
                    if sil_id and sil_id not in component_map:
                        sil = session.query(HVACComponent).get(sil_id)
                        if sil:
                            component_map[sil.id] = {
                                'id': sil.id,
                                'name': getattr(sil, 'name', None) or f"Silencer {sil.id}",
                                'component_type': 'silencer',
                                'is_silencer': True,
                                'noise_level': getattr(sil, 'noise_level', None),
                                'selected_product_id': getattr(sil, 'selected_product_id', None),
                                'silencer_model': getattr(sil, 'name', ''),
                            }
                            components_data.append(component_map[sil.id])
        
        # Build segment data
        segments_data = []
        for seg in self.current_path.segments:
            segments_data.append({
                'id': seg.id,
                'from_component_id': seg.from_component_id,
                'to_component_id': seg.to_component_id,
                'length': getattr(seg, 'length', 0) or 0,
                'duct_shape': getattr(seg, 'duct_shape', 'rectangular'),
                'segment_order': getattr(seg, 'segment_order', 0),
            })
        
        # Get existing sequence if available
        sequence = None
        if hasattr(self.current_path, 'get_element_sequence'):
            sequence = self.current_path.get_element_sequence()
        elif hasattr(self.current_path, 'element_sequence') and self.current_path.element_sequence:
            import json
            try:
                sequence = json.loads(self.current_path.element_sequence)
            except (json.JSONDecodeError, TypeError):
                pass
        
        self.path_sequence_widget.set_data(components_data, segments_data, sequence)
        self._sequence_modified = False
        self.save_order_btn.setEnabled(False)
    
    def _on_sequence_changed(self, sequence: List[Dict]):
        """Handle sequence changes from the reorder widget"""
        self._sequence_modified = True
        self.save_order_btn.setEnabled(True)
        
        # Store the new sequence for potential saving
        self._pending_sequence = sequence
    
    def _on_sequence_element_selected(self, element_type: str, element_id: int):
        """Handle element selection in sequence widget"""
        self.element_select_requested.emit(element_id, element_type)
    
    def _on_sequence_element_double_clicked(self, element_type: str, element_id: int):
        """Handle element double-click to open edit dialog"""
        self.edit_element_requested.emit(element_id, element_type)
    
    def _populate_silencer_table(self):
        """Load silencer products from the database into the table"""
        try:
            session = get_session()
            products = session.query(SilencerProduct).all()

            self._silencer_products = []
            self.silencer_table.setRowCount(len(products))

            for row, product in enumerate(products):
                self._silencer_products.append(product)

                self.silencer_table.setItem(row, 0, QTableWidgetItem(product.manufacturer or ""))
                self.silencer_table.setItem(row, 1, QTableWidgetItem(product.model_number or ""))
                self.silencer_table.setItem(row, 2, QTableWidgetItem((product.silencer_type or "").title()))

                size_str = f'{int(product.length or 0)}\u00d7{int(product.width or 0)}\u00d7{int(product.height or 0)}"'
                self.silencer_table.setItem(row, 3, QTableWidgetItem(size_str))

                flow_str = f"{int(product.flow_rate_min or 0)}-{int(product.flow_rate_max or 0)}"
                self.silencer_table.setItem(row, 4, QTableWidgetItem(flow_str))

                il_500 = QTableWidgetItem(f"{product.insertion_loss_500 or 0:.0f} dB")
                il_500.setTextAlignment(Qt.AlignCenter)
                self.silencer_table.setItem(row, 5, il_500)

                il_1k = QTableWidgetItem(f"{product.insertion_loss_1000 or 0:.0f} dB")
                il_1k.setTextAlignment(Qt.AlignCenter)
                self.silencer_table.setItem(row, 6, il_1k)

                cost_str = f"${product.cost_estimate or 0:,.0f}"
                self.silencer_table.setItem(row, 7, QTableWidgetItem(cost_str))

            session.close()
        except Exception as e:
            print(f"DEBUG: Error populating silencer table: {e}")
            self._silencer_products = []
            self.silencer_table.setRowCount(0)
    
    def _on_insert_silencer(self):
        """Handle Insert Silencer button click in the Edit Path tab"""
        if not self.current_path_id:
            QMessageBox.warning(self, "No Path", "Please select a path first.")
            return

        current_row = self.path_sequence_widget.list_widget.currentRow()
        if current_row < 0:
            QMessageBox.warning(
                self, "No Position Selected",
                "Please select an element in the path sequence to insert the silencer after."
            )
            return

        selected_rows = self.silencer_table.selectionModel().selectedRows()
        if not selected_rows:
            QMessageBox.warning(
                self, "No Silencer Selected",
                "Please select a silencer product from the table below."
            )
            return

        table_row = selected_rows[0].row()
        if table_row < 0 or table_row >= len(self._silencer_products):
            return

        product = self._silencer_products[table_row]

        try:
            session = get_session()

            # Resolve a drawing_id from the path's existing components
            drawing_id = None
            if self.current_path and self.current_path.segments:
                for seg in self.current_path.segments:
                    comp = seg.from_component or seg.to_component
                    if comp:
                        drawing_id = getattr(comp, 'drawing_id', None)
                        if drawing_id:
                            break
            if not drawing_id:
                from models.project import Drawing
                first_drawing = session.query(Drawing).filter(
                    Drawing.project_id == self.project_id
                ).first()
                if first_drawing:
                    drawing_id = first_drawing.id

            if not drawing_id:
                QMessageBox.warning(
                    self, "No Drawing",
                    "Cannot insert silencer: no drawing is associated with this project."
                )
                session.close()
                return

            silencer_component = HVACComponent(
                project_id=self.project_id,
                drawing_id=drawing_id,
                name=f"Silencer: {product.manufacturer} {product.model_number}",
                component_type='silencer',
                x_position=0.0,
                y_position=0.0,
                is_silencer=True,
                silencer_type=product.silencer_type,
                selected_product_id=product.id,
                noise_level=-15.0,
                cfm=float((product.flow_rate_min or 0) + (product.flow_rate_max or 0)) / 2.0,
            )
            session.add(silencer_component)
            session.commit()

            component_id = silencer_component.id

            silencer_data = {
                'id': component_id,
                'name': silencer_component.name,
                'component_type': 'silencer',
                'is_silencer': True,
                'selected_product_id': product.id,
                'silencer_model': product.model_number,
                'noise_level': -15.0,
            }

            self.path_sequence_widget.insert_silencer_at(current_row, component_id, silencer_data)

            session.close()

            # Auto-save the updated sequence so the diagram refreshes with the silencer
            self._auto_save_sequence()

        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to insert silencer:\n{str(e)}")
    
    def _on_silencer_removed(self, component_id: int):
        """Handle silencer removal from the path sequence widget"""
        try:
            session = get_session()
            comp = session.query(HVACComponent).filter(HVACComponent.id == component_id).first()
            if comp and comp.is_silencer:
                session.delete(comp)
                session.commit()
            session.close()
        except Exception:
            pass

        # Auto-save the updated sequence so the diagram refreshes without the silencer
        self._auto_save_sequence()
    
    def _auto_save_sequence(self):
        """Save the current sequence from the widget and reload the path to refresh all views."""
        if not self.current_path_id:
            return

        sequence = self.path_sequence_widget.get_sequence()
        if not sequence:
            return

        try:
            session = get_session()
            path = session.query(HVACPath).filter(HVACPath.id == self.current_path_id).first()
            if not path:
                session.close()
                return

            segment_order_map = {}
            segment_index = 1
            for item in sequence:
                if item.get('type') == 'segment':
                    segment_order_map[item['id']] = segment_index
                    segment_index += 1

            for seg in path.segments:
                if seg.id in segment_order_map:
                    seg.segment_order = segment_order_map[seg.id]

            if hasattr(path, 'set_element_sequence'):
                path.set_element_sequence(sequence)
            else:
                import json
                path.element_sequence = json.dumps(sequence)

            session.commit()
            session.close()

            self._sequence_modified = False
            self.save_order_btn.setEnabled(False)

            self._load_path(self.current_path_id)

        except Exception as e:
            print(f"DEBUG: Error auto-saving sequence: {e}")
    
    def _save_element_order(self):
        """Save the modified element order to the database"""
        if not self.current_path_id or not hasattr(self, '_pending_sequence'):
            return
        
        try:
            session = get_session()
            
            # Get the path
            path = session.query(HVACPath).filter(HVACPath.id == self.current_path_id).first()
            if not path:
                session.close()
                QMessageBox.warning(self, "Error", "Path not found in database.")
                return
            
            # Get the new sequence
            sequence = self._pending_sequence
            
            # Update segment_order based on the new sequence
            segment_order_map = {}
            segment_index = 1
            for item in sequence:
                if item.get('type') == 'segment':
                    segment_order_map[item['id']] = segment_index
                    segment_index += 1
            
            # Update segments in the database
            for seg in path.segments:
                if seg.id in segment_order_map:
                    seg.segment_order = segment_order_map[seg.id]
            
            # Save the element sequence
            if hasattr(path, 'set_element_sequence'):
                path.set_element_sequence(sequence)
            else:
                import json
                path.element_sequence = json.dumps(sequence)
            
            session.commit()
            session.close()
            
            self._sequence_modified = False
            self.save_order_btn.setEnabled(False)
            
            # Reload the path to refresh the diagram
            self._load_path(self.current_path_id)
            
            QMessageBox.information(self, "Success", "Element order saved successfully.")
            
        except Exception as e:
            print(f"DEBUG: Error saving element order: {e}")
            import traceback
            traceback.print_exc()
            QMessageBox.critical(self, "Error", f"Failed to save element order:\n{str(e)}")
    
    def _export_analysis(self):
        """Export path analysis"""
        if not self.current_path_id:
            QMessageBox.information(self, "No Path", "Please select a path first.")
            return

        # For now, just show a message - can be expanded later
        QMessageBox.information(
            self,
            "Export",
            "Export functionality will be available in a future update."
        )

    def _on_nc_element_selected(self, element_type: str, element_id: int):
        """Handle element selection from NC results table"""
        self.element_select_requested.emit(element_id, element_type)
        self.pan_to_element_requested.emit(element_id, element_type)
        if hasattr(self, 'path_sequence_widget'):
            self.path_sequence_widget.highlight_element(element_type, element_id)

    def _on_silencer_placement_requested(self, silencer_component_id: int):
        """Handle silencer placement request from sequence widget"""
        if not self.current_path_id:
            QMessageBox.warning(self, "No Path", "Please select a path first.")
            return

        # Find the silencer component data
        silencer_data = self._build_silencer_data(silencer_component_id)
        if not silencer_data:
            QMessageBox.warning(self, "Error", "Could not find silencer component data.")
            return

        # Emit signal for DrawingInterface to handle
        self.silencer_placement_requested.emit(
            self.current_path_id,
            silencer_component_id,
            silencer_data
        )

    def _build_silencer_data(self, component_id: int) -> Optional[dict]:
        """Build silencer data dict for placement mode"""
        try:
            session = get_session()
            comp = session.query(HVACComponent).filter(HVACComponent.id == component_id).first()
            if not comp or not comp.is_silencer:
                session.close()
                return None

            silencer_data = {
                'component_id': component_id,
                'product_id': comp.selected_product_id,
                'product_length': 36.0,  # Default 3 feet
                'is_elbow': False,
                'position_on_path': comp.position_on_path or 0.5,
                'elbow_component_id': comp.elbow_component_id,
                'insertion_loss_500': None,
                'model_number': None,
            }

            # Get product details if available
            if comp.selected_product_id:
                product = session.query(SilencerProduct).filter(
                    SilencerProduct.id == comp.selected_product_id
                ).first()
                if product:
                    silencer_data['product_length'] = float(product.length) if product.length else 36.0
                    silencer_data['insertion_loss_500'] = product.il_500
                    silencer_data['model_number'] = product.model_number
                    if product.shape and 'elbow' in product.shape.lower():
                        silencer_data['is_elbow'] = True

            session.close()
            return silencer_data

        except Exception as e:
            print(f"DEBUG: Error building silencer data: {e}")
            return None

    def _update_nc_results_table(self):
        """Update the NC results table with cumulative values from current path"""
        if not hasattr(self, 'nc_results_table') or not self.current_path:
            return

        # Get target NC from space
        target_nc = 35  # Default
        if self.current_path.target_space:
            target_nc = int(self.current_path.target_space.target_nc or 35)
        self.nc_results_table.set_target_nc(target_nc)

        # Calculate cumulative element results
        element_results = self._calculate_cumulative_nc_values()
        self.nc_results_table.update_results(element_results, is_live_update=False)

    def _calculate_cumulative_nc_values(self) -> List[Dict]:
        """Calculate cumulative octave band values for each path element.

        Uses engine ``path_elements`` when available for accurate per-band
        spectra, otherwise falls back to a simplified model.
        """
        if not self.current_path or not self.calculation_results:
            return []

        path_elements = self.calculation_results.get('path_elements', [])
        if path_elements:
            return self._build_nc_results_from_engine(path_elements)
        return self._build_nc_results_fallback()

    def _build_nc_results_from_engine(self, path_elements: List[Dict]) -> List[Dict]:
        """Build NC table rows from the engine's per-element results.

        Each engine element carries ``noise_after_spectrum`` (8-band) and
        ``nc_rating`` computed by the noise engine.  We map these to DB IDs
        so the table rows are clickable, and inject intermediate component
        rows between segment groups.
        """
        from calculations.nc_rating_analyzer import NCRatingAnalyzer
        nc_analyzer = NCRatingAnalyzer()

        results: List[Dict] = []
        segments = self._get_ordered_segments()

        # Map silencer DB IDs from the stored element_sequence
        silencer_id_list: List[int] = []
        element_sequence = None
        if hasattr(self.current_path, 'get_element_sequence'):
            element_sequence = self.current_path.get_element_sequence()
        if element_sequence:
            silencer_id_list = [
                item['id'] for item in element_sequence
                if item.get('type') == 'silencer'
            ]

        segment_idx = 0
        silencer_idx = 0
        last_spectrum: Optional[List[float]] = None

        for elem in path_elements:
            elem_type = elem.get('element_type', '')
            spectrum_8 = elem.get('noise_after_spectrum', [0.0] * 8)
            nc_rating = elem.get('nc_rating', 0)

            if elem_type == 'source':
                db_id = self._get_source_component_id()
                name = self.calculation_results.get('source_name', 'Source')
                row_type = 'source'
            elif elem_type in ('duct', 'flex_duct'):
                # Inject intermediate component row before this segment
                if segment_idx > 0 and segment_idx <= len(segments) and last_spectrum is not None:
                    prev_seg = segments[segment_idx - 1]
                    to_comp = getattr(prev_seg, 'to_component', None)
                    if to_comp:
                        is_sil = bool(getattr(to_comp, 'is_silencer', False))
                        comp_type = getattr(to_comp, 'component_type', None) or 'component'
                        comp_name = getattr(to_comp, 'name', None) or comp_type.replace('_', ' ').title()
                        results.append({
                            'element_type': 'silencer' if is_sil else comp_type,
                            'element_name': comp_name,
                            'element_id': to_comp.id,
                            'cumulative_spectrum': list(last_spectrum[:7]),
                            'nc_rating': nc_analyzer.determine_nc_rating(last_spectrum),
                            'is_silencer': is_sil,
                        })

                db_id = segments[segment_idx].id if segment_idx < len(segments) else None
                name = f"Segment {segment_idx + 1}"
                segment_idx += 1
                row_type = 'segment'
            elif elem_type == 'elbow':
                db_id = None
                name = 'Elbow'
                row_type = 'elbow'
            elif elem_type == 'junction':
                db_id = None
                name = 'Junction'
                row_type = 'junction'
            elif elem_type == 'silencer':
                db_id = silencer_id_list[silencer_idx] if silencer_idx < len(silencer_id_list) else None
                silencer_idx += 1
                name = 'Silencer'
                if db_id:
                    try:
                        session = get_session()
                        sil_comp = session.query(HVACComponent).get(db_id)
                        if sil_comp:
                            name = getattr(sil_comp, 'name', None) or name
                        session.close()
                    except Exception:
                        pass
                row_type = 'silencer'
            elif elem_type == 'terminal':
                db_id = self.current_path.target_space_id if self.current_path.target_space else None
                name = self.current_path.target_space.name if self.current_path.target_space else 'Receiver'
                row_type = 'terminal'
            else:
                db_id = None
                name = elem_type.replace('_', ' ').title()
                row_type = elem_type

            results.append({
                'element_type': row_type,
                'element_name': name,
                'element_id': db_id,
                'cumulative_spectrum': list(spectrum_8[:7]),
                'nc_rating': nc_rating,
                'is_silencer': elem_type == 'silencer',
            })
            last_spectrum = list(spectrum_8)

        # If the engine did not emit a terminal row but we have a target space,
        # append one using the last known spectrum.
        has_terminal = any(r['element_type'] == 'terminal' for r in results)
        if not has_terminal and self.current_path.target_space and last_spectrum:
            results.append({
                'element_type': 'terminal',
                'element_name': self.current_path.target_space.name,
                'element_id': self.current_path.target_space_id,
                'cumulative_spectrum': list(last_spectrum[:7]),
                'nc_rating': nc_analyzer.determine_nc_rating(last_spectrum),
                'is_silencer': False,
            })

        return results

    def _build_nc_results_fallback(self) -> List[Dict]:
        """Simplified NC calculation when engine path_elements are unavailable."""
        from calculations.nc_rating_analyzer import NCRatingAnalyzer
        nc_analyzer = NCRatingAnalyzer()
        results: List[Dict] = []

        source_noise = self.calculation_results.get('source_noise', 50.0)
        cumulative = [source_noise] * 8

        def display(spectrum_8):
            return spectrum_8[:7]

        nc_rating = nc_analyzer.determine_nc_rating(cumulative)
        results.append({
            'element_type': 'source',
            'element_name': self.calculation_results.get('source_name', 'Source'),
            'element_id': self._get_source_component_id(),
            'cumulative_spectrum': display(cumulative),
            'nc_rating': nc_rating,
            'is_silencer': False,
        })

        segments = self._get_ordered_segments()
        for i, segment in enumerate(segments):
            attenuation = getattr(segment, 'duct_loss', 0) or 0
            cumulative = [max(0, c - attenuation) for c in cumulative]
            nc_rating = nc_analyzer.determine_nc_rating(cumulative)
            results.append({
                'element_type': 'segment',
                'element_name': f"Segment {i + 1}",
                'element_id': getattr(segment, 'id', None),
                'cumulative_spectrum': display(cumulative),
                'nc_rating': nc_rating,
                'is_silencer': False,
            })

            to_comp = getattr(segment, 'to_component', None)
            if to_comp and i < len(segments) - 1:
                comp_type = getattr(to_comp, 'component_type', 'component')
                comp_name = getattr(to_comp, 'name', None) or comp_type.replace('_', ' ').title()
                nc_rating = nc_analyzer.determine_nc_rating(cumulative)
                results.append({
                    'element_type': comp_type,
                    'element_name': comp_name,
                    'element_id': to_comp.id,
                    'cumulative_spectrum': display(cumulative),
                    'nc_rating': nc_rating,
                    'is_silencer': bool(getattr(to_comp, 'is_silencer', False)),
                })

        if self.current_path.target_space:
            nc_rating = nc_analyzer.determine_nc_rating(cumulative)
            results.append({
                'element_type': 'terminal',
                'element_name': self.current_path.target_space.name,
                'element_id': self.current_path.target_space_id,
                'cumulative_spectrum': display(cumulative),
                'nc_rating': nc_rating,
                'is_silencer': False,
            })

        return results

    def update_for_silencer_position(self, position_data: dict, is_live: bool = False):
        """Update NC table for silencer position changes during placement"""
        if not hasattr(self, 'nc_results_table'):
            return

        # Recalculate with temporary silencer position and update table
        element_results = self._calculate_cumulative_nc_values()
        self.nc_results_table.update_results(element_results, is_live_update=is_live)

    def revert_nc_table(self):
        """Revert NC table to saved state (for placement cancellation)"""
        if hasattr(self, 'nc_results_table'):
            self.nc_results_table.revert_to_saved()
