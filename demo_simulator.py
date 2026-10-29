"""
Demo Simulator - Virtual TV Demo Mode for TV Freedom.

This module provides simulated device profiles and diagnostic data for development
and testing without requiring a physical television.

IMPORTANT: This module MUST NEVER execute real ADB commands or modify real devices.
All data returned is purely simulated and clearly marked as DEMO DATA.
"""

from dataclasses import dataclass, field
from typing import Literal
import random
import time


@dataclass(frozen=True)
class DemoDeviceProfile:
    """Immutable profile defining a simulated TV device for demo mode."""
    id: str
    name: str
    description: str
    manufacturer: str
    model: str
    android_version: str
    api_level: int
    storage_total_gb: int
    storage_free_gb: int
    adb_enabled: bool
    adb_authorized: bool
    compatible: bool
    compatibility_warnings: tuple[str, ...] = field(default_factory=tuple)
    connection_failure: str | None = None


# -----------------------------------------------------------------------------
# Simulated Device Profiles
# -----------------------------------------------------------------------------

DEMO_PROFILES: dict[str, DemoDeviceProfile] = {
    "android_tv_compatible": DemoDeviceProfile(
        id="android_tv_compatible",
        name="Compatible Android TV",
        description="A modern Android TV device fully compatible with TV Freedom features.",
        manufacturer="Sony",
        model="XR-65A80K",
        android_version="Android 12 (API 31)",
        api_level=31,
        storage_total_gb=32,
        storage_free_gb=18,
        adb_enabled=True,
        adb_authorized=True,
        compatible=True,
        compatibility_warnings=(),
        connection_failure=None,
    ),
    "google_tv_compatible": DemoDeviceProfile(
        id="google_tv_compatible",
        name="Compatible Google TV",
        description="A Google TV device (Chromecast with Google TV) fully compatible with TV Freedom.",
        manufacturer="Google",
        model="Chromecast with Google TV (4K)",
        android_version="Android 13 (API 33)",
        api_level=33,
        storage_total_gb=8,
        storage_free_gb=4,
        adb_enabled=True,
        adb_authorized=True,
        compatible=True,
        compatibility_warnings=(
            "Limited internal storage (8 GB) — package management may be constrained",
        ),
        connection_failure=None,
    ),
    "android_tv_older": DemoDeviceProfile(
        id="android_tv_older",
        name="Older Android TV",
        description="An older Android TV device running Android 9 with limited feature support.",
        manufacturer="TCL",
        model="55R617",
        android_version="Android 9 (API 28)",
        api_level=28,
        storage_total_gb=16,
        storage_free_gb=6,
        adb_enabled=True,
        adb_authorized=True,
        compatible=False,
        compatibility_warnings=(
            "Android 9 (API 28) is below minimum supported version (API 29)",
            "Launcher replacement not supported on this Android version",
            "Package management features may be unreliable",
        ),
        connection_failure=None,
    ),
    "low_storage_device": DemoDeviceProfile(
        id="low_storage_device",
        name="Low-Storage Device",
        description="A device with critically low available storage space.",
        manufacturer="Xiaomi",
        model="Mi Box S (2GB/8GB)",
        android_version="Android 11 (API 30)",
        api_level=30,
        storage_total_gb=8,
        storage_free_gb=0.5,
        adb_enabled=True,
        adb_authorized=True,
        compatible=True,
        compatibility_warnings=(
            "Critically low free storage (512 MB) — backups and modifications may fail",
            "Unable to create safety backup — insufficient space",
            "Package installation or modification not recommended",
        ),
        connection_failure=None,
    ),
    "adb_disabled": DemoDeviceProfile(
        id="adb_disabled",
        name="ADB Disabled",
        description="A compatible device with ADB debugging turned off or not authorized.",
        manufacturer="NVIDIA",
        model="SHIELD TV Pro (2019)",
        android_version="Android 11 (API 30)",
        api_level=30,
        storage_total_gb=16,
        storage_free_gb=10,
        adb_enabled=False,
        adb_authorized=False,
        compatible=False,
        compatibility_warnings=(
            "USB Debugging is disabled in Developer Options",
            "ADB authorization has not been granted on the TV",
            "Enable USB Debugging and authorize this computer to proceed",
        ),
        connection_failure="ADB connection refused: device unauthorized. "
                           "Please enable USB Debugging and accept the authorization prompt on your TV.",
    ),
    "unsupported_device": DemoDeviceProfile(
        id="unsupported_device",
        name="Unsupported Device",
        description="A device that cannot be modified by TV Freedom due to manufacturer restrictions.",
        manufacturer="Amazon",
        model="Fire TV Stick 4K Max",
        android_version="Android 11 (API 30) - Fire OS 8",
        api_level=30,
        storage_total_gb=16,
        storage_free_gb=8,
        adb_enabled=True,
        adb_authorized=True,
        compatible=False,
        compatibility_warnings=(
            "Fire OS is a heavily modified Android fork — not supported",
            "Bootloader is locked and cannot be unlocked",
            "Package management and launcher replacement are blocked by Amazon",
            "This device cannot be safely modified by TV Freedom",
        ),
        connection_failure=None,
    ),
}


