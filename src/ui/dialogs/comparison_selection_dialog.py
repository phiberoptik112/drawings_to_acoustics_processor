"""
Dialog for selecting two drawing sets for comparison
"""

from typing import List, Tuple
from PySide6.QtWidgets import (
	QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
	QComboBox, QGroupBox, QTextEdit, QMessageBox
)
from PySide6.QtCore import Qt

from models.drawing_sets import DrawingSet


class ComparisonSelectionDialog(QDialog):
	"""Dialog for selecting base and compare drawing sets"""
	
	def __init__(self, parent, drawing_sets: List[DrawingSet]):
		super().__init__(parent)
		self.drawing_sets = drawing_sets
		self.base_set_id = None
		self.compare_set_id = None
		self.init_ui()
	
	def init_ui(self):
		self.setWindowTitle("Select Drawing Sets for Comparison")
		self.setGeometry(300, 300, 500, 400)
		self.setModal(True)
		
		layout = QVBoxLayout()
		
		instructions = QLabel(
			"Select two drawing sets to compare. Changes will be detected between "
			"the base set (reference) and compare set (new design)."
		)
		instructions.setWordWrap(True)
		layout.addWidget(instructions)
		
		selection_group = QGroupBox("Drawing Set Selection")
		selection_layout = QVBoxLayout()
		
		base_layout = QHBoxLayout()
		base_layout.addWidget(QLabel("Base Set (Reference):"))
		self.base_combo = QComboBox()
		self.populate_combo(self.base_combo)
		self.base_combo.currentTextChanged.connect(self.on_selection_changed)
		base_layout.addWidget(self.base_combo)
		selection_layout.addLayout(base_layout)
		
		compare_layout = QHBoxLayout()
		compare_layout.addWidget(QLabel("Compare Set (New):"))
		self.compare_combo = QComboBox()
		self.populate_combo(self.compare_combo)
		self.compare_combo.currentTextChanged.connect(self.on_selection_changed)
		compare_layout.addWidget(self.compare_combo)
		selection_layout.addLayout(compare_layout)
		
		selection_group.setLayout(selection_layout)
		layout.addWidget(selection_group)
		
		preview_group = QGroupBox("Comparison Preview")
		preview_layout = QVBoxLayout()
		self.preview_text = QTextEdit()
		self.preview_text.setMaximumHeight(150)
		self.preview_text.setReadOnly(True)
		preview_layout.addWidget(self.preview_text)
		preview_group.setLayout(preview_layout)
		layout.addWidget(preview_group)
		
		button_layout = QHBoxLayout()
		self.compare_button = QPushButton("Start Comparison")
		self.compare_button.clicked.connect(self.accept)
		self.compare_button.setDefault(True)
		self.compare_button.setEnabled(False)
		cancel_button = QPushButton("Cancel")
		cancel_button.clicked.connect(self.reject)
		button_layout.addStretch()
		button_layout.addWidget(self.compare_button)
		button_layout.addWidget(cancel_button)
		layout.addLayout(button_layout)
		
		self.setLayout(layout)
		self.update_preview()
	
	def populate_combo(self, combo: QComboBox):
		combo.clear()
		combo.addItem("-- Select Drawing Set --", None)
		for drawing_set in self.drawing_sets:
			drawing_count = len(drawing_set.drawings) if drawing_set.drawings else 0
			active_indicator = " (Active)" if drawing_set.is_active else ""
			item_text = f"{drawing_set.name} ({drawing_set.phase_type}) - {drawing_count} drawings{active_indicator}"
			combo.addItem(item_text, drawing_set.id)
	
	def on_selection_changed(self):
		self.base_set_id = self.base_combo.currentData()
		self.compare_set_id = self.compare_combo.currentData()
		can_compare = (
			self.base_set_id is not None and
			self.compare_set_id is not None and
			self.base_set_id != self.compare_set_id
		)
		self.compare_button.setEnabled(can_compare)
		self.update_preview()
	
	def update_preview(self):
		if not self.base_set_id or not self.compare_set_id:
			self.preview_text.setText("Select both drawing sets to see comparison preview.")
			return
		if self.base_set_id == self.compare_set_id:
			self.preview_text.setText("⚠️ Please select different drawing sets for comparison.")
			return
		base_set = next((ds for ds in self.drawing_sets if ds.id == self.base_set_id), None)
		compare_set = next((ds for ds in self.drawing_sets if ds.id == self.compare_set_id), None)
		if not base_set or not compare_set:
			self.preview_text.setText("Error: Could not find selected drawing sets.")
			return
		preview_text = f"📊 Comparison Preview:\n\n"
		preview_text += f"Base Set: {base_set.name} ({base_set.phase_type})\n"
		preview_text += f"  • {len(base_set.drawings) if base_set.drawings else 0} drawings\n"
		if getattr(base_set, 'created_date', None):
			preview_text += f"  • Created: {base_set.created_date.strftime('%Y-%m-%d')}\n\n"
		else:
			preview_text += "\n"
		preview_text += f"Compare Set: {compare_set.name} ({compare_set.phase_type})\n"
		preview_text += f"  • {len(compare_set.drawings) if compare_set.drawings else 0} drawings\n"
		if getattr(compare_set, 'created_date', None):
			preview_text += f"  • Created: {compare_set.created_date.strftime('%Y-%m-%d')}\n\n"
		else:
			preview_text += "\n"
		preview_text += "The comparison will analyze:\n"
		preview_text += "  • Room layout changes (added, removed, modified spaces)\n"
		preview_text += "  • HVAC component changes (equipment relocation, additions)\n"
		preview_text += "  • HVAC path routing changes\n"
		preview_text += "  • Acoustic impact analysis\n"
		self.preview_text.setText(preview_text)
	
	def get_selected_sets(self) -> Tuple[int, int]:
		return self.base_set_id, self.compare_set_id
	
	def accept(self):
		if not self.base_set_id or not self.compare_set_id:
			QMessageBox.warning(self, "Selection Required", "Please select both base and compare drawing sets.")
			return
		if self.base_set_id == self.compare_set_id:
			QMessageBox.warning(self, "Different Sets Required", "Please select different drawing sets for comparison.")
			return
		super().accept()