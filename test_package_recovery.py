"""
Package Recovery Tests - Tests for the package recovery workflow.

These tests verify that package recovery (re-enabling packages from backups)
works correctly with proper safety checks, validation, and error handling.
"""

import pytest
import time
from unittest.mock import Mock, patch, MagicMock
from pathlib import Path

from backup_manager import (
    BackupManager,
    BackupContent,
    BackupMetadata,
    BackupType,
    BackupStatus,
    create_backup_manager,
)
from action_engine import (
    ActionEngine,
    ExecutionResult,
    ExecutionPhase,
    create_action_engine,
)
from action_history import (
    ActionHistory,
    ActionRecord,
    ActionType as HistoryActionType,
    ActionStatus,
    create_action_history,
)
from package_inventory import (
    PackageInventory,
    PackageInfo,
    PackageCategory,
    PackageSource,
    create_package_inventory,
)
from package_classifier import (
    PackageClassifier,
    PackageSafetyAssessment,
    SafetyLevel,
    ActionType,
    create_package_classifier,
)
from device_identification import DeviceIdentity
from diagnostics import DiagnosticResult
from adb_manager import ADBManager, ADBState, ADBDevice, ADBConnectionResult


class MockADBManager:
    """Mock ADB manager for testing."""
    def __init__(self, connected=True, adb_path="/fake/adb"):
        self._adb_path = adb_path
        self._connected_device = ADBDevice("TEST123", "device", "usb") if connected else None
        self._connection_state = ADBState.CONNECTED if connected else ADBState.NO_DEVICE
        self._last_error = None
        self.run_shell_command_results = {}
        self.get_all_devices_result = []
        self.get_usb_devices_result = []

    @property
    def adb_path(self):
        return self._adb_path

    @property
    def is_adb_available(self):
        return self._adb_path is not None

    @property
    def connection_state(self):
        return self._connection_state

    @property
    def connected_device(self):
        return self._connected_device

    @connected_device.setter
    def connected_device(self, value):
        self._connected_device = value

    @property
    def last_error(self):
        return self._last_error

    def run_shell_command(self, command: str):
        if command in self.run_shell_command_results:
            return self.run_shell_command_results[command]
        return True, "output", ""

    def get_all_devices(self):
        return self.get_all_devices_result

    def get_usb_devices(self):
        return self.get_usb_devices_result


