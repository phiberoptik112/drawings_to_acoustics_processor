# Revised Product Requirements Document (PRD)
## Acoustic Analysis Tool - Project-Based UI System

### Executive Summary
Desktop application built with PyQt5 featuring a project-based workflow that manages multiple drawings, spaces, and acoustic calculations across complex building projects for LEED acoustic certification.

---

## Application Architecture Overview

### Project-Centric Workflow
The application follows a hierarchical project structure:
```
Project
├── Project Settings (name, description, database)
├── Drawings (multiple PDFs - floors, mechanical plans, etc.)
├── Spaces (rooms requiring acoustic analysis)
├── HVAC Paths (mechanical duct routes with properties)
├── Component Library (project-specific HVAC equipment)
└── Calculations (RT60 + background noise per space)
```

---

## User Interface Flow

### 1. Application Launch - Splash Screen
```
┌─────────────────────────────────────────┐
│          Acoustic Analysis Tool         │
│                                         │
│  ┌─────────────────────────────────┐    │
│  │        Recent Projects          │    │
│  │  • Office Building 2024         │    │
│  │  • Hospital Wing Renovation     │    │
│  │  • School Auditorium           │    │
│  └─────────────────────────────────┘    │
│                                         │
│      [New Project]  [Open Project]     │
│           [Import Project]              │
└─────────────────────────────────────────┘
```

**New Project Dialog:**
- Project Name (required)
- Project Description
- Project Location/Path
- Initial settings (default scale, units, etc.)

### 2. Project Dashboard - Main Menu
```
Project: Office Building 2024
┌─────────────────────────────────────────────────────────────┐
│ [File] [Project] [Drawings] [Calculations] [Reports] [Help] │
├─────────────────┬───────────────────┬───────────────────────┤
│   Drawings      │      Spaces       │    Component Library  │
│                 │                   │                       │
│ 📄 Floor 1 Plan │ 🏢 Conference A   │ 🔧 AHU-1 (15 tons)   │
│ 📄 Floor 2 Plan │ 🏢 Office 101     │ 🔧 Silencer-A        │
│ 📄 Mech Plan    │ 🏢 Lobby          │ 🔧 VAV-Box-1         │
│ 📄 Roof Plan    │ 🏢 Break Room     │                       │
│                 │                   │ 🎵 Acoustic Materials│
│ [Import Drawing]│ [New Space]       │ 📋 ACT Ceiling       │
│ [Remove]        │ [Edit Properties] │ 📋 Carpet Tile       │
│                 │ [Duplicate]       │ 📋 Painted Drywall   │
│                 │                   │                       │
│                 │ HVAC Paths:       │ [Add Component]       │
│                 │ 🔀 Supply-101     │ [Edit Library]        │
│                 │ 🔀 Return-101     │                       │
│                 │ 🔀 Supply-Conf    │                       │
│                 │                   │                       │
│                 │ Analysis Status:  │                       │
│                 │ ✅ Conference A   │                       │
│                 │ ⏳ Office 101     │                       │
│                 │ ❌ Lobby          │                       │
└─────────────────┴───────────────────┴───────────────────────┤
│ Ready | Project: Office Building 2024 | 4 drawings, 12 spaces, 8 paths │
└─────────────────────────────────────────────────────────────┘
```

### 3. Drawing Analysis Interface
**Accessed by double-clicking a drawing from the dashboard**

