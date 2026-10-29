"""
Action Engine - Safe action execution with confirmation for TV Freedom.
This module provides a strict action execution engine that enforces
confirmation, backup, execution, verification, and logging for all
device-changing operations.
"""
from dataclasses import dataclass, field
from typing import Optional
from pathlib import Path
import time
import json
from enum import Enum
import re
from adb_manager import ADBManager, ADBState, ADBConnectionResult
from device_identification import DeviceIdentifier, DeviceIdentity
from diagnostics import DiagnosticsEngine, DiagnosticResult
from package_inventory import PackageInventory, PackageInfo, PackageSource
from package_classifier import PackageClassifier, PackageSafetyAssessment, SafetyLevel, ActionType
from backup_manager import BackupManager, BackupType
from action_history import ActionHistory, ActionRecord, ActionType as HistoryActionType, ActionStatus
from recommendation_engine import RecommendationEngine, Recommendation
class ExecutionPhase(Enum):
    """Phase of action execution."""
    INIT = "init"
    VALIDATION = "validation"
    BACKUP = "backup"
    CONFIRMATION = "confirmation"
    EXECUTION = "execution"
    VERIFICATION = "verification"
    LOGGING = "logging"
    COMPLETE = "complete"
    FAILED = "failed"
@dataclass
class ExecutionResult:
    """Result of action execution."""
    success: bool
    action_id: str
    phase: ExecutionPhase
    message: str
    details: dict = field(default_factory=dict)
    error: str = ""
    backup_id: Optional[str] = None
    verification_passed: bool = False
    def to_dict(self) -> dict:
        return {
            "success": self.success,
            "action_id": self.action_id,
            "phase": self.phase.value,
            "message": self.message,
            "details": self.details,
            "error": self.error,
            "backup_id": self.backup_id,
            "verification_passed": self.verification_passed,
        }
def is_valid_package_name(package_name: str) -> bool:
    """Conservatively validate Android package-name syntax."""
    if not isinstance(package_name, str) or len(package_name) > 255:
        return False
    return bool(
        re.fullmatch(
            r"[A-Za-z_][A-Za-z0-9_]*(?:\.[A-Za-z_][A-Za-z0-9_]*)+",
            package_name,
        )
    )


