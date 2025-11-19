"""
Materials Database Setup Dialog
Provides diagnostic information and configuration for material database loading
"""

from __future__ import annotations

import os
import sqlite3
from typing import Optional

from PySide6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QTabWidget,
    QWidget,
    QTableWidget,
    QTableWidgetItem,
    QTextEdit,
    QGroupBox,
    QFormLayout,
    QLineEdit,
    QFileDialog,
    QMessageBox,
    QHeaderView,
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QFont

from models import get_session
from models.rt60_models import AcousticMaterial
from data.materials import get_database_path, load_materials_from_database, get_fallback_materials
from data.materials_database import get_materials_database


class MaterialsDatabaseSetupDialog(QDialog):
    """Dialog for viewing and debugging materials database configuration"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Materials Database Setup")
        self.setModal(True)
        self.resize(900, 700)
        
        self._build_ui()
        self.refresh_data()
    
    def _build_ui(self):
        """Build the user interface"""
        layout = QVBoxLayout(self)
        
        # Header
        header_layout = QHBoxLayout()
        title_label = QLabel("Materials Database Configuration")
        title_label.setFont(QFont("Arial", 14, QFont.Bold))
        header_layout.addWidget(title_label)
        header_layout.addStretch()
        
        refresh_btn = QPushButton("Refresh")
        refresh_btn.clicked.connect(self.refresh_data)
        header_layout.addWidget(refresh_btn)
        
        layout.addLayout(header_layout)
        
        # Main tabs
        tabs = QTabWidget()
        
        # Overview tab
        overview_tab = self._create_overview_tab()
        tabs.addTab(overview_tab, "Overview")
        
        # SQLite Materials tab
        sqlite_tab = self._create_sqlite_tab()
        tabs.addTab(sqlite_tab, "SQLite Materials")
        
        # Component Library Materials tab
        component_tab = self._create_component_library_tab()
        tabs.addTab(component_tab, "Component Library")
        
        # Diagnostics tab
        diagnostics_tab = self._create_diagnostics_tab()
        tabs.addTab(diagnostics_tab, "Diagnostics")
        
        layout.addWidget(tabs)
        
        # Close button
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        close_btn = QPushButton("Close")
        close_btn.clicked.connect(self.accept)
        button_layout.addWidget(close_btn)
        layout.addLayout(button_layout)
    
    def _create_overview_tab(self):
        """Create the overview tab with summary information"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # Database paths
        paths_group = QGroupBox("Database Paths")
        paths_layout = QFormLayout()
        
        self.sqlite_path_label = QLabel()
        self.sqlite_path_label.setTextInteractionFlags(Qt.TextSelectableByMouse)
        paths_layout.addRow("SQLite Database:", self.sqlite_path_label)
        
        self.project_db_label = QLabel()
        self.project_db_label.setTextInteractionFlags(Qt.TextSelectableByMouse)
        paths_layout.addRow("Project Database:", self.project_db_label)
        
        paths_group.setLayout(paths_layout)
        layout.addWidget(paths_group)
        
        # Material counts
        counts_group = QGroupBox("Material Counts")
        counts_layout = QFormLayout()
        
        self.sqlite_count_label = QLabel()
        counts_layout.addRow("SQLite Materials:", self.sqlite_count_label)
        
        self.component_count_label = QLabel()
        counts_layout.addRow("Component Library Materials:", self.component_count_label)
        
        self.enhanced_count_label = QLabel()
        counts_layout.addRow("Enhanced Materials:", self.enhanced_count_label)
        
        self.total_count_label = QLabel()
        self.total_count_label.setFont(QFont("Arial", 10, QFont.Bold))
        counts_layout.addRow("Total Available:", self.total_count_label)
        
        counts_group.setLayout(counts_layout)
        layout.addWidget(counts_group)
        
        # Status
        status_group = QGroupBox("Status")
        status_layout = QVBoxLayout()
        
        self.status_text = QTextEdit()
        self.status_text.setReadOnly(True)
        self.status_text.setMaximumHeight(150)
        status_layout.addWidget(self.status_text)
        
        status_group.setLayout(status_layout)
        layout.addWidget(status_group)
        
        layout.addStretch()
        
        return widget
    
    def _create_sqlite_tab(self):
        """Create tab showing SQLite database materials"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        info_label = QLabel("Materials loaded from SQLite database (materials/acoustic_materials.db)")
        info_label.setWordWrap(True)
        layout.addWidget(info_label)
        
        self.sqlite_table = QTableWidget()
        self.sqlite_table.setColumnCount(4)
        self.sqlite_table.setHorizontalHeaderLabels(["Name", "NRC", "Category", "Source"])
        self.sqlite_table.horizontalHeader().setStretchLastSection(True)
        self.sqlite_table.setAlternatingRowColors(True)
        layout.addWidget(self.sqlite_table)
        
        return widget
    
    def _create_component_library_tab(self):
        """Create tab showing Component Library materials"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        info_label = QLabel("Materials from Component Library (SQLAlchemy AcousticMaterial model)")
        info_label.setWordWrap(True)
        layout.addWidget(info_label)
        
        self.component_table = QTableWidget()
        self.component_table.setColumnCount(5)
        self.component_table.setHorizontalHeaderLabels(["Name", "NRC", "Category", "Manufacturer", "Source"])
        self.component_table.horizontalHeader().setStretchLastSection(True)
        self.component_table.setAlternatingRowColors(True)
        layout.addWidget(self.component_table)
        
        return widget
    
    def _create_diagnostics_tab(self):
        """Create diagnostics tab with detailed information"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # File system checks
        files_group = QGroupBox("File System Checks")
        files_layout = QVBoxLayout()
        
        self.diagnostics_text = QTextEdit()
        self.diagnostics_text.setReadOnly(True)
        self.diagnostics_text.setFont(QFont("Courier", 9))
        files_layout.addWidget(self.diagnostics_text)
        
        files_group.setLayout(files_layout)
        layout.addWidget(files_group)
        
        # Recommendations
        recommendations_group = QGroupBox("Recommendations")
        recommendations_layout = QVBoxLayout()
        
        self.recommendations_text = QTextEdit()
        self.recommendations_text.setReadOnly(True)
        self.recommendations_text.setMaximumHeight(150)
        recommendations_layout.addWidget(self.recommendations_text)
        
        recommendations_group.setLayout(recommendations_layout)
        layout.addWidget(recommendations_group)
        
        return widget
    
    def refresh_data(self):
        """Refresh all data in the dialog"""
        # Update paths
        sqlite_path = get_database_path()
        self.sqlite_path_label.setText(sqlite_path)
        
        try:
            # Try to get project database path from location manager
            from utils.location_manager import LocationManager
            location_manager = LocationManager()
            project_db_path = location_manager.get_database_path()
            if project_db_path:
                self.project_db_label.setText(project_db_path)
            else:
                self.project_db_label.setText("No active project database")
        except Exception as e:
            self.project_db_label.setText(f"Unable to determine: {str(e)}")
        
        # Load and count materials
        try:
            sqlite_materials = load_materials_from_database()
            sqlite_count = len(sqlite_materials)
        except Exception as e:
            sqlite_materials = {}
            sqlite_count = 0
        
        try:
            from data.materials_database import get_materials_database
            db = get_materials_database()
            component_materials = db.load_materials_from_sqlalchemy()
            component_count = len(component_materials)
        except Exception as e:
            component_materials = {}
            component_count = 0
        
        try:
            try:
                from data.enhanced_materials import ENHANCED_MATERIALS
            except ImportError:
                from enhanced_materials import ENHANCED_MATERIALS
            enhanced_count = len(ENHANCED_MATERIALS) if ENHANCED_MATERIALS else 0
        except Exception:
            enhanced_count = 0
        
        # Get total from merged sources
        try:
            all_materials = db.get_all_materials()
            total_count = len(all_materials)
        except Exception:
            total_count = sqlite_count + component_count + enhanced_count
        
        # Update counts
        self.sqlite_count_label.setText(str(sqlite_count))
        self.component_count_label.setText(str(component_count))
        self.enhanced_count_label.setText(str(enhanced_count))
        self.total_count_label.setText(str(total_count))
        
        # Update status
        status_lines = []
        if sqlite_count > 0:
            status_lines.append(f"✓ SQLite database loaded: {sqlite_count} materials")
        else:
            status_lines.append(f"⚠ SQLite database: Not found or empty (using fallback: {len(get_fallback_materials())} materials)")
        
        if component_count > 0:
            status_lines.append(f"✓ Component Library: {component_count} materials")
        else:
            status_lines.append("⚠ Component Library: No materials found")
        
        if enhanced_count > 0:
            status_lines.append(f"✓ Enhanced materials: {enhanced_count} materials")
        
        status_lines.append(f"\nTotal materials available: {total_count}")
        
        self.status_text.setPlainText("\n".join(status_lines))
        
        # Populate SQLite table
        self._populate_sqlite_table(sqlite_materials)
        
        # Populate Component Library table
        self._populate_component_table(component_materials)
        
        # Update diagnostics
        self._update_diagnostics(sqlite_path, sqlite_count, component_count)
    
    def _populate_sqlite_table(self, materials: dict):
        """Populate the SQLite materials table"""
        self.sqlite_table.setRowCount(len(materials))
        
        for row, (key, material) in enumerate(sorted(materials.items(), key=lambda x: x[1]['name'])):
            self.sqlite_table.setItem(row, 0, QTableWidgetItem(material['name']))
            
            nrc_text = f"{material.get('nrc', 0):.2f}" if material.get('nrc') is not None else "—"
            self.sqlite_table.setItem(row, 1, QTableWidgetItem(nrc_text))
            
            self.sqlite_table.setItem(row, 2, QTableWidgetItem(material.get('category', 'unknown')))
            
            source = material.get('source', 'sqlite_database')
            self.sqlite_table.setItem(row, 3, QTableWidgetItem(source))
    
    def _populate_component_table(self, materials: dict):
        """Populate the Component Library materials table"""
        self.component_table.setRowCount(len(materials))
        
        for row, (key, material) in enumerate(sorted(materials.items(), key=lambda x: x[1]['name'])):
            self.component_table.setItem(row, 0, QTableWidgetItem(material['name']))
            
            nrc_text = f"{material.get('nrc', 0):.2f}" if material.get('nrc') is not None else "—"
            self.component_table.setItem(row, 1, QTableWidgetItem(nrc_text))
            
            self.component_table.setItem(row, 2, QTableWidgetItem(material.get('category', 'unknown')))
            
            mfr = material.get('manufacturer', '—')
            self.component_table.setItem(row, 3, QTableWidgetItem(mfr))
            
            source = material.get('source', 'component_library')
            self.component_table.setItem(row, 4, QTableWidgetItem(source))
    
    def _update_diagnostics(self, sqlite_path: str, sqlite_count: int, component_count: int):
        """Update diagnostics information"""
        lines = []
        
        # SQLite database checks
        lines.append("SQLite Database Checks:")
        lines.append("=" * 50)
        
        if os.path.exists(sqlite_path):
            lines.append(f"✓ File exists: {sqlite_path}")
            
            # Check file permissions
            if os.access(sqlite_path, os.R_OK):
                lines.append("✓ File is readable")
            else:
                lines.append("✗ File is NOT readable")
            
            if os.access(sqlite_path, os.W_OK):
                lines.append("✓ File is writable")
            else:
                lines.append("⚠ File is read-only")
            
            # Check file size
            try:
                size_mb = os.path.getsize(sqlite_path) / (1024 * 1024)
                lines.append(f"  File size: {size_mb:.2f} MB")
            except Exception:
                lines.append("  Could not determine file size")
            
            # Check database structure
            try:
                conn = sqlite3.connect(sqlite_path)
                cursor = conn.cursor()
                cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='acoustic_materials'")
                if cursor.fetchone():
                    lines.append("✓ Table 'acoustic_materials' exists")
                    
                    cursor.execute("SELECT COUNT(*) FROM acoustic_materials")
                    db_count = cursor.fetchone()[0]
                    lines.append(f"  Records in database: {db_count}")
                else:
                    lines.append("✗ Table 'acoustic_materials' NOT found")
                conn.close()
            except Exception as e:
                lines.append(f"✗ Database error: {e}")
        else:
            lines.append(f"✗ File NOT found: {sqlite_path}")
            lines.append(f"  Expected location: {os.path.abspath(sqlite_path)}")
        
        lines.append("")
        
        # Component Library checks
        lines.append("Component Library Checks:")
        lines.append("=" * 50)
        
        try:
            session = get_session()
            try:
                count = session.query(AcousticMaterial).count()
                lines.append(f"✓ Component Library accessible")
                lines.append(f"  Materials in database: {count}")
            except Exception as e:
                lines.append(f"✗ Component Library error: {e}")
            finally:
                session.close()
        except Exception as e:
            lines.append(f"✗ Cannot access Component Library: {e}")
        
        lines.append("")
        
        # Loading summary
        lines.append("Loading Summary:")
        lines.append("=" * 50)
        lines.append(f"SQLite materials loaded: {sqlite_count}")
        lines.append(f"Component Library materials loaded: {component_count}")
        
        self.diagnostics_text.setPlainText("\n".join(lines))
        
        # Recommendations
        recommendations = []
        
        if sqlite_count == 0:
            recommendations.append("• SQLite database not found or empty. Check that materials/acoustic_materials.db exists.")
            recommendations.append("• The system is using fallback materials. Consider importing materials into Component Library.")
        
        if component_count == 0:
            recommendations.append("• No materials in Component Library. Use 'Component Library > Acoustic Treatment' tab to add materials.")
        
        if sqlite_count > 0 and component_count > 0:
            recommendations.append("• Both sources are available. Materials are merged with Component Library taking priority.")
        
        if not recommendations:
            recommendations.append("• All systems operational. Materials are loading correctly from all sources.")
        
        self.recommendations_text.setPlainText("\n".join(recommendations))

