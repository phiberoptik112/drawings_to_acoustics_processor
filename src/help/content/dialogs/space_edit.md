# Space Edit Dialog

Edit the properties of a space including dimensions, materials, and acoustic targets.

## Tabs

- **Basic Properties**: Room dimensions, type, and targets
- **Surface Materials**: Define materials for each surface
- **Partition Isolation**: STC ratings for walls and partitions
- **Calculations**: View RT60 and noise analysis results

## RT60 Calculation

RT60 (Reverberation Time) is calculated based on:
- Room volume
- Surface areas and their absorption coefficients
- Target values based on room type

The plot on the right shows calculated vs. target RT60 across frequencies.

---

## Controls

### room_type_combo
**Room Type Presets**

Select a room type to automatically apply appropriate:
- Target RT60 values
- Default materials
- NC criteria

Common room types include:
- Conference Room
- Open Office
- Private Office
- Classroom
- Auditorium

### name_edit
**Space Name**

Enter a descriptive name for this space. This will appear in reports and exports.

### floor_area_spin
**Floor Area**

The floor area in square feet. This is typically calculated from the drawn boundary but can be adjusted manually.

### ceiling_height_spin
**Ceiling Height**

The room height in feet. Combined with floor area, this determines the room volume.

### target_rt60_spin
**Target RT60**

The target reverberation time in seconds. Typical values:
- Speech: 0.6-0.8 seconds
- Music: 1.0-1.5 seconds
- General: 0.8-1.0 seconds

### ceiling_material_combo
**Ceiling Material**

Select the acoustic material for the ceiling surface. This significantly affects RT60.

Common ceiling materials:
- Acoustic Ceiling Tile (high absorption)
- Painted Drywall (low absorption)
- Metal Deck (minimal absorption)

### wall_material_combo
**Wall Material**

Select the wall surface material. Consider both primary and secondary wall materials for mixed surfaces.

### floor_material_combo
**Floor Material**

Select the floor covering material.

Common floor materials:
- Carpet on Concrete (moderate absorption)
- Hard Tile/Stone (minimal absorption)
- Wood Flooring (low absorption)

### save_btn
**Save Changes**

Save all changes without closing the dialog. Use this to save progress while continuing to edit.

### calculate_btn
**Calculate RT60**

Run the RT60 calculation with current settings. Results appear in the plot and Calculations tab.
