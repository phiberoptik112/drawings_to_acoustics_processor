### HVAC Component: Library Import did not persist on reopen

- **Date**: 2025-08-21
- **Area**: Drawing view → Edit HVAC Component dialog → Import from Library Mech. Units
- **Status**: Fixed

### Symptoms
- Double‑clicking a component on the drawing opens “Edit HVAC Component”.
- Clicking “Import from Library Mech. Units”, selecting a unit, then “Update Component” appeared to work, but reopening the dialog for the same component did not show the imported unit’s frequency preview, making it look like the change did not persist.

### Root Cause
- The app historically stores a selected Mechanical Unit identifier in `HVACPath.primary_source_id` (backward‑compatibility fallback), while modern logic also supports referencing an `HVACComponent` via the same column/relationship. Because the import action only updated the component fields (name/type/noise) and relied on the ambiguous `primary_source_id` behavior, the dialog did not restore frequency‑band previews on reopen, giving the impression that nothing was saved.

### Fix Overview
1. **Immediate persistence + logging when applying a Mechanical Unit**
   - When a unit is chosen, the dialog now:
     - Updates `name`, `component_type`, and seeds `noise_level` from the octave‑band spectrum.
     - Immediately saves these values for the component in edit mode.
     - Associates the selected Mechanical Unit id to any paths where this component is the source by writing it to `HVACPath.primary_source_id` (maintaining compatibility with existing calculations).
     - Emits detailed debug logs for traceability.

2. **Restore preview on reopen**
   - On dialog load, the code scans connected paths; if the edited component is the source and the path has `primary_source_id` set to a Mechanical Unit id, the dialog loads that unit’s octave‑band JSON and restores the frequency preview labels.

3. **User‑visible diagnostics**
   - Added debug prints when opening the component editor from the drawing overlay and throughout the import/save path.

### Files changed
- `src/ui/dialogs/hvac_component_dialog.py`
  - Import chooser open logging.
  - `_apply_mechanical_unit(...)` now prints selection details, parses octave bands, computes A‑weighted level, saves component fields immediately, and associates the unit with relevant paths. Also logs each step.
  - `load_component_data(...)` now restores octave‑band preview by reading the associated Mechanical Unit via `HVACPath.primary_source_id` when this component is the source.
  - `save_component(...)` logs before/after values and re‑propagates a selected Mechanical Unit to paths.
- `src/ui/drawing_interface.py`
  - Logs when opening the component dialog from the overlay (component id/name).

### Related models and calculation flow
- `models/hvac.py`
  - `HVACPath.primary_source_id`: currently declared as `ForeignKey('hvac_components.id')`, but calculators also treat it as a Mechanical Unit id for backward compatibility.
- `models/mechanical.py`
  - `MechanicalUnit`: holds octave‑band JSON fields `inlet_levels_json`, `radiated_levels_json`, `outlet_levels_json` used to seed/preview values.
- `calculations/hvac_path_calculator.py`
  - When building `path_data['source_component']`:
    - Prefers the `primary_source` relationship to a component.
    - Otherwise interprets `primary_source_id` as a `MechanicalUnit.id` and derives A‑weighted level from its octave bands. This is why linking the Mechanical Unit id into `primary_source_id` keeps the solver working.

### Data interaction diagram (high‑level)
- User picks Mechanical Unit in dialog → dialog parses bands and seeds `noise_level` → dialog saves `HVACComponent` fields → dialog sets `HVACPath.primary_source_id = <MechanicalUnit.id>` when the component is the source → calculator reads `primary_source_id` (unit id fallback) → derives source spectrum/level → analysis proceeds.

### Debug log keys to look for
- `DEBUG[DrawingInterface]`: opening component dialog
- `DEBUG[HVACComponentDialog]: Opening Mechanical Unit chooser ...`
- `DEBUG[HVACComponentDialog]: Applying Mechanical Unit ...`
- `DEBUG[HVACComponentDialog]: Parsed bands ...`
- `DEBUG[HVACComponentDialog]: Set base noise from spectrum -> ...`
- `DEBUG[HVACComponentDialog]: Immediate component save after unit apply ...`
- `DEBUG[HVACComponentDialog]: Linked/Updated path ... primary_source_id -> MechanicalUnit id ...`
- `DEBUG[HVACComponentDialog]: Restoring preview from Mechanical Unit ...`

### Reproduce and verify
1. Double‑click a component on the drawing.
2. Click “Import from Library Mech. Units”, select a unit, press “Select”, then “Update Component”.
3. Reopen the component editor: the frequency preview should show the imported bands; base noise level should reflect the seeded dB(A). Terminal will show the debug messages listed above.

### Risks and considerations
- `HVACPath.primary_source_id` has dual meaning (component id vs. Mechanical Unit id). The calculator handles the unit‑id case explicitly, but the schema/relationship suggests a component id.

### Recommended improvements (follow‑up tasks)
- Schema clarity:
  - Add `HVACPath.primary_source_component_id` (FK → `hvac_components.id`) and `HVACPath.primary_source_unit_id` (FK → `mechanical_units.id`).
  - Migrate current values by detecting whether the id matches an existing `MechanicalUnit` or `HVACComponent`.
  - Deprecate overload of `primary_source_id` and drop it after migration.
- Direct linkage on components:
  - Add `HVACComponent.mechanical_unit_id` (FK → `mechanical_units.id`) so the dialog can persist the selection directly without scanning paths to restore preview.
- Performance:
  - Add DB indexes on `hvac_components(project_id, drawing_id)` and on `hvac_segments(hvac_path_id, segment_order)` to speed up lookups and ordering.
  - Ensure all dialog queries use `selectinload` where relationships are accessed in hot paths.
- UX:
  - Display the selected unit name in the dialog header when present.
  - Provide an explicit “Clear imported unit” action.
- Testing:
  - Add an integration test that creates a component, links a Mechanical Unit through the dialog code path, saves, reopens, and asserts that preview labels match the unit’s bands and the component’s noise level was seeded.

### Scripts/Modules involved
- UI/dialogs:
  - `src/ui/dialogs/hvac_component_dialog.py`
  - `src/ui/drawing_interface.py`
- Models (database):
  - `src/models/hvac.py`
  - `src/models/mechanical.py`
- Calculations:
  - `src/calculations/hvac_path_calculator.py`

### Summary
The apparent “not saved” behavior was a visibility issue: data was saved but the dialog did not restore the imported unit’s preview on reopen. The fix adds immediate persistence, links the chosen unit to source paths, restores previews on reopen, and provides comprehensive debug logging to trace the data flow between UI, models, and calculations.
