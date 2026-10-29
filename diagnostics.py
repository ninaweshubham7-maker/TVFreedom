"""
Diagnostics - Comprehensive diagnostics dashboard for TV Freedom.

This module provides a complete diagnostics dashboard that retrieves
and displays detailed device information using read-only ADB operations.
"""

from dataclasses import dataclass, field
from typing import Optional
from datetime import datetime
from pathlib import Path
import json
import time

from adb_manager import ADBManager, ADBDevice, ADBState
from device_identification import DeviceIdentifier, DeviceIdentity


@dataclass
class DiagnosticResult:
    """Result of a diagnostic run."""
    timestamp: datetime
    success: bool
    device_identity: Optional[DeviceIdentity] = None
    error_message: str = ""
    collection_time_ms: int = 0
    sections: dict = field(default_factory=dict)
    
    def to_dict(self) -> dict:
        """Convert to dictionary for export."""
        result = {
            "timestamp": self.timestamp.isoformat(),
            "success": self.success,
            "error_message": self.error_message,
            "collection_time_ms": self.collection_time_ms,
            "sections": self.sections,
        }
        if self.device_identity:
            result["device_identity"] = {
                "manufacturer": self.device_identity.manufacturer,
                "model": self.device_identity.model,
                "brand": self.device_identity.brand,
                "device_codename": self.device_identity.device_codename,
                "board": self.device_identity.board,
                "android_version": self.device_identity.android_version,
                "android_release": self.device_identity.android_release,
                "api_level": self.device_identity.api_level,
                "security_patch": self.device_identity.security_patch,
                "build_id": self.device_identity.build_id,
                "build_fingerprint": self.device_identity.build_fingerprint,
                "build_type": self.device_identity.build_type,
                "build_tags": self.device_identity.build_tags,
                "cpu_abi": self.device_identity.cpu_abi,
                "cpu_abilist": self.device_identity.cpu_abilist,
                "screen_resolution": self.device_identity.screen_resolution,
                "screen_density": self.device_identity.screen_density,
                "default_launcher": self.device_identity.default_launcher,
                "uptime_seconds": self.device_identity.uptime_seconds,
                "memory_total_mb": self.device_identity.memory_total_mb,
                "memory_available_mb": self.device_identity.memory_available_mb,
                "storage_total_gb": self.device_identity.storage_total_gb,
                "storage_free_gb": self.device_identity.storage_free_gb,
                "storage_free_percent": self.device_identity.storage_free_percent,
                "platform_type": self.device_identity.platform_type,
                "characteristics": self.device_identity.characteristics,
                "is_tv_device": self.device_identity.is_tv_device,
                "connection_type": self.device_identity.connection_type,
                "serial": self.device_identity.serial,
                "compatibility_score": self.device_identity.compatibility_score,
                "compatibility_notes": self.device_identity.compatibility_notes,
                "supported_features": self.device_identity.supported_features,
                "unsupported_features": self.device_identity.unsupported_features,
            }
        return result