```
Drawing: Mechanical Plan - Office Building 2024
┌────────────────────────────────────────────────────────────┐
│ [←Back] [File] [Edit] [View] [Tools] [Calculate]           │
│ [📁] [💾] [🔍+] [🔍-] [📏] [✏️] [👆] [🔲] [🔗]            │
├──────────────┬─────────────────────────────────────────────┤
│ Project      │ Central Drawing Area                        │
│ Elements     │                                             │
│              │ ┌─────────────────────────────────────────┐ │
│ Drawing Mode │ │                                         │ │
│ ◉ HVAC Path  │ │                                         │ │
│ ○ Room Area  │ │        PDF Viewer                       │ │
│              │ │        + Drawing Overlay                │ │
│ Current Tool │ │                                         │ │
│ ◉ Component  │ │   [AHU]────────[VAV]──┐                │ │
│ ○ Segment    │ │                       │                 │ │
│ ○ Rectangle  │ │                  [DIFF] ← Office 101    │ │
│              │ │                                         │ │
│ Spaces       │ └─────────────────────────────────────────┘ │
│ ┌──────────┐ │                                             │
│ │Conf A    │ │                                             │
│ │Office101 │ │                                             │
│ └──────────┘ │                                             │
│              │                                             │
│ HVAC Paths   │                                             │
│ ┌──────────┐ │                                             │
│ │Supply-101│ │                                             │
│ │Return-101│ │                                             │
│ │Supply-Cnf│ │                                             │
│ └──────────┘ │                                             │
│              │                                             │
│ [New Path]   │                                             │
│ [New Room]   │                                             │
│              │                                             │
│ Properties   │                                             │
│ ┌──────────┐ │                                             │
│ │Segment:3 │ │                                             │
│ │Length:25'│ │                                             │
│ │Size:12x8 │ │                                             │
│ │From:VAV-1│ │                                             │
│ │To:Diff-1 │ │                                             │
│ └──────────┘ │                                             │
└──────────────┴─────────────────────────────────────────────┤
│ Scale 1:100 | Drawing: MechPlan.pdf | Tool: Segment        │
└────────────────────────────────────────────────────────────┘
```

---

## Drawing Interaction Methods

### HVAC Path Drawing - Segment-Based Approach

**Component-to-Component Drawing Workflow:**
1. **Component Placement**: Click to place HVAC components (AHU, VAV, Diffuser, etc.)
2. **Segment Drawing**: Click between components to create duct segments
3. **Automatic Calculation**: Each segment calculates length based on drawing scale
4. **Path Assembly**: Multiple segments form complete paths from source to terminal

**Visual Representation:**
```
Drawing Canvas Example:
[AHU-1] ──── Segment 1 (45') ──── [VAV-Box] ──── Segment 2 (25') ──── [Diffuser]
   │                                   │                                   │
Component 1                      Component 2                        Component 3
```

**Segment Properties Interface:**
```
HVAC Segment Properties: Segment 2
┌─────────────────────────────────────────┐
│ Segment Information                     │
│ From Component: VAV-Box-1               │
│ To Component: Diffuser-101              │
│ Length: 25.3 ft (from drawing scale)    │
│                                         │
│ Duct Properties                         │
│ Duct Size: [12" x 8" ▼]                │
│ Duct Type: [Rectangular ▼]             │
│ Insulation: [1" Fiberglass ▼]          │
│                                         │
│ Fittings/Components in Segment          │
│ ┌─────────────────────────────────────┐ │
│ │ 90° Elbow      | 15.2 ft | +3 dB   │ │
│ │ Tee Branch     | 22.1 ft | +2 dB   │ │
│ └─────────────────────────────────────┘ │
│                                         │
│ [Add Fitting] [Remove] [Edit]           │
│                                         │
│ Segment Loss: -3.2 dB                  │
│ Segment Addition: +5 dB (fittings)     │
│                                         │
│ [Calculate] [Save] [Cancel]             │
└─────────────────────────────────────────┘
```

### Room Volume Drawing - Rectangle-Based Approach

**Room Boundary Drawing Workflow:**
1. **Rectangle Tool**: Click and drag to draw room boundaries as rectangles
2. **Scale-Based Area**: Area calculated automatically from drawing scale
3. **Height Input**: Manual input for ceiling height
4. **Volume Calculation**: Area × Height = Room Volume

