# Unified Dashboard + Drawing Workflow Refactor Plan

## Objective

- **Keep a persistent split-view** where the left pane is the `ProjectDashboard` (Drawings/Spaces/HVAC Paths) and the right pane is a single drawing panel derived from `drawing_interface.py`.
- **Synchronize selections**: selecting a drawing, space, or HVAC path on the left updates the right drawing view to the correct drawing/page and centers/highlights the relevant path.
- **Eliminate extra windows**: stop spawning new `DrawingInterface` windows; instead, switch the embedded right-side panel to the selected drawing.

## Approach Summary

- Extract the current drawing UI from `src/ui/drawing_interface.py` into an embeddable widget `DrawingPanel` while preserving `DrawingInterface` as a thin, standalone wrapper.
- Embed a single `DrawingPanel` into the `ProjectDashboard` right pane.
- Add APIs to center/zoom to path elements, highlight them, and toggle path-only visibility.
- Wire dashboard selections (Drawings/Spaces/HVAC Paths) to call these APIs.

## Architecture Changes

### New `DrawingPanel` (embeddable widget)

- Factor out the internal content of `DrawingInterface` (toolbars, left tools, `PDFViewer`, `DrawingOverlay`, scale manager, status integration) into a new `QWidget`: `DrawingPanel`.
- Public signals: `finished`, `paths_updated` (mirrors existing where applicable).
- Public state: `project_id`, `drawing_id`, current page/zoom, visible path set, path-only mode.

### `DrawingInterface` (compatibility wrapper)

- Keep `DrawingInterface(QMainWindow)` for standalone flows; internally contains a `DrawingPanel` and forwards menu/toolbar actions.
- Existing code paths that open a dedicated window continue to work without changes.

### `ProjectDashboard` integration

- Replace the current right panel with a container hosting:
  - Optional compact status groups (Analysis Status, HVAC Pathing per Space).
  - The embedded `DrawingPanel` (takes remaining space; stretch factor 1).
- Replace actions that open new windows with calls into the embedded panel:
  - Drawings tab → `drawing_panel.load_drawing(drawing_id)`.
  - HVAC Paths tab (row select) → `drawing_panel.focus_path(path_id, center=True, highlight=True, exclusive=True)`.
  - Spaces tab “HVAC Pathing per Space” table (double-click) → same as above.

### `PDFViewer` enhancements

- Add view control methods:
  - `zoom_to_rect(x: int, y: int, w: int, h: int, padding_ratio: float = 0.15) -> None`
  - `center_on_point(x: int, y: int) -> None`
- If needed, wrap the label in a `QScrollArea` to enable reliable centering/zooming.

### `DrawingOverlay` enhancements

- Add helpers:
  - `compute_path_bounding_rect(path_id: int) -> Optional[QRect]` — compute bounds from registered elements.
  - `set_highlighted_path(path_id: Optional[int]) -> None` — visually emphasize a path; dim non-focused elements when in exclusive mode.
- Reuse existing registration (`register_path_elements`, `visible_paths`) for show/hide.

## Public APIs (to be implemented)

- In `DrawingPanel`:
  - `load_drawing(drawing_id: int) -> None`
  - `display_path(path_id: int, *, center: bool = True, highlight: bool = True, exclusive: bool = True) -> bool`
  - `focus_path` (alias to `display_path`)
  - `clear_focus() -> None`
  - `ensure_path_registered(path_id: int) -> bool`
  - `set_path_only_mode(enabled: bool) -> None`
  - `center_on_rect(x: int, y: int, w: int, h: int, padding_ratio: float = 0.15) -> None`

- In `PDFViewer`:
  - `zoom_to_rect(...)`
  - `center_on_point(...)`

- In `DrawingOverlay`:
  - `compute_path_bounding_rect(...)`
  - `set_highlighted_path(...)`

## Selection Synchronization Rules

- **Drawings tab**: open/selection calls `load_drawing(drawing_id)`; drawing panel swaps to that PDF and loads saved elements.
- **HVAC Paths tab**:
  - Single-click selection: `focus_path(path_id, center=True, highlight=True, exclusive=True)`.
  - Double-click: open `HVACPathDialog` for editing; on close, re-focus the path.
- **Spaces tab → HVAC Pathing per Space**: double-click a row → focus path as above.
- If a path resides on a different drawing/page, the panel automatically switches and displays a short status message (e.g., “Jumped to: `Mech_plan_test.pdf` page 3”).

## Data Resolution for Focusing

- Determine drawing for a path via its segments’ components (`from_component.drawing_id` or `to_component.drawing_id`).
- Determine page number from related `DrawingElement` records when available; otherwise best-effort center using component coordinates on current page.
- Compute focus rectangle via `DrawingOverlay.compute_path_bounding_rect(path_id)`; fallback to DB component positions with padding.

