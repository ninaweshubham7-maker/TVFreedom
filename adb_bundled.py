"""
Bundled ADB Management - Internal ADB binary discovery and management.

This module handles locating the bundled ADB executable (platform-tools/adb.exe)
within the application's installation directory, with fallback to system PATH.

Google's Android SDK Platform Tools are licensed under the Apache License 2.0,
which permits redistribution. The adb.exe binary can be bundled with TV Freedom
to eliminate the manual ADB installation requirement for end users.
"""

import os
import sys
import shutil
import subprocess
from pathlib import Path
from typing import Optional


def get_application_root() -> Path:
    """
    Get the root directory of the TV Freedom application.
    
    Works for both development (source tree) and packaged (PyInstaller, etc.) deployments.
    
    Returns:
        Path to the application root directory.
    """
    # For PyInstaller frozen executables
    if getattr(sys, 'frozen', False):
        # sys.executable is the path to the frozen executable
        return Path(sys.executable).parent
    
    # For development: this file is in the project root
    return Path(__file__).parent


def get_bundled_adb_path() -> Optional[Path]:
    """
    Get the path to the bundled ADB executable.
    
    Searches for adb.exe in the bundled platform-tools directory.
    
    Returns:
        Path to adb.exe if found, None otherwise.
    """
    app_root = get_application_root()
    
    # Standard bundled locations
    candidates = [
        app_root / "platform-tools" / "adb.exe",           # Windows
        app_root / "platform-tools" / "adb",               # Linux/macOS
        app_root / "bin" / "platform-tools" / "adb.exe",   # Alternative Windows
        app_root / "bin" / "platform-tools" / "adb",       # Alternative Linux/macOS
        app_root / "resources" / "platform-tools" / "adb.exe",
        app_root / "resources" / "platform-tools" / "adb",
    ]
    
    for candidate in candidates:
        if candidate.exists() and candidate.is_file():
            # Verify it's executable (on Windows, .exe is sufficient)
            if sys.platform == "win32" or os.access(candidate, os.X_OK):
                return candidate
    
    return None


def get_adb_path(prefer_bundled: bool = True) -> Optional[str]:
    """
    Get the ADB executable path, checking bundled location first.
    
    Args:
        prefer_bundled: If True, check bundled location before system PATH.
        
    Returns:
        Absolute path to adb executable as string, or None if not found.
    """
    if prefer_bundled:
        bundled = get_bundled_adb_path()
        if bundled:
            return str(bundled)
    
    # Fallback to system PATH
    system_adb = shutil.which("adb")
    if system_adb:
        return system_adb
    
    return None


def check_adb_available(prefer_bundled: bool = True) -> tuple[bool, Optional[str]]:
    """
    Check if ADB is available (bundled or system).
    
    Args:
        prefer_bundled: If True, check bundled location first.
        
    Returns:
        Tuple of (available, path_or_none).
    """
    path = get_adb_path(prefer_bundled=prefer_bundled)
    if path:
        return True, path
    return False, None


def is_using_bundled_adb() -> bool:
    """
    Check if the currently resolved ADB path is the bundled one.
    
    Returns:
        True if using bundled ADB, False if using system ADB or not available.
    """
    bundled = get_bundled_adb_path()
    if not bundled:
        return False
    
    current = get_adb_path(prefer_bundled=True)
    if not current:
        return False
    
    return Path(current).resolve() == bundled.resolve()


def get_adb_version(adb_path: Optional[str] = None) -> Optional[str]:
    """
    Get the ADB version string.
    
    Args:
        adb_path: Optional explicit ADB path. If None, uses discovery.
        
    Returns:
        Version string (e.g., "Android Debug Bridge version 1.0.41"), or None on failure.
    """
    if adb_path is None:
        adb_path = get_adb_path()
    
    if not adb_path:
        return None
    
    import subprocess
    try:
        result = subprocess.run(
            [adb_path, "version"],
            capture_output=True,
            text=True,
            timeout=5,
            check=False,
        )
        if result.returncode == 0:
            # Output format: "Android Debug Bridge version 1.0.41\nVersion 34.0.5-12345678\nInstalled as /path/to/adb"
            lines = result.stdout.strip().split('\n')
            if lines:
                return lines[0]
    except Exception:
        pass
    return None


def get_bundled_adb_info() -> dict:
    """
    Get information about the bundled ADB availability.
    
    Returns:
        Dictionary with keys: available, path, version, is_bundled
    """
    bundled_path = get_bundled_adb_path()
    system_path = shutil.which("adb")
    active_path = get_adb_path(prefer_bundled=True)
    
    info = {
        "bundled_available": bundled_path is not None,
        "bundled_path": str(bundled_path) if bundled_path else None,
        "system_available": system_path is not None,
        "system_path": system_path,
        "active_path": active_path,
        "using_bundled": is_using_bundled_adb(),
        "version": None,
    }
    
    if active_path:
        info["version"] = get_adb_version(active_path)
    
    return info