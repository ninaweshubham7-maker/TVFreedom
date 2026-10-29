"""
Automated tests for the ADB Manager module.

These tests use mocked subprocess responses to verify ADB connectivity logic
without requiring a physical TV, emulator, network connection, or installed ADB.
"""

import pytest
import subprocess
from unittest.mock import patch, MagicMock, Mock
from adb_manager import (
    ADBManager,
    ADBDevice,
    ADBConnectionResult,
    ADBState,
    check_adb_available,
)


# -----------------------------------------------------------------------------
# Fixtures
# -----------------------------------------------------------------------------

@pytest.fixture
def mock_adb_path():
    """Mock ADB path for testing."""
    return "/fake/path/adb"


@pytest.fixture
def adb_manager(mock_adb_path):
    """Create an ADBManager instance with mocked ADB path."""
    with patch("adb_manager.shutil.which", return_value=mock_adb_path):
        manager = ADBManager(adb_path=mock_adb_path, timeout=5)
        yield manager


@pytest.fixture
def adb_manager_no_adb():
    """Create an ADBManager instance with no bundled or system ADB available.

    Explicitly mock bundled discovery as well as PATH lookup so this fixture
    remains deterministic on developer machines that ship platform-tools.
    """
    with patch("adb_manager.get_adb_path", return_value=None), patch(
        "adb_manager.shutil.which", return_value=None
    ):
        manager = ADBManager(adb_path=None, timeout=5)
        yield manager


# -----------------------------------------------------------------------------
# ADB Availability Tests
# -----------------------------------------------------------------------------

def test_check_adb_available_found():
    """Test check_adb_available when bundled/system discovery finds ADB."""
    with patch("adb_manager.bundled_check_adb_available", return_value=(True, "/usr/bin/adb")):
        available, path = check_adb_available()
        assert available is True
        assert path == "/usr/bin/adb"


def test_check_adb_available_not_found():
    """Test check_adb_available when neither bundled nor system ADB exists."""
    with patch("adb_manager.bundled_check_adb_available", return_value=(False, None)):
        available, msg = check_adb_available()
        assert available is False
        assert "ADB not found" in msg


def test_manager_adb_available_true(adb_manager):
    """Test manager reports ADB available when path provided."""
    assert adb_manager.is_adb_available is True
    assert adb_manager.adb_path == "/fake/path/adb"


def test_manager_adb_available_false(adb_manager_no_adb):
    """Test manager reports ADB unavailable when no path."""
    assert adb_manager_no_adb.is_adb_available is False
    assert adb_manager_no_adb.adb_path is None
    assert adb_manager_no_adb.connection_state == ADBState.UNAVAILABLE


# -----------------------------------------------------------------------------
# USB Device Discovery Tests
# -----------------------------------------------------------------------------

def test_get_usb_devices_empty(adb_manager):
    """Test get_usb_devices returns empty list when no devices."""
    with patch.object(adb_manager, "_run_adb", return_value=(True, "List of devices attached\n\n", "")):
        devices = adb_manager.get_usb_devices()
        assert devices == []


def test_get_usb_devices_single(adb_manager):
    """Test get_usb_devices with one USB device."""
    output = "List of devices attached\nABC123\tdevice usb:1-2\n\n"
    with patch.object(adb_manager, "_run_adb", return_value=(True, output, "")):
        devices = adb_manager.get_usb_devices()
        assert len(devices) == 1
        assert devices[0].serial == "ABC123"
        assert devices[0].state == "device"
        assert devices[0].connection_type == "usb"
        assert devices[0].ip_port is None


def test_get_usb_devices_multiple(adb_manager):
    """Test get_usb_devices with multiple USB devices."""
    output = "List of devices attached\nABC123\tdevice usb:1-2\nDEF456\tunauthorized usb:1-3\n\n"
    with patch.object(adb_manager, "_run_adb", return_value=(True, output, "")):
        devices = adb_manager.get_usb_devices()
        assert len(devices) == 2
        assert devices[0].serial == "ABC123"
        assert devices[0].state == "device"
        assert devices[1].serial == "DEF456"
        assert devices[1].state == "unauthorized"


