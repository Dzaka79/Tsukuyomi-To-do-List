# AGENTS.md

## Project state

Tsukuyomi To-do-List — single-user Streamlit to-do app (Python 3.14).

- `SPEC.md` is the source of truth for features, data structure, and acceptance criteria — read it before changing behavior.
- `logic.py`: all pure logic (no Streamlit imports) + `test_logic.py` (54 passed, 9 skipped pending photos).
- `ui-app.py`: Streamlit UI (SPEC §1–§2), verified with an AppTest smoke pass and a real server boot.
- `launcher.py` + PyInstaller → `dist\Tsukuyomi TDL - Login.exe` (verified: boots, serves HTTP 200).
- Not a git repository. Windows (win32).

## Environment

- Python 3.14.0 venv at `.venv/`. Installed: `pip`, `pytest`, `streamlit` (1.66), `pyinstaller` (6.22).
- Run tools via `.venv\Scripts\python.exe` / `.venv\Scripts\streamlit.exe`; do not edit anything inside `.venv/`.

## Commands

- Tests: `.venv\Scripts\python.exe -m pytest test_logic.py -q` (verified: 54 passed, 9 skipped).
- Dev UI: `.venv\Scripts\streamlit.exe run ui-app.py` (theme via `.streamlit/config.toml`).
- Build exe (verified, ~3 min):
  `.venv\Scripts\pyinstaller.exe --noconfirm --clean --onefile --windowed --name "Tsukuyomi TDL - Login" --add-data "ui-app.py;." --add-data "logic.py;." --add-data "assets;assets" --collect-all streamlit launcher.py`

## Gotchas

- The UI fails fast (`st.error` + stop) until the 9 roster photos exist — inventory in SPEC §3.2. The 9 skipped pytest cases activate automatically once they are saved to `assets/characters/`. Do not weaken the skip guard.
- The frozen exe bundles `assets/` (photos + banner) inside itself and mirrors any missing files into `<exe_folder>\assets` on first run — never overwrites existing files there, so users customize images beside the exe. `data/tasks.json` is created beside the exe; the exe can be run from any folder. Logs to `tsukuyomi_tdl.log` beside the exe (console is hidden). `base == bundle` guard prevents self-copy when running the launcher unfrozen.
- Never remove `--global.developmentMode false` from `launcher.py`: PyInstaller's collected streamlit package is misdetected as a dev checkout and then rejects `--server.port`.
- Daily character/photo pick is deterministic per date (seeded `random.Random`, SPEC §2.9) — take the date as a parameter; no persistence, no `date.today()` inside `daily_pick()`.
- `load_store()` must stay crash-tolerant: missing/corrupt/bad-schema files return the default empty store (SPEC §2.8 / AC18).
- Widget callbacks in `ui-app.py` are `on_click`/`on_change` (they run before the rerun so the message box, rendered earlier in the script, shows the fresh text). Message-changing logic must stay in callbacks, not inline after widgets.
- Streamlit 1.66 AppTest quirks: buttons need `.click().run()` (an explicit run; `click()` alone does nothing); form `text_input`s ignore `.set_value()` — set `at.session_state["text_<mission>"]` directly after opening the form; `st.components.v1.html` is deprecated — use `st.iframe(..., height=1)` for the shortcut-scroll script.
- When adding a manifest (`pyproject.toml`/`requirements.txt`), pin the deps actually installed and update the commands above.
