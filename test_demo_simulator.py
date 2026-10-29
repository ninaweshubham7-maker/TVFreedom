"""
Automated tests for the Demo Simulator module.

These tests verify that all simulated profiles work correctly,
connection failures are simulated properly, and DEMO DATA markers
are present in all returned diagnostic information.
"""

import pytest
from demo_simulator import (
    DemoSimulator,
    DemoDeviceProfile,
    get_available_profiles,
    get_profile_by_id,
    DEMO_PROFILES,
    demo_guard,
    DemoModeGuard,
)


# -----------------------------------------------------------------------------
# Profile Tests
# -----------------------------------------------------------------------------

def test_all_profiles_exist():
    """Verify all six required profiles are defined."""
    required_profiles = {
        "android_tv_compatible",
        "google_tv_compatible",
        "android_tv_older",
        "low_storage_device",
        "adb_disabled",
        "unsupported_device",
    }
    assert set(DEMO_PROFILES.keys()) == required_profiles


def test_profile_structure():
    """Verify each profile has all required fields with correct types."""
    for profile_id, profile in DEMO_PROFILES.items():
        assert isinstance(profile.id, str)
        assert profile.id == profile_id
        assert isinstance(profile.name, str) and profile.name
        assert isinstance(profile.description, str) and profile.description
        assert isinstance(profile.manufacturer, str) and profile.manufacturer
        assert isinstance(profile.model, str) and profile.model
        assert isinstance(profile.android_version, str) and profile.android_version
        assert isinstance(profile.api_level, int) and profile.api_level > 0
        assert isinstance(profile.storage_total_gb, int) and profile.storage_total_gb > 0
        assert isinstance(profile.storage_free_gb, (int, float)) and profile.storage_free_gb >= 0
        assert isinstance(profile.adb_enabled, bool)
        assert isinstance(profile.adb_authorized, bool)
        assert isinstance(profile.compatible, bool)
        assert isinstance(profile.compatibility_warnings, tuple)
        assert profile.connection_failure is None or isinstance(profile.connection_failure, str)


def test_get_available_profiles():
    """Verify get_available_profiles returns all profiles sorted by name."""
    profiles = get_available_profiles()
    assert len(profiles) == 6
    names = [p.name for p in profiles]
    assert names == sorted(names)


def test_get_profile_by_id():
    """Verify get_profile_by_id returns correct profile or None."""
    profile = get_profile_by_id("android_tv_compatible")
    assert profile is not None
    assert profile.id == "android_tv_compatible"
    assert profile.name == "Compatible Android TV"

    assert get_profile_by_id("nonexistent") is None


# -----------------------------------------------------------------------------
# Compatible Android TV Profile Tests
# -----------------------------------------------------------------------------

def test_compatible_android_tv_profile():
    """Test the Compatible Android TV profile."""
    profile = DEMO_PROFILES["android_tv_compatible"]
    assert profile.manufacturer == "Sony"
    assert profile.model == "XR-65A80K"
    assert profile.android_version == "Android 12 (API 31)"
    assert profile.api_level == 31
    assert profile.storage_total_gb == 32
    assert profile.storage_free_gb == 18
    assert profile.adb_enabled is True
    assert profile.adb_authorized is True
    assert profile.compatible is True
    assert profile.compatibility_warnings == ()
    assert profile.connection_failure is None


def test_compatible_android_tv_connect_success():
    """Test successful connection for compatible Android TV."""
    sim = DemoSimulator("android_tv_compatible")
    success, error = sim.connect()
    assert success is True
    assert error is None
    assert sim.is_connected is True


def test_compatible_android_tv_diagnostic():
    """Test diagnostic for compatible Android TV."""
    sim = DemoSimulator("android_tv_compatible")
    sim.connect()
    results = sim.run_diagnostic()

    assert sim.diagnostic_run is True
    assert "Manufacturer" in results
    assert results["Manufacturer"] == "Sony 🧪 DEMO DATA"
    assert "Device Model" in results
    assert results["Device Model"] == "XR-65A80K 🧪 DEMO DATA"
    assert "Android Version" in results
    assert "API Level" in results
    assert "Total Storage" in results
    assert "Available Storage" in results
    assert "ADB Status" in results
    assert "Authorized & Connected" in results["ADB Status"]
    assert "TV Freedom Compatibility" in results
    assert "✅ Compatible" in results["TV Freedom Compatibility"]
    # Verify all values have DEMO DATA marker
    for value in results.values():
        assert "🧪 DEMO DATA" in value


