"""
Package Inventory - Installed application analysis for TV Freedom.

This module provides comprehensive installed application inventory
with detailed information about each package.
"""

from dataclasses import dataclass, field
from typing import Optional
from enum import Enum
import json
from pathlib import Path

from adb_manager import ADBManager, ADBState


class PackageCategory(Enum):
    """Categories for package classification."""
    STREAMING = "streaming"
    SYSTEM = "system"
    GOOGLE_SERVICES = "google_services"
    MANUFACTURER = "manufacturer"
    RECOMMENDATIONS = "recommendations"
    SCREENSAVER = "screensaver"
    INPUT = "input"
    NETWORK = "network"
    SETTINGS = "settings"
    LAUNCHER = "launcher"
    UNKNOWN = "unknown"


class PackageSource(Enum):
    """Source of the package."""
    SYSTEM = "system"           # Pre-installed system app
    USER = "user"               # User-installed app
    UPDATED_SYSTEM = "updated_system"  # System app with updates
    UNKNOWN = "unknown"


@dataclass
class PackageInfo:
    """Information about an installed package."""
    package_name: str
    display_name: str = "Unknown"
    version_name: str = "Unknown"
    version_code: int = 0
    category: PackageCategory = PackageCategory.UNKNOWN
    source: PackageSource = PackageSource.UNKNOWN
    enabled: bool = True
    installer_package: str = "Unknown"
    install_location: str = "Unknown"  # internal, external, etc.
    permissions: list[str] = field(default_factory=list)
    activities: list[str] = field(default_factory=list)
    services: list[str] = field(default_factory=list)
    receivers: list[str] = field(default_factory=list)
    providers: list[str] = field(default_factory=list)
    is_launcher: bool = False
    is_system_ui: bool = False
    is_settings: bool = False
    is_input_method: bool = False
    is_accessibility: bool = False
    is_device_admin: bool = False
    first_install_time: int = 0
    last_update_time: int = 0
    data_dir: str = "Unknown"
    apk_path: str = "Unknown"
    # Classification confidence
    classification_confidence: float = 0.0  # 0.0 to 1.0
    classification_reason: str = ""
    
    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "package_name": self.package_name,
            "display_name": self.display_name,
            "version_name": self.version_name,
            "version_code": self.version_code,
            "category": self.category.value,
            "source": self.source.value,
            "enabled": self.enabled,
            "installer_package": self.installer_package,
            "install_location": self.install_location,
            "permissions": self.permissions,
            "activities": self.activities,
            "services": self.services,
            "receivers": self.receivers,
            "providers": self.providers,
            "is_launcher": self.is_launcher,
            "is_system_ui": self.is_system_ui,
            "is_settings": self.is_settings,
            "is_input_method": self.is_input_method,
            "is_accessibility": self.is_accessibility,
            "is_device_admin": self.is_device_admin,
            "first_install_time": self.first_install_time,
            "last_update_time": self.last_update_time,
            "data_dir": self.data_dir,
            "apk_path": self.apk_path,
            "classification_confidence": self.classification_confidence,
            "classification_reason": self.classification_reason,
        }