def test_get_usb_devices_filters_tcpip(adb_manager):
    """Test get_usb_devices filters out TCP/IP devices."""
    output = "List of devices attached\nABC123\tdevice usb:1-2\n192.168.1.100:5555\tdevice\n\n"
    with patch.object(adb_manager, "_run_adb", return_value=(True, output, "")):
        devices = adb_manager.get_usb_devices()
        assert len(devices) == 1
        assert devices[0].serial == "ABC123"
        assert devices[0].connection_type == "usb"


def test_get_usb_devices_command_failure(adb_manager):
    """Test get_usb_devices handles command failure."""
    with patch.object(adb_manager, "_run_adb", return_value=(False, "", "adb server killed")):
        devices = adb_manager.get_usb_devices()
        assert devices == []
        assert adb_manager.last_error == "Failed to list devices: adb server killed"


# -----------------------------------------------------------------------------
# USB Connection Tests
# -----------------------------------------------------------------------------

def test_connect_usb_no_adb(adb_manager_no_adb):
    """Test connect_usb fails when ADB unavailable."""
    result = adb_manager_no_adb.connect_usb()
    assert result.success is False
    assert result.state == ADBState.UNAVAILABLE
    assert "ADB not available" in result.message
    assert "TV Freedom includes bundled ADB" in result.error_details


def test_connect_usb_no_devices(adb_manager):
    """Test connect_usb fails when no USB devices."""
    with patch.object(adb_manager, "get_usb_devices", return_value=[]):
        result = adb_manager.connect_usb()
        assert result.success is False
        assert result.state == ADBState.NO_DEVICE
        assert "No USB devices detected" in result.message


def test_connect_usb_specific_serial_not_found(adb_manager):
    """Test connect_usb fails when specific serial not found."""
    with patch.object(adb_manager, "get_usb_devices", return_value=[ADBDevice("ABC123", "device", "usb")]):
        result = adb_manager.connect_usb(serial="NOTFOUND")
        assert result.success is False
        assert result.state == ADBState.ERROR
        assert "not found" in result.message.lower()


def test_connect_usb_unauthorized(adb_manager):
    """Test connect_usb returns unauthorized state."""
    device = ADBDevice("ABC123", "unauthorized", "usb")
    with patch.object(adb_manager, "get_usb_devices", return_value=[device]):
        result = adb_manager.connect_usb()
        assert result.success is False
        assert result.state == ADBState.UNAUTHORIZED
        assert result.device == device
        assert "unauthorized" in result.message.lower()
        assert "authorization dialog" in result.error_details


def test_connect_usb_offline(adb_manager):
    """Test connect_usb returns offline state."""
    device = ADBDevice("ABC123", "offline", "usb")
    with patch.object(adb_manager, "get_usb_devices", return_value=[device]):
        result = adb_manager.connect_usb()
        assert result.success is False
        assert result.state == ADBState.OFFLINE
        assert result.device == device
        assert "offline" in result.message.lower()


def test_connect_usb_unknown_state(adb_manager):
    """Test connect_usb handles unknown device state."""
    device = ADBDevice("ABC123", "unknown", "usb")
    with patch.object(adb_manager, "get_usb_devices", return_value=[device]):
        result = adb_manager.connect_usb()
        assert result.success is False
        assert result.state == ADBState.ERROR
        assert "unexpected state" in result.message.lower()


def test_connect_usb_success(adb_manager):
    """Test connect_usb succeeds with authorized device."""
    device = ADBDevice("ABC123", "device", "usb")
    with patch.object(adb_manager, "get_usb_devices", return_value=[device]):
        result = adb_manager.connect_usb()
        assert result.success is True
        assert result.state == ADBState.CONNECTED
        assert result.device == device
        assert "Connected to ABC123 via USB" in result.message
        assert adb_manager.connected_device == device
        assert adb_manager.connection_state == ADBState.CONNECTED


