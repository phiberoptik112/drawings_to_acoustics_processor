# HVAC Path Dialog

Create and configure HVAC noise paths from mechanical sources to receiver spaces.

## Path Structure

An HVAC path consists of:
1. **Source**: Mechanical unit generating noise
2. **Components**: Equipment along the path (elbows, silencers, etc.)
3. **Segments**: Duct runs connecting components
4. **Receiver**: The space where noise is delivered

## Noise Calculation

The path calculator computes:
- Sound power at each point
- Attenuation from duct lining
- Insertion loss from silencers
- End reflection loss at diffusers/grilles
- Final NC rating at the receiver

---

## Controls

### path_name_edit
**Path Name**

Enter a descriptive name for this path. Examples:
- "AHU-1 to Conference Room Supply"
- "Return Air from Open Office"

### path_type_combo
**Path Type**

Select the path type:
- **Supply**: Air flowing from AHU to space
- **Return**: Air flowing from space back to AHU
- **Exhaust**: Air leaving the building
- **Transfer**: Air between spaces

### target_space_combo
**Target Space**

Select the receiving space for this path. The calculated noise will be attributed to this space.

### source_unit_combo
**Source Mechanical Unit**

Select the mechanical unit that generates the noise. The unit's sound power spectrum is the starting point for calculations.

### components_list
**Components List**

Shows all components in this path. Components are ordered from source to receiver.

- Double-click to edit component properties
- Use Add/Remove buttons to modify the path
- Drag to reorder components

### segments_list
**Segments List**

Shows duct segments connecting components.

Each segment has:
- Length in feet
- Duct dimensions (width × height)
- Lining type and thickness
- Fittings (elbows, branches)

### calculate_btn
**Calculate Noise**

Run the noise calculation for this path. Results show:
- Sound power at each point
- Attenuation by element
- Final dB(A) and NC rating

### diagram_panel
**Path Diagram**

ASCII diagram showing the path structure from source to receiver with calculated noise levels at each point.

Click on elements in the diagram to select and edit them.