class PackageInventory:
    """Manages installed package inventory."""
    
    def __init__(self, adb_manager: ADBManager):
        self.adb_manager = adb_manager
        self._packages: list[PackageInfo] = []
        self._package_map: dict[str, PackageInfo] = {}
        self._last_refresh: float = 0
    
    def refresh(self) -> tuple[bool, str]:
        """
        Refresh the package inventory from the device.
        
        Returns:
            Tuple of (success, message).
        """
        if not self.adb_manager.connected_device or \
           self.adb_manager.connection_state != ADBState.CONNECTED:
            return False, "No device connected"
        
        try:
            self._packages = []
            self._package_map = {}
            
            # Get all packages with basic info
            success, output = self._run_safe("pm list packages -f")
            if not success:
                return False, f"Failed to list packages: {output}"
            
            package_lines = [line for line in output.strip().split('\n') if line.startswith("package:")]
            
            for line in package_lines:
                # Format: package:/path/to/base.apk=com.package.name
                try:
                    apk_part, pkg_name = line.split('=', 1)
                    apk_path = apk_part.replace("package:", "").strip()
                    pkg_name = pkg_name.strip()
                    
                    pkg_info = self._get_package_details(pkg_name, apk_path)
                    self._packages.append(pkg_info)
                    self._package_map[pkg_name] = pkg_info
                except ValueError:
                    continue
            
            self._last_refresh = time.time()
            return True, f"Found {len(self._packages)} packages"
            
        except Exception as e:
            return False, f"Inventory refresh failed: {str(e)}"
    
    def _run_safe(self, command: str) -> tuple[bool, str]:
        """Run a safe ADB command."""
        success, stdout, stderr = self.adb_manager.run_shell_command(command)
        return success, stdout.strip() if stdout else stderr.strip()
    
    def _get_package_details(self, package_name: str, apk_path: str) -> PackageInfo:
        """Get detailed information for a single package."""
        pkg = PackageInfo(package_name=package_name, apk_path=apk_path)
        
        # Get package info via dumpsys
        success, output = self._run_safe(f"dumpsys package {package_name}")
        if success:
            self._parse_dumpsys_output(pkg, output)
        
        # Get installer
        success, output = self._run_safe(f"pm get-installer {package_name}")
        if success and output:
            pkg.installer_package = output.replace("package:", "").strip()
        
        # Get install location
        success, output = self._run_safe(f"pm get-install-location {package_name}")
        if success:
            pkg.install_location = output.strip()
        
        # Determine source
        pkg.source = self._determine_source(pkg)
        
        # Classify package
        self._classify_package(pkg)
        
        return pkg
    
    def _parse_dumpsys_output(self, pkg: PackageInfo, output: str):
        """Parse dumpsys package output."""
        current_section = None
        
        for line in output.split('\n'):
            line = line.strip()
            if not line:
                continue
            
            # Section headers
            if line.startswith("Package ["):
                current_section = "package"
            elif line.startswith("  User "):
                current_section = "user"
            elif line.startswith("  Shared User "):
                current_section = "shared_user"
            elif "versionCode=" in line and "versionName=" in line:
                # Parse version info
                try:
                    parts = line.split()
                    for part in parts:
                        if part.startswith("versionCode="):
                            pkg.version_code = int(part.split("=")[1].rstrip(","))
                        elif part.startswith("versionName="):
                            pkg.version_name = part.split("=")[1].rstrip(",")
                except (ValueError, IndexError):
                    pass
            elif "pkgFlags=" in line:
                # Parse flags for system/user status
                try:
                    flags_part = line.split("pkgFlags=")[1].split()[0]
                    flags = int(flags_part, 16)
                    # SYSTEM_FLAG = 0x1, UPDATED_SYSTEM_APP_FLAG = 0x80000000
                    if flags & 0x1:
                        pkg.source = PackageSource.SYSTEM
                    if flags & 0x80000000:
                        pkg.source = PackageSource.UPDATED_SYSTEM
                except (ValueError, IndexError):
                    pass
            elif "installTime=" in line:
                try:
                    pkg.first_install_time = int(line.split("installTime=")[1].split()[0])
                except (ValueError, IndexError):
                    pass
            elif "updateTime=" in line:
                try:
                    pkg.last_update_time = int(line.split("updateTime=")[1].split()[0])
                except (ValueError, IndexError):
                    pass
            elif line.startswith("  User ") and "installed=true" in line:
                pkg.enabled = True
            elif line.startswith("  User ") and "installed=false" in line:
                pkg.enabled = False
            elif "dataDir=" in line:
                try:
                    pkg.data_dir = line.split("dataDir=")[1].split()[0]
                except IndexError:
                    pass
            elif line.startswith("    ") and "android.permission." in line:
                # Permission
                perm = line.strip()
                if perm.startswith("android.permission."):
                    pkg.permissions.append(perm)
            elif "Activity" in line and "{" in line:
                # Activity
                pkg.activities.append(line.strip())
            elif "Service" in line and "{" in line:
                pkg.services.append(line.strip())
            elif "Provider" in line and "{" in line:
                pkg.providers.append(line.strip())
            elif "Receiver" in line and "{" in line:
                pkg.receivers.append(line.strip())
        
        # Get display name from package label
        success, output = self._run_safe(f"pm dump {pkg.package_name} | grep -A1 'label='")
        if not success:
            # Try alternative
            success, output = self._run_safe(f"dumpsys package {pkg.package_name} | grep -A1 'label='")
        if success and "label=" in output:
            try:
                pkg.display_name = output.split("label=")[1].split()[0].strip()
            except IndexError:
                pass
    
    def _determine_source(self, pkg: PackageInfo) -> PackageSource:
        """Determine package source."""
        installer = pkg.installer_package.lower()
        
        if pkg.source != PackageSource.UNKNOWN:
            return pkg.source
        
        if "com.google.android.feedback" in installer or \
           "com.android.vending" in installer or \
           "com.android.chrome" in installer:
            return PackageSource.USER
        
        # Check if it's a known system package pattern
        system_patterns = [
            "android.", "com.android.", "com.google.android.",
            "com.qualcomm.", "com.mediatek.", "com.samsung.",
            "com.sony.", "com.htc.", "com.lge.", "com.motorola.",
        ]
        
        for pattern in system_patterns:
            if pkg.package_name.startswith(pattern):
                return PackageSource.SYSTEM
        
        return PackageSource.UNKNOWN
    
    def _classify_package(self, pkg: PackageInfo):
        """Classify package into category with confidence."""
        name = pkg.package_name.lower()
        display = pkg.display_name.lower()
        
        # Launcher detection
        if pkg.is_launcher or "launcher" in name or "home" in name:
            pkg.category = PackageCategory.LAUNCHER
            pkg.is_launcher = True
            pkg.classification_confidence = 0.9
            pkg.classification_reason = "Package name or category indicates launcher"
            return
        
        # System UI
        if "systemui" in name or "system_ui" in name:
            pkg.category = PackageCategory.SYSTEM
            pkg.is_system_ui = True
            pkg.classification_confidence = 0.95
            pkg.classification_reason = "System UI package"
        
        # Settings
        if "settings" in name and ("android" in name or "com.android" in name):
            pkg.category = PackageCategory.SETTINGS
            pkg.is_settings = True
            pkg.classification_confidence = 0.9
            pkg.classification_reason = "System Settings package"
        
        # Input methods
        if any(keyword in name for keyword in ["inputmethod", "keyboard", "ime"]):
            pkg.category = PackageCategory.INPUT
            pkg.is_input_method = True
            pkg.classification_confidence = 0.85
            pkg.classification_reason = "Input method package"
        
        # Accessibility
        if "accessibility" in name or "talkback" in name or "switchaccess" in name:
            pkg.category = PackageCategory.SYSTEM
            pkg.is_accessibility = True
            pkg.classification_confidence = 0.85
            pkg.classification_reason = "Accessibility service"
        
        # Device admin
        if "deviceadmin" in name or "device_admin" in name:
            pkg.category = PackageCategory.SYSTEM
            pkg.is_device_admin = True
            pkg.classification_confidence = 0.8
            pkg.classification_reason = "Device admin package"
        
        # Streaming apps
        streaming_keywords = [
            "netflix", "hulu", "disney", "prime", "amazon.video",
            "youtube", "youtubetv", "hbomax", "paramount", "peacock",
            "apple.tv", "roku", "plex", "kodi", "vlc", "twitch",
            "spotify", "pandora", "tidal", "deezer", "soundcloud",
            "crunchyroll", "funimation", "vrv", "tubi", "pluto",
            "crackle", "vudu", "fandango", "movies", "tv",
        ]
        for kw in streaming_keywords:
            if kw in name or kw in display:
                pkg.category = PackageCategory.STREAMING
                pkg.classification_confidence = 0.8
                pkg.classification_reason = f"Streaming service detected ({kw})"
                break
        
        # Google services
        google_patterns = [
            "com.google.android.gms", "com.google.android.gsf",
            "com.google.android.gms.wearable", "com.google.android.tts",
            "com.google.android.tts", "com.google.android.inputmethod",
            "com.google.android.youtube", "com.google.android.music",
            "com.google.android.videos", "com.google.android.play",
        ]
        for pattern in google_patterns:
            if pattern in name:
                pkg.category = PackageCategory.GOOGLE_SERVICES
                pkg.classification_confidence = 0.9
                pkg.classification_reason = f"Google service ({pattern})"
                break
        
        # Manufacturer services
        manufacturer_keywords = [
            "sony", "tcl", "xiaomi", "hisense", "philips", "sharp",
            "nvidia", "shield", "mediatek", "qualcomm", "amlogic",
            "realtek", "broadcom", "intel", "nvidia",
        ]
        for kw in manufacturer_keywords:
            if kw in name:
                pkg.category = PackageCategory.MANUFACTURER
                pkg.classification_confidence = 0.7
                pkg.classification_reason = f"Manufacturer service ({kw})"
                break
        
        # Recommendations/sponsored content
        recommendation_keywords = [
            "recommendation", "suggestion", "discovery", "promo",
            "advertisement", "ads", "sponsored", "leanback",
            "tvlauncher", "ambient", "screensaver", "dream",
        ]
        for kw in recommendation_keywords:
            if kw in name or kw in display:
                pkg.category = PackageCategory.RECOMMENDATIONS
                pkg.classification_confidence = 0.75
                pkg.classification_reason = f"Recommendation/ambient content ({kw})"
                break
        
        # Screensaver/dream
        screensaver_keywords = [
            "dreamservice", "screensaver", "daydream", "ambient",
            "com.android.dreams", "photoscreensaver",
        ]
        for kw in screensaver_keywords:
            if kw in name:
                pkg.category = PackageCategory.SCREENSAVER
                pkg.classification_confidence = 0.8
                pkg.classification_reason = f"Screensaver/dream service ({kw})"
                break
        
        # Network/connectivity
        network_keywords = [
            "wifi", "bluetooth", "nfc", "hotspot", "tether",
            "connectivity", "network", "telephony",
        ]
        for kw in network_keywords:
            if kw in name and pkg.category == PackageCategory.UNKNOWN:
                pkg.category = PackageCategory.NETWORK
                pkg.classification_confidence = 0.6
                pkg.classification_reason = f"Network/connectivity service ({kw})"
                break
        
        # Default to system if it's a system package
        if pkg.category == PackageCategory.UNKNOWN and pkg.source in (PackageSource.SYSTEM, PackageSource.UPDATED_SYSTEM):
            pkg.category = PackageCategory.SYSTEM
            pkg.classification_confidence = 0.5
            pkg.classification_reason = "System package (unclassified)"
        
        # Default to user if user-installed
        if pkg.category == PackageCategory.UNKNOWN and pkg.source == PackageSource.USER:
            pkg.category = PackageCategory.UNKNOWN
            pkg.classification_confidence = 0.3
            pkg.classification_reason = "User-installed app (unknown purpose)"
    
    def get_all_packages(self) -> list[PackageInfo]:
        """Get all packages."""
        return self._packages.copy()
    
    def get_package(self, package_name: str) -> Optional[PackageInfo]:
        """Get a specific package by name."""
        return self._package_map.get(package_name)
    
    def get_packages_by_category(self, category: PackageCategory) -> list[PackageInfo]:
        """Get packages filtered by category."""
        return [p for p in self._packages if p.category == category]
    
    def get_packages_by_source(self, source: PackageSource) -> list[PackageInfo]:
        """Get packages filtered by source."""
        return [p for p in self._packages if p.source == source]
    
    def get_enabled_packages(self) -> list[PackageInfo]:
        """Get only enabled packages."""
        return [p for p in self._packages if p.enabled]
    
    def get_disabled_packages(self) -> list[PackageInfo]:
        """Get only disabled packages."""
        return [p for p in self._packages if not p.enabled]
    
    def get_launcher_packages(self) -> list[PackageInfo]:
        """Get launcher packages."""
        return [p for p in self._packages if p.is_launcher]
    
    def get_critical_packages(self) -> list[PackageInfo]:
        """Get packages that should never be disabled (system critical)."""
        critical_categories = {
            PackageCategory.SYSTEM,
            PackageCategory.LAUNCHER,
            PackageCategory.SETTINGS,
            PackageCategory.INPUT,
            PackageCategory.NETWORK,
        }
        return [p for p in self._packages if p.category in critical_categories or p.is_device_admin or p.is_accessibility]
    
    def get_summary(self) -> dict:
        """Get inventory summary."""
        return {
            "total": len(self._packages),
            "enabled": len(self.get_enabled_packages()),
            "disabled": len(self.get_disabled_packages()),
            "system": len(self.get_packages_by_source(PackageSource.SYSTEM)),
            "user": len(self.get_packages_by_source(PackageSource.USER)),
            "updated_system": len(self.get_packages_by_source(PackageSource.UPDATED_SYSTEM)),
            "by_category": {
                cat.value: len(self.get_packages_by_category(cat))
                for cat in PackageCategory
            },
            "critical_count": len(self.get_critical_packages()),
            "last_refresh": self._last_refresh,
        }
    
    def export_inventory(self, output_path: Path, redact: bool = False) -> bool:
        """Export inventory to JSON file."""
        try:
            data = {
                "timestamp": time.time(),
                "summary": self.get_summary(),
                "packages": [p.to_dict() for p in self._packages],
            }
            
            if redact:
                for pkg in data["packages"]:
                    pkg["package_name"] = "REDACTED"
                    pkg["apk_path"] = "REDACTED"
                    pkg["data_dir"] = "REDACTED"
            
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            return True
        except Exception as e:
            print(f"Export failed: {e}")
            return False


import time


def create_package_inventory(adb_manager: ADBManager) -> PackageInventory:
    """Factory function to create a PackageInventory."""
    return PackageInventory(adb_manager)