class TestBackupManagerPackageRecovery:
    """Tests for BackupManager package recovery methods."""

    @pytest.fixture
    def mock_adb(self):
        return MockADBManager()

    @pytest.fixture
    def backup_manager(self, mock_adb):
        with patch("backup_manager.DeviceIdentifier"), \
             patch("backup_manager.DiagnosticsEngine"), \
             patch("backup_manager.PackageInventory"), \
             patch("backup_manager.PackageClassifier"):
            bm = BackupManager(mock_adb, backup_root=Path("/tmp/test_backups"))
            # Mock the internal components
            bm.device_identifier = Mock()
            bm.diagnostics_engine = Mock()
            bm.package_inventory = Mock()
            bm.package_classifier = Mock()
            return bm

    @pytest.fixture
    def sample_device_identity(self):
        return DeviceIdentity(
            manufacturer="Sony",
            model="XR-65A80K",
            serial="TEST123",
            android_version="Android 12 (API 31)",
            api_level=31,
        )

    @pytest.fixture
    def sample_package_info_enabled(self):
        return PackageInfo(
            package_name="com.example.testapp",
            display_name="Test App",
            enabled=True,
            source=PackageSource.USER,
        )

    @pytest.fixture
    def sample_package_info_disabled(self):
        return PackageInfo(
            package_name="com.example.testapp",
            display_name="Test App",
            enabled=False,
            source=PackageSource.USER,
        )

    def test_get_package_recovery_candidates_empty_backup(self, backup_manager):
        """Test recovery candidates with empty backup."""
        backup_manager.get_backup = Mock(return_value=BackupContent(
            metadata=BackupMetadata(
                backup_id="test_backup",
                timestamp=time.time(),
                backup_type=BackupType.MANUAL,
                status=BackupStatus.COMPLETED,
                device_serial="TEST123",
                device_identity={},
                sections=["packages"],
                failed_sections=[],
            ),
            package_inventory=[],
        ))
    
        candidates = backup_manager.get_package_recovery_candidates("test_backup")
        assert candidates == []

    def test_get_package_recovery_candidates_no_backup(self, backup_manager):
        """Test recovery candidates when backup not found."""
        backup_manager.get_backup = Mock(return_value=None)
    
        candidates = backup_manager.get_package_recovery_candidates("nonexistent")
        assert candidates == []

    def test_get_package_recovery_candidates_pkg_enabled_in_backup_disabled_now(
        self, backup_manager, sample_device_identity, sample_package_info_enabled, sample_package_info_disabled
    ):
        """Test recovery candidates when package was enabled in backup but disabled now."""
        backup_pkg = sample_package_info_enabled
        current_pkg = sample_package_info_disabled
    
        backup_content = BackupContent(
            metadata=BackupMetadata(
                backup_id="test_backup",
                timestamp=time.time(),
                backup_type=BackupType.MANUAL,
                status=BackupStatus.COMPLETED,
                device_serial="TEST123",
                device_identity={},
                sections=["packages"],
                failed_sections=[],
            ),
            package_inventory=[backup_pkg],
        )
    
        backup_manager.get_backup = Mock(return_value=backup_content)
        backup_manager.package_inventory.refresh = Mock(return_value=(True, "OK"))
        backup_manager.package_inventory.get_all_packages = Mock(return_value=[current_pkg])
    
        candidates = backup_manager.get_package_recovery_candidates("test_backup")
    
        assert len(candidates) == 1
        assert candidates[0]["package_name"] == "com.example.testapp"
        assert candidates[0]["recoverable"] is True
        assert candidates[0]["current_state"] == "disabled"
        assert candidates[0]["backup_enabled"] is True

    def test_get_package_recovery_candidates_pkg_already_enabled(
        self, backup_manager, sample_device_identity, sample_package_info_enabled
    ):
        """Test recovery candidates when package already enabled."""
        backup_pkg = sample_package_info_enabled
        current_pkg = sample_package_info_enabled  # Same, enabled
    
        backup_content = BackupContent(
            metadata=BackupMetadata(
                backup_id="test_backup",
                timestamp=time.time(),
                backup_type=BackupType.MANUAL,
                status=BackupStatus.COMPLETED,
                device_serial="TEST123",
                device_identity={},
                sections=["packages"],
                failed_sections=[],
            ),
            package_inventory=[backup_pkg],
        )
    
        backup_manager.get_backup = Mock(return_value=backup_content)
        backup_manager.package_inventory.refresh = Mock(return_value=(True, "OK"))
        backup_manager.package_inventory.get_all_packages = Mock(return_value=[current_pkg])
    
        candidates = backup_manager.get_package_recovery_candidates("test_backup")
    
        assert len(candidates) == 1
        assert candidates[0]["recoverable"] is False
        assert candidates[0]["current_state"] == "enabled"

    def test_get_package_recovery_candidates_pkg_not_installed(
        self, backup_manager, sample_package_info_enabled
    ):
        """Test recovery candidates when package no longer installed."""
        backup_pkg = sample_package_info_enabled
    
        backup_content = BackupContent(
            metadata=BackupMetadata(
                backup_id="test_backup",
                timestamp=time.time(),
                backup_type=BackupType.MANUAL,
                status=BackupStatus.COMPLETED,
                device_serial="TEST123",
                device_identity={},
                sections=["packages"],
                failed_sections=[],
            ),
            package_inventory=[backup_pkg],
        )
    
        backup_manager.get_backup = Mock(return_value=backup_content)
        backup_manager.package_inventory.refresh = Mock(return_value=(True, "OK"))
        backup_manager.package_inventory.get_all_packages = Mock(return_value=[])
    
        candidates = backup_manager.get_package_recovery_candidates("test_backup")
    
        assert len(candidates) == 1
        assert candidates[0]["recoverable"] is False
        assert candidates[0]["current_state"] == "not_installed"

    def test_get_package_recovery_candidates_pkg_was_disabled_in_backup(
        self, backup_manager, sample_package_info_disabled
    ):
        """Test recovery candidates when package was disabled in backup."""
        backup_pkg = sample_package_info_disabled
        current_pkg = sample_package_info_disabled
    
        backup_content = BackupContent(
            metadata=BackupMetadata(
                backup_id="test_backup",
                timestamp=time.time(),
                backup_type=BackupType.MANUAL,
                status=BackupStatus.COMPLETED,
                device_serial="TEST123",
                device_identity={},
                sections=["packages"],
                failed_sections=[],
            ),
            package_inventory=[backup_pkg],
        )
    
        backup_manager.get_backup = Mock(return_value=backup_content)
        backup_manager.package_inventory.refresh = Mock(return_value=(True, "OK"))
        backup_manager.package_inventory.get_all_packages = Mock(return_value=[current_pkg])
    
        candidates = backup_manager.get_package_recovery_candidates("test_backup")
    
        # Package was disabled in backup, so not recoverable (wasn't enabled originally)
        assert len(candidates) == 0

    def test_restore_package_success(self, backup_manager, sample_package_info_enabled, sample_package_info_disabled):
        """Test successful package restore."""
        backup_pkg = sample_package_info_enabled
        current_pkg = sample_package_info_disabled
    
        backup_content = BackupContent(
            metadata=BackupMetadata(
                backup_id="test_backup",
                timestamp=time.time(),
                backup_type=BackupType.MANUAL,
                status=BackupStatus.COMPLETED,
                device_serial="TEST123",
                device_identity={},
                sections=["packages"],
                failed_sections=[],
            ),
            package_inventory=[backup_pkg],
        )
    
        backup_manager.get_backup = Mock(return_value=backup_content)
        backup_manager.package_inventory.refresh = Mock(return_value=(True, "OK"))
        backup_manager.package_inventory.get_package = Mock(side_effect=[
            current_pkg,  # First call - current state (disabled)
            sample_package_info_enabled,  # Second call - after enable (enabled)
        ])
    
        # Mock the ADB command to succeed
        backup_manager.adb_manager.run_shell_command = Mock(return_value=(True, "Success", ""))
        backup_manager.package_classifier.assess_package = Mock(return_value=PackageSafetyAssessment(
            package_name="com.example.testapp",
            display_name="Test App",
            safety_level=SafetyLevel.USER_APP,
            allowed_actions=[ActionType.ENABLE],
            confidence=0.95,
        ))
    
        success, msg = backup_manager.restore_package("test_backup", "com.example.testapp")
    
        assert success is True
        assert "Successfully re-enabled" in msg
        backup_manager.adb_manager.run_shell_command.assert_called_with("pm enable com.example.testapp")

    def test_restore_package_not_found_in_backup(self, backup_manager):
        """Test restore when package not in backup."""
        backup_content = BackupContent(
            metadata=BackupMetadata(
                backup_id="test_backup",
                timestamp=time.time(),
                backup_type=BackupType.MANUAL,
                status=BackupStatus.COMPLETED,
                device_serial="TEST123",
                device_identity={},
                sections=["packages"],
                failed_sections=[],
            ),
            package_inventory=[],  # Empty inventory
        )
    
        backup_manager.get_backup = Mock(return_value=backup_content)
    
        success, msg = backup_manager.restore_package("test_backup", "com.nonexistent")
    
        assert success is False
        assert "No package inventory in backup" in msg

    def test_restore_package_already_enabled(self, backup_manager, sample_package_info_enabled):
        """Test restore when package already enabled."""
        backup_pkg = sample_package_info_enabled
        current_pkg = sample_package_info_enabled  # Already enabled
    
        backup_content = BackupContent(
            metadata=BackupMetadata(
                backup_id="test_backup",
                timestamp=time.time(),
                backup_type=BackupType.MANUAL,
                status=BackupStatus.COMPLETED,
                device_serial="TEST123",
                device_identity={},
                sections=["packages"],
                failed_sections=[],
            ),
            package_inventory=[sample_package_info_enabled],
        )
    
        backup_manager.get_backup = Mock(return_value=backup_content)
        backup_manager.package_inventory.refresh = Mock(return_value=(True, "OK"))
        backup_manager.package_inventory.get_package = Mock(return_value=sample_package_info_enabled)
    
        success, msg = backup_manager.restore_package("test_backup", "com.example.testapp")
    
        assert success is False
        assert "already enabled" in msg

    def test_restore_package_not_installed(self, backup_manager, sample_package_info_enabled):
        """Test restore when package no longer installed."""
        backup_content = BackupContent(
            metadata=BackupMetadata(
                backup_id="test_backup",
                timestamp=time.time(),
                backup_type=BackupType.MANUAL,
                status=BackupStatus.COMPLETED,
                device_serial="TEST123",
                device_identity={},
                sections=["packages"],
                failed_sections=[],
            ),
            package_inventory=[sample_package_info_enabled],
        )
    
        backup_manager.get_backup = Mock(return_value=backup_content)
        backup_manager.package_inventory.refresh = Mock(return_value=(True, "OK"))
        backup_manager.package_inventory.get_package = Mock(return_value=None)  # Not installed
    
        success, msg = backup_manager.restore_package("test_backup", "com.example.testapp")
    
        assert success is False
        assert "no longer installed" in msg

    def test_restore_package_device_mismatch(self, backup_manager, sample_package_info_enabled):
        """Test restore with device mismatch."""
        backup_content = BackupContent(
            metadata=BackupMetadata(
                backup_id="test_backup",
                timestamp=time.time(),
                backup_type=BackupType.MANUAL,
                status=BackupStatus.COMPLETED,
                device_serial="OTHER_DEVICE",
                device_identity={},
                sections=["packages"],
                failed_sections=[],
            ),
            package_inventory=[sample_package_info_enabled],
        )
    
        backup_manager.get_backup = Mock(return_value=backup_content)
        backup_manager.adb_manager.connected_device = Mock(serial="TEST123")
    
        success, msg = backup_manager.restore_package("test_backup", "com.example.testapp")
    
        assert success is False
        assert "different device" in msg

    def test_restore_package_was_disabled_in_backup(self, backup_manager, sample_package_info_disabled):
        """Test restore when package was disabled in backup."""
        backup_content = BackupContent(
            metadata=BackupMetadata(
                backup_id="test_backup",
                timestamp=time.time(),
                backup_type=BackupType.MANUAL,
                status=BackupStatus.COMPLETED,
                device_serial="TEST123",
                device_identity={},
                sections=["packages"],
                failed_sections=[],
            ),
            package_inventory=[PackageInfo(package_name="com.example.testapp", enabled=False)],
        )
    
        backup_manager.get_backup = Mock(return_value=backup_content)
    
        success, msg = backup_manager.restore_package("test_backup", "com.example.testapp")
    
        assert success is False
        assert "not enabled in the backup" in msg


