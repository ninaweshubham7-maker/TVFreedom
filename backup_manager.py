"""
Backup Manager - Local backup and recovery for TV Freedom.

This module provides a genuine local backup system that captures
device state before any modifications, enabling reliable recovery.
"""

from dataclasses import dataclass, field, asdict
from typing import Optional
from pathlib import Path
import json
import time
import shutil
from datetime import datetime
from enum import Enum

from adb_manager import ADBManager, ADBState
from device_identification import DeviceIdentifier, DeviceIdentity
from diagnostics import DiagnosticsEngine, DiagnosticResult
from package_inventory import PackageInventory, PackageInfo
from package_classifier import PackageClassifier, PackageSafetyAssessment


class BackupType(Enum):
    """Type of backup."""
    FULL = "full"                 # Complete device state
    PRE_ACTION = "pre_action"     # Before a specific action
    MANUAL = "manual"             # User-initiated
    SCHEDULED = "scheduled"       # Automatic scheduled backup


class BackupStatus(Enum):
    """Backup status."""
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    INCOMPLETE = "incomplete"     # Some sections failed
    RESTORED = "restored"         # Has been used for restore


@dataclass
class BackupMetadata:
    """Metadata about a backup."""
    backup_id: str
    timestamp: float
    backup_type: BackupType
    status: BackupStatus
    device_serial: str
    device_identity: dict  # Serialized DeviceIdentity
    sections: list[str]  # Which sections were backed up
    failed_sections: list[str] = field(default_factory=list)
    size_bytes: int = 0
    description: str = ""
    action_context: Optional[dict] = None  # For pre-action backups
    
    def to_dict(self) -> dict:
        return {
            "backup_id": self.backup_id,
            "timestamp": self.timestamp,
            "timestamp_iso": datetime.fromtimestamp(self.timestamp).isoformat(),
            "backup_type": self.backup_type.value,
            "status": self.status.value,
            "device_serial": self.device_serial,
            "device_identity": self.device_identity,
            "sections": self.sections,
            "failed_sections": self.failed_sections,
            "size_bytes": self.size_bytes,
            "description": self.description,
            "action_context": self.action_context,
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> 'BackupMetadata':
        return cls(
            backup_id=data["backup_id"],
            timestamp=data["timestamp"],
            backup_type=BackupType(data["backup_type"]),
            status=BackupStatus(data["status"]),
            device_serial=data["device_serial"],
            device_identity=data["device_identity"],
            sections=data["sections"],
            failed_sections=data.get("failed_sections", []),
            size_bytes=data.get("size_bytes", 0),
            description=data.get("description", ""),
            action_context=data.get("action_context"),
        )


@dataclass
class BackupContent:
    """Full backup content."""
    metadata: BackupMetadata
    device_identity: Optional[DeviceIdentity] = None
    diagnostic_result: Optional[DiagnosticResult] = None
    package_inventory: list[PackageInfo] = field(default_factory=list)
    package_assessments: dict[str, dict] = field(default_factory=dict)
    settings_snapshot: dict = field(default_factory=dict)
    
    def save(self, backup_dir: Path) -> bool:
        """Save backup to directory."""
        try:
            backup_dir.mkdir(parents=True, exist_ok=True)
            
            # Save metadata
            with open(backup_dir / "metadata.json", 'w', encoding='utf-8') as f:
                json.dump(self.metadata.to_dict(), f, indent=2)
            
            # Save device identity
            if self.device_identity:
                with open(backup_dir / "device_identity.json", 'w', encoding='utf-8') as f:
                    json.dump(self._device_identity_to_dict(self.device_identity), f, indent=2)
            
            # Save diagnostic result
            if self.diagnostic_result:
                with open(backup_dir / "diagnostics.json", 'w', encoding='utf-8') as f:
                    json.dump(self.diagnostic_result.to_dict(), f, indent=2)
            
            # Save package inventory
            if self.package_inventory:
                with open(backup_dir / "packages.json", 'w', encoding='utf-8') as f:
                    json.dump([p.to_dict() for p in self.package_inventory], f, indent=2)
            
            # Save package assessments
            if self.package_assessments:
                with open(backup_dir / "assessments.json", 'w', encoding='utf-8') as f:
                    json.dump(self.package_assessments, f, indent=2)
            
            # Save settings snapshot
            if self.settings_snapshot:
                with open(backup_dir / "settings.json", 'w', encoding='utf-8') as f:
                    json.dump(self.settings_snapshot, f, indent=2)
            
            return True
        except Exception as e:
            print(f"Backup save failed: {e}")
            return False
    
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
    
    @classmethod
    def load(cls, backup_dir: Path) -> Optional['BackupContent']:
        """Load backup from directory."""
        try:
            # Load metadata
            with open(backup_dir / "metadata.json", 'r', encoding='utf-8') as f:
                meta_data = json.load(f)
            metadata = BackupMetadata.from_dict(meta_data)
            
            content = cls(metadata=metadata)
            
            # Load device identity
            identity_path = backup_dir / "device_identity.json"
            if identity_path.exists():
                with open(identity_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                content.device_identity = cls._dict_to_device_identity(data)
            
            # Load diagnostic result
            diag_path = backup_dir / "diagnostics.json"
            if diag_path.exists():
                with open(diag_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                content.diagnostic_result = DiagnosticResult(
                    timestamp=datetime.fromisoformat(data["timestamp"]),
                    success=data["success"],
                    error_message=data.get("error_message", ""),
                    collection_time_ms=data.get("collection_time_ms", 0),
                    sections=data.get("sections", {}),
                )
            
            # Load package inventory
            pkg_path = backup_dir / "packages.json"
            if pkg_path.exists():
                with open(pkg_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                content.package_inventory = [cls._dict_to_package_info(p) for p in data]
            
            # Load assessments
            assess_path = backup_dir / "assessments.json"
            if assess_path.exists():
                with open(assess_path, 'r', encoding='utf-8') as f:
                    content.package_assessments = json.load(f)
            
            # Load settings
            settings_path = backup_dir / "settings.json"
            if settings_path.exists():
                with open(settings_path, 'r', encoding='utf-8') as f:
                    content.settings_snapshot = json.load(f)
            
            return content
        except Exception as e:
            print(f"Backup load failed: {e}")
            return None
    
    @staticmethod
    def _dict_to_device_identity(data: dict) -> DeviceIdentity:
        return DeviceIdentity(
            manufacturer=data.get("manufacturer", "Unknown"),
            model=data.get("model", "Unknown"),
            brand=data.get("brand", "Unknown"),
            device_codename=data.get("device_codename", "Unknown"),
            board=data.get("board", "Unknown"),
            android_version=data.get("android_version", "Unknown"),
            android_release=data.get("android_release", "Unknown"),
            api_level=data.get("api_level", 0),
            security_patch=data.get("security_patch", "Unknown"),
            build_id=data.get("build_id", "Unknown"),
            build_fingerprint=data.get("build_fingerprint", "Unknown"),
            build_type=data.get("build_type", "Unknown"),
            build_tags=data.get("build_tags", "Unknown"),
            cpu_abi=data.get("cpu_abi", "Unknown"),
            cpu_abilist=data.get("cpu_abilist", "Unknown"),
            screen_resolution=data.get("screen_resolution", "Unknown"),
            screen_density=data.get("screen_density", 0),
            default_launcher=data.get("default_launcher", "Unknown"),
            uptime_seconds=data.get("uptime_seconds", 0),
            memory_total_mb=data.get("memory_total_mb", 0),
            memory_available_mb=data.get("memory_available_mb", 0),
            storage_total_gb=data.get("storage_total_gb", 0.0),
            storage_free_gb=data.get("storage_free_gb", 0.0),
            storage_free_percent=data.get("storage_free_percent", 0.0),
            platform_type=data.get("platform_type", "unknown"),
            characteristics=data.get("characteristics", "Unknown"),
            is_tv_device=data.get("is_tv_device", False),
            connection_type=data.get("connection_type", "unknown"),
            serial=data.get("serial", "Unknown"),
            compatibility_score=data.get("compatibility_score", 0),
            compatibility_notes=data.get("compatibility_notes", []),
            supported_features=data.get("supported_features", []),
            unsupported_features=data.get("unsupported_features", []),
        )
    
    @staticmethod
    def _dict_to_package_info(data: dict) -> PackageInfo:
        return PackageInfo(
            package_name=data.get("package_name", "Unknown"),
            display_name=data.get("display_name", "Unknown"),
            version_name=data.get("version_name", "Unknown"),
            version_code=data.get("version_code", 0),
            category=data.get("category", "unknown"),
            source=data.get("source", "unknown"),
            enabled=data.get("enabled", True),
            installer_package=data.get("installer_package", "Unknown"),
            install_location=data.get("install_location", "Unknown"),
            permissions=data.get("permissions", []),
            activities=data.get("activities", []),
            services=data.get("services", []),
            receivers=data.get("receivers", []),
            providers=data.get("providers", []),
            is_launcher=data.get("is_launcher", False),
            is_system_ui=data.get("is_system_ui", False),
            is_settings=data.get("is_settings", False),
            is_input_method=data.get("is_input_method", False),
            is_accessibility=data.get("is_accessibility", False),
            is_device_admin=data.get("is_device_admin", False),
            first_install_time=data.get("first_install_time", 0),
            last_update_time=data.get("last_update_time", 0),
            data_dir=data.get("data_dir", "Unknown"),
            apk_path=data.get("apk_path", "Unknown"),
            classification_confidence=data.get("classification_confidence", 0.0),
            classification_reason=data.get("classification_reason", ""),
        )


class BackupManager:
    """Manages device backups and recovery."""
    
    def __init__(self, adb_manager: ADBManager, backup_root: Optional[Path] = None):
        self.adb_manager = adb_manager
        self.device_identifier = DeviceIdentifier(adb_manager)
        self.diagnostics_engine = DiagnosticsEngine(adb_manager)
        self.package_inventory = PackageInventory(adb_manager)
        self.package_classifier = PackageClassifier()
        
        # Backup storage location
        if backup_root is None:
            backup_root = Path.home() / "TVFreedom_Backups"
        self.backup_root = Path(backup_root)
        self.backup_root.mkdir(parents=True, exist_ok=True)
    
    def create_backup(self, backup_type: BackupType = BackupType.MANUAL,
                      description: str = "",
                      action_context: Optional[dict] = None) -> Optional[BackupMetadata]:
        """
        Create a complete device backup.
        
        Args:
            backup_type: Type of backup.
            description: Human-readable description.
            action_context: Context about action (for pre-action backups).
            
        Returns:
            BackupMetadata if successful, None otherwise.
        """
        if not self.adb_manager.connected_device or \
           self.adb_manager.connection_state != ADBState.CONNECTED:
            return None
        
        # Generate backup ID
        timestamp = time.time()
        backup_id = f"backup_{int(timestamp)}_{self.adb_manager.connected_device.serial[:8]}"
        backup_dir = self.backup_root / backup_id
        
        # Create metadata
        metadata = BackupMetadata(
            backup_id=backup_id,
            timestamp=timestamp,
            backup_type=backup_type,
            status=BackupStatus.IN_PROGRESS,
            device_serial=self.adb_manager.connected_device.serial,
            device_identity={},  # Will fill in
            sections=[],
            failed_sections=[],
            description=description,
            action_context=action_context,
        )
        
        content = BackupContent(metadata=metadata)
        
        try:
            # 1. Device identity
            try:
                content.device_identity = self.device_identifier.identify_device()
                metadata.device_identity = content._device_identity_to_dict(content.device_identity)
                metadata.sections.append("device_identity")
            except Exception as e:
                metadata.failed_sections.append(f"device_identity: {str(e)}")
            
            # 2. Full diagnostics
            try:
                content.diagnostic_result = self.diagnostics_engine.run_full_diagnostic()
                metadata.sections.append("diagnostics")
            except Exception as e:
                metadata.failed_sections.append(f"diagnostics: {str(e)}")
            
            # 3. Package inventory
            try:
                success, msg = self.package_inventory.refresh()
                if success:
                    content.package_inventory = self.package_inventory.get_all_packages()
                    metadata.sections.append("packages")
                else:
                    metadata.failed_sections.append(f"packages: {msg}")
            except Exception as e:
                metadata.failed_sections.append(f"packages: {str(e)}")
            
            # 4. Package safety assessments
            try:
                content.package_assessments = {}
                for pkg in content.package_inventory:
                    assessment = self.package_classifier.assess_package(pkg, self.package_inventory)
                    content.package_assessments[pkg.package_name] = assessment.to_dict()
                metadata.sections.append("assessments")
            except Exception as e:
                metadata.failed_sections.append(f"assessments: {str(e)}")
            
            # 5. Settings snapshot
            try:
                content.settings_snapshot = self._capture_settings()
                metadata.sections.append("settings")
            except Exception as e:
                metadata.failed_sections.append(f"settings: {str(e)}")
            
            # Update metadata
            metadata.status = BackupStatus.COMPLETED if not metadata.failed_sections else BackupStatus.INCOMPLETE
            
            # Calculate size
            if content.save(backup_dir):
                metadata.size_bytes = self._get_dir_size(backup_dir)
                # Update metadata file with final size
                content.metadata = metadata
                content.save(backup_dir)
                return metadata
            else:
                metadata.status = BackupStatus.FAILED
                return metadata
                
        except Exception as e:
            metadata.status = BackupStatus.FAILED
            metadata.failed_sections.append(f"general: {str(e)}")
            return metadata
    
    def _capture_settings(self) -> dict:
        """Capture important system settings."""
        settings = {}
        
        # Global settings
        setting_keys = [
            "install_non_market_apps",
            "adb_enabled",
            "development_settings_enabled",
            "wifi_on",
            "bluetooth_on",
            "location_mode",
            "screen_brightness",
            "screen_off_timeout",
            "sleep_timeout",
            "font_scale",
            "animator_duration_scale",
            "transition_animation_scale",
            "window_animation_scale",
        ]
        
        for key in setting_keys:
            success, output = self._run_safe(f"settings get global {key}")
            if success:
                settings[f"global.{key}"] = output
            else:
                settings[f"global.{key}"] = "unavailable"
        
        # Secure settings
        secure_keys = [
            "location_providers_allowed",
            "install_non_market_apps",
            "device_provisioned",
            "user_setup_complete",
        ]
        
        for key in secure_keys:
            success, output = self._run_safe(f"settings get secure {key}")
            if success:
                settings[f"secure.{key}"] = output
            else:
                settings[f"secure.{key}"] = "unavailable"
        
        # System settings
        system_keys = [
            "screen_brightness_mode",
            "screen_off_timeout",
            "volume_music",
            "volume_ring",
            "volume_alarm",
            "volume_notification",
            "volume_voice",
        ]
        
        for key in system_keys:
            success, output = self._run_safe(f"settings get system {key}")
            if success:
                settings[f"system.{key}"] = output
            else:
                settings[f"system.{key}"] = "unavailable"
        
        return settings
    
    def _run_safe(self, command: str) -> tuple[bool, str]:
        """Run a safe ADB command."""
        success, stdout, stderr = self.adb_manager.run_shell_command(command)
        return success, stdout.strip() if stdout else stderr.strip()
    
    def _get_dir_size(self, path: Path) -> int:
        """Get directory size in bytes."""
        total = 0
        for f in path.rglob('*'):
            if f.is_file():
                total += f.stat().st_size
        return total
    
    def list_backups(self) -> list[BackupMetadata]:
        """List all available backups."""
        backups = []
        for backup_dir in sorted(self.backup_root.iterdir(), key=lambda p: p.stat().st_mtime, reverse=True):
            if backup_dir.is_dir():
                meta_path = backup_dir / "metadata.json"
                if meta_path.exists():
                    try:
                        with open(meta_path, 'r', encoding='utf-8') as f:
                            data = json.load(f)
                        backups.append(BackupMetadata.from_dict(data))
                    except Exception:
                        pass
        return backups
    
    def get_backup(self, backup_id: str) -> Optional[BackupContent]:
        """Load a specific backup."""
        backup_dir = self.backup_root / backup_id
        if backup_dir.exists():
            return BackupContent.load(backup_dir)
        return None
    
    def delete_backup(self, backup_id: str) -> bool:
        """Delete a backup."""
        backup_dir = self.backup_root / backup_id
        if backup_dir.exists():
            try:
                shutil.rmtree(backup_dir)
                return True
            except Exception:
                return False
        return False
    
    def restore_settings(self, backup_id: str) -> tuple[bool, str]:
        """
        Restore settings from a backup.
        
        Args:
            backup_id: ID of backup to restore from.
            
        Returns:
            Tuple of (success, message).
        """
        if not self.adb_manager.connected_device or \
           self.adb_manager.connection_state != ADBState.CONNECTED:
            return False, "No device connected"
        
        content = self.get_backup(backup_id)
        if not content:
            return False, "Backup not found"
        
        if not content.settings_snapshot:
            return False, "No settings in backup"
        
        restored = 0
        failed = 0
        
        for key, value in content.settings_snapshot.items():
            if value == "unavailable":
                continue
            
            # Parse namespace
            if key.startswith("global."):
                namespace = "global"
                setting_key = key[7:]
            elif key.startswith("secure."):
                namespace = "secure"
                setting_key = key[7:]
            elif key.startswith("system."):
                namespace = "system"
                setting_key = key[7:]
            else:
                continue
            
            success, _ = self._run_safe(f"settings put {namespace} {setting_key} {value}")
            if success:
                restored += 1
            else:
                failed += 1
        
        return True, f"Restored {restored} settings, {failed} failed"
    
    def get_recovery_info(self, backup_id: str) -> dict:
        """Get information about what can be recovered from a backup."""
        content = self.get_backup(backup_id)
        if not content:
            return {"error": "Backup not found"}
        
        info = {
            "backup_id": content.metadata.backup_id,
            "timestamp": content.metadata.timestamp,
            "device": content.metadata.device_serial,
            "sections_available": content.metadata.sections,
            "sections_failed": content.metadata.failed_sections,
            "can_restore_settings": bool(content.settings_snapshot),
            "package_count": len(content.package_inventory),
            "assessment_count": len(content.package_assessments),
            "has_diagnostics": content.diagnostic_result is not None,
            "has_device_identity": content.device_identity is not None,
            "actions_performed": content.metadata.action_context or {},
        }
        
        # Determine what can be reversed
        if content.metadata.action_context:
            action = content.metadata.action_context
            info["original_action"] = action.get("action", "unknown")
            info["target_package"] = action.get("package", "unknown")
            info["can_reverse"] = True
            info["reverse_instructions"] = self._get_reverse_instructions(action)
        else:
            info["can_reverse"] = False
            info["reverse_instructions"] = "No specific action recorded for this backup."
        
        # Add package recovery candidates
        if content.package_inventory:
            info["package_recovery_candidates"] = self.get_package_recovery_candidates(backup_id)
        
        return info
    
    def _get_reverse_instructions(self, action: dict) -> str:
        """Get reverse instructions for an action."""
        action_type = action.get("action", "")
        package = action.get("package", "")
        
        if action_type == "disable":
            return f"To re-enable: pm enable {package}"
        elif action_type == "uninstall":
            return f"To restore: Re-install from Play Store or restore from backup data."
        elif action_type == "clear_data":
            return f"Data cannot be automatically restored. App will reset to default state."
        elif action_type == "settings_change":
            return "Settings restored from backup snapshot."
        
        return "No specific reverse instructions available."
    
    def export_backup_summary(self, output_path: Path) -> bool:
        """Export summary of all backups to JSON."""
        try:
            backups = self.list_backups()
            data = {
                "export_time": time.time(),
                "backup_count": len(backups),
                "backups": [b.to_dict() for b in backups],
            }
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2)
            return True
        except Exception:
            return False

    def restore_package(self, backup_id: str, package_name: str) -> tuple[bool, str]:
        """
        Restore a specific package from a backup by re-enabling it.
        
        Args:
            backup_id: ID of backup to restore from.
            package_name: Package name to restore.
            
        Returns:
            Tuple of (success, message).
        """
        if not self.adb_manager.connected_device or \
           self.adb_manager.connection_state != ADBState.CONNECTED:
            return False, "No device connected"
        
        content = self.get_backup(backup_id)
        if not content:
            return False, "Backup not found"
        
        # Verify this backup has package data
        if not content.package_inventory:
            return False, "No package inventory in backup"
        
        # Find the package in the backup
        backup_pkg = None
        for pkg in content.package_inventory:
            if pkg.package_name == package_name:
                backup_pkg = pkg
                break
        
        if not backup_pkg:
            return False, f"Package {package_name} not found in backup"
        
        # Check if the package was enabled in the backup (only re-enable if it was enabled before)
        if not backup_pkg.enabled:
            return False, f"Package {package_name} was not enabled in the backup (was already disabled)"
        
        # Verify device matches
        if content.metadata.device_serial != self.adb_manager.connected_device.serial:
            return False, f"Backup is for a different device ({content.metadata.device_serial})"
        
        # Check current package state
        success, msg = self.package_inventory.refresh()
        if not success:
            return False, f"Failed to refresh package inventory: {msg}"
        
        current_pkg = self.package_inventory.get_package(package_name)
        if not current_pkg:
            return False, f"Package {package_name} no longer installed on device"
        
        if current_pkg.enabled:
            return False, f"Package {package_name} is already enabled"
        
        # Verify safety assessment allows re-enabling
        assessment = self.package_classifier.assess_package(current_pkg, self.package_inventory)
        # ENABLE is always allowed per PackageClassifier._is_action_allowed
        
        # Execute re-enable
        package_action = getattr(self.adb_manager, "run_package_action", None)
        if callable(package_action):
            success, stdout, stderr = package_action("enable", package_name)
        else:
            success, stdout, stderr = self.adb_manager.run_shell_command(f"pm enable {package_name}")
        output = stdout if stdout else stderr
        
        if not success:
            return False, f"Failed to re-enable package: {output}"
        
        # Verify the re-enable took effect
        verify_success, verify_msg = self.package_inventory.refresh()
        if not verify_success:
            return False, f"Package re-enabled but verification failed: {verify_msg}"
        
        verified_pkg = self.package_inventory.get_package(package_name)
        if not verified_pkg or not verified_pkg.enabled:
            return False, "Package re-enable command succeeded but package is still disabled"
        
        return True, f"Successfully re-enabled {package_name}"
    
    def get_package_recovery_candidates(self, backup_id: str) -> list[dict]:
        """
        Get list of packages from a backup that can be recovered (were enabled in backup but disabled now).
        
        Args:
            backup_id: ID of backup to check.
            
        Returns:
            List of dicts with package recovery info.
        """
        content = self.get_backup(backup_id)
        if not content:
            return []
        
        if not content.package_inventory:
            return []
        
        # Get current package states
        success, msg = self.package_inventory.refresh()
        if not success:
            return []
        
        current_packages = {p.package_name: p for p in self.package_inventory.get_all_packages()}
        
        candidates = []
        for backup_pkg in content.package_inventory:
            # Only consider packages that were enabled in the backup
            if not backup_pkg.enabled:
                continue
            
            current_pkg = current_packages.get(backup_pkg.package_name)
            if not current_pkg:
                # Package no longer installed
                candidates.append({
                    "package_name": backup_pkg.package_name,
                    "display_name": backup_pkg.display_name,
                    "backup_enabled": True,
                    "current_state": "not_installed",
                    "recoverable": False,
                    "reason": "Package no longer installed on device"
                })
                continue
            
            if current_pkg.enabled:
                # Already enabled, no recovery needed
                candidates.append({
                    "package_name": backup_pkg.package_name,
                    "display_name": backup_pkg.display_name,
                    "backup_enabled": True,
                    "current_state": "enabled",
                    "recoverable": False,
                    "reason": "Package is already enabled"
                })
                continue
            
            # Package was enabled in backup but is now disabled - recoverable
            candidates.append({
                "package_name": backup_pkg.package_name,
                "display_name": backup_pkg.display_name,
                "backup_enabled": True,
                "current_state": "disabled",
                "recoverable": True,
                "reason": "Package was enabled in backup but is now disabled"
            })
        
        return candidates


def create_backup_manager(adb_manager: ADBManager, backup_root: Optional[Path] = None) -> BackupManager:
    """Factory function to create a BackupManager."""
    return BackupManager(adb_manager, backup_root)