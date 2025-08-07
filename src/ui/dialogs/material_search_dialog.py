"""
Material Search Dialog - Advanced material search with frequency analysis and treatment recommendations
"""

from PySide6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QTabWidget,
                             QWidget, QPushButton, QLabel, QGroupBox, 
                             QComboBox, QSpinBox, QCheckBox, QTextEdit,
                             QMessageBox, QProgressDialog, QSplitter)
from PySide6.QtCore import Qt, Signal, QThread
from PySide6.QtGui import QFont

try:
    from ui.widgets.material_graph_overlay import MaterialGraphOverlay
    from calculations.treatment_analyzer import TreatmentAnalyzer
    from data.material_search import MaterialSearchEngine
except ImportError:
    import sys
    import os
    current_dir = os.path.dirname(__file__)
    src_dir = os.path.dirname(os.path.dirname(os.path.dirname(current_dir)))
    sys.path.insert(0, src_dir)
    from ui.widgets.material_graph_overlay import MaterialGraphOverlay
    from calculations.treatment_analyzer import TreatmentAnalyzer
    from data.material_search import MaterialSearchEngine


class TreatmentAnalysisThread(QThread):
    """Background thread for treatment analysis"""
    
    analysis_complete = Signal(dict)
    progress_update = Signal(str)
    
    def __init__(self, space_data, surface_types, available_areas):
        super().__init__()
        self.space_data = space_data
        self.surface_types = surface_types
        self.available_areas = available_areas
        self.analyzer = TreatmentAnalyzer()

        
    def run(self):
        try:
            self.progress_update.emit("Analyzing treatment gaps...")
            
            # Analyze gaps
            gap_analysis = self.analyzer.analyze_treatment_gaps(self.space_data)
            
            self.progress_update.emit("Finding optimal materials...")
            
            # Get material suggestions
            suggestions = self.analyzer.suggest_optimal_materials(
                self.space_data, self.surface_types, self.available_areas
            )
            
            self.progress_update.emit("Calculating improvements...")
            
            # Combine results
            results = {
                'gap_analysis': gap_analysis,
                'material_suggestions': suggestions,
                'status': 'success'
            }
            
            self.analysis_complete.emit(results)
            
        except Exception as e:
            self.analysis_complete.emit({
                'error': str(e),
                'status': 'error'
            })


