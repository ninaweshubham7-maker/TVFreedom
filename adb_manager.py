"""
ADB Manager - Real device connectivity for TV Freedom.

This module provides ADB connectivity for compatible Android TV and Google TV
devices over USB and Wi-Fi/network connections. Diagnostics use a read-only
command path; device mutations are exposed only through separate, explicit,
allowlisted methods pinned to the selected device.
"""

from dataclasses import dataclass, field
from enum import Enum
import subprocess
import shutil
import time
import json
import os
import re
from typing import Optional
from pathlib import Path

from adb_bundled import get_adb_path, check_adb_available as bundled_check_adb_available, is_using_bundled_adb, get_adb_version


class ADBState(Enum):
    """Possible ADB connection states."""
    UNAVAILABLE = "unavailable"          # ADB executable not found
    NO_DEVICE = "no_device"              # No devices detected
    UNAUTHORIZED = "unauthorized"        # Device unauthorized (needs TV approval)
    OFFLINE = "offline"                  # Device offline
    CONNECTED = "connected"              # Successfully connected
    ERROR = "error"                      # Connection error


@dataclass(frozen=True)
class ADBDevice:
    """Represents a detected ADB device."""
    serial: str
    state: str  # "device", "unauthorized", "offline"
    connection_type: str  # "usb" or "tcpip"
    ip_port: str | None = None  # For TCP/IP connections
    # Extended device info (populated after connection)
    manufacturer: str | None = None
    model: str | None = None
    android_version: str | None = None
    api_level: int | None = None
    cpu_abi: str | None = None
    build_fingerprint: str | None = None
    screen_resolution: str | None = None
    screen_density: int | None = None
    device_codename: str | None = None
    board: str | None = None
    default_launcher: str | None = None
    uptime_seconds: int | None = None
    memory_total_mb: int | None = None
    memory_available_mb: int | None = None
    platform_type: str | None = None  # "android_tv", "google_tv", "fire_tv", "unknown"
    compatibility_notes: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class ADBConnectionResult:
    """Result of a connection attempt."""
    success: bool
    state: ADBState
    device: ADBDevice | None
    message: str
    error_details: str | None = None


