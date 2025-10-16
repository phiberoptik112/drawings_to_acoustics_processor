# Project Settings Dialog - UI Guide

## Dialog Overview

```
┌────────────────────────────────────────────────────────────────────┐
│ Project Settings                                          [×]        │
├────────────────────────────────────────────────────────────────────┤
│ ┌─────────────────────────────────────────────────────────────────┐│
│ │ [ General Settings ] [ Drawing Sets ]                           ││
│ └─────────────────────────────────────────────────────────────────┘│
│                                                                      │
│  Tab content appears here                                           │
│                                                                      │
│                                                                      │
│                                                                      │
│                                                                      │
│                                                                      │
│                                                                      │
│                                                                      │
│                                                                      │
│                                                           [Save Changes] [Cancel] │
└────────────────────────────────────────────────────────────────────┘
```

## Tab 1: General Settings

```
┌────────────────────────────────────────────────────────────────────┐
│ [ General Settings ] [ Drawing Sets ]                               │
├────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  Project Name:        [Office Building 2024___________________]     │
│                                                                      │
│  Description:         ┌───────────────────────────────────────┐    │
│                       │Acoustic analysis for new office       │    │
│                       │building including RT60 and HVAC noise │    │
│                       └───────────────────────────────────────┘    │
│                                                                      │
│  Location:            /Users/username/Documents/AcousticAnalysis    │
│                       (Read only - set during project creation)     │
│                                                                      │
│  Default Scale:       [1:100                           ▼]           │
│                                                                      │
│  Default Units:       [feet                            ▼]           │
│                                                                      │
│  ┌─ Project Statistics ────────────────────────────────────────┐   │
│  │                                                               │   │
│  │  • 4 drawing(s)                                              │   │
│  │  • 12 space(s)                                               │   │
│  │  • 8 HVAC path(s)                                            │   │
│  │  • 15 HVAC component(s)                                      │   │
│  │  • 3 drawing set(s)                                          │   │
│  │                                                               │   │
│  └───────────────────────────────────────────────────────────────┘ │
│                                                                      │
│                                                   [Save Changes] [Cancel]
└────────────────────────────────────────────────────────────────────┘
```

### General Settings - Field Descriptions

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| Project Name | Text Input | Yes | The name of your project. Used in window titles and exports. |
| Description | Multi-line Text | No | Optional description of the project scope, purpose, or notes. |
| Location | Label (Read-only) | - | File system path where project database is stored. Set at creation. |
| Default Scale | Dropdown | Yes | Default scale for imported drawings (1:50 to 1:1000). |
| Default Units | Dropdown | Yes | Default measurement units (feet or meters). |

## Tab 2: Drawing Sets

```
┌────────────────────────────────────────────────────────────────────┐
│ [ General Settings ] [ Drawing Sets ]                               │
├────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  Drawing sets help organize drawings by design phase (DD, SD, CD...)│
│                                                                      │
│  ┌──────────────────────────────────────────────────────────────┐  │
│  │ 🟢 🟦 Design Development (DD) - 3 drawings                    │  │
│  │ ⚪ 🟨 Schematic Design (SD) - 2 drawings                      │  │
│  │ ⚪ 🟥 Construction Documents (CD) - 4 drawings                │  │
│  │ ⚪ 🟩 Final - As Built (Final) - 0 drawings                   │  │
│  └──────────────────────────────────────────────────────────────┘  │
│                                                                      │
│  [Add Drawing Set] [Edit Set] [Remove Set] [Set as Active]         │
│                                                                      │
│  ┌─ Drawings in Selected Set ────────────────────────────────────┐ │
│  │ Drawing Name      │ Scale  │ File Path                        │ │
│  │─────────────────────────────────────────────────────────────│ │
│  │ Floor 1 Plan      │ 1:100  │ floor1_plan.pdf                 │ │
│  │ Floor 2 Plan      │ 1:100  │ floor2_plan.pdf                 │ │
│  │ Mechanical Plan   │ 1:200  │ mech_plan.pdf                   │ │
│  └──────────────────────────────────────────────────────────────┘ │
│                                                                      │
│                                                   [Save Changes] [Cancel]
└────────────────────────────────────────────────────────────────────┘
```

