# CFM Integration, Passive Components, and Engine Delineation Plan

## High-Risk Areas (assessed first)

- **Mechanical Unit integration conflicts**: Ensure passive CFM inheritance does not override valid Mechanical Unit spectra/CFM. Guard to preserve source `flow_rate` when enriching spectrum and surface mismatches explicitly in debug.
- **Existing calculation stability**: Validate that legacy paths without new fields (e.g., `cfm`) calculate identically; add regression set for representative ducts, elbows, junctions.
- **UI consistency in save workflow**: Confirm `hvac_component_dialog.py` persists `cfm` reliably and that imported Mechanical Units set CFM and preview only when data exists; verify no silent fallbacks.

## File Reviews and Actions

### 1) `src/ui/dialogs/hvac_component_dialog.py`

- **Observations**:
  - Adds detailed save/start/verify debug lines, re-queries session instance, sets `component.cfm` explicitly, and verifies post-commit.
  - Mechanical Unit chooser maps `unit_type` to internal component type, previews spectra, and propagates selected unit to connected paths when component is a path source.
  - Provides passive context preview from a recent element result to assist passive components.

- **Actions**:
  - Keep verification prints. Add tests for: (a) edit path, change CFM, verify DB matches; (b) import unit with `airflow_cfm` sets `cfm_spin`, disables standard, persists.
  - Validate preview resilience when JSON band rows are missing or partially null.

### 2) `src/calculations/hvac_path_calculator.py` — Passive Components

- **Observations**:
  - In `_build_path_data_within_session`, passive source types (`elbow`, `junction`, `tee`, `reducer`, `damper`, `silencer`) inherit CFM from upstream active (`fan`, `ahu`, `unit`, `blower`, `compressor`).
  - Preserves `flow_rate` when enriching source with Mechanical Unit bands.
  - Extensive `DEBUG_LEGACY_SOURCE` output clarifies inheritance.

- **Actions**:
  - Keep inheritance foremost. Add a warning if no upstream active CFM found; fall back to default with explicit banner.
  - Unit test: ELBOW-1 inherits 500 CFM from RF 1-1.

### 3) `src/calculations/hvac_path_calculator.py` — Flow Rate Propagation

- **Observations**:
  - `_build_segments_with_flow_propagation` seeds first segment with source CFM; subsequent segments use `_calculate_segment_flow_rate` with reasonableness bounds and 0.8^n decay as a conservative placeholder.
  - Velocity computed from area when needed; defaults preserved.

- **Actions**:
  - Add validation hook for conservation checks (sum downstream ≤ upstream) with warnings in debug.
  - Integration tests: monotonically non-increasing flow for a linear path; contextual junction tests in engine-level logic.

## Engine Delineation and Origin Context

### Goals

- **Terminal delineations**: Clear banners to indicate which engine/stage runs: Path Calculator vs Noise Engine.
- **Origin tagging**: Distinguish "user-initiated" vs "background" calculations in banners and debug.

### Proposed Interface

- Path Calculator: `calculate_path_noise(path_id: int, debug: bool=False, origin: str="user")`
- Internal calls thread `origin` down to Noise Calculator and Noise Engine for consistent banners.

### Banner Formats

- Path Calculator start/end:
  - `\n===== [PATH CALCULATOR] START | origin={origin} | path_id={path_id} =====`
  - `===== [PATH CALCULATOR] END   | origin={origin} | valid={calc_results.get('calculation_valid')} =====\n`
- Noise Engine start/end (already has a header; augment):
  - `\n===== [NOISE ENGINE] START | origin={origin} | path_id={path_id} =====`
  - `===== [NOISE ENGINE] END   | origin={origin} | nc={nc_rating} | terminal={current_dba:.1f} dB(A) =====\n`

### Background vs User

- Default `origin="user"` in UI actions.
- Set `origin="background"` for scheduler/auto-recalc flows (e.g., segment update, fitting add, bulk project calc).

## Validation & Testing Plan

- **Unit**:
  - Passive CFM inheritance for passive sources.
  - Flow propagation reasonableness and velocity computation.
  - Dialog save verification persistency for `cfm`.
- **Integration**:
  - End-to-end path: source bands preserved, `flow_rate` consistent, engine banners printed with correct origin.
  - Junction branching respects upstream/downstream logic; banners show origin.
- **Regression**:
  - Legacy paths without `cfm` unchanged results; verify NC and terminal dBA within tolerance.

## Rollout & Risk Mitigation

- Feature flags via `HVAC_DEBUG_EXPORT` keep banners/dev noise controlled.
- Add conservative fallbacks for missing data; never abort on banner logging.
- Maintain legacy order fallback on connectivity traversal.

## Next Steps

1. Add `origin` parameter and banner prints in Path Calculator and thread into Noise Calculator/Engine.
2. Emit warnings for passive inheritance when no active CFM found.
3. Implement tests per above lists.
