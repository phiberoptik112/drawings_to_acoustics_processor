### Codebase Review (PySide6 Acoustic Analysis Tool)

This document summarizes a general code review of the current repository with an emphasis on backend–UI boundaries, data access, and maintainability. It highlights issues, risks, and concrete recommendations for refactoring, especially around how the backend interacts with the UI.

---

## Architecture overview

- **App entry**: `src/main.py` boots `QApplication` and shows `ui/SplashScreen`.
- **Startup/DB**: `ui/splash_screen.py` calls `models.initialize_database()` and populates silencer data.
- **UI**: Large PySide6 widgets and dialogs (e.g., `ui/drawing_interface.py`, `ui/results_widget.py`, `ui/hvac_management_widget.py`, dialogs under `ui/dialogs/…`).
- **Backend**:
  - Data models in `src/models/*` (SQLAlchemy ORM; sqlite by default in `~/Documents/AcousticAnalysis/acoustic_analysis.db`).
  - Calculations in `src/calculations/*` (RT60, HVAC path/noise, NC analyzer, etc.).
  - Drawing subsystems in `src/drawing/*` (PDF viewer + overlay + tools + scale mgmt).
- **Tests/docs**: Numerous pytest files and design/implementation docs at repo root.

---

## High-priority issues

1. **DB session lifecycle misalignment with UI object lifetime**
   - Multiple widgets query with `session = get_session(); …; session.close()` then stash ORM objects into Qt widgets/lists for later use. This can yield detached objects and lazy-load errors when accessed after session close.
   - Example patterns in `ui/hvac_management_widget.py` and `ui/results_widget.py` relying on closed-session objects but mitigating via `selectinload` in some places. Not consistently applied.
   - Impact: sporadic crashes, subtle data staleness, and difficult-to-reproduce bugs.

2. **Potential integrity errors when creating segments with a single endpoint**
   - Model: `models.hvac.HVACSegment.from_component_id` and `.to_component_id` are `nullable=False`.
   - Creator: `calculations/hvac_path_calculator.py` may create a segment when only one endpoint is matched (see `create_hvac_path_from_drawing`), populating `from_component_id` or `to_component_id` with `None`. This can violate NOT NULL.
   - Impact: runtime DB errors and failed path creation, depending on the data captured from the overlay.

3. **Heavy business logic directly in UI thread**
   - UI performs DB reads/writes and long-running calculations synchronously (e.g., HVAC/RT60 calculations, Excel export). Timed refreshes (`QTimer` every 5s/30s) also pull from DB in the GUI thread.
   - Impact: UI freezes, unresponsive interactions, and flicker.

4. **Tight coupling between UI and backend/services**
   - Widgets reach directly into the ORM and calculation engines (e.g., `DrawingInterface` creates RT60/Noise/HVAC calculators, queries sessions, and writes to DB).
   - Duplicate logic: building path data from DB exists in both `ui/drawing_interface.py` and `calculations/hvac_path_calculator.py`.
   - Impact: harder to test, maintain, and evolve the data model.

5. **Debug prints scattered in UI rendering and event handling**
   - Extensive `print("DEBUG: …")` in `drawing/drawing_overlay.py` and `ui/drawing_interface.py` (and others) during paint and interaction paths.
   - Impact: noisy stdout, performance overhead during drawing/zoom, no log levels or routing.

6. **Ad-hoc migrations**
   - `models/database.initialize_database` tries idempotent HVAC schema migration via `ensure_hvac_schema()` but lacks structured migration tooling.
   - Impact: fragile upgrades, especially as schema complexity grows.

7. **UI list views store complex widgets and ORM objects**
   - `QListWidget` with per-item widget compositions and ORM object payloads (e.g., saved in `Qt.UserRole`).
   - Impact: memory churn, poor scalability. Should prefer model/view patterns with lightweight roles.

8. **Business rules embedded in rendering logic**
   - `drawing_overlay.py` contains calculations, connection inference, and persistence concerns intertwined with painting/interaction.
   - Impact: feature work and bug fixing spill across concerns, increasing regressions.

9. **Requirements are only lower-bounded**
   - `requirements.txt` pins minimal versions, not exact tested versions.
   - Impact: non-reproducible builds, unexpected dependency changes.

---

## Medium-priority issues

- Inconsistent eager-loading: Some queries use `selectinload` properly; others not, increasing detached/lazy-load risk.
- Repeated session creation/closing sprinkled across UI code (no central repository/service handling units-of-work).
- Timer-driven refreshes (`5s`/`30s`) can reload entire datasets frequently; should be event-driven where possible.
- Error handling often swallows exceptions with broad `except Exception` and `print`/`QMessageBox`, losing stack context.
- Mixed coordinate systems and dict-based element payloads across overlay and dialogs; no typed schema or dataclasses.
- Excel export UI triggers heavy I/O synchronously on main thread.

---

## Backend–UI interaction: recommended changes

1. **Introduce a service layer (application services) between UI and ORM/calculators**
   - Create `services/` with classes like `ProjectService`, `SpaceService`, `HVACService`, `DrawingService`.
   - Services own sessions and transactions (Unit of Work) and expose async-friendly methods used by UI.
   - Centralize logic currently duplicated (e.g., building path data from DB, exporting summaries).

2. **Adopt repository pattern and a scoped session per interaction**
   - Provide repositories (read-only where feasible) and a `SessionManager` that yields context-managed sessions.
   - UI calls services which open a session, perform work, return DTOs/plain dicts. UI never holds ORM objects.

