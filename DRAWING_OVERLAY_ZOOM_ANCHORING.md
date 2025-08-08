### Drawing Overlay Zoom Anchoring - Implementation Notes

This document summarizes the fix for HVAC path/components shifting when the PDF zoom changes, and provides reference steps for future maintenance.

### Problem

- **Symptoms**: HVAC components/segments and path visuals appeared to move relative to the drawing when zooming, or after app reload they reloaded in incorrect positions. In some cases, new elements placed post‑reload either disappeared off‑screen or stayed fixed relative to the viewport instead of the drawing.

- **Root causes**:
  - Overlay coordinates were stored in screen pixels and scaled incrementally on each zoom. Incremental scaling introduced drift/rounding and compounded errors.
  - On reload, persisted elements were restored in pixel space without knowledge of the zoom level at save time, leading to mismatches when the initial viewer zoom was not 100%.
  - Overlay origin could diverge from the pixmap origin if the `QLabel` centered the PDF (padding/margins).

### Design

1. Maintain a stable, zoom‑independent base copy of all overlay geometry ("base geometry") at 100% zoom.
2. On every zoom, reproject on‑screen coordinates from base geometry using the current zoom factor. No incremental scaling of mutated values.
3. Persist the `saved_zoom` alongside element geometry so reloads can normalize back to base geometry before projection.
4. Ensure overlay origin stays aligned with the PDF pixmap’s top‑left.

### Key Changes

- File: `src/drawing/drawing_overlay.py`
  - Added fields: `_current_zoom_factor`, `_base_rectangles`, `_base_components`, `_base_segments`, `_base_measurements`.
  - Rewrote `set_zoom_factor(zoom_factor: float)` to:
    - Lazily initialize base geometry from current elements (dividing by prior zoom).
    - Project base → screen using the new zoom for rectangles, components, segments, and measurements.
    - Recompute pixel lengths and formatted real‑world labels via `ScaleManager`.
  - `get_elements_data()` now stamps each element with `saved_zoom` (the current overlay zoom) before persistence.
  - `load_elements_data(data)` now:
    - Rebuilds `QRect` bounds for rectangles.
    - Rebuilds base geometry by normalizing stored coordinates using `item['saved_zoom'] or 1.0`.
    - Calls `set_zoom_factor(self._current_zoom_factor)` to project to the current viewer zoom immediately after load.

- File: `src/ui/drawing_interface.py`
  - `update_overlay_size()` now calls `self.drawing_overlay.move(0, 0)` to keep overlay origin aligned to the PDF label’s top‑left.
  - `pdf_zoom_changed()` still updates `ScaleManager.scale_ratio` and now delegates to `drawing_overlay.set_zoom_factor(zoom_factor)`.

- File: `src/models/drawing_elements.py`
  - `DrawingElement.from_overlay_data(...)` stores `saved_zoom` in the `properties` for rectangles, components, segments, and measurements so reloads can normalize correctly.

### Data Flow (save → reload → paint)

1. User draws → overlay holds pixel coordinates for current zoom and base caches.
2. Save: `DrawingElementManager.save_elements(...)` persists element dicts which include `saved_zoom`.
3. Reload: `DrawingElementManager.load_elements(...)` returns element dicts; overlay:
   - Reconstructs `QRect` bounds.
   - Builds base geometry from persisted values using `saved_zoom` (normalize to 100%).
   - Projects to current zoom via `set_zoom_factor(current_zoom)`.
4. Paint: all coordinates are screen‑space for the current zoom; lengths re‑derived for labels.

### Debugging Checklist

- If elements shift when zooming:
  - Verify `set_zoom_factor` is called with the actual `PDFViewer.zoom_factor`.
  - Ensure base arrays (`_base_*`) are populated exactly once or rebuilt on load.
  - Confirm no additional transforms are applied in paint methods (`draw_components`, `draw_segments`, etc.).

- If elements misplace after reload:
  - Inspect a loaded element’s `properties.saved_zoom`; it must reflect the zoom when saved.
  - In `load_elements_data`, confirm normalization divides by `saved_zoom` before projecting.
  - Check that `update_overlay_size()` ran and overlay size matches `pdf_label.pixmap().size()`.

- If lateral drift persists:
  - The PDF `QLabel` may center the pixmap (empty margins). Align overlay origin to pixmap origin:
    - Compute content offsets as `offset_x = (pdf_label.width() - pixmap.width()) // 2` and same for Y.
    - Move overlay to `(offset_x, offset_y)`. We currently set `(0, 0)`; add offset if needed for your layout.

### API Notes

- `DrawingOverlay.set_zoom_factor(zoom_factor: float)`
  - Idempotent for the same `zoom_factor`.
  - Recomputes all draw coordinates and length labels.

- `DrawingOverlay.get_elements_data()`
  - Returns deep-ish copies of element lists and injects `saved_zoom` on each dict.

- `DrawingOverlay.load_elements_data(data: dict)`
  - Accepts grouped `rectangles|components|segments|measurements` lists (as produced by `DrawingElementManager`).
  - Rebuilds base caches and projects to the current zoom.

### Manual QA

1. Place two components and a segment at 100% zoom; zoom to 150%/200%/Fit Width; verify positions stay anchored.
2. Save, quit, relaunch; load the same drawing:
   - Previously saved items should render in the same drawing locations before any interaction.
3. Place a new component at the current zoom; zoom in/out; verify it remains anchored.

### Future Improvements

- Compute and apply pixmap content offsets (`center` alignment) so the overlay origin exactly matches the pixmap origin on any container sizing.
- Persist and restore the last zoom per drawing so the initial projection matches user context immediately on open.
- Consider migrating to a `QGraphicsView/QGraphicsScene` pipeline for built‑in view transforms if future needs grow.

### Files Touched

- `src/drawing/drawing_overlay.py`
- `src/ui/drawing_interface.py`
- `src/models/drawing_elements.py`

### Related Docs

- `PATH_VISIBILITY_IMPLEMENTATION.md` — for interaction with path show/hide and mapping of overlay elements to paths.