# -----------------------------------------------------------------------------
# Compatible Google TV Profile Tests
# -----------------------------------------------------------------------------

def test_compatible_google_tv_profile():
    """Test the Compatible Google TV profile."""
    profile = DEMO_PROFILES["google_tv_compatible"]
    assert profile.manufacturer == "Google"
    assert profile.model == "Chromecast with Google TV (4K)"
    assert profile.android_version == "Android 13 (API 33)"
    assert profile.api_level == 33
    assert profile.storage_total_gb == 8
    assert profile.storage_free_gb == 4
    assert profile.adb_enabled is True
    assert profile.adb_authorized is True
    assert profile.compatible is True
    assert len(profile.compatibility_warnings) == 1
    assert "Limited internal storage" in profile.compatibility_warnings[0]
    assert profile.connection_failure is None


def test_compatible_google_tv_connect_success():
    """Test successful connection for compatible Google TV."""
    sim = DemoSimulator("google_tv_compatible")
    success, error = sim.connect()
    assert success is True
    assert error is None


def test_compatible_google_tv_diagnostic():
    """Test diagnostic for compatible Google TV includes storage warning."""
    sim = DemoSimulator("google_tv_compatible")
    sim.connect()
    results = sim.run_diagnostic()

    assert "TV Freedom Compatibility" in results
    assert "✅ Compatible" in results["TV Freedom Compatibility"]
    # Verify warning appears in profile
    warnings = sim.get_compatibility_warnings()
    assert len(warnings) == 1
    assert "Limited internal storage" in warnings[0]


# -----------------------------------------------------------------------------
# Older Android TV Profile Tests
# -----------------------------------------------------------------------------

def test_older_android_tv_profile():
    """Test the Older Android TV profile."""
    profile = DEMO_PROFILES["android_tv_older"]
    assert profile.manufacturer == "TCL"
    assert profile.model == "55R617"
    assert profile.android_version == "Android 9 (API 28)"
    assert profile.api_level == 28
    assert profile.storage_total_gb == 16
    assert profile.storage_free_gb == 6
    assert profile.adb_enabled is True
    assert profile.adb_authorized is True
    assert profile.compatible is False
    assert len(profile.compatibility_warnings) == 3
    assert any("Android 9" in w for w in profile.compatibility_warnings)
    assert any("Launcher replacement" in w for w in profile.compatibility_warnings)
    assert profile.connection_failure is None


def test_older_android_tv_not_compatible():
    """Test that older Android TV shows as incompatible."""
    sim = DemoSimulator("android_tv_older")
    sim.connect()
    results = sim.run_diagnostic()

    assert "TV Freedom Compatibility" in results
    assert "❌ Not Compatible" in results["TV Freedom Compatibility"]
    warnings = sim.get_compatibility_warnings()
    assert len(warnings) == 3


# -----------------------------------------------------------------------------
# Low Storage Device Profile Tests
# -----------------------------------------------------------------------------

def test_low_storage_device_profile():
    """Test the Low-Storage Device profile."""
    profile = DEMO_PROFILES["low_storage_device"]
    assert profile.manufacturer == "Xiaomi"
    assert profile.model == "Mi Box S (2GB/8GB)"
    assert profile.android_version == "Android 11 (API 30)"
    assert profile.api_level == 30
    assert profile.storage_total_gb == 8
    assert profile.storage_free_gb == 0.5
    assert profile.adb_enabled is True
    assert profile.adb_authorized is True
    assert profile.compatible is True
    assert len(profile.compatibility_warnings) == 3
    assert any("Critically low free storage" in w for w in profile.compatibility_warnings)
    assert any("Unable to create safety backup" in w for w in profile.compatibility_warnings)
    assert profile.connection_failure is None


