"""
Project Dashboard - Main project management interface
"""

import os
from PySide6.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
                             QLabel, QPushButton, QListWidget, QListWidgetItem,
                             QTabWidget, QMenuBar, QStatusBar, QMessageBox,
                             QFileDialog, QSplitter, QTextEdit, QGroupBox, QDialog,
                             QTableWidget, QTableWidgetItem, QHeaderView, QCheckBox, QSizePolicy)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont, QIcon, QColor, QAction

from models import (
    get_session,
    Project,
    Drawing,
    Space,
    HVACPath,
    RoomBoundary,
    HVACComponent,
    HVACSegment,
    DrawingElement,
)
from models.hvac import HVACSegment
from models.hvac import SegmentFitting
from sqlalchemy.orm import selectinload
from ui.drawing_interface import DrawingInterface
from ui.results_widget import ResultsWidget
from ui.dialogs.hvac_path_dialog import HVACPathDialog
from ui.dialogs.drawing_sets_dialog import DrawingSetsDialog
from ui.drawing_comparison_interface import DrawingComparisonInterface
from data.excel_exporter import ExcelExporter, ExportOptions, EXCEL_EXPORT_AVAILABLE


class ProjectDashboard(QMainWindow):
    """Main project dashboard window"""
    
    finished = Signal()
    
    def __init__(self, project_id):
        super().__init__()
        self.project_id = project_id
        self.project = None
        self.drawing_interface = None
        
        # Store reference to space edit dialogs to keep them alive (non-modal)
        self.space_edit_dialogs = []
        
        # Store reference to component library dialog to keep it alive (non-modal)
        self.component_library_dialog = None
        
        self.load_project()
        self.init_ui()
        self.refresh_all_data()
        
    def load_project(self):
        """Load project from database"""
        try:
            session = get_session()
            self.project = session.query(Project).filter(Project.id == self.project_id).first()
            session.close()
            
            if not self.project:
                raise Exception(f"Project with ID {self.project_id} not found")
                
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to load project:\n{str(e)}")
            self.close()
            
    def init_ui(self):
        """Initialize the user interface"""
        self.setWindowTitle(f"Project: {self.project.name}")
        self.setGeometry(100, 100, 1200, 800)
        
        # Create menu bar
        self.create_menu_bar()
        
        # Create central widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # Main layout
        main_layout = QVBoxLayout()
        # Keep top chrome compact so center content gets vertical space
        try:
            main_layout.setContentsMargins(6, 4, 6, 6)
            main_layout.setSpacing(6)
        except Exception:
            pass
        
        # Project info header
        self.create_project_header(main_layout)
        
        # Create splitter for main content
        splitter = QSplitter(Qt.Horizontal)
        
        # Left panel - project elements
        left_panel = self.create_left_panel()
        splitter.addWidget(left_panel)
        
        # Right panel - details
        right_panel = self.create_right_panel()
        splitter.addWidget(right_panel)
        
        # Set splitter proportions (favor the drawing/right pane)
        splitter.setSizes([450, 750])
        
        main_layout.addWidget(splitter)
        central_widget.setLayout(main_layout)
        
        # Create status bar
        self.create_status_bar()
        
    def create_menu_bar(self):
        """Create the menu bar"""
        menubar = self.menuBar()
        
        # File menu
        file_menu = menubar.addMenu('File')
        file_menu.addAction('Save Project', self.save_project)
        file_menu.addSeparator()
        file_menu.addAction('Export Results', self.export_results)
        file_menu.addSeparator()
        file_menu.addAction('Close Project', self.close)
        
        # Project menu
        project_menu = menubar.addMenu('Project')
        project_menu.addAction('Project Settings', self.project_settings)
        project_menu.addAction('Import Drawing', self.import_drawing)
        
        # Drawings menu
        drawings_menu = menubar.addMenu('Drawings')
        drawings_menu.addAction('Open Drawing', self.open_drawing)
        drawings_menu.addAction('Remove Drawing', self.remove_drawing)
        
        # Calculations menu
        calc_menu = menubar.addMenu('Calculations')
        calc_menu.addAction('Calculate All RT60', self.calculate_all_rt60)
        calc_menu.addAction('Calculate All Noise', self.calculate_all_noise)
        
        # Reports menu
        reports_menu = menubar.addMenu('Reports')
        reports_menu.addAction('Project Summary', self.show_project_summary)
        reports_menu.addAction('Export to Excel', self.export_to_excel)
        
        # Settings menu
        settings_menu = menubar.addMenu('Settings')
        settings_menu.addAction('Database Settings...', self.open_database_settings)
        
        # Help menu
        help_menu = menubar.addMenu('Help')
        help_menu.addAction('About', self.show_about)
        
    def create_project_header(self, layout):
        """Create a compact project information header (single line)."""
        header_widget = QWidget()
        header_layout = QHBoxLayout()
        try:
            header_layout.setContentsMargins(6, 2, 6, 2)
            header_layout.setSpacing(8)
        except Exception:
            pass
        
        # Project title and optional description on one row
        title_label = QLabel(self.project.name)
        try:
            title_label.setFont(QFont("Arial", 13, QFont.Bold))
        except Exception:
            pass
        title_label.setStyleSheet("color: #ffffff; margin: 0px;")
        
        # Only show description if it exists and isn't a placeholder
        desc_text = (self.project.description or "").strip()
        show_desc = bool(desc_text and desc_text.lower() != "no description")
        if show_desc:
            description_label = QLabel(desc_text)
            description_label.setStyleSheet("color: #cfcfcf; margin: 0px;")
            try:
                description_label.setWordWrap(False)
            except Exception:
                pass
        
        # Inline layout: Title — Description
        info_row = QHBoxLayout()
        try:
            info_row.setContentsMargins(0, 0, 0, 0)
            info_row.setSpacing(8)
        except Exception:
            pass
        info_row.addWidget(title_label)
        if show_desc:
            sep = QLabel("—")
            sep.setStyleSheet("color: #9a9a9a;")
            info_row.addWidget(sep)
            info_row.addWidget(description_label)
        
        header_layout.addLayout(info_row)
        header_layout.addStretch()
        
        header_widget.setLayout(header_layout)
        # Cap the header height so it doesn't steal vertical space
        try:
            header_widget.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Maximum)
            header_widget.setMaximumHeight(32)
        except Exception:
            pass
        layout.addWidget(header_widget)
        
    def apply_dark_list_style(self, list_widget: QListWidget) -> None:
        """Apply consistent dark mode styling to list widgets."""
        list_widget.setStyleSheet(
            """
            QListWidget {
                background-color: #1e1e1e;
                color: #e0e0e0;
                border: 1px solid #3a3a3a;
            }
            QListWidget::item { padding: 2px 6px; }
            QListWidget::item:selected {
                background-color: #2d6cdf;
                color: #ffffff;
            }
            """
        )

    def create_left_panel(self):
        """Create the left panel with project elements"""
        left_widget = QWidget()
        left_layout = QVBoxLayout()
        
        # Create tabs for different element types
        tabs = QTabWidget()
        
        # Drawing Sets tab (new)
        drawing_sets_tab = self.create_drawing_sets_tab()
        tabs.addTab(drawing_sets_tab, "📁 Drawing Sets")
        
        # Drawings tab
        drawings_tab = self.create_drawings_tab()
        tabs.addTab(drawings_tab, "Drawings")
        
        # Spaces tab
        spaces_tab = self.create_spaces_tab()
        tabs.addTab(spaces_tab, "Spaces")
        
        # HVAC Paths tab
        hvac_tab = self.create_hvac_tab()
        tabs.addTab(hvac_tab, "HVAC Paths")
        
        # Results tab
        self.results_widget = ResultsWidget(self.project_id)
        self.results_widget.export_requested.connect(self.export_to_excel)
        tabs.addTab(self.results_widget, "📊 Results & Analysis")

        # Locations tab
        locations_tab = self.create_locations_tab()
        tabs.addTab(locations_tab, "📍 Locations")

        left_layout.addWidget(tabs)
        left_widget.setLayout(left_layout)

        return left_widget

    def create_locations_tab(self):
        """Create the locations browser tab"""
        from ui.widgets.location_browser_widget import LocationBrowserWidget

        widget = QWidget()
        layout = QVBoxLayout()

        # Location browser
        self.location_browser = LocationBrowserWidget(self.project_id, self)
        self.location_browser.location_selected.connect(self.on_location_selected)
        layout.addWidget(self.location_browser)

        # Auto-sync button
        button_layout = QHBoxLayout()

        sync_all_btn = QPushButton("🔄 Sync All Locations")
        sync_all_btn.setToolTip("Automatically create location bookmarks for all spaces and HVAC paths")
        sync_all_btn.clicked.connect(self.auto_sync_all_locations)
        button_layout.addWidget(sync_all_btn)

        button_layout.addStretch()
        layout.addLayout(button_layout)

        widget.setLayout(layout)
        return widget
        
    def create_drawing_sets_tab(self):
        """Create the drawing sets management tab"""
        widget = QWidget()
        layout = QVBoxLayout()
        
        # Drawing sets list with phase indicators
        self.drawing_sets_list = QListWidget()
        self.apply_dark_list_style(self.drawing_sets_list)
        try:
            self.drawing_sets_list.itemDoubleClicked.connect(self.manage_drawing_sets)
        except Exception:
            pass
        layout.addWidget(self.drawing_sets_list)
        
        # Management buttons
        button_layout = QHBoxLayout()
        
        new_set_btn = QPushButton("New Set")
        new_set_btn.clicked.connect(self.create_new_drawing_set)
        
        set_active_btn = QPushButton("Set Active")
        set_active_btn.clicked.connect(self.set_active_drawing_set)
        
        compare_sets_btn = QPushButton("Compare Sets")
        compare_sets_btn.clicked.connect(self.compare_drawing_sets)
        
        manage_sets_btn = QPushButton("Manage Sets")
        manage_sets_btn.clicked.connect(self.manage_drawing_sets)
        
        button_layout.addWidget(new_set_btn)
        button_layout.addWidget(set_active_btn)
        button_layout.addWidget(compare_sets_btn)
        button_layout.addWidget(manage_sets_btn)
        button_layout.addStretch()
        
        layout.addLayout(button_layout)
        widget.setLayout(layout)
        
        return widget
        
    def create_drawings_tab(self):
        """Create the drawings tab"""
        widget = QWidget()
        layout = QVBoxLayout()
        
        # Drawings list
        self.drawings_list = QListWidget()
        self.apply_dark_list_style(self.drawings_list)
        self.drawings_list.itemDoubleClicked.connect(self.open_selected_drawing)
        # Keep the embedded preview synchronized with selection
        try:
            self.drawings_list.currentItemChanged.connect(self.on_drawings_selection_changed)
        except Exception:
            pass
        layout.addWidget(self.drawings_list)
        
        # Buttons
        button_layout = QHBoxLayout()
        
        import_btn = QPushButton("Import Drawing")
        import_btn.clicked.connect(self.import_drawing)
        
        open_btn = QPushButton("Open Drawing")
        open_btn.clicked.connect(self.open_drawing)
        
        remove_btn = QPushButton("Remove")
        remove_btn.clicked.connect(self.remove_drawing)
        
        button_layout.addWidget(import_btn)
        button_layout.addWidget(open_btn)
        button_layout.addWidget(remove_btn)
        button_layout.addStretch()
        
        layout.addLayout(button_layout)
        widget.setLayout(layout)
        
        return widget
        
    def create_spaces_tab(self):
        """Create the spaces tab"""
        widget = QWidget()
        layout = QVBoxLayout()
        
        # Spaces list
        self.spaces_list = QListWidget()
        self.apply_dark_list_style(self.spaces_list)
        # Enable double-click to edit space properties
        self.spaces_list.itemDoubleClicked.connect(self.edit_space)
        # Update HVAC pathing table on selection change
        try:
            self.spaces_list.currentItemChanged.connect(self.on_spaces_selection_changed)
        except Exception:
            pass
        layout.addWidget(self.spaces_list)
        
        # Buttons
        button_layout = QHBoxLayout()
        
        new_space_btn = QPushButton("New Space")
        new_space_btn.clicked.connect(self.new_space)
        
        edit_space_btn = QPushButton("Edit Properties")
        edit_space_btn.clicked.connect(self.edit_space)
        
        duplicate_btn = QPushButton("Duplicate")
        duplicate_btn.clicked.connect(self.duplicate_space)

        delete_space_btn = QPushButton("Delete")
        delete_space_btn.clicked.connect(self.delete_space)
        
        button_layout.addWidget(new_space_btn)
        button_layout.addWidget(edit_space_btn)
        button_layout.addWidget(duplicate_btn)
        button_layout.addWidget(delete_space_btn)
        button_layout.addStretch()
        
        layout.addLayout(button_layout)
        widget.setLayout(layout)
        
        return widget
        
    def create_hvac_tab(self):
        """Create the HVAC paths tab"""
        widget = QWidget()
        layout = QVBoxLayout()
        
        # HVAC paths list
        self.hvac_list = QListWidget()
        self.apply_dark_list_style(self.hvac_list)
        self.hvac_list.itemDoubleClicked.connect(self.edit_hvac_path)
        # Single-click selection focuses path on embedded panel
        try:
            self.hvac_list.itemClicked.connect(self._on_hvac_path_clicked)
        except Exception:
            pass
        layout.addWidget(self.hvac_list)
        
        # Buttons
        button_layout = QHBoxLayout()
        
        new_path_btn = QPushButton("New Path")
        new_path_btn.clicked.connect(self.new_hvac_path)
        
        edit_path_btn = QPushButton("Edit Path")
        edit_path_btn.clicked.connect(self.edit_hvac_path)
        
        button_layout.addWidget(new_path_btn)
        button_layout.addWidget(edit_path_btn)
        button_layout.addStretch()
        
        layout.addLayout(button_layout)
        widget.setLayout(layout)
        
        return widget
        
    def create_right_panel(self):
        """Create the right panel with details and results"""
        right_widget = QWidget()
        right_layout = QVBoxLayout()
        
        # HVAC Pathing per Space group
        self.space_hvac_group = QGroupBox("HVAC Pathing per Space")
        space_hvac_layout = QVBoxLayout()
        
        self.space_hvac_table = QTableWidget(0, 5)
        self.space_hvac_table.setHorizontalHeaderLabels([
            "Path Name", "Type", "Segments", "Noise dB(A)", "NC"
        ])
        self.space_hvac_table.setSelectionBehavior(self.space_hvac_table.SelectionBehavior.SelectRows)
        self.space_hvac_table.setEditTriggers(self.space_hvac_table.EditTrigger.NoEditTriggers)
        self.space_hvac_table.cellDoubleClicked.connect(self.open_space_path_from_table)
        
        header = self.space_hvac_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.Stretch)
        for col in range(1, 5):
            header.setSectionResizeMode(col, QHeaderView.ResizeToContents)
        
        space_hvac_layout.addWidget(self.space_hvac_table)
        
        # Button row for space and drawing actions
        button_row = QHBoxLayout()
        
        self.edit_receiver_btn = QPushButton("Edit Space HVAC Receiver")
        self.edit_receiver_btn.clicked.connect(self.open_space_receiver_dialog)
        button_row.addWidget(self.edit_receiver_btn)
        
        self.library_btn = QPushButton("Component Library")
        self.library_btn.setToolTip("Manage mechanical units, silencers, and acoustic treatment schedules")
        self.library_btn.clicked.connect(self.open_component_library)
        button_row.addWidget(self.library_btn)
        
        self.open_editor_btn = QPushButton("Open Drawing Editor…")
        self.open_editor_btn.setToolTip("Open the full drawing editor with rectangle, component, and segment tools")
        self.open_editor_btn.clicked.connect(self.open_selected_drawing_editor)
        button_row.addWidget(self.open_editor_btn)
        
        button_row.addStretch()
        
        space_hvac_layout.addLayout(button_row)
        self.space_hvac_group.setLayout(space_hvac_layout)
        right_layout.addWidget(self.space_hvac_group)
 
        right_widget.setLayout(right_layout)
        
        return right_widget

    def open_selected_drawing_editor(self):
        """Open the full drawing editor window for the currently selected drawing."""
        current = self.drawings_list.currentItem() if hasattr(self, 'drawings_list') else None
        if not current:
            QMessageBox.information(self, "Open Drawing", "Select a drawing first.")
            return
        drawing_id = current.data(Qt.UserRole)
        if drawing_id is None:
            QMessageBox.information(self, "Open Drawing", "Select a valid drawing.")
            return
        try:
            self.drawing_interface = DrawingInterface(drawing_id, self.project_id)
            try:
                self.drawing_interface.paths_updated.connect(self.refresh_hvac_paths)
            except Exception:
                pass
            self.drawing_interface.show()
        except Exception as e:
            QMessageBox.critical(self, "Drawing Editor", f"Failed to open drawing editor:\n{e}")
        
    def create_status_bar(self):
        """Create the status bar"""
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        
        # Add status information
        self.update_status_bar()
        
    def refresh_all_data(self):
        """Refresh all data displays"""
        self.refresh_drawing_sets()
        self.refresh_drawings()
        self.refresh_spaces()
        self.refresh_hvac_paths()
        self.refresh_component_library()
        self.update_analysis_status()
        self.update_status_bar()
        
        # Refresh results widget
        if hasattr(self, 'results_widget'):
            self.results_widget.refresh_data()
        
    def refresh_drawing_sets(self):
        """Refresh the drawing sets list"""
        try:
            session = get_session()
            from models.drawing_sets import DrawingSet as _DrawingSet
            from sqlalchemy.orm import selectinload as _selectinload
            drawing_sets = (
                session.query(_DrawingSet)
                .options(_selectinload(_DrawingSet.drawings))
                .filter(_DrawingSet.project_id == self.project_id)
                .order_by(_DrawingSet.created_date)
                .all()
            )
            self.drawing_sets_list.clear()
            for drawing_set in drawing_sets:
                drawing_count = len(drawing_set.drawings) if drawing_set.drawings else 0
                active_indicator = "🟢" if drawing_set.is_active else "⚪"
                phase_colors = { 'DD': '🟦', 'SD': '🟨', 'CD': '🟥', 'Final': '🟩', 'Legacy': '⚫' }
                phase_icon = phase_colors.get(drawing_set.phase_type, '⚪')
                item_text = f"{active_indicator} {phase_icon} {drawing_set.name} ({drawing_set.phase_type}) - {drawing_count} drawings"
                item = QListWidgetItem(item_text)
                item.setData(Qt.UserRole, drawing_set.id)
                if drawing_set.is_active:
                    item.setForeground(QColor(144, 238, 144))
                self.drawing_sets_list.addItem(item)
            session.close()
        except Exception as e:
            QMessageBox.warning(self, "Warning", f"Could not load drawing sets:\n{str(e)}")
            
    def refresh_drawings(self):
        """Refresh the drawings list"""
        try:
            session = get_session()
            drawings = session.query(Drawing).filter(Drawing.project_id == self.project_id).all()
            
            self.drawings_list.clear()
            for drawing in drawings:
                item_text = f"📄 {drawing.name}"
                item = QListWidgetItem(item_text)
                item.setData(Qt.UserRole, drawing.id)
                self.drawings_list.addItem(item)
                
            session.close()
            
        except Exception as e:
            QMessageBox.warning(self, "Warning", f"Could not load drawings:\n{str(e)}")
            
    def refresh_spaces(self):
        """Refresh the spaces list, grouped by drawing set, with enhanced status information"""
        try:
            from models.drawing_sets import DrawingSet
            from sqlalchemy.orm import selectinload
            
            session = get_session()
            # Load spaces with drawing_set relationship
            spaces = (
                session.query(Space)
                .options(selectinload(Space.drawing_set))
                .filter(Space.project_id == self.project_id)
                .all()
            )
            
            self.spaces_list.clear()
            
            # Group spaces by drawing set
            grouped_spaces = {}
            no_set_spaces = []
            
            for space in spaces:
                if hasattr(space, 'drawing_set') and space.drawing_set:
                    ds_id = space.drawing_set.id
                    ds_name = space.drawing_set.name
                    ds_phase = space.drawing_set.phase_type or ""
                    if ds_id not in grouped_spaces:
                        grouped_spaces[ds_id] = {
                            'name': ds_name,
                            'phase': ds_phase,
                            'spaces': []
                        }
                    grouped_spaces[ds_id]['spaces'].append(space)
                else:
                    no_set_spaces.append(space)
            
            # Helper function to create space item
            def create_space_item(space, indented=False):
                # RT60 analysis status
                rt60_icon = "✅" if space.calculated_rt60 else "❌"
                
                # Get mechanical noise status
                try:
                    noise_status = space.get_mechanical_noise_status()
                    nc_rating = noise_status.get('nc_rating')
                    
                    if nc_rating is not None:
                        if nc_rating <= 25:
                            noise_icon = "🔇"  # Very quiet
                        elif nc_rating <= 35:
                            noise_icon = "🔉"  # Moderate
                        elif nc_rating <= 45:
                            noise_icon = "🔊"  # Loud
                        else:
                            noise_icon = "📢"  # Very loud
                        noise_text = f"NC{nc_rating}"
                    else:
                        noise_icon = "🔇"
                        noise_text = "No HVAC"
                except Exception:
                    noise_icon = "❓"
                    noise_text = "Error"
                    nc_rating = None
                
                # Drawing association status
                drawing_icon = "📋" if space.drawing_id else "❔"
                
                # Build item text with comprehensive status
                indent = "    " if indented else ""
                item_text = f"{indent}{drawing_icon} {space.name}"
                
                # Add status indicators
                status_parts = []
                status_parts.append(f"RT60: {rt60_icon}")
                status_parts.append(f"Noise: {noise_icon}{noise_text}")
                
                if status_parts:
                    item_text += f" | {' | '.join(status_parts)}"
                
                item = QListWidgetItem(item_text)
                item.setData(Qt.UserRole, space.id)
                
                # Dark theme friendly color coding using foreground (avoid light backgrounds)
                if space.calculated_rt60 and nc_rating is not None:
                    # Both calculated - color text based on noise level
                    if nc_rating <= 35:
                        item.setForeground(QColor(144, 238, 144))  # Light green text
                    elif nc_rating <= 45:
                        item.setForeground(QColor(255, 215, 0))    # Gold text
                    else:
                        item.setForeground(QColor(255, 99, 99))    # Soft red text
                elif space.calculated_rt60:
                    # Only RT60 calculated
                    item.setForeground(QColor(113, 183, 255))      # Light blue text
                else:
                    # Nothing calculated
                    item.setForeground(QColor(160, 160, 160))      # Gray text
                
                return item
            
            # Add grouped spaces with headers
            for ds_id, ds_data in sorted(grouped_spaces.items(), key=lambda x: x[1]['name']):
                # Add drawing set header
                header_text = f"📁 {ds_data['name']}"
                if ds_data['phase']:
                    header_text += f" ({ds_data['phase']})"
                header_item = QListWidgetItem(header_text)
                header_item.setFlags(Qt.ItemIsEnabled)  # Not selectable
                header_item.setFont(QFont("Arial", 10, QFont.Bold))
                header_item.setBackground(QColor("#2a2a2a"))
                header_item.setData(Qt.UserRole, None)  # No space ID
                self.spaces_list.addItem(header_item)
                
                # Add spaces under this drawing set with indentation
                for space in sorted(ds_data['spaces'], key=lambda s: s.name):
                    item = create_space_item(space, indented=True)
                    self.spaces_list.addItem(item)
            
            # Add spaces without drawing set
            if no_set_spaces:
                header_item = QListWidgetItem("📁 No Drawing Set")
                header_item.setFlags(Qt.ItemIsEnabled)  # Not selectable
                header_item.setFont(QFont("Arial", 10, QFont.Bold))
                header_item.setBackground(QColor("#2a2a2a"))
                header_item.setData(Qt.UserRole, None)
                self.spaces_list.addItem(header_item)
                
                for space in sorted(no_set_spaces, key=lambda s: s.name):
                    item = create_space_item(space, indented=True)
                    self.spaces_list.addItem(item)
            
            session.close()
            # Keep the HVAC pathing table synchronized with current selection
            self.update_space_hvac_paths_table()
            
        except Exception as e:
            QMessageBox.warning(self, "Warning", f"Could not load spaces:\n{str(e)}")
            
    def refresh_hvac_paths(self):
        """Refresh the HVAC paths list, grouped by drawing set"""
        try:
            from models.drawing_sets import DrawingSet
            from sqlalchemy.orm import selectinload
            
            session = get_session()
            # Load paths with drawing_set relationship
            paths = (
                session.query(HVACPath)
                .options(selectinload(HVACPath.drawing_set))
                .filter(HVACPath.project_id == self.project_id)
                .all()
            )
            
            self.hvac_list.clear()
            
            # Group paths by drawing set
            grouped_paths = {}
            no_set_paths = []
            
            for path in paths:
                if hasattr(path, 'drawing_set') and path.drawing_set:
                    ds_id = path.drawing_set.id
                    ds_name = path.drawing_set.name
                    ds_phase = path.drawing_set.phase_type or ""
                    if ds_id not in grouped_paths:
                        grouped_paths[ds_id] = {
                            'name': ds_name,
                            'phase': ds_phase,
                            'paths': []
                        }
                    grouped_paths[ds_id]['paths'].append(path)
                else:
                    no_set_paths.append(path)
            
            # Add grouped paths with headers
            for ds_id, ds_data in sorted(grouped_paths.items(), key=lambda x: x[1]['name']):
                # Add drawing set header
                header_text = f"📁 {ds_data['name']}"
                if ds_data['phase']:
                    header_text += f" ({ds_data['phase']})"
                header_item = QListWidgetItem(header_text)
                header_item.setFlags(Qt.ItemIsEnabled)  # Not selectable
                header_item.setFont(QFont("Arial", 10, QFont.Bold))
                header_item.setBackground(QColor("#2a2a2a"))
                header_item.setData(Qt.UserRole, None)  # No path ID
                self.hvac_list.addItem(header_item)
                
                # Add paths under this drawing set with indentation
                for path in sorted(ds_data['paths'], key=lambda p: p.name):
                    item_text = f"    🔀 {path.name} ({path.path_type})"
                    item = QListWidgetItem(item_text)
                    item.setData(Qt.UserRole, path.id)
                    self.hvac_list.addItem(item)
            
            # Add paths without drawing set
            if no_set_paths:
                header_item = QListWidgetItem("📁 No Drawing Set")
                header_item.setFlags(Qt.ItemIsEnabled)  # Not selectable
                header_item.setFont(QFont("Arial", 10, QFont.Bold))
                header_item.setBackground(QColor("#2a2a2a"))
                header_item.setData(Qt.UserRole, None)
                self.hvac_list.addItem(header_item)
                
                for path in sorted(no_set_paths, key=lambda p: p.name):
                    item_text = f"    🔀 {path.name} ({path.path_type})"
                    item = QListWidgetItem(item_text)
                    item.setData(Qt.UserRole, path.id)
                    self.hvac_list.addItem(item)
            
            session.close()
        except Exception as e:
            QMessageBox.warning(self, "Warning", f"Could not load HVAC paths:\n{str(e)}")
        finally:
            # Keep list in sync after operations
            self.update_analysis_status()
            self.update_space_hvac_paths_table()
            
    def refresh_component_library(self):
        """Refresh the component library display"""
        # If the library UI is not present (section removed to maximize space), skip updates
        if not hasattr(self, 'library_list') or self.library_list is None:
            return

        from data.components import STANDARD_COMPONENTS
        from data.materials import STANDARD_MATERIALS

        self.library_list.clear()

        # Add HVAC components
        self.library_list.addItem("🔧 HVAC Components:")
        for key, component in STANDARD_COMPONENTS.items():
            item_text = f"  • {component['name']}"
            self.library_list.addItem(item_text)

        # Add acoustic materials
        self.library_list.addItem("🎵 Acoustic Materials:")
        material_count = len(STANDARD_MATERIALS)
        self.library_list.addItem(f"  • {material_count} standard materials")
        
    def update_analysis_status(self):
        """Update the analysis status display"""
        try:
            session = get_session()
            
            # Count spaces and their analysis status
            spaces = session.query(Space).filter(Space.project_id == self.project_id).all()
            total_spaces = len(spaces)
            analyzed_spaces = len([s for s in spaces if s.calculated_rt60])
            
            # Count HVAC paths
            paths = session.query(HVACPath).filter(HVACPath.project_id == self.project_id).all()
            total_paths = len(paths)
            
            status_text = f"Analysis Status:\n\n"
            status_text += f"Spaces: {analyzed_spaces}/{total_spaces} analyzed\n"
            status_text += f"HVAC Paths: {total_paths} created\n\n"

            if analyzed_spaces < total_spaces:
                status_text += "⚠️ Some spaces need RT60 analysis\n"
            else:
                status_text += "✅ All spaces analyzed\n"

            if hasattr(self, 'status_text') and self.status_text is not None:
                self.status_text.setText(status_text)
            session.close()
            
        except Exception as e:
            if hasattr(self, 'status_text') and self.status_text is not None:
                self.status_text.setText(f"Error loading status: {str(e)}")
            
    def update_status_bar(self):
        """Update the status bar"""
        try:
            session = get_session()
            
            drawing_count = session.query(Drawing).filter(Drawing.project_id == self.project_id).count()
            space_count = session.query(Space).filter(Space.project_id == self.project_id).count()
            path_count = session.query(HVACPath).filter(HVACPath.project_id == self.project_id).count()
            
            status_text = f"Ready | Project: {self.project.name} | {drawing_count} drawings, {space_count} spaces, {path_count} paths"
            self.status_bar.showMessage(status_text)
            
            session.close()
            
        except Exception as e:
            self.status_bar.showMessage(f"Error: {str(e)}")

    def open_component_library(self):
        """Open the Component Library management dialog."""
        try:
            # If dialog already exists and is visible, just raise it to front
            if self.component_library_dialog and self.component_library_dialog.isVisible():
                self.component_library_dialog.raise_()
                self.component_library_dialog.activateWindow()
                return
            
            from ui.dialogs.component_library_dialog import ComponentLibraryDialog
            
            # Create non-modal dialog
            dialog = ComponentLibraryDialog(self, project_id=self.project_id)
            
            # Connect signals for updates and cleanup
            dialog.library_updated.connect(self.on_component_library_updated)
            dialog.finished.connect(self.on_component_library_closed)
            
            # Store reference to prevent garbage collection
            self.component_library_dialog = dialog
            
            # Show as non-modal window
            dialog.show()
            
        except Exception as e:
            QMessageBox.critical(self, "Component Library", f"Failed to open Component Library:\n{e}")
            
    # Slot implementations (placeholder methods)
    def import_drawing(self):
        """Import a new drawing (PDF)"""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Import PDF Drawing", "", "PDF Files (*.pdf);;All Files (*)"
        )
        
        if file_path:
            try:
                # Get drawing name from user
                drawing_name = os.path.splitext(os.path.basename(file_path))[0]
                
                session = get_session()
                
                # Create new drawing record
                drawing = Drawing(
                    project_id=self.project_id,
                    name=drawing_name,
                    file_path=file_path,
                    scale_string=self.project.default_scale
                )
                
                session.add(drawing)
                session.commit()
                session.close()
                
                # Refresh drawings list
                self.refresh_drawings()
                
                QMessageBox.information(self, "Success", f"Drawing '{drawing_name}' imported successfully.")
                
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to import drawing:\n{str(e)}")
        
    def open_drawing(self):
        """Open the selected drawing"""
        self.open_selected_drawing(self.drawings_list.currentItem())
        
    def open_selected_drawing(self, item):
        """Open the selected drawing in the drawing editor."""
        if not item:
            return
        drawing_id = item.data(Qt.UserRole)
        try:
            session = get_session()
            drawing = session.query(Drawing).filter(Drawing.id == drawing_id).first()
            session.close()
            if not drawing:
                QMessageBox.information(self, "Open Drawing", "Selected drawing not found.")
                return
            # Open in the drawing editor
            self.drawing_interface = DrawingInterface(drawing_id, self.project_id)
            try:
                self.drawing_interface.paths_updated.connect(self.refresh_hvac_paths)
            except Exception:
                pass
            self.drawing_interface.show()
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Could not open drawing:\n{e}")

    def on_drawings_selection_changed(self, current, _previous):
        """Handle drawing selection changes."""
        # Drawing preview removed - selection change no longer triggers automatic action
        pass
        
    def _on_drawing_selected(self, current, _previous):
        """Handle drawing selection - drawing panel removed."""
        # Drawing panel removed - no action needed
        pass
 
    def _on_hvac_path_clicked(self, item):
        """Handle HVAC path click - drawing panel removed."""
        # Drawing panel removed - no action needed
        pass
        
    def remove_drawing(self):
        """Remove the selected drawing"""
        try:
            current_item = self.drawings_list.currentItem()
            if not current_item:
                QMessageBox.information(self, "Remove Drawing", "Select a drawing to remove.")
                return
            drawing_id = current_item.data(Qt.UserRole)
            if drawing_id is None:
                QMessageBox.information(self, "Remove Drawing", "Select a valid drawing to remove.")
                return

            session = get_session()
            drawing = session.query(Drawing).filter(Drawing.id == drawing_id).first()
            if not drawing:
                session.close()
                QMessageBox.warning(self, "Remove Drawing", "Selected drawing not found.")
                return

            # Gather dependency counts for confirmation
            spaces_count = session.query(Space).filter(Space.drawing_id == drawing_id).count()
            boundaries_count = session.query(RoomBoundary).filter(RoomBoundary.drawing_id == drawing_id).count()
            components = session.query(HVACComponent).filter(HVACComponent.drawing_id == drawing_id).all()
            component_ids = [c.id for c in components]
            segments_count = 0
            if component_ids:
                segments_count = (
                    session.query(HVACSegment)
                    .filter(
                        (HVACSegment.from_component_id.in_(component_ids))
                        | (HVACSegment.to_component_id.in_(component_ids))
                    )
                    .count()
                )
            elements_count = session.query(DrawingElement).filter(DrawingElement.drawing_id == drawing_id).count()

            confirm_text = (
                f"Remove drawing '{drawing.name}'?\n\n"
                f"This will:\n"
                f"• Detach {spaces_count} space(s) from this drawing\n"
                f"• Delete {boundaries_count} room boundary(ies) on this drawing\n"
                f"• Delete {segments_count} HVAC segment(s) tied to components on this drawing\n"
                f"• Delete {len(components)} HVAC component(s) on this drawing\n"
                f"• Delete {elements_count} saved overlay element(s) (rectangles, components, segments, measurements)\n\n"
                "Project data remains otherwise intact. The PDF file on disk is not deleted."
            )

            reply = QMessageBox.question(
                self,
                "Confirm Removal",
                confirm_text,
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No,
            )
            if reply != QMessageBox.Yes:
                session.close()
                return

            try:
                # Start cleanup in a single transaction
                # 1) Delete HVAC segment fittings for segments tied to components on this drawing
                if component_ids:
                    segment_ids = [
                        sid for (sid,) in session.query(HVACSegment.id)
                        .filter(
                            (HVACSegment.from_component_id.in_(component_ids))
                            | (HVACSegment.to_component_id.in_(component_ids))
                        )
                        .all()
                    ]

                    if segment_ids:
                        # Delete fittings first to satisfy FK constraints
                        session.query(SegmentFitting).filter(
                            SegmentFitting.segment_id.in_(segment_ids)
                        ).delete(synchronize_session=False)

                        # Then delete the segments themselves
                        session.query(HVACSegment).filter(
                            HVACSegment.id.in_(segment_ids)
                        ).delete(synchronize_session=False)

                # 2) Delete HVAC components on this drawing
                session.query(HVACComponent).filter(HVACComponent.drawing_id == drawing_id).delete(
                    synchronize_session=False
                )

                # 3) Delete overlay elements and room boundaries tied to this drawing
                session.query(DrawingElement).filter(DrawingElement.drawing_id == drawing_id).delete(
                    synchronize_session=False
                )
                session.query(RoomBoundary).filter(RoomBoundary.drawing_id == drawing_id).delete(
                    synchronize_session=False
                )

                # 4) Detach spaces (keep the spaces; clear drawing reference)
                session.query(Space).filter(Space.drawing_id == drawing_id).update(
                    {Space.drawing_id: None}, synchronize_session=False
                )

                # 5) Finally delete the drawing record itself
                session.delete(drawing)
                session.commit()
            except Exception as e:
                session.rollback()
                session.close()
                QMessageBox.critical(self, "Remove Drawing", f"Failed to remove drawing:\n{e}")
                return

            session.close()

            # Close any open drawing interface for this drawing
            try:
                if getattr(self, "drawing_interface", None) is not None:
                    if getattr(self.drawing_interface, "drawing_id", None) == drawing_id:
                        self.drawing_interface.close()
                        self.drawing_interface = None
            except Exception:
                pass

            # Refresh UI elements
            self.refresh_drawings()
            self.refresh_spaces()
            self.refresh_hvac_paths()
            self.update_analysis_status()
            self.update_status_bar()

            QMessageBox.information(self, "Remove Drawing", f"Drawing '{drawing.name}' removed.")

        except Exception as e:
            QMessageBox.critical(self, "Remove Drawing", f"Unexpected error:\n{e}")
        
    def new_space(self):
        """Create a new space"""
        try:
            from .dialogs.new_space_dialog import NewSpaceDialog
            
            dialog = NewSpaceDialog(self, self.project_id)
            result = dialog.exec()
            
            if result == QDialog.Accepted:
                # Refresh the spaces list to show the new space
                self.refresh_spaces()
                
        except ImportError:
            # Fallback to manual space creation if dialog doesn't exist
            self.create_manual_space()
    
    def create_manual_space(self):
        """Create a space manually without drawing integration"""
        from PySide6.QtWidgets import QInputDialog
        from models.space import Space
        from models import get_session
        
        # Get space name
        space_name, ok = QInputDialog.getText(
            self, 
            "New Space", 
            "Enter space name:",
            text="New Space"
        )
        
        if not ok or not space_name.strip():
            return
            
        try:
            session = get_session()
            
            # Create basic space
            space = Space(
                project_id=self.project_id,
                name=space_name.strip(),
                description="Created from project dashboard",
                floor_area=100.0,  # Default area
                ceiling_height=9.0,  # Default height
                target_rt60=0.8,
                # Set default materials
                ceiling_material='acoustic_ceiling_tile',
                wall_material='painted_drywall',
                floor_material='carpet_on_concrete'
            )
            
            session.add(space)
            session.commit()
            session.close()
            
            QMessageBox.information(
                self, 
                "Space Created", 
                f"Space '{space_name}' created successfully.\n\n"
                "To set precise dimensions and materials:\n"
                "1. Draw a rectangle on a PDF drawing\n"
                "2. Right-click and select 'Create Room/Space'\n"
                "3. Or edit this space's properties to set dimensions manually"
            )
            
            # Refresh the spaces list
            self.refresh_spaces()
            
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to create space:\n{str(e)}")
        
    def edit_space(self, item=None):
        """Edit space properties. Can be triggered by button or double-click on a list item."""
        # Support both double-click (passes QListWidgetItem) and button click
        current_item = item if (item is not None and hasattr(item, 'data')) else self.spaces_list.currentItem()
        if not current_item:
            QMessageBox.warning(self, "No Selection", "Please select a space to edit.")
            return
            
        space_id = current_item.data(Qt.UserRole)
        
        try:
            session = get_session()
            space = session.query(Space).filter(Space.id == space_id).first()
            
            if not space:
                QMessageBox.critical(self, "Error", "Selected space not found.")
                session.close()
                return
            
            # Import the dialog here to avoid circular imports
            from ui.dialogs.space_edit_dialog import SpaceEditDialog
            
            # Create non-modal dialog
            dialog = SpaceEditDialog(self, space)
            
            # Connect signals for updates and cleanup
            dialog.space_updated.connect(self.on_space_updated)
            dialog.finished.connect(lambda: self.on_space_dialog_closed(dialog))
            
            # Store reference to prevent garbage collection
            self.space_edit_dialogs.append(dialog)
            
            # Show as non-modal window
            dialog.show()
            
            # Close session after dialog is shown
            session.close()
            
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to edit space:\n{str(e)}")
    
    def on_space_updated(self):
        """Handle when a space is updated in the edit dialog"""
        # Refresh the UI to show updated data
        self.refresh_spaces()
        self.refresh_all_data()
    
    def on_space_dialog_closed(self, dialog):
        """Handle cleanup when a space edit dialog is closed"""
        # Remove the dialog reference to allow garbage collection
        if dialog in self.space_edit_dialogs:
            self.space_edit_dialogs.remove(dialog)
    
    def on_component_library_updated(self):
        """Handle when component library data is updated"""
        # Refresh the library list to show changes
        self.refresh_component_library()
    
    def on_component_library_closed(self):
        """Handle cleanup when component library dialog is closed"""
        # Remove the dialog reference to allow garbage collection
        self.component_library_dialog = None
        
    def duplicate_space(self):
        """Duplicate the selected space"""
        QMessageBox.information(self, "Duplicate Space", "Space duplication will be implemented.")
    
    def delete_space(self):
        """Delete the selected space and detach dependent records"""
        try:
            current_item = self.spaces_list.currentItem()
            if not current_item:
                QMessageBox.information(self, "Delete Space", "Select a space to delete.")
                return
            space_id = current_item.data(Qt.UserRole)
            if space_id is None:
                QMessageBox.information(self, "Delete Space", "Select a valid space to delete.")
                return

            session = get_session()
            space = session.query(Space).filter(Space.id == space_id).first()
            if not space:
                session.close()
                QMessageBox.warning(self, "Delete Space", "Selected space not found.")
                return

            # Gather dependency counts for confirmation
            hvac_count = session.query(HVACPath).filter(HVACPath.target_space_id == space_id).count()
            boundaries_count = session.query(RoomBoundary).filter(RoomBoundary.space_id == space_id).count()

            confirm_text = (
                f"Delete space '{space.name}'?\n\n"
                f"This will:\n"
                f"• Delete {boundaries_count} room boundary(ies) linked to this space\n"
                f"• Detach {hvac_count} HVAC path(s) currently targeting this space\n"
                f"• Remove RT60 results and surface materials stored for this space"
            )

            reply = QMessageBox.question(
                self,
                "Confirm Delete",
                confirm_text,
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No,
            )
            if reply != QMessageBox.Yes:
                session.close()
                return

            try:
                # Detach HVAC paths that reference this space
                session.query(HVACPath).filter(HVACPath.target_space_id == space_id).update(
                    {HVACPath.target_space_id: None}, synchronize_session=False
                )

                # Delete the space (cascades remove related orphan rows per model config)
                session.delete(space)
                session.commit()
            except Exception as e:
                session.rollback()
                session.close()
                QMessageBox.critical(self, "Delete Space", f"Failed to delete space:\n{e}")
                return

            session.close()

            # Refresh UI elements
            self.refresh_spaces()
            self.refresh_hvac_paths()
            self.update_analysis_status()
            self.update_status_bar()

            QMessageBox.information(self, "Delete Space", f"Space '{space.name}' deleted.")
        except Exception as e:
            QMessageBox.critical(self, "Delete Space", f"Unexpected error:\n{e}")
        
    def new_hvac_path(self):
        """Create a new HVAC path using the HVACPathDialog"""
        try:
            dialog = HVACPathDialog(self, project_id=self.project_id)
            if dialog.exec() == QDialog.Accepted:
                # Dialog emits saved path internally; just refresh
                self.refresh_hvac_paths()
                self.update_analysis_status()
                self.update_space_hvac_paths_table()
        except Exception as e:
            QMessageBox.critical(self, "New HVAC Path", f"Failed to create HVAC path:\n{str(e)}")
        
    def edit_hvac_path(self, item=None):
        """Edit HVAC path properties with dialog"""
        try:
            # Determine selected path id
            # Handle connections from both double-click (item passed) and button click (bool passed)
            if isinstance(item, bool) or item is None or not hasattr(item, 'data'):
                item = self.hvac_list.currentItem()
            if not item:
                QMessageBox.information(self, "Edit HVAC Path", "Select a path to edit.")
                return
            path_id = item.data(Qt.UserRole)
            if path_id is None:
                QMessageBox.information(self, "Edit HVAC Path", "Select a path to edit.")
                return
            session = get_session()
            path = (
                session.query(HVACPath)
                .options(
                    selectinload(HVACPath.target_space),
                    selectinload(HVACPath.segments).selectinload(HVACSegment.from_component),
                    selectinload(HVACPath.segments).selectinload(HVACSegment.to_component),
                    # Ensure fittings are eagerly loaded to avoid lazy-load after session close
                    selectinload(HVACPath.segments).selectinload(HVACSegment.fittings),
                )
                .filter(HVACPath.id == path_id)
                .first()
            )
            session.close()
            if not path:
                QMessageBox.warning(self, "Edit HVAC Path", "Selected path not found.")
                return
            dialog = HVACPathDialog(self, project_id=self.project_id, path=path)
            if dialog.exec() == QDialog.Accepted:
                self.refresh_hvac_paths()
                self.update_analysis_status()
                self.update_space_hvac_paths_table()
                self.update_space_hvac_paths_table()
        except Exception as e:
            QMessageBox.critical(self, "Edit HVAC Path", f"Failed to edit HVAC path:\n{str(e)}")
        
    def save_project(self):
        """Save the current project"""
        QMessageBox.information(self, "Save Project", "Project saved successfully.")
        
    def export_results(self):
        """Export analysis results"""
        QMessageBox.information(self, "Export Results", "Results export will be implemented.")
        
    def project_settings(self):
        """Open project settings"""
        try:
            from ui.dialogs.project_settings_dialog import ProjectSettingsDialog
            
            dialog = ProjectSettingsDialog(self, self.project_id)
            if dialog.exec() == QDialog.Accepted:
                # Reload project data and refresh UI
                self.load_project()
                self.setWindowTitle(f"Project: {self.project.name}")
                self.refresh_all_data()
                
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to open project settings:\n{str(e)}")
        
    def calculate_all_rt60(self):
        """Calculate RT60 for all spaces"""
        QMessageBox.information(self, "Calculate RT60", "RT60 calculation will be implemented.")
        
    def calculate_all_noise(self):
        """Calculate noise for all HVAC paths"""
        QMessageBox.information(self, "Calculate Noise", "Noise calculation will be implemented.")
        
    def show_project_summary(self):
        """Show project summary report"""
        QMessageBox.information(self, "Project Summary", "Project summary will be implemented.")
        
    def export_to_excel(self):
        """Export project analysis to Excel"""
        try:
            if not EXCEL_EXPORT_AVAILABLE:
                QMessageBox.warning(self, "Export Not Available", 
                                   "Excel export requires the openpyxl library.\n"
                                   "Please install it using: pip install openpyxl")
                return
            
            # Get export file path
            default_name = f"{self.project.name.replace(' ', '_')}_acoustic_analysis.xlsx"
            file_path, _ = QFileDialog.getSaveFileName(
                self, "Export to Excel", default_name, 
                "Excel Files (*.xlsx);;All Files (*)"
            )
            
            if not file_path:
                return
            
            # Create export options dialog
            export_options = self.get_export_options()
            if not export_options:
                return
            
            # Create exporter and get summary
            exporter = ExcelExporter()
            summary = exporter.get_export_summary(self.project_id)
            
            if "error" in summary:
                QMessageBox.critical(self, "Export Error", f"Failed to prepare export:\n{summary['error']}")
                return
            
            # Show export summary and confirm
            confirm_msg = f"Export Summary for '{summary['project_name']}':\n\n"
            confirm_msg += f"• {summary['total_spaces']} spaces ({summary['spaces_with_rt60']} with RT60)\n"
            confirm_msg += f"• {summary['total_hvac_paths']} HVAC paths ({summary['paths_with_noise']} with noise calc)\n"
            confirm_msg += f"• {summary['total_components']} HVAC components\n\n"
            confirm_msg += f"Sheets to export: {', '.join(summary['sheets_to_export'])}\n\n"
            confirm_msg += f"Export to: {file_path}"
            
            reply = QMessageBox.question(self, "Confirm Export", confirm_msg,
                                       QMessageBox.Yes | QMessageBox.No,
                                       QMessageBox.Yes)
            
            if reply != QMessageBox.Yes:
                return
            
            # Perform export
            success = exporter.export_project_analysis(self.project_id, file_path, export_options)
            
            if success:
                reply = QMessageBox.information(self, "Export Complete", 
                                              f"Successfully exported project analysis to:\n{file_path}\n\n"
                                              f"Would you like to open the file?",
                                              QMessageBox.Yes | QMessageBox.No,
                                              QMessageBox.No)
                
                if reply == QMessageBox.Yes:
                    import subprocess
                    import platform
                    
                    try:
                        if platform.system() == 'Darwin':  # macOS
                            subprocess.call(['open', file_path])
                        elif platform.system() == 'Windows':  # Windows
                            os.startfile(file_path)
                        else:  # Linux
                            subprocess.call(['xdg-open', file_path])
                    except Exception as e:
                        QMessageBox.information(self, "File Exported", 
                                              f"Export completed but couldn't open file automatically:\n{file_path}")
            else:
                QMessageBox.critical(self, "Export Failed", "Failed to export project analysis to Excel.")
                
        except Exception as e:
            QMessageBox.critical(self, "Export Error", f"Failed to export to Excel:\n{str(e)}")
    
    def on_spaces_selection_changed(self, current, _previous):
        """When the selection in the Spaces tab changes, refresh the HVAC table."""
        try:
            self.update_space_hvac_paths_table()
        except Exception:
            pass

    def update_space_hvac_paths_table(self):
        """Populate the 'HVAC Pathing per Space' table for the selected space."""
        if not hasattr(self, 'space_hvac_table'):
            return
        current_item = self.spaces_list.currentItem() if hasattr(self, 'spaces_list') else None
        if not current_item:
            self.space_hvac_table.setRowCount(0)
            return
        space_id = current_item.data(Qt.UserRole)
        try:
            session = get_session()
            paths = (
                session.query(HVACPath)
                .options(selectinload(HVACPath.segments))
                .filter(HVACPath.project_id == self.project_id)
                .filter(HVACPath.target_space_id == space_id)
                .all()
            )
            self.space_hvac_table.setRowCount(len(paths))
            for row, path in enumerate(paths):
                name_item = QTableWidgetItem(path.name or "")
                name_item.setData(Qt.UserRole, path.id)
                type_item = QTableWidgetItem(path.path_type or "")
                seg_count = len(path.segments) if getattr(path, 'segments', None) is not None else 0
                seg_item = QTableWidgetItem(str(seg_count))
                noise_item = QTableWidgetItem(
                    f"{float(path.calculated_noise):.1f}" if path.calculated_noise is not None else "—"
                )
                nc_item = QTableWidgetItem(
                    f"NC-{float(path.calculated_nc):.0f}" if path.calculated_nc is not None else "—"
                )
                self.space_hvac_table.setItem(row, 0, name_item)
                self.space_hvac_table.setItem(row, 1, type_item)
                self.space_hvac_table.setItem(row, 2, seg_item)
                self.space_hvac_table.setItem(row, 3, noise_item)
                self.space_hvac_table.setItem(row, 4, nc_item)
            session.close()
        except Exception as e:
            # Show a single-row error
            self.space_hvac_table.setRowCount(1)
            self.space_hvac_table.setItem(0, 0, QTableWidgetItem(f"Error: {e}"))
            for col in range(1, 5):
                self.space_hvac_table.setItem(0, col, QTableWidgetItem(""))

    def open_space_path_from_table(self, row, _column):
        """Open the double-clicked HVAC path from the table for editing."""
        try:
            item = self.space_hvac_table.item(row, 0)
            if not item:
                return
            path_id = item.data(Qt.UserRole)
            if path_id is None:
                return
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
            session.close()
            if not path:
                QMessageBox.warning(self, "Edit HVAC Path", "Selected path not found.")
                return
            dialog = HVACPathDialog(self, project_id=self.project_id, path=path)
            if dialog.exec() == QDialog.Accepted:
                self.refresh_hvac_paths()
                self.update_analysis_status()
                self.update_space_hvac_paths_table()
        except Exception as e:
            QMessageBox.critical(self, "Edit HVAC Path", f"Failed to open HVAC path:\n{str(e)}")

    def open_space_receiver_dialog(self):
        """Open the receiver analysis dialog for the currently selected space."""
        try:
            current_item = self.spaces_list.currentItem()
            if not current_item:
                QMessageBox.information(self, "Receiver Analysis", "Select a space first.")
                return
            space_id = current_item.data(Qt.UserRole)
            if space_id is None:
                QMessageBox.information(self, "Receiver Analysis", "Select a valid space.")
                return
            from ui.dialogs.hvac_receiver_dialog import HVACReceiverDialog
            dialog = HVACReceiverDialog(self, space_id)
            dialog.exec()
        except Exception as e:
            QMessageBox.critical(self, "Receiver Analysis", f"Failed to open receiver dialog:\n{str(e)}")

    def get_export_options(self):
        """Get export options from user"""
        try:
            from PySide6.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QCheckBox, QPushButton, QLabel
            
            class ExportOptionsDialog(QDialog):
                def __init__(self, parent=None):
                    super().__init__(parent)
                    self.setWindowTitle("Excel Export Options")
                    self.setModal(True)
                    self.setFixedSize(400, 350)
                    
                    layout = QVBoxLayout()
                    
                    # Instructions
                    instructions = QLabel("Select what to include in the Excel export:")
                    instructions.setWordWrap(True)
                    layout.addWidget(instructions)
                    
                    # Checkboxes for export options
                    self.spaces_cb = QCheckBox("Spaces Analysis (RT60, materials)")
                    self.spaces_cb.setChecked(True)
                    layout.addWidget(self.spaces_cb)
                    
                    self.hvac_paths_cb = QCheckBox("HVAC Paths (noise calculations)")
                    self.hvac_paths_cb.setChecked(True)
                    layout.addWidget(self.hvac_paths_cb)
                    
                    self.components_cb = QCheckBox("HVAC Components (equipment list)")
                    self.components_cb.setChecked(True)
                    layout.addWidget(self.components_cb)
                    
                    self.rt60_details_cb = QCheckBox("RT60 Compliance Details")
                    self.rt60_details_cb.setChecked(True)
                    layout.addWidget(self.rt60_details_cb)
                    
                    self.nc_analysis_cb = QCheckBox("NC Analysis and Standards")
                    self.nc_analysis_cb.setChecked(True)
                    layout.addWidget(self.nc_analysis_cb)
                    
                    self.recommendations_cb = QCheckBox("Recommendations and Issues")
                    self.recommendations_cb.setChecked(True)
                    layout.addWidget(self.recommendations_cb)
                    
                    # Buttons
                    button_layout = QHBoxLayout()
                    
                    select_all_btn = QPushButton("Select All")
                    select_all_btn.clicked.connect(self.select_all)
                    
                    select_none_btn = QPushButton("Select None")
                    select_none_btn.clicked.connect(self.select_none)
                    
                    ok_btn = QPushButton("Export")
                    ok_btn.clicked.connect(self.accept)
                    ok_btn.setDefault(True)
                    
                    cancel_btn = QPushButton("Cancel")
                    cancel_btn.clicked.connect(self.reject)
                    
                    button_layout.addWidget(select_all_btn)
                    button_layout.addWidget(select_none_btn)
                    button_layout.addStretch()
                    button_layout.addWidget(ok_btn)
                    button_layout.addWidget(cancel_btn)
                    
                    layout.addLayout(button_layout)
                    self.setLayout(layout)
                
                def select_all(self):
                    for cb in [self.spaces_cb, self.hvac_paths_cb, self.components_cb, 
                              self.rt60_details_cb, self.nc_analysis_cb, self.recommendations_cb]:
                        cb.setChecked(True)
                
                def select_none(self):
                    for cb in [self.spaces_cb, self.hvac_paths_cb, self.components_cb, 
                              self.rt60_details_cb, self.nc_analysis_cb, self.recommendations_cb]:
                        cb.setChecked(False)
                
                def get_options(self):
                    return ExportOptions(
                        include_spaces=self.spaces_cb.isChecked(),
                        include_hvac_paths=self.hvac_paths_cb.isChecked(),
                        include_components=self.components_cb.isChecked(),
                        include_rt60_details=self.rt60_details_cb.isChecked(),
                        include_nc_analysis=self.nc_analysis_cb.isChecked(),
                        include_recommendations=self.recommendations_cb.isChecked(),
                        include_charts=False  # Not implemented yet
                    )
            
            dialog = ExportOptionsDialog(self)
            if dialog.exec() == QDialog.Accepted:
                return dialog.get_options()
            else:
                return None
                
        except Exception as e:
            QMessageBox.warning(self, "Options Error", f"Error getting export options:\n{str(e)}")
            return ExportOptions()  # Default options
        
    def open_database_settings(self):
        """Open the database settings dialog"""
        try:
            from ui.dialogs.database_settings_dialog import DatabaseSettingsDialog
            from models.database import engine
            
            # Get current database path
            current_db_path = None
            if engine:
                db_url = str(engine.url)
                if db_url.startswith('sqlite:///'):
                    current_db_path = db_url[10:]  # Remove 'sqlite:///'
            
            dialog = DatabaseSettingsDialog(self, current_db_path)
            if dialog.exec() == dialog.accepted:
                QMessageBox.information(
                    self,
                    "Settings Updated",
                    "Database settings have been updated.\n"
                    "Please restart the application for the changes to take effect."
                )
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to open database settings:\n{str(e)}")
    
    def show_about(self):
        """Show about dialog"""
        QMessageBox.about(self, "About", "Acoustic Analysis Tool v1.0\nfor LEED Acoustic Certification")
        
    def closeEvent(self, event):
        """Handle window close event"""
        self.finished.emit()
        event.accept()

    def create_new_drawing_set(self):
        """Create a new drawing set"""
        try:
            dialog = DrawingSetsDialog(self, self.project_id, mode='create')
            if dialog.exec() == QDialog.Accepted:
                self.refresh_drawing_sets()
                self.refresh_drawings()
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to create drawing set:\n{str(e)}")

    def set_active_drawing_set(self):
        """Set the selected drawing set as active"""
        try:
            current_item = getattr(self, 'drawing_sets_list', None)
            current_item = current_item.currentItem() if current_item else None
            if not current_item:
                QMessageBox.information(self, "Set Active", "Please select a drawing set.")
                return
            set_id = current_item.data(Qt.UserRole)
            session = get_session()
            from models.drawing_sets import DrawingSet as _DrawingSet
            session.query(_DrawingSet).filter(_DrawingSet.project_id == self.project_id).update({_DrawingSet.is_active: False})
            drawing_set = session.query(_DrawingSet).filter(_DrawingSet.id == set_id).first()
            if drawing_set:
                drawing_set.is_active = True
                session.commit()
                QMessageBox.information(self, "Active Set", f"'{drawing_set.name}' is now the active drawing set.")
                self.refresh_drawing_sets()
            session.close()
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to set active drawing set:\n{str(e)}")

    def compare_drawing_sets(self):
        """Open drawing sets comparison interface"""
        try:
            session = get_session()
            from models.drawing_sets import DrawingSet as _DrawingSet
            from sqlalchemy.orm import selectinload as _selectinload
            drawing_sets = (
                session.query(_DrawingSet)
                .options(_selectinload(_DrawingSet.drawings))
                .filter(_DrawingSet.project_id == self.project_id)
                .all()
            )
            session.close()
            if len(drawing_sets) < 2:
                QMessageBox.information(self, "Compare Sets", "At least two drawing sets are required for comparison.")
                return
            from ui.dialogs.comparison_selection_dialog import ComparisonSelectionDialog
            dialog = ComparisonSelectionDialog(self, drawing_sets)
            if dialog.exec() == QDialog.Accepted:
                base_set_id, compare_set_id = dialog.get_selected_sets()
                comparison_interface = DrawingComparisonInterface(base_set_id, compare_set_id)
                comparison_interface.show()
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to open comparison:\n{str(e)}")

    def manage_drawing_sets(self):
        """Open drawing sets management dialog"""
        try:
            dialog = DrawingSetsDialog(self, self.project_id, mode='manage')
            if dialog.exec() == QDialog.Accepted:
                self.refresh_drawing_sets()
                self.refresh_drawings()
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to open drawing sets management:\n{str(e)}")

    def on_location_selected(self, location_data):
        """Handle location selection from location browser"""
        try:
            element_type = location_data.get('location_type')
            element_id = location_data.get('element_id')

            if element_type == 'space':
                # Open space edit dialog
                self.open_space_by_id(element_id)
            elif element_type == 'hvac_path':
                # Open HVAC path dialog
                self.open_hvac_path_by_id(element_id)

        except Exception as e:
            QMessageBox.warning(self, "Navigation Error", f"Could not navigate to location:\n{e}")

    def open_space_by_id(self, space_id):
        """Open space edit dialog for a specific space ID"""
        try:
            session = get_session()
            space = session.query(Space).filter(Space.id == space_id).first()
            session.close()

            if not space:
                QMessageBox.warning(self, "Not Found", f"Space with ID {space_id} not found.")
                return

            # Import and open space edit dialog
            from ui.dialogs.space_edit_dialog import SpaceEditDialog

            dialog = SpaceEditDialog(self, space)
            dialog.space_updated.connect(self.on_space_updated)
            dialog.finished.connect(lambda: self.on_space_dialog_closed(dialog))

            self.space_edit_dialogs.append(dialog)
            dialog.show()

        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to open space:\n{e}")

    def open_hvac_path_by_id(self, path_id):
        """Open HVAC path dialog for a specific path ID"""
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
            session.close()

            if not path:
                QMessageBox.warning(self, "Not Found", f"HVAC path with ID {path_id} not found.")
                return

            dialog = HVACPathDialog(self, project_id=self.project_id, path=path)
            if dialog.exec() == QDialog.Accepted:
                self.refresh_hvac_paths()
                self.update_analysis_status()
                self.update_space_hvac_paths_table()

        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to open HVAC path:\n{e}")

    def auto_sync_all_locations(self):
        """Auto-sync location bookmarks for all spaces and HVAC paths"""
        try:
            from utils.location_manager import LocationManager
            from PySide6.QtWidgets import QProgressDialog

            # Get all spaces and paths
            session = get_session()
            spaces = session.query(Space).filter(Space.project_id == self.project_id).all()
            paths = session.query(HVACPath).filter(HVACPath.project_id == self.project_id).all()
            session.close()

            total = len(spaces) + len(paths)

            # Progress dialog
            progress = QProgressDialog("Syncing location bookmarks...", "Cancel", 0, total, self)
            progress.setWindowTitle("Auto-Sync Locations")
            progress.setModal(True)
            progress.show()

            synced_count = 0

            # Sync spaces
            for i, space in enumerate(spaces):
                if progress.wasCanceled():
                    break

                progress.setValue(i)
                progress.setLabelText(f"Syncing space: {space.name}...")

                LocationManager.auto_sync_space_locations(space.id)
                synced_count += 1

            # Sync HVAC paths
            for i, path in enumerate(paths):
                if progress.wasCanceled():
                    break

                progress.setValue(len(spaces) + i)
                progress.setLabelText(f"Syncing HVAC path: {path.name}...")

                LocationManager.auto_sync_path_locations(path.id)
                synced_count += 1

            progress.setValue(total)

            # Refresh location browser
            if hasattr(self, 'location_browser'):
                self.location_browser.load_locations()

            QMessageBox.information(
                self,
                "Sync Complete",
                f"Successfully synced {synced_count} location bookmarks."
            )

        except Exception as e:
            QMessageBox.critical(self, "Sync Error", f"Failed to sync locations:\n{e}")