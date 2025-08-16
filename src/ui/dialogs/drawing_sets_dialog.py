"""
Drawing Sets Management Dialog
Handles creation, editing, and assignment of drawings to sets
"""

from PySide6.QtWidgets import (
	QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
	QListWidget, QListWidgetItem, QLineEdit, QComboBox,
	QTextEdit, QGroupBox, QSplitter, QMessageBox, QCheckBox,
	QTabWidget, QWidget, QTableWidget, QTableWidgetItem,
	QHeaderView, QAbstractItemView
)
from PySide6.QtCore import Qt

from models import get_session, Drawing
from models.drawing_sets import DrawingSet
from sqlalchemy.orm import selectinload


class DrawingSetsDialog(QDialog):
	"""Dialog for managing drawing sets and assignments"""
	
	def __init__(self, parent, project_id: int, mode: str = 'manage'):
		super().__init__(parent)
		self.project_id = project_id
		self.mode = mode  # 'create', 'edit', 'manage'
		self.project = None
		self.drawing_sets = []
		self.drawings = []
		
		self.load_data()
		self.init_ui()
		self.refresh_data()
	
	def load_data(self):
		"""Load project data"""
		session = get_session()
		try:
			# Eager-load drawings to avoid detached lazy-loads when session closes
			self.drawing_sets = (
				session.query(DrawingSet)
				.options(selectinload(DrawingSet.drawings))
				.filter(DrawingSet.project_id == self.project_id)
				.all()
			)
			self.drawings = session.query(Drawing).filter(Drawing.project_id == self.project_id).all()
		finally:
			session.close()
	
	def init_ui(self):
		"""Initialize the user interface"""
		self.setWindowTitle("Drawing Sets Management")
		self.setGeometry(200, 200, 900, 700)
		self.setModal(True)
		
		layout = QVBoxLayout()
		
		if self.mode == 'create':
			self.create_creation_ui(layout)
		else:
			self.create_management_ui(layout)
		
		# Dialog buttons
		button_layout = QHBoxLayout()
		
		self.ok_button = QPushButton("OK")
		self.ok_button.clicked.connect(self.accept)
		self.ok_button.setDefault(True)
		
		cancel_button = QPushButton("Cancel")
		cancel_button.clicked.connect(self.reject)
		
		button_layout.addStretch()
		button_layout.addWidget(self.ok_button)
		button_layout.addWidget(cancel_button)
		
		layout.addLayout(button_layout)
		self.setLayout(layout)
	
	def create_creation_ui(self, layout):
		"""Create UI for creating a new drawing set"""
		# Set properties
		properties_group = QGroupBox("New Drawing Set Properties")
		properties_layout = QVBoxLayout()
		
		# Name
		name_layout = QHBoxLayout()
		name_layout.addWidget(QLabel("Name:"))
		self.name_edit = QLineEdit()
		name_layout.addWidget(self.name_edit)
		properties_layout.addLayout(name_layout)
		
		# Phase type
		phase_layout = QHBoxLayout()
		phase_layout.addWidget(QLabel("Phase:"))
		self.phase_combo = QComboBox()
		self.phase_combo.addItems(['DD', 'SD', 'CD', 'Final', 'Legacy', 'Other'])
		phase_layout.addWidget(self.phase_combo)
		properties_layout.addLayout(phase_layout)
		
		# Description
		properties_layout.addWidget(QLabel("Description:"))
		self.description_edit = QTextEdit()
		self.description_edit.setMaximumHeight(100)
		properties_layout.addWidget(self.description_edit)
		
		# Set as active
		self.active_checkbox = QCheckBox("Set as active drawing set")
		properties_layout.addWidget(self.active_checkbox)
		
		properties_group.setLayout(properties_layout)
		layout.addWidget(properties_group)
	
	def create_management_ui(self, layout):
		"""Create UI for managing existing drawing sets"""
		# Create tabs
		tabs = QTabWidget()
		
		# Drawing Sets tab
		sets_tab = self.create_sets_tab()
		tabs.addTab(sets_tab, "Drawing Sets")
		
		# Assignment tab
		assignment_tab = self.create_assignment_tab()
		tabs.addTab(assignment_tab, "Drawing Assignment")
		
		layout.addWidget(tabs)
	
	def create_sets_tab(self):
		"""Create the drawing sets management tab"""
		widget = QWidget()
		layout = QVBoxLayout()
		
		# Drawing sets table
		self.sets_table = QTableWidget()
		self.sets_table.setColumnCount(5)
		self.sets_table.setHorizontalHeaderLabels(['Name', 'Phase', 'Drawings', 'Active', 'Created'])
		self.sets_table.setSelectionBehavior(QAbstractItemView.SelectRows)
		
		# Configure table
		header = self.sets_table.horizontalHeader()
		header.setSectionResizeMode(0, QHeaderView.Stretch)
		header.setSectionResizeMode(1, QHeaderView.ResizeToContents)
		header.setSectionResizeMode(2, QHeaderView.ResizeToContents)
		header.setSectionResizeMode(3, QHeaderView.ResizeToContents)
		header.setSectionResizeMode(4, QHeaderView.ResizeToContents)
		
		layout.addWidget(self.sets_table)
		
		# Sets buttons
		sets_button_layout = QHBoxLayout()
		
		new_set_btn = QPushButton("New Set")
		new_set_btn.clicked.connect(self.create_new_set)
		
		edit_set_btn = QPushButton("Edit Set")
		edit_set_btn.clicked.connect(self.edit_selected_set)
		
		delete_set_btn = QPushButton("Delete Set")
		delete_set_btn.clicked.connect(self.delete_selected_set)
		
		set_active_btn = QPushButton("Set Active")
		set_active_btn.clicked.connect(self.set_selected_active)
		
		sets_button_layout.addWidget(new_set_btn)
		sets_button_layout.addWidget(edit_set_btn)
		sets_button_layout.addWidget(delete_set_btn)
		sets_button_layout.addWidget(set_active_btn)
		sets_button_layout.addStretch()
		
		layout.addLayout(sets_button_layout)
		widget.setLayout(layout)
		return widget
	
	def create_assignment_tab(self):
		"""Create the drawing assignment tab with drag-and-drop"""
		widget = QWidget()
		layout = QVBoxLayout()
		
		# Splitter for drawing sets and drawings
		splitter = QSplitter(Qt.Horizontal)
		
		# Left side: Drawing sets and drawings under them (read-only view)
		sets_widget = QWidget()
		sets_layout = QVBoxLayout()
		sets_layout.addWidget(QLabel("Drawing Sets:"))
		
		self.assignment_sets_list = QListWidget()
		sets_layout.addWidget(self.assignment_sets_list)
		
		sets_widget.setLayout(sets_layout)
		splitter.addWidget(sets_widget)
		
		# Right side: All drawings with their current set
		drawings_widget = QWidget()
		drawings_layout = QVBoxLayout()
		drawings_layout.addWidget(QLabel("All Drawings:"))
		
		self.assignment_drawings_list = QListWidget()
		drawings_layout.addWidget(self.assignment_drawings_list)
		
		drawings_widget.setLayout(drawings_layout)
		splitter.addWidget(drawings_widget)
		
		layout.addWidget(splitter)
		widget.setLayout(layout)
		return widget
	
	def refresh_data(self):
		"""Refresh all data displays"""
		self.load_data()
		if hasattr(self, 'sets_table'):
			self.refresh_sets_table()
		if hasattr(self, 'assignment_sets_list'):
			self.refresh_assignment_lists()
	
	def refresh_sets_table(self):
		"""Refresh the drawing sets table"""
		self.sets_table.setRowCount(len(self.drawing_sets))
		for row, drawing_set in enumerate(self.drawing_sets):
			# Name
			name_item = QTableWidgetItem(drawing_set.name)
			name_item.setData(Qt.UserRole, drawing_set.id)
			self.sets_table.setItem(row, 0, name_item)
			# Phase
			self.sets_table.setItem(row, 1, QTableWidgetItem(drawing_set.phase_type))
			# Drawing count
			drawing_count = len(drawing_set.drawings) if drawing_set.drawings else 0
			self.sets_table.setItem(row, 2, QTableWidgetItem(str(drawing_count)))
			# Active
			self.sets_table.setItem(row, 3, QTableWidgetItem("Yes" if drawing_set.is_active else "No"))
			# Created
			self.sets_table.setItem(row, 4, QTableWidgetItem(drawing_set.created_date.strftime("%Y-%m-%d") if drawing_set.created_date else ""))
	
	def refresh_assignment_lists(self):
		"""Refresh the assignment lists"""
		self.assignment_sets_list.clear()
		self.assignment_drawings_list.clear()
		
		# Add drawing sets with their drawings
		for drawing_set in self.drawing_sets:
			set_item = QListWidgetItem(f"📁 {drawing_set.name} ({drawing_set.phase_type})")
			set_item.setData(Qt.UserRole, {'type': 'set', 'id': drawing_set.id})
			self.assignment_sets_list.addItem(set_item)
			if drawing_set.drawings:
				for drawing in drawing_set.drawings:
					drawing_item = QListWidgetItem(f"  📄 {drawing.name}")
					drawing_item.setData(Qt.UserRole, {'type': 'drawing', 'id': drawing.id, 'set_id': drawing_set.id})
					self.assignment_sets_list.addItem(drawing_item)
		
		# Add all drawings with their current set label
		for drawing in self.drawings:
			set_name = "Unassigned"
			if drawing.drawing_set_id:
				parent_set = next((ds for ds in self.drawing_sets if ds.id == drawing.drawing_set_id), None)
				if parent_set:
					set_name = f"{parent_set.name} ({parent_set.phase_type})"
			drawing_item = QListWidgetItem(f"📄 {drawing.name} - {set_name}")
			drawing_item.setData(Qt.UserRole, {'type': 'drawing', 'id': drawing.id, 'set_id': drawing.drawing_set_id})
			self.assignment_drawings_list.addItem(drawing_item)
	
	def create_new_set(self):
		"""Create a new drawing set (simple prompt)"""
		from PySide6.QtWidgets import QInputDialog
		name, ok = QInputDialog.getText(self, "New Drawing Set", "Enter set name:")
		if not ok or not name.strip():
			return
		phase, ok = QInputDialog.getItem(self, "Drawing Set Phase", "Select phase:", ['DD', 'SD', 'CD', 'Final', 'Legacy', 'Other'], 0, False)
		if not ok:
			return
		session = get_session()
		try:
			existing_active = session.query(DrawingSet).filter(DrawingSet.project_id == self.project_id, DrawingSet.is_active == True).first()
			new_set = DrawingSet(project_id=self.project_id, name=name.strip(), phase_type=phase, is_active=existing_active is None)
			session.add(new_set)
			session.commit()
			QMessageBox.information(self, "Success", f"Drawing set '{name}' created successfully.")
			self.refresh_data()
		except Exception as e:
			session.rollback()
			QMessageBox.critical(self, "Error", f"Failed to create drawing set:\n{str(e)}")
		finally:
			session.close()
	
	def edit_selected_set(self):
		"""Edit the selected drawing set name"""
		selected_rows = self.sets_table.selectionModel().selectedRows()
		if not selected_rows:
			QMessageBox.information(self, "Edit Set", "Please select a drawing set to edit.")
			return
		row = selected_rows[0].row()
		set_id = self.sets_table.item(row, 0).data(Qt.UserRole)
		from PySide6.QtWidgets import QInputDialog
		new_name, ok = QInputDialog.getText(self, "Edit Drawing Set", "Set name:")
		if not ok or not new_name.strip():
			return
		session = get_session()
		try:
			set_to_edit = session.query(DrawingSet).filter(DrawingSet.id == set_id).first()
			if set_to_edit:
				set_to_edit.name = new_name.strip()
				session.commit()
				QMessageBox.information(self, "Success", "Drawing set updated successfully.")
				self.refresh_data()
		except Exception as e:
			session.rollback()
			QMessageBox.critical(self, "Error", f"Failed to update drawing set:\n{str(e)}")
		finally:
			session.close()
	
	def delete_selected_set(self):
		"""Delete the selected drawing set"""
		selected_rows = self.sets_table.selectionModel().selectedRows()
		if not selected_rows:
			QMessageBox.information(self, "Delete Set", "Please select a drawing set to delete.")
			return
		row = selected_rows[0].row()
		set_id = self.sets_table.item(row, 0).data(Qt.UserRole)
		# Confirm
		reply = QMessageBox.question(self, "Confirm Deletion", "Delete selected drawing set? This will unassign drawings from the set.", QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
		if reply != QMessageBox.Yes:
			return
		session = get_session()
		try:
			# Unassign drawings
			session.query(Drawing).filter(Drawing.drawing_set_id == set_id).update({Drawing.drawing_set_id: None})
			# Delete set
			session.query(DrawingSet).filter(DrawingSet.id == set_id).delete()
			session.commit()
			QMessageBox.information(self, "Success", "Drawing set deleted successfully.")
			self.refresh_data()
		except Exception as e:
			session.rollback()
			QMessageBox.critical(self, "Error", f"Failed to delete drawing set:\n{str(e)}")
		finally:
			session.close()
	
	def set_selected_active(self):
		"""Set the selected drawing set as active"""
		selected_rows = self.sets_table.selectionModel().selectedRows()
		if not selected_rows:
			QMessageBox.information(self, "Set Active", "Please select a drawing set to make active.")
			return
		row = selected_rows[0].row()
		set_id = self.sets_table.item(row, 0).data(Qt.UserRole)
		session = get_session()
		try:
			# Deactivate all sets in project
			session.query(DrawingSet).filter(DrawingSet.project_id == self.project_id).update({DrawingSet.is_active: False})
			# Activate selected set
			session.query(DrawingSet).filter(DrawingSet.id == set_id).update({DrawingSet.is_active: True})
			session.commit()
			QMessageBox.information(self, "Success", "Active drawing set updated.")
			self.refresh_data()
		except Exception as e:
			session.rollback()
			QMessageBox.critical(self, "Error", f"Failed to set active drawing set:\n{str(e)}")
		finally:
			session.close()
	
	def accept(self):
		"""Handle dialog acceptance"""
		if self.mode == 'create':
			self.create_drawing_set()
		super().accept()
	
	def create_drawing_set(self):
		"""Create the new drawing set from the creation form"""
		name = self.name_edit.text().strip() if hasattr(self, 'name_edit') else ''
		if not name:
			QMessageBox.warning(self, "Validation Error", "Please enter a name for the drawing set.")
			return
		phase = self.phase_combo.currentText() if hasattr(self, 'phase_combo') else 'Other'
		description = self.description_edit.toPlainText().strip() if hasattr(self, 'description_edit') else ''
		is_active = self.active_checkbox.isChecked() if hasattr(self, 'active_checkbox') else False
		session = get_session()
		try:
			if is_active:
				session.query(DrawingSet).filter(DrawingSet.project_id == self.project_id).update({DrawingSet.is_active: False})
			new_set = DrawingSet(project_id=self.project_id, name=name, phase_type=phase, description=description, is_active=is_active)
			session.add(new_set)
			session.commit()
		except Exception:
			session.rollback()
			raise
		finally:
			session.close()