# -----------------------------------------------------------------------------
# Demo Simulation Logic
# -----------------------------------------------------------------------------

class DemoSimulator:
    """
    Simulates device connections and diagnostics for demo mode.

    This class is strictly separated from real ADB communication.
    It MUST NEVER be used in production with real devices.
    """

    DEMO_DATA_MARKER = "🧪 DEMO DATA"

    def __init__(self, profile_id: str = "android_tv_compatible"):
        """
        Initialize the simulator with a specific profile.

        Args:
            profile_id: The ID of the demo profile to use.
                       Must be one of the keys in DEMO_PROFILES.
        """
        if profile_id not in DEMO_PROFILES:
            raise ValueError(f"Unknown demo profile: {profile_id}. "
                           f"Available: {list(DEMO_PROFILES.keys())}")
        self._profile = DEMO_PROFILES[profile_id]
        self._connected = False
        self._diagnostic_run = False

    @property
    def profile(self) -> DemoDeviceProfile:
        """Get the current demo profile."""
        return self._profile

    @property
    def is_connected(self) -> bool:
        """Simulated connection status."""
        return self._connected

    @property
    def diagnostic_run(self) -> bool:
        """Whether a diagnostic has been run."""
        return self._diagnostic_run

    def connect(self) -> tuple[bool, str | None]:
        """
        Simulate connecting to the device.

        Returns:
            Tuple of (success: bool, error_message: str | None).
            On failure, error_message contains a simulated ADB error.
        """
        # Simulate connection delay
        time.sleep(0.5)

        if self._profile.connection_failure:
            self._connected = False
            return False, self._profile.connection_failure

        if not self._profile.adb_enabled:
            self._connected = False
            return False, "ADB connection refused: USB debugging is disabled on the device."

        if not self._profile.adb_authorized:
            self._connected = False
            return False, ("ADB connection refused: device unauthorized. "
                          "Please accept the USB debugging authorization prompt on your TV.")

        self._connected = True
        return True, None

    def disconnect(self) -> None:
        """Simulate disconnecting from the device."""
        self._connected = False
        self._diagnostic_run = False

    def run_diagnostic(self) -> dict[str, str]:
        """
        Simulate running a full device diagnostic.

        Returns:
            Dictionary of diagnostic information, all values marked as DEMO DATA.
        """
        if not self._connected:
            raise RuntimeError("Cannot run diagnostic: not connected. Call connect() first.")

        # Simulate diagnostic delay
        time.sleep(1.0)

        self._diagnostic_run = True

        profile = self._profile
        storage_free_mb = int(profile.storage_free_gb * 1024)
        storage_total_mb = int(profile.storage_total_gb * 1024)

        return {
            "Manufacturer": f"{profile.manufacturer} {self.DEMO_DATA_MARKER}",
            "Device Model": f"{profile.model} {self.DEMO_DATA_MARKER}",
            "Android Version": f"{profile.android_version} {self.DEMO_DATA_MARKER}",
            "API Level": f"API {profile.api_level} {self.DEMO_DATA_MARKER}",
            "Total Storage": f"{profile.storage_total_gb} GB {self.DEMO_DATA_MARKER}",
            "Available Storage": f"{profile.storage_free_gb} GB ({storage_free_mb} MB) {self.DEMO_DATA_MARKER}",
            "Storage Used": f"{profile.storage_total_gb - profile.storage_free_gb} GB {self.DEMO_DATA_MARKER}",
            "ADB Status": (
                "Authorized & Connected" if profile.adb_authorized else "Not Authorized"
            ) + f" {self.DEMO_DATA_MARKER}",
            "TV Freedom Compatibility": (
                "✅ Compatible" if profile.compatible else "❌ Not Compatible"
            ) + f" {self.DEMO_DATA_MARKER}",
            "Screen Resolution": "3840x2160 @ 60Hz (simulated) " + self.DEMO_DATA_MARKER,
            "CPU Architecture": "arm64-v8a (simulated) " + self.DEMO_DATA_MARKER,
            "Build ID": f"DEMO_BUILD_{profile.id.upper()}_{random.randint(100000, 999999)} " + self.DEMO_DATA_MARKER,
        }

    def get_compatibility_warnings(self) -> list[str]:
        """Get compatibility warnings for the current profile."""
        return list(self._profile.compatibility_warnings)

    def get_connection_status(self) -> tuple[str, str]:
        """
        Get human-readable connection status.

        Returns:
            Tuple of (status_key, status_message).
            status_key is one of: 'connected', 'disconnected', 'attention'
        """
        if not self._connected:
            if self._profile.connection_failure or not self._profile.adb_enabled or not self._profile.adb_authorized:
                return "attention", "Connection failed — see error details"
            return "disconnected", "Not connected"
        return "connected", "Connected and ready"


