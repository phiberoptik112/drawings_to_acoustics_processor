"""
Silencer Filter Dialog - Filter and select silencer products based on requirements
"""

from PySide6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QFormLayout,
                             QLabel, QLineEdit, QComboBox, QPushButton,
                             QGroupBox, QDoubleSpinBox, QSpinBox, QTableWidget,
                             QTableWidgetItem, QHeaderView, QMessageBox,
                             QSplitter, QTextEdit, QCheckBox, QFrame,
                             QScrollArea, QGridLayout, QWidget)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont

from typing import Dict, Any, Optional, List
from data.silencer_database import SilencerFilterEngine
from models import get_session
from models.hvac import SilencerProduct

_FREQ_BANDS = [63, 125, 250, 500, 1000, 2000, 4000, 8000]


class SilencerFilterDialog(QDialog):
    """Dialog for filtering and selecting silencer products"""

    product_selected = Signal(SilencerProduct)

    def __init__(self, noise_requirements=None, space_constraints=None,
                 nc_compliance_data=None, parent=None):
        super().__init__(parent)
        self.noise_requirements = noise_requirements or {}
        self.space_constraints = space_constraints or {}
        # nc_compliance_data keys: target_nc (int), receiver_spectrum ([8 floats]),
        #   nc_limits ([8 floats]), required_il ([8 floats])
        self.nc_compliance_data = nc_compliance_data
        self.filter_engine = SilencerFilterEngine()
        self.selected_product = None
        self.products_data = []

        self.init_ui()
        self.load_initial_requirements()
        self.update_product_list()
        
    def init_ui(self):
        """Initialize the user interface"""
        self.setWindowTitle("Silencer Product Selection")
        self.setModal(True)
        self.resize(1100, 750)

        main_layout = QVBoxLayout()

        # Header
        header_label = QLabel("Silencer Product Selection & Filtering")
        header_label.setFont(QFont("Arial", 14, QFont.Bold))
        header_label.setAlignment(Qt.AlignCenter)
        main_layout.addWidget(header_label)

        # Create splitter for filter criteria and results
        splitter = QSplitter(Qt.Horizontal)

        # Left panel - scrollable filter criteria
        filter_content = self.create_filter_panel()
        scroll = QScrollArea()
        scroll.setWidget(filter_content)
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll.setMinimumWidth(320)
        scroll.setMaximumWidth(380)
        splitter.addWidget(scroll)

        # Right panel - Product results
        results_panel = self.create_results_panel()
        splitter.addWidget(results_panel)

        # Set initial sizes (left filter, right results)
        splitter.setSizes([350, 750])
        main_layout.addWidget(splitter)
        
        # Buttons
        button_layout = QHBoxLayout()
        
        # Product count label
        self.product_count_label = QLabel("0 products found")
        button_layout.addWidget(self.product_count_label)
        
        button_layout.addStretch()
        
        self.clear_btn = QPushButton("Clear Filters")
        self.clear_btn.clicked.connect(self.clear_filters)
        button_layout.addWidget(self.clear_btn)
        
        self.cancel_btn = QPushButton("Cancel")
        self.cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(self.cancel_btn)
        
        self.select_btn = QPushButton("Select Product")
        self.select_btn.setStyleSheet("background-color: #2ecc71; color: white; font-weight: bold;")
        self.select_btn.clicked.connect(self.select_product)
        self.select_btn.setEnabled(False)
        button_layout.addWidget(self.select_btn)
        
        main_layout.addLayout(button_layout)
        self.setLayout(main_layout)
    
    def _load_manufacturer_list(self):
        """Populate manufacturer combo from the database"""
        try:
            session = get_session()
            rows = session.query(SilencerProduct.manufacturer).distinct().order_by(SilencerProduct.manufacturer).all()
            session.close()
            for (mfr,) in rows:
                if mfr:
                    self.manufacturer_combo.addItem(mfr)
        except Exception:
            for mfr in ["IAC Acoustics", "Kinetics", "Price Industries", "Ruskin", "SoundAttenuators", "Vibro-Acoustics"]:
                self.manufacturer_combo.addItem(mfr)

    def create_nc_compliance_group(self) -> QGroupBox:
        """Build the read-only NC Compliance Requirements display."""
        group = QGroupBox("NC Compliance Requirements")
        outer = QVBoxLayout()

        if not self.nc_compliance_data:
            placeholder = QLabel("No path calculation data available.\nOpen via the path analysis panel\nto see per-band NC requirements.")
            placeholder.setAlignment(Qt.AlignCenter)
            placeholder.setStyleSheet("color: #888; font-style: italic; padding: 8px;")
            outer.addWidget(placeholder)
            group.setLayout(outer)
            return group

        data = self.nc_compliance_data
        target_nc = data.get('target_nc')
        receiver_spectrum = data.get('receiver_spectrum', [0.0] * 8)
        nc_limits = data.get('nc_limits', [0.0] * 8)
        required_il = data.get('required_il', [0.0] * 8)

        # Target NC header
        nc_label = QLabel(f"Target: NC-{target_nc}" if target_nc else "Target NC: —")
        nc_label.setFont(QFont("Arial", 10, QFont.Bold))
        nc_label.setAlignment(Qt.AlignCenter)
        outer.addWidget(nc_label)

        # Column headers
        grid = QGridLayout()
        grid.setHorizontalSpacing(6)
        grid.setVerticalSpacing(2)
        for col, heading in enumerate(["Hz", "Received", "NC Limit", "Need IL"]):
            lbl = QLabel(heading)
            lbl.setFont(QFont("Arial", 8, QFont.Bold))
            lbl.setAlignment(Qt.AlignCenter)
            grid.addWidget(lbl, 0, col)

        for row_idx, (freq, received, limit, need_il) in enumerate(
            zip(_FREQ_BANDS, receiver_spectrum, nc_limits, required_il), start=1
        ):
            compliant = need_il <= 0.0
            bg = "#e8f5e9" if compliant else ("#fff3e0" if need_il < 5 else "#ffebee")
            text_color = "#2e7d32" if compliant else ("#e65100" if need_il < 5 else "#b71c1c")
            row_style = f"background-color: {bg}; color: {text_color}; border-radius: 3px; padding: 2px 4px;"

            freq_lbl = QLabel(f"{freq}")
            freq_lbl.setAlignment(Qt.AlignCenter)
            freq_lbl.setStyleSheet(row_style)
            grid.addWidget(freq_lbl, row_idx, 0)

            recv_lbl = QLabel(f"{received:.1f} dB")
            recv_lbl.setAlignment(Qt.AlignCenter)
            recv_lbl.setStyleSheet(row_style)
            grid.addWidget(recv_lbl, row_idx, 1)

            limit_lbl = QLabel(f"{limit:.0f} dB")
            limit_lbl.setAlignment(Qt.AlignCenter)
            limit_lbl.setStyleSheet(row_style)
            grid.addWidget(limit_lbl, row_idx, 2)

            if compliant:
                need_text = "OK"
            else:
                need_text = f"+{need_il:.1f} dB"
            need_lbl = QLabel(need_text)
            need_lbl.setAlignment(Qt.AlignCenter)
            font = QFont("Arial", 9, QFont.Bold)
            need_lbl.setFont(font)
            need_lbl.setStyleSheet(row_style)
            grid.addWidget(need_lbl, row_idx, 3)

        outer.addLayout(grid)

        # Legend
        legend = QLabel("Green = compliant  |  Amber/Red = IL needed")
        legend.setAlignment(Qt.AlignCenter)
        legend.setStyleSheet("color: #666; font-size: 9px; padding-top: 4px;")
        outer.addWidget(legend)

        group.setLayout(outer)
        return group

    def create_filter_panel(self):
        """Create the filter criteria panel"""
        panel = QFrame()
        layout = QVBoxLayout()

        # NC Compliance display (top)
        layout.addWidget(self.create_nc_compliance_group())

        # Insertion Loss Requirements
        il_group = QGroupBox("Required Insertion Loss")
        il_layout = QFormLayout()
        
        self.insertion_loss_spins = {}
        frequency_bands = [63, 125, 250, 500, 1000, 2000, 4000, 8000]
        
        for freq in frequency_bands:
            spin = QDoubleSpinBox()
            spin.setRange(0, 50)
            spin.setSuffix(" dB")
            spin.setDecimals(1)
            spin.valueChanged.connect(self.update_product_list)
            il_layout.addRow(f"{freq} Hz:", spin)
            self.insertion_loss_spins[freq] = spin
        
        il_group.setLayout(il_layout)
        layout.addWidget(il_group)
        
        # Physical Constraints
        physical_group = QGroupBox("Physical Constraints")
        physical_layout = QFormLayout()
        
        self.max_length_spin = QDoubleSpinBox()
        self.max_length_spin.setRange(0, 200)
        self.max_length_spin.setSuffix(" inches")
        self.max_length_spin.setSpecialValueText("No limit")
        self.max_length_spin.valueChanged.connect(self.update_product_list)
        physical_layout.addRow("Max Length:", self.max_length_spin)
        
        self.max_width_spin = QDoubleSpinBox()
        self.max_width_spin.setRange(0, 100)
        self.max_width_spin.setSuffix(" inches")
        self.max_width_spin.setSpecialValueText("No limit")
        self.max_width_spin.valueChanged.connect(self.update_product_list)
        physical_layout.addRow("Max Width:", self.max_width_spin)
        
        self.max_height_spin = QDoubleSpinBox()
        self.max_height_spin.setRange(0, 100)
        self.max_height_spin.setSuffix(" inches")
        self.max_height_spin.setSpecialValueText("No limit")
        self.max_height_spin.valueChanged.connect(self.update_product_list)
        physical_layout.addRow("Max Height:", self.max_height_spin)
        
        physical_group.setLayout(physical_layout)
        layout.addWidget(physical_group)
        
        # Flow Rate Requirements
        flow_group = QGroupBox("Flow Rate Requirements")
        flow_layout = QFormLayout()
        
        self.flow_rate_spin = QDoubleSpinBox()
        self.flow_rate_spin.setRange(0, 10000)
        self.flow_rate_spin.setSuffix(" CFM")
        self.flow_rate_spin.setSpecialValueText("Not specified")
        self.flow_rate_spin.valueChanged.connect(self.update_product_list)
        flow_layout.addRow("Flow Rate:", self.flow_rate_spin)
        
        flow_group.setLayout(flow_layout)
        layout.addWidget(flow_group)
        
        # Silencer Type
        type_group = QGroupBox("Silencer Type")
        type_layout = QFormLayout()
        
        self.silencer_type_combo = QComboBox()
        self.silencer_type_combo.addItems([
            "Any Type", "dissipative", "reactive", "hybrid",
            "rectangular", "elbow", "circular_packless",
        ])
        self.silencer_type_combo.currentTextChanged.connect(self.update_product_list)
        type_layout.addRow("Type:", self.silencer_type_combo)
        
        type_group.setLayout(type_layout)
        layout.addWidget(type_group)
        
        # Manufacturer Filter
        mfg_group = QGroupBox("Manufacturer")
        mfg_layout = QFormLayout()
        
        self.manufacturer_combo = QComboBox()
        self.manufacturer_combo.addItem("Any Manufacturer")
        self._load_manufacturer_list()
        self.manufacturer_combo.currentTextChanged.connect(self.update_product_list)
        mfg_layout.addRow("Manufacturer:", self.manufacturer_combo)
        
        mfg_group.setLayout(mfg_layout)
        layout.addWidget(mfg_group)
        
        # Cost Range
        cost_group = QGroupBox("Cost Range")
        cost_layout = QFormLayout()
        
        self.min_cost_spin = QDoubleSpinBox()
        self.min_cost_spin.setRange(0, 50000)
        self.min_cost_spin.setPrefix("$")
        self.min_cost_spin.setSpecialValueText("No minimum")
        self.min_cost_spin.valueChanged.connect(self.update_product_list)
        cost_layout.addRow("Min Cost:", self.min_cost_spin)
        
        self.max_cost_spin = QDoubleSpinBox()
        self.max_cost_spin.setRange(0, 50000)
        self.max_cost_spin.setPrefix("$")
        self.max_cost_spin.setSpecialValueText("No maximum")
        self.max_cost_spin.valueChanged.connect(self.update_product_list)
        cost_layout.addRow("Max Cost:", self.max_cost_spin)
        
        cost_group.setLayout(cost_layout)
        layout.addWidget(cost_group)
        
        # Availability
        avail_group = QGroupBox("Availability")
        avail_layout = QVBoxLayout()
        
        self.in_stock_cb = QCheckBox("In Stock")
        self.in_stock_cb.setChecked(False)
        self.in_stock_cb.toggled.connect(self.update_product_list)
        avail_layout.addWidget(self.in_stock_cb)
        
        self.lead_time_cb = QCheckBox("Lead Time")
        self.lead_time_cb.setChecked(False)
        self.lead_time_cb.toggled.connect(self.update_product_list)
        avail_layout.addWidget(self.lead_time_cb)
        
        avail_group.setLayout(avail_layout)
        layout.addWidget(avail_group)
        
        layout.addStretch()
        panel.setLayout(layout)
        return panel
    
    def create_results_panel(self):
        """Create the product results panel"""
        panel = QFrame()
        layout = QVBoxLayout()
        
        # Sort controls
        sort_layout = QHBoxLayout()
        sort_layout.addWidget(QLabel("Sort by:"))
        
        self.sort_combo = QComboBox()
        self.sort_combo.addItems([
            "Match Score (Best First)", "Cost (Low to High)", "Cost (High to Low)",
            "Insertion Loss (High to Low)", "Size (Small to Large)", "Manufacturer"
        ])
        self.sort_combo.currentTextChanged.connect(self.sort_results)
        sort_layout.addWidget(self.sort_combo)
        sort_layout.addStretch()
        
        layout.addLayout(sort_layout)
        
        # Results table
        self.results_table = QTableWidget()
        self.results_table.setColumnCount(8)
        self.results_table.setHorizontalHeaderLabels([
            "Manufacturer", "Model", "Type", "Dimensions\n(L×W×H)", 
            "Flow Range\n(CFM)", "Key Insertion Loss\n(dB @ 500Hz)", 
            "Cost", "Match\nScore"
        ])
        
        # Configure table
        header = self.results_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeToContents)  # Manufacturer
        header.setSectionResizeMode(1, QHeaderView.ResizeToContents)  # Model
        header.setSectionResizeMode(2, QHeaderView.ResizeToContents)  # Type
        header.setSectionResizeMode(3, QHeaderView.ResizeToContents)  # Dimensions
        header.setSectionResizeMode(4, QHeaderView.ResizeToContents)  # Flow Range
        header.setSectionResizeMode(5, QHeaderView.ResizeToContents)  # Insertion Loss
        header.setSectionResizeMode(6, QHeaderView.ResizeToContents)  # Cost
        header.setSectionResizeMode(7, QHeaderView.ResizeToContents)  # Match Score
        
        self.results_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.results_table.setSelectionMode(QTableWidget.SingleSelection)
        self.results_table.itemSelectionChanged.connect(self.on_product_selection_changed)
        self.results_table.itemDoubleClicked.connect(self.select_product)
        
        layout.addWidget(self.results_table)
        
        # Product details
        details_group = QGroupBox("Selected Product Details")
        details_layout = QVBoxLayout()
        
        self.details_text = QTextEdit()
        self.details_text.setMaximumHeight(150)
        self.details_text.setReadOnly(True)
        details_layout.addWidget(self.details_text)
        
        details_group.setLayout(details_layout)
        layout.addWidget(details_group)
        
        panel.setLayout(layout)
        return panel
    
    def load_initial_requirements(self):
        """Load initial requirements from noise and space constraints"""
        
        # Load noise requirements
        for freq in [63, 125, 250, 500, 1000, 2000, 4000, 8000]:
            if f'insertion_loss_{freq}' in self.noise_requirements:
                self.insertion_loss_spins[freq].setValue(
                    self.noise_requirements[f'insertion_loss_{freq}']
                )
        
        # Load space constraints
        if 'max_length' in self.space_constraints:
            self.max_length_spin.setValue(self.space_constraints['max_length'])
        if 'max_width' in self.space_constraints:
            self.max_width_spin.setValue(self.space_constraints['max_width'])
        if 'max_height' in self.space_constraints:
            self.max_height_spin.setValue(self.space_constraints['max_height'])
        
        # Load flow rate
        if 'flow_rate' in self.noise_requirements:
            self.flow_rate_spin.setValue(self.noise_requirements['flow_rate'])
    
    def get_filter_requirements(self) -> Dict[str, Any]:
        """Get current filter requirements from UI"""
        requirements = {}
        
        # Insertion loss requirements
        for freq, spin in self.insertion_loss_spins.items():
            if spin.value() > 0:
                requirements[f'insertion_loss_{freq}'] = spin.value()
        
        # Physical constraints
        if self.max_length_spin.value() > 0:
            requirements['max_length'] = self.max_length_spin.value()
        if self.max_width_spin.value() > 0:
            requirements['max_width'] = self.max_width_spin.value()
        if self.max_height_spin.value() > 0:
            requirements['max_height'] = self.max_height_spin.value()
        
        # Flow rate
        if self.flow_rate_spin.value() > 0:
            requirements['flow_rate'] = self.flow_rate_spin.value()
        
        # Silencer type
        if self.silencer_type_combo.currentText() != "Any Type":
            requirements['silencer_type'] = self.silencer_type_combo.currentText()
        
        # Manufacturer
        if self.manufacturer_combo.currentText() != "Any Manufacturer":
            requirements['manufacturer'] = self.manufacturer_combo.currentText()
        
        # Cost range
        if self.min_cost_spin.value() > 0:
            requirements['min_cost'] = self.min_cost_spin.value()
        if self.max_cost_spin.value() > 0:
            requirements['max_cost'] = self.max_cost_spin.value()
        
        # Availability
        availability = []
        if self.in_stock_cb.isChecked():
            availability.append('in_stock')
        if self.lead_time_cb.isChecked():
            availability.append('lead_time')
        if availability:
            requirements['availability'] = availability
        
        return requirements
    
    def update_product_list(self):
        """Update the product list based on current filters"""
        requirements = self.get_filter_requirements()
        
        try:
            self.products_data = self.filter_engine.get_ranked_products(requirements)
            self.populate_results_table()
            self.update_product_count()
            
        except Exception as e:
            QMessageBox.warning(self, "Filter Error", f"Error filtering products:\n{str(e)}")
    
    def populate_results_table(self):
        """Populate the results table with filtered products"""
        self.results_table.setRowCount(len(self.products_data))
        
        for row, item in enumerate(self.products_data):
            product = item['product']
            match_score = item['match_score']
            
            # Manufacturer
            self.results_table.setItem(row, 0, QTableWidgetItem(product.manufacturer or ""))
            
            # Model
            self.results_table.setItem(row, 1, QTableWidgetItem(product.model_number or ""))
            
            # Type
            type_text = (product.silencer_type or "").title()
            self.results_table.setItem(row, 2, QTableWidgetItem(type_text))
            
            # Dimensions
            dimensions = f"{product.length or 0:.0f}×{product.width or 0:.0f}×{product.height or 0:.0f}\""
            self.results_table.setItem(row, 3, QTableWidgetItem(dimensions))
            
            # Flow Range
            flow_min = product.flow_rate_min or 0
            flow_max = product.flow_rate_max or 0
            flow_range = f"{flow_min:.0f}-{flow_max:.0f}"
            self.results_table.setItem(row, 4, QTableWidgetItem(flow_range))
            
            # Key Insertion Loss (500 Hz)
            il_500 = product.insertion_loss_500 or 0
            il_text = f"{il_500:.1f}"
            self.results_table.setItem(row, 5, QTableWidgetItem(il_text))
            
            # Cost
            cost = product.cost_estimate or 0
            cost_text = f"${cost:,.0f}"
            self.results_table.setItem(row, 6, QTableWidgetItem(cost_text))
            
            # Match Score
            score_text = f"{match_score:.0f}%"
            score_item = QTableWidgetItem(score_text)
            
            # Color code match score
            if match_score >= 90:
                score_item.setBackground(Qt.green)
            elif match_score >= 75:
                score_item.setBackground(Qt.yellow)
            elif match_score >= 60:
                score_item.setBackground(Qt.GlobalColor.orange)
            else:
                score_item.setBackground(Qt.red)
            
            self.results_table.setItem(row, 7, score_item)
    
    def sort_results(self, sort_criteria: str):
        """Sort results based on selected criteria"""
        if not self.products_data:
            return
        
        if sort_criteria == "Match Score (Best First)":
            self.products_data.sort(key=lambda x: x['match_score'], reverse=True)
        elif sort_criteria == "Cost (Low to High)":
            self.products_data.sort(key=lambda x: x['product'].cost_estimate or 0)
        elif sort_criteria == "Cost (High to Low)":
            self.products_data.sort(key=lambda x: x['product'].cost_estimate or 0, reverse=True)
        elif sort_criteria == "Insertion Loss (High to Low)":
            self.products_data.sort(key=lambda x: x['product'].insertion_loss_500 or 0, reverse=True)
        elif sort_criteria == "Size (Small to Large)":
            self.products_data.sort(key=lambda x: (x['product'].length or 0) * 
                                   (x['product'].width or 0) * (x['product'].height or 0))
        elif sort_criteria == "Manufacturer":
            self.products_data.sort(key=lambda x: x['product'].manufacturer or "")
        
        self.populate_results_table()
    
    def update_product_count(self):
        """Update the product count label"""
        count = len(self.products_data)
        self.product_count_label.setText(f"{count} products found")
    
    def on_product_selection_changed(self):
        """Handle product selection change"""
        current_row = self.results_table.currentRow()
        
        if current_row >= 0 and current_row < len(self.products_data):
            product = self.products_data[current_row]['product']
            match_score = self.products_data[current_row]['match_score']
            self.selected_product = product
            self.select_btn.setEnabled(True)
            self.show_product_details(product, match_score)
        else:
            self.selected_product = None
            self.select_btn.setEnabled(False)
            self.details_text.clear()
    
    def show_product_details(self, product: SilencerProduct, match_score: float):
        """Show detailed information about selected product"""
        details = []
        details.append(f"<h3>{product.manufacturer} {product.model_number}</h3>")
        details.append(f"<b>Type:</b> {(product.silencer_type or '').title()}")
        details.append(f"<b>Match Score:</b> {match_score:.1f}%")
        details.append("")
        
        details.append("<b>Physical Specifications:</b>")
        details.append(f"• Dimensions: {product.length or 0:.0f}\" × {product.width or 0:.0f}\" × {product.height or 0:.0f}\"")
        details.append(f"• Weight: {product.weight or 0:.1f} lbs")
        details.append("")
        
        details.append("<b>Performance Specifications:</b>")
        details.append(f"• Flow Rate: {product.flow_rate_min or 0:.0f} - {product.flow_rate_max or 0:.0f} CFM")
        details.append(f"• Max Velocity: {product.velocity_max or 0:.0f} FPM")
        details.append("")
        
        details.append("<b>Insertion Loss by Frequency:</b>")
        frequencies = [63, 125, 250, 500, 1000, 2000, 4000, 8000]
        for freq in frequencies:
            loss = getattr(product, f'insertion_loss_{freq}', 0) or 0
            details.append(f"• {freq} Hz: {loss:.1f} dB")
        details.append("")
        
        details.append("<b>Cost & Availability:</b>")
        details.append(f"• Estimated Cost: ${product.cost_estimate or 0:,.0f}")
        details.append(f"• Availability: {(product.availability or 'Unknown').title()}")
        
        self.details_text.setHtml("<br>".join(details))
    
    def clear_filters(self):
        """Clear all filters"""
        # Clear insertion loss requirements
        for spin in self.insertion_loss_spins.values():
            spin.setValue(0)
        
        # Clear physical constraints
        self.max_length_spin.setValue(0)
        self.max_width_spin.setValue(0)
        self.max_height_spin.setValue(0)
        
        # Clear flow rate
        self.flow_rate_spin.setValue(0)
        
        # Reset combo boxes
        self.silencer_type_combo.setCurrentIndex(0)
        self.manufacturer_combo.setCurrentIndex(0)
        
        # Clear cost range
        self.min_cost_spin.setValue(0)
        self.max_cost_spin.setValue(0)
        
        # Reset availability checkboxes (unchecked = no availability filter)
        self.in_stock_cb.setChecked(False)
        self.lead_time_cb.setChecked(False)
        
        # Update results
        self.update_product_list()
    
    def select_product(self):
        """Select the current product"""
        if self.selected_product:
            self.product_selected.emit(self.selected_product)
            self.accept()
        else:
            QMessageBox.warning(self, "No Selection", "Please select a product first.")
    
    def get_selected_product(self) -> Optional[SilencerProduct]:
        """Get the selected product"""
        return self.selected_product
    
    def closeEvent(self, event):
        """Handle dialog close event"""
        if hasattr(self.filter_engine, 'close'):
            self.filter_engine.close()
        event.accept()


def show_silencer_filter_dialog(noise_requirements=None, space_constraints=None,
                               nc_compliance_data=None, parent=None):
    """Show silencer filter dialog and return (accepted, product)."""
    dialog = SilencerFilterDialog(noise_requirements, space_constraints,
                                  nc_compliance_data, parent)
    return dialog.exec(), dialog.get_selected_product()