def test_connect_usb_picks_first_when_multiple(adb_manager):
    """Test connect_usb picks first device when multiple available."""
    devices = [
        ADBDevice("ABC123", "device", "usb"),
        ADBDevice("DEF456", "device", "usb"),
    ]
    with patch.object(adb_manager, "get_usb_devices", return_value=devices):
        result = adb_manager.connect_usb()
        assert result.success is True
        assert result.device.serial == "ABC123"


# -----------------------------------------------------------------------------
# Network Connection Tests
# -----------------------------------------------------------------------------

def test_connect_network_no_adb(adb_manager_no_adb):
    """Test connect_network fails when ADB unavailable."""
    result = adb_manager_no_adb.connect_network("192.168.1.100")
    assert result.success is False
    assert result.state == ADBState.UNAVAILABLE


def test_connect_network_invalid_ip(adb_manager):
    """Test connect_network rejects invalid IP."""
    result = adb_manager.connect_network("not-an-ip")
    assert result.success is False
    assert result.state == ADBState.ERROR
    assert "Invalid IP" in result.message


def test_connect_network_invalid_port(adb_manager):
    """Test connect_network rejects invalid port."""
    result = adb_manager.connect_network("192.168.1.100", port=0)
    assert result.success is False
    assert result.state == ADBState.ERROR
    assert "Invalid port" in result.message
    
    result = adb_manager.connect_network("192.168.1.100", port=70000)
    assert result.success is False
    assert result.state == ADBState.ERROR


def test_connect_network_connection_refused(adb_manager):
    """Test connect_network handles connection refused."""
    with patch.object(adb_manager, "_run_adb", return_value=(False, "", "connection refused")):
        result = adb_manager.connect_network("192.168.1.100", 5555)
        assert result.success is False
        assert result.state == ADBState.ERROR
        assert "Failed to connect" in result.message


def test_connect_network_timeout(adb_manager):
    """Test connect_network handles timeout."""
    with patch.object(adb_manager, "_run_adb", return_value=(False, "", "Command timed out after 15 seconds")):
        result = adb_manager.connect_network("192.168.1.100", 5555)
        assert result.success is False
        assert result.state == ADBState.ERROR
        assert "timed out" in result.error_details.lower()


def test_connect_network_success_already_connected(adb_manager):
    """Test connect_network succeeds with 'already connected' response."""
    with patch.object(adb_manager, "_run_adb", return_value=(True, "already connected to 192.168.1.100:5555", "")):
        with patch.object(adb_manager, "get_all_devices", return_value=[
            ADBDevice("192.168.1.100:5555", "device", "tcpip", ip_port="192.168.1.100:5555")
        ]):
            result = adb_manager.connect_network("192.168.1.100", 5555)
            assert result.success is True
            assert result.state == ADBState.CONNECTED
            assert "192.168.1.100:5555" in result.message


def test_connect_network_success_new_connection(adb_manager):
    """Test connect_network succeeds with new connection."""
    with patch.object(adb_manager, "_run_adb", return_value=(True, "connected to 192.168.1.100:5555", "")):
        with patch.object(adb_manager, "get_all_devices", return_value=[
            ADBDevice("192.168.1.100:5555", "device", "tcpip", ip_port="192.168.1.100:5555")
        ]):
            result = adb_manager.connect_network("192.168.1.100", 5555)
            assert result.success is True
            assert result.state == ADBState.CONNECTED


def test_connect_network_device_unauthorized_after_connect(adb_manager):
    """Test connect_network detects unauthorized device after connect."""
    with patch.object(adb_manager, "_run_adb", return_value=(True, "connected to 192.168.1.100:5555", "")):
        with patch.object(adb_manager, "get_all_devices", return_value=[
            ADBDevice("192.168.1.100:5555", "unauthorized", "tcpip", ip_port="192.168.1.100:5555")
        ]):
            result = adb_manager.connect_network("192.168.1.100", 5555)
            assert result.success is False
            assert result.state == ADBState.UNAUTHORIZED
            assert "unauthorized" in result.message.lower()