def get_available_profiles() -> list[DemoDeviceProfile]:
    """Get all available demo profiles sorted by name."""
    return sorted(DEMO_PROFILES.values(), key=lambda p: p.name)


def get_profile_by_id(profile_id: str) -> DemoDeviceProfile | None:
    """Get a demo profile by its ID."""
    return DEMO_PROFILES.get(profile_id)


# -----------------------------------------------------------------------------
# Demo Mode Guard
# -----------------------------------------------------------------------------

class DemoModeGuard:
    """
    Runtime guard to prevent accidental real device operations in demo mode.

    Usage:
        guard = DemoModeGuard()
        guard.ensure_demo_mode()  # Raises if not in demo mode
    """

    def __init__(self):
        self._demo_mode_active = False

    def activate(self) -> None:
        """Activate demo mode protection."""
        self._demo_mode_active = True

    def deactivate(self) -> None:
        """Deactivate demo mode protection."""
        self._demo_mode_active = False

    @property
    def is_active(self) -> bool:
        """Check if demo mode protection is active."""
        return self._demo_mode_active

    def ensure_demo_mode(self, operation: str = "operation") -> None:
        """
        Ensure demo mode is active, otherwise raise an error.

        Args:
            operation: Description of the operation being attempted.

        Raises:
            RuntimeError: If demo mode is not active.
        """
        if not self._demo_mode_active:
            raise RuntimeError(
                f"Attempted {operation} outside of Demo Mode. "
                "Real device operations are not implemented. "
                "Enable Demo Mode in the sidebar to use simulated features."
            )

    def forbid_real_adb(self, operation: str = "ADB command") -> None:
        """
        Explicitly forbid real ADB operations.

        This is a safety mechanism to ensure demo code never calls real ADB.

        Args:
            operation: Description of the ADB operation being prevented.

        Raises:
            RuntimeError: Always raises to prevent real ADB execution.
        """
        raise RuntimeError(
            f"BLOCKED: Attempted real {operation} in Demo Mode. "
            "Demo Simulator must never execute real ADB commands. "
            "Use DemoSimulator methods instead."
        )


# Global demo mode guard instance
demo_guard = DemoModeGuard()