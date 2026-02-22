# Component Library

Manage mechanical units, silencers, and acoustic materials for your project.

## Tabs

- **Mechanical Units**: AHUs and other noise sources
- **Noise Sources**: Custom noise spectra
- **Silencers**: Manufacturer silencer data
- **Acoustic Treatment**: Material absorption data

## Importing Data

You can import equipment schedules from:
- CSV files with manufacturer data
- Image files (OCR extraction)
- Manual entry

---

## Controls

### mech_units_list
**Mechanical Units List**

Shows all mechanical units defined in the project.

Each unit has:
- Name and model number
- CFM rating
- Sound power spectrum (by frequency)

Double-click to edit unit properties.

### add_mech_unit_btn
**Add Mechanical Unit**

Create a new mechanical unit. You'll need to provide:
- Unit name/tag
- CFM airflow rate
- Sound power levels at octave bands

### import_schedule_btn
**Import Schedule**

Import a mechanical schedule from file:
- CSV with sound power data
- Image of equipment schedule (OCR)

The importer will parse the data and create units.

### silencers_list
**Silencers List**

Shows available silencer products.

Silencers are characterized by:
- Length
- Pressure drop
- Insertion loss by frequency

### materials_list
**Acoustic Materials List**

Shows acoustic treatment materials.

Each material has:
- NRC (Noise Reduction Coefficient)
- Absorption coefficients by frequency

### freq_table
**Frequency Data Table**

Edit sound power or insertion loss values at octave band frequencies:
- 63 Hz, 125 Hz, 250 Hz, 500 Hz
- 1 kHz, 2 kHz, 4 kHz, 8 kHz

### save_btn
**Save Changes**

Save all changes to the component library. Changes affect all paths using these components.
