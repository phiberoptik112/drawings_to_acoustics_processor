## Automatic Fittings Detection for HVAC Paths

### Why
- **Goal**: Eliminate manual per-segment fittings and make the fittings portion of a Path automatically inferred from what is connected before and after each path element.
- **Benefits**: Faster authoring, fewer user errors, deterministic calculations, and cleaner data model.

### Current state (summary)
- Data model:
  - `HVACSegment` stores geometry/duct properties and references `from_component`/`to_component`.
  - Manual fittings live in `SegmentFitting` and are edited in `HVACSegmentDialog` via `FittingTableWidget` using `STANDARD_FITTINGS`.
- Calculations:
  - `HVACPathCalculator.build_path_data_from_db` translates segments to dicts and copies any `segment.fittings` into `segment_data['fittings']`.
  - A coarse `segment_data['fitting_type']` is derived from manual fittings to hint the engine (`elbow`/`junction`).
  - `NoiseCalculator._determine_element_type` maps to engine `PathElement` types, mainly `duct`, `elbow`, `junction`, `flex_duct`, `terminal`, `source`.
- UI: segment fittings are manually entered; path dialog shows results but fittings management is per-segment.

### North Star behavior
- For each segment in a path, the system infers upstream and downstream fittings from adjacent connectivity and properties.
- The calculator uses an explicit list of path elements with interleaved pseudo-elements for fittings, e.g. `[source] - [elbow] - [duct] - [tee] - [duct] - [reducer] - [duct] - [terminal]`.
- Manual `SegmentFitting` entries are ignored by default; optionally surfaced as "legacy" and convertible to notes if needed.

### Scope
- In-scope: detection rules, calculator integration, UI read-only view of detected fittings, feature flag, tests, minimal migration.
- Out-of-scope (Phase 2): storing full polylines, angle-accurate elbows, advanced junction acoustics beyond current engine capabilities.

---

### Detection model
Automatic detection is computed at two junctions for each `HVACSegment s[i]`:
- Upstream joint J(i-1,i) between `s[i-1]`→`s[i]` via shared component C_up (unless `s[i]` is first).
- Downstream joint J(i,i+1) between `s[i]`→`s[i+1]` via shared component C_dn (unless `s[i]` is last).

Key inputs available without new geometry columns:
- Component types at joints (e.g., `branch`, `damper`, `silencer`, etc.).
- Node degree (how many segments touch a component) from the path graph.
- Duct property transitions across segments: shape (`rectangular`/`circular`), dimensions (`width`/`height`/`diameter`), lining changes.

#### Core rules (Phase 1)
- **Junction (tee)**: If a component at a joint has degree ≥ 3 within the path, classify the joint as a `junction`.
  - If the current segment is the pass-through leg (based on two colinear segments when geometry is available; otherwise default), prefer `tee_straight`.
  - If the current segment is the branching leg, prefer `tee_branch`.
  - Without angles, use heuristic: the longest of the two connected segments at the node is likely the through path → `tee_straight` on that connection; the other gets `tee_branch`.
- **Reducer / Transition**: If cross-section (shape or size) changes across a joint, classify as `reducer`.
  - Round↔rectangular ⇒ treat as `transition` (new subtype) or as `reducer` with a special tag.
- **Damper**: If the joint component type is `damper`/`balancing_damper`/`fire_damper`, classify as a `damper` fitting.
- **Elbow (heuristic)**:
  - If a joint component type is `branch`, do NOT call it an elbow; it is a junction.
  - If we have geometry (Phase 2), an angle ≈ 90° ⇒ `elbow_90`; ≈ 45° ⇒ `elbow_45`.
  - Without geometry (Phase 1), we only classify elbows if an explicit `elbow` component exists in the model (optional) or we skip elbow detection (safe, conservative) until geometry is available.
- **No fitting**: If none of the above apply, no automatic fitting is inserted at that joint.

#### Ambiguity handling
- When multiple rules apply, choose priority: `junction` > `damper` > `reducer` > `elbow`.
- If detection is ambiguous, add a warning to the analysis result and choose the more conservative type (`junction` over elbow).

