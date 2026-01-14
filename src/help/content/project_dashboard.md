# Project Dashboard

The Project Dashboard is your central hub for managing acoustic analysis projects. From here you can manage drawings, spaces, HVAC paths, and view analysis results.

## Key Features

- **Drawing Sets**: Organize drawings by project phase (SD, DD, CD, Final)
- **Spaces**: Define rooms and their acoustic properties
- **HVAC Paths**: Model mechanical noise pathways
- **Results**: View RT60 and noise analysis results

## Workflow Tips

1. Start by importing PDF drawings
2. Create spaces by drawing rectangles on the PDF
3. Define HVAC paths connecting mechanical equipment to spaces
4. Run calculations to analyze acoustics

---

## Controls

### drawing_sets_list
**Drawing Sets List**

Displays all drawing sets in the project, organized by phase type.

- Double-click a set to manage its drawings
- Green indicator shows the active set
- Use "Set Active" to switch between sets for comparison

### drawings_list
**Drawings List**

Shows all PDF drawings imported into the project.

- Double-click to open in the Drawing Editor
- Import new drawings with "Import Drawing"
- Drawings can be associated with drawing sets

### spaces_list
**Spaces List**

Lists all defined spaces/rooms in the project.

- Green text: Fully analyzed (RT60 + noise)
- Blue text: RT60 calculated only
- Gray text: No calculations yet
- Double-click to edit space properties

### hvac_list
**HVAC Paths List**

Shows all HVAC noise paths in the project.

- Paths connect mechanical sources to receiver spaces
- Each path consists of components and duct segments
- Double-click to edit path configuration

### import_drawing
**Import Drawing Button**

Click to import a PDF drawing file. The drawing will be added to the current project and can be opened in the Drawing Editor.

### edit_receiver_btn
**Edit Space HVAC Receiver**

Opens the receiver analysis dialog for the selected space, showing all HVAC paths that terminate at this space and their combined noise levels.

### library_btn
**Component Library**

Opens the Component Library dialog where you can:
- Manage mechanical units and their noise spectra
- Define silencer products
- Set up acoustic materials
