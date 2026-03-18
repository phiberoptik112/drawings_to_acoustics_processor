# AGENTS.md

## Learned User Preferences

- Drawing UI Path Analysis panel should mirror Edit HVAC Path window behavior (silencers, NC table, double-click edit).
- Edit HVAC Path window should be non-modal so the drawing UI stays usable simultaneously.
- HVAC paths must be associated with the correct PDF page in bookmarks and location display.
- Silencer changes must be reflected immediately in the drawing view, sequence widget, and noise calculations.
- Avoid storing the database in ~/Documents when Documents is synced to iCloud Drive with Optimize Mac Storage.
- Remove debug instrumentation after fixes are confirmed.

## Learned Workspace Facts

- HVAC models (`HVACComponent`, `HVACSegment`, `HVACPath`, `SilencerProduct`) are all in `models.hvac`.
- Silencers live in the `element_sequence` JSON on `HVACPath`; they are not segment endpoints (`from_component`/`to_component`).
- `HVACComponent` has NOT NULL constraints on `drawing_id`, `x_position`, and `y_position`; use sentinels (0.0) for components not placed on a drawing.
- NC table uses `element_type='terminal'` for the receiver space row; handle it in the receiver/space branch before the component branch to avoid misrouting.
- Silencer library catalog keys (`il_63`, `model`, `length_in`) differ from `SilencerProduct` columns (`insertion_loss_63`, `model_number`, `length`); a mapping function is needed.
- Silencer catalog seeding should use a sentinel guard (e.g. `source_document`) rather than `if existing_count > 0: return`, which blocks catalog entries when sample products exist.
- `HVACComponentDialog.__init__` signature is `(parent, project_id, drawing_id, page_number, component)`. Pass `component=component` as a keyword to avoid positional mixup with `page_number`.
- Use `selectinload()` for SQLAlchemy relationships accessed after the session closes (e.g. `Space.surface_materials`).
- Re-fetch paths with eager-loaded relationships before emitting `path_saved` to avoid `DetachedInstanceError`.
- Use `setWindowModality(Qt.NonModal)` and `show()` instead of `exec()` for non-modal dialogs; keep dialog references to prevent garbage collection.
- Call `show()` before `raise_()` and `activateWindow()` when restoring a hidden Qt window.
- Dialogs may be opened from different parents (dashboard vs drawing interface); do not assume `DrawingInterface` is in the parent chain.
- Default database path on macOS: `~/Library/Application Support/AcousticAnalysis/` (avoids iCloud eviction).
- `RoomBoundary` stores base-zoom pixel dimensions; area must be recalculated using `Drawing.scale_ratio`.
- A-weighting is additive in dB; combine octave bands via power summation, not linear averaging.
- NC exceedances are `(frequency, dB_over_limit)` where the NC curve limit = measured - exceedance.
- `calculate_element_attenuation` must branch on `element_type` (duct, elbow, flex_duct), not only `duct_shape`.
- Silencer cards use purple styling (`#f3e5f5` background, `#7b1fa2` button).
- Location bookmarks require automatic sync after path save; manual sync alone is insufficient.