def test_connect_network_device_offline_after_connect(adb_manager):
    """Test connect_network detects offline device after connect."""
    with patch.object(adb_manager, "_run_adb", return_value=(True, "connected to 192.168.1.100:5555", "")):
        with patch.object(adb_manager, "get_all_devices", return_value=[
            ADBDevice("192.168.1.100:5555", "offline", "tcpip", ip_port="192.168.1.100:5555")
        ]):
            result = adb_manager.connect_network("192.168.1.100", 5555)
            assert result.success is False
            assert result.state == ADBState.OFFLINE


def test_connect_network_device_not_in_list_after_connect(adb_manager):
    """Test connect_network fails when device not visible after connect."""
    with patch.object(adb_manager, "_run_adb", return_value=(True, "connected to 192.168.1.100:5555", "")):
        with patch.object(adb_manager, "get_all_devices", return_value=[]):
            result = adb_manager.connect_network("192.168.1.100", 5555)
            assert result.success is False
            assert result.state == ADBState.ERROR
            assert "not visible" in result.message


# -----------------------------------------------------------------------------
# Disconnect Tests
# -----------------------------------------------------------------------------

def test_disconnect_not_connected(adb_manager):
    """Test disconnect returns False when not connected."""
    assert adb_manager.connected_device is None
    result = adb_manager.disconnect()
    assert result is False


def test_disconnect_usb(adb_manager):
    """Test disconnect clears USB connection."""
    device = ADBDevice("ABC123", "device", "usb")
    adb_manager._connected_device = device
    adb_manager._connection_state = ADBState.CONNECTED
    
    result = adb_manager.disconnect()
    assert result is True
    assert adb_manager.connected_device is None
    assert adb_manager.connection_state == ADBState.NO_DEVICE


def test_disconnect_network_runs_adb_disconnect(adb_manager):
    """Test disconnect runs adb disconnect for network devices."""
    device = ADBDevice("192.168.1.100:5555", "device", "tcpip", ip_port="192.168.1.100:5555")
    adb_manager._connected_device = device
    adb_manager._connection_state = ADBState.CONNECTED
    
    with patch.object(adb_manager, "_run_adb", return_value=(True, "disconnected 192.168.1.100:5555", "")) as mock_run:
        result = adb_manager.disconnect()
        assert result is True
        mock_run.assert_called_once_with(["disconnect", "192.168.1.100:5555"], timeout=5)
        assert adb_manager.connected_device is None


# -----------------------------------------------------------------------------
# All Devices Tests
# -----------------------------------------------------------------------------

def test_get_all_devices_mixed(adb_manager):
    """Test get_all_devices returns both USB and network devices."""
    output = "List of devices attached\nABC123\tdevice usb:1-2\n192.168.1.100:5555\tdevice\n\n"
    with patch.object(adb_manager, "_run_adb", return_value=(True, output, "")):
        devices = adb_manager.get_all_devices()
        assert len(devices) == 2
        assert devices[0].serial == "ABC123"
        assert devices[0].connection_type == "usb"
        assert devices[1].serial == "192.168.1.100:5555"
        assert devices[1].connection_type == "tcpip"
        assert devices[1].ip_port == "192.168.1.100:5555"


def test_get_all_devices_emulator_treated_as_usb(adb_manager):
    """Test get_all_devices treats emulator as USB type."""
    output = "List of devices attached\nemulator-5554\tdevice\n\n"
    with patch.object(adb_manager, "_run_adb", return_value=(True, output, "")):
        devices = adb_manager.get_all_devices()
        assert len(devices) == 1
        assert devices[0].serial == "emulator-5554"
        assert devices[0].connection_type == "usb"  # emulator doesn't have : in serial
        assert devices[0].ip_port is None


# -----------------------------------------------------------------------------
# Shell Command Tests
# -----------------------------------------------------------------------------

def test_run_shell_command_no_device(adb_manager):
    """Test run_shell_command fails when no device connected."""
    success, stdout, stderr = adb_manager.run_shell_command("getprop ro.product.model")
    assert success is False
    assert "No device connected" in stderr


