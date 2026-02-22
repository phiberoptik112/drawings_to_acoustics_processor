# Project Settings

Configure project properties and manage drawing sets.

## General Settings

- **Project Name**: Display name for the project
- **Description**: Optional project description
- **Default Scale**: Default scale for new drawings
- **Project Location**: Path for project files

## Drawing Sets

Organize drawings by project phase:
- **SD**: Schematic Design
- **DD**: Design Development  
- **CD**: Construction Documents
- **Final**: As-built / Final

---

## Controls

### project_name_edit
**Project Name**

Enter the project name. This appears in the dashboard title and exports.

### description_edit
**Project Description**

Optional description text. Can include:
- Client name
- Building address
- Project phase

### default_scale_combo
**Default Scale**

Select the default scale for new drawings:
- 1/8" = 1'-0"
- 1/4" = 1'-0"
- 3/8" = 1'-0"
- 1/2" = 1'-0"

### drawing_sets_list
**Drawing Sets List**

Shows all drawing sets in the project.

Each set can contain multiple drawings and represents a project phase or revision.

### add_set_btn
**Add Drawing Set**

Create a new drawing set. Specify:
- Set name
- Phase type
- Whether to make it active

### set_active_btn
**Set Active**

Make the selected drawing set active. The active set is used for comparisons and is highlighted in green.

### delete_set_btn
**Delete Set**

Remove a drawing set. Drawings in the set will be unassigned but not deleted.

### save_btn
**Save Changes**

Save all project settings changes.