class TestActionEnginePackageRestore:
    """Tests for ActionEngine package restore execution."""

    @pytest.fixture
    def mock_adb(self):
        return MockADBManager()

    @pytest.fixture
    def action_engine(self, mock_adb):
        with patch("action_engine.DeviceIdentifier"), \
             patch("action_engine.DiagnosticsEngine"), \
             patch("action_engine.PackageInventory"), \
             patch("action_engine.PackageClassifier"), \
             patch("action_engine.BackupManager"), \
             patch("action_engine.ActionHistory"), \
             patch("action_engine.RecommendationEngine"):
            ae = ActionEngine(mock_adb)
            ae.device_identifier = Mock()
            ae.diagnostics_engine = Mock()
            ae.package_inventory = Mock()
            ae.package_classifier = Mock()
            ae.backup_manager = Mock()
            ae.action_history = Mock()
            return ae

    def test_uninstall_rejects_non_user_apps_before_backup(self, action_engine):
        action_engine.package_inventory.get_package = Mock(return_value=PackageInfo(
            package_name="com.example.systemapp",
            source=PackageSource.SYSTEM,
        ))

        result = action_engine.execute_uninstall_package(
            package_name="com.example.systemapp",
            confirmed=True,
        )

        assert result.success is False
        assert "user-installed apps" in result.message
        action_engine.backup_manager.create_backup.assert_not_called()

    def test_execute_restore_package_success(self, action_engine):
        """Test successful package restore execution."""
        # Mock backup content
        backup_pkg = PackageInfo(package_name="com.example.testapp", display_name="Test App", enabled=True)
        backup_content = BackupContent(
            metadata=BackupMetadata(
                backup_id="test_backup",
                timestamp=time.time(),
                backup_type=BackupType.MANUAL,
                status=BackupStatus.COMPLETED,
                device_serial="TEST123",
                device_identity={},
                sections=["packages"],
                failed_sections=[],
            ),
            package_inventory=[PackageInfo(package_name="com.example.testapp", enabled=True)],
        )

        action_engine.backup_manager.get_backup = Mock(return_value=BackupContent(
            metadata=BackupMetadata(
                backup_id="test_backup",
                timestamp=time.time(),
                backup_type=BackupType.MANUAL,
                status=BackupStatus.COMPLETED,
                device_serial="TEST123",
                device_identity={},
                sections=["packages"],
                failed_sections=[],
            ),
            package_inventory=[PackageInfo(package_name="com.example.testapp", enabled=True)],
        ))

        action_engine.adb_manager.connected_device = Mock(serial="TEST123")
        action_engine.package_inventory.refresh = Mock(return_value=(True, "Package inventory refreshed"))
        # First call: currently disabled; second call (after enable): enabled
        action_engine.package_inventory.get_package = Mock(side_effect=[
            PackageInfo(package_name="com.example.testapp", display_name="Test App", enabled=False),
            PackageInfo(package_name="com.example.testapp", display_name="Test App", enabled=True),
        ])

        action_engine.package_classifier.assess_package = Mock(return_value=PackageSafetyAssessment(
            package_name="com.example.testapp",
            display_name="Test App",
            safety_level=SafetyLevel.USER_APP,
            allowed_actions=[ActionType.ENABLE],
            confidence=0.95,
        ))

        action_engine.backup_manager.create_backup = Mock(return_value=BackupMetadata(
            backup_id="recovery_backup_123",
            timestamp=time.time(),
            backup_type=BackupType.PRE_ACTION,
            status=BackupStatus.COMPLETED,
            device_serial="TEST123",
            device_identity={},
            sections=[],
            failed_sections=[],
        ))

        # First call: package is disabled; second call: enabled after recovery
        action_engine.package_inventory.get_package = Mock(side_effect=[
            PackageInfo(
                package_name="com.example.testapp",
                display_name="Test App",
                enabled=False,
            ),
            PackageInfo(
                package_name="com.example.testapp",
                display_name="Test App",
                enabled=True,
            ),
        ])

        action_engine.action_history.create_action = Mock(return_value=ActionRecord(
            action_id="action_123",
            timestamp=time.time(),
            action_type=HistoryActionType.ENABLE_PACKAGE,
            target="com.example.testapp",
        ))
        action_engine.action_history.confirm_action = Mock()
        action_engine.action_history.start_execution = Mock()
        action_engine.action_history.complete_action = Mock()

        result = action_engine.execute_restore_package(
            package_name="com.example.testapp",
            backup_id="test_backup",
            confirmed=True,
        )

        assert result.success is True
        assert "Successfully restored" in result.message
        assert result.verification_passed is True
        assert result.backup_id == "recovery_backup_123"

    def test_execute_restore_package_not_confirmed(self, action_engine):
        """Test restore package requires confirmation."""
        backup_content = BackupContent(
            metadata=BackupMetadata(
                backup_id="test_backup",
                timestamp=time.time(),
                backup_type=BackupType.MANUAL,
                status=BackupStatus.COMPLETED,
                device_serial="TEST123",
                device_identity={},
                sections=["packages"],
                failed_sections=[],
            ),
            package_inventory=[PackageInfo(package_name="com.example.testapp", enabled=True)],
        )

        action_engine.backup_manager.get_backup = Mock(return_value=BackupContent(
            metadata=BackupMetadata(
                backup_id="test_backup",
                timestamp=time.time(),
                backup_type=BackupType.MANUAL,
                status=BackupStatus.COMPLETED,
                device_serial="TEST123",
                device_identity={},
                sections=["packages"],
                failed_sections=[],
            ),
            package_inventory=[PackageInfo(package_name="com.example.testapp", enabled=True)],
        ))

        action_engine.adb_manager.connected_device = Mock(serial="TEST123")
        action_engine.package_inventory.refresh = Mock(return_value=(True, "Package inventory refreshed"))
        action_engine.package_inventory.get_package = Mock(return_value=PackageInfo(
            package_name="com.example.testapp",
            enabled=False,
        ))

        action_engine.package_classifier.assess_package = Mock(return_value=PackageSafetyAssessment(
            package_name="com.example.testapp",
            display_name="Test App",
            safety_level=SafetyLevel.USER_APP,
            allowed_actions=[ActionType.ENABLE],
            confidence=0.95,
        ))

        action_engine.backup_manager.create_backup = Mock(return_value=BackupMetadata(
            backup_id="recovery_backup_123",
            timestamp=time.time(),
            backup_type=BackupType.PRE_ACTION,
            status=BackupStatus.COMPLETED,
            device_serial="TEST123",
            device_identity={},
            sections=[],
            failed_sections=[],
        ))

        action_engine.action_history.create_action = Mock(return_value=ActionRecord(
            action_id="action_123",
            timestamp=time.time(),
            action_type=HistoryActionType.ENABLE_PACKAGE,
            target="com.example.testapp",
        ))

        result = action_engine.execute_restore_package(
            package_name="com.example.testapp",
            backup_id="test_backup",
            confirmed=False,  # Not confirmed
        )

        assert result.success is False
        assert result.phase == ExecutionPhase.CONFIRMATION
        assert "User confirmation required" in result.message
        assert result.details["action"] == "restore_package"

    def test_execute_restore_package_backup_not_found(self, action_engine):
        """Test restore when backup not found."""
        action_engine.backup_manager.get_backup = Mock(return_value=None)
        action_engine.adb_manager.connected_device = Mock(serial="TEST123")

        result = action_engine.execute_restore_package(
            package_name="com.example.testapp",
            backup_id="nonexistent",
            confirmed=True,
        )

        assert result.success is False
        assert result.phase == ExecutionPhase.FAILED
        assert "Backup not found" in result.message

    def test_execute_restore_package_device_mismatch(self, action_engine):
        """Test restore with device mismatch."""
        backup_content = BackupContent(
            metadata=BackupMetadata(
                backup_id="test_backup",
                timestamp=time.time(),
                backup_type=BackupType.MANUAL,
                status=BackupStatus.COMPLETED,
                device_serial="OTHER_DEVICE",
                device_identity={},
                sections=["packages"],
                failed_sections=[],
            ),
            package_inventory=[PackageInfo(package_name="com.example.testapp", enabled=True)],
        )

        action_engine.backup_manager.get_backup = Mock(return_value=backup_content)
        action_engine.adb_manager.connected_device = Mock(serial="TEST123")

        result = action_engine.execute_restore_package(
            package_name="com.example.testapp",
            backup_id="test_backup",
            confirmed=True,
        )

        assert result.success is False
        assert "different device" in result.message

    def test_execute_restore_package_already_enabled(self, action_engine):
        """Test restore when package already enabled."""
        action_engine.backup_manager.get_backup = Mock(return_value=BackupContent(
            metadata=BackupMetadata(
                backup_id="test_backup",
                timestamp=time.time(),
                backup_type=BackupType.MANUAL,
                status=BackupStatus.COMPLETED,
                device_serial="TEST123",
                device_identity={},
                sections=["packages"],
                failed_sections=[],
            ),
            package_inventory=[PackageInfo(package_name="com.example.testapp", enabled=True)],
        ))

        action_engine.adb_manager.connected_device = Mock(serial="TEST123")
        action_engine.package_inventory.get_package = Mock(return_value=PackageInfo(
            package_name="com.example.testapp",
            enabled=True,  # Already enabled
        ))

        result = action_engine.execute_restore_package(
            package_name="com.example.testapp",
            backup_id="test_backup",
            confirmed=True,
        )

        assert result.success is False
        assert "already enabled" in result.message

    def test_execute_restore_package_not_installed(self, action_engine):
        """Test restore when package not installed."""
        action_engine.backup_manager.get_backup = Mock(return_value=BackupContent(
            metadata=BackupMetadata(
                backup_id="test_backup",
                timestamp=time.time(),
                backup_type=BackupType.MANUAL,
                status=BackupStatus.COMPLETED,
                device_serial="TEST123",
                device_identity={},
                sections=["packages"],
                failed_sections=[],
            ),
            package_inventory=[PackageInfo(package_name="com.example.testapp", enabled=True)],
        ))

        action_engine.adb_manager.connected_device = Mock(serial="TEST123")
        action_engine.package_inventory.get_package = Mock(return_value=None)  # Not installed

        result = action_engine.execute_restore_package(
            package_name="com.example.testapp",
            backup_id="test_backup",
            confirmed=True,
        )

        assert result.success is False
        assert "not installed" in result.message

    def test_execute_restore_package_pkg_disabled_in_backup(self, action_engine):
        """Test restore when package was disabled in backup."""
        action_engine.backup_manager.get_backup = Mock(return_value=BackupContent(
            metadata=BackupMetadata(
                backup_id="test_backup",
                timestamp=time.time(),
                backup_type=BackupType.MANUAL,
                status=BackupStatus.COMPLETED,
                device_serial="TEST123",
                device_identity={},
                sections=["packages"],
                failed_sections=[],
            ),
            package_inventory=[PackageInfo(package_name="com.example.testapp", enabled=False)],  # Was disabled
        ))

        action_engine.adb_manager.connected_device = Mock(serial="TEST123")

        result = action_engine.execute_restore_package(
            package_name="com.example.testapp",
            backup_id="test_backup",
            confirmed=True,
        )

        assert result.success is False
        assert "not enabled in backup" in result.message


