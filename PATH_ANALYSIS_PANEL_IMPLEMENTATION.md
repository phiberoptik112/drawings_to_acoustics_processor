# Path Analysis Panel Implementation

## Overview

This implementation adds a new **Path Analysis Panel** to the Drawing Interface that displays HVAC path calculations alongside the drawing view, creating a visual connection between the physical path on the drawing and its acoustic calculations.

## New Files Created

### 1. `src/ui/widgets/path_element_card.py`
Individual card widgets for displaying path elements:
- **PathElementCard**: Clickable card showing element name, noise level, attenuation, and NC rating
- **PathArrow**: Simple arrow connector between cards
- **PathResultsSummary**: Summary widget showing overall path results

### 2. `src/ui/widgets/path_analysis_panel.py`
Main panel widget containing:
- Path selector dropdown
- Scrollable flow diagram of path elements
- Results summary at bottom
- Recalculate and export buttons

## Modified Files

### 1. `src/ui/drawing_interface.py`
- Added PathAnalysisPanel as fourth splitter panel (tools | drawing | analysis | help)
- Added menu item "View > Toggle Analysis Panel"
- Connected bidirectional signals for hover highlighting
- Added methods for:
  - `toggle_analysis_panel()` - Show/hide the panel
  - `show_path_in_analysis_panel(path_id)` - Display specific path
  - `highlight_element_on_drawing()` - Highlight from panel hover
  - `on_drawing_element_hovered()` - Handle drawing hover → panel

### 2. `src/drawing/drawing_overlay.py`
- Added `element_hovered` and `element_unhovered` signals
- Added element highlighting state variables
- Added methods:
  - `set_highlighted_element(id, type)` - Set highlight from analysis panel
  - `clear_highlighted_element()` - Clear highlight
  - `set_selected_element(id, type)` - Set selection from analysis panel
  - `_is_element_highlighted()` / `_is_element_selected()` - Check state
- Modified `draw_components()` and `draw_segments()` to apply highlight/selection styling
- Added hover detection in `mouseMoveEvent()`

### 3. `src/ui/widgets/__init__.py`
- Added exports for new widgets

## UI Layout

```
┌──────────────────────────────────────────────────────────────────────┐
│ Toolbar  |  View > Toggle Analysis Panel                             │
├──────────┬────────────────────────────────────┬─────────────────────┤
│  Tools   │           Drawing                   │  Analysis Panel    │
│  Panel   │           PDF + Overlay             │  (collapsible)     │
│  280px   │           750px                     │  400px             │
│          │                                     ├───────────────────┤
│  Spaces  │                                     │ Path: [selector]  │
│  ──────  │      Components & Segments          │                   │
│  Paths   │      visually rendered              │  ┌─────────────┐  │
│  ──────  │            ↕                        │  │ Source Card │  │
│  Elements│      HOVER LINKED                   │  └──────┬──────┘  │
│          │            ↕                        │         ▼         │
│          │                                     │  ┌─────────────┐  │
│          │                                     │  │ Segment 1   │  │
│          │                                     │  └──────┬──────┘  │
│          │                                     │         ▼         │
│          │                                     │  ┌─────────────┐  │
│          │                                     │  │ Receiver    │  │
│          │                                     │  └─────────────┘  │
│          │                                     │  ┌─────────────┐  │
│          │                                     │  │  SUMMARY    │  │
│          │                                     │  └─────────────┘  │
└──────────┴────────────────────────────────────┴───────────────────┘
```

## Bidirectional Linking

### Analysis Panel → Drawing
- **Hover** on card → Highlights element on drawing (blue outline, larger size)
- **Click** on card → Selects element on drawing (cyan outline) and pans view
- **Double-click** on card → Opens edit dialog for that element

### Drawing → Analysis Panel
- **Hover** over component/segment → Highlights corresponding card in panel
- **Unhover** → Clears card highlights
- Path selection in paths list → Updates analysis panel

## Visual Styling

### Element Cards
- **Source**: Light orange background, 🔊 icon
- **Segment**: White background, ━━ icon, shows dimensions/length/lining
- **Component**: White background, type-specific icons (↪️ elbow, 🔇 silencer, etc.)
- **Receiver**: Light green background, 🏠 icon, NC pass/fail indicator

### Highlighting
- **Hover**: Light blue background (#e3f2fd), blue border
- **Selected**: Darker blue background (#bbdefb), cyan border, dashed outer ring

### NC Compliance Colors
- NC ≤ 25: Green
- NC 26-35: Light green
- NC 36-40: Yellow
- NC 41-45: Orange
- NC > 45: Red

## Usage

1. Open a drawing with HVAC paths defined
2. Select a path from the "Saved Paths" list in the left panel
3. The Analysis Panel automatically shows the path's calculation flow
4. Hover over elements in either the drawing or analysis panel to see linked highlighting
5. Double-click cards to edit elements
6. Use View > Toggle Analysis Panel (or collapse button) to show/hide

## Future Enhancements

- Inline editing of segment properties without dialog
- Live recalculation as properties change
- Path comparison view
- Export path diagram to image/PDF
