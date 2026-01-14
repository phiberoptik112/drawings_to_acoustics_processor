# HVAC Segment Dialog

Configure duct segment properties including dimensions, lining, and fittings.

## Segment Properties

- **Length**: Physical duct length in feet
- **Dimensions**: Width × Height for rectangular ducts
- **Lining**: Internal acoustic treatment
- **Fittings**: Elbows, branches, and transitions

## Noise Attenuation

Duct segments attenuate noise through:
1. **Natural attenuation**: Friction and surface losses
2. **Lined duct**: Additional absorption from lining
3. **Fittings**: Regenerated noise from turbulence

---

## Controls

### length_spin
**Segment Length**

Enter the duct length in feet. This affects natural attenuation calculations.

### width_spin
**Duct Width**

Enter the duct width in inches. Combined with height, this determines the duct cross-section.

### height_spin
**Duct Height**

Enter the duct height in inches. For round ducts, use equal width and height.

### duct_type_combo
**Duct Type**

Select the duct construction:
- **Rectangular**: Standard sheet metal duct
- **Round**: Spiral or longitudinal seam
- **Flex**: Flexible duct sections

### lining_type_combo
**Lining Type**

Select the internal duct lining:
- **None**: Bare sheet metal
- **1" Fiberglass**: Standard acoustic lining
- **2" Fiberglass**: Enhanced attenuation
- **External Wrap**: Thermal insulation only

### upstream_fitting
**Upstream Fitting**

Configure the fitting at the upstream (source) end of this segment.

Options include:
- None
- Elbow (radius depends on duct size)
- Branch takeoff
- Transition

### downstream_fitting
**Downstream Fitting**

Configure the fitting at the downstream (receiver) end.

### calculate_btn
**Calculate Segment**

Calculate the attenuation for this segment based on current settings.

### save_btn
**Save Segment**

Save the segment configuration and return to the path dialog.