---

### Engine integration
We will explicitly construct engine elements instead of relying on a single `fitting_type` per segment.

- Extend `HVACPathCalculator.build_path_data_from_db` to produce either:
  - `path_data['elements']`: a fully-typed sequence of elements, including detected fittings, or
  - Fallback `path_data['segments']` (legacy) when flag off.
- Update `NoiseCalculator.calculate_hvac_path_noise` and `_convert_path_data_to_elements` to consume `path_data['elements']` if provided and bypass legacy inference.
- Mapping to engine `PathElement.element_type`:
  - `duct` → `duct` (existing)
  - `junction` (tee) → `junction` (existing)
  - `elbow_90`, `elbow_45` → `elbow` (existing), carry angle via aux fields if needed later
  - `reducer`/`transition`/`damper` → two options:
    - Phase 1: model as `junction` in the engine and add a scalar `generated_dba` overlay using `STANDARD_FITTINGS` (pragmatic approximation).
    - Phase 2: add explicit reducer/transition/damper support to `HVACNoiseEngine` with proper spectra.

Pseudocode for elementization:
```python
# in HVACPathCalculator
if use_auto_fittings:
    elements = []
    elements.append(PathElement(element_type='source', ...))
    for i, seg in enumerate(ordered_segments):
        # upstream fitting at joint with previous segment
        if i > 0:
            f_up = infer_joint_fitting(ordered_segments[i-1], seg, joint_component=shared_component(...))
            if f_up is not None:
                elements.append(f_up)
        # the duct segment itself
        elements.append(to_duct_element(seg))
        # downstream fitting will be inserted before the next segment when i+1 loop runs
    elements.append(PathElement(element_type='terminal', ...))
    path_data['elements'] = elements
else:
    # legacy: only segments
    path_data['segments'] = [...]
```

---

### Data model changes
- Keep `SegmentFitting` for backward compatibility in Phase 1 (ignored by default).
- Optional new columns (Phase 2) on `HVACSegment` to enable angle-accurate elbow detection:
  - `start_x`, `start_y`, `end_x`, `end_y` (float, pixels or world units)
  - Alternatively, `path_points_json` for polylines.
- Optional new flag on `HVACPath`:
  - `auto_fitting_detection` (boolean, default true) to allow path-level override.

Migration approach:
- Lightweight SQL migration script that adds columns if missing; default values preserve behavior.
- No destructive schema changes in Phase 1; `segment_fittings` table remains.

---

### UI changes
- `HVACSegmentDialog`:
  - Replace editable fittings table with a read-only "Detected Fittings" panel showing upstream/downstream detection per segment.
  - Show a per-path toggle: "Auto-detect fittings" (on by default). When off, legacy manual fittings UI reveals (advanced users only).
- `HVACPathDialog`:
  - Add a summarized view listing detected fittings in the ASCII diagram sidebar, inline with segment ordering.
  - Surface warnings for ambiguous detections with affordance to override type for a joint (optional: lightweight override that writes a hint, not a `SegmentFitting`).

---

### Detection algorithm details
Helpers:
```python
def build_adjacency(segments):
    # returns dict[component_id] -> list[segment]

def classify_joint(prev_seg, next_seg, component, rules_ctx) -> Optional[Fitting]:
    # degree-based tee
    deg = len(adjacency[component.id])
    if deg >= 3:
        return Fitting(type='junction', subtype=_tee_subtype(prev_seg, next_seg))
    # reducer / transition
    if _shape_or_size_changes(prev_seg, next_seg):
        return Fitting(type='reducer', subtype=_transition_subtype(prev_seg, next_seg))
    # damper
    if component.component_type in {'damper', 'balancing_damper', 'fire_damper'}:
        return Fitting(type='damper')
    # elbow (Phase 2 with angles)
    if rules_ctx.has_geometry and _angle_between(prev_seg, next_seg) >= 70:
        return Fitting(type='elbow', subtype='elbow_90')
    if rules_ctx.has_geometry and 30 <= _angle_between(prev_seg, next_seg) < 70:
        return Fitting(type='elbow', subtype='elbow_45')
    return None
```