def test_run_shell_command_not_connected_state(adb_manager):
    """Test run_shell_command fails when not in connected state."""
    adb_manager._connected_device = ADBDevice("ABC123", "device", "usb")
    adb_manager._connection_state = ADBState.UNAUTHORIZED
    
    success, stdout, stderr = adb_manager.run_shell_command("getprop ro.product.model")
    assert success is False
    assert "not connected" in stderr.lower()


def test_run_shell_command_rejects_unsafe(adb_manager):
    """Test run_shell_command rejects unsafe commands."""
    adb_manager._connected_device = ADBDevice("ABC123", "device", "usb")
    adb_manager._connection_state = ADBState.CONNECTED
    
    unsafe_commands = [
        "pm uninstall com.example.app",
        "pm disable-user com.example.app",
        "rm /data/local/tmp/file",
        "reboot",
        "settings put global something 1",
        "getprop ro.product.model; pm disable-user com.example.app",
        "cat /proc/meminfo && reboot",
        "dumpsys battery | pm uninstall com.example.app",
    ]
    
    for cmd in unsafe_commands:
        success, stdout, stderr = adb_manager.run_shell_command(cmd)
        assert success is False
        assert "not allowed" in stderr or "Command not allowed" in stderr


def test_run_package_action_is_allowlisted_and_pinned_to_connected_device(adb_manager):
    """Package mutations use a separate explicit API and target the selected TV."""
    adb_manager._connected_device = ADBDevice("ABC123", "device", "usb")
    adb_manager._connection_state = ADBState.CONNECTED
    with patch.object(adb_manager, "_run_adb", return_value=(True, "Success", "")) as run:
        assert adb_manager.run_package_action("disable", "com.example.app")[0] is True
        run.assert_called_once_with(["-s", "ABC123", "shell", "pm", "disable-user", "com.example.app"], timeout=30)


def test_run_package_action_rejects_invalid_action_and_package(adb_manager):
    adb_manager._connected_device = ADBDevice("ABC123", "device", "usb")
    adb_manager._connection_state = ADBState.CONNECTED
    for action, package in [
        ("reboot", "com.example.app"),
        ("disable", "com.example.app; reboot"),
        ("uninstall", ""),
        ("disable", "a." + "b" * 254),
        ("disable", None),
    ]:
        success, _, error = adb_manager.run_package_action(action, package)
        assert success is False
        assert error


def test_run_shell_command_allows_safe(adb_manager):
    """Test run_shell_command allows safe read-only commands."""
    adb_manager._connected_device = ADBDevice("ABC123", "device", "usb")
    adb_manager._connection_state = ADBState.CONNECTED
    
    safe_commands = [
        "getprop ro.product.model",
        "cat /proc/cpuinfo",
        "cat /sys/class/thermal/thermal_zone0/temp",
        "cat /sys/devices/system/cpu/cpu0/cpufreq/scaling_cur_freq 2>/dev/null || cat /sys/devices/system/cpu/cpu0/cpufreq/cpuinfo_cur_freq 2>/dev/null",
        "ls /system/app",
        "ls /sys/class/thermal/",
        "df /data",
        "dumpsys battery",
        "dumpsys wifi | head -50",
        "dumpsys package com.android.settings",
        "pm list packages",
        "pm list packages -f",
        "pm dump com.android.settings | grep -A1 'label='",
        "pm list packages -c android.intent.category.HOME",
        "pm get-installer com.android.settings",
        "settings get secure install_non_market_apps",
        "wm size",
        "ip addr show",
        "getenforce",
        "which pm",
        "cmd package resolve-activity --brief android.intent.action.MAIN android.intent.category.HOME",
        "dumpsys package com.android.settings | grep -A1 'label='",
    ]
    
    for cmd in safe_commands:
        with patch.object(adb_manager, "_run_adb", return_value=(True, "output", "")) as mock_run:
            success, stdout, stderr = adb_manager.run_shell_command(cmd)
            assert success is True
            mock_run.assert_called_once_with(["-s", "ABC123", "shell", cmd])


# -----------------------------------------------------------------------------
# Device Properties Tests
# -----------------------------------------------------------------------------

