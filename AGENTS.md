# AGENTS.md

## Cursor Cloud specific instructions

### Product overview

Acoustic Analysis Tool — a PySide6 desktop application for LEED acoustic certification analysis. No external services or servers required; uses embedded SQLite via SQLAlchemy.

### Running the application

```bash
source .venv/bin/activate
# On the VM desktop (for GUI interaction via computerUse subagent):
DISPLAY=:1 python src/main.py
# Headless (for automated tests only):
QT_QPA_PLATFORM=offscreen xvfb-run -a python src/main.py
```

The app MUST be launched on `DISPLAY=:1` (the VM's desktop) for GUI interaction via the computerUse subagent. Do NOT use a separate Xvfb on `:99` — the computerUse subagent cannot see or interact with displays other than `:1`.

### Running tests

All tests are standalone Python scripts (no pytest runner configured). Use `QT_QPA_PLATFORM=offscreen` and `xvfb-run` for any test that imports PySide6.

```bash
source .venv/bin/activate
QT_QPA_PLATFORM=offscreen xvfb-run -a python test_mvp.py
QT_QPA_PLATFORM=offscreen xvfb-run -a python test_structure.py
```

See `CLAUDE.md` for the full list of test commands.

### Known test failures (pre-existing)

- `test_mvp.py` Database Operations / Excel Export / GUI Components tests fail because the test passes `"sqlite:///:memory:"` as `db_path` to `initialize_database()`, which prefixes it again with `sqlite:///`, creating an invalid URL. This is a pre-existing bug in the tests, not an environment issue.
- `test_mvp.py` Data Libraries test fails on `assert 'acoustic_tile' in STANDARD_MATERIALS` because the key name has changed in the materials module.
- Calculation Engines and Core Imports tests pass successfully.

### System dependencies (pre-installed by snapshot)

The following system packages are needed for PySide6/Qt to function in a headless environment:
`libegl1`, `libgl1`, `libopengl0`, `libxkbcommon0`, `libdbus-1-3`, `libxcb-cursor0`, `libxcb-xinerama0`, `libxcb-icccm4`, `libxcb-image0`, `libxcb-keysyms1`, `libxcb-randr0`, `libxcb-render-util0`, `libxcb-shape0`, `libxkbcommon-x11-0`, `xvfb`, `python3.12-venv`.

### Optional heavy dependencies (not installed)

`torch`, `torchvision`, `transformers`, `timm`, `paddleocr` are listed in `requirements.txt` but are only needed for the mechanical schedule OCR/AI table detection feature. They add ~3-5 GB of downloads and are not required for core acoustic analysis functionality.

### Database

- Project data is stored in `~/Documents/AcousticAnalysis/acoustic_analysis.db` (auto-created on first run).
- Optional materials database: `materials/acoustic_materials.db` (1,339+ materials). If missing, the app falls back to 17 built-in materials.

### Gotchas

- The `initialize_database()` function expects a **file path** (e.g., `/tmp/test.db`), not a SQLAlchemy URL. It prepends `sqlite:///` internally.
- PySide6 requires a display server. For headless environments, always use `xvfb-run -a` or set `QT_QPA_PLATFORM=offscreen`.
- The Xvfb virtual framebuffer must be started before launching the app with `DISPLAY=:99`.