**Room Properties Interface:**
```
Room Properties: Conference Room A
┌─────────────────────────────────────────┐
│ Geometry (from drawing)                 │
│ Rectangle Dimensions: 25' × 17'         │
│ Floor Area: 425 sf (calculated)         │
│                                         │
│ Height Input                            │
│ Ceiling Height: [9.0 ▼] ft             │
│ Volume: 3,825 cf (calculated)           │
│                                         │
│ Surface Areas (calculated)              │
│ Floor: 425 sf                          │
│ Ceiling: 425 sf                        │
│ Walls: 756 sf (perimeter × height)     │
│ Total Surface: 1,606 sf                │
│                                         │
│ Surface Materials                       │
│ Ceiling: [ACT Standard ▼] 425 sf        │
│ Walls: [Painted Drywall ▼] 756 sf       │
│ Floor: [Carpet Tile ▼] 425 sf           │
│                                         │
│ Target RT60: [0.8 ▼] seconds            │
│ Calculated RT60: 1.2 seconds ❌         │
│                                         │
│ [Recalculate] [Material Library]        │
└─────────────────────────────────────────┘
```

### Drawing Tools & Visual Feedback

**HVAC Path Mode Tools:**
- **Component Tool**: Place equipment icons (AHU, VAV, Diffuser, etc.)
- **Segment Tool**: Draw lines between components
- **Selection Tool**: Click to select and edit components/segments

**Room Volume Mode Tools:**
- **Rectangle Tool**: Click-drag to define room boundaries
- **Selection Tool**: Click to select and edit rooms
- **Dimension Tool**: Show measurements on drawing

**Visual Elements:**
```
HVAC Path Visualization:
🔧 [AHU-1] ═══════════════ 45.2' ═══════════════ 🔧 [VAV-1]
                     Segment 1 (12"×8")

Room Visualization:
┌─────────────── 25' ──────────────┐
│                                  │ 17'
│         Conference Room A        │
│         425 sf × 9' = 3,825 cf   │
└──────────────────────────────────┘
```

---

## Enhanced Database Structure

### Segment-Based HVAC Paths
```sql
-- HVAC Components (equipment placed on drawing)
CREATE TABLE hvac_components (
    id INTEGER PRIMARY KEY,
    project_id INTEGER,
    drawing_id INTEGER,
    name TEXT NOT NULL,
    component_type TEXT, -- 'ahu', 'vav', 'diffuser', 'grille', etc.
    x_position REAL, -- Drawing coordinates
    y_position REAL,
    noise_level REAL, -- Base noise for equipment
    FOREIGN KEY (project_id) REFERENCES projects (id),
    FOREIGN KEY (drawing_id) REFERENCES drawings (id)
);

-- HVAC Segments (connections between components)
CREATE TABLE hvac_segments (
    id INTEGER PRIMARY KEY,
    hvac_path_id INTEGER,
    from_component_id INTEGER,
    to_component_id INTEGER,
    length REAL, -- Calculated from drawing scale
    duct_width REAL,
    duct_height REAL,
    duct_shape TEXT,
    segment_order INTEGER, -- Order in path (1, 2, 3...)
    FOREIGN KEY (hvac_path_id) REFERENCES hvac_paths (id),
    FOREIGN KEY (from_component_id) REFERENCES hvac_components (id),
    FOREIGN KEY (to_component_id) REFERENCES hvac_components (id)
);

-- Fittings within segments
CREATE TABLE segment_fittings (
    id INTEGER PRIMARY KEY,
    segment_id INTEGER,
    fitting_type TEXT, -- 'elbow', 'tee', 'reducer', etc.
    position_on_segment REAL, -- Distance from start of segment
    noise_adjustment REAL, -- +/- dB contribution
    FOREIGN KEY (segment_id) REFERENCES hvac_segments (id)
);

-- Room boundaries (rectangles)
CREATE TABLE room_boundaries (
    id INTEGER PRIMARY KEY,
    space_id INTEGER,
    drawing_id INTEGER,
    x_position REAL, -- Rectangle corner coordinates
    y_position REAL,
    width REAL, -- Drawing units
    height REAL, -- Drawing units
    calculated_area REAL, -- sf based on scale
    FOREIGN KEY (space_id) REFERENCES spaces (id),
    FOREIGN KEY (drawing_id) REFERENCES drawings (id)
);

-- Enhanced spaces table
ALTER TABLE spaces ADD COLUMN ceiling_height REAL; -- ft
ALTER TABLE spaces ADD COLUMN calculated_volume REAL; -- cf
ALTER TABLE spaces ADD COLUMN wall_area REAL; -- calculated from perimeter × height
```

