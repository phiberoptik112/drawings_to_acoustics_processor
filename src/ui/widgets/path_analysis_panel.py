"""
Path Analysis Panel - Collapsible panel showing HVAC path calculation alongside drawing

This panel displays the path flow diagram with interactive cards that link
to the drawing overlay for visual correlation between physical path and calculations.
"""

from typing import Optional, Dict, List, Any
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QComboBox, QScrollArea, QFrame, QSizePolicy, QSplitter,
    QToolButton, QMessageBox
)
from PySide6.QtCore import Qt, Signal, QTimer
from PySide6.QtGui import QFont

from models import get_session
from models.hvac import HVACPath, HVACSegment, HVACComponent
from sqlalchemy.orm import selectinload

from .path_element_card import PathElementCard, PathArrow, PathResultsSummary


class PathAnalysisPanel(QWidget):
    """Panel showing HVAC path calculation alongside drawing"""
    
    # Signals for drawing coordination
    element_hover_requested = Signal(object, str)  # element_id, element_type - highlight on drawing
    element_unhover_requested = Signal()  # clear highlight on drawing
    element_select_requested = Signal(object, str)  # element_id, element_type - select on drawing
    pan_to_element_requested = Signal(object, str)  # element_id, element_type - pan drawing to element
    path_changed = Signal(int)  # Emitted when path selection changes
    edit_element_requested = Signal(object, str)  # element_id, element_type - open edit dialog
    
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
        
        # Ensure light background and dark text for the entire panel
        self.setStyleSheet("""
            PathAnalysisPanel {
                background-color: #f5f5f5;
            }
            PathAnalysisPanel QLabel {
                color: #333;
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
        
        # Main content area with scroll
        self.content_widget = QWidget()
        content_layout = QVBoxLayout()
        content_layout.setContentsMargins(0, 0, 0, 0)
        
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
            }
        """)
        
        self.diagram_container = QWidget()
        self.diagram_layout = QVBoxLayout()
        self.diagram_layout.setContentsMargins(4, 4, 4, 4)
        self.diagram_layout.setSpacing(0)
        self.diagram_container.setLayout(self.diagram_layout)
        scroll.setWidget(self.diagram_container)
        
        content_layout.addWidget(scroll, 1)
        
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
        segments = getattr(path, 'segments', None)
        if not segments:
            return "Unknown Source"
        
        # Get the first segment's from_component
        try:
            first_segment = min(segments, key=lambda s: getattr(s, 'segment_order', 0) or 0)
            from_comp = getattr(first_segment, 'from_component', None)
            if from_comp:
                name = getattr(from_comp, 'name', None) or getattr(from_comp, 'component_type', None)
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
        
        # Segments and intermediate components
        segments = sorted(self.current_path.segments, key=lambda s: s.segment_order or 0)
        segment_results = self.calculation_results.get('path_elements', [])
        
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
    
    def _get_source_component_id(self) -> Optional[int]:
        """Get the ID of the source component"""
        if not self.current_path:
            return None
        
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