def test_get_device_properties(adb_manager):
    """Test get_device_properties returns expected keys."""
    adb_manager._connected_device = ADBDevice("ABC123", "device", "usb")
    adb_manager._connection_state = ADBState.CONNECTED
    
    props = {
        "ro.product.manufacturer": "Sony",
        "ro.product.model": "XR-65A80K",
        "ro.build.version.release": "12",
        "ro.build.version.sdk": "31",
        "ro.build.id": "SP1A.210812.016",
        "ro.product.cpu.abi": "arm64-v8a",
        "ro.build.characteristics": "tv",
    }
    
    def mock_run_shell(cmd, timeout=None):
        # cmd is like "getprop ro.product.manufacturer"
        prop = cmd.split()[-1]
        return True, props.get(prop, "Unknown"), ""
    
    with patch.object(adb_manager, "run_shell_command", side_effect=mock_run_shell):
        result = adb_manager.get_device_properties()
        
        for key in props:
            assert key in result
            assert result[key] == props[key]


def test_get_device_properties_missing(adb_manager):
    """Test get_device_properties handles missing properties."""
    adb_manager._connected_device = ADBDevice("ABC123", "device", "usb")
    adb_manager._connection_state = ADBState.CONNECTED
    
    with patch.object(adb_manager, "_run_adb", return_value=(False, "", "property not found")):
        result = adb_manager.get_device_properties()
        for key in result:
            assert result[key] == "Unknown"


# -----------------------------------------------------------------------------
# Storage Info Tests
# -----------------------------------------------------------------------------

def test_get_storage_info_success(adb_manager):
    """Test get_storage_info parses df output correctly."""
    adb_manager._connected_device = ADBDevice("ABC123", "device", "usb")
    adb_manager._connection_state = ADBState.CONNECTED
    
    # df output: Filesystem 1K-blocks Used Available Use% Mounted on
    df_output = "Filesystem     1K-blocks      Used Available Use% Mounted on\n/data       32505856  14320128  18185728  44% /data\n"
    
    with patch.object(adb_manager, "run_shell_command", return_value=(True, df_output, "")):
        result = adb_manager.get_storage_info()
        
        assert "total_gb" in result
        assert "used_gb" in result
        assert "free_gb" in result
        assert "free_percent" in result
        assert result["total_gb"] == round(32505856 / 1024 / 1024, 2)
        assert result["used_gb"] == round(14320128 / 1024 / 1024, 2)
        assert result["free_gb"] == round(18185728 / 1024 / 1024, 2)


def test_get_storage_info_failure(adb_manager):
    """Test get_storage_info handles command failure."""
    adb_manager._connected_device = ADBDevice("ABC123", "device", "usb")
    adb_manager._connection_state = ADBState.CONNECTED
    
    with patch.object(adb_manager, "run_shell_command", return_value=(False, "", "permission denied")):
        result = adb_manager.get_storage_info()
        assert "error" in result
        assert "permission denied" in result["error"].lower()


def test_get_storage_info_unparsable(adb_manager):
    """Test get_storage_info handles unparsable output."""
    adb_manager._connected_device = ADBDevice("ABC123", "device", "usb")
    adb_manager._connection_state = ADBState.CONNECTED
    
    with patch.object(adb_manager, "run_shell_command", return_value=(True, "weird output", "")):
        result = adb_manager.get_storage_info()
        assert "error" in result


# -----------------------------------------------------------------------------
# Guidance Tests
# -----------------------------------------------------------------------------

def test_get_adb_installation_guidance(adb_manager):
    """Test get_adb_installation_guidance returns helpful text."""
    guidance = adb_manager.get_adb_installation_guidance()
    assert "Android SDK Platform Tools" in guidance
    assert "developer.android.com" in guidance
    assert "PATH" in guidance
    assert "winget" in guidance or "choco" in guidance


def test_get_connection_guidance_all_states(adb_manager):
    """Test get_connection_guidance returns text for all states."""
    for state in ADBState:
        guidance = adb_manager.get_connection_guidance(state)
        assert isinstance(guidance, str)
        assert len(guidance) > 0


def test_get_connection_guidance_error_includes_last_error(adb_manager):
    """Test error guidance includes last error details."""
    adb_manager._last_error = "custom error message"
    guidance = adb_manager.get_connection_guidance(ADBState.ERROR)
    assert "custom error message" in guidance