class MaterialSearchDialog(QDialog):
    """Advanced material search dialog with treatment analysis"""
    
    material_applied = Signal(dict, str)  # material, surface_type
    
    def __init__(self, parent=None, space_data=None):
        super().__init__(parent)
        self.space_data = space_data or {}
        self.selected_materials = {}
        self.analysis_results = {}
        
        self.init_ui()
        self.load_space_data()
        
    def init_ui(self):
        """Initialize user interface"""
        self.setWindowTitle("Material Search & Treatment Analysis")
        self.setModal(True)
        self.resize(1000, 700)
        
        layout = QVBoxLayout()
        
        # Header with space info
        header = self.create_header()
        layout.addWidget(header)
        
        # Main tabs
        tabs = QTabWidget()
        
        # Frequency Analysis tab
        freq_tab = self.create_frequency_analysis_tab()
        tabs.addTab(freq_tab, "Frequency Analysis")
        
        # Treatment Recommendations tab
        treatment_tab = self.create_treatment_tab()
        tabs.addTab(treatment_tab, "Treatment Analysis")
        
        # Material Comparison tab
        comparison_tab = self.create_comparison_tab()
        tabs.addTab(comparison_tab, "Material Comparison")
        
        layout.addWidget(tabs)
        
        # Action buttons
        button_layout = QHBoxLayout()
        
        self.analyze_btn = QPushButton("Analyze Treatment Needs")
        self.analyze_btn.clicked.connect(self.run_treatment_analysis)
        button_layout.addWidget(self.analyze_btn)
        
        button_layout.addStretch()
        
        self.apply_btn = QPushButton("Apply Selected Materials")
        self.apply_btn.setEnabled(False)
        self.apply_btn.clicked.connect(self.apply_materials)
        button_layout.addWidget(self.apply_btn)
        
        self.close_btn = QPushButton("Close")
        self.close_btn.clicked.connect(self.accept)
        button_layout.addWidget(self.close_btn)
        
        layout.addLayout(button_layout)
        self.setLayout(layout)
        
    def create_header(self):
        """Create header with space information"""
        header = QGroupBox("Current Space")
        layout = QHBoxLayout()
        
        # Space info
        space_name = self.space_data.get('name', 'Unnamed Space')
        volume = self.space_data.get('volume', 0)
        target_rt60 = self.space_data.get('target_rt60', 0.6)
        
        info_text = f"<b>{space_name}</b><br>"
        info_text += f"Volume: {volume:,.0f} ft³<br>"
        info_text += f"Target RT60: {target_rt60:.1f}s"
        
        info_label = QLabel(info_text)
        layout.addWidget(info_label)
        
        # Current RT60 status
        rt60_by_freq = self.space_data.get('rt60_by_frequency', {})
        if rt60_by_freq:
            avg_rt60 = sum(rt60_by_freq.values()) / len(rt60_by_freq)
            status_text = f"<b>Current Performance:</b><br>"
            status_text += f"Average RT60: {avg_rt60:.2f}s<br>"
            
            # Check if needs treatment
            needs_treatment = any(abs(rt60 - target_rt60) > 0.1 for rt60 in rt60_by_freq.values())
            if needs_treatment:
                status_text += '<span style="color: orange;">⚠ Treatment Needed</span>'
            else:
                status_text += '<span style="color: green;">✓ Within Target</span>'
                
            status_label = QLabel(status_text)
            layout.addWidget(status_label)
        
        layout.addStretch()
        header.setLayout(layout)
        return header
        
    def create_frequency_analysis_tab(self):
        """Create frequency analysis tab"""
        widget = QWidget()
        layout = QVBoxLayout()
        
        # Instructions
        instructions = QLabel("Click on frequency points in the graph to search for materials optimized at that frequency.")
        instructions.setWordWrap(True)
        layout.addWidget(instructions)
        
        # Material graph overlay
        self.material_graph = MaterialGraphOverlay()
        self.material_graph.material_selected.connect(self.on_material_selected)
        layout.addWidget(self.material_graph)
        
        widget.setLayout(layout)
        return widget
        
    def create_treatment_tab(self):
        """Create treatment analysis tab"""
        widget = QWidget()
        layout = QVBoxLayout()
        
        # Control panel
        control_group = QGroupBox("Treatment Analysis Options")
        control_layout = QHBoxLayout()
        
        control_layout.addWidget(QLabel("Surface Types:"))
        
        self.ceiling_cb = QCheckBox("Ceiling")
        self.ceiling_cb.setChecked(True)
        control_layout.addWidget(self.ceiling_cb)
        
        self.wall_cb = QCheckBox("Walls")
        self.wall_cb.setChecked(True)
        control_layout.addWidget(self.wall_cb)
        
        self.floor_cb = QCheckBox("Floor")
        self.floor_cb.setChecked(False)  # Floor treatments less common
        control_layout.addWidget(self.floor_cb)
        
        control_layout.addStretch()
        control_group.setLayout(control_layout)
        layout.addWidget(control_group)
        
        # Results area
        self.treatment_results = QTextEdit()
        self.treatment_results.setReadOnly(True)
        self.treatment_results.setHtml("<i>Click 'Analyze Treatment Needs' to get recommendations</i>")
        layout.addWidget(self.treatment_results)
        
        widget.setLayout(layout)
        return widget
        
    def create_comparison_tab(self):
        """Create material comparison tab"""
        widget = QWidget()
        layout = QVBoxLayout()
        
        # Selected materials area
        selected_group = QGroupBox("Selected Materials")
        selected_layout = QVBoxLayout()
        
        self.selected_materials_display = QTextEdit()
        self.selected_materials_display.setReadOnly(True)
        self.selected_materials_display.setMaximumHeight(150)
        self.selected_materials_display.setHtml("<i>No materials selected</i>")
        selected_layout.addWidget(self.selected_materials_display)
        
        selected_group.setLayout(selected_layout)
        layout.addWidget(selected_group)
        
        # Comparison results
        comparison_group = QGroupBox("Performance Comparison")
        comparison_layout = QVBoxLayout()
        
        self.comparison_results = QTextEdit()
        self.comparison_results.setReadOnly(True)
        self.comparison_results.setHtml("<i>Select materials to compare their performance</i>")
        comparison_layout.addWidget(self.comparison_results) 
        
        comparison_group.setLayout(comparison_layout)
        layout.addWidget(comparison_group)
        
        widget.setLayout(layout)
        return widget
        
    def load_space_data(self):
        """Load space data into the interface"""
        if self.space_data:
            self.material_graph.set_space_data(self.space_data)
            
    def on_material_selected(self, material):
        """Handle material selection from graph overlay"""
        # Show material selection dialog
        surface_type = self.prompt_surface_type()
        if surface_type:
            self.selected_materials[surface_type] = material
            self.update_selected_materials_display()
            self.update_comparison()
            self.apply_btn.setEnabled(len(self.selected_materials) > 0)
            
    def prompt_surface_type(self):
        """Prompt user to select surface type for material"""
        from PySide6.QtWidgets import QInputDialog
        
        surface_types = ["Ceiling", "Wall", "Floor"]
        surface_type, ok = QInputDialog.getItem(
            self, "Select Surface Type", 
            "Which surface will this material be applied to?",
            surface_types, 0, False
        )
        
        if ok:
            return surface_type.lower()
        return None
        
    def run_treatment_analysis(self):
        """Run comprehensive treatment analysis"""
        # Get selected surface types
        surface_types = []
        if self.ceiling_cb.isChecked():
            surface_types.append('ceiling')
        if self.wall_cb.isChecked():
            surface_types.append('wall')
        if self.floor_cb.isChecked():
            surface_types.append('floor')
            
        if not surface_types:
            QMessageBox.warning(self, "No Surfaces Selected", 
                              "Please select at least one surface type for analysis.")
            return
            
        # Estimate available areas
        floor_area = self.space_data.get('floor_area', 500)
        available_areas = {
            'ceiling': floor_area,
            'wall': self.space_data.get('wall_area', floor_area * 2),
            'floor': floor_area
        }
        
        # Show progress dialog
        self.progress_dialog = QProgressDialog("Analyzing treatment options...", "Cancel", 0, 0, self)
        self.progress_dialog.setWindowModality(Qt.WindowModal)
        self.progress_dialog.show()
        
        # Start analysis thread
        self.analysis_thread = TreatmentAnalysisThread(
            self.space_data, surface_types, available_areas
        )
        self.analysis_thread.analysis_complete.connect(self.on_analysis_complete)
        self.analysis_thread.progress_update.connect(self.progress_dialog.setLabelText)
        self.analysis_thread.start()
        
    def on_analysis_complete(self, results):
        """Handle completed treatment analysis"""
        self.progress_dialog.close()
        
        if results.get('status') == 'error':
            QMessageBox.critical(self, "Analysis Error", 
                               f"Error during analysis: {results.get('error', 'Unknown error')}")
            return
            
        self.analysis_results = results
        self.display_treatment_results(results)
        
    def display_treatment_results(self, results):
        """Display treatment analysis results"""
        gap_analysis = results.get('gap_analysis', {})
        suggestions = results.get('material_suggestions', {})
        
        html = "<h3>Treatment Analysis Results</h3>"
        
        # Overall assessment
        overall = gap_analysis.get('overall_assessment', {})
        if overall:
            urgency = overall.get('treatment_urgency', 'unknown').title()
            avg_severity = overall.get('average_severity', 0)
            problem_count = overall.get('problem_frequency_count', 0)
            
            html += f"<h4>Overall Assessment</h4>"
            html += f"<p><b>Treatment Urgency:</b> {urgency}<br>"
            html += f"<b>Average Severity:</b> {avg_severity:.1f}/100<br>"
            html += f"<b>Problem Frequencies:</b> {problem_count}</p>"
        
        # Problem frequencies
        problem_frequencies = gap_analysis.get('problem_frequencies', [])
        if problem_frequencies:
            html += f"<h4>Problem Frequencies</h4>"
            html += "<ul>"
            for freq in problem_frequencies:
                gap_info = gap_analysis['frequency_gaps'].get(freq, {})
                gap = gap_info.get('gap', 0)
                treatment_type = gap_info.get('treatment_type', 'unknown')
                html += f"<li><b>{freq}Hz:</b> {gap:+.2f}s ({treatment_type})</li>"
            html += "</ul>"
        
        # Surface recommendations
        surface_recs = suggestions.get('surface_recommendations', {})
        if surface_recs:
            html += "<h4>Recommended Materials</h4>"
            
            for surface_type, rec in surface_recs.items():
                best_material = rec.get('best_overall_material', {}).get('material', {})
                if best_material:
                    html += f"<h5>{surface_type.title()}</h5>"
                    html += f"<p><b>Material:</b> {best_material.get('name', 'Unknown')}<br>"
                    
                    nrc = best_material.get('nrc', 0)
                    html += f"<b>NRC:</b> {nrc:.2f}<br>"
                    
                    expected_impact = rec.get('expected_impact', {})
                    reduction = expected_impact.get('overall_rt60_reduction', 0)
                    html += f"<b>Expected RT60 Reduction:</b> {reduction:.2f}s</p>"
        
        # Implementation priority
        priorities = suggestions.get('implementation_priority', [])
        if priorities:
            html += "<h4>Implementation Priority</h4>"
            html += "<ol>"
            for priority in priorities[:3]:  # Top 3
                surface = priority['surface_type']
                material = priority['material']['name']
                reduction = priority['expected_reduction']
                html += f"<li><b>{surface.title()}:</b> {material} (−{reduction:.2f}s RT60)</li>"
            html += "</ol>"
        
        self.treatment_results.setHtml(html)
        
    def update_selected_materials_display(self):
        """Update the selected materials display"""
        if not self.selected_materials:
            self.selected_materials_display.setHtml("<i>No materials selected</i>")
            return
            
        html = "<h4>Selected Materials</h4><ul>"
        for surface_type, material in self.selected_materials.items():
            name = material.get('name', 'Unknown')
            nrc = material.get('nrc', 0)
            html += f"<li><b>{surface_type.title()}:</b> {name} (NRC: {nrc:.2f})</li>"
        html += "</ul>"
        
        self.selected_materials_display.setHtml(html)
        
    def update_comparison(self):
        """Update material comparison"""
        if len(self.selected_materials) < 2:
            self.comparison_results.setHtml("<i>Select at least 2 materials to compare</i>")
            return
            
        html = "<h4>Material Performance Comparison</h4>"
        html += "<table border='1' cellpadding='5'>"
        html += "<tr><th>Surface</th><th>Material</th><th>NRC</th>"
        
        # Frequency headers
        frequencies = [125, 250, 500, 1000, 2000, 4000]
        for freq in frequencies:
            html += f"<th>{freq}Hz</th>"
        html += "</tr>"
        
        # Material rows
        for surface_type, material in self.selected_materials.items():
            html += f"<tr><td><b>{surface_type.title()}</b></td>"
            html += f"<td>{material.get('name', 'Unknown')}</td>"
            html += f"<td>{material.get('nrc', 0):.2f}</td>"
            
            # Frequency coefficients
            coefficients = material.get('coefficients', {})
            for freq in frequencies:
                coeff = coefficients.get(str(freq), 0)
                html += f"<td>{coeff:.2f}</td>"
            html += "</tr>"
        
        html += "</table>"
        
        # Add performance summary
        if self.space_data and len(self.selected_materials) > 0:
            html += "<h5>Estimated Performance Impact</h5>"
            html += "<p><i>Run treatment analysis to see detailed performance predictions</i></p>"
        
        self.comparison_results.setHtml(html)
        
    def apply_materials(self):
        """Apply selected materials"""
        if not self.selected_materials:
            return
            
        reply = QMessageBox.question(
            self, "Apply Materials",
            f"Apply {len(self.selected_materials)} selected materials to the space?",
            QMessageBox.Yes | QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            for surface_type, material in self.selected_materials.items():
                self.material_applied.emit(material, surface_type)
            
            self.accept()


# Convenience function to show dialog
def show_material_search_dialog(parent=None, space_data=None):
    """Show material search dialog"""
    dialog = MaterialSearchDialog(parent, space_data)
    return dialog.exec()