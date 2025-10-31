# EsStat Copilot Guide

## Architecture Overview
- **main.py** (141 lines) - CLI entry point and main event loop; `printscreen` orchestrates the data fetcher task, Live UI updates, and keyboard event handling.
- **dashboard.py** (411 lines) - `Dashboard` class manages layout, panel specs, UI state (help/pause/edit modes), cached data, and rendering logic.
- **input_handler.py** (164 lines) - `KeyListener` captures async keyboard input in raw terminal mode; arrow key sequences parsed into events.
- **data_handler.py** (120 lines) - `DataHandler` wraps `aiohttp` GETs against ES (`_cluster/health`, `_cat/recovery`, `_cluster/settings`, `_cat/shards`) and filters fields via the constants declared at the top; new calls should stay async and whitelist the keys they expose.
## Architecture Overview
- **main.py** (141 lines) - CLI entry point and main event loop; `printscreen` orchestrates the data fetcher task, Live UI updates, and keyboard event handling.
- **dashboard.py** (411 lines) - `Dashboard` class manages layout, panel specs, UI state (help/pause/edit modes), cached data, and rendering logic.
- **input_handler.py** (164 lines) - `KeyListener` captures async keyboard input in raw terminal mode; arrow key sequences parsed into events.
- **data_handler.py** (120 lines) - `DataHandler` wraps `aiohttp` GETs against ES endpoints and filters fields via constants; all calls are async.

## Core Components

### Main Event Loop (`main.py`)
- **CLI Entry**: `click` command exposes `esstat <host> --port 9200` that runs `asyncio.run(printscreen)`.
- **printscreen**: Creates `Dashboard`, `DataHandler`, and `KeyListener`; runs `_data_fetcher` task and Live UI loop concurrently.
- **_data_fetcher**: Background task that calls `dashboard.refresh()` every 5s (respects pause mode); handles errors and updates error footer.
- **_handle_key_events**: Processes keyboard input (q/h/p/e, arrow keys for edit mode); updates Live UI on state changes.

### Dashboard Management (`dashboard.py`)
- **Dashboard Class**: Manages Rich layout, panel specifications, cached ES data, and UI state.
- **PanelSpec**: Dataclass defining panel key, title, data fetch callback, render callback, and display options (border, auto-height, etc.).
- **Layout Building**: `_build_layout` creates header/main split, side (status, settings, countdown) and body (recovery, relocation) panels.
- **State Management**: Tracks help mode, pause mode, edit mode, selected row, data readiness, and error messages.
- **UI Updates**: `update_ui` renders cached data into panels; `update_countdown` shows countdown/paused/loading state.
- **Dynamic Heights**: `_measure_height` and `_estimate_width` calculate panel dimensions based on content and terminal size.

### Input Handling (`input_handler.py`)
- **KeyListener**: Async keyboard input capture using event loop's `add_reader`.
- **raw_mode**: Context manager to set terminal to cbreak mode for character-by-character input.
- **parse_keys**: Buffers and parses escape sequences (e.g., `\x1b[A` → `"UP"`); handles incomplete sequences across reads.
- **Helper Functions**: `get_key_context` returns raw_mode or nullcontext; `create_key_listener` starts listener if stdin is TTY.

### Data Fetching (`data_handler.py`)
- **DataHandler**: Async context manager wrapping `aiohttp.ClientSession` for ES API calls.
- **_get**: Generic GET method with error handling (returns default on non-200 or ClientError).
- **get_status**: Fetches `_cluster/health`, filters by `STATE_FIELDS`.
- **get_settings**: Fetches `_cluster/settings?include_defaults=true&flat_settings=true`, merges defaults/persistent/transient, filters by `SETTING_FIELDS`.
- **get_recovery**: Fetches `_cat/recovery?active_only=true&format=json`.
- **get_relocations**: Fetches `_cat/shards?format=json`, splits `node` field into `source`/`target` for relocation arrows, filters out `"STARTED"` state.

## Rendering (`renderables/`)
- **Status Panel** `renderables/status.py` consumes the filtered cluster dict, uses `status_row` for color coding, and builds a `Tree`; reuse that helper to keep `✓/✖` and rounding rules consistent.
- **Settings Panel** `renderables/settings.py` renders `Table` + legend, highlighting substrings through `SHORTCUTS`; extend both the shortcuts tuple and the legend helpers when surfacing new settings.
- **Recovery & Relocation Tables** `renderables/recovery.py` and `renderables/relocation.py` iterate fixed `COLUMNS` tuples and call `empty_box` when nothing is active; preserve ordering and state filters like `FILTER_OUT = ("UNASSIGNED",)`.
- **Header Rendering** `renderables/header.py` implements `Header.__rich__` to supply a grid with app name, cluster, and timestamp each refresh; add header data by adding columns in that grid.
- **Empty States** `renderables/common.empty_box` is the canonical fallback; return it instead of raw strings whenever data is missing to avoid Live layout glitches.
- **Countdown Panel** `renderables/countdown.py` renders countdown timer, paused state, or loading spinner.

## Adding New Features

### New Dashboard Panel
1. Define fetch method in `DataHandler` (follow `_get` pattern, whitelist fields).
2. Create render function in `renderables/` (return Rich renderable or use `Panel`).
3. Add `PanelSpec` to `Dashboard._panels` tuple with key, title, fetch/render callbacks, and display options.
4. Update `Dashboard._build_layout` to add panel to layout tree.

### New Keyboard Shortcut
1. Add key handling in `main._handle_key_events`.
2. Implement corresponding method in `Dashboard` class.
3. Document in `renderables/settings.KEYBOARD_SHORTCUTS`.

### New ES Endpoint
- Follow the `_get` pattern in `DataHandler`, always pass `format=json` or `?flat_settings=true` where appropriate, and keep request URLs relative to `scheme://api:port/`.
- Define field whitelist constants (like `STATE_FIELDS`, `SETTING_FIELDS`) at top of `data_handler.py`.

## Development Guidelines
- **Runtime** Tooling targets Python ≥3.13 (see `.python-version` and `pyproject.toml`); create a venv, activate, then run `python -m pip install -e .` to expose the CLI while iterating.
- **Manual Checks** No automated tests exist; validate UI changes with `esstat localhost` .
- **Build Artifacts** Ignore the mirrored sources under `build/lib/esstat/`; all authoritative code lives in `esstat/`.
- **Async Caveat** `printscreen` uses blocking `time.sleep(5)` after awaiting data; if you introduce concurrent tasks, switch to `asyncio.sleep` but keep the 5s cadence so Live refresh stays smooth.
- **Error Handling** `_get` returns `{}` or `[]` on non-200 responses; downstream renderables must safely handle empty payloads instead of assuming keys exist.
- **Relocation Filters** `DataHandler.get_relocations` filters out `"STARTED"` states and the UI additionally hides `"UNASSIGNED"`; match those filters if you add more relocation views.
- **Auth & Schemes** `DataHandler` already accepts `port` and `scheme`; extend the initializer for auth tokens instead of baking credentials into URLs when secured clusters are required.