### Drawing Sets - Visual Indicators

#### Status Indicators
- 🟢 **Green Circle**: Active drawing set (current working set)
- ⚪ **White Circle**: Inactive drawing set

#### Phase Type Icons
- 🟦 **Blue Square**: DD (Design Development)
- 🟨 **Yellow Square**: SD (Schematic Design)
- 🟥 **Red Square**: CD (Construction Documents)
- 🟩 **Green Square**: Final (As-Built)
- ⚫ **Black Circle**: Legacy (archived)
- ⚪ **White Circle**: Other

### Drawing Sets - Operations

#### Add Drawing Set
```
┌─────────────────────────────────────────────────┐
│ Add Drawing Set                        [×]       │
├─────────────────────────────────────────────────┤
│                                                  │
│  Set Name:      [DD - Revision 3____________]   │
│                                                  │
│  Phase Type:    [DD                       ▼]    │
│                                                  │
│  Description:   ┌────────────────────────┐      │
│                 │Updated plans with      │      │
│                 │revised HVAC layout     │      │
│                 └────────────────────────┘      │
│                                                  │
│  ☐ Set as active drawing set                    │
│                                                  │
│                           [Create] [Cancel]     │
└─────────────────────────────────────────────────┘
```

#### Edit Drawing Set
```
┌─────────────────────────────────────────────────┐
│ Edit Drawing Set                       [×]       │
├─────────────────────────────────────────────────┤
│                                                  │
│  Set Name:      [Design Development_________]   │
│                                                  │
│  Phase Type:    [DD                       ▼]    │
│                                                  │
│  Description:   ┌────────────────────────┐      │
│                 │Design development      │      │
│                 │phase drawings          │      │
│                 └────────────────────────┘      │
│                                                  │
│  ☑ Set as active drawing set                    │
│                                                  │
│                             [Save] [Cancel]     │
└─────────────────────────────────────────────────┘
```

#### Remove Confirmation
```
┌─────────────────────────────────────────────────┐
│ Confirm Removal                                  │
├─────────────────────────────────────────────────┤
│                                                  │
│  Remove drawing set 'Design Development'?        │
│                                                  │
│  This set contains 3 drawing(s).                │
│  The drawings will NOT be deleted, only         │
│  unassigned from this set.                      │
│                                                  │
│                             [Yes] [No]          │
└─────────────────────────────────────────────────┘
```

## Workflow Examples

### Workflow 1: Rename Project
1. Click **Project** → **Project Settings**
2. In General Settings tab, modify **Project Name** field
3. Click **Save Changes**
4. Dashboard window title updates automatically

### Workflow 2: Change Default Scale
1. Open **Project Settings**
2. In General Settings tab, select new **Default Scale** from dropdown
3. Click **Save Changes**
4. Future imported drawings will use this scale

### Workflow 3: Create New Drawing Set
1. Open **Project Settings**
2. Switch to **Drawing Sets** tab
3. Click **Add Drawing Set** button
4. Fill in:
   - Name: "Construction Documents - Rev 1"
   - Phase Type: "CD"
   - Description: (optional)
   - Check "Set as active" if this should be working set
5. Click **Create**
6. New set appears in list

### Workflow 4: Mark Different Set as Active
1. Open **Project Settings**
2. Switch to **Drawing Sets** tab
3. Click on desired set in list
4. Click **Set as Active** button
5. Green indicator moves to selected set
6. Click **Save Changes**

### Workflow 5: View Drawing Set Contents
1. Open **Project Settings**
2. Switch to **Drawing Sets** tab
3. Click on a set in the list
4. Bottom table shows all drawings assigned to that set
5. View name, scale, and file path

