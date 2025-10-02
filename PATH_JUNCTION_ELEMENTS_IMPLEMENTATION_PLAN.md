## Standalone Junction Elements — Implementation Plan

### Objective
Introduce standalone `junction` elements in path data (built via `src/calculations/path_data_builder.py`) so `HVACNoiseEngine` can use its context-aware branch/main flow logic and `branch_takeoff_choice` heuristics for tee/branch/cross fittings.

### Current Behavior (problem)
- Segments with duct geometry are forced to `element_type='duct'` and fittings are processed inside `_calculate_duct_effect()` → `_calculate_fitting_effect_for_duct()`.
- This bypasses the engine’s junction-only path that computes upstream/downstream flows, areas, and honors `branch_takeoff_choice`.
- Result: junction spectra selection is not context-aware.

### Desired Behavior
- For tee/branch/cross fittings, emit a distinct `junction` element in the sequence, with zero geometry but with a `fitting_type` and optional `branch_takeoff_choice`.
- Ensure the junction sits between two geometric elements so the engine can infer upstream (previous) and downstream (next) areas/flows.

### Data Contract for Junction Element
- **Required fields**:
  - `element_type`: "junction" (explicit override)
  - `fitting_type`: e.g., `tee_branch`, `t_junction`, `x_junction`, `branch_takeoff_90`
  - `flow_rate`: numeric CFM (defaults to last known flow if not provided)
- **Optional fields**:
  - `branch_takeoff_choice`: `auto` | `main_duct` | `branch_duct`
  - `diameter`/`duct_width`/`duct_height`: omit or set to 0; junctions are non-geometric here
  - `lining_thickness`, `pressure_drop`, etc.: omit

### Implementation Steps

1) Path builder emits junction elements
- Location: `src/calculations/path_data_builder.py`
- Approach: during segment processing, when a segment’s `fitting_type` tokenizes to a tee/branch/cross junction, insert a separate junction element immediately after the duct in the returned `segments` list.
- Rules:
  - Keep the original duct element (length and geometry unchanged).
  - Insert a new dict:
    - `{'element_type': 'junction', 'fitting_type': segment.fitting_type, 'flow_rate': segment.flow_rate, 'branch_takeoff_choice': segment.get('branch_takeoff_choice')}`
    - Omit geometry keys or set them to 0 so it won’t be reinterpreted as a duct.
  - Do not split duct lengths on first pass; placement of the junction between two ducts is adequate for the engine to infer areas.
- Where to implement:
  - In the injected `segment_data_builder` function OR wrap in `SegmentProcessor.process_segments()` to post-process each produced segment dict and append a junction dict when needed.

2) Engine type-detection respects explicit `element_type`
- Location: `src/calculations/hvac_noise_engine.py` in `_determine_element_type()`.
- Change: if `segment.get('element_type') in {'duct','junction','elbow','flex_duct','terminal','source'}`, return it immediately before geometry checks. This lets the builder override the default geometry-first rule.

3) Ensure flows and areas are available to the engine
- The engine’s junction logic uses:
  - `last_flow_rate` (tracked during iteration) as upstream flow;
  - The next non-source element’s `flow_rate` as downstream flow;
  - Areas from the previous element with geometry and the next element (via `_calculate_duct_area`).
- Action: guarantee adjacent duct elements retain their geometry and populated `flow_rate` so the inserted `junction` sits between two geometric elements whenever possible.

4) Honor `branch_takeoff_choice`
- Set `branch_takeoff_choice` on the junction element or the upstream duct; the engine checks both and then falls back to its auto heuristic.

5) Switch builders (prefer PathDataBuilder)
- Update the calling site (legacy path flow) to prefer `PathDataBuilder.build_path_data()` over the legacy `_build_path_data_within_session`.
- Provide a feature flag to control rollout:
  - Env: `HVAC_USE_PATH_DATA_BUILDER=1`
  - If flag enabled, use `PathDataBuilder`; else legacy.

6) Debug instrumentation
- Path builder:
  - Log each emitted element with: `index`, `element_type`, `fitting_type`, `flow_rate`, `branch_takeoff_choice`.
  - When inserting a junction, print a single-line summary identifying the adjacent upstream/downstream element IDs.
- Engine:
  - The existing junction context prints are sufficient; confirm we see `DEBUG_ENGINE: Flow logic analysis` and `JUNCTION CALCULATOR RETURNED DATA` for the new `junction` elements.

7) Validation and tests
- Unit tests:
  - Verify `PathDataBuilder` emits a `junction` dict when `fitting_type` includes `branch`/`tee`/`cross` and geometry is present.
  - Verify `element_type` override is preserved in the emitted dict.
- Integration test:
  - Run a path with: duct → (tee_branch) → duct and assert engine logs include junction context analysis and that `branch_takeoff_choice='branch_duct'` selects the branch spectrum.
  - Confirm no regression for segments without fittings.

8) Backward compatibility
- `_determine_element_type` continues to work for legacy paths; only respects explicit override when present.
- If `PathDataBuilder` is disabled by flag, behavior remains unchanged.

### Tokenization rules for identifying junction fittings
- Treat as junction when any of the tokens are present: `{'branch', 'tee', 't_junction', 'x', 'cross', 'junction'}`.
- Elbows stay as elbows. Optionally, elbows could also be emitted standalone later (out of scope for first pass).

### Out of scope (not blocking this change)
- Negative A-weighted attenuation observed in rectangular duct debug; track separately.

### Milestones
- M1: Engine override support in `_determine_element_type` (small change)
- M2: PathDataBuilder emits `junction` elements for tee/branch/cross
- M3: Feature flag gating + integration test green
- M4: Remove flag (make default) after broader regression pass

### Risks & mitigations
- **Misordered elements**: ensure junction insert preserves original order; add assertion in builder.
- **Missing downstream geometry**: if a junction is terminal-adjacent, fallback to element’s own area or upstream area, as engine already does.
- **Flow inconsistencies**: keep per-element `flow_rate` propagation intact (no new math here).