## UX Details

- Add a checkbox in HVAC Paths tab: **Link selection to drawing view** (default ON). When OFF, left selections do not drive the drawing panel.
- When focusing a path:
  - Ensure its elements are visible; optionally toggle `path_only_mode` to hide other paths.
  - Apply temporary highlight/halo; provide a quick toggle above the viewer: “Show All / Path Only”.
- Preserve current zoom unless a center/zoom rectangle is provided (then `zoom_to_rect` with padding is used).

## Migration Steps

1. Create `DrawingPanel` by extracting internals from `DrawingInterface` (tools, overlay, viewer, scale, signals). Keep existing logic and styles.
2. Implement viewer centering/zooming (`PDFViewer.zoom_to_rect`, `center_on_point`). Introduce `QScrollArea` if necessary.
3. Implement overlay helpers (`compute_path_bounding_rect`, `set_highlighted_path`).
4. Insert `DrawingPanel` into `ProjectDashboard` right pane; wire signals from Drawings/Spaces/HVAC Paths to panel APIs.
5. Replace “Open Drawing” actions to reuse the embedded panel. Keep `DrawingInterface` for standalone mode as a wrapper.
6. Add a link-selection toggle and a small status/toast helper.
7. QA: regression of drawing tools, path show/hide, path registration, page switching.

## Open Questions / Options

- Single split window vs two top-level windows “locked” side-by-side? (Recommend single split.)
- HVAC path selection: single-click focuses; double-click edits — acceptable?
- Auto-switch drawings on path focus — silent or prompt?
- Do `HVACComponent`/`HVACSegment` models need a `page_number` for precise jumps? (Option to add.)
- Highlight style preferences (color, thickness, halo) and whether to dim vs hide others when `exclusive=True`.
- Performance: acceptable to match/register path elements on each selection, or should we add a per-drawing cache?
- Keep `DrawingInterface` standalone entry point, or converge entirely on embedded workflow?

## Acceptance Criteria

- Selecting an HVAC path in `ProjectDashboard` highlights and centers it in the right drawing panel.
- Switching to a path on another drawing auto-loads that drawing (and page), shows a brief status, and highlights the path.
- No additional drawing windows are opened during this flow.
- Path-only toggle hides all unrelated elements; Show All restores them.
- Existing measurement, scale, rectangle-to-space, and export flows continue to function.

## Testing Plan

- Unit-ish UI tests (manual or Qt-driven):
  - Drawings selection updates the panel without spawning windows.
  - HVAC path selection centers/highlights; path on other drawing switches correctly.
  - Double-click HVAC path opens `HVACPathDialog`; after changes, the panel re-focuses and reflects updates.
  - Path-only mode hides unrelated elements and persists while navigating.
  - Zoom/fit interactions still behave after a focus.
- Data integrity tests:
  - Elements registration survives focus cycles and page changes.
  - No detached SQLAlchemy access in dialogs after session close (use `selectinload` where needed as already implemented).

## Work Breakdown (Checklist)

- [ ] Create `DrawingPanel` (`QWidget`) and migrate internals from `DrawingInterface`.
- [ ] Add `load_drawing`, `focus_path`, `ensure_path_registered`, `set_path_only_mode`, `center_on_rect` methods.
- [ ] Add `PDFViewer.zoom_to_rect` and `center_on_point` (introduce `QScrollArea` if necessary).
- [ ] Add `DrawingOverlay.compute_path_bounding_rect` and `set_highlighted_path`.
- [ ] Embed `DrawingPanel` into `ProjectDashboard` right pane; style/layout tuning.
- [ ] Wire Drawings/Spaces/HVAC Paths selections to panel APIs; add “Link selection to drawing view” toggle.
- [ ] Replace “Open Drawing” to use embedded panel; keep `DrawingInterface` for standalone.
- [ ] QA and performance tuning; optional caching of path element lookups.

## Risks & Mitigations

- Centering precision across zoom/page: mitigate with `zoom_to_rect` padding and robust page dimension handling.
- Detached ORM access when dialogs open: continue using `selectinload` and re-query fresh instances where needed (pattern already used).
- Performance on large drawings: lazy registration and optional caching of element mappings.

## Rollout

- Behind a feature flag/config (e.g., `embedded_drawing_mode = true`).
- Allow fallback to legacy windowed mode during UAT.
- Update README and user guides after acceptance.

## Future Enhancements

- Persist per-path camera/zoom bookmarks.
- Multi-path compare view (split inside the drawing panel).
- Keyboard shortcuts for cycling paths and jumping between segments/components.