Noise mapping (Phase 1):
- Use `STANDARD_FITTINGS[<subtype>]['noise_adjustment']` to populate `generated_dba` when the engine lacks explicit support.

---

### Feature flagging and rollout
- Config:
  - Environment variable `HVAC_AUTO_FITTINGS=1` → default on.
  - Per-path override via `HVACPath.auto_fitting_detection` if column is present; otherwise fallback to env.
- Rollout steps:
  1. Ship detection behind flag, leave legacy UI accessible.
  2. Enable by default after validation; keep legacy for one release.
  3. Deprecate manual `SegmentFitting` editing; keep read-only history.

---

### Testing
- Unit tests (pure):
  - Degree-based tee detection for Y, T and cross nodes.
  - Reducer detection on size and shape change.
  - Damper mapping from component type.
  - Fallback behavior when ambiguous.
- Integration tests:
  - Build a simple path (source → segment → branch → two segments → terminal) and assert elementization inserts one junction and yields higher generated noise than straight path.
  - Verify reducer detection changes output when upstream/downstream sizes differ.
  - Ensure disabling auto-detect reverts to legacy behavior.
- UI tests:
  - Read-only detected fittings panel renders and updates after edits.

---

### Backward compatibility and migration
- When legacy `SegmentFitting` rows exist:
  - Show a banner: "Manual fittings present (legacy). Auto-detect is enabled; manual fittings are ignored."
  - Offer a quick action to disable auto-detect for this path (for comparison) without deleting legacy data.
- No data loss in Phase 1.

---

### Tasks (sequenced)
1. Calculator and engine integration
   - Add `elements` support in `NoiseCalculator._convert_path_data_to_elements` (prefer elements over segments).
   - Implement `infer_fittings_for_path` in `HVACPathCalculator` to elementize paths with detected joints.
   - Map reducer/damper to junction with `generated_dba` overlay using `STANDARD_FITTINGS` (Phase 1).
2. Feature flags
   - Read `HVAC_AUTO_FITTINGS` env; thread through `HVACPathCalculator` and dialogs.
   - Optional: add `HVACPath.auto_fitting_detection` column and honor it when present.
3. UI
   - Replace editable fittings table with read-only panel + flag toggle.
   - Update path ASCII diagram to annotate detected fittings inline.
4. Tests
   - Add unit tests for detection functions.
   - Add integration tests for elementization and result deltas.
5. (Optional, Phase 2) Geometry capture
   - Add start/end coordinates to `HVACSegment` and populate from drawing creation.
   - Implement angle-based elbow detection; add `elbow_90`/`elbow_45` subtypes reliably.
6. (Optional, Phase 2) Engine extensions
   - Add explicit reducer/transition/damper spectral models to `HVACNoiseEngine`.

---

### Acceptance criteria
- With auto-detect ON and no manual fittings, a branched path reports at least one `junction` element and higher generated noise than the same path without branching.
- Changing duct size between segments yields a detected `reducer` and measurably different terminal noise.
- Disabling auto-detect reverts to legacy behavior without errors and uses manual fittings if present.
- UI shows detected fittings per joint, with clear labels and no editing by default.

---

### Risks and mitigations
- Elbow detection accuracy without geometry → Phase 2 introduces geometry columns; Phase 1 avoids speculative elbows.
- Over-counting fittings at nodes shared by multiple segments → de-duplicate by joint (component, adjacent pair) and insert per transition only.
- Engine lacking reducer/damper models → approximate via `generated_dba` now; add full support later.

---

### Implementation notes
- Prefer building `elements` over enriching `segments` with `fitting_type` to support multiple fittings per joint and correct ordering.
- Keep `SegmentFitting` model for one release for migration; mark UI as legacy.
- Thread warnings from detection into `PathResult.warnings` for UI display.