### Workflow 6: Remove Old Drawing Set
1. Open **Project Settings**
2. Switch to **Drawing Sets** tab
3. Select obsolete set from list
4. Click **Remove Set** button
5. Confirm removal in dialog
6. Set removed; drawings remain but are unassigned

## Keyboard Shortcuts

| Shortcut | Action |
|----------|--------|
| Enter | Save Changes (when Save button has focus) |
| Esc | Cancel and close dialog |
| Tab | Navigate between fields |
| Ctrl+Tab | Switch between tabs |

## Best Practices

### Project Naming
- Use descriptive names: "Office Building 2024" not "Project1"
- Include client or location if managing multiple projects
- Avoid special characters that might cause file system issues

### Description Usage
- Document project scope and goals
- Note any special requirements or considerations
- Include client contact information if needed

### Scale Settings
- Set default scale to most common drawing scale
- Can be overridden per drawing after import
- Affects real-world dimension calculations

### Drawing Set Organization
- Create sets for each design phase (DD, SD, CD, Final)
- Only one set should be active at a time
- Use descriptive names with revision numbers
- Add descriptions to track changes between sets

### Active Set Management
- Keep most current set as active
- Deactivate obsolete sets rather than deleting them
- Use "Legacy" phase type for archived sets

## Validation and Error Handling

### Field Validation
- **Project Name**: Required field, cannot be empty
- **Phase Type**: Must select from predefined options
- **Drawing Set Name**: Required when creating/editing sets

### Error Messages

#### Empty Project Name
```
┌─────────────────────────────────────┐
│ Validation Error                     │
├─────────────────────────────────────┤
│ Project name is required.            │
│                                      │
│                  [OK]                │
└─────────────────────────────────────┘
```

#### Database Error
```
┌─────────────────────────────────────┐
│ Error                                │
├─────────────────────────────────────┤
│ Failed to save project settings:     │
│ Database connection error            │
│                                      │
│                  [OK]                │
└─────────────────────────────────────┘
```

### Success Messages

#### Settings Saved
```
┌─────────────────────────────────────┐
│ Success                              │
├─────────────────────────────────────┤
│ Project settings saved successfully. │
│                                      │
│                  [OK]                │
└─────────────────────────────────────┘
```

#### Drawing Set Created
```
┌─────────────────────────────────────┐
│ Success                              │
├─────────────────────────────────────┤
│ Drawing set 'DD - Rev 3' created    │
│ successfully.                        │
│                                      │
│                  [OK]                │
└─────────────────────────────────────┘
```

## Technical Notes

### Data Persistence
- All changes saved immediately to database on "Save Changes"
- Cancel discards all changes, even drawing set modifications
- No auto-save - must explicitly save

### Active Set Behavior
- Only one set can be active at a time
- Setting a set as active automatically deactivates others
- Active status persists across application sessions

### Drawing Assignment
- Drawings can belong to zero or one drawing set
- Removing a set unassigns its drawings (doesn't delete them)
- Unassigned drawings remain in project

### UI Updates
- Dashboard automatically refreshes after settings save
- Window title updates to reflect new project name
- Drawing set changes visible in dashboard's "Drawing Sets" tab

## Accessibility

- All controls keyboard accessible
- Tab order logical (top to bottom, left to right)
- Clear focus indicators
- Descriptive labels for screen readers
- Color coding supplemented with icons/text

## Troubleshooting

### Dialog Won't Open
- Check console for error messages
- Verify project_id is valid
- Ensure database connection is working

### Changes Not Saving
- Check for validation errors
- Verify write permissions on database file
- Look for error messages in dialog

### Drawing Sets Not Loading
- Verify database schema includes drawing_sets table
- Check for database migration issues
- Ensure proper relationships configured

### Active Set Not Updating
- Refresh dashboard after making changes
- Check database for is_active flag
- Verify only one set has is_active=True