class TestBackupManagerGetRecoveryInfo:
    """Tests for get_recovery_info with package recovery details."""

    @pytest.fixture
    def mock_adb(self):
        return MockADBManager()

    @pytest.fixture
    def backup_manager(self, mock_adb):
        with patch("backup_manager.DeviceIdentifier"), \
             patch("backup_manager.DiagnosticsEngine"), \
             patch("backup_manager.PackageInventory"), \
             patch("backup_manager.PackageClassifier"):
            bm = BackupManager(Mock(), backup_root=Path("/tmp/test_backups"))
            bm.device_identifier = Mock()
            bm.diagnostics_engine = Mock()
            bm.package_inventory = Mock()
            bm.package_classifier = Mock()
            return bm

    def test_get_recovery_info_includes_package_candidates(self, backup_manager):
        """Test get_recovery_info includes package recovery candidates."""
        backup_content = BackupContent(
            metadata=BackupMetadata(
                backup_id="test_backup",
                timestamp=time.time(),
                backup_type=BackupType.MANUAL,
                status=BackupStatus.COMPLETED,
                device_serial="TEST123",
                device_identity={},
                sections=["packages"],
                failed_sections=[],
            ),
            package_inventory=[
                PackageInfo(package_name="com.example.app1", display_name="App 1", enabled=True),
                PackageInfo(package_name="com.example.app2", display_name="App 2", enabled=True),
                PackageInfo(package_name="com.example.app3", display_name="App 3", enabled=False),
            ],
        )
    
        backup_manager.get_backup = Mock(return_value=BackupContent(
            metadata=BackupMetadata(
                backup_id="test_backup",
                timestamp=time.time(),
                backup_type=BackupType.MANUAL,
                status=BackupStatus.COMPLETED,
                device_serial="TEST123",
                device_identity={},
                sections=["packages"],
                failed_sections=[],
            ),
            package_inventory=[
                PackageInfo(package_name="com.example.app1", display_name="App 1", enabled=True),
                PackageInfo(package_name="com.example.app2", display_name="App 2", enabled=True),
                PackageInfo(package_name="com.example.app3", display_name="App 3", enabled=False),
            ],
        ))
    
        # Mock current inventory: app1 enabled, app2 disabled, app3 disabled
        backup_manager.package_inventory.refresh = Mock(return_value=(True, "OK"))
        backup_manager.package_inventory.get_all_packages = Mock(return_value=[
            PackageInfo(package_name="com.example.app1", display_name="App 1", enabled=True),
            PackageInfo(package_name="com.example.app2", display_name="App 2", enabled=False),
            PackageInfo(package_name="com.example.app3", display_name="App 3", enabled=False),
        ])
    
        info = backup_manager.get_recovery_info("test_backup")
    
        assert "package_recovery_candidates" in info
        candidates = info["package_recovery_candidates"]
    
        # app1: was enabled, now enabled -> not recoverable
        # app2: was enabled, now disabled -> recoverable
        # app3: was disabled -> not recoverable
    
        recoverable = [c for c in candidates if c["recoverable"]]
        assert len(recoverable) == 1
        assert recoverable[0]["package_name"] == "com.example.app2"


class TestIntegrationScenarios:
    """Integration tests for complete recovery workflow."""

    @pytest.fixture
    def mock_adb(self):
        return MockADBManager()

    def test_full_disable_then_restore_workflow(self):
        """Test complete workflow: disable -> backup -> restore."""
        # This test verifies the full workflow works end-to-end
        # by checking that all components work together
        pass  # Placeholder for integration test

    def test_recovery_preserves_safety_checks(self):
        """Test that recovery still enforces safety checks."""
        # Even during recovery, critical packages should not be re-enabled
        # if they were somehow disabled
        pass  # Placeholder

    def test_recovery_updates_action_history(self):
        """Test that recovery creates proper action history entries."""
        pass  # Placeholder


if __name__ == "__main__":
    pytest.main([__file__, "-v"])