def test_low_storage_device_diagnostic_shows_low_space():
    """Test diagnostic shows critically low storage."""
    sim = DemoSimulator("low_storage_device")
    sim.connect()
    results = sim.run_diagnostic()

    assert "Available Storage" in results
    assert "0.5 GB" in results["Available Storage"]
    assert "TV Freedom Compatibility" in results
    assert "✅ Compatible" in results["TV Freedom Compatibility"]
    warnings = sim.get_compatibility_warnings()
    assert len(warnings) == 3


# -----------------------------------------------------------------------------
# ADB Disabled Profile Tests
# -----------------------------------------------------------------------------

def test_adb_disabled_profile():
    """Test the ADB Disabled profile."""
    profile = DEMO_PROFILES["adb_disabled"]
    assert profile.manufacturer == "NVIDIA"
    assert profile.model == "SHIELD TV Pro (2019)"
    assert profile.android_version == "Android 11 (API 30)"
    assert profile.api_level == 30
    assert profile.storage_total_gb == 16
    assert profile.storage_free_gb == 10
    assert profile.adb_enabled is False
    assert profile.adb_authorized is False
    assert profile.compatible is False
    assert len(profile.compatibility_warnings) == 3
    assert profile.connection_failure is not None
    assert "ADB connection refused" in profile.connection_failure


def test_adb_disabled_connection_fails():
    """Test that ADB disabled profile fails to connect."""
    sim = DemoSimulator("adb_disabled")
    success, error = sim.connect()
    assert success is False
    assert error is not None
    assert "ADB connection refused" in error
    assert sim.is_connected is False


def test_adb_disabled_diagnostic_raises_when_not_connected():
    """Test that diagnostic fails when not connected."""
    sim = DemoSimulator("adb_disabled")
    # Don't connect
    with pytest.raises(RuntimeError, match="not connected"):
        sim.run_diagnostic()


# -----------------------------------------------------------------------------
# Unsupported Device Profile Tests
# -----------------------------------------------------------------------------

def test_unsupported_device_profile():
    """Test the Unsupported Device profile."""
    profile = DEMO_PROFILES["unsupported_device"]
    assert profile.manufacturer == "Amazon"
    assert profile.model == "Fire TV Stick 4K Max"
    assert profile.android_version == "Android 11 (API 30) - Fire OS 8"
    assert profile.api_level == 30
    assert profile.storage_total_gb == 16
    assert profile.storage_free_gb == 8
    assert profile.adb_enabled is True
    assert profile.adb_authorized is True
    assert profile.compatible is False
    assert len(profile.compatibility_warnings) == 4
    assert any("Fire OS" in w for w in profile.compatibility_warnings)
    assert any("bootloader is locked" in w.lower() for w in profile.compatibility_warnings)
    assert any("blocked by Amazon" in w for w in profile.compatibility_warnings)
    assert profile.connection_failure is None


def test_unsupported_device_connects_but_incompatible():
    """Test that unsupported device connects but shows as incompatible."""
    sim = DemoSimulator("unsupported_device")
    success, error = sim.connect()
    assert success is True
    assert error is None
    assert sim.is_connected is True

    results = sim.run_diagnostic()
    assert "TV Freedom Compatibility" in results
    assert "❌ Not Compatible" in results["TV Freedom Compatibility"]
    warnings = sim.get_compatibility_warnings()
    assert len(warnings) == 4


# -----------------------------------------------------------------------------
# Demo Mode Guard Tests
# -----------------------------------------------------------------------------

def test_demo_mode_guard_activate_deactivate():
    """Test DemoModeGuard activation and deactivation."""
    guard = DemoModeGuard()
    assert guard.is_active is False

    guard.activate()
    assert guard.is_active is True

    guard.deactivate()
    assert guard.is_active is False


def test_demo_mode_guard_ensure_demo_mode():
    """Test ensure_demo_mode raises when not active."""
    guard = DemoModeGuard()
    guard.activate()
    guard.ensure_demo_mode("test operation")  # Should not raise

    guard.deactivate()
    with pytest.raises(RuntimeError, match="outside of Demo Mode"):
        guard.ensure_demo_mode("test operation")


