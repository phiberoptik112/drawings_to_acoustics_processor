"""
Location Browser Widget - Displays bookmarked locations for spaces and HVAC paths
"""

from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QTreeWidget,
                             QTreeWidgetItem, QPushButton, QLabel, QComboBox,
                             QGroupBox, QMessageBox, QMenu)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont, QIcon, QColor

from models import get_session
from models.drawing_sets import DrawingSet
from utils.location_manager import LocationManager


class LocationBrowserWidget(QWidget):
    """Widget for browsing and navigating to bookmarked locations"""

    # Signals
    location_selected = Signal(dict)  # Emits location data
    navigate_to_location = Signal(int, int, int)  # drawing_id, page, element_type_and_id

    def __init__(self, project_id, parent=None):
        super().__init__(parent)
        self.project_id = project_id
        self.init_ui()
        self.load_locations()

    def init_ui(self):
        """Initialize the user interface"""
        layout = QVBoxLayout()

        # Header
        header_layout = QHBoxLayout()
        header_label = QLabel("📍 Drawing Locations")
        header_label.setFont(QFont("Arial", 11, QFont.Bold))
        header_layout.addWidget(header_label)

        # Refresh button
        self.refresh_btn = QPushButton("⟳")
        self.refresh_btn.setMaximumWidth(30)
        self.refresh_btn.setToolTip("Refresh locations")
        self.refresh_btn.clicked.connect(self.load_locations)
        header_layout.addWidget(self.refresh_btn)

        header_layout.addStretch()
        layout.addLayout(header_layout)

        # Filter by drawing set
        filter_layout = QHBoxLayout()
        filter_layout.addWidget(QLabel("Filter:"))

        self.filter_combo = QComboBox()
        self.filter_combo.currentIndexChanged.connect(self.on_filter_changed)
        filter_layout.addWidget(self.filter_combo, 1)

        layout.addLayout(filter_layout)

        # Tree widget showing locations
        self.tree = QTreeWidget()
        self.tree.setHeaderLabels(["Location", "Count"])
        self.tree.setAlternatingRowColors(True)
        self.tree.itemDoubleClicked.connect(self.on_item_double_clicked)
        self.tree.setContextMenuPolicy(Qt.CustomContextMenu)
        self.tree.customContextMenuRequested.connect(self.show_context_menu)

        # Set column widths
        self.tree.setColumnWidth(0, 300)

        layout.addWidget(self.tree)

        # Summary label
        self.summary_label = QLabel("No locations")
        self.summary_label.setStyleSheet("color: #888; font-style: italic;")
        layout.addWidget(self.summary_label)

        self.setLayout(layout)

    def load_locations(self):
        """Load all locations for the project"""
        try:
            # Load drawing sets for filter
            session = get_session()
            drawing_sets = (
                session.query(DrawingSet)
                .filter(DrawingSet.project_id == self.project_id)
                .order_by(DrawingSet.name)
                .all()
            )

            self.filter_combo.clear()
            self.filter_combo.addItem("All Drawing Sets", None)
            for ds in drawing_sets:
                self.filter_combo.addItem(f"{ds.name} ({ds.phase_type})", ds.id)

            session.close()

            # Load locations
            self.refresh_locations()

        except Exception as e:
            QMessageBox.warning(self, "Load Error", f"Failed to load locations:\n{e}")

    def refresh_locations(self):
        """Refresh the locations display"""
        self.tree.clear()

        try:
            # Get filter
            filter_set_id = self.filter_combo.currentData()

            locations = LocationManager.get_all_locations_for_project(self.project_id)

            # Group by drawing set -> drawing -> page
            grouped = {}
            total_spaces = 0
            total_paths = 0

            for loc in locations:
                # Apply filter
                if filter_set_id is not None and loc.drawing_set_id != filter_set_id:
                    continue

                # Count totals
                if loc.location_type.value == 'space':
                    total_spaces += 1
                elif loc.location_type.value == 'hvac_path':
                    total_paths += 1

                # Group by drawing set
                set_key = loc.drawing_set_id or 'no_set'
                if set_key not in grouped:
                    set_name = "No Drawing Set"
                    if loc.drawing_set and hasattr(loc.drawing_set, 'name'):
                        set_name = loc.drawing_set.name
                        if hasattr(loc.drawing_set, 'phase_type') and loc.drawing_set.phase_type:
                            set_name += f" ({loc.drawing_set.phase_type})"

                    grouped[set_key] = {
                        'name': set_name,
                        'id': loc.drawing_set_id,
                        'drawings': {}
                    }

                # Group by drawing
                drawing_key = loc.drawing_id
                if drawing_key not in grouped[set_key]['drawings']:
                    drawing_name = "Unknown Drawing"
                    if loc.drawing and hasattr(loc.drawing, 'name'):
                        drawing_name = loc.drawing.name

                    grouped[set_key]['drawings'][drawing_key] = {
                        'name': drawing_name,
                        'id': loc.drawing_id,
                        'pages': {}
                    }

                # Group by page
                page_key = loc.page_number or 1
                if page_key not in grouped[set_key]['drawings'][drawing_key]['pages']:
                    grouped[set_key]['drawings'][drawing_key]['pages'][page_key] = {
                        'number': page_key,
                        'spaces': [],
                        'hvac_paths': []
                    }

                # Add to appropriate list
                if loc.location_type.value == 'space':
                    grouped[set_key]['drawings'][drawing_key]['pages'][page_key]['spaces'].append(loc)
                elif loc.location_type.value == 'hvac_path':
                    grouped[set_key]['drawings'][drawing_key]['pages'][page_key]['hvac_paths'].append(loc)

            # Build tree
            for set_key in sorted(grouped.keys(), key=lambda k: grouped[k]['name']):
                set_data = grouped[set_key]

                # Drawing set item
                set_item = QTreeWidgetItem(self.tree)
                set_item.setText(0, f"📁 {set_data['name']}")

                total_in_set = sum(
                    len(page['spaces']) + len(page['hvac_paths'])
                    for drawing in set_data['drawings'].values()
                    for page in drawing['pages'].values()
                )
                set_item.setText(1, str(total_in_set))
                set_item.setFont(0, QFont("Arial", 10, QFont.Bold))
                set_item.setExpanded(True)

                # Drawing items
                for drawing_key in sorted(set_data['drawings'].keys()):
                    drawing_data = set_data['drawings'][drawing_key]

                    drawing_item = QTreeWidgetItem(set_item)
                    drawing_item.setText(0, f"  📄 {drawing_data['name']}")

                    total_in_drawing = sum(
                        len(page['spaces']) + len(page['hvac_paths'])
                        for page in drawing_data['pages'].values()
                    )
                    drawing_item.setText(1, str(total_in_drawing))

                    # Page items
                    for page_key in sorted(drawing_data['pages'].keys()):
                        page_data = drawing_data['pages'][page_key]

                        page_label = f"Page {page_data['number']}" if page_data['number'] > 1 else "Page 1"
                        page_item = QTreeWidgetItem(drawing_item)
                        page_item.setText(0, f"    📋 {page_label}")
                        page_item.setText(1, str(len(page_data['spaces']) + len(page_data['hvac_paths'])))

                        # Space items
                        for space_loc in page_data['spaces']:
                            space_item = QTreeWidgetItem(page_item)
                            space_item.setText(0, f"      🏠 {space_loc.element_name or 'Unnamed Space'}")
                            space_item.setData(0, Qt.UserRole, space_loc.to_dict())
                            space_item.setForeground(0, QColor("#90CAF9"))  # Light blue

                        # HVAC path items
                        for path_loc in page_data['hvac_paths']:
                            path_item = QTreeWidgetItem(page_item)
                            path_item.setText(0, f"      🔀 {path_loc.element_name or 'Unnamed Path'}")
                            path_item.setData(0, Qt.UserRole, path_loc.to_dict())
                            path_item.setForeground(0, QColor("#A5D6A7"))  # Light green

            # Update summary
            self.summary_label.setText(
                f"{total_spaces} space{'s' if total_spaces != 1 else ''}, "
                f"{total_paths} HVAC path{'s' if total_paths != 1 else ''}"
            )

        except Exception as e:
            QMessageBox.warning(self, "Refresh Error", f"Failed to refresh locations:\n{e}")

    def on_filter_changed(self, index):
        """Handle filter change"""
        self.refresh_locations()

    def on_item_double_clicked(self, item, column):
        """Handle double-click on tree item"""
        location_data = item.data(0, Qt.UserRole)
        if location_data:
            self.location_selected.emit(location_data)

            # Could emit navigate signal here if we have drawing interface
            # self.navigate_to_location.emit(
            #     location_data['drawing_id'],
            #     location_data['page_number'],
            #     location_data['element_id']
            # )

    def show_context_menu(self, position):
        """Show context menu for tree items"""
        item = self.tree.itemAt(position)
        if not item:
            return

        location_data = item.data(0, Qt.UserRole)
        if not location_data:
            return

        menu = QMenu(self)

        # View details action
        view_action = menu.addAction("📋 View Details")
        view_action.triggered.connect(lambda: self.show_location_details(location_data))

        # Open in drawing editor action
        open_action = menu.addAction("🖼️ Open in Drawing Editor")
        open_action.triggered.connect(lambda: self.open_in_editor(location_data))

        menu.exec_(self.tree.viewport().mapToGlobal(position))

    def show_location_details(self, location_data):
        """Show detailed information about a location"""
        msg = f"<h3>{location_data['element_name']}</h3>"
        msg += f"<p><b>Type:</b> {location_data['location_type'].replace('_', ' ').title()}<br>"
        msg += f"<b>Drawing:</b> Drawing ID {location_data['drawing_id']}<br>"
        msg += f"<b>Page:</b> {location_data['page_number']}<br>"

        if location_data.get('drawing_set_id'):
            msg += f"<b>Drawing Set:</b> Set ID {location_data['drawing_set_id']}<br>"

        if location_data.get('has_bbox'):
            msg += f"<b>Coordinates:</b> ({location_data['center_x']:.1f}, {location_data['center_y']:.1f})"

        msg += "</p>"

        QMessageBox.information(self, "Location Details", msg)

    def open_in_editor(self, location_data):
        """Open the drawing editor at this location"""
        # This would need to be connected to the parent dashboard's drawing interface
        QMessageBox.information(
            self,
            "Open in Editor",
            f"Opening {location_data['element_name']} in drawing editor...\n\n"
            "(This would navigate to the drawing and highlight the element)"
        )

    def get_selected_location(self):
        """Get the currently selected location data"""
        current_item = self.tree.currentItem()
        if current_item:
            return current_item.data(0, Qt.UserRole)
        return None
