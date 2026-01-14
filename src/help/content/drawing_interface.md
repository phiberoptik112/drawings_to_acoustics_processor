# Drawing Interface

The Drawing Interface is where you work with PDF drawings to define spaces and HVAC components.

## Drawing Tools

- **Rectangle**: Draw room boundaries
- **Polygon**: Draw complex room shapes
- **Component**: Place HVAC components (AHUs, diffusers, etc.)
- **Segment**: Connect components with duct runs

## Workflow

1. **Set the scale** using the calibration tool (📏)
2. **Draw spaces** using rectangle or polygon tools
3. **Place components** for HVAC equipment
4. **Connect with segments** to define duct paths

## Navigation

- Scroll wheel to zoom in/out
- Click and drag to pan
- Use page controls to navigate multi-page PDFs

---

## Controls

### rectangle_tool
**Rectangle Tool**

Click and drag to draw rectangular room boundaries.

After drawing, right-click to:
- Create a new space
- Link to an existing space
- Set room properties

### polygon_tool
**Polygon Tool**

Click to place points, double-click to complete the polygon.

Use for irregularly-shaped rooms that can't be represented by simple rectangles.

### component_tool
**Component Tool**

Click to place HVAC components on the drawing.

Components include:
- Air Handling Units (AHUs)
- Diffusers and Grilles
- Silencers
- Elbows and Transitions

### segment_tool
**Segment Tool**

Click on a component to start, then click on another component to create a duct segment connecting them.

Segments have:
- Length (calculated from scale)
- Duct dimensions
- Lining properties
- Fittings (elbows, branches, etc.)

### calibrate_scale
**Calibrate Scale**

Use this tool to set the drawing scale:

1. Click "Calibrate Scale" in the Tools menu
2. Draw a line on a known dimension
3. Enter the actual dimension in feet
4. The scale will be calculated automatically

### paths_list
**Paths List**

Shows all HVAC paths defined on this drawing.

- Check/uncheck to show/hide path overlays
- Double-click to edit path details

### spaces_list
**Spaces List**

Shows all spaces associated with this drawing.

- Check/uncheck to show/hide space boundaries
- Double-click to edit space properties
