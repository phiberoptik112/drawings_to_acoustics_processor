"""
Drawing Comparison Interface - Side-by-side drawing comparison with change detection
"""

import json
from PySide6.QtWidgets import (
	QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
	QSplitter, QLabel, QPushButton, QToolBar, QStatusBar,
	QGroupBox, QListWidget, QListWidgetItem, QTabWidget,
	QProgressBar, QMessageBox, QComboBox, QCheckBox
)
from PySide6.QtCore import Qt, QThread, Signal
from PySide6.QtGui import QColor

from models import get_session
from models.drawing_sets import DrawingSet, DrawingComparison, ChangeItem
from drawing.drawing_comparison import DrawingComparisonEngine
from sqlalchemy.orm import selectinload


class ComparisonWorker(QThread):
	"""Background worker for performing drawing comparison"""
	progress_updated = Signal(int, str)  # percentage, status message
	comparison_completed = Signal(object)  # DrawingComparison object
	error_occurred = Signal(str)  # error message
	
	def __init__(self, base_set_id: int, compare_set_id: int):
		super().__init__()
		self.base_set_id = base_set_id
		self.compare_set_id = compare_set_id
		self.comparison_engine = DrawingComparisonEngine()
	
	def run(self):
		try:
			self.progress_updated.emit(10, "Initializing comparison...")
			self.progress_updated.emit(30, "Analyzing spaces...")
			self.progress_updated.emit(60, "Detecting HVAC changes...")
			self.progress_updated.emit(80, "Calculating acoustic impact...")
			comparison = self.comparison_engine.compare_drawing_sets(self.base_set_id, self.compare_set_id)
			self.progress_updated.emit(100, "Comparison complete!")
			self.comparison_completed.emit(comparison)
		except Exception as e:
			self.error_occurred.emit(str(e))