# -----------------------------------------------------------------------------
# IP Validation Tests
# -----------------------------------------------------------------------------

@pytest.mark.parametrize("ip,expected", [
    ("192.168.1.1", True),
    ("10.0.0.1", True),
    ("172.16.0.1", True),
    ("255.255.255.255", True),
    ("0.0.0.0", True),
    ("256.1.1.1", False),
    ("192.168.1", False),
    ("192.168.1.1.1", False),
    ("not-an-ip", False),
    ("", False),
    ("abc.def.ghi.jkl", False),
])
def test_is_valid_ip(adb_manager, ip, expected):
    """Test IP validation with various inputs."""
    assert adb_manager._is_valid_ip(ip) == expected


# -----------------------------------------------------------------------------
# _run_adb Tests
# -----------------------------------------------------------------------------

def test_run_adb_success(adb_manager):
    """Test _run_adb returns success on exit code 0."""
    with patch("adb_manager.subprocess.run") as mock_run:
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = "output"
        mock_result.stderr = ""
        mock_run.return_value = mock_result
        
        success, stdout, stderr = adb_manager._run_adb(["devices"])
        assert success is True
        assert stdout == "output"
        assert stderr == ""
        mock_run.assert_called_once()


def test_run_adb_failure(adb_manager):
    """Test _run_adb returns failure on non-zero exit code."""
    with patch("adb_manager.subprocess.run") as mock_run:
        mock_result = MagicMock()
        mock_result.returncode = 1
        mock_result.stdout = ""
        mock_result.stderr = "error message"
        mock_run.return_value = mock_result
        
        success, stdout, stderr = adb_manager._run_adb(["devices"])
        assert success is False
        assert stdout == ""
        assert stderr == "error message"


def test_run_adb_timeout(adb_manager):
    """Test _run_adb handles timeout."""
    with patch("adb_manager.subprocess.run", side_effect=subprocess.TimeoutExpired("cmd", 10)):
        success, stdout, stderr = adb_manager._run_adb(["devices"], timeout=10)
        assert success is False
        assert "timed out" in stderr.lower()


def test_run_adb_file_not_found(adb_manager):
    """Test _run_adb handles FileNotFoundError."""
    with patch("adb_manager.subprocess.run", side_effect=FileNotFoundError()):
        success, stdout, stderr = adb_manager._run_adb(["devices"])
        assert success is False
        assert "ADB executable not found" in stderr


def test_run_adb_no_adb_path(adb_manager_no_adb):
    """Test _run_adb fails fast when no ADB path."""
    success, stdout, stderr = adb_manager_no_adb._run_adb(["devices"])
    assert success is False
    assert "ADB executable not found" in stderr


# -----------------------------------------------------------------------------
# Connection State Transitions
# -----------------------------------------------------------------------------

def test_state_transition_usb_connect_then_disconnect(adb_manager):
    """Test full USB connect -> disconnect state transition."""
    device = ADBDevice("ABC123", "device", "usb")
    
    with patch.object(adb_manager, "get_usb_devices", return_value=[device]):
        result = adb_manager.connect_usb()
        assert result.success is True
        assert adb_manager.connection_state == ADBState.CONNECTED
        
        result = adb_manager.disconnect()
        assert result is True
        assert adb_manager.connection_state == ADBState.NO_DEVICE
        assert adb_manager.connected_device is None


def test_state_transition_network_connect_then_disconnect(adb_manager):
    """Test full network connect -> disconnect state transition."""
    with patch.object(adb_manager, "_run_adb", return_value=(True, "connected to 192.168.1.100:5555", "")):
        with patch.object(adb_manager, "get_all_devices", return_value=[
            ADBDevice("192.168.1.100:5555", "device", "tcpip", ip_port="192.168.1.100:5555")
        ]):
            result = adb_manager.connect_network("192.168.1.100", 5555)
            assert result.success is True
            assert adb_manager.connection_state == ADBState.CONNECTED
        
        with patch.object(adb_manager, "_run_adb", return_value=(True, "disconnected", "")):
            result = adb_manager.disconnect()
            assert result is True
            assert adb_manager.connection_state == ADBState.NO_DEVICE


