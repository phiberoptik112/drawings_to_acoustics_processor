# Acoustic Materials Tab - Quick Start Guide

## Opening the Component Library

1. From the project dashboard, click **"Component Library"** button
2. Navigate to the **"Acoustic Treatment"** tab
3. You'll see two panels side-by-side:
   - **Left**: Acoustic Materials
   - **Right**: Material Schedules (existing functionality)

## Adding Your First Material

### Using the Manual Treatment Add Dialog

1. Click **"Manual Treatment Add"** button
2. Fill in the material information:
   ```
   Name*: Acoustic Ceiling Tile
   Category: ceilings
   Manufacturer: Armstrong
   Product Code: BP3020
   Mounting Type: suspended
   Thickness: 3/4 inch
   ```

3. Enter absorption coefficients for each frequency:
   ```
   125 Hz:  0.35
   250 Hz:  0.55
   500 Hz:  0.70
   1000 Hz: 0.80
   2000 Hz: 0.75
   4000 Hz: 0.70
   ```

4. Watch the NRC auto-calculate: **0.70**
5. Click **"Save"**

Your first acoustic material is now in the database! 🎉

## Viewing Materials

### All Materials
- Default view shows **all acoustic materials** in the database
- Materials display as: `"Material Name - NRC: 0.XX"`
- Hover over any material to see details in tooltip

### Project Materials Only
- Check **"Show only project materials"** checkbox
- List filters to show only materials used in current project's spaces
- Uncheck to return to full list

## Editing Materials

### Method 1: Edit Dialog (Recommended for major changes)
1. Select a material from the list
2. Click **"Edit"** button
3. Modify any fields you need
4. Click **"Save"**

### Method 2: Quick Edit in Table (For absorption values only)
1. Select a material from the list
2. Absorption coefficients appear in the table below
3. Double-click any coefficient value to edit it
4. NRC updates automatically as you type
5. Click **"Save Changes"** when done

## Deleting Materials

1. Select a material from the list
2. Click **"Delete"** button
3. Review the confirmation dialog:
   - If material is in use, you'll see usage count
   - Deletion is still allowed but requires confirmation
4. Click **"Yes"** to confirm deletion

## Example Materials to Add

Here are some common acoustic materials you can add for testing:

### Acoustic Ceiling Tile
```
Name: Acoustic Ceiling Tile
Category: ceilings
Mounting: suspended
Coefficients: 0.35, 0.55, 0.70, 0.80, 0.75, 0.70
NRC: 0.70
```

### Wall Fabric Panel
```
Name: Wall Fabric Panel (1" thick)
Category: walls
Mounting: spaced
Coefficients: 0.15, 0.45, 0.85, 0.95, 0.90, 0.85
NRC: 0.79
```

### Carpet on Concrete
```
Name: Carpet on Concrete Floor
Category: floors
Mounting: direct
Coefficients: 0.05, 0.10, 0.20, 0.30, 0.40, 0.50
NRC: 0.25
```

### Acoustic Foam
```
Name: Acoustic Foam Panel (2" thick)
Category: walls
Mounting: direct
Coefficients: 0.08, 0.25, 0.65, 0.85, 0.90, 0.95
NRC: 0.66
```

### Fiberglass Insulation
```
Name: Fiberglass Insulation in Wall
Category: walls
Mounting: direct
Coefficients: 0.10, 0.35, 0.75, 0.95, 0.95, 0.90
NRC: 0.75
```

## Understanding the Table

### Frequency Columns (Editable)
- **125 Hz** - Low frequency (bass)
- **250 Hz** - Speech intelligibility start
- **500 Hz** - Primary speech frequency
- **1000 Hz** - Mid speech frequency
- **2000 Hz** - High speech frequency
- **4000 Hz** - High frequency (treble)

### NRC Column (Calculated)
- **NRC** = (α₂₅₀ + α₅₀₀ + α₁₀₀₀ + α₂₀₀₀) / 4
- Automatically updates when you edit absorption values
- Grey background indicates it's read-only
- Range: 0.00 (no absorption) to 1.00 (total absorption)

## Tips & Tricks

### Absorption Coefficient Guidelines
- **0.00 - 0.20**: Hard surfaces (concrete, glass, tile)
- **0.20 - 0.50**: Moderate absorption (carpet, drapery)
- **0.50 - 0.80**: Good absorption (acoustic ceiling, fabric panels)
- **0.80 - 1.00**: Excellent absorption (thick foam, fiberglass)

### When to Use Which Method
- **Add Dialog**: Creating new materials from scratch
- **Edit Dialog**: Major changes (name, category, manufacturer)
- **Table Edit**: Quick adjustments to absorption values
- **Delete**: Removing outdated or incorrect materials

### Best Practices
1. Use descriptive names (include thickness if relevant)
2. Fill in manufacturer and product code for traceability
3. Add mounting type - it affects performance
4. Write notes in description field
5. Double-check coefficients against manufacturer data
6. Keep NRC calculation in mind (speech frequencies matter most)

## Troubleshooting

### "No materials found"
- No acoustic materials in database yet
- Click "Manual Treatment Add" to create your first one

### "No materials used in this project yet"
- Filter is enabled but project has no materials assigned to spaces
- Uncheck filter or add materials to space surfaces first

### Edit/Delete buttons disabled
- No material is selected in the list
- Click a material to select it

### NRC not calculating
- Need values for all 4 speech frequencies (250, 500, 1000, 2000 Hz)
- Enter values in those columns and NRC will appear

### Can't edit NRC directly
- NRC is calculated automatically
- Edit the 4 speech frequency bands to change NRC

## Integration with Spaces

Materials added here can be assigned to room surfaces in the Space Editor:

1. Open a space in the Space Editor
2. Navigate to surface instances
3. Select a surface (ceiling, wall, floor)
4. Choose material from dropdown
5. Material's absorption coefficients used in RT60 calculations

## Running the Test Script

Want to test without clicking around?

```bash
# From project root
python test_acoustic_materials_tab.py
```

This opens the Component Library and provides a test checklist.

## Need More Info?

See **ACOUSTIC_MATERIALS_TAB_ENHANCEMENT.md** for:
- Technical implementation details
- Database schema information
- API reference
- Future enhancement ideas
- Troubleshooting guide

## Common Workflows

### Adding a Material from a Spec Sheet
1. Open manufacturer PDF spec sheet
2. Find absorption coefficients table
3. Click "Manual Treatment Add"
4. Enter material name and manufacturer info
5. Type in coefficients from spec sheet
6. Verify NRC matches spec sheet
7. Save

### Comparing Two Materials
1. Select first material → note absorption values
2. Select second material → compare in table
3. Consider: frequency response, NRC, mounting type
4. Choose based on project requirements

### Batch Adding Materials
1. Prepare a list of materials with coefficients
2. Add first material via dialog
3. Immediately add next (dialog remembers category)
4. Repeat for all materials
5. Review full list when done

## Getting Help

If you encounter issues:
1. Check **IMPLEMENTATION_SUMMARY.md** for known limitations
2. Review **ACOUSTIC_MATERIALS_TAB_ENHANCEMENT.md** for details
3. Check linting: `read_lints src/ui/dialogs/component_library_dialog.py`
4. Run test script: `python test_acoustic_materials_tab.py`

---

**Happy material management!** 🎵🔊