class ADBManager:
    """
    Manages ADB connections to Android TV / Google TV devices.

    Ordinary shell diagnostics are read-only. Package changes and launcher
    installation use separate guarded methods with explicit allowlists.
    """
    
    # Read-only ADB commands that are safe to execute
    SAFE_COMMANDS = {
        "devices": ["devices", "-l"],
        "getprop": ["shell", "getprop"],
        "shell_getprop": ["shell", "getprop"],
    }
    
    # Default ADB ports for network connections
    DEFAULT_ADB_PORT = 5555
    
    def __init__(self, adb_path: str | None = None, timeout: int = 10):
        """
        Initialize the ADB Manager.
        
        Args:
            adb_path: Optional path to ADB executable. If None, searches bundled location first, then PATH.
            timeout: Default timeout in seconds for ADB commands.
        """
        self._adb_path = adb_path or get_adb_path(prefer_bundled=True)
        self._timeout = timeout
        self._connected_device: ADBDevice | None = None
        self._connection_state = ADBState.UNAVAILABLE if not self._adb_path else ADBState.NO_DEVICE
        self._last_error: str | None = None
    
    @staticmethod
    def _find_adb() -> str | None:
        """Find ADB executable - checks bundled location first, then PATH."""
        return get_adb_path(prefer_bundled=True)
    
    @property
    def adb_path(self) -> str | None:
        """Get the ADB executable path."""
        return self._adb_path
    
    @property
    def is_adb_available(self) -> bool:
        """Check if ADB executable is available."""
        return self._adb_path is not None
    
    @property
    def connection_state(self) -> ADBState:
        """Get current connection state."""
        return self._connection_state
    
    @property
    def connected_device(self) -> ADBDevice | None:
        """Get currently connected device."""
        return self._connected_device
    
    @property
    def last_error(self) -> str | None:
        """Get last error message."""
        return self._last_error
    
    def _run_adb(self, args: list[str], timeout: int | None = None) -> tuple[bool, str, str]:
        """
        Run an ADB command safely.
        
        Args:
            args: Command arguments (without 'adb' prefix)
            timeout: Command timeout in seconds
            
        Returns:
            Tuple of (success, stdout, stderr)
        """
        if not self._adb_path:
            return False, "", "ADB executable not found"
        
        cmd = [self._adb_path] + args
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=timeout or self._timeout,
                check=False,
            )
            return result.returncode == 0, result.stdout, result.stderr
        except subprocess.TimeoutExpired:
            return False, "", f"Command timed out after {timeout or self._timeout} seconds"
        except FileNotFoundError:
            return False, "", "ADB executable not found"
        except Exception as e:
            return False, "", f"Unexpected error: {e}"
    
    def get_usb_devices(self) -> list[ADBDevice]:
        """
        Get list of USB-connected ADB devices.
        
        Returns:
            List of ADBDevice objects for USB devices.
        """
        success, stdout, stderr = self._run_adb(["devices", "-l"])
        if not success:
            self._last_error = f"Failed to list devices: {stderr}"
            return []
        
        devices = []
        for line in stdout.strip().split('\n')[1:]:  # Skip header
            line = line.strip()
            if not line:
                continue
            parts = line.split()
            if len(parts) >= 2:
                serial = parts[0]
                state = parts[1]
                # Check if it's a USB device (no IP:port in serial)
                if ':' not in serial:
                    devices.append(ADBDevice(
                        serial=serial,
                        state=state,
                        connection_type="usb",
                    ))
        return devices
    
    def connect_usb(self, serial: str | None = None) -> ADBConnectionResult:
        """
        Connect to a USB device.
        
        Args:
            serial: Optional specific device serial. If None, uses first available.
            
        Returns:
            ADBConnectionResult with connection status.
        """
        if not self._adb_path:
            return ADBConnectionResult(
                success=False,
                state=ADBState.UNAVAILABLE,
                device=None,
                message="ADB not available. Bundled ADB is missing and no system ADB found.",
                error_details="TV Freedom includes bundled ADB. If you see this error, the application package may be incomplete. Contact support or re-install.",
            )
        
        devices = self.get_usb_devices()
        if not devices:
            self._connection_state = ADBState.NO_DEVICE
            return ADBConnectionResult(
                success=False,
                state=ADBState.NO_DEVICE,
                device=None,
                message="No USB devices detected. Connect your TV via USB and enable USB debugging.",
                error_details="Run 'adb devices' to verify. Check USB cable and TV settings.",
            )
        
        target_device = None
        if serial:
            target_device = next((d for d in devices if d.serial == serial), None)
            if not target_device:
                return ADBConnectionResult(
                    success=False,
                    state=ADBState.ERROR,
                    device=None,
                    message=f"Device with serial '{serial}' not found.",
                    error_details=f"Available devices: {[d.serial for d in devices]}",
                )
        else:
            target_device = devices[0]
        
        # Check device state
        if target_device.state == "unauthorized":
            self._connection_state = ADBState.UNAUTHORIZED
            return ADBConnectionResult(
                success=False,
                state=ADBState.UNAUTHORIZED,
                device=target_device,
                message="Device unauthorized. Accept the USB debugging prompt on your TV.",
                error_details="Check your TV screen for the authorization dialog. Enable 'Always allow from this computer'.",
            )
        elif target_device.state == "offline":
            self._connection_state = ADBState.OFFLINE
            return ADBConnectionResult(
                success=False,
                state=ADBState.OFFLINE,
                device=target_device,
                message="Device is offline. Try reconnecting the USB cable.",
                error_details="Device not responding to ADB. Check USB connection and TV power state.",
            )
        elif target_device.state != "device":
            self._connection_state = ADBState.ERROR
            return ADBConnectionResult(
                success=False,
                state=ADBState.ERROR,
                device=target_device,
                message=f"Device in unexpected state: {target_device.state}",
                error_details=f"Serial: {target_device.serial}, State: {target_device.state}",
            )
        
        # Device is authorized and online
        self._connected_device = target_device
        self._connection_state = ADBState.CONNECTED
        self._last_error = None
        return ADBConnectionResult(
            success=True,
            state=ADBState.CONNECTED,
            device=target_device,
            message=f"Connected to {target_device.serial} via USB",
            error_details=None,
        )
    
    def connect_network(self, ip: str, port: int = DEFAULT_ADB_PORT) -> ADBConnectionResult:
        """
        Connect to a device over network (TCP/IP).
        
        Args:
            ip: TV IP address
            port: ADB port (default 5555)
            
        Returns:
            ADBConnectionResult with connection status.
        """
        if not self._adb_path:
            return ADBConnectionResult(
                success=False,
                state=ADBState.UNAVAILABLE,
                device=None,
                message="ADB not available. Bundled ADB is missing and no system ADB found.",
                error_details="TV Freedom includes bundled ADB. If you see this error, the application package may be incomplete. Contact support or re-install.",
            )
        
        # Validate IP format
        if not self._is_valid_ip(ip):
            return ADBConnectionResult(
                success=False,
                state=ADBState.ERROR,
                device=None,
                message=f"Invalid IP address: {ip}",
                error_details="Please enter a valid IPv4 address (e.g., 192.168.1.100)",
            )
        
        if not (1 <= port <= 65535):
            return ADBConnectionResult(
                success=False,
                state=ADBState.ERROR,
                device=None,
                message=f"Invalid port: {port}",
                error_details="Port must be between 1 and 65535",
            )
        
        ip_port = f"{ip}:{port}"
        
        # First, try to connect
        success, stdout, stderr = self._run_adb(["connect", ip_port], timeout=15)
        if not success:
            self._connection_state = ADBState.ERROR
            self._last_error = stderr
            return ADBConnectionResult(
                success=False,
                state=ADBState.ERROR,
                device=None,
                message=f"Failed to connect to {ip_port}",
                error_details=stderr or "Connection refused or timeout. Verify IP, port, and network ADB is enabled on TV.",
            )
        
        # Check connection result
        output = stdout.strip().lower()
        if "connected" not in output and "already connected" not in output:
            self._connection_state = ADBState.ERROR
            return ADBConnectionResult(
                success=False,
                state=ADBState.ERROR,
                device=None,
                message=f"Unexpected connection response: {stdout}",
                error_details=stderr,
            )
        
        # Verify device is now listed
        devices = self.get_all_devices()
        target_device = next((d for d in devices if d.ip_port == ip_port or d.serial == ip_port), None)
        
        if not target_device:
            # Try to find by serial matching IP:port
            target_device = next((d for d in devices if ip_port in d.serial), None)
        
        if not target_device:
            self._connection_state = ADBState.ERROR
            return ADBConnectionResult(
                success=False,
                state=ADBState.ERROR,
                device=None,
                message=f"Connected to {ip_port} but device not visible in device list",
                error_details="Device may be unauthorized or offline. Check TV for authorization prompt.",
            )
        
        # Check device state
        if target_device.state == "unauthorized":
            self._connection_state = ADBState.UNAUTHORIZED
            return ADBConnectionResult(
                success=False,
                state=ADBState.UNAUTHORIZED,
                device=target_device,
                message="Device unauthorized. Accept the wireless debugging prompt on your TV.",
                error_details="Check your TV screen for the authorization dialog.",
            )
        elif target_device.state == "offline":
            self._connection_state = ADBState.OFFLINE
            return ADBConnectionResult(
                success=False,
                state=ADBState.OFFLINE,
                device=target_device,
                message="Device is offline after connection.",
                error_details="Network connection unstable or TV went to sleep.",
            )
        elif target_device.state != "device":
            self._connection_state = ADBState.ERROR
            return ADBConnectionResult(
                success=False,
                state=ADBState.ERROR,
                device=target_device,
                message=f"Device in unexpected state: {target_device.state}",
                error_details=f"Serial: {target_device.serial}, State: {target_device.state}",
            )
        
        self._connected_device = target_device
        self._connection_state = ADBState.CONNECTED
        self._last_error = None
        return ADBConnectionResult(
            success=True,
            state=ADBState.CONNECTED,
            device=target_device,
            message=f"Connected to {ip_port} via network",
            error_details=None,
        )

    def pair_wireless(self, ip: str, pairing_port: int, pairing_code: str) -> ADBConnectionResult:
        """
        Pair with a device using Android 11+ wireless debugging pairing.
        
        Args:
            ip: TV IP address
            pairing_port: Pairing port (different from connection port)
            pairing_code: 6-8 digit pairing code shown on TV
            
        Returns:
            ADBConnectionResult with pairing status.
        """
        if not self._adb_path:
            return ADBConnectionResult(
                success=False,
                state=ADBState.UNAVAILABLE,
                device=None,
                message="ADB not available. Bundled ADB is missing and no system ADB found.",
                error_details="TV Freedom includes bundled ADB. If you see this error, the application package may be incomplete. Contact support or re-install.",
            )
        
        if not self._is_valid_ip(ip):
            return ADBConnectionResult(
                success=False,
                state=ADBState.ERROR,
                device=None,
                message=f"Invalid IP address: {ip}",
                error_details="Please enter a valid IPv4 address (e.g., 192.168.1.100)",
            )
        
        if not (1 <= pairing_port <= 65535):
            return ADBConnectionResult(
                success=False,
                state=ADBState.ERROR,
                device=None,
                message=f"Invalid pairing port: {pairing_port}",
                error_details="Port must be between 1 and 65535",
            )
        
        if not pairing_code or not pairing_code.isdigit() or not (6 <= len(pairing_code) <= 8):
            return ADBConnectionResult(
                success=False,
                state=ADBState.ERROR,
                device=None,
                message="Invalid pairing code",
                error_details="Pairing code must be 6-8 digits as shown on your TV",
            )
        
        ip_port = f"{ip}:{pairing_port}"
        
        # Run adb pair command
        success, stdout, stderr = self._run_adb(["pair", ip_port, pairing_code], timeout=30)
        if not success:
            self._connection_state = ADBState.ERROR
            self._last_error = stderr
            return ADBConnectionResult(
                success=False,
                state=ADBState.ERROR,
                device=None,
                message=f"Pairing failed with {ip_port}",
                error_details=stderr or "Check pairing code, IP, and port. Ensure wireless debugging is active on TV.",
            )
        
        output = stdout.strip().lower()
        if "successfully paired" not in output and "paired" not in output:
            self._connection_state = ADBState.ERROR
            return ADBConnectionResult(
                success=False,
                state=ADBState.ERROR,
                device=None,
                message=f"Unexpected pairing response: {stdout}",
                error_details=stderr,
            )
        
        self._last_error = None
        return ADBConnectionResult(
            success=True,
            state=ADBState.CONNECTED,
            device=None,  # Will need to connect separately after pairing
            message=f"Successfully paired with {ip}:{pairing_port}. Now connect using the connection port.",
            error_details=None,
        )

    def connect_after_pairing(self, ip: str, connection_port: int = DEFAULT_ADB_PORT) -> ADBConnectionResult:
        """
        Connect to a device after successful wireless pairing.
        This uses the standard network connection but the device should already be paired.
        
        Args:
            ip: TV IP address
            connection_port: ADB connection port (typically different from pairing port)
            
        Returns:
            ADBConnectionResult with connection status.
        """
        return self.connect_network(ip, connection_port)
    
    def disconnect(self) -> bool:
        """
        Disconnect from the current device.
        
        For network connections, runs 'adb disconnect'.
        For USB, simply clears the connection state.
        
        Returns:
            True if disconnect was attempted, False if not connected.
        """
        if not self._connected_device:
            return False
        
        if self._connected_device.connection_type == "tcpip" and self._adb_path:
            ip_port = self._connected_device.ip_port or self._connected_device.serial
            self._run_adb(["disconnect", ip_port], timeout=5)
        
        self._connected_device = None
        self._connection_state = ADBState.NO_DEVICE if self._adb_path else ADBState.UNAVAILABLE
        self._last_error = None
        return True
    
    def get_all_devices(self) -> list[ADBDevice]:
        """
        Get all detected devices (USB and network).
        
        Returns:
            List of all ADBDevice objects.
        """
        success, stdout, stderr = self._run_adb(["devices", "-l"])
        if not success:
            self._last_error = f"Failed to list devices: {stderr}"
            return []
        
        devices = []
        for line in stdout.strip().split('\n')[1:]:  # Skip header
            line = line.strip()
            if not line:
                continue
            parts = line.split()
            if len(parts) >= 2:
                serial = parts[0]
                state = parts[1]
                # Determine connection type
                if ':' in serial and not serial.startswith('emulator-'):
                    connection_type = "tcpip"
                    ip_port = serial
                else:
                    connection_type = "usb"
                    ip_port = None
                devices.append(ADBDevice(
                    serial=serial,
                    state=state,
                    connection_type=connection_type,
                    ip_port=ip_port,
                ))
        return devices
    
    def run_package_action(self, action: str, package_name: str) -> tuple[bool, str, str]:
        """Execute one explicitly allowlisted package-management action.

        The ordinary ``run_shell_command`` path remains read-only. Mutations are
        deliberately separated, restricted to package operations, validated
        against a package-name pattern, and pinned to the currently connected
        device serial so a second attached device cannot be modified by mistake.
        """
        import re

        if not self._connected_device:
            return False, "", "No device connected"
        if self._connection_state != ADBState.CONNECTED:
            return False, "", f"Device not connected (state: {self._connection_state.value})"
        if not isinstance(package_name, str) or len(package_name) > 255 or not re.fullmatch(
            r"[A-Za-z_][A-Za-z0-9_]*(?:\.[A-Za-z_][A-Za-z0-9_]*)+",
            package_name,
        ):
            return False, "", "Invalid Android package name"
        allowed_actions = {
            "disable": ["shell", "pm", "disable-user", package_name],
            "enable": ["shell", "pm", "enable", package_name],
            # Only uninstall user-installed apps through the UI; this operation
            # is still guarded by PackageClassifier and explicit confirmation.
            "uninstall": ["shell", "pm", "uninstall", package_name],
        }
        if action not in allowed_actions:
            return False, "", f"Package action not allowed: {action}"
        args = ["-s", self._connected_device.serial] + allowed_actions[action]
        return self._run_adb(args, timeout=30)

    def install_tv_freedom_launcher(self, apk_path: str) -> tuple[bool, str, str]:
        """Install only the project's built TV Freedom launcher APK.

        This intentionally does not expose a generic APK installer. The path
        must be the expected build output under this application's launcher
        source tree, and the command is pinned to the selected device.
        """
        if not self._connected_device:
            return False, "", "No device connected"
        if self._connection_state != ADBState.CONNECTED:
            return False, "", f"Device not connected (state: {self._connection_state.value})"
        expected = (Path(__file__).resolve().parent / "launcher-android" / "app" / "build" / "outputs" / "apk" / "debug" / "app-debug.apk").resolve()
        supplied = Path(apk_path).resolve()
        if supplied != expected:
            return False, "", "Only the TV Freedom launcher build output can be installed from this screen"
        if not supplied.is_file():
            return False, "", "Launcher APK not built yet. Build it from launcher-android in Android Studio first."
        return self._run_adb(["-s", self._connected_device.serial, "install", "-r", str(supplied)], timeout=120)

    @staticmethod
    def _is_read_only_shell_command(command: str) -> bool:
        """Accept only complete, explicitly read-only diagnostic command forms."""
        if not isinstance(command, str) or not command or len(command) > 2048:
            return False

        package_pattern = r"[A-Za-z_][A-Za-z0-9_]*(?:\.[A-Za-z_][A-Za-z0-9_]*)+"

        def valid_package(value: str) -> bool:
            return len(value) <= 255 and re.fullmatch(package_pattern, value) is not None

        def valid_path(value: str) -> bool:
            if not value.startswith("/"):
                return False
            segments = value.strip("/").split("/")
            return bool(segments) and all(
                segment not in {"", ".", ".."}
                and re.fullmatch(r"[A-Za-z0-9_.-]+", segment)
                for segment in segments
            )

        if re.fullmatch(r"getprop(?: [A-Za-z0-9_.-]+)?", command):
            return True
        if re.fullmatch(r"(?:cat|ls|df) /[A-Za-z0-9_./-]+/?", command):
            path = command.split(" ", 1)[1]
            return valid_path(path)
        if re.fullmatch(
            r"cat /sys/devices/system/cpu/cpu[0-9]+/cpufreq/"
            r"(?:scaling_cur_freq|cpuinfo_cur_freq|scaling_max_freq|cpuinfo_max_freq)"
            r" 2>/dev/null \|\| cat /sys/devices/system/cpu/cpu[0-9]+/cpufreq/"
            r"(?:scaling_cur_freq|cpuinfo_cur_freq|scaling_max_freq|cpuinfo_max_freq)"
            r" 2>/dev/null",
            command,
        ):
            return True
        if command in {
            "dumpsys battery",
            "dumpsys display",
            "dumpsys meminfo",
            "dumpsys package",
            "dumpsys batterystats --short",
            "dumpsys SurfaceFlinger --latency",
            "ip addr show",
            "getenforce",
            "wm size",
            "wm density",
            "pm get-install-location",
            "cmd package resolve-activity --brief android.intent.action.MAIN android.intent.category.HOME",
        }:
            return True
        if re.fullmatch(r"dumpsys (?:wifi|connectivity) \| head -50", command):
            return True
        if re.fullmatch(rf"dumpsys package {package_pattern}", command):
            return valid_package(command.rsplit(" ", 1)[1])
        if re.fullmatch(
            rf"(?:pm dump|dumpsys package) {package_pattern} \| grep -A1 'label='",
            command,
        ):
            return valid_package(command.split(" ")[2])
        if re.fullmatch(r"pm list packages(?: -(?:f|e|d|s|3))?", command):
            return True
        if command == "pm list packages -c android.intent.category.HOME":
            return True
        if re.fullmatch(rf"pm (?:path|get-installer) {package_pattern}", command):
            return valid_package(command.rsplit(" ", 1)[1])
        if re.fullmatch(r"settings get (?:global|secure|system) [A-Za-z0-9_.-]+", command):
            return True
        return re.fullmatch(
            r"which (?:screenrecord|screencap|input|settings|pm|am)", command
        ) is not None

    def run_shell_command(self, command: str) -> tuple[bool, str, str]:
        """
        Run a read-only shell command on the connected device.
        
        Args:
            command: Shell command to run (e.g., "getprop ro.product.model")
            
        Returns:
            Tuple of (success, stdout, stderr)
        """
        if not self._connected_device:
            return False, "", "No device connected"
        
        if self._connection_state != ADBState.CONNECTED:
            return False, "", f"Device not connected (state: {self._connection_state.value})"
        
        if not self._is_read_only_shell_command(command):
            return False, "", f"Command not allowed: {command}. Only read-only diagnostic commands permitted."
        
        return self._run_adb(["-s", self._connected_device.serial, "shell", command])
    
    def get_device_properties(self) -> dict[str, str]:
        """
        Get key device properties via getprop.
        
        Returns:
            Dictionary of property key-value pairs.
        """
        props = {}
        key_props = [
            "ro.product.manufacturer",
            "ro.product.model",
            "ro.product.brand",
            "ro.build.version.release",
            "ro.build.version.sdk",
            "ro.build.id",
            "ro.product.cpu.abi",
            "ro.build.characteristics",
        ]
        
        for prop in key_props:
            success, stdout, stderr = self.run_shell_command(f"getprop {prop}")
            if success and stdout.strip():
                props[prop] = stdout.strip()
            else:
                props[prop] = "Unknown"
        
        return props
    
    def get_storage_info(self) -> dict[str, str]:
        """
        Get storage information via df.
        
        Returns:
            Dictionary with storage details.
        """
        success, stdout, stderr = self.run_shell_command("df /data")
        if not success:
            return {"error": stderr or "Failed to get storage info"}
        
        lines = stdout.strip().split('\n')
        if len(lines) >= 2:
            parts = lines[1].split()
            if len(parts) >= 4:
                # df output: Filesystem 1K-blocks Used Available Use% Mounted on
                total_kb = int(parts[1])
                used_kb = int(parts[2])
                free_kb = int(parts[3])
                return {
                    "total_gb": round(total_kb / 1024 / 1024, 2),
                    "used_gb": round(used_kb / 1024 / 1024, 2),
                    "free_gb": round(free_kb / 1024 / 1024, 2),
                    "free_percent": round(free_kb / total_kb * 100, 1) if total_kb > 0 else 0,
                }
        return {"error": "Could not parse storage info"}

    def get_extended_device_info(self) -> ADBDevice:
        """
        Get comprehensive device information and return an updated ADBDevice.
        
        This retrieves all available device properties for identification and diagnostics.
        
        Returns:
            Updated ADBDevice with extended information.
        """
        if not self._connected_device or self._connection_state != ADBState.CONNECTED:
            return self._connected_device
        
        # Get all properties
        props = {}
        extended_props = [
            "ro.product.manufacturer",
            "ro.product.model",
            "ro.product.brand",
            "ro.product.device",
            "ro.product.board",
            "ro.build.version.release",
            "ro.build.version.sdk",
            "ro.build.version.security_patch",
            "ro.build.id",
            "ro.build.fingerprint",
            "ro.build.type",
            "ro.build.tags",
            "ro.product.cpu.abi",
            "ro.product.cpu.abilist",
            "ro.build.characteristics",
            "ro.hwui.texture_cache_size",
            "ro.sf.lcd_density",
            "ro.product.locale",
            "ro.product.locale.region",
        ]
        
        for prop in extended_props:
            success, stdout, stderr = self.run_shell_command(f"getprop {prop}")
            if success and stdout.strip():
                props[prop] = stdout.strip()
            else:
                props[prop] = "Unknown"
        
        # Get screen resolution
        screen_res = "Unknown"
        success, stdout, stderr = self.run_shell_command("wm size")
        if success and stdout.strip():
            screen_res = stdout.strip().replace("Physical size: ", "")
        
        # Get screen density
        screen_density = None
        success, stdout, stderr = self.run_shell_command("wm density")
        if success and stdout.strip():
            try:
                screen_density = int(stdout.strip().replace("Physical density: ", "").replace("Override density: ", ""))
            except ValueError:
                pass
        
        # Get default launcher
        default_launcher = "Unknown"
        success, stdout, stderr = self.run_shell_command("cmd package resolve-activity --brief android.intent.action.MAIN android.intent.category.HOME")
        if success and stdout.strip():
            # Output format: "package/activity"
            default_launcher = stdout.strip()
        
        # Get uptime
        uptime_seconds = None
        success, stdout, stderr = self.run_shell_command("cat /proc/uptime")
        if success and stdout.strip():
            try:
                uptime_seconds = int(float(stdout.strip().split()[0]))
            except (ValueError, IndexError):
                pass
        
        # Get memory info
        memory_total_mb = None
        memory_available_mb = None
        success, stdout, stderr = self.run_shell_command("cat /proc/meminfo")
        if success and stdout.strip():
            for line in stdout.strip().split('\n'):
                if line.startswith("MemTotal:"):
                    try:
                        memory_total_mb = int(line.split()[1]) // 1024
                    except (ValueError, IndexError):
                        pass
                elif line.startswith("MemAvailable:"):
                    try:
                        memory_available_mb = int(line.split()[1]) // 1024
                    except (ValueError, IndexError):
                        pass
        
        # Determine platform type
        platform_type = self._determine_platform_type(props)
        
        # Generate compatibility notes
        compatibility_notes = self._generate_compatibility_notes(props, platform_type)
        
        # Create updated device
        updated_device = ADBDevice(
            serial=self._connected_device.serial,
            state=self._connected_device.state,
            connection_type=self._connected_device.connection_type,
            ip_port=self._connected_device.ip_port,
            manufacturer=props.get("ro.product.manufacturer"),
            model=props.get("ro.product.model"),
            android_version=f"Android {props.get('ro.build.version.release', 'Unknown')} (API {props.get('ro.build.version.sdk', 'Unknown')})",
            api_level=int(props.get("ro.build.version.sdk", 0)) if props.get("ro.build.version.sdk", "0").isdigit() else None,
            cpu_abi=props.get("ro.product.cpu.abi"),
            build_fingerprint=props.get("ro.build.fingerprint"),
            screen_resolution=screen_res,
            screen_density=screen_density,
            device_codename=props.get("ro.product.device"),
            board=props.get("ro.product.board"),
            default_launcher=default_launcher,
            uptime_seconds=uptime_seconds,
            memory_total_mb=memory_total_mb,
            memory_available_mb=memory_available_mb,
            platform_type=platform_type,
            compatibility_notes=compatibility_notes,
        )
        
        return updated_device

    def _determine_platform_type(self, props: dict[str, str]) -> str:
        """Determine the platform type based on device properties."""
        manufacturer = props.get("ro.product.manufacturer", "").lower()
        brand = props.get("ro.product.brand", "").lower()
        model = props.get("ro.product.model", "").lower()
        characteristics = props.get("ro.build.characteristics", "").lower()
        fingerprint = props.get("ro.build.fingerprint", "").lower()
        
        # Check for Fire TV / Fire OS
        if "amazon" in manufacturer or "amazon" in brand or "fire" in model or "aft" in model:
            return "fire_tv"
        
        # Check for Google TV
        if "google" in manufacturer or "google" in brand or "google tv" in fingerprint or "chromecast" in model:
            return "google_tv"
        
        # Check for Android TV characteristics
        if "tv" in characteristics or "television" in characteristics:
            return "android_tv"
        
        # Check for common Android TV manufacturers/models
        android_tv_indicators = ["sony", "tcl", "xiaomi", "hisense", "philips", "sharp", "nvidia", "shield"]
        for indicator in android_tv_indicators:
            if indicator in manufacturer or indicator in brand or indicator in model:
                return "android_tv"
        
        return "unknown"

    def _generate_compatibility_notes(self, props: dict[str, str], platform_type: str) -> list[str]:
        """Generate compatibility notes based on device properties."""
        notes = []
        
        if platform_type == "fire_tv":
            notes.append("Fire OS detected — TV Freedom does not support Amazon Fire TV devices")
            notes.append("Bootloader is locked and cannot be unlocked on Fire TV")
            notes.append("Package management and launcher replacement are blocked by Amazon")
        elif platform_type == "unknown":
            notes.append("Platform type could not be determined — compatibility uncertain")
            notes.append("Recommend verifying device is Android TV or Google TV before proceeding")
        
        # Check API level
        api_level = props.get("ro.build.version.sdk", "0")
        if api_level.isdigit():
            api = int(api_level)
            if api < 29:
                notes.append(f"Android API level {api} is below minimum supported version (API 29)")
                notes.append("Launcher replacement and some features may not work on Android 9 or earlier")
            elif api >= 33:
                notes.append(f"Android API level {api} (Android 13+) — modern wireless debugging supported")
        
        # Check storage
        storage_info = self.get_storage_info()
        if "free_gb" in storage_info and storage_info["free_gb"] < 1:
            notes.append(f"Critically low storage: {storage_info['free_gb']} GB free")
            notes.append("Backups and modifications may fail due to insufficient space")
        
        # Check ABIs
        abi = props.get("ro.product.cpu.abi", "")
        if abi and "arm64" not in abi and "x86_64" not in abi:
            notes.append(f"CPU architecture {abi} — some features may have limited compatibility")
        
        return notes
    
    @staticmethod
    def _is_valid_ip(ip: str) -> bool:
        """Validate IPv4 address format."""
        parts = ip.split('.')
        if len(parts) != 4:
            return False
        try:
            return all(0 <= int(part) <= 255 for part in parts)
        except ValueError:
            return False
    
    def get_adb_installation_guidance(self) -> str:
        """Get installation guidance for ADB."""
        using_bundled = is_using_bundled_adb()
        if using_bundled:
            return (
                "TV Freedom includes a bundled ADB (Android Debug Bridge) for device connectivity.\n\n"
                "If you see this message, the bundled ADB was not found in the application package.\n"
                "This should not happen with a proper installation.\n\n"
                "Troubleshooting:\n"
                "1. Ensure you installed TV Freedom using the official installer\n"
                "2. Re-install TV Freedom if the bundled ADB is missing\n"
                "3. As a fallback, you can install Android SDK Platform Tools manually:\n"
                "   - Download from: https://developer.android.com/studio/releases/platform-tools\n"
                "   - Extract and add to system PATH\n"
                "   - TV Freedom will auto-detect system ADB if bundled is unavailable\n"
                "4. Alternative install methods (Windows):\n"
                "   - winget install Google.AndroidSDKPlatformTools\n"
                "   - choco install adb\n\n"
                "Contact support if the issue persists."
            )
        else:
            return (
                "TV Freedom uses system ADB (Android Debug Bridge) from PATH.\n\n"
                "If ADB is not found, you can install it:\n"
                "1. Download Android SDK Platform Tools:\n"
                "   https://developer.android.com/studio/releases/platform-tools\n"
                "2. Extract and add to system PATH\n"
                "3. Verify with: adb version\n\n"
                "Alternative: Install via winget:\n"
                "   winget install Google.AndroidSDKPlatformTools\n\n"
                "Or via Chocolatey:\n"
                "   choco install adb\n\n"
                "Note: Official TV Freedom releases include bundled ADB - no manual installation needed."
            )
    
    def get_connection_guidance(self, state: ADBState) -> str:
        """Get user-friendly guidance for a connection state."""
        guidance = {
            ADBState.UNAVAILABLE: self.get_adb_installation_guidance(),
            ADBState.NO_DEVICE: (
                "No ADB devices detected.\n\n"
                "For USB connection:\n"
                "1. Connect your TV via USB cable (data-capable, not charge-only)\n"
                "2. On TV: Settings → System → Developer Options → Enable USB Debugging\n"
                "3. Accept the 'Allow USB debugging?' prompt on your TV\n"
                "4. Click 'Refresh Devices' below\n\n"
                "For Network connection:\n"
                "1. Ensure TV and PC are on the same Wi-Fi network\n"
                "2. On TV: Settings → System → Developer Options → Enable 'ADB over network' or 'Wireless debugging'\n"
                "3. Note the IP address and port shown on TV\n"
                "4. Enter them in the Network Connection section below"
            ),
            ADBState.UNAUTHORIZED: (
                "Device is connected but unauthorized.\n\n"
                "Action required on your TV:\n"
                "1. Look for the 'Allow USB debugging?' or 'Allow wireless debugging?' prompt\n"
                "2. Check 'Always allow from this computer' (recommended)\n"
                "3. Tap OK / Allow\n"
                "4. Click 'Retry Connection' below"
            ),
            ADBState.OFFLINE: (
                "Device is offline.\n\n"
                "Troubleshooting:\n"
                "- Check USB cable connection (try a different cable/port)\n"
                "- Ensure TV is awake and not in sleep mode\n"
                "- For network: verify both devices on same Wi-Fi\n"
                "- Restart ADB server: run 'adb kill-server' then retry\n"
                "- Restart the TV if needed"
            ),
            ADBState.CONNECTED: (
                "Device successfully connected!\n\n"
                "You can now run diagnostics from the Device Diagnostics page.\n"
                "All operations are read-only - your TV will not be modified."
            ),
            ADBState.ERROR: (
                "Connection error occurred.\n\n"
                f"Details: {self._last_error or 'Unknown error'}\n\n"
                "Common fixes:\n"
                "- Verify IP address and port are correct\n"
                "- Ensure 'ADB over network' / 'Wireless debugging' is enabled on TV\n"
                "- Check firewall/antivirus isn't blocking ADB\n"
                "- Try USB connection instead\n"
                "- Restart ADB: 'adb kill-server' in Command Prompt"
            ),
        }
        return guidance.get(state, "Unknown state")


