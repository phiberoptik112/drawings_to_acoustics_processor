# Material Schedules Quick Start Guide

## Overview
The Material Schedules feature allows you to manage material/finishes schedule PDFs associated with each drawing set in your project. This is useful for:
- Tracking material changes across design phases (DD, SD, CD, Final)
- Comparing material schedules between drawing sets
- Organizing acoustic treatment documentation by project phase

## Accessing the Feature

1. **Open your project** in the Project Dashboard
2. Click the **"Component Library"** button (located above "Open Drawing Editor")
3. Navigate to the **"Acoustic Treatment"** tab

## Adding Your First Material Schedule

### Step 1: Prepare Your PDF
- Ensure your material schedule is in PDF format
- Place it in an accessible location (or it will be copied to the project)

### Step 2: Add the Schedule
1. In the Acoustic Treatment tab, click **"Add Schedule"**
2. Fill in the dialog:
   - **Drawing Set:** Select which phase this schedule belongs to (e.g., "DD Phase 1")
   - **Schedule Name:** Enter a descriptive name (e.g., "Interior Finishes Schedule")
   - **Schedule Type:** Choose the appropriate category:
     - `finishes` - Interior/exterior finishes
     - `materials` - General materials
     - `acoustic_treatments` - Acoustic panels, ceilings, etc.
     - `ceiling_systems` - Ceiling-specific schedules
     - `flooring` - Flooring materials
     - `wall_systems` - Wall assemblies
     - `other` - Miscellaneous
   - **Description:** (Optional) Add notes about this schedule
   - **PDF File:** Click "Browse..." to select your PDF
   - **Copy to project folder:** ✓ Checked (recommended)
     - Copies the PDF to `project_location/materials/[DrawingSet]/`
     - Ensures the schedule stays with the project
     - Uncheck if you want to reference an external file only
3. Click **"Save"**

### Step 3: View the Schedule
- The schedule now appears in the list under its drawing set
- Click on it to preview the PDF in the right panel

## Organizing Material Schedules

### By Drawing Set
Material schedules are automatically grouped by their drawing set:

```
═══ 🟦 DD Phase 1 (DD) ═══
  📄 Interior Finishes (finishes)
  📄 Acoustic Treatments (acoustic_treatments)
  
═══ 🟨 SD Phase 2 (SD) ═══
  📄 Updated Interior Finishes (finishes)
  📄 Ceiling Systems (ceiling_systems)
  
═══ 🟥 CD Phase 3 (CD) ═══
  📄 Final Interior Finishes (finishes)
```

### Phase Icons
- 🟦 DD (Design Development)
- 🟨 SD (Schematic Design)
- 🟥 CD (Construction Documents)
- 🟩 Final
- ⚫ Legacy

## Comparing Material Schedules

Compare schedules from different drawing sets to track changes:

1. Click **"Compare Schedules"** in the Acoustic Treatment tab
2. Select the **base drawing set** (left side)
3. Select the **schedule** from that set
4. Select the **compare drawing set** (right side)
5. Select the **schedule** from that set
6. View both PDFs side-by-side

**Tip:** This is useful for comparing DD vs CD phases to see what materials changed.

## Editing a Material Schedule

1. Select the schedule in the list
2. Click **"Edit"**
3. Update any field (name, description, PDF file, etc.)
4. Click **"Save"**

**Note:** You can change the PDF file by browsing to a new one.

## Deleting a Material Schedule

1. Select the schedule in the list
2. Click **"Delete"**
3. Confirm the deletion

**Important:** The PDF file itself is NOT deleted from disk. Only the database reference is removed.

## File Storage Modes

### Project-Managed (Recommended)
✅ **Copy to project folder** checkbox CHECKED
- PDF is copied to: `project_location/materials/[DrawingSet_Name]/[Schedule_Name].pdf`
- Project is portable - all files travel with it
- Original file can be deleted/moved without affecting the project

### External Reference
⬜ **Copy to project folder** checkbox UNCHECKED
- Only the file path is stored in the database
- PDF must remain at the original location
- Useful for network-shared material libraries

### Hybrid Mode
The system stores both paths when you copy to project:
- If the managed copy exists, it's used
- If the managed copy is deleted, it falls back to the external path
- Both paths are visible in the edit dialog

## Best Practices

### 1. Organize by Phase
Create separate drawing sets for each design phase and add corresponding material schedules:
- DD Phase → DD material schedules
- CD Phase → CD material schedules

### 2. Consistent Naming
Use clear, consistent names:
- ✅ "Interior Finishes - Level 1"
- ✅ "Acoustic Ceiling Systems"
- ❌ "Schedule 1"
- ❌ "Materials.pdf"

### 3. Use Descriptions
Add notes about what changed or why this version is significant:
```
Description: "Updated per value engineering review on 3/15/2024. 
Replaced acoustic tile A with more cost-effective tile B."
```

### 4. Compare Regularly
Compare schedules between phases to track material changes that might affect acoustic performance.

### 5. Keep PDFs Updated
When you receive updated material schedules:
1. Add the new schedule to the appropriate drawing set
2. Compare with the previous version
3. Note significant changes in the description

## Troubleshooting

### "PDF file not found"
- The PDF was moved or deleted from its original location
- If you used "Copy to project folder", check: `project_location/materials/`
- Edit the schedule and select the PDF again

### "Failed to load PDF"
- The PDF may be corrupted
- Try opening it in a PDF viewer to verify
- Re-export from the original source if needed

### "No drawing sets available"
- You need to create at least one drawing set first
- Go to the "Drawing Sets" tab in the Project Dashboard
- Click "New Set" to create one

### Schedule doesn't appear in the list
- Refresh the Component Library dialog (close and reopen)
- Verify the schedule is assigned to a drawing set in your project

## Integration with Other Features

### Drawing Set Comparison (Future)
Material schedule changes will be highlighted when comparing drawing sets.

### RT60 Calculations (Future)
Material properties from schedules will be automatically linked to spaces for acoustic calculations.

### LEED Documentation (Future)
Material schedules will be included in LEED acoustic reports.

## Tips & Tricks

1. **Quick Preview:** Click "Load PDF..." to preview any PDF without adding it to the database

2. **Multiple Schedules:** You can add multiple schedules to the same drawing set (e.g., one for finishes, one for acoustic treatments)

3. **Archive Old Versions:** Keep old material schedules in "Legacy" drawing sets for historical reference

4. **Network Storage:** If your team uses a shared network drive for material schedules, use external reference mode and update paths if needed

## Next Steps

1. Add your current material schedules to the active drawing set
2. When you receive updated schedules for a new phase, create a new drawing set and add them there
3. Use the comparison tool to identify changes between phases
4. Add descriptions noting significant material changes that affect acoustics

---

**Need Help?** Check the full implementation documentation in `MATERIAL_SCHEDULES_IMPLEMENTATION.md`

