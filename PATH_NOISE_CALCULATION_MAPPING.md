## HVAC Path Noise Calculation: UI Tools ↔ Calculation Pipeline Mapping

- Purpose: Document what is actually happening in the HVAC path noise analysis so you can troubleshoot. This is a noise calculation, per octave band (63–8000 Hz), from a given noise source to a given receiver space.

### UI entrypoints (Path creation and analysis)
- `src/ui/drawing_interface.py`
  - `create_hvac_path_from_drawing(...)` → persists path and triggers immediate calculation via `HVACPathCalculator.create_hvac_path_from_drawing(...)` → `calculate_path_noise(...)`.
  - `calculate_all_hvac_paths(...)` → iterates DB paths, calls calculator for each.
- `src/ui/dialogs/hvac_path_dialog.py`
  - Full CRUD UI for path components/segments; uses `HVACPathCalculator` for on-demand calculation.
  - Stores/reads optional source spectrum from a selected `MechanicalUnit` (octave bands when available).
- `src/ui/hvac_management_widget.py`
  - `analyze_current_path(...)` and `calculate_all_paths(...)` → call `HVACPathCalculator.calculate_path_noise(...)` and render segment breakdown.
- `src/ui/dialogs/hvac_receiver_dialog.py`
  - Combines multiple path terminal spectra at a receiver space per octave band; applies room correction (single source Eq 27 or distributed array Eq 29), then computes overall dB(A) and NC.

### High-level pipeline
1) UI constructs or selects a path → `HVACPathCalculator.calculate_path_noise(path_id)`
2) Calculator builds the data model from DB → `HVACPathCalculator.build_path_data_from_db(hvac_path)`
   - Source:
     - If `primary_source` is a `MechanicalUnit`, attempts to read 8-band `outlet_levels_json` → `octave_band_levels` and derives A-weighted `noise_level`.
     - Else, uses the first segment’s `from_component` with a default or stored `noise_level`.
   - Segments: per segment collects geometry, lining, duct shape/type, and infers a `fitting_type` of `elbow`/`junction` if any fittings present (to drive generated-noise models).
   - Terminal: basic placeholder object (room-correction hook exists in the engine).
3) Legacy-to-engine conversion → `NoiseCalculator._convert_path_data_to_elements(path_data)` builds a list of `PathElement`s.
4) Core per-octave computation → `HVACNoiseEngine.calculate_path_noise(path_elements)`
   - Frequency bands: `[63, 125, 250, 500, 1000, 2000, 4000, 8000]` (8 bands).
   - Source initialization:
     - If `source.octave_band_levels` present, use as the initial spectrum.
     - Else estimate spectrum from `source_noise_level` using a typical HVAC spectral shape.
   - For each element (order preserved):
     - Compute per-element effect via `_calculate_element_effect(...)`:
       - `duct` → insertion loss spectrum (lined/unlined, circular/rectangular calculators) → subtract from spectrum per band.
       - `elbow` → generated noise spectrum (turning vanes or junction-based elbow model) → log-add to spectrum per band.
       - `junction` → generated noise spectrum (T-junction model) → log-add per band.
       - `flex_duct` → insertion loss spectrum → subtract per band.
       - `terminal` → room-correction metadata only (placeholder; final receiver correction happens in the receiver dialog).
     - Clamp band levels to non-negative after attenuation.
     - Recompute overall dB(A) from spectrum with A-weighting.
     - Compute per-element NC from the spectrum vs NC curves.
     - Record element result with:
       - `noise_before`, `noise_after`, `noise_after_dba`, `noise_after_spectrum`
       - `attenuation_spectrum` and/or `generated_spectrum`
       - `attenuation_dba` / `generated_dba` when applicable
5) Engine returns `PathResult` with final terminal spectrum, terminal dB(A), total attenuation, NC, and full `element_results`.
6) Calculator converts to legacy dict and updates DB fields on success: `HVACPath.calculated_noise` and `HVACPath.calculated_nc`.
7) Receiver combination (if used) → `HVACReceiverDialog.calculate_combined_noise()`
   - Pulls per-path terminal spectrum (8-band), truncates to 7 bands (63–4000 Hz) for room correction.
   - Per-band LP computation using `ReceiverRoomSoundCorrection`:
     - Single source (Eq 27) or distributed array (Eq 29).
   - Energy-sums bands across paths → back to dB per band → pads to 8 bands for engine utilities.
   - Computes total dB(A) and NC at the receiver.

### Data model: what moves where
- `HVACPathCalculator.build_path_data_from_db(...)` produces:
  - `source_component`: `{ component_type, noise_level, octave_band_levels? }`
  - `segments[]`: each has `{ length, duct_width, duct_height, diameter?, duct_shape, duct_type, lining_thickness, fittings[], fitting_type? }`
    - `fittings[]`: `{ fitting_type, noise_adjustment, position }` (noise_adjustment informs UI but core engine uses inferred `fitting_type` for generated-noise models)
  - `terminal_component`: `{ component_type, noise_level }` (room volume/absorption may be added if available)
