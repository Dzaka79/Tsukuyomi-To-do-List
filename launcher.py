"""Launch Tsukuyomi To-do-List: start the Streamlit server and open a browser.

PyInstaller entry point for "Tsukuyomi TDL - Login.exe". Frozen mode bundles
ui-app.py + logic.py, serves them headless on a free local port, writes a log
next to the exe (console is hidden), and opens the default browser.
"""

from __future__ import annotations

import os
import shutil
import socket
import sys
import threading
import time
import webbrowser
from pathlib import Path


def _is_frozen() -> bool:
    return bool(getattr(sys, "frozen", False))


def _base_dir() -> Path:
    """Directory the app treats as its home (data/, assets/ live here)."""
    if _is_frozen():
        return Path(sys.argv[0]).resolve().parent
    return Path(__file__).resolve().parent


def _bundle_dir() -> Path:
    """Directory containing ui-app.py/logic.py (temp extraction when frozen)."""
    if _is_frozen():
        return Path(getattr(sys, "_MEIPASS", _base_dir())).resolve()
    return _base_dir()


def _redirect_stdio(base: Path) -> None:
    """With --noconsole, sys.stdout/stderr are None; log to a file instead."""
    if not _is_frozen():
        return
    if sys.stdout is None:
        try:
            # Line-buffered so the log is useful even if the app is killed.
            sys.stdout = open(
                base / "tsukuyomi_tdl.log",
                "w",
                encoding="utf-8",
                errors="replace",
                buffering=1,
            )
        except OSError:
            sys.stdout = open(os.devnull, "w", encoding="utf-8")
    if sys.stderr is None:
        sys.stderr = sys.stdout


def _materialize_assets(base: Path, bundle: Path) -> None:
    """Frozen builds bundle assets/ inside _MEIPASS (deleted after exit).

    Mirror any missing asset files next to the exe on first run so images
    resolve beside data/ and can be replaced by the user. Existing files are
    never overwritten.
    """
    src_root = bundle / "assets"
    if not src_root.is_dir() or base == bundle:
        return
    copied = 0
    for src in src_root.rglob("*"):
        if not src.is_file():
            continue
        dst = base / src.relative_to(bundle)
        if dst.is_file():
            continue
        try:
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(src, dst)
            copied += 1
        except OSError:
            pass
    if copied and sys.stdout is not None:
        print(f"launcher: materialized {copied} asset file(s) into {base}")


def _free_port(start: int = 8501, attempts: int = 100) -> int:
    for port in range(start, start + attempts):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            try:
                sock.bind(("127.0.0.1", port))
            except OSError:
                continue
            return port
    raise RuntimeError("No free port available for Tsukuyomi TDL.")


def _open_when_ready(port: int, url: str, timeout: float = 60.0) -> None:
    """Open the default browser once the Streamlit port accepts connections."""
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.settimeout(0.5)
            try:
                sock.connect(("127.0.0.1", port))
            except OSError:
                time.sleep(0.5)
                continue
        break
    webbrowser.open(url)


def main() -> None:
    base = _base_dir()
    os.chdir(base)
    _redirect_stdio(base)
    bundle = _bundle_dir()
    if _is_frozen():
        _materialize_assets(base, bundle)
    if str(bundle) not in sys.path:
        sys.path.insert(0, str(bundle))

    from streamlit.web import cli as stcli

    port = _free_port()
    url = f"http://localhost:{port}"
    threading.Thread(
        target=_open_when_ready, args=(port, url), daemon=True
    ).start()

    sys.argv = [
        "streamlit",
        "run",
        str(bundle / "ui-app.py"),
        "--server.headless",
        "true",
        "--server.address",
        "127.0.0.1",
        "--server.port",
        str(port),
        # PyInstaller's collected streamlit package is misdetected as a dev
        # checkout, which forbids an explicit server.port (and expects a
        # frontend dev server). Force a normal installed-mode runtime.
        "--global.developmentMode",
        "false",
        "--browser.gatherUsageStats",
        "false",
        "--theme.base",
        "dark",
        "--theme.primaryColor",
        "#6c8cff",
        "--theme.backgroundColor",
        "#111d33",
        "--theme.secondaryBackgroundColor",
        "#0c1526",
        "--theme.textColor",
        "#e7ecf5",
    ]
    sys.exit(stcli.main())


if __name__ == "__main__":
    main()