---

## Calculation Engines Priority

### Phase 1: Room Acoustics (RT60)
**Implementation Priority:**
1. **Rectangle Area Calculator**: Area from drawn rectangles and drawing scale
2. **Surface Area Calculator**: Floor, ceiling, walls from dimensions and height
3. **Material Database**: Surface materials with absorption coefficients
4. **Surface Area Assignment**: Material selection per surface type
5. **RT60 Calculator**: Sabine/Eyring formula implementation
6. **Results Display**: Simple tabular output

### Phase 2: Mechanical Background Noise
**Implementation Priority:**
1. **Component Placement**: Equipment icons on drawings
2. **Segment Drawing**: Lines between components with length calculation
3. **Path Assembly**: Chain segments into complete paths
4. **Segment Properties**: Duct size, fittings, and loss calculations
5. **Path Noise Calculator**: 
   - Starting equipment noise
   - Segment-by-segment attenuation
   - Fitting additions
   - Terminal adjustments
6. **NC Calculation**: Convert final dB(A) to NC rating

**Path Calculation Logic (Segment-Based):**
```
Equipment Starting Level (Component 1)
Segment 1: - Distance Loss - Duct Loss + Fitting Additions
Segment 2: - Distance Loss - Duct Loss + Fitting Additions
...
Segment N: - Distance Loss - Duct Loss + Terminal Addition
= Final NC Level at Space
```

---

## Enhanced Drawing Interface Features

### Scale-Accurate Measurements
**Scale Input Interface:**
```
Drawing Scale Settings
┌─────────────────────────────────────────┐
│ Current Drawing: Mechanical Plan        │
│                                         │
│ Scale Input Method:                     │
│ ◉ Standard Scale                        │
│   Scale: [1:100 ▼]                     │
│                                         │
│ ○ Custom Scale                          │
│   Drawing Distance: [2.5] inches        │
│   Actual Distance: [25] feet            │
│                                         │
│ ○ Reference Line                        │
│   [Draw reference line on drawing]      │
│   Actual Length: [50] feet              │
│                                         │
│ Current Scale: 1" = 10'                 │
│ [Apply] [Cancel]                        │
└─────────────────────────────────────────┘
```

### Real-Time Feedback
- **Length Display**: Show segment lengths as you draw
- **Area Display**: Show room area as you draw rectangles
- **Snap-to-Grid**: Optional grid overlay for alignment
- **Measurement Overlay**: Temporary dimension lines

---

## Development Milestones - Updated

### Milestone 1: Project System (Week 1-2)
- Splash screen and project creation
- Project dashboard interface
- SQLite database setup with segment-based tables
- Basic project save/load

### Milestone 2: Drawing Management & Scale (Week 3-4)
- Drawing import and display in dashboard
- PDF viewer integration with scale system
- Scale input interface and coordinate mapping
- Drawing-to-project association

### Milestone 3: Room Rectangle Drawing (Week 5-6)
- Rectangle drawing tool for room boundaries
- Area calculation from drawing scale
- Height input and volume calculation
- Room properties interface

### Milestone 4: HVAC Component & Segment System (Week 7-8)
- Component placement tools
- Segment drawing between components
- Length calculation from drawing scale
- Segment properties interface

### Milestone 5: Path Assembly & Properties (Week 9-10)
- Multi-segment path creation
- Path-to-space linking
- Component and fitting libraries
- Segment fitting assignment

### Milestone 6: RT60 Calculator (Week 11-12)
- Surface area calculations (floor, ceiling, walls)
- Material database and assignment interface
- RT60 calculation engine
- Results display and validation

### Milestone 7: Mechanical Noise Calculator (Week 13-14)
- Segment-based noise calculation engine
- Equipment and fitting noise contributions
- Path loss calculations
- NC rating conversion

### Milestone 8: Integrated Results (Week 15-16)
- Combined RT60 + mechanical noise display
- Project-wide results summary
- Export functionality
- Performance optimization

This segment-based approach for HVAC paths and rectangle-based room definition provides more accurate and intuitive drawing interactions while maintaining scale accuracy for reliable calculations.