def test_demo_mode_guard_forbid_real_adb():
    """Test forbid_real_adb always raises."""
    guard = DemoModeGuard()
    guard.activate()
    with pytest.raises(RuntimeError, match="BLOCKED: Attempted real"):
        guard.forbid_real_adb("test command")


# -----------------------------------------------------------------------------
# Simulator State Tests
# -----------------------------------------------------------------------------

def test_simulator_disconnect_resets_state():
    """Test that disconnect resets simulator state."""
    sim = DemoSimulator("android_tv_compatible")
    sim.connect()
    sim.run_diagnostic()

    assert sim.is_connected is True
    assert sim.diagnostic_run is True

    sim.disconnect()

    assert sim.is_connected is False
    assert sim.diagnostic_run is False


def test_simulator_get_connection_status():
    """Test get_connection_status returns correct status."""
    sim = DemoSimulator("android_tv_compatible")

    # Not connected
    status_key, status_msg = sim.get_connection_status()
    assert status_key == "disconnected"

    # Connected
    sim.connect()
    status_key, status_msg = sim.get_connection_status()
    assert status_key == "connected"

    # Attention (failed connection)
    sim2 = DemoSimulator("adb_disabled")
    sim2.connect()
    status_key, status_msg = sim2.get_connection_status()
    assert status_key == "attention"


def test_invalid_profile_raises():
    """Test that invalid profile ID raises ValueError."""
    with pytest.raises(ValueError, match="Unknown demo profile"):
        DemoSimulator("invalid_profile")


# -----------------------------------------------------------------------------
# DEMO DATA Marker Tests
# -----------------------------------------------------------------------------

def test_all_diagnostic_values_have_demo_marker():
    """Verify every diagnostic value contains the DEMO DATA marker."""
    for profile_id in DEMO_PROFILES:
        sim = DemoSimulator(profile_id)
        if sim.profile.adb_enabled and sim.profile.adb_authorized:
            sim.connect()
            results = sim.run_diagnostic()
            for key, value in results.items():
                assert "🧪 DEMO DATA" in value, f"{profile_id}.{key} missing DEMO DATA marker"


# -----------------------------------------------------------------------------
# Profile-Specific Field Tests
# -----------------------------------------------------------------------------

def test_profile_specific_fields():
    """Test profile-specific diagnostic fields."""
    sim = DemoSimulator("android_tv_compatible")
    sim.connect()
    results = sim.run_diagnostic()

    # Check specific fields exist
    assert "Screen Resolution" in results
    assert "CPU Architecture" in results
    assert "Build ID" in results

    # Build ID should contain profile ID
    assert "ANDROID_TV_COMPATIBLE" in results["Build ID"]


# -----------------------------------------------------------------------------
# Integration-style Tests
# -----------------------------------------------------------------------------

def test_full_flow_compatible_device():
    """Test full connect -> diagnostic flow for compatible device."""
    sim = DemoSimulator("android_tv_compatible")

    # Connect
    success, error = sim.connect()
    assert success
    assert error is None

    # Run diagnostic
    results = sim.run_diagnostic()
    assert results

    # Verify key fields
    assert results["Manufacturer"] == "Sony 🧪 DEMO DATA"
    assert "✅ Compatible" in results["TV Freedom Compatibility"]
    assert "Authorized & Connected" in results["ADB Status"]

    # Disconnect
    sim.disconnect()
    assert not sim.is_connected


def test_full_flow_incompatible_device():
    """Test full flow for incompatible device (connects but shows warnings)."""
    sim = DemoSimulator("unsupported_device")

    success, error = sim.connect()
    assert success

    results = sim.run_diagnostic()
    assert "❌ Not Compatible" in results["TV Freedom Compatibility"]
    assert len(sim.get_compatibility_warnings()) == 4


def test_full_flow_connection_failure():
    """Test flow for device that fails to connect."""
    sim = DemoSimulator("adb_disabled")

    success, error = sim.connect()
    assert not success
    assert error is not None
    assert "ADB connection refused" in error

    # Diagnostic should fail
    with pytest.raises(RuntimeError):
        sim.run_diagnostic()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])