# Convenience function for quick ADB availability check
def check_adb_available() -> tuple[bool, str | None]:
    """
    Quick check if ADB is available (bundled or system).
    
    Returns:
        Tuple of (available, path_or_error_message)
    """
    available, path = bundled_check_adb_available(prefer_bundled=True)
    if available:
        return True, path
    return False, "ADB not found. TV Freedom includes bundled ADB - ensure the application is properly installed."


if __name__ == "__main__":
    # Simple self-test
    print("TV Freedom ADB Manager - Self Test")
    print("=" * 40)
    
    available, path = check_adb_available()
    print(f"ADB Available: {available}")
    if available:
        print(f"ADB Path: {path}")
    
    mgr = ADBManager()
    print(f"Manager ADB Path: {mgr.adb_path}")
    print(f"Initial State: {mgr.connection_state.value}")
    
    print("\nScanning for USB devices...")
    usb_devices = mgr.get_usb_devices()
    print(f"USB Devices Found: {len(usb_devices)}")
    for d in usb_devices:
        print(f"  - {d.serial} ({d.state})")
    
    print("\nScanning for all devices...")
    all_devices = mgr.get_all_devices()
    print(f"All Devices Found: {len(all_devices)}")
    for d in all_devices:
        print(f"  - {d.serial} ({d.state}) [{d.connection_type}]")
    
    print("\nDone.")