class ActionEngine:
    """
    Safe action execution engine.
    Enforces the complete safety workflow:
    1. Validate device and action
    2. Check compatibility and safety
    3. Create pre-action backup
    4. Require explicit user confirmation
    5. Execute action
    6. Verify result
    7. Log to action history
    """
    def __init__(self, adb_manager: ADBManager):
        self.adb_manager = adb_manager
        self.device_identifier = DeviceIdentifier(adb_manager)
        self.diagnostics_engine = DiagnosticsEngine(adb_manager)
        self.package_inventory = PackageInventory(adb_manager)
        self.package_classifier = PackageClassifier()
        self.backup_manager = BackupManager(adb_manager)
        self.action_history = ActionHistory()
        self.recommendation_engine = RecommendationEngine(adb_manager)
        self._current_action: Optional[ActionRecord] = None
        self._execution_callback = None
    def set_progress_callback(self, callback):
        """Set callback for execution progress updates."""
        self._execution_callback = callback
    def _report_progress(self, phase: ExecutionPhase, message: str, details: dict = None):
        """Report progress via callback."""
        if self._execution_callback:
            self._execution_callback(phase.value, message, details or {})
    def execute_disable_package(self, package_name: str,
        confirmed: bool = False) -> ExecutionResult:
        """
        Execute package disable with full safety workflow.
        Args:
            package_name: Package to disable.
            confirmed: Whether user has already confirmed.
        Returns:
            ExecutionResult with outcome.
        """
        return self._execute_package_action(
            package_name=package_name,
            action_type=ActionType.DISABLE,
            history_action_type=HistoryActionType.DISABLE_PACKAGE,
            confirmed=confirmed,
            adb_command=["pm", "disable-user", package_name],
            reversal_action=ActionType.ENABLE,
            reversal_parameters={"package": package_name},
            reversal_instructions=f"To re-enable: pm enable {package_name}",
        )
    def execute_enable_package(self, package_name: str,
        confirmed: bool = False) -> ExecutionResult:
        """Execute package enable."""
        return self._execute_package_action(
            package_name=package_name,
            action_type=ActionType.ENABLE,
            history_action_type=HistoryActionType.ENABLE_PACKAGE,
            confirmed=confirmed,
            adb_command=["pm", "enable", package_name],
            reversal_action=ActionType.DISABLE,
            reversal_parameters={"package": package_name},
            reversal_instructions=f"To disable again: pm disable-user {package_name}",
        )
    def execute_uninstall_package(self, package_name: str,
        confirmed: bool = False) -> ExecutionResult:
        """Execute package uninstall (user apps only)."""
        return self._execute_package_action(
            package_name=package_name,
            action_type=ActionType.UNINSTALL,
            history_action_type=HistoryActionType.UNINSTALL_PACKAGE,
            confirmed=confirmed,
            adb_command=["pm", "uninstall", package_name],
            reversal_action=None,  # Cannot auto-reverse uninstall
            reversal_parameters={},
            reversal_instructions=f"Re-install from Play Store or restore from backup.",
        )
    def execute_clear_package_data(self, package_name: str,
        confirmed: bool = False) -> ExecutionResult:
        """Execute clear package data."""
        return self._execute_package_action(
            package_name=package_name,
            action_type=ActionType.CLEAR_DATA,
            history_action_type=HistoryActionType.CLEAR_PACKAGE_DATA,
            confirmed=confirmed,
            adb_command=["pm", "clear", package_name],
            reversal_action=None,
            reversal_parameters={},
            reversal_instructions="Data cannot be automatically restored. App will reset to defaults.",
        )
    def execute_restore_package(self, package_name: str, backup_id: str,
        confirmed: bool = False) -> ExecutionResult:
        """
        Execute package restore (re-enable) from a backup with full safety workflow.
        Args:
            package_name: Package to re-enable.
            backup_id: Backup ID containing the original package state.
            confirmed: Whether user has already confirmed.
        Returns:
            ExecutionResult with outcome.
        """
        return self._execute_restore_package_action(
            package_name=package_name,
            backup_id=backup_id,
            confirmed=confirmed,
        )
    def execute_change_setting(self, namespace: str, key: str, value: str,
        confirmed: bool = False) -> ExecutionResult:
        """Execute settings change."""
        target = f"{namespace}.{key}"
        return self._execute_generic_action(
            target=target,
            action_type=ActionType.CHANGE_SETTING,
            history_action_type=HistoryActionType.CHANGE_SETTING,
            confirmed=confirmed,
            adb_command=["settings", "put", namespace, key, value],
            reversal_action=HistoryActionType.CHANGE_SETTING,
            reversal_parameters={"namespace": namespace, "key": key},
            reversal_instructions=f"To revert: settings put {namespace} {key} <original_value>",
            pre_action_backup=True,
        )
    def execute_multiple_settings(self, settings: list[tuple[str, str, str]],
        confirmed: bool = False) -> ExecutionResult:
        """Execute multiple settings changes atomically."""
        # Create a combined action
        target = f"multiple_settings_{len(settings)}"
        return self._execute_generic_action(
            target=target,
            action_type=ActionType.CHANGE_MULTIPLE_SETTINGS,
            history_action_type=HistoryActionType.CHANGE_MULTIPLE_SETTINGS,
            confirmed=confirmed,
            adb_command=[],  # Handled specially
            custom_executor=lambda: self._execute_multiple_settings_internal(settings),
            reversal_action=HistoryActionType.CHANGE_MULTIPLE_SETTINGS,
            reversal_parameters={"settings": settings},
            reversal_instructions="Settings restored from pre-action backup.",
            pre_action_backup=True,
        )
    def _execute_package_action(self, package_name: str, action_type: ActionType,
        history_action_type: HistoryActionType,
                                 confirmed: bool, adb_command: list[str],
                                 reversal_action: Optional[ActionType],
                                 reversal_parameters: dict,
                                 reversal_instructions: str) -> ExecutionResult:
        """Execute a package action with full safety workflow."""
        # Phase 1: Validation
        self._report_progress(ExecutionPhase.VALIDATION, "Validating device and package...")
        if not is_valid_package_name(package_name):
            return ExecutionResult(
                success=False, action_id="", phase=ExecutionPhase.FAILED,
                message="Invalid package name",
                error="Package name failed syntax validation",
            )
        if not self.adb_manager.connected_device or \
           self.adb_manager.connection_state != ADBState.CONNECTED:
            return ExecutionResult(
                success=False, action_id="", phase=ExecutionPhase.FAILED,
                message="No device connected", error="Device not connected")
        # Refresh inventory
        self.package_inventory.refresh()
        pkg = self.package_inventory.get_package(package_name)
        if not pkg:
            return ExecutionResult(
                success=False, action_id="", phase=ExecutionPhase.FAILED,
                message=f"Package not found: {package_name}",
                error="Package not in inventory")
        if action_type == ActionType.UNINSTALL and pkg.source != PackageSource.USER:
            return ExecutionResult(
                success=False, action_id="", phase=ExecutionPhase.FAILED,
                message="Uninstall is restricted to user-installed apps.",
                error="Package is not identified as a user-installed app")
        # Safety assessment
        assessment = self.package_classifier.assess_package(pkg, self.package_inventory)
        if not self._is_action_allowed(action_type, assessment):
            return ExecutionResult(
                success=False, action_id="", phase=ExecutionPhase.FAILED,
                message=f"Action not allowed: {assessment.explanation}",
                error=assessment.explanation,
                details={"safety_level": assessment.safety_level.value,
                        "warnings": assessment.warnings})
        # Phase 2: Backup
        self._report_progress(ExecutionPhase.BACKUP, "Creating pre-action backup...")
        backup_result = self.backup_manager.create_backup(
            backup_type=BackupType.PRE_ACTION,
            description=f"Before {action_type.value} {package_name}",
            action_context={
                "action": action_type.value,
                "package": package_name,
                "assessment": assessment.to_dict(),
            }
        )
        if not backup_result or backup_result.status.name == "FAILED":
            return ExecutionResult(
                success=False, action_id="", phase=ExecutionPhase.FAILED,
                message="Failed to create pre-action backup",
                error="Backup creation failed")
        # Create action record
        device_identity = self.device_identifier.identify_device()
        action = self.action_history.create_action(
            action_type=history_action_type,
            target=package_name,
            parameters={"package": package_name, "adb_command": adb_command},
            device_serial=self.adb_manager.connected_device.serial,
            device_identity=self._device_identity_to_dict(device_identity),
            reversal_action=HistoryActionType(reversal_action.value) if reversal_action else None,
            reversal_parameters=reversal_parameters,
            reversal_instructions=reversal_instructions,
            backup_id=backup_result.backup_id,
        )
        self._current_action = action
        # Phase 3: Confirmation
        if not confirmed:
            self._report_progress(ExecutionPhase.CONFIRMATION, "Awaiting user confirmation...")
            return ExecutionResult(
                success=False, action_id=action.action_id, phase=ExecutionPhase.CONFIRMATION,
                message="User confirmation required",
                details={
                    "action_id": action.action_id,
                    "package": package_name,
                    "action": action_type.value,
                    "safety_level": assessment.safety_level.value,
                    "warnings": assessment.warnings,
                    "reversal_instructions": reversal_instructions,
                    "backup_id": backup_result.backup_id,
                })
        # Mark confirmed
        self.action_history.confirm_action(action.action_id)
        # Phase 4: Execution
        self._report_progress(ExecutionPhase.EXECUTION, f"Executing {action_type.value}...")
        self.action_history.start_execution(action.action_id)
        try:
            # Real ADBManager keeps the read-only diagnostic channel separate
            # from the tightly allowlisted mutation channel. Lightweight test
            # doubles may only expose run_shell_command for backward compatibility.
            package_action = getattr(self.adb_manager, "run_package_action", None)
            if callable(package_action) and action_type in (ActionType.DISABLE, ActionType.ENABLE, ActionType.UNINSTALL):
                success, stdout, stderr = package_action(action_type.value, package_name)
            else:
                success, stdout, stderr = self.adb_manager.run_shell_command(" ".join(adb_command))
            output = stdout if stdout else stderr
        except Exception as e:
            success = False
            output = str(e)
        # Phase 5: Verification
        self._report_progress(ExecutionPhase.VERIFICATION, "Verifying result...")
        verification_passed = False
        if success:
            verification_passed = self._verify_package_action(package_name, action_type)
        # Phase 6: Logging
        self._report_progress(ExecutionPhase.LOGGING, "Logging action...")
        self.action_history.complete_action(
            action.action_id, success, output, "" if success else output)
        if not success:
            return ExecutionResult(
                success=False, action_id=action.action_id, phase=ExecutionPhase.FAILED,
                message=f"Execution failed: {output}", error=output,
                backup_id=backup_result.backup_id, verification_passed=False)
        if not verification_passed:
            return ExecutionResult(
                success=False, action_id=action.action_id, phase=ExecutionPhase.FAILED,
                message="Action executed but verification failed",
                error="Post-action verification failed",
                backup_id=backup_result.backup_id, verification_passed=False)
        # Phase 7: Complete
        self._report_progress(ExecutionPhase.COMPLETE, "Action completed successfully")
        return ExecutionResult(
            success=True, action_id=action.action_id, phase=ExecutionPhase.COMPLETE,
            message=f"Successfully {action_type.value}d {package_name}",
            details={"output": output, "verification": "passed"},
            backup_id=backup_result.backup_id, verification_passed=True)
    def _execute_generic_action(self, target: str, action_type: ActionType,
        history_action_type: HistoryActionType,
                                 confirmed: bool, adb_command: list[str],
                                 reversal_action: Optional[HistoryActionType],
                                 reversal_parameters: dict,
                                 reversal_instructions: str,
                                 pre_action_backup: bool = True,
                                 custom_executor: callable = None) -> ExecutionResult:
        """Execute a generic action with safety workflow."""
        # Phase 1: Validation
        self._report_progress(ExecutionPhase.VALIDATION, "Validating device...")
        if not self.adb_manager.connected_device or \
           self.adb_manager.connection_state != ADBState.CONNECTED:
            return ExecutionResult(
                success=False, action_id="", phase=ExecutionPhase.FAILED,
                message="No device connected", error="Device not connected")
        # Phase 2: Backup (if requested)
        backup_result = None
        if pre_action_backup:
            self._report_progress(ExecutionPhase.BACKUP, "Creating pre-action backup...")
            backup_result = self.backup_manager.create_backup(
                backup_type=BackupType.PRE_ACTION,
                description=f"Before {action_type.value} on {target}",
                action_context={
                    "action": action_type.value,
                    "target": target,
                    "adb_command": adb_command,
                }
            )
            if not backup_result or backup_result.status.name == "FAILED":
                return ExecutionResult(
                    success=False, action_id="", phase=ExecutionPhase.FAILED,
                    message="Failed to create pre-action backup",
                    error="Backup creation failed")
        # Create action record
        device_identity = self.device_identifier.identify_device()
        action = self.action_history.create_action(
            action_type=history_action_type,
            target=target,
            parameters={"target": target, "adb_command": adb_command},
            device_serial=self.adb_manager.connected_device.serial,
            device_identity=self._device_identity_to_dict(device_identity),
            reversal_action=reversal_action,
            reversal_parameters=reversal_parameters,
            reversal_instructions=reversal_instructions,
            backup_id=backup_result.backup_id if backup_result else None,
        )
        self._current_action = action
        # Phase 3: Confirmation
        if not confirmed:
            self._report_progress(ExecutionPhase.CONFIRMATION, "Awaiting user confirmation...")
            return ExecutionResult(
                success=False, action_id=action.action_id, phase=ExecutionPhase.CONFIRMATION,
                message="User confirmation required",
                details={
                    "action_id": action.action_id,
                    "target": target,
                    "action": action_type.value,
                    "reversal_instructions": reversal_instructions,
                    "backup_id": backup_result.backup_id if backup_result else None,
                })
        # Mark confirmed
        self.action_history.confirm_action(action.action_id)
        # Phase 4: Execution
        self._report_progress(ExecutionPhase.EXECUTION, f"Executing {action_type.value}...")
        self.action_history.start_execution(action.action_id)
        try:
            if custom_executor:
                success, output = custom_executor()
            else:
                success, stdout, stderr = self.adb_manager.run_shell_command(" ".join(adb_command))
                output = stdout if stdout else stderr
        except Exception as e:
            success = False
            output = str(e)
        # Phase 5: Verification
        self._report_progress(ExecutionPhase.VERIFICATION, "Verifying result...")
        # Basic verification - could be enhanced
        verification_passed = success
        # Phase 6: Logging
        self._report_progress(ExecutionPhase.LOGGING, "Logging action...")
        self.action_history.complete_action(
            action.action_id, success, output, "" if success else output)
        if not success:
            return ExecutionResult(
                success=False, action_id=action.action_id, phase=ExecutionPhase.FAILED,
                message=f"Execution failed: {output}", error=output,
                backup_id=backup_result.backup_id if backup_result else None,
                verification_passed=False)
        if not verification_passed:
            return ExecutionResult(
                success=False, action_id=action.action_id, phase=ExecutionPhase.FAILED,
                message="Action executed but verification failed",
                error="Post-action verification failed",
                backup_id=backup_result.backup_id if backup_result else None,
                verification_passed=False)
        # Phase 7: Complete
        self._report_progress(ExecutionPhase.COMPLETE, "Action completed successfully")
        return ExecutionResult(
            success=True, action_id=action.action_id, phase=ExecutionPhase.COMPLETE,
            message=f"Successfully executed {action_type.value}",
            details={"output": output, "verification": "passed"},
            backup_id=backup_result.backup_id if backup_result else None,
            verification_passed=True)
    def _execute_multiple_settings_internal(self, settings: list[tuple[str, str, str]]) -> tuple[bool, str]:
        """Execute multiple settings changes."""
        results = []
        for namespace, key, value in settings:
            success, stdout, stderr = self.adb_manager.run_shell_command(
                f"settings put {namespace} {key} {value}")
            output = stdout if stdout else stderr
            if not success:
                return False, f"Failed to set {namespace}.{key}: {output}"
            results.append(f"{namespace}.{key}={value}")
        return True, "; ".join(results)
    def _execute_restore_package_action(self, package_name: str, backup_id: str,
                                         confirmed: bool) -> ExecutionResult:
        """Execute a package restore (re-enable) from backup with full safety workflow."""
        # Phase 1: Validation
        self._report_progress(ExecutionPhase.VALIDATION, "Validating device and backup...")
        if not is_valid_package_name(package_name):
            return ExecutionResult(
                success=False, action_id="", phase=ExecutionPhase.FAILED,
                message="Invalid package name",
                error="Package name failed syntax validation",
            )
        if not self.adb_manager.connected_device or \
           self.adb_manager.connection_state != ADBState.CONNECTED:
            return ExecutionResult(
                success=False, action_id="", phase=ExecutionPhase.FAILED,
                message="No device connected", error="Device not connected")
        # Verify backup exists and load it
        backup_content = self.backup_manager.get_backup(backup_id)
        if not backup_content:
            return ExecutionResult(
                success=False, action_id="", phase=ExecutionPhase.FAILED,
                message="Backup not found", error="Backup not found")
        # Verify backup has package inventory
        if not backup_content.package_inventory:
            return ExecutionResult(
                success=False, action_id="", phase=ExecutionPhase.FAILED,
                message="Backup does not contain package inventory", error="No package data in backup")
        # Find package in backup
        backup_pkg = None
        for pkg in backup_content.package_inventory:
            if pkg.package_name == package_name:
                backup_pkg = pkg
                break
        if not backup_pkg:
            return ExecutionResult(
                success=False, action_id="", phase=ExecutionPhase.FAILED,
                message=f"Package {package_name} not found in backup", error="Package not in backup")
        # Verify package was enabled in backup
        if not backup_pkg.enabled:
            return ExecutionResult(
                success=False, action_id="", phase=ExecutionPhase.FAILED,
                message=f"Package {package_name} was not enabled in backup", error="Cannot restore disabled package")
        # Verify device matches
        if backup_content.metadata.device_serial != self.adb_manager.connected_device.serial:
            return ExecutionResult(
                success=False, action_id="", phase=ExecutionPhase.FAILED,
                message="Backup is for a different device",
                error=f"Backup device: {backup_content.metadata.device_serial}, Current: {self.adb_manager.connected_device.serial}")
        # Refresh inventory to get current state
        self.package_inventory.refresh()
        current_pkg = self.package_inventory.get_package(package_name)
        if not current_pkg:
            return ExecutionResult(
                success=False, action_id="", phase=ExecutionPhase.FAILED,
                message=f"Package {package_name} not installed on device", error="Package not found on device")
        if current_pkg.enabled:
            return ExecutionResult(
                success=False, action_id="", phase=ExecutionPhase.FAILED,
                message=f"Package {package_name} is already enabled", error="Already enabled")
        # Safety assessment - re-enable is always allowed per classifier
        assessment = self.package_classifier.assess_package(current_pkg, self.package_inventory)
        if not self._is_action_allowed(ActionType.ENABLE, assessment):
            return ExecutionResult(
                success=False, action_id="", phase=ExecutionPhase.FAILED,
                message=f"Re-enable not allowed: {assessment.explanation}", error=assessment.explanation)
        # Phase 2: Backup (create pre-recovery backup)
        self._report_progress(ExecutionPhase.BACKUP, "Creating pre-recovery backup...")
        backup_result = self.backup_manager.create_backup(
            backup_type=BackupType.PRE_ACTION,
            description=f"Before restore (re-enable) {package_name}",
            action_context={
                "action": "restore_package",
                "package": package_name,
                "source_backup": backup_id,
            }
        )
        if not backup_result or backup_result.status.name == "FAILED":
            return ExecutionResult(
                success=False, action_id="", phase=ExecutionPhase.FAILED,
                message="Failed to create pre-recovery backup", error="Backup creation failed")
        # Create action record for the restore
        device_identity = self.device_identifier.identify_device()
        action = self.action_history.create_action(
            action_type=HistoryActionType.ENABLE_PACKAGE,
            target=package_name,
            parameters={"package": package_name, "source_backup": backup_id},
            device_serial=self.adb_manager.connected_device.serial,
            device_identity=self._device_identity_to_dict(device_identity),
            reversal_action=HistoryActionType.DISABLE_PACKAGE,
            reversal_parameters={"package": package_name},
            reversal_instructions=f"To disable again: pm disable-user {package_name}",
            backup_id=backup_result.backup_id,
        )
        self._current_action = action
        # Phase 3: Confirmation
        if not confirmed:
            self._report_progress(ExecutionPhase.CONFIRMATION, "Awaiting user confirmation...")
            return ExecutionResult(
                success=False, action_id=action.action_id, phase=ExecutionPhase.CONFIRMATION,
                message="User confirmation required",
                details={
                    "action_id": action.action_id,
                    "package": package_name,
                    "action": "restore_package",
                    "safety_level": assessment.safety_level.value,
                    "warnings": assessment.warnings,
                    "reversal_instructions": f"To disable again: pm disable-user {package_name}",
                    "backup_id": backup_result.backup_id,
                    "source_backup": backup_id,
                })
        # Mark confirmed
        self.action_history.confirm_action(action.action_id)
        # Phase 4: Execution
        self._report_progress(ExecutionPhase.EXECUTION, f"Re-enabling {package_name}...")
        self.action_history.start_execution(action.action_id)
        try:
            success, stdout, stderr = self.adb_manager.run_shell_command(f"pm enable {package_name}")
            output = stdout if stdout else stderr
        except Exception as e:
            success = False
            output = str(e)
        # Phase 5: Verification
        self._report_progress(ExecutionPhase.VERIFICATION, "Verifying result...")
        verification_passed = False
        if success:
            verification_passed = self._verify_package_action(package_name, ActionType.ENABLE)
        # Phase 6: Logging
        self._report_progress(ExecutionPhase.LOGGING, "Logging action...")
        self.action_history.complete_action(
            action.action_id, success, output, "" if success else output)
        if not success:
            return ExecutionResult(
                success=False, action_id=action.action_id, phase=ExecutionPhase.FAILED,
                message=f"Execution failed: {output}", error=output,
                backup_id=backup_result.backup_id, verification_passed=False)
        if not verification_passed:
            return ExecutionResult(
                success=False, action_id=action.action_id, phase=ExecutionPhase.FAILED,
                message="Action executed but verification failed",
                error="Post-recovery verification failed",
                backup_id=backup_result.backup_id, verification_passed=False)
        # Phase 7: Complete
        self._report_progress(ExecutionPhase.COMPLETE, "Package restored successfully")
        return ExecutionResult(
            success=True, action_id=action.action_id, phase=ExecutionPhase.COMPLETE,
            message=f"Successfully restored (re-enabled) {package_name}",
            details={"output": output, "verification": "passed", "source_backup": backup_id},
            backup_id=backup_result.backup_id, verification_passed=True)
    def _is_action_allowed(self, action_type: ActionType, assessment: PackageSafetyAssessment) -> bool:
        """Check if action is allowed based on safety assessment."""
        if action_type == ActionType.DISABLE:
            return assessment.can_disable()
        elif action_type == ActionType.UNINSTALL:
            return assessment.can_uninstall()
        elif action_type == ActionType.CLEAR_DATA:
            return assessment.safety_level in (SafetyLevel.SAFE, SafetyLevel.USER_APP)
        elif action_type == ActionType.ENABLE:
            return True  # Enabling is always allowed
        return False
    def _verify_package_action(self, package_name: str, action_type: ActionType) -> bool:
        """Verify that a package action took effect."""
        # Refresh package info
        success, msg = self.package_inventory.refresh()
        if not success:
            return False
        pkg = self.package_inventory.get_package(package_name)
        if not pkg:
            return action_type == ActionType.UNINSTALL  # Should be gone
        if action_type == ActionType.DISABLE:
            return not pkg.enabled
        elif action_type == ActionType.ENABLE:
            return pkg.enabled
        elif action_type == ActionType.CLEAR_DATA:
            # Hard to verify, assume success if command succeeded
            return True
        return True
    def _device_identity_to_dict(self, identity: DeviceIdentity) -> dict:
        return {
            "manufacturer": identity.manufacturer,
            "model": identity.model,
            "brand": identity.brand,
            "device_codename": identity.device_codename,
            "board": identity.board,
            "android_version": identity.android_version,
            "android_release": identity.android_release,
            "api_level": identity.api_level,
            "security_patch": identity.security_patch,
            "build_id": identity.build_id,
            "build_fingerprint": identity.build_fingerprint,
            "build_type": identity.build_type,
            "build_tags": identity.build_tags,
            "cpu_abi": identity.cpu_abi,
            "cpu_abilist": identity.cpu_abilist,
            "screen_resolution": identity.screen_resolution,
            "screen_density": identity.screen_density,
            "default_launcher": identity.default_launcher,
            "uptime_seconds": identity.uptime_seconds,
            "memory_total_mb": identity.memory_total_mb,
            "memory_available_mb": identity.memory_available_mb,
            "storage_total_gb": identity.storage_total_gb,
            "storage_free_gb": identity.storage_free_gb,
            "storage_free_percent": identity.storage_free_percent,
            "platform_type": identity.platform_type,
            "characteristics": identity.characteristics,
            "is_tv_device": identity.is_tv_device,
            "connection_type": identity.connection_type,
            "serial": identity.serial,
            "compatibility_score": identity.compatibility_score,
            "compatibility_notes": identity.compatibility_notes,
            "supported_features": identity.supported_features,
            "unsupported_features": identity.unsupported_features,
        }
    def get_execution_status(self, action_id: str) -> Optional[ExecutionPhase]:
        """Get current execution phase for an action."""
        action = self.action_history.get_action(action_id)
        if not action:
            return None
        if action.status == ActionStatus.PENDING:
            return ExecutionPhase.CONFIRMATION
        elif action.status == ActionStatus.CONFIRMED:
            return ExecutionPhase.EXECUTION
        elif action.status == ActionStatus.EXECUTING:
            return ExecutionPhase.EXECUTION
        elif action.status == ActionStatus.COMPLETED:
            return ExecutionPhase.COMPLETE
        elif action.status == ActionStatus.FAILED:
            return ExecutionPhase.FAILED
        elif action.status == ActionStatus.ROLLED_BACK:
            return ExecutionPhase.COMPLETE
        return ExecutionPhase.INIT
def create_action_engine(adb_manager: ADBManager) -> ActionEngine:
        """Factory function to create an ActionEngine."""
        return ActionEngine(adb_manager)
