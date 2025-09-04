"""
HVAC Segment Dialog - Configure duct segments with fittings and acoustic properties
"""

from typing import Union, Optional
from PySide6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QFormLayout,
                             QLabel, QLineEdit, QTextEdit, QComboBox, 
                             QPushButton, QGroupBox, QDoubleSpinBox,
                             QMessageBox, QSpinBox, QCheckBox, QTableWidget,
                             QTableWidgetItem, QHeaderView, QListWidget,
                             QListWidgetItem, QSplitter, QWidget, QSizePolicy)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont

from models import get_session
from models.database import get_hvac_session
from models.hvac import HVACSegment, SegmentFitting
from data.components import STANDARD_FITTINGS
from calculations.hvac_path_calculator import HVACPathCalculator
from calculations.noise_calculator import NoiseCalculator


class FittingTableWidget(QTableWidget):
    """Table widget for managing segment fittings"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.init_ui()
        
    def init_ui(self):
        """Initialize the table UI"""
        self.setColumnCount(4)
        self.setHorizontalHeaderLabels(["Fitting Type", "Quantity", "Noise Adjustment", "Actions"])
        
        # Set column widths
        header = self.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.Stretch)
        header.setSectionResizeMode(1, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.ResizeToContents)
        
        self.setMaximumHeight(200)
        
    def add_fitting(self, fitting_type, quantity=1, noise_adjustment=0.0):
        """Add a fitting to the table"""
        row = self.rowCount()
        self.insertRow(row)
        
        # Fitting type
        type_combo = QComboBox()
        type_combo.addItems(list(STANDARD_FITTINGS.keys()))
        type_combo.setCurrentText(fitting_type)
        self.setCellWidget(row, 0, type_combo)
        
        # Quantity
        qty_spin = QSpinBox()
        qty_spin.setRange(1, 10)
        qty_spin.setValue(quantity)
        self.setCellWidget(row, 1, qty_spin)
        
        # Noise adjustment
        noise_spin = QDoubleSpinBox()
        noise_spin.setRange(-20, 20)
        noise_spin.setSuffix(" dB")
        noise_spin.setDecimals(1)
        noise_spin.setValue(noise_adjustment)
        self.setCellWidget(row, 2, noise_spin)
        
        # Remove button
        remove_btn = QPushButton("Remove")
        remove_btn.clicked.connect(lambda: self.remove_fitting(row))
        self.setCellWidget(row, 3, remove_btn)
        
    def remove_fitting(self, row):
        """Remove a fitting from the table"""
        self.removeRow(row)
        
    def get_fittings_data(self):
        """Get fittings data from table"""
        fittings = []
        for row in range(self.rowCount()):
            fitting_type = self.cellWidget(row, 0).currentText()
            quantity = self.cellWidget(row, 1).value()
            noise_adjustment = self.cellWidget(row, 2).value()
            
            fittings.append({
                'fitting_type': fitting_type,
                'quantity': quantity,
                'noise_adjustment': noise_adjustment
            })
        return fittings
        
    def set_fittings_data(self, fittings_data):
        """Set fittings data in table"""
        self.setRowCount(0)
        for fitting in fittings_data:
            self.add_fitting(
                fitting.get('fitting_type', 'elbow'),
                fitting.get('quantity', 1),
                fitting.get('noise_adjustment', 0.0)
            )


class HVACSegmentDialog(QDialog):
    """Dialog for configuring HVAC segments with fittings"""
    
    segment_saved = Signal(HVACSegment)  # Emits saved segment
    segment_updated = Signal(int)  # Emits segment ID when updated
    
    def __init__(self, parent=None, hvac_path_id=None, from_component=None, 
                 to_component=None, segment=None):
        super().__init__(parent)
        self.hvac_path_id = hvac_path_id
        self.from_component = from_component
        self.to_component = to_component
        
        # Handle the case where segment is passed as an integer ID
        if isinstance(segment, int):
            segment_id = segment
            import os
            debug_enabled = os.environ.get('HVAC_DEBUG_EXPORT')
            if debug_enabled:
                print(f"DEBUG_SEG: Dialog received segment ID {segment_id}, loading from database")
            
            try:
                from models.database import get_hvac_session
                from models.hvac import HVACSegment
                from sqlalchemy.orm import selectinload
                
                with get_hvac_session() as session:
                    segment = (
                        session.query(HVACSegment)
                        .options(
                            selectinload(HVACSegment.from_component),
                            selectinload(HVACSegment.to_component),
                            selectinload(HVACSegment.fittings)
                        )
                        .filter_by(id=segment_id)
                        .first()
                    )
                    
                    if not segment:
                        raise ValueError(f"Segment with ID {segment_id} not found")
                    
                    # Pre-load relationships while session is active
                    from_component = segment.from_component
                    to_component = segment.to_component  
                    fittings = list(segment.fittings)
                    
                    if debug_enabled:
                        print(f"DEBUG_SEG: Successfully loaded segment {segment_id} from database:")
                        print(f"DEBUG_SEG:   length = {segment.length}")
                        print(f"DEBUG_SEG:   duct_width = {segment.duct_width}")
                        print(f"DEBUG_SEG:   duct_height = {segment.duct_height}")
                        
                    # Store the loaded data in case the segment becomes detached
                    self._segment_data = {
                        'id': segment.id,
                        'length': segment.length,
                        'duct_width': segment.duct_width,
                        'duct_height': segment.duct_height,
                        'diameter': getattr(segment, 'diameter', 0),
                        'duct_shape': segment.duct_shape,
                        'duct_type': segment.duct_type,
                        'segment_order': segment.segment_order,
                        'flow_rate': segment.flow_rate,
                        'flow_velocity': segment.flow_velocity,
                        'insulation': getattr(segment, 'insulation', None),
                        'lining_thickness': getattr(segment, 'lining_thickness', 0),
                        'from_component': from_component,
                        'to_component': to_component,
                        'fittings': fittings
                    }
                        
            except Exception as e:
                if debug_enabled:
                    print(f"DEBUG_SEG: Failed to load segment {segment_id}: {e}")
                # Fall back to None to create new segment
                segment = None
        
        self.segment = segment  # Existing segment for editing
        self.is_editing = segment is not None
        # Guard flag: becomes True after UI has been populated with DB values
        self._ui_ready = False
        
        # Calculators for context-aware fitting calculations
        self.path_calculator = HVACPathCalculator()
        self.noise_calc = NoiseCalculator()
        self.noise_engine = self.noise_calc.hvac_engine
        
        self.init_ui()
        if self.is_editing:
            self.load_segment_data()
        
    def init_ui(self):
        """Initialize the user interface"""
        title = "Edit HVAC Segment" if self.is_editing else "Configure HVAC Segment"
        self.setWindowTitle(title)
        self.setModal(True)
        self.resize(700, 600)
        
        layout = QVBoxLayout()
        
        # Header
        header_label = QLabel(title)
        header_label.setFont(QFont("Arial", 14, QFont.Bold))
        header_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(header_label)
        
        # Connection Information
        if self.from_component and self.to_component:
            connection_text = f"From: {self.from_component.name} → To: {self.to_component.name}"
            connection_label = QLabel(connection_text)
            connection_label.setStyleSheet("background-color: #f0f0f0; padding: 8px; border-radius: 4px;")
            layout.addWidget(connection_label)
        
        # Organize vertically: Fitting -> Segment -> Fitting
        v_splitter = QSplitter(Qt.Vertical)
        v_splitter.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        
        # Upstream fitting
        upstream_panel = self.create_upstream_fitting_panel()
        v_splitter.addWidget(upstream_panel)
        
        # Segment properties
        middle_panel = self.create_segment_properties_panel()
        v_splitter.addWidget(middle_panel)
        
        # Downstream fitting
        downstream_panel = self.create_downstream_fitting_panel()
        v_splitter.addWidget(downstream_panel)
        
        v_splitter.setSizes([220, 380, 220])
        layout.addWidget(v_splitter)
        layout.setStretch(0, 0)
        layout.setStretch(1, 1)
        
        # Buttons
        button_layout = QHBoxLayout()
        
        if self.is_editing:
            self.delete_btn = QPushButton("Delete Segment")
            self.delete_btn.setStyleSheet("background-color: #e74c3c; color: white;")
            self.delete_btn.clicked.connect(self.delete_segment)
            button_layout.addWidget(self.delete_btn)
        
        button_layout.addStretch()
        
        self.cancel_btn = QPushButton("Cancel")
        self.cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(self.cancel_btn)
        
        save_text = "Update Segment" if self.is_editing else "Create Segment"
        self.save_btn = QPushButton(save_text)
        self.save_btn.clicked.connect(self.save_segment)
        button_layout.addWidget(self.save_btn)
        
        layout.addLayout(button_layout)
        self.setLayout(layout)
        
        # Initial context compute (guard against premature clobbering)
        try:
            import os
            debug_enabled = os.environ.get('HVAC_DEBUG_EXPORT')
            if debug_enabled:
                print("DEBUG_SEG_INIT: Calling initial refresh_context (pre-load)")
            self.refresh_context()
        except Exception:
            pass

        # Apply endpoint fitting constraints based on connected component types
        try:
            self._apply_endpoint_fitting_constraints()
        except Exception:
            pass
        
    def create_segment_properties_panel(self):
        """Create the segment properties panel"""
        panel = QWidget()
        layout = QVBoxLayout()
        
        # Segment Information
        info_group = QGroupBox("Segment Information")
        info_layout = QFormLayout()
        
        # Length
        self.length_spin = QDoubleSpinBox()
        self.length_spin.setRange(0, 1000)
        self.length_spin.setSuffix(" ft")
        self.length_spin.setDecimals(1)
        info_layout.addRow("Length:", self.length_spin)
        
        # Segment order
        self.order_spin = QSpinBox()
        self.order_spin.setRange(1, 100)
        info_layout.addRow("Segment Order:", self.order_spin)
        
        info_group.setLayout(info_layout)
        layout.addWidget(info_group)
        
        # Duct Properties
        duct_group = QGroupBox("Duct Properties")
        duct_layout = QFormLayout()
        
        # Duct shape
        self.shape_combo = QComboBox()
        self.shape_combo.addItems(["rectangular", "circular"])  # use 'circular' to match engine
        self.shape_combo.currentTextChanged.connect(self.on_duct_shape_changed)
        duct_layout.addRow("Duct Shape:", self.shape_combo)
        
        # Duct dimensions
        self.width_spin = QDoubleSpinBox()
        self.width_spin.setRange(1, 100)
        self.width_spin.setSuffix(" in")
        self.width_spin.setDecimals(1)
        duct_layout.addRow("Width:", self.width_spin)
        
        self.height_spin = QDoubleSpinBox()
        self.height_spin.setRange(1, 100)
        self.height_spin.setSuffix(" in")
        self.height_spin.setDecimals(1)
        duct_layout.addRow("Height:", self.height_spin)

        # Diameter for circular ducts
        self.diameter_spin = QDoubleSpinBox()
        self.diameter_spin.setRange(1, 120)
        self.diameter_spin.setSuffix(" in")
        self.diameter_spin.setDecimals(1)
        duct_layout.addRow("Diameter:", self.diameter_spin)
        
        # Duct type
        self.duct_type_combo = QComboBox()
        self.duct_type_combo.addItems(["sheet_metal", "fiberglass", "flexible"])
        duct_layout.addRow("Duct Type:", self.duct_type_combo)
        
        # Lining material and thickness
        self.insulation_combo = QComboBox()
        self.insulation_combo.addItems(["none", "fiberglass", "foam", "mineral_wool"])
        duct_layout.addRow("Lining Material:", self.insulation_combo)

        self.lining_thickness_spin = QDoubleSpinBox()
        self.lining_thickness_spin.setRange(0, 6)
        self.lining_thickness_spin.setDecimals(1)
        self.lining_thickness_spin.setSuffix(" in")
        duct_layout.addRow("Lining Thickness:", self.lining_thickness_spin)
        
        duct_group.setLayout(duct_layout)
        layout.addWidget(duct_group)
        
        # Acoustic Properties
        acoustic_group = QGroupBox("Acoustic Properties")
        acoustic_layout = QFormLayout()
        
        # Distance loss
        self.distance_loss_spin = QDoubleSpinBox()
        self.distance_loss_spin.setRange(0, 50)
        self.distance_loss_spin.setSuffix(" dB")
        self.distance_loss_spin.setDecimals(2)
        acoustic_layout.addRow("Distance Loss:", self.distance_loss_spin)
        
        # Duct loss
        self.duct_loss_spin = QDoubleSpinBox()
        self.duct_loss_spin.setRange(0, 50)
        self.duct_loss_spin.setSuffix(" dB")
        self.duct_loss_spin.setDecimals(2)
        acoustic_layout.addRow("Duct Loss:", self.duct_loss_spin)
        
        # Fitting additions
        self.fitting_additions_spin = QDoubleSpinBox()
        self.fitting_additions_spin.setRange(0, 20)
        self.fitting_additions_spin.setSuffix(" dB")
        self.fitting_additions_spin.setDecimals(2)
        acoustic_layout.addRow("Fitting Additions:", self.fitting_additions_spin)
        
        acoustic_group.setLayout(acoustic_layout)
        layout.addWidget(acoustic_group)
        
        # React to changes that affect downstream context
        self.length_spin.valueChanged.connect(self.on_segment_changed)
        self.shape_combo.currentTextChanged.connect(self.on_segment_changed)
        self.width_spin.valueChanged.connect(self.on_segment_changed)
        self.height_spin.valueChanged.connect(self.on_segment_changed)
        self.diameter_spin.valueChanged.connect(self.on_segment_changed)
        self.duct_type_combo.currentTextChanged.connect(self.on_segment_changed)
        self.insulation_combo.currentTextChanged.connect(self.on_segment_changed)
        self.lining_thickness_spin.valueChanged.connect(self.on_segment_changed)
        self.order_spin.valueChanged.connect(self.on_segment_changed)
        
        panel.setLayout(layout)
        return panel
        
    def create_upstream_fitting_panel(self):
        """Create panel for the fitting before the segment"""
        panel = QWidget()
        layout = QFormLayout()
        
        header = QLabel("Upstream Fitting")
        header.setFont(QFont("Arial", 12, QFont.Bold))
        header.setAlignment(Qt.AlignLeft)
        box = QVBoxLayout()
        box.addWidget(header)
        
        inner = QWidget()
        inner_layout = QFormLayout()
        
        self.up_fitting_combo = QComboBox()
        self.up_fitting_combo.addItem("none")
        self.up_fitting_combo.addItems(list(STANDARD_FITTINGS.keys()))
        self.up_fitting_combo.currentTextChanged.connect(self.on_upstream_fitting_changed)
        inner_layout.addRow("Fitting Type:", self.up_fitting_combo)
        
        self.upstream_noise_label = QLabel("Upstream: — dB(A)")
        inner_layout.addRow("Context Noise:", self.upstream_noise_label)
        
        self.up_auto_label = QLabel("Auto gen: — dB")
        inner_layout.addRow("Auto Generated:", self.up_auto_label)
        
        self.up_use_auto_chk = QCheckBox("Use auto")
        self.up_use_auto_chk.setChecked(True)
        self.up_use_auto_chk.stateChanged.connect(self.on_upstream_use_auto_changed)
        self.up_adjust_spin = QDoubleSpinBox()
        self.up_adjust_spin.setRange(-20, 20)
        self.up_adjust_spin.setDecimals(1)
        self.up_adjust_spin.setSuffix(" dB")
        self.up_adjust_spin.setEnabled(False)
        self.up_adjust_spin.valueChanged.connect(self.on_upstream_adjust_changed)
        auto_row = QHBoxLayout()
        auto_row.addWidget(self.up_use_auto_chk)
        auto_row.addWidget(self.up_adjust_spin)
        auto_container = QWidget()
        auto_container.setLayout(auto_row)
        inner_layout.addRow("Adjustment:", auto_container)
        
        inner.setLayout(inner_layout)
        box.addWidget(inner)
        panel.setLayout(box)
        return panel
    
    def create_downstream_fitting_panel(self):
        """Create panel for the fitting after the segment"""
        panel = QWidget()
        box = QVBoxLayout()
        header = QLabel("Downstream Fitting")
        header.setFont(QFont("Arial", 12, QFont.Bold))
        header.setAlignment(Qt.AlignLeft)
        box.addWidget(header)
        
        inner = QWidget()
        layout = QFormLayout()
        
        self.down_fitting_combo = QComboBox()
        self.down_fitting_combo.addItem("none")
        self.down_fitting_combo.addItems(list(STANDARD_FITTINGS.keys()))
        self.down_fitting_combo.currentTextChanged.connect(self.on_downstream_fitting_changed)
        layout.addRow("Fitting Type:", self.down_fitting_combo)
        
        self.downstream_noise_label = QLabel("After Segment: — dB(A)")
        layout.addRow("Context Noise:", self.downstream_noise_label)
        
        self.down_auto_label = QLabel("Auto gen: — dB")
        layout.addRow("Auto Generated:", self.down_auto_label)
        
        self.down_use_auto_chk = QCheckBox("Use auto")
        self.down_use_auto_chk.setChecked(True)
        self.down_use_auto_chk.stateChanged.connect(self.on_downstream_use_auto_changed)
        self.down_adjust_spin = QDoubleSpinBox()
        self.down_adjust_spin.setRange(-20, 20)
        self.down_adjust_spin.setDecimals(1)
        self.down_adjust_spin.setSuffix(" dB")
        self.down_adjust_spin.setEnabled(False)
        self.down_adjust_spin.valueChanged.connect(self.on_downstream_adjust_changed)
        auto_row = QHBoxLayout()
        auto_row.addWidget(self.down_use_auto_chk)
        auto_row.addWidget(self.down_adjust_spin)
        auto_container = QWidget()
        auto_container.setLayout(auto_row)
        layout.addRow("Adjustment:", auto_container)
        
        inner.setLayout(layout)
        box.addWidget(inner)
        panel.setLayout(box)
        return panel
    
    # --- Context and calculation helpers ---
    def _map_fitting_to_element_type(self, fitting_type: str) -> str:
        ft = (fitting_type or '').lower()
        if ft.startswith('elbow'):
            return 'elbow'
        if 'tee' in ft or 'junction' in ft or 'branch' in ft:
            return 'junction'
        if 'reducer' in ft:
            return 'junction'
        return 'duct'
    
    def _build_segment_element_from_ui(self):
        return self.noise_engine.__class__.PathElement if False else None  # placeholder to keep type hints quiet
    
    def _endpoint_allows_fitting(self, component) -> tuple:
        """Return (allowed: bool, default_fitting: Optional[str]) for a component endpoint.
        - Elbow components suggest 'elbow_90'
        - Branch/Junction/Tee components suggest 'tee_branch'
        - Other components do not allow endpoint fittings here.
        """
        try:
            if component is None:
                return False, None
            ctype = str(getattr(component, 'component_type', '') or '').lower()
            if 'elbow' in ctype:
                return True, 'elbow_90'
            if 'branch' in ctype or 'tee' in ctype or 'junction' in ctype:
                return True, 'tee_branch'
            return False, None
        except Exception:
            return False, None

    def _apply_endpoint_fitting_constraints(self) -> None:
        """Enable/disable upstream/downstream fitting combos based on neighbor components.
        Also set sensible default selection if allowed and currently 'none'.
        """
        # Upstream
        allow_up, up_default = self._endpoint_allows_fitting(getattr(self, 'from_component', None))
        self.up_fitting_combo.setEnabled(bool(allow_up))
        if not allow_up:
            self.up_fitting_combo.blockSignals(True)
            try:
                idx = self.up_fitting_combo.findText('none')
                if idx >= 0:
                    self.up_fitting_combo.setCurrentIndex(idx)
            finally:
                self.up_fitting_combo.blockSignals(False)
        else:
            # Apply default if currently 'none'
            if self.up_fitting_combo.currentText() == 'none' and up_default:
                self.up_fitting_combo.blockSignals(True)
                try:
                    idx = self.up_fitting_combo.findText(up_default)
                    if idx >= 0:
                        self.up_fitting_combo.setCurrentIndex(idx)
                finally:
                    self.up_fitting_combo.blockSignals(False)

        # Downstream
        allow_down, down_default = self._endpoint_allows_fitting(getattr(self, 'to_component', None))
        self.down_fitting_combo.setEnabled(bool(allow_down))
        if not allow_down:
            self.down_fitting_combo.blockSignals(True)
            try:
                idx = self.down_fitting_combo.findText('none')
                if idx >= 0:
                    self.down_fitting_combo.setCurrentIndex(idx)
            finally:
                self.down_fitting_combo.blockSignals(False)
        else:
            if self.down_fitting_combo.currentText() == 'none' and down_default:
                self.down_fitting_combo.blockSignals(True)
                try:
                    idx = self.down_fitting_combo.findText(down_default)
                    if idx >= 0:
                        self.down_fitting_combo.setCurrentIndex(idx)
                finally:
                    self.down_fitting_combo.blockSignals(False)

    def _make_segment_element(self):
        from calculations.hvac_noise_engine import PathElement
        element_type = 'duct'
        # Reuse legacy mapping if present in data later; for dialog, treat as duct
        return PathElement(
            element_type=element_type,
            element_id='editing_segment',
            length=self.length_spin.value() or 0.0,
            width=self.width_spin.value() or 12.0,
            height=self.height_spin.value() or 8.0,
            diameter=self.diameter_spin.value() or 0.0,
            duct_shape=self.shape_combo.currentText() or 'rectangular',
            duct_type=self.duct_type_combo.currentText() or 'sheet_metal',
            lining_thickness=self.lining_thickness_spin.value() or 0.0,
        )
    
    def _get_upstream_context(self) -> tuple:
        """Return (dba, spectrum) before this segment based on current path calc"""
        try:
            if not self.hvac_path_id:
                raise ValueError('no path id')
            
            # Update the in-memory segment object only after UI is populated
            if self._ui_ready and self.segment:
                self.update_segment_properties(self.segment)
            
            result = self.path_calculator.calculate_path_noise(self.hvac_path_id)
            order = self.order_spin.value() or (self.segment.segment_order if self.segment else 1)
            # If first segment, use source
            find_id = f"segment_{max(0, order-1)}"
            upstream_dba = None
            upstream_spectrum = None
            # element_results includes a source element with element_order 0
            for el in result.segment_results:
                if order == 1 and el.get('element_type') == 'source':
                    upstream_dba = el.get('noise_after_dba') or el.get('noise_after') or 50.0
                    upstream_spectrum = el.get('noise_after_spectrum')
                    break
                if el.get('element_id') == f"segment_{order-1}":
                    upstream_dba = el.get('noise_after_dba') or el.get('noise_after') or 50.0
                    upstream_spectrum = el.get('noise_after_spectrum')
                    break
            if upstream_dba is None:
                upstream_dba = 50.0
            if not upstream_spectrum:
                upstream_spectrum = self.noise_engine._estimate_spectrum_from_dba(upstream_dba)
            return upstream_dba, upstream_spectrum
        except Exception:
            dba = 50.0
            return dba, self.noise_engine._estimate_spectrum_from_dba(dba)
    
    def _get_downstream_context(self) -> tuple:
        """Return (dba, spectrum) after this segment based on segment attenuation applied to upstream"""
        up_dba, up_spec = self._get_upstream_context()
        element = self._make_segment_element()
        effect = self.noise_engine._calculate_element_effect(element, up_spec.copy(), up_dba)
        # Apply attenuation to get downstream spectrum, then recompute dBA
        downstream_spec = up_spec.copy()
        att = effect.get('attenuation_spectrum') or [0.0]*8
        if isinstance(att, list):
            for i in range(min(8, len(att))):
                downstream_spec[i] = max(0.0, downstream_spec[i] - att[i])
        down_dba = self.noise_engine._calculate_dba_from_spectrum(downstream_spec)
        return down_dba, downstream_spec
    
    def _auto_generated_for_fitting(self, fitting_type: str, context_spectrum: list, context_dba: float) -> float:
        """Return the net dB increase of a fitting given context spectrum.
        Calculates generated spectrum for the fitting and combines with context to
        report delta dB(A)."""
        from calculations.hvac_noise_engine import PathElement
        etype = self._map_fitting_to_element_type(fitting_type)
        element = PathElement(element_type=etype, element_id='tmp_fit')
        effect = self.noise_engine._calculate_element_effect(element, context_spectrum, context_dba)
        generated = effect.get('generated_spectrum') or [0.0] * 8
        new_spec = context_spectrum.copy()
        for i in range(min(8, len(generated))):
            if generated[i] > 0:
                new_spec[i] = self.noise_engine._combine_noise_levels(new_spec[i], generated[i])
        new_dba = self.noise_engine._calculate_dba_from_spectrum(new_spec)
        return max(0.0, new_dba - context_dba)
    
    def refresh_context(self):
        import os
        debug_enabled = os.environ.get('HVAC_DEBUG_EXPORT')
        
        if debug_enabled:
            print(f"\nDEBUG_SEG_CONTEXT: Refreshing context for segment dialog")
            print(f"DEBUG_SEG_CONTEXT: Current UI values:")
            print(f"DEBUG_SEG_CONTEXT:   length = {self.length_spin.value()}")
            print(f"DEBUG_SEG_CONTEXT:   width = {self.width_spin.value()}")
            print(f"DEBUG_SEG_CONTEXT:   height = {self.height_spin.value()}")
            print(f"DEBUG_SEG_CONTEXT:   shape = {self.shape_combo.currentText()}")
        
        try:
            up_dba, _ = self._get_upstream_context()
            self.upstream_noise_label.setText(f"Upstream: {up_dba:.1f} dB(A)")
            
            if debug_enabled:
                print(f"DEBUG_SEG_CONTEXT: Upstream context calculated: {up_dba:.1f} dB(A)")
            
            self._recalc_upstream_auto()
            self._recalc_downstream_context_and_auto()
            
            if debug_enabled:
                print(f"DEBUG_SEG_CONTEXT: Context refresh completed\n")
                
        except Exception as e:
            if debug_enabled:
                print(f"DEBUG_SEG_CONTEXT: Error during context refresh: {e}")
                import traceback
                traceback.print_exc()
    
    def _recalc_upstream_auto(self):
        dba, spec = self._get_upstream_context()
        ft = self.up_fitting_combo.currentText()
        if ft and ft != 'none':
            gen = self._auto_generated_for_fitting(ft, spec, dba)
        else:
            gen = 0.0
        self.up_auto_label.setText(f"Auto gen: {gen:+.1f} dB")
        if self.up_use_auto_chk.isChecked():
            self.up_adjust_spin.blockSignals(True)
            self.up_adjust_spin.setValue(gen)
            self.up_adjust_spin.blockSignals(False)
    
    def _recalc_downstream_context_and_auto(self):
        dba, spec = self._get_downstream_context()
        self.downstream_noise_label.setText(f"After Segment: {dba:.1f} dB(A)")
        ft = self.down_fitting_combo.currentText()
        if ft and ft != 'none':
            gen = self._auto_generated_for_fitting(ft, spec, dba)
        else:
            gen = 0.0
        self.down_auto_label.setText(f"Auto gen: {gen:+.1f} dB")
        if self.down_use_auto_chk.isChecked():
            self.down_adjust_spin.blockSignals(True)
            self.down_adjust_spin.setValue(gen)
            self.down_adjust_spin.blockSignals(False)
    
    # --- Signal handlers ---
    def on_segment_changed(self, *args):
        import os
        debug_enabled = os.environ.get('HVAC_DEBUG_EXPORT')
        
        if debug_enabled:
            print(f"\nDEBUG_SEG_CHANGE: Segment UI values changed, refreshing context")
            print(f"DEBUG_SEG_CHANGE: Triggered by: {args if args else 'unknown'}")
        
        try:
            # Update the in-memory segment only after UI is ready
            if self._ui_ready and self.is_editing and self.segment:
                if debug_enabled:
                    print(f"DEBUG_SEG_CHANGE: Updating in-memory segment before context refresh")
                self.update_segment_properties(self.segment)
            
            self.refresh_context()
        except Exception as e:
            if debug_enabled:
                print(f"DEBUG_SEG_CHANGE: Error during segment change handling: {e}")
    
    def on_upstream_fitting_changed(self, *args):
        self._recalc_upstream_auto()
    
    def on_upstream_use_auto_changed(self, state):
        self.up_adjust_spin.setEnabled(not self.up_use_auto_chk.isChecked())
        if self.up_use_auto_chk.isChecked():
            self._recalc_upstream_auto()
    
    def on_upstream_adjust_changed(self, *args):
        # No-op; value saved on commit
        pass
    
    def on_downstream_fitting_changed(self, *args):
        self._recalc_downstream_context_and_auto()
    
    def on_downstream_use_auto_changed(self, state):
        self.down_adjust_spin.setEnabled(not self.down_use_auto_chk.isChecked())
        if self.down_use_auto_chk.isChecked():
            self._recalc_downstream_context_and_auto()
    
    def on_downstream_adjust_changed(self, *args):
        # No-op; value saved on commit
        pass
    
        
    def on_duct_shape_changed(self, shape):
        """Handle duct shape change"""
        if shape == "circular":
            # Show diameter; hide rectangular dims
            self.diameter_spin.setEnabled(True)
            self.width_spin.setEnabled(False)
            self.height_spin.setEnabled(False)
        else:
            self.diameter_spin.setEnabled(False)
            self.width_spin.setEnabled(True)
            self.height_spin.setEnabled(True)
    
    def add_fitting(self):
        """Add a new fitting to the table"""
        self.fittings_table.add_fitting("elbow")
    
    def add_fitting_from_library(self, item):
        """Add fitting from library selection"""
        fitting_type = item.data(Qt.UserRole)
        self.fittings_table.add_fitting(fitting_type)
    
    def load_segment_data(self):
        """Load existing segment data for editing"""
        import os
        debug_enabled = os.environ.get('HVAC_DEBUG_EXPORT')
        
        if not self.segment:
            if debug_enabled:
                print("DEBUG_SEG: No segment to load")
            return
        
        if debug_enabled:
            print(f"\nDEBUG_SEG: Loading segment data for segment ID {getattr(self.segment, 'id', 'unknown')}")
            print(f"DEBUG_SEG: segment.length = {getattr(self.segment, 'length', 'missing')}")
            print(f"DEBUG_SEG: segment.duct_width = {getattr(self.segment, 'duct_width', 'missing')}")
            print(f"DEBUG_SEG: segment.duct_height = {getattr(self.segment, 'duct_height', 'missing')}")
            print(f"DEBUG_SEG: segment.duct_shape = {getattr(self.segment, 'duct_shape', 'missing')}")
            print(f"DEBUG_SEG: segment attributes: {[attr for attr in dir(self.segment) if not attr.startswith('_')]}")
        
        # Check if we have cached segment data from constructor loading
        if hasattr(self, '_segment_data') and self._segment_data:
            if debug_enabled:
                print("DEBUG_SEG: Using cached segment data from constructor")
            data = self._segment_data
            # Ensure we don't set zero values for critical dimensions
            length_val = float(data.get('length', 0) or 0)
            width_val = float(data.get('duct_width', 12) or 12)
            height_val = float(data.get('duct_height', 8) or 8)
            
            # Use reasonable defaults if values are zero or missing
            if length_val <= 0:
                length_val = 10.0  # Default 10 ft
                print(f"DEBUG_SEG: length 0, setting default length value to {length_val}")
            if width_val <= 0:
                width_val = 12.0   # Default 12 in
                print(f"DEBUG_SEG: width 0, setting default width value to {width_val}")
            if height_val <= 0:
                height_val = 8.0   # Default 8 in
                print(f"DEBUG_SEG: height 0, setting default height value to {height_val}")
                height_val = 8.0   # Default 8 in
            
            # Only set UI fields after computing sane defaults, and log before setting
            if debug_enabled:
                print(f"DEBUG_SEG: UI about to receive values (cached): length={length_val}, width={width_val}, height={height_val}")
            self.length_spin.blockSignals(True)
            self.length_spin.setValue(length_val)
            self.length_spin.blockSignals(False)
            self.order_spin.blockSignals(True)
            self.order_spin.setValue(data.get('segment_order', 1))
            self.order_spin.blockSignals(False)
            
            # Duct properties
            shape_val = data.get('duct_shape', 'rectangular') or 'rectangular'
            shape_index = self.shape_combo.findText(shape_val)
            self.shape_combo.blockSignals(True)
            if shape_index >= 0:
                self.shape_combo.setCurrentIndex(shape_index)
            else:
                self.shape_combo.setCurrentIndex(0)  # Default to first option
            self.shape_combo.blockSignals(False)
            # Ensure control enable states match selected shape
            try:
                self.on_duct_shape_changed(shape_val)
            except Exception:
                pass
            
            self.width_spin.blockSignals(True)
            self.width_spin.setValue(width_val)
            self.width_spin.blockSignals(False)
            self.height_spin.blockSignals(True)
            self.height_spin.setValue(height_val)
            self.height_spin.blockSignals(False)
            self.diameter_spin.blockSignals(True)
            self.diameter_spin.setValue(data.get('diameter', 0) or 0)
            self.diameter_spin.blockSignals(False)
            
            if debug_enabled:
                print(f"DEBUG_SEG: Applied cached values: length={length_val}, width={width_val}, height={height_val}")
            
            # This print is now inside the value setting block above
        else:
            # Fallback to direct segment access (original logic)
            if debug_enabled:
                print("DEBUG_SEG: Using direct segment access (fallback)")
            # Ensure we don't set zero values for critical dimensions
            length_val = float(getattr(self.segment, 'length', 0) or 0)
            width_val = float(getattr(self.segment, 'duct_width', 12) or 12)
            height_val = float(getattr(self.segment, 'duct_height', 8) or 8)
            
            # Use reasonable defaults if values are zero or missing
            if length_val <= 0:
                length_val = 10.0  # Default 10 ft
            if width_val <= 0:
                width_val = 12.0   # Default 12 in
            if height_val <= 0:
                height_val = 8.0   # Default 8 in
            
            if debug_enabled:
                print(f"DEBUG_SEG: UI about to receive values (direct): length={length_val}, width={width_val}, height={height_val}")
            self.length_spin.blockSignals(True)
            self.length_spin.setValue(length_val)
            self.length_spin.blockSignals(False)
            self.order_spin.blockSignals(True)
            self.order_spin.setValue(getattr(self.segment, 'segment_order', 1) or 1)
            self.order_spin.blockSignals(False)
            
            # Duct properties
            shape_val = getattr(self.segment, 'duct_shape', 'rectangular') or 'rectangular'
            shape_index = self.shape_combo.findText(shape_val)
            self.shape_combo.blockSignals(True)
            if shape_index >= 0:
                self.shape_combo.setCurrentIndex(shape_index)
            else:
                self.shape_combo.setCurrentIndex(0)  # Default to first option
            self.shape_combo.blockSignals(False)
            try:
                self.on_duct_shape_changed(shape_val)
            except Exception:
                pass
            
            self.width_spin.blockSignals(True)
            self.width_spin.setValue(width_val)
            self.width_spin.blockSignals(False)
            self.height_spin.blockSignals(True)
            self.height_spin.setValue(height_val)
            self.height_spin.blockSignals(False)
            self.diameter_spin.blockSignals(True)
            self.diameter_spin.setValue(getattr(self.segment, 'diameter', 0) or 0)
            self.diameter_spin.blockSignals(False)
            
            if debug_enabled:
                print(f"DEBUG_SEG: Applied direct values: length={length_val}, width={width_val}, height={height_val}")
        
        # Get duct_type and other properties from cache or segment
        duct_type = None
        insulation = None
        lining_thickness = 0
        
        if hasattr(self, '_segment_data') and self._segment_data:
            duct_type = self._segment_data.get('duct_type')
            insulation = self._segment_data.get('insulation')
            lining_thickness = self._segment_data.get('lining_thickness', 0)
        else:
            duct_type = getattr(self.segment, 'duct_type', None)
            insulation = getattr(self.segment, 'insulation', None)
            lining_thickness = getattr(self.segment, 'lining_thickness', 0) or 0
        
        if duct_type:
            index = self.duct_type_combo.findText(duct_type)
            if index >= 0:
                self.duct_type_combo.setCurrentIndex(index)
        
        if insulation:
            index = self.insulation_combo.findText(insulation)
            if index >= 0:
                self.insulation_combo.setCurrentIndex(index)
        
        self.lining_thickness_spin.setValue(lining_thickness)
        
        # Acoustic properties
        self.distance_loss_spin.setValue(self.segment.distance_loss or 0)
        self.duct_loss_spin.setValue(self.segment.duct_loss or 0)
        self.fitting_additions_spin.setValue(self.segment.fitting_additions or 0)
        
        # Load fittings reliably using stored position_on_segment so upstream/downstream
        # are deterministic regardless of DB return order.
        try:
            fits = list(self.segment.fittings)
        except Exception:
            fits = []
        # Sort by position; treat None as 0.0
        try:
            fits_sorted = sorted(fits, key=lambda f: (getattr(f, 'position_on_segment', 0.0) or 0.0))
        except Exception:
            fits_sorted = fits
        # Map to upstream/downstream
        length_val = float(getattr(self.segment, 'length', 0.0) or 0.0)
        if len(fits_sorted) == 1:
            f = fits_sorted[0]
            pos = float(getattr(f, 'position_on_segment', 0.0) or 0.0)
            # Heuristic: position in latter half -> downstream, else upstream
            is_down = pos >= max(0.0, 0.5 * length_val)
            if is_down:
                idx = self.down_fitting_combo.findText(f.fitting_type)
                if idx >= 0:
                    self.down_fitting_combo.setCurrentIndex(idx)
                if f.noise_adjustment is not None:
                    self.down_adjust_spin.setValue(f.noise_adjustment)
            else:
                idx = self.up_fitting_combo.findText(f.fitting_type)
                if idx >= 0:
                    self.up_fitting_combo.setCurrentIndex(idx)
                if f.noise_adjustment is not None:
                    self.up_adjust_spin.setValue(f.noise_adjustment)
        elif len(fits_sorted) >= 2:
            up_f = fits_sorted[0]
            down_f = fits_sorted[-1]
            idx = self.up_fitting_combo.findText(up_f.fitting_type)
            if idx >= 0:
                self.up_fitting_combo.setCurrentIndex(idx)
            if getattr(up_f, 'noise_adjustment', None) is not None:
                self.up_adjust_spin.setValue(up_f.noise_adjustment)
            idx = self.down_fitting_combo.findText(down_f.fitting_type)
            if idx >= 0:
                self.down_fitting_combo.setCurrentIndex(idx)
            if getattr(down_f, 'noise_adjustment', None) is not None:
                self.down_adjust_spin.setValue(down_f.noise_adjustment)

        # Enforce applicability and defaults now that prior values are loaded
        try:
            self._apply_endpoint_fitting_constraints()
        except Exception:
            pass
        # Final UI validation and debugging
        if debug_enabled:
            print(f"DEBUG_SEG: Final UI state after load_segment_data:")
            print(f"DEBUG_SEG:   length_spin.value() = {self.length_spin.value()}")
            print(f"DEBUG_SEG:   width_spin.value() = {self.width_spin.value()}")
            print(f"DEBUG_SEG:   height_spin.value() = {self.height_spin.value()}")
            print(f"DEBUG_SEG:   shape_combo.currentText() = '{self.shape_combo.currentText()}'")
            print(f"DEBUG_SEG:   duct_type_combo.currentText() = '{self.duct_type_combo.currentText()}'")
            
            # Check if values are still zeros (problem detection)
            if self.length_spin.value() == 0:
                print(f"DEBUG_SEG: WARNING - Length is still 0 after loading!")
            if self.width_spin.value() == 0:
                print(f"DEBUG_SEG: WARNING - Width is still 0 after loading!")
            if self.height_spin.value() == 0:
                print(f"DEBUG_SEG: WARNING - Height is still 0 after loading!")
        
        # Mark UI ready and then refresh computed context to display labels
        try:
            self._ui_ready = True
            self.refresh_context()
        except Exception as e:
            if debug_enabled:
                print(f"DEBUG_SEG: Error during context refresh: {e}")
        
        if debug_enabled:
            print(f"DEBUG_SEG: load_segment_data completed\n")
    
    def reload_segment_from_database(self):
        """Reload segment data from database to reflect any external updates"""
        import os
        debug_enabled = os.environ.get('HVAC_DEBUG_EXPORT')
        
        if not self.is_editing or not self.segment:
            if debug_enabled:
                print("DEBUG_SEG_RELOAD: No segment to reload")
            return
        
        try:
            segment_id = getattr(self.segment, 'id', None)
            if not segment_id:
                if debug_enabled:
                    print("DEBUG_SEG_RELOAD: No segment ID available")
                return
            
            if debug_enabled:
                print(f"\nDEBUG_SEG_RELOAD: Reloading segment {segment_id} from database")
            
            from models.database import get_hvac_session
            from models.hvac import HVACSegment
            from sqlalchemy.orm import selectinload
            
            with get_hvac_session() as session:
                fresh_segment = (
                    session.query(HVACSegment)
                    .options(
                        selectinload(HVACSegment.from_component),
                        selectinload(HVACSegment.to_component),
                        selectinload(HVACSegment.fittings)
                    )
                    .filter_by(id=segment_id)
                    .first()
                )
                
                if not fresh_segment:
                    if debug_enabled:
                        print(f"DEBUG_SEG_RELOAD: Segment {segment_id} not found in database")
                    return
                
                # Cache the fresh data for loading
                self._segment_data = {
                    'id': fresh_segment.id,
                    'length': fresh_segment.length,
                    'duct_width': fresh_segment.duct_width,
                    'duct_height': fresh_segment.duct_height,
                    'duct_shape': fresh_segment.duct_shape,
                    'duct_type': fresh_segment.duct_type,
                    'segment_order': fresh_segment.segment_order,
                    'flow_rate': fresh_segment.flow_rate,
                    'flow_velocity': fresh_segment.flow_velocity,
                    'diameter': getattr(fresh_segment, 'diameter', 0),
                    'insulation': fresh_segment.insulation,
                    'lining_thickness': getattr(fresh_segment, 'lining_thickness', 0),
                    'from_component': fresh_segment.from_component,
                    'to_component': fresh_segment.to_component,
                    'fittings': list(fresh_segment.fittings)
                }
                
                # Update the dialog's segment reference
                self.segment = fresh_segment
                
                if debug_enabled:
                    print(f"DEBUG_SEG_RELOAD: Reloaded segment data:")
                    print(f"DEBUG_SEG_RELOAD:   length = {fresh_segment.length}")
                    print(f"DEBUG_SEG_RELOAD:   duct_width = {fresh_segment.duct_width}")
                    print(f"DEBUG_SEG_RELOAD:   duct_height = {fresh_segment.duct_height}")
                    print(f"DEBUG_SEG_RELOAD:   duct_shape = {fresh_segment.duct_shape}")
            
            # Reload the UI with fresh data
            self.load_segment_data()
            
            if debug_enabled:
                print(f"DEBUG_SEG_RELOAD: UI reloaded with fresh database data\n")
            
        except Exception as e:
            if debug_enabled:
                print(f"DEBUG_SEG_RELOAD: Error reloading segment: {e}")
                import traceback
                traceback.print_exc()
    
    def save_segment(self):
        """Save the HVAC segment using standardized session management"""
        # Validate inputs first
        if not self.validate_segment_inputs():
            return
            
        try:
            with get_hvac_session() as session:
                if self.is_editing:
                    # Always re-query to get session-attached instance
                    segment = session.query(HVACSegment).filter(HVACSegment.id == self.segment.id).first()
                    if not segment:
                        raise ValueError("Segment not found in database")
                    
                    # Apply changes to session-attached instance
                    self.apply_changes_to_segment(segment, session)
                    
                    # Update our dialog reference to the session-attached instance
                    self.segment = segment
                else:
                    # Create new segment
                    segment = self.create_new_segment()
                    session.add(segment)
                    session.flush()  # Get ID before commit
                    self.segment = segment
                    
                    # Add fittings to new segment
                    self.update_segment_fittings(segment, session)
                
                # Clear cached segment data since we now use session-attached instances
                self._segment_data = None
                
                # Commit handled by context manager
            
            # Post-save operations
            self.trigger_path_recalculation()
            
            # Emit signals for UI updates
            self.segment_saved.emit(self.segment)
            if self.is_editing:
                self.segment_updated.emit(self.segment.id)
            
            self.accept()
            
        except Exception as e:
            import os
            if os.environ.get('HVAC_DEBUG_EXPORT'):
                import traceback
                traceback.print_exc()
            QMessageBox.critical(self, "Save Error", f"Failed to save segment:\n{str(e)}")
    
    def validate_segment_inputs(self):
        """Validate segment input fields"""
        if self.length_spin.value() <= 0:
            QMessageBox.warning(self, "Validation Error", "Please enter a valid segment length.")
            return False
        return True
    
    def apply_changes_to_segment(self, segment, session):
        """Apply UI changes to the session-attached segment instance"""
        import os
        debug_enabled = os.environ.get('HVAC_DEBUG_EXPORT')
        
        if debug_enabled:
            print(f"DEBUG_SEG_SAVE: Applying changes to segment ID {segment.id}")
            print(f"DEBUG_SEG_SAVE: Current UI values:")
            print(f"  length = {self.length_spin.value()}")
            print(f"  width = {self.width_spin.value()}")
            print(f"  height = {self.height_spin.value()}")
        
        # Update segment properties
        segment.length = self.length_spin.value()
        segment.segment_order = self.order_spin.value()
        segment.duct_width = self.width_spin.value()
        segment.duct_height = self.height_spin.value()
        segment.diameter = self.diameter_spin.value()
        segment.duct_shape = self.shape_combo.currentText()
        segment.duct_type = self.duct_type_combo.currentText()
        segment.insulation = self.insulation_combo.currentText()
        segment.lining_thickness = self.lining_thickness_spin.value()
        segment.distance_loss = self.distance_loss_spin.value()
        segment.duct_loss = self.duct_loss_spin.value()
        segment.fitting_additions = self.fitting_additions_spin.value()
        
        # Update fittings
        self.update_segment_fittings(segment, session)
        
        if debug_enabled:
            print(f"DEBUG_SEG_SAVE: Applied changes successfully")
    
    def create_new_segment(self):
        """Create a new segment instance from UI values"""
        return HVACSegment(
            hvac_path_id=self.hvac_path_id,
            from_component_id=self.from_component.id if self.from_component else None,
            to_component_id=self.to_component.id if self.to_component else None,
            length=self.length_spin.value(),
            segment_order=self.order_spin.value(),
            duct_width=self.width_spin.value(),
            duct_height=self.height_spin.value(),
            diameter=self.diameter_spin.value(),
            duct_shape=self.shape_combo.currentText(),
            duct_type=self.duct_type_combo.currentText(),
            insulation=self.insulation_combo.currentText(),
            lining_thickness=self.lining_thickness_spin.value(),
            distance_loss=self.distance_loss_spin.value(),
            duct_loss=self.duct_loss_spin.value(),
            fitting_additions=self.fitting_additions_spin.value()
        )
    
    def trigger_path_recalculation(self):
        """Trigger path recalculation after segment changes"""
        import os
        debug_enabled = os.environ.get('HVAC_DEBUG_EXPORT')
        
        if debug_enabled:
            print(f"DEBUG_SEG_SAVE: Triggering path recalculation for path {self.hvac_path_id}")
        
        try:
            if hasattr(self, 'path_calculator') and self.hvac_path_id:
                self.path_calculator.calculate_path_noise(self.hvac_path_id)
                if debug_enabled:
                    print(f"DEBUG_SEG_SAVE: Path recalculation completed")
        except Exception as calc_e:
            if debug_enabled:
                print(f"DEBUG_SEG_SAVE: Path recalculation failed: {calc_e}")
    
    def update_segment_properties(self, segment):
        """Update segment properties - now deprecated in favor of direct updates in save_segment"""
        import os
        debug_enabled = os.environ.get('HVAC_DEBUG_EXPORT')
        
        if debug_enabled:
            print(f"DEBUG_SEG_UPDATE: update_segment_properties called (deprecated method)")
            print(f"DEBUG_SEG_UPDATE: Segment ID: {getattr(segment, 'id', 'unknown')}")
        
        # This method is now only used for in-memory updates during context calculations
        # Actual database updates are handled directly in save_segment to avoid session issues
        if hasattr(segment, '__dict__'):  # Only update if it's a real object
            segment.length = self.length_spin.value()
            segment.segment_order = self.order_spin.value()
            segment.duct_width = self.width_spin.value()
            segment.duct_height = self.height_spin.value()
            segment.diameter = self.diameter_spin.value()
            segment.duct_shape = self.shape_combo.currentText()
            segment.duct_type = self.duct_type_combo.currentText()
            segment.insulation = self.insulation_combo.currentText()
            segment.lining_thickness = self.lining_thickness_spin.value()
            segment.distance_loss = self.distance_loss_spin.value()
            segment.duct_loss = self.duct_loss_spin.value()
            segment.fitting_additions = self.fitting_additions_spin.value()
            
            if debug_enabled:
                print(f"DEBUG_SEG_UPDATE: In-memory update complete")
    
    def update_segment_fittings(self, segment, session):
        """Update segment fittings"""
        # Remove existing fittings
        for fitting in list(segment.fittings):
            session.delete(fitting)
        
        # Upstream fitting (if any)
        up_type = self.up_fitting_combo.currentText()
        allow_up, _ = self._endpoint_allows_fitting(getattr(self, 'from_component', None))
        if allow_up and up_type and up_type != 'none':
            up_adj = self.up_adjust_spin.value()
            session.add(SegmentFitting(
                segment_id=segment.id,
                fitting_type=up_type,
                quantity=1,
                noise_adjustment=up_adj,
                position_on_segment=0.0
            ))
        
        # Downstream fitting (if any)
        down_type = self.down_fitting_combo.currentText()
        allow_down, _ = self._endpoint_allows_fitting(getattr(self, 'to_component', None))
        if allow_down and down_type and down_type != 'none':
            down_adj = self.down_adjust_spin.value()
            session.add(SegmentFitting(
                segment_id=segment.id,
                fitting_type=down_type,
                quantity=1,
                noise_adjustment=down_adj,
                position_on_segment=(segment.length or 0.0)
            ))
    
    def delete_segment(self):
        """Delete the HVAC segment"""
        if not self.is_editing or not self.segment:
            return
            
        reply = QMessageBox.question(
            self, "Delete Segment",
            f"Are you sure you want to delete this segment?\n\n"
            "This will also remove all fittings associated with this segment.",
            QMessageBox.Yes | QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            try:
                session = get_session()
                session.delete(self.segment)
                session.commit()
                session.close()
                
                self.accept()
                
            except Exception as e:
                session.rollback()
                session.close()
                QMessageBox.critical(self, "Error", f"Failed to delete segment:\n{str(e)}")


# Convenience function to show dialog
def show_hvac_segment_dialog(parent=None, hvac_path_id=None, from_component=None, 
                           to_component=None, segment=None):
    """Show HVAC segment dialog"""
    dialog = HVACSegmentDialog(parent, hvac_path_id, from_component, to_component, segment)
    return dialog.exec() 