class DrawingComparisonInterface(QMainWindow):
	"""Main interface for drawing sets comparison"""
	
	def __init__(self, base_set_id: int, compare_set_id: int):
		super().__init__()
		self.base_set_id = base_set_id
		self.compare_set_id = compare_set_id
		self.comparison = None
		self.change_items = []
		self.sync_enabled = True
		self.load_drawing_sets()
		self.init_ui()
		self.start_comparison()
	
	def load_drawing_sets(self):
		session = get_session()
		try:
			# Eager-load drawings so counts can be accessed after session closes
			self.base_set = (
				session.query(DrawingSet)
				.options(selectinload(DrawingSet.drawings))
				.filter(DrawingSet.id == self.base_set_id)
				.first()
			)
			self.compare_set = (
				session.query(DrawingSet)
				.options(selectinload(DrawingSet.drawings))
				.filter(DrawingSet.id == self.compare_set_id)
				.first()
			)
			if not self.base_set or not self.compare_set:
				raise Exception("Could not load drawing sets")
		finally:
			session.close()
	
	def init_ui(self):
		self.setWindowTitle(f"Drawing Comparison: {self.base_set.name} vs {self.compare_set.name}")
		self.setGeometry(100, 100, 1200, 800)
		
		toolbar = QToolBar()
		self.addToolBar(toolbar)
		self.sync_checkbox = QCheckBox("Sync Viewers")
		self.sync_checkbox.setChecked(True)
		self.sync_checkbox.toggled.connect(self.set_sync_enabled)
		toolbar.addWidget(self.sync_checkbox)
		
		central = QWidget()
		self.setCentralWidget(central)
		main_layout = QVBoxLayout()
		
		header = QWidget()
		h_layout = QHBoxLayout()
		base_group = QGroupBox(f"Base: {self.base_set.name}")
		compare_group = QGroupBox(f"Compare: {self.compare_set.name}")
		base_layout = QVBoxLayout()
		base_layout.addWidget(QLabel(f"Phase: {self.base_set.phase_type}"))
		base_layout.addWidget(QLabel(f"Drawings: {len(self.base_set.drawings) if self.base_set.drawings else 0}"))
		base_group.setLayout(base_layout)
		compare_layout = QVBoxLayout()
		compare_layout.addWidget(QLabel(f"Phase: {self.compare_set.phase_type}"))
		compare_layout.addWidget(QLabel(f"Drawings: {len(self.compare_set.drawings) if self.compare_set.drawings else 0}"))
		compare_group.setLayout(compare_layout)
		h_layout.addWidget(base_group)
		h_layout.addWidget(compare_group)
		progress_group = QGroupBox("Status")
		pg_layout = QVBoxLayout()
		self.progress_label = QLabel("Ready to compare...")
		self.progress_bar = QProgressBar()
		pg_layout.addWidget(self.progress_label)
		pg_layout.addWidget(self.progress_bar)
		progress_group.setLayout(pg_layout)
		h_layout.addWidget(progress_group)
		header.setLayout(h_layout)
		main_layout.addWidget(header)
		
		# Bottom splitter with changes lists
		bottom_splitter = QSplitter(Qt.Vertical)
		
		changes_widget = QWidget()
		changes_layout = QVBoxLayout()
		self.changes_list = QListWidget()
		self.critical_list = QListWidget()
		tabs = QTabWidget()
		tabs.addTab(self.changes_list, "All Changes")
		tabs.addTab(self.critical_list, "Critical")
		changes_layout.addWidget(tabs)
		changes_widget.setLayout(changes_layout)
		bottom_splitter.addWidget(changes_widget)
		
		main_layout.addWidget(bottom_splitter)
		central.setLayout(main_layout)
		
		self.status_bar = QStatusBar()
		self.setStatusBar(self.status_bar)
		self.status_bar.showMessage("Ready")
	
	def start_comparison(self):
		self.progress_label.setText("Starting comparison...")
		self.progress_bar.setValue(0)
		self.comparison_worker = ComparisonWorker(self.base_set_id, self.compare_set_id)
		self.comparison_worker.progress_updated.connect(self.update_progress)
		self.comparison_worker.comparison_completed.connect(self.on_comparison_completed)
		self.comparison_worker.error_occurred.connect(self.on_comparison_error)
		self.comparison_worker.start()
	
	def update_progress(self, percentage: int, message: str):
		self.progress_bar.setValue(percentage)
		self.progress_label.setText(message)
		self.status_bar.showMessage(message)
	
	def on_comparison_completed(self, comparison: DrawingComparison):
		self.comparison = comparison
		session = get_session()
		try:
			self.change_items = session.query(ChangeItem).filter(ChangeItem.comparison_id == comparison.id).all()
		finally:
			session.close()
		self.update_changes_display()
		self.progress_label.setText(f"Comparison complete - {comparison.total_changes} changes detected")
	
	def on_comparison_error(self, error_message: str):
		self.progress_label.setText("Comparison failed")
		self.progress_bar.setValue(0)
		QMessageBox.critical(self, "Comparison Error", f"Failed to compare drawing sets:\n{error_message}")
	
	def update_changes_display(self):
		self.changes_list.clear()
		self.critical_list.clear()
		if not self.change_items:
			return
		severity_colors = {
			'critical': QColor(255, 99, 99),
			'high': QColor(255, 165, 0),
			'medium': QColor(255, 215, 0),
			'low': QColor(144, 238, 144),
		}
		sorted_changes = sorted(self.change_items, key=lambda x: {
			'critical': 0, 'high': 1, 'medium': 2, 'low': 3
		}.get(getattr(x, 'severity', 'low'), 4))
		for change in sorted_changes:
			change_details = json.loads(change.change_details) if change.change_details else {}
			element_name = change_details.get('name', f"{change.element_type}_{change.id}")
			icon = {'added': '➕', 'removed': '➖', 'modified': '📝', 'moved': '↔️'}.get(change.change_type, '❓')
			item_text = f"{icon} {element_name} - {change.change_type} ({change.severity})"
			item = QListWidgetItem(item_text)
			item.setData(Qt.UserRole, change.id)
			if change.severity in severity_colors:
				item.setForeground(severity_colors[change.severity])
			self.changes_list.addItem(item)
			if change.severity == 'critical':
				crit_item = QListWidgetItem(item_text)
				crit_item.setData(Qt.UserRole, change.id)
				crit_item.setForeground(severity_colors['critical'])
				self.critical_list.addItem(crit_item)
	
	def set_sync_enabled(self, enabled: bool):
		self.sync_enabled = enabled