3. **Move heavy operations off the GUI thread**
   - Use `QThreadPool`/`QRunnable` or `QThread` + signals for:
     - HVAC noise calculations (single and batch)
     - Excel export
     - Material search/treatment analysis (already threaded in `MaterialSearchDialog` — follow that pattern elsewhere)

4. **Define typed DTOs/dataclasses for drawing elements and HVAC path payloads**
   - Replace loose dicts for components/segments/measurements with `@dataclass` payloads and validation.
   - Normalize coordinate handling (screen vs PDF vs real units) in a shared utility.

5. **Centralize logging**
   - Replace `print` with Python `logging` configured once at startup with levels/handlers.
   - Gate verbose overlay/debug logs under `DEBUG` and avoid logging inside paint loops.

6. **Unify path-data builders**
   - Keep a single authoritative routine to transform ORM → calculation input (and vice versa), used by both dialogs and calculators.

7. **Event-driven UI updates**
   - Replace polling timers with signals where possible (e.g., emit `path_created/updated/deleted` → update lists/tables).
   - For cross-widget events, use a lightweight event bus or Qt signals at the application/service layer.

---

## Data model and persistence recommendations

- Align `HVACSegment` nullability with creation logic:
  - Option A: enforce both endpoints are required at creation time; skip segments with partial endpoints.
  - Option B: if partial endpoints are valid, change `from_component_id`/`to_component_id` to `nullable=True` and update code accordingly.
- Introduce Alembic for migrations; generate migration scripts per schema change.
- Add DB constraints where business rules require them (e.g., segment order uniqueness per path).
- Consider storing drawing element IDs and referencing them when registering elements to paths to avoid position-based matching.

---

## UI architecture and performance

- Convert large `QListWidget` usages with embedded widgets to `QAbstractItemModel` + `QTableView/QListView` for performance and clean separation.
- Debounce expensive refreshes; when timers are necessary, load minimal columns and only what changed since last update (timestamps, counts).
- Extract composition of complex HTML/strings in widgets to small presenters/formatters.

---

## Error handling and UX

- Standardize user-facing errors and logging. Bubble detailed exceptions to logs; show concise messages to users.
- Replace broad `except Exception` with narrower exceptions; re-raise or log with stack traces.
- For long-running operations, show progress/spinners and allow cancellation (`QProgressDialog` pattern used in materials analysis is good; replicate elsewhere).

---

## Testing and CI

- Expand tests around service layer (after introducing it) to cover:
  - Path creation from drawing data (endpoint matching, constraints)
  - RT60/Noise calculation contracts (stable DTOs)
  - DB migration round-trips
- Add headless UI smoke tests for dialog/widget flows where practical (Qt Test or pytest-qt).
- Add CI with pinned dependency lock (e.g., `requirements.txt` + `requirements-lock.txt` or `pip-tools`).

---

## Quick wins (low-risk improvements)

- Replace `print` with `logging` and set logger names per module.
- Add `selectinload` consistently to every place that reads relationships and later closes the session.
- Extract duplicated routines (e.g., build path data from DB) into a shared module.
- Add type hints to calculators and data layer; run `mypy` in CI.
- Pin tested dependency versions and provide a `constraints.txt` or lockfile.
- Document database location/override in `README.md` and support an environment variable (e.g., `AA_DB_PATH`).

---

## Suggested refactor roadmap

1. Phase 1 (stability)
   - Introduce logging; standardize exception paths.
   - Fix `HVACSegment` nullability vs creation logic; add tests.
   - Centralize ORM→DTO conversion and eager-loading.

2. Phase 2 (architecture)
   - Add `services/` layer with `SessionManager` context manager; stop returning ORM objects to UI.
   - Thread long-running operations. Replace polling refreshes with signals where possible.

3. Phase 3 (UX and performance)
   - Swap heavy `QListWidget`+widgets to model/view tables.
   - Dataclass element schemas; unify coordinate conversions.
   - Introduce Alembic migrations.

---

## Examples of targeted changes

- Service entrypoints (sketch):
  - `HVACService.create_path_from_drawing(project_id, drawing_elements: PathElementsDTO) -> HVACPathDTO`
  - `HVACService.calculate_path_noise(path_id) -> PathAnalysisDTO`
  - `SpaceService.calculate_rt60(space_id) -> RT60ResultDTO`
  - `ExportService.export_project(project_id, options) -> Path`

- Logging change:
  - Configure `logging.basicConfig(level=INFO)` at startup; use `logger = logging.getLogger(__name__)` in modules.

- Session pattern:
  - `with SessionManager() as session: …` in services; repositories accept session injected in ctor.

---

## Noted strengths

- Good use of `selectinload` in key paths to mitigate detached-object issues.
- Clear separation of domain models and calculators in `calculations/*`.
- Helpful documentation files and extensive tests signal a strong focus on correctness and UX.

---

## Risks if left unaddressed

- Increasing frequency of detached-object/lazy-load errors as features grow.
- Intermittent UI freezes on large drawings and projects.
- Flaky path creation due to segment endpoint nullability.
- Hard-to-reproduce bugs from duplicated transformation logic and debug prints in hot paths.

---

## Closing

Addressing session management, introducing a service layer with typed DTOs, and moving heavy work off the GUI thread will significantly improve reliability, testability, and performance. The outlined roadmap prioritizes safety and incremental change while unlocking cleaner backend–UI boundaries for future features.