class DiagnosticsEngine:
    """Performs comprehensive device diagnostics."""
    
    def __init__(self, adb_manager: ADBManager):
        self.adb_manager = adb_manager
        self.device_identifier = DeviceIdentifier(adb_manager)
        self.last_result: Optional[DiagnosticResult] = None
    
    def run_full_diagnostic(self, redact_serial: bool = False) -> DiagnosticResult:
        """
        Run a complete diagnostic collection.
        
        Args:
            redact_serial: Whether to redact serial numbers in the result.
            
        Returns:
            DiagnosticResult with all collected information.
        """
        start_time = time.time()
        
        if not self.adb_manager.connected_device or \
           self.adb_manager.connection_state != ADBState.CONNECTED:
            return DiagnosticResult(
                timestamp=datetime.now(),
                success=False,
                error_message="No device connected. Please connect a device first.",
            )
        
        try:
            # Identify device
            device_identity = self.device_identifier.identify_device()
            
            # Collect additional diagnostic sections
            sections = {}
            
            # System properties
            sections["system_properties"] = self._collect_system_properties()
            
            # Storage details
            sections["storage"] = self._collect_storage_details()
            
            # Memory details
            sections["memory"] = self._collect_memory_details()
            
            # CPU details
            sections["cpu"] = self._collect_cpu_details()
            
            # Battery/Power details (if available)
            sections["battery"] = self._collect_battery_details()
            
            # Display details
            sections["display"] = self._collect_display_details()
            
            # Network details
            sections["network"] = self._collect_network_details()
            
            # Installed packages summary
            sections["packages_summary"] = self._collect_packages_summary()
            
            # Security settings
            sections["security"] = self._collect_security_settings()
            
            # Feature availability
            sections["features"] = self._collect_feature_availability()
            
            collection_time = int((time.time() - start_time) * 1000)
            
            # Redact serial if requested
            if redact_serial and device_identity:
                device_identity.serial = "REDACTED"
                if device_identity.build_fingerprint != "Unknown":
                    # Redact serial in fingerprint if present
                    pass
            
            result = DiagnosticResult(
                timestamp=datetime.now(),
                success=True,
                device_identity=device_identity,
                collection_time_ms=collection_time,
                sections=sections,
            )
            
            self.last_result = result
            return result
            
        except Exception as e:
            collection_time = int((time.time() - start_time) * 1000)
            return DiagnosticResult(
                timestamp=datetime.now(),
                success=False,
                error_message=f"Diagnostic failed: {str(e)}",
                collection_time_ms=collection_time,
            )
    
    def _run_safe_command(self, command: str) -> tuple[bool, str]:
        """Run a safe ADB command and return (success, output)."""
        success, stdout, stderr = self.adb_manager.run_shell_command(command)
        return success, stdout.strip() if stdout else stderr.strip()
    
    def _collect_system_properties(self) -> dict:
        """Collect system properties."""
        props = {}
        key_props = [
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
            "ro.build.display.id",
            "ro.product.cpu.abi",
            "ro.product.cpu.abilist",
            "ro.build.characteristics",
            "ro.hwui.texture_cache_size",
            "ro.sf.lcd_density",
            "ro.product.locale",
            "ro.product.locale.region",
            "ro.serialno",
            "ro.bootloader",
            "ro.hardware",
            "ro.revision",
        ]
        
        for prop in key_props:
            success, output = self._run_safe_command(f"getprop {prop}")
            props[prop] = output if success else "Unavailable"
        
        return props
    
    def _collect_storage_details(self) -> dict:
        """Collect detailed storage information."""
        storage = {}
        
        # Internal storage
        success, output = self._run_safe_command("df /data")
        if success:
            lines = output.split('\n')
            if len(lines) >= 2:
                parts = lines[1].split()
                if len(parts) >= 6:
                    storage["internal"] = {
                        "filesystem": parts[0],
                        "total_kb": int(parts[1]),
                        "used_kb": int(parts[2]),
                        "free_kb": int(parts[3]),
                        "use_percent": parts[4],
                        "mounted_on": parts[5],
                    }
        
        # System partition
        success, output = self._run_safe_command("df /system")
        if success:
            lines = output.split('\n')
            if len(lines) >= 2:
                parts = lines[1].split()
                if len(parts) >= 6:
                    storage["system"] = {
                        "filesystem": parts[0],
                        "total_kb": int(parts[1]),
                        "used_kb": int(parts[2]),
                        "free_kb": int(parts[3]),
                        "use_percent": parts[4],
                        "mounted_on": parts[5],
                    }
        
        # Cache partition
        success, output = self._run_safe_command("df /cache")
        if success:
            lines = output.split('\n')
            if len(lines) >= 2:
                parts = lines[1].split()
                if len(parts) >= 6:
                    storage["cache"] = {
                        "filesystem": parts[0],
                        "total_kb": int(parts[1]),
                        "used_kb": int(parts[2]),
                        "free_kb": int(parts[3]),
                        "use_percent": parts[4],
                        "mounted_on": parts[5],
                    }
        
        # External storage (if available)
        success, output = self._run_safe_command("df /sdcard")
        if success:
            lines = output.split('\n')
            if len(lines) >= 2:
                parts = lines[1].split()
                if len(parts) >= 6:
                    storage["external"] = {
                        "filesystem": parts[0],
                        "total_kb": int(parts[1]),
                        "used_kb": int(parts[2]),
                        "free_kb": int(parts[3]),
                        "use_percent": parts[4],
                        "mounted_on": parts[5],
                    }
        
        return storage
    
    def _collect_memory_details(self) -> dict:
        """Collect memory information."""
        memory = {}
        
        success, output = self._run_safe_command("cat /proc/meminfo")
        if success:
            for line in output.split('\n'):
                if ':' in line:
                    key, value = line.split(':', 1)
                    key = key.strip()
                    value = value.strip()
                    if key in ["MemTotal", "MemFree", "MemAvailable", "Buffers", "Cached", "SwapTotal", "SwapFree"]:
                        try:
                            memory[key] = int(value.split()[0])  # kB
                        except (ValueError, IndexError):
                            memory[key] = value
        
        # Also get vmstat for more details
        success, output = self._run_safe_command("cat /proc/vmstat")
        if success:
            memory["vmstat"] = {}
            for line in output.split('\n'):
                if ' ' in line:
                    key, value = line.split(' ', 1)
                    if key in ["pgfault", "pgmajfault", "pswpin", "pswpout"]:
                        try:
                            memory["vmstat"][key] = int(value.strip())
                        except ValueError:
                            pass
        
        return memory
    
    def _collect_cpu_details(self) -> dict:
        """Collect CPU information."""
        cpu = {}
        
        success, output = self._run_safe_command("cat /proc/cpuinfo")
        if success:
            cpu["cpuinfo"] = output
            # Parse key info
            for line in output.split('\n'):
                if ':' in line:
                    key, value = line.split(':', 1)
                    key = key.strip()
                    value = value.strip()
                    if key in ["Processor", "Hardware", "Revision", "Serial", "model name", "cpu cores", "cpu MHz", "BogoMIPS"]:
                        cpu[key] = value
        
        # CPU frequencies
        success, output = self._run_safe_command("ls /sys/devices/system/cpu/")
        if success:
            cpu["cpu_directories"] = output.strip().split()
        
        # Current frequencies
        freq_info = {}
        for cpu_dir in cpu.get("cpu_directories", []):
            if cpu_dir.startswith("cpu"):
                success, output = self._run_safe_command(f"cat /sys/devices/system/cpu/{cpu_dir}/cpufreq/scaling_cur_freq 2>/dev/null || cat /sys/devices/system/cpu/{cpu_dir}/cpufreq/cpuinfo_cur_freq 2>/dev/null")
                if success and output.isdigit():
                    freq_info[cpu_dir] = int(output) // 1000  # Convert to MHz
        cpu["current_frequencies_mhz"] = freq_info
        
        # Max frequencies
        max_freq_info = {}
        for cpu_dir in cpu.get("cpu_directories", []):
            if cpu_dir.startswith("cpu"):
                success, output = self._run_safe_command(f"cat /sys/devices/system/cpu/{cpu_dir}/cpufreq/scaling_max_freq 2>/dev/null || cat /sys/devices/system/cpu/{cpu_dir}/cpufreq/cpuinfo_max_freq 2>/dev/null")
                if success and output.isdigit():
                    max_freq_info[cpu_dir] = int(output) // 1000
        cpu["max_frequencies_mhz"] = max_freq_info
        
        return cpu
    
    def _collect_battery_details(self) -> dict:
        """Collect battery/power information."""
        battery = {}
        
        success, output = self._run_safe_command("dumpsys battery")
        if success:
            battery["dumpsys"] = output
            # Parse key values
            for line in output.split('\n'):
                line = line.strip()
                if ':' in line:
                    key, value = line.split(':', 1)
                    key = key.strip().lower().replace(' ', '_')
                    value = value.strip()
                    if key in ["level", "scale", "status", "health", "present", "technology", "voltage", "temperature", "plugged"]:
                        battery[key] = value
        
        # Battery stats
        success, output = self._run_safe_command("dumpsys batterystats --short")
        if success:
            battery["stats_summary"] = output[:2000]  # Truncate if too long
        
        return battery
    
    def _collect_display_details(self) -> dict:
        """Collect display information."""
        display = {}
        
        success, output = self._run_safe_command("wm size")
        if success:
            display["size"] = output
        
        success, output = self._run_safe_command("wm density")
        if success:
            display["density"] = output
        
        success, output = self._run_safe_command("dumpsys display")
        if success:
            display["dumpsys"] = output[:3000]  # Truncate
        
        # SurfaceFlinger info
        success, output = self._run_safe_command("dumpsys SurfaceFlinger --latency")
        if success:
            display["surfaceflinger_latency"] = output[:1000]
        
        return display
    
    def _collect_network_details(self) -> dict:
        """Collect network information."""
        network = {}
        
        # IP addresses
        success, output = self._run_safe_command("ip addr show")
        if success:
            network["interfaces"] = output
        
        # Wi-Fi info
        success, output = self._run_safe_command("dumpsys wifi | head -50")
        if success:
            network["wifi"] = output
        
        # Connectivity
        success, output = self._run_safe_command("dumpsys connectivity | head -50")
        if success:
            network["connectivity"] = output
        
        # DNS
        success, output = self._run_safe_command("getprop net.dns1")
        if success:
            network["dns1"] = output
        success, output = self._run_safe_command("getprop net.dns2")
        if success:
            network["dns2"] = output
        
        return network
    
    def _collect_packages_summary(self) -> dict:
        """Collect summary of installed packages."""
        packages = {}
        
        # Total package count
        success, output = self._run_safe_command("pm list packages")
        if success:
            all_packages = output.strip().split('\n')
            packages["total_count"] = len([p for p in all_packages if p.startswith("package:")])
        
        # Enabled packages
        success, output = self._run_safe_command("pm list packages -e")
        if success:
            enabled = output.strip().split('\n')
            packages["enabled_count"] = len([p for p in enabled if p.startswith("package:")])
        
        # Disabled packages
        success, output = self._run_safe_command("pm list packages -d")
        if success:
            disabled = output.strip().split('\n')
            packages["disabled_count"] = len([p for p in disabled if p.startswith("package:")])
        
        # System packages
        success, output = self._run_safe_command("pm list packages -s")
        if success:
            system = output.strip().split('\n')
            packages["system_count"] = len([p for p in system if p.startswith("package:")])
        
        # Third-party packages
        success, output = self._run_safe_command("pm list packages -3")
        if success:
            third_party = output.strip().split('\n')
            packages["third_party_count"] = len([p for p in third_party if p.startswith("package:")])
        
        # Launcher packages
        success, output = self._run_safe_command("pm list packages -c android.intent.category.HOME")
        if success:
            launchers = output.strip().split('\n')
            packages["launcher_packages"] = [p.replace("package:", "") for p in launchers if p.startswith("package:")]
        
        return packages
    
    def _collect_security_settings(self) -> dict:
        """Collect security-related settings."""
        security = {}
        
        # ADB status
        success, output = self._run_safe_command("getprop ro.adb.secure")
        if success:
            security["adb_secure"] = output
        
        # Debuggable
        success, output = self._run_safe_command("getprop ro.debuggable")
        if success:
            security["debuggable"] = output
        
        # Secure boot
        success, output = self._run_safe_command("getprop ro.boot.verifiedbootstate")
        if success:
            security["verified_boot"] = output
        
        # SELinux
        success, output = self._run_safe_command("getenforce")
        if success:
            security["selinux"] = output
        
        # Encryption
        success, output = self._run_safe_command("getprop ro.crypto.state")
        if success:
            security["encryption"] = output
        
        # Unknown sources
        success, output = self._run_safe_command("settings get secure install_non_market_apps")
        if success:
            security["unknown_sources"] = output
        
        return security
    
    def _collect_feature_availability(self) -> dict:
        """Check availability of specific features."""
        features = {}
        
        # Check for wireless debugging
        success, output = self._run_safe_command("settings get global adb_wifi_enabled")
        if success:
            features["wireless_debugging"] = output == "1"
        
        # Check for ADB over network (legacy)
        success, output = self._run_safe_command("getprop service.adb.tcp.port")
        if success and output != "":
            features["legacy_network_adb_port"] = output
        
        # Check for screen recording
        success, output = self._run_safe_command("which screenrecord")
        features["screenrecord"] = success and output != ""
        
        # Check for screenshot
        success, output = self._run_safe_command("which screencap")
        features["screencap"] = success and output != ""
        
        # Check for input injection
        success, output = self._run_safe_command("which input")
        features["input_injection"] = success and output != ""
        
        # Check for settings access
        success, output = self._run_safe_command("which settings")
        features["settings_access"] = success and output != ""
        
        # Check for package manager
        success, output = self._run_safe_command("which pm")
        features["package_manager"] = success and output != ""
        
        # Check for activity manager
        success, output = self._run_safe_command("which am")
        features["activity_manager"] = success and output != ""
        
        return features
    
    def export_result(self, result: DiagnosticResult, output_path: Path, redact: bool = False) -> bool:
        """
        Export diagnostic result to JSON file.
        
        Args:
            result: DiagnosticResult to export.
            output_path: Path to output file.
            redact: Whether to redact sensitive information.
            
        Returns:
            True if export succeeded.
        """
        try:
            data = result.to_dict()
            
            if redact:
                data = self._redact_data(data)
            
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            
            return True
        except Exception as e:
            print(f"Export failed: {e}")
            return False
    
    def _redact_data(self, data: dict) -> dict:
        """Redact sensitive information from diagnostic data."""
        import copy
        data = copy.deepcopy(data)
        
        # Redact serial in device identity
        if "device_identity" in data and data["device_identity"]:
            data["device_identity"]["serial"] = "REDACTED"
            if "build_fingerprint" in data["device_identity"]:
                fp = data["device_identity"]["build_fingerprint"]
                # Redact potential serial in fingerprint
                if fp != "Unknown":
                    data["device_identity"]["build_fingerprint"] = "REDACTED"
        
        # Redact serial in system properties
        if "sections" in data and "system_properties" in data["sections"]:
            props = data["sections"]["system_properties"]
            if "ro.serialno" in props:
                props["ro.serialno"] = "REDACTED"
        
        # Redact network interfaces MAC addresses
        if "sections" in data and "network" in data["sections"]:
            # Could parse and redact MAC addresses if needed
            pass
        
        return data
    
    def get_last_result(self) -> Optional[DiagnosticResult]:
        """Get the last diagnostic result."""
        return self.last_result


def create_diagnostics_engine(adb_manager: ADBManager) -> DiagnosticsEngine:
    """Factory function to create a DiagnosticsEngine."""
    return DiagnosticsEngine(adb_manager)