- `NoiseCalculator._convert_path_data_to_elements(...)` → `PathElement[]` consumed by the engine.
- Engine results exposed to UI:
  - `path_elements`/`path_segments` (per-element breakdown)
  - `octave_band_spectrum` (terminal 8-band spectrum)
  - `terminal_noise` (dB(A)), `nc_rating`, `total_attenuation_dba`

### Octave bands, weighting, and rating
- Bands: 63, 125, 250, 500, 1000, 2000, 4000, 8000 Hz (8 bands in the core engine).
- A-weighting: applied per band to compute dB(A) from the current spectrum.
- NC rating: highest NC curve not exceeded by the terminal per-band spectrum.
- Room correction module works on 7 bands (63–4000 Hz). The receiver combines paths using 7-band LP then pads back to 8 for overall dB(A)/NC utilities.

### Where to inspect numbers (helpful for debugging)
- Per-element spectra after each operation: `element_results[].noise_after_spectrum` (8-band).
- Attenuation vs generated spectra per element: `attenuation_spectrum` / `generated_spectrum`.
- Source spectrum used: `source_element.octave_band_levels` (if present) or the estimated spectrum from `source_noise_level`.
- Receiver band table: shown in `HVACReceiverDialog` (7 bands, LP in dB), method selectable per row (Eq 27 vs Eq 29).

### Common pitfalls to check
- Source data:
  - If a `MechanicalUnit` is selected, ensure `outlet_levels_json` (fallbacks: `inlet_levels_json`, `radiated_levels_json`) contains keys "63"–"8000" as strings; otherwise the engine will fall back to spectrum estimation from dB(A).
- Bands mismatch:
  - Core engine uses 8 bands; room correction uses 7. The receiver dialog truncates the 8k band before correction and pads back for display/utilities.
- Element typing:
  - Segments default to `duct` unless `fitting_type` is inferred (`elbow`/`junction`) or `duct_type == 'flexible'` → `flex_duct`.
- Negative band levels:
  - After attenuation the engine clamps bands at 0 dB to avoid negative SPLs; very large insertion loss values may mask unrealistic inputs.

### Minimal “how it all connects” map
- UI tool → Data → Calculator → Engine → UI results
  - Drawing/Dialogs/Management → `build_path_data_from_db` → `_convert_path_data_to_elements` → `calculate_path_noise` → per-element spectra, terminal spectrum, dB(A), NC
  - Receiver dialog → per-path terminal spectrum (engine) → room correction (7 bands) → energy sum → total dB(A), NC

### Suggested debugging hooks (non-breaking enhancements)
- Add a developer toggle to write the following per path to JSON/CSV:
  - Initial source spectrum (8-band) and source dB(A)
  - Per-element: `attenuation_spectrum`, `generated_spectrum`, `noise_before`, `noise_after`, `noise_after_spectrum`
  - Final terminal spectrum, terminal dB(A), NC
- Surface “Terminal Octave Bands (63–8k Hz)” in existing UI panels where `element_results` are already present (a table is already presented in receiver dialog; add a similar table for a single path in the path dialog/management views).
- In the receiver dialog, echo the 8th band (8k) separately for transparency when converting to 7 bands for room correction.

### Files of interest
- UI/frontend tools
  - `src/ui/drawing_interface.py` (create/calc all paths; path creation from overlay)
  - `src/ui/dialogs/hvac_path_dialog.py` (create/edit path; analysis; source spectrum injection)
  - `src/ui/hvac_management_widget.py` (single/all-path analysis display)
  - `src/ui/dialogs/hvac_receiver_dialog.py` (receiver-side combination and room correction)
- Calculation core
  - `src/calculations/hvac_path_calculator.py` (DB ↔ calculation data builder; orchestrates calc and DB updates)
  - `src/calculations/noise_calculator.py` (adapter to engine; element construction; result conversion)
  - `src/calculations/hvac_noise_engine.py` (per-octave band pipeline; element effects; A-weighting; NC)
  - Room correction: `src/calculations/receiver_room_sound_correction_calculations.py` (7-band room LP)

### Debug export (JSON/CSV) — how to enable and where files go
- Toggle via environment variable: set `HVAC_DEBUG_EXPORT=1` (or `true/yes/on`).
- When enabled, each call to `HVACPathCalculator.calculate_path_noise(...)` writes:
  - JSON: full payload (source/terminal spectra, per-element spectra, geometry, NC/attenuation).
  - CSV: one row per element with band columns for after/attenuation/generated.
- Output directory: `~/Documents/AcousticAnalysis/debug_exports/project_<project_id>/`
  - Filenames: `path_<id>_<name>_<YYYYMMDD_HHMMSS>.json` and `.csv`.
- Implementation:
  - See `HVACPathCalculator._debug_export_path_result(...)`.
  - Uses engine bands `[63..8000]`; receiver correction stays 7-band separately.

This mapping reflects current behavior and should make it clear where each per-octave-band value originates and how it flows from a source through path elements to the receiver space. For deeper issues, enable the debug export to capture full spectra at each step.