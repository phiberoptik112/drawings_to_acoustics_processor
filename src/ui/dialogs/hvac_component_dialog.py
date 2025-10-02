"""
HVAC Component Dialog - Add and edit HVAC components with noise properties
"""

from typing import Union, Optional
from PySide6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QFormLayout,
                             QLabel, QLineEdit, QTextEdit, QComboBox, 
                             QPushButton, QGroupBox, QDoubleSpinBox,
                             QMessageBox, QSpinBox, QCheckBox)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont

from models import get_session
from models.database import get_hvac_session
from models.mechanical import MechanicalUnit
from models.hvac import HVACComponent, HVACPath, HVACSegment
from data.components import STANDARD_COMPONENTS
from calculations.hvac_constants import get_default_cfm_for_component, is_valid_cfm_value


class HVACComponentDialog(QDialog):
    """Dialog for adding and editing HVAC components"""
    
    component_saved = Signal(HVACComponent)  # Emits saved component
    
    def __init__(self, parent=None, project_id=None, drawing_id=None, component=None):
        super().__init__(parent)
        self.project_id = project_id
        self.drawing_id = drawing_id
        self.component = component  # Existing component for editing
        self.is_editing = component is not None
        # Track a selected Mechanical Unit from the chooser so we can persist on save
        self._selected_mech_unit_id = None
        
        self.init_ui()
        if self.is_editing:
            self.load_component_data()
        # Allow parent to feed HVAC engine context for passive components
        self._passive_context_elem = None
        
    def init_ui(self):
        """Initialize the user interface"""
        title = "Edit HVAC Component" if self.is_editing else "Add HVAC Component"
        self.setWindowTitle(title)
        self.setModal(True)
        self.resize(500, 400)
        
        layout = QVBoxLayout()
        
        # Header
        header_label = QLabel(title)
        header_label.setFont(QFont("Arial", 14, QFont.Bold))
        header_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(header_label)
        
        # Component Information
        info_group = QGroupBox("Component Information")
        info_layout = QFormLayout()
        
        # Component name
        self.name_edit = QLineEdit()
        self.name_edit.setPlaceholderText("e.g., AHU-1, VAV-Box-A, Diffuser-101")
        info_layout.addRow("Component Name:", self.name_edit)
        
        # Component type
        self.type_combo = QComboBox()
        component_types = list(STANDARD_COMPONENTS.keys())
        self.type_combo.addItems(component_types)
        self.type_combo.currentTextChanged.connect(self.on_component_type_changed)
        info_layout.addRow("Component Type:", self.type_combo)
        
        # Import from Library button row (mechanical units)
        import_row = QHBoxLayout()
        self.import_from_library_btn = QPushButton("Import from Library Mech. Units")
        self.import_from_library_btn.setToolTip("Load name/type (and standard noise) from project Mechanical Units library")
        self.import_from_library_btn.clicked.connect(self.import_from_library_mechanical_units)
        import_row.addWidget(self.import_from_library_btn)
        import_row.addStretch()
        info_layout.addRow("", self.import_from_library_btn)

        info_group.setLayout(info_layout)
        layout.addWidget(info_group)
        
        # Position Information
        position_group = QGroupBox("Position on Drawing")
        position_layout = QFormLayout()
        
        # X position
        self.x_spin = QSpinBox()
        self.x_spin.setRange(0, 10000)
        self.x_spin.setSuffix(" px")
        position_layout.addRow("X Position:", self.x_spin)
        
        # Y position
        self.y_spin = QSpinBox()
        self.y_spin.setRange(0, 10000)
        self.y_spin.setSuffix(" px")
        position_layout.addRow("Y Position:", self.y_spin)
        
        position_group.setLayout(position_layout)
        layout.addWidget(position_group)
        
        # Acoustic Properties
        acoustic_group = QGroupBox("Acoustic Properties")
        acoustic_layout = QFormLayout()
        
        # Noise level
        self.noise_spin = QDoubleSpinBox()
        self.noise_spin.setRange(0, 120)
        self.noise_spin.setSuffix(" dB(A)")
        self.noise_spin.setDecimals(1)
        acoustic_layout.addRow("Base Noise Level:", self.noise_spin)
        
        # CFM (airflow rate)
        self.cfm_spin = QDoubleSpinBox()
        self.cfm_spin.setRange(10, 100000)
        self.cfm_spin.setSuffix(" CFM")
        self.cfm_spin.setDecimals(0)
        acoustic_layout.addRow("Airflow Rate:", self.cfm_spin)
        
        # Use standard checkbox
        self.use_standard_cb = QCheckBox("Use standard values for component type")
        self.use_standard_cb.setChecked(True)
        self.use_standard_cb.toggled.connect(self.on_use_standard_toggled)
        acoustic_layout.addRow("", self.use_standard_cb)

        # Frequency preview (read-only) for imported Mechanical Units
        self.freq_preview_title = QLabel("Frequency Bands (Lp) — imported from Library when available")
        self.freq_preview_title.setStyleSheet("color: #aaa;")
        acoustic_layout.addRow(self.freq_preview_title)
        mono_css = "font-family: Courier New, monospace;"
        self.inlet_label = QLabel("Inlet: —")
        self.inlet_label.setStyleSheet(mono_css)
        self.radiated_label = QLabel("Radiated: —")
        self.radiated_label.setStyleSheet(mono_css)
        self.outlet_label = QLabel("Outlet: —")
        self.outlet_label.setStyleSheet(mono_css)
        acoustic_layout.addRow(self.inlet_label)
        acoustic_layout.addRow(self.radiated_label)
        acoustic_layout.addRow(self.outlet_label)
        
        acoustic_group.setLayout(acoustic_layout)
        layout.addWidget(acoustic_group)

        # Junction Preferences (only shown for relevant component types)
        self.junction_group = QGroupBox("Junction Preferences")
        self.junction_layout = QFormLayout()
        self.branch_takeoff_choice_combo = QComboBox()
        self.branch_takeoff_choice_combo.addItems(["auto", "main_duct", "branch_duct"])
        self.junction_layout.addRow("BRANCH_TAKEOFF_90 spectrum:", self.branch_takeoff_choice_combo)
        self.junction_group.setLayout(self.junction_layout)
        layout.addWidget(self.junction_group)
        
        # Component Details
        details_group = QGroupBox("Component Details")
        details_layout = QVBoxLayout()
        
        self.details_text = QTextEdit()
        self.details_text.setMaximumHeight(100)
        self.details_text.setPlaceholderText("Additional details about this component...")
        details_layout.addWidget(self.details_text)
        
        details_group.setLayout(details_layout)
        layout.addWidget(details_group)
        
        # Buttons
        button_layout = QHBoxLayout()
        
        if self.is_editing:
            self.delete_btn = QPushButton("Delete Component")
            self.delete_btn.setStyleSheet("background-color: #e74c3c; color: white;")
            self.delete_btn.clicked.connect(self.delete_component)
            button_layout.addWidget(self.delete_btn)
        
        button_layout.addStretch()
        
        self.cancel_btn = QPushButton("Cancel")
        self.cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(self.cancel_btn)
        
        save_text = "Update Component" if self.is_editing else "Add Component"
        self.save_btn = QPushButton(save_text)
        self.save_btn.clicked.connect(self.save_component)
        button_layout.addWidget(self.save_btn)
        
        layout.addLayout(button_layout)
        self.setLayout(layout)
        
        # Initialize with first component type
        self.on_component_type_changed(self.type_combo.currentText())

    # Public helper so parent dialogs can supply recent element result
    def apply_passive_context_from_element_result(self, element_result: dict) -> None:
        """Pre-load acoustic fields for passive components using the last analysis.

        element_result is expected to contain keys like 'noise_before',
        'noise_after_spectrum', 'attenuation_spectrum', 'generated_spectrum',
        and 'element_type'. We use this to compute a representative base
        noise level shown in the dialog.
        """
        try:
            self._passive_context_elem = dict(element_result or {})
            et = str(self._passive_context_elem.get('element_type', '') or '')
            # Only auto-derive for passive/inline types
            if et in {'duct', 'flex_duct', 'elbow', 'junction'}:
                # Fill preview labels from spectra where available
                def fmt(vals):
                    if not vals:
                        return '—'
                    return ", ".join(f"{float(v):.0f}" for v in vals)
                self.inlet_label.setText(f"Inlet:    —")
                self.radiated_label.setText(f"Radiated: —")
                self.outlet_label.setText(
                    f"Outlet:   {fmt(self._passive_context_elem.get('noise_after_spectrum'))}")
        except Exception:
            pass

    # --- Library import helpers ---
    def import_from_library_mechanical_units(self):
        """Open a simple chooser to select a MechanicalUnit from the project and
        populate component name/type and noise level accordingly."""
        try:
            session = get_session()
            units = (
                session.query(MechanicalUnit)
                .filter(MechanicalUnit.project_id == self.project_id)
                .order_by(MechanicalUnit.name)
                .all()
            )
            session.close()
        except Exception as e:
            QMessageBox.warning(self, "Library", f"Failed to load Mechanical Units:\n{e}")
            return

        if not units:
            QMessageBox.information(self, "Library", "No Mechanical Units found. Use Component Library to import.")
            return

        # Build a lightweight chooser dialog
        from PySide6.QtWidgets import QListWidget, QListWidgetItem
        chooser = QDialog(self)
        chooser.setWindowTitle("Select Mechanical Unit")
        v = QVBoxLayout(chooser)
        listw = QListWidget()
        for u in units:
            label_type = u.unit_type or "unit"
            item = QListWidgetItem(f"{u.name} ({label_type})")
            item.setData(Qt.UserRole, u)
            listw.addItem(item)
        v.addWidget(listw)
        btns = QHBoxLayout()
        select_btn = QPushButton("Select")
        cancel_btn = QPushButton("Cancel")
        btns.addStretch(); btns.addWidget(cancel_btn); btns.addWidget(select_btn)
        v.addLayout(btns)

        def accept_selection():
            item = listw.currentItem()
            if not item:
                QMessageBox.information(chooser, "Select", "Pick a unit from the list.")
                return
            unit = item.data(Qt.UserRole)
            self._apply_mechanical_unit(unit)
            chooser.accept()

        listw.itemDoubleClicked.connect(lambda _i: accept_selection())
        select_btn.clicked.connect(accept_selection)
        cancel_btn.clicked.connect(chooser.reject)

        # Save-on-close behavior: apply currently highlighted item even if user closes the chooser
        # without clicking Select. This ensures the latest visible choice is used.
        def on_close_result(result: int):
            try:
                item = listw.currentItem()
                if item is None:
                    return
                unit = item.data(Qt.UserRole)
                if unit is None:
                    return
                # Apply selection (this also persists immediately when editing)
                self._apply_mechanical_unit(unit)
            except Exception:
                # Non-fatal; user can still explicitly select or update
                pass
        chooser.finished.connect(on_close_result)
        print("DEBUG[HVACComponentDialog]: Opening Mechanical Unit chooser (project_id=",
              self.project_id, ") with count=", len(units))
        chooser.exec()

    def _apply_mechanical_unit(self, unit: MechanicalUnit) -> None:
        try:
            print(f"DEBUG[HVACComponentDialog]: Applying Mechanical Unit id={getattr(unit,'id',None)} name='{getattr(unit,'name',None)}' unit_type='{getattr(unit,'unit_type',None)}'")
        except Exception:
            pass
        # Set name
        self.name_edit.setText(unit.name or "")
        # Map unit_type to internal component types
        mapped_type = self._map_unit_type_to_component_type(unit.unit_type)
        idx = self.type_combo.findText(mapped_type)
        if idx >= 0:
            self.type_combo.setCurrentIndex(idx)
        else:
            # Fallback: append once
            if mapped_type:
                self.type_combo.addItem(mapped_type)
                self.type_combo.setCurrentText(mapped_type)
        # Populate acoustic properties from the unit's octave-band data when available
        try:
            import json
            def parse_row(js):
                if not js:
                    return None
                try:
                    data = json.loads(js)
                except Exception:
                    return None
                order = ["63","125","250","500","1000","2000","4000","8000"]
                vals = []
                for k in order:
                    v = data.get(k)
                    vals.append(float(v) if v is not None and str(v).strip() != '' else None)
                return vals
            inlet = parse_row(getattr(unit, 'inlet_levels_json', None))
            radiated = parse_row(getattr(unit, 'radiated_levels_json', None))
            outlet = parse_row(getattr(unit, 'outlet_levels_json', None))

            def fmt(vals):
                if not vals:
                    return "—"
                return ", ".join("" if v is None else f"{float(v):.0f}" for v in vals)

            self.inlet_label.setText(f"Inlet:    {fmt(inlet)}")
            self.radiated_label.setText(f"Radiated: {fmt(radiated)}")
            self.outlet_label.setText(f"Outlet:   {fmt(outlet)}")
            print("DEBUG[HVACComponentDialog]: Parsed bands inlet=", inlet, "radiated=", radiated, "outlet=", outlet)
            # Remember selection for persistence on save
            try:
                self._selected_mech_unit_id = int(getattr(unit, 'id', 0) or 0) or None
            except Exception:
                self._selected_mech_unit_id = None

            # Set CFM from mechanical unit if available
            if hasattr(unit, 'airflow_cfm') and unit.airflow_cfm:
                self.cfm_spin.setValue(unit.airflow_cfm)
                self.use_standard_cb.setChecked(False)
                self.cfm_spin.setEnabled(True)
            
            # If no band data is available, fall back to standard noise behavior
            if not (inlet or radiated or outlet):
                # Fallback to standard noise when no bands
                self.use_standard_cb.setChecked(True)
                self.on_use_standard_toggled(True)
        except Exception:
            # On any parsing failure, keep previous behavior
            self.use_standard_cb.setChecked(True)
            self.on_use_standard_toggled(True)

    @staticmethod
    def _map_unit_type_to_component_type(unit_type_text: Optional[str]) -> str:
        if not unit_type_text:
            return 'ahu'
        t = unit_type_text.strip().lower()
        # Common schedule abbreviations
        mapping = {
            'ahu': 'ahu',
            'rtu': 'ahu',  # roof-top unit behaves like AHU for noise seed
            'doas': 'ahu',
            'vav': 'vav',
            'ef': 'fan',
            'rf': 'fan',
            'tf': 'fan',
            'fan': 'fan',
            'diffuser': 'diffuser',
            'grille': 'grille',
            'return fan': 'fan',
            'exhaust fan': 'fan',
            'supply fan': 'fan',
            'chiller': 'fan',  # placeholder
        }
        # Try direct and startswith matching (e.g., 'ahu-4-1')
        if t in mapping:
            return mapping[t]
        for key in mapping:
            if t.startswith(key):
                return mapping[key]
        # default
        return 'ahu'
        
    def on_component_type_changed(self, component_type):
        """Handle component type change"""
        if component_type in STANDARD_COMPONENTS:
            standard_noise = STANDARD_COMPONENTS[component_type].get('noise_level', 50.0)
            standard_cfm = STANDARD_COMPONENTS[component_type].get('cfm', get_default_cfm_for_component(component_type))
            self.noise_spin.setValue(standard_noise)
            self.cfm_spin.setValue(standard_cfm)
            
            # Update name suggestion
            if not self.name_edit.text():
                self.name_edit.setText(f"{component_type.upper()}-1")
        # Show the junction preferences only for branch/junction-like components
        ctype = (component_type or '').lower()
        show_junction = ('branch' in ctype) or ('junction' in ctype) or ('tee' in ctype)
        self.junction_group.setVisible(show_junction)
    
    def on_use_standard_toggled(self, checked):
        """Handle use standard checkbox toggle"""
        if checked:
            component_type = self.type_combo.currentText()
            if component_type in STANDARD_COMPONENTS:
                standard_noise = STANDARD_COMPONENTS[component_type].get('noise_level', 50.0)
                standard_cfm = STANDARD_COMPONENTS[component_type].get('cfm', get_default_cfm_for_component(component_type))
                self.noise_spin.setValue(standard_noise)
                self.cfm_spin.setValue(standard_cfm)
            self.noise_spin.setEnabled(False)
            self.cfm_spin.setEnabled(False)
        else:
            self.noise_spin.setEnabled(True)
            self.cfm_spin.setEnabled(True)
    
    def load_component_data(self):
        """Load existing component data for editing"""
        if not self.component:
            return
        
        # Refresh component from database to ensure we have latest data
        try:
            session = get_session()
            fresh_component = session.query(HVACComponent).filter(HVACComponent.id == self.component.id).first()
            if fresh_component:
                print(f"DEBUG_COMPONENT_REFRESH: Refreshed component from database")
                print(f"DEBUG_COMPONENT_REFRESH:   Fresh CFM value: {fresh_component.cfm}")
                self.component = fresh_component
            session.close()
        except Exception as e:
            print(f"DEBUG_COMPONENT_REFRESH: Failed to refresh component: {e}")
            
        self.name_edit.setText(self.component.name)
        
        # Set component type
        index = self.type_combo.findText(self.component.component_type)
        if index >= 0:
            self.type_combo.setCurrentIndex(index)
        
        # Set position
        self.x_spin.setValue(int(self.component.x_position))
        self.y_spin.setValue(int(self.component.y_position))
        
        # Set noise level
        if self.component.noise_level is not None:
            self.noise_spin.setValue(self.component.noise_level)
            self.use_standard_cb.setChecked(False)
            self.noise_spin.setEnabled(True)
            
        # Set CFM value
        print(f"DEBUG_COMPONENT_LOAD: Loading component {self.component.id} ({self.component.name})")
        print(f"DEBUG_COMPONENT_LOAD:   Has CFM attr: {hasattr(self.component, 'cfm')}")
        print(f"DEBUG_COMPONENT_LOAD:   CFM value: {getattr(self.component, 'cfm', 'None')}")
        print(f"DEBUG_COMPONENT_LOAD:   CFM type: {type(getattr(self.component, 'cfm', None))}")
        
        if hasattr(self.component, 'cfm') and self.component.cfm is not None:
            print(f"DEBUG_COMPONENT_LOAD:   Setting CFM spin to: {self.component.cfm}")
            self.cfm_spin.setValue(self.component.cfm)
            self.use_standard_cb.setChecked(False)
            self.cfm_spin.setEnabled(True)
        else:
            # Use default CFM for component type
            default_cfm = get_default_cfm_for_component(self.component.component_type)
            print(f"DEBUG_COMPONENT_LOAD:   Using default CFM: {default_cfm}")
            self.cfm_spin.setValue(default_cfm)
        # Try to restore frequency preview from a Mechanical Unit association on any path
        try:
            session = get_session()
            db_comp = session.query(HVACComponent).filter(HVACComponent.id == self.component.id).first()
            if db_comp:
                paths = (
                    session.query(HVACPath)
                    .join(HVACSegment, HVACSegment.hvac_path_id == HVACPath.id)
                    .filter((HVACSegment.from_component_id == db_comp.id) | (HVACSegment.to_component_id == db_comp.id))
                    .all()
                )
                for p in paths:
                    if not p.segments:
                        continue
                    first_seg = sorted(p.segments, key=lambda s: getattr(s, 'segment_order', 0))[0]
                    if getattr(first_seg, 'from_component_id', None) != db_comp.id:
                        continue  # only treat this component as a source
                    mu_id = getattr(p, 'primary_source_id', None)
                    if mu_id:
                        try:
                            unit = session.query(MechanicalUnit).filter(MechanicalUnit.id == mu_id).first()
                        except Exception:
                            unit = None
                        if unit is not None:
                            print(f"DEBUG[HVACComponentDialog]: Restoring preview from Mechanical Unit id={mu_id} via path id={p.id}")
                            # Reuse the same rendering helpers
                            import json
                            def parse_row(js):
                                if not js:
                                    return None
                                try:
                                    data = json.loads(js)
                                except Exception:
                                    return None
                                order = ["63","125","250","500","1000","2000","4000","8000"]
                                return [float(data.get(k)) if data.get(k) not in (None, "") else None for k in order]
                            inlet = parse_row(getattr(unit, 'inlet_levels_json', None))
                            radiated = parse_row(getattr(unit, 'radiated_levels_json', None))
                            outlet = parse_row(getattr(unit, 'outlet_levels_json', None))
                            def fmt(vals):
                                if not vals:
                                    return "—"
                                return ", ".join("" if v is None else f"{float(v):.0f}" for v in vals)
                            self.inlet_label.setText(f"Inlet:    {fmt(inlet)}")
                            self.radiated_label.setText(f"Radiated: {fmt(radiated)}")
                            self.outlet_label.setText(f"Outlet:   {fmt(outlet)}")
                            self._selected_mech_unit_id = int(mu_id)
                            break
            session.close()
        except Exception as e:
            try:
                session.close()
            except Exception:
                pass
            print("DEBUG[HVACComponentDialog]: Failed to restore Mechanical Unit preview:", e)

        # Restore BRANCH_TAKEOFF_90 choice if present
        try:
            value = getattr(self.component, 'branch_takeoff_choice', None)
            if value:
                idx = self.branch_takeoff_choice_combo.findText(str(value))
                if idx >= 0:
                    self.branch_takeoff_choice_combo.setCurrentIndex(idx)
        except Exception:
            pass
    
    def save_component(self):
        """Save the HVAC component using standardized session management"""
        # Validate inputs first
        if not self.validate_component_inputs():
            return
        
        print(f"DEBUG_COMPONENT_SAVE_START: Starting save process")
        print(f"DEBUG_COMPONENT_SAVE_START:   is_editing: {self.is_editing}")
        print(f"DEBUG_COMPONENT_SAVE_START:   component_id: {getattr(self.component, 'id', 'None') if self.component else 'None'}")
        print(f"DEBUG_COMPONENT_SAVE_START:   UI CFM value: {self.cfm_spin.value()}")
        
        try:
            with get_hvac_session() as session:
                if self.is_editing:
                    # Always re-query to get session-attached instance
                    component = session.query(HVACComponent).filter(HVACComponent.id == self.component.id).first()
                    if not component:
                        raise ValueError("Component not found in database")
                    
                    print(f"DEBUG_COMPONENT_SAVE_START: Found component in DB:")
                    print(f"DEBUG_COMPONENT_SAVE_START:   DB CFM before save: {getattr(component, 'cfm', 'None')}")
                    
                    print("DEBUG[HVACComponentDialog]: Updating existing component", {
                        "id": component.id, "prev_name": component.name, 
                        "prev_type": component.component_type, "prev_noise": component.noise_level,
                        "prev_cfm": getattr(component, 'cfm', None)
                    })
                    
                    # Apply changes to session-attached instance
                    self.apply_changes_to_component(component, session)
                    
                    print(f"DEBUG_COMPONENT_SAVE_START: After apply_changes_to_component:")
                    print(f"DEBUG_COMPONENT_SAVE_START:   DB CFM after apply: {getattr(component, 'cfm', 'None')}")
                    
                    # Update our dialog reference to the session-attached instance
                    self.component = component
                    
                    print("DEBUG[HVACComponentDialog]: Saved component", {
                        "id": component.id, "name": component.name, 
                        "type": component.component_type, "noise": component.noise_level,
                        "cfm": getattr(component, 'cfm', None)
                    })
                else:
                    # Create new component
                    component = self.create_new_component()
                    session.add(component)
                    session.flush()  # Get ID before commit
                    self.component = component
                    
                    print("DEBUG[HVACComponentDialog]: Created new component", {
                        "id": component.id, "name": component.name, "type": component.component_type,
                        "cfm": getattr(component, 'cfm', None)
                    })
                
                # Commit handled by context manager
                print(f"DEBUG_COMPONENT_SAVE_START: About to commit changes")
            
            # Verify the save worked by re-querying
            with get_hvac_session() as verify_session:
                if self.is_editing:
                    verify_component = verify_session.query(HVACComponent).filter(HVACComponent.id == self.component.id).first()
                    if verify_component:
                        print(f"DEBUG_COMPONENT_SAVE_VERIFY: Post-save verification:")
                        print(f"DEBUG_COMPONENT_SAVE_VERIFY:   DB CFM after commit: {getattr(verify_component, 'cfm', 'None')}")
                        print(f"DEBUG_COMPONENT_SAVE_VERIFY:   Expected CFM: {self.cfm_spin.value()}")
                        if getattr(verify_component, 'cfm', None) == self.cfm_spin.value():
                            print(f"DEBUG_COMPONENT_SAVE_VERIFY:   SUCCESS: CFM saved correctly")
                        else:
                            print(f"DEBUG_COMPONENT_SAVE_VERIFY:   ERROR: CFM not saved correctly")
            
            self.component_saved.emit(self.component)
            self.accept()
            
        except Exception as e:
            print(f"DEBUG_COMPONENT_SAVE_ERROR: Save failed with error: {e}")
            QMessageBox.critical(self, "Save Error", f"Failed to save component:\n{str(e)}")
    
    def validate_component_inputs(self):
        """Validate component input fields"""
        name = self.name_edit.text().strip()
        if not name:
            QMessageBox.warning(self, "Validation Error", "Please enter a component name.")
            return False
        return True
    
    def apply_changes_to_component(self, component, session):
        """Apply UI changes to the session-attached component instance"""
        name = self.name_edit.text().strip()
        component.name = name
        component.component_type = self.type_combo.currentText()
        component.x_position = self.x_spin.value()
        component.y_position = self.y_spin.value()
        component.noise_level = self.noise_spin.value()
        # Persist BRANCH_TAKEOFF_90 preference
        try:
            component.branch_takeoff_choice = self.branch_takeoff_choice_combo.currentText()
        except Exception:
            pass
        
        # Debug CFM save process
        cfm_value = self.cfm_spin.value()
        print(f"DEBUG_COMPONENT_SAVE: Saving component {component.id} ({component.name})")
        print(f"DEBUG_COMPONENT_SAVE:   UI CFM value: {cfm_value}")
        print(f"DEBUG_COMPONENT_SAVE:   Setting component.cfm to: {cfm_value}")
        component.cfm = cfm_value
        
        # Handle mechanical unit association propagation
        self.update_mechanical_unit_associations(component, session)
    
    def create_new_component(self):
        """Create a new component instance from UI values"""
        name = self.name_edit.text().strip()
        cfm_value = self.cfm_spin.value()
        print(f"DEBUG_COMPONENT_CREATE: Creating new component")
        print(f"DEBUG_COMPONENT_CREATE:   UI CFM value: {cfm_value}")
        
        return HVACComponent(
            project_id=self.project_id,
            drawing_id=self.drawing_id,
            name=name,
            component_type=self.type_combo.currentText(),
            x_position=self.x_spin.value(),
            y_position=self.y_spin.value(),
            noise_level=self.noise_spin.value(),
            cfm=cfm_value,
            branch_takeoff_choice=self.branch_takeoff_choice_combo.currentText()
        )
    
    def update_mechanical_unit_associations(self, component, session):
        """Update mechanical unit associations for paths containing this component"""
        # If user imported a Mechanical Unit in this edit, propagate association to any paths
        try:
            if self._selected_mech_unit_id:
                print(f"DEBUG[HVACComponentDialog]: Propagating Mechanical Unit id {self._selected_mech_unit_id} to paths for component id {component.id}")
                paths = (
                    session.query(HVACPath)
                    .join(HVACSegment, HVACSegment.hvac_path_id == HVACPath.id)
                    .filter((HVACSegment.from_component_id == component.id) | (HVACSegment.to_component_id == component.id))
                    .all()
                )
                for p in paths:
                    if not p.segments:
                        continue
                    first_seg = sorted(p.segments, key=lambda s: getattr(s, 'segment_order', 0))[0]
                    if getattr(first_seg, 'from_component_id', None) == component.id:
                        p.primary_source_id = self._selected_mech_unit_id
                        print(f"DEBUG[HVACComponentDialog]: Updated path id={p.id} primary_source_id -> MechanicalUnit id {self._selected_mech_unit_id}")
        except Exception as e:
            print("DEBUG[HVACComponentDialog]: Failed to update paths with Mechanical Unit:", e)
    
    def delete_component(self):
        """Delete the HVAC component"""
        if not self.is_editing or not self.component:
            return
            
        reply = QMessageBox.question(
            self, "Delete Component",
            f"Are you sure you want to delete '{self.component.name}'?\n\n"
            "This will also remove any segments connected to this component.",
            QMessageBox.Yes | QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            try:
                session = get_session()
                session.delete(self.component)
                session.commit()
                session.close()
                
                self.accept()
                
            except Exception as e:
                session.rollback()
                session.close()
                QMessageBox.critical(self, "Error", f"Failed to delete component:\n{str(e)}")


# Convenience function to show dialog
def show_hvac_component_dialog(parent=None, project_id=None, drawing_id=None, component=None):
    """Show HVAC component dialog"""
    dialog = HVACComponentDialog(parent, project_id, drawing_id, component)
    return dialog.exec() 