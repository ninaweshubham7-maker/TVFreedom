"""Launch TV Freedom in an Edge app window with a local Streamlit server."""

import ctypes
import os
import socket
import subprocess
import sys
import time
import traceback
import urllib.error
import urllib.request
import winreg
from pathlib import Path

from streamlit.web import cli as stcli

SERVER_MODE = "--tvfreedom-streamlit-server"
STARTUP_TIMEOUT_SECONDS = 45


def get_project_root() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parents[1]


def find_edge() -> Path:
    candidates = [
        Path(os.environ.get("ProgramFiles(x86)", "C:/Program Files (x86)"))
        / "Microsoft/Edge/Application/msedge.exe",
        Path(os.environ.get("ProgramFiles", "C:/Program Files"))
        / "Microsoft/Edge/Application/msedge.exe",
        Path(os.environ.get("LOCALAPPDATA", ""))
        / "Microsoft/Edge/Application/msedge.exe",
    ]

    for key_path in (
        r"SOFTWARE\Microsoft\Windows\CurrentVersion\App Paths\msedge.exe",
        r"SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\App Paths\msedge.exe",
    ):
        try:
            with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, key_path) as key:
                executable, _ = winreg.QueryValueEx(key, None)
            candidates.append(Path(executable.strip('"')))
        except OSError:
            pass

    for candidate in candidates:
        if candidate.is_file():
            return candidate.resolve()
    raise FileNotFoundError(
        "Microsoft Edge is required to show TV Freedom in a desktop app window."
    )


def get_log_path() -> Path:
    local_app_data = Path(
        os.environ.get("LOCALAPPDATA", Path.home() / "AppData" / "Local")
    )
    log_dir = local_app_data / "TVFreedom" / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    return log_dir / "desktop-launcher.log"


def get_available_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as listener:
        listener.bind(("127.0.0.1", 0))
        return listener.getsockname()[1]


def run_streamlit_server(app_path: Path, server_args: list[str]) -> None:
    sys.argv = [
        "streamlit",
        "run",
        str(app_path),
        "--global.developmentMode=false",
        "--server.headless=true",
        "--server.address=127.0.0.1",
        "--browser.gatherUsageStats=false",
        *server_args,
    ]
    stcli.main()


def wait_for_server(process: subprocess.Popen, url: str, log_path: Path) -> None:
    deadline = time.monotonic() + STARTUP_TIMEOUT_SECONDS
    health_url = f"{url}/_stcore/health"

    while time.monotonic() < deadline:
        if process.poll() is not None:
            details = log_path.read_text(encoding="utf-8", errors="replace")[-4000:]
            raise RuntimeError(
                f"The local TV Freedom server exited during startup. See {log_path}.\n"
                f"{details}"
            )
        try:
            with urllib.request.urlopen(health_url, timeout=1) as response:
                if response.status == 200:
                    return
        except (OSError, urllib.error.URLError):
            time.sleep(0.25)

    raise TimeoutError(
        f"TV Freedom did not start within {STARTUP_TIMEOUT_SECONDS} seconds. "
        f"See {log_path}."
    )


def stop_server(process: subprocess.Popen) -> None:
    if process.poll() is not None:
        return
    process.terminate()
    try:
        process.wait(timeout=5)
    except subprocess.TimeoutExpired:
        process.kill()
        process.wait(timeout=5)


def show_error(message: str) -> None:
    ctypes.windll.user32.MessageBoxW(None, message, "TV Freedom", 0x10)


def run_desktop_app() -> None:
    project_root = get_project_root()
    app_path = project_root / "app.py"
    if not app_path.is_file():
        raise FileNotFoundError(f"TV Freedom app.py not found: {app_path}")

    edge = find_edge()
    port = get_available_port()
    url = f"http://127.0.0.1:{port}"
    log_path = get_log_path()
    user_data = Path(
        os.environ.get("LOCALAPPDATA", Path.home() / "AppData" / "Local")
    ) / "TVFreedom" / "EdgeProfile"
    user_data.mkdir(parents=True, exist_ok=True)

    server_command = [sys.executable]
    if not getattr(sys, "frozen", False):
        server_command.append(str(Path(__file__).resolve()))
    server_command.extend([SERVER_MODE, f"--server.port={port}"])

    with log_path.open("a", encoding="utf-8") as log_file:
        log_file.write(f"\nStarting TV Freedom at {url}\n")
        log_file.flush()
        server = subprocess.Popen(
            server_command,
            cwd=project_root,
            stdin=subprocess.DEVNULL,
            stdout=log_file,
            stderr=subprocess.STDOUT,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )

    edge_process = None
    try:
        wait_for_server(server, url, log_path)
        edge_process = subprocess.Popen(
            [
                str(edge),
                f"--app={url}",
                f"--user-data-dir={user_data}",
                "--no-first-run",
                "--no-default-browser-check",
            ],
            cwd=project_root,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
        return_code = edge_process.wait()
        if return_code:
            raise RuntimeError(
                f"Microsoft Edge app window exited with code {return_code}."
            )
    finally:
        stop_server(server)


def main() -> None:
    if SERVER_MODE in sys.argv[1:]:
        marker_index = sys.argv.index(SERVER_MODE)
        server_args = sys.argv[marker_index + 1 :]
        run_streamlit_server(get_project_root() / "app.py", server_args)
        return

    try:
        run_desktop_app()
    except Exception as error:
        try:
            log_path = get_log_path()
            with log_path.open("a", encoding="utf-8") as log_file:
                log_file.write(traceback.format_exc())
        except OSError:
            log_path = Path("desktop-launcher.log")
        show_error(f"{error}\n\nLauncher details: {log_path}")


if __name__ == "__main__":
    main()