# -----------------------------------------------------------------------------
# Integration-style Tests
# -----------------------------------------------------------------------------

def test_full_usb_flow_authorized(adb_manager):
    """Test complete USB flow: discover -> connect -> run command -> disconnect."""
    device = ADBDevice("ABC123", "device", "usb")
    
    with patch.object(adb_manager, "get_usb_devices", return_value=[device]):
        connect_result = adb_manager.connect_usb()
    assert connect_result.success
    
    with patch.object(adb_manager, "_run_adb", return_value=(True, "Sony", "")):
        success, stdout, stderr = adb_manager.run_shell_command("getprop ro.product.manufacturer")
    assert success
    assert stdout == "Sony"
    
    disconnect_result = adb_manager.disconnect()
    assert disconnect_result
    assert adb_manager.connection_state == ADBState.NO_DEVICE


def test_full_network_flow(adb_manager):
    """Test complete network flow: connect -> verify -> disconnect."""
    with patch.object(adb_manager, "_run_adb", return_value=(True, "connected to 192.168.1.100:5555", "")):
        with patch.object(adb_manager, "get_all_devices", return_value=[
            ADBDevice("192.168.1.100:5555", "device", "tcpip", ip_port="192.168.1.100:5555")
        ]):
            connect_result = adb_manager.connect_network("192.168.1.100", 5555)
    assert connect_result.success
    assert adb_manager.connection_state == ADBState.CONNECTED
    assert adb_manager.connected_device.ip_port == "192.168.1.100:5555"
    
    with patch.object(adb_manager, "_run_adb", return_value=(True, "disconnected", "")):
        disconnect_result = adb_manager.disconnect()
    assert disconnect_result


# -----------------------------------------------------------------------------
# Safety Tests - No Device Modifying Commands
# -----------------------------------------------------------------------------

def test_never_executes_modifying_commands(adb_manager):
    """Verify manager never allows modifying commands."""
    adb_manager._connected_device = ADBDevice("ABC123", "device", "usb")
    adb_manager._connection_state = ADBState.CONNECTED
    
    modifying_commands = [
        "pm uninstall com.test",
        "pm disable-user com.test",
        "pm enable com.test",
        "pm install /path/to.apk",
        "settings put secure something 1",
        "settings put global something 1",
        "settings put system something 1",
        "am force-stop com.test",
        "am kill-all",
        "reboot",
        "reboot recovery",
        "reboot bootloader",
        "rm -rf /data/local/tmp/*",
        "dd if=/dev/zero of=/dev/block/by-name/boot",
        "flashall",
        "fastboot flash",
        "cmd package uninstall",
    ]
    
    for cmd in modifying_commands:
        success, stdout, stderr = adb_manager.run_shell_command(cmd)
        assert success is False, f"Command should be rejected: {cmd}"
        assert "not allowed" in stderr or "Command not allowed" in stderr


def test_allows_read_only_diagnostic_commands(adb_manager):
    """Verify manager allows read-only diagnostic commands."""
    adb_manager._connected_device = ADBDevice("ABC123", "device", "usb")
    adb_manager._connection_state = ADBState.CONNECTED
    
    read_only_commands = [
        "getprop ro.product.model",
        "getprop ro.build.version.sdk",
        "cat /proc/meminfo",
        "cat /proc/cpuinfo",
        "df /data",
        "df /system",
        "ls /system/app",
        "ls /data/app",
        "dumpsys battery",
        "dumpsys meminfo",
        "dumpsys package com.android.settings",
        "pm list packages",
        "pm list packages -d",
        "pm list packages -e",
        "pm path com.android.settings",
    ]
    
    for cmd in read_only_commands:
        with patch.object(adb_manager, "_run_adb", return_value=(True, "output", "")) as mock_run:
            success, stdout, stderr = adb_manager.run_shell_command(cmd)
            assert success is True, f"Command should be allowed: {cmd}"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])