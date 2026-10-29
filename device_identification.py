"""
Device Identification - Comprehensive device analysis for TV Freedom.

This module provides detailed device identification and classification
based on ADB device properties. It uses multiple signals to determine
platform type and compatibility.
"""

from dataclasses import dataclass, field
from typing import Optional
from adb_manager import ADBManager, ADBDevice, ADBState


@dataclass
class DeviceIdentity:
    """Complete device identity information."""
    # Basic info
    manufacturer: str = "Unknown"
    model: str = "Unknown"
    brand: str = "Unknown"
    device_codename: str = "Unknown"
    board: str = "Unknown"
    
    # Android version
    android_version: str = "Unknown"  # e.g., "Android 12 (API 31)"
    android_release: str = "Unknown"  # e.g., "12"
    api_level: int = 0
    security_patch: str = "Unknown"
    build_id: str = "Unknown"
    build_fingerprint: str = "Unknown"
    build_type: str = "Unknown"
    build_tags: str = "Unknown"
    
    # Hardware
    cpu_abi: str = "Unknown"
    cpu_abilist: str = "Unknown"
    screen_resolution: str = "Unknown"
    screen_density: int = 0
    
    # Runtime
    default_launcher: str = "Unknown"
    uptime_seconds: int = 0
    memory_total_mb: int = 0
    memory_available_mb: int = 0
    
    # Storage (from separate query)
    storage_total_gb: float = 0.0
    storage_free_gb: float = 0.0
    storage_free_percent: float = 0.0
    
    # Classification
    platform_type: str = "unknown"  # android_tv, google_tv, fire_tv, unknown
    characteristics: str = "Unknown"
    is_tv_device: bool = False
    
    # Compatibility
    compatibility_score: int = 0  # 0-100
    compatibility_notes: list[str] = field(default_factory=list)
    supported_features: list[str] = field(default_factory=list)
    unsupported_features: list[str] = field(default_factory=list)
    
    # Connection
    connection_type: str = "unknown"
    serial: str = "Unknown"


class DeviceIdentifier:
    """Analyzes device properties to identify and classify the device."""
    
    # Minimum API level for full feature support
    MIN_API_LEVEL = 29  # Android 10
    RECOMMENDED_API_LEVEL = 31  # Android 12
    
    # Known platform signatures
    FIRE_TV_INDICATORS = {
        "manufacturer": ["amazon"],
        "brand": ["amazon"],
        "model": ["fire", "aft"],
        "fingerprint": ["amazon", "fireos"],
    }
    
    GOOGLE_TV_INDICATORS = {
        "manufacturer": ["google"],
        "brand": ["google"],
        "model": ["chromecast", "google tv"],
        "fingerprint": ["google tv", "chromecast"],
    }
    
    ANDROID_TV_MANUFACTURERS = [
        "sony", "tcl", "xiaomi", "hisense", "philips", "sharp", 
        "nvidia", "shield", "jvc", "toshiba", "panasonic", "sanyo",
        "airtv", "mi box", "dynalink", "on"
    ]
    
    def __init__(self, adb_manager: ADBManager):
        self.adb_manager = adb_manager
    
    def identify_device(self) -> DeviceIdentity:
        """
        Perform comprehensive device identification.
        
        Returns:
            DeviceIdentity with all available information.
        """
        if not self.adb_manager.connected_device or \
           self.adb_manager.connection_state != ADBState.CONNECTED:
            return DeviceIdentity()
        
        # Get extended device info from ADB manager
        extended_device = self.adb_manager.get_extended_device_info()
        
        # Get storage info
        storage = self.adb_manager.get_storage_info()
        
        # Build identity
        identity = DeviceIdentity(
            manufacturer=extended_device.manufacturer or "Unknown",
            model=extended_device.model or "Unknown",
            brand=extended_device.manufacturer or "Unknown",  # Often same as manufacturer
            device_codename=extended_device.device_codename or "Unknown",
            board=extended_device.board or "Unknown",
            android_version=extended_device.android_version or "Unknown",
            api_level=extended_device.api_level or 0,
            cpu_abi=extended_device.cpu_abi or "Unknown",
            screen_resolution=extended_device.screen_resolution or "Unknown",
            screen_density=extended_device.screen_density or 0,
            default_launcher=extended_device.default_launcher or "Unknown",
            uptime_seconds=extended_device.uptime_seconds or 0,
            memory_total_mb=extended_device.memory_total_mb or 0,
            memory_available_mb=extended_device.memory_available_mb or 0,
            storage_total_gb=storage.get("total_gb", 0.0),
            storage_free_gb=storage.get("free_gb", 0.0),
            storage_free_percent=storage.get("free_percent", 0.0),
            platform_type=extended_device.platform_type or "unknown",
            characteristics="tv" if extended_device.platform_type in ("android_tv", "google_tv") else "unknown",
            is_tv_device=extended_device.platform_type in ("android_tv", "google_tv"),
            connection_type=extended_device.connection_type or "unknown",
            serial=extended_device.serial or "Unknown",
        )
        
        # Extract additional info from build fingerprint
        if extended_device.build_fingerprint:
            identity.build_fingerprint = extended_device.build_fingerprint
            self._parse_build_fingerprint(identity, extended_device.build_fingerprint)
        
        # Determine platform type if not already set
        if identity.platform_type == "unknown":
            identity.platform_type = self._determine_platform_type(identity)
            identity.is_tv_device = identity.platform_type in ("android_tv", "google_tv")
            identity.characteristics = "tv" if identity.is_tv_device else "unknown"
        
        # Calculate compatibility
        self._calculate_compatibility(identity)
        
        return identity
    
    def _parse_build_fingerprint(self, identity: DeviceIdentity, fingerprint: str):
        """Parse build fingerprint for additional information."""
        # Format: manufacturer/device/model:version/id/build:user/release-keys
        # Example: google/sabrina/sabrina:13/TD4A.221105.002/9127208:user/release-keys
        try:
            parts = fingerprint.split('/')
            if len(parts) >= 3:
                identity.brand = parts[0] or identity.brand
                identity.device_codename = parts[1] or identity.device_codename
                identity.model = parts[2] or identity.model
            
            # Parse version info from fingerprint
            version_part = fingerprint.split(':')
            if len(version_part) >= 2:
                version_info = version_part[1]
                if version_info and identity.android_version == "Unknown":
                    identity.android_version = f"Android {version_info} (from fingerprint)"
        except Exception:
            pass  # Keep existing values
    
    def _determine_platform_type(self, identity: DeviceIdentity) -> str:
        """Determine platform type using multiple signals."""
        manufacturer = (identity.manufacturer or "").lower()
        brand = (identity.brand or "").lower()
        model = (identity.model or "").lower()
        fingerprint = (identity.build_fingerprint or "").lower()
        characteristics = (identity.characteristics or "").lower()
        
        # Check for Fire TV first (most restrictive)
        for indicator in self.FIRE_TV_INDICATORS["manufacturer"]:
            if indicator in manufacturer:
                return "fire_tv"
        for indicator in self.FIRE_TV_INDICATORS["brand"]:
            if indicator in brand:
                return "fire_tv"
        for indicator in self.FIRE_TV_INDICATORS["model"]:
            if indicator in model:
                return "fire_tv"
        for indicator in self.FIRE_TV_INDICATORS["fingerprint"]:
            if indicator in fingerprint:
                return "fire_tv"
        
        # Check for Google TV
        for indicator in self.GOOGLE_TV_INDICATORS["manufacturer"]:
            if indicator in manufacturer:
                return "google_tv"
        for indicator in self.GOOGLE_TV_INDICATORS["brand"]:
            if indicator in brand:
                return "google_tv"
        for indicator in self.GOOGLE_TV_INDICATORS["model"]:
            if indicator in model:
                return "google_tv"
        for indicator in self.GOOGLE_TV_INDICATORS["fingerprint"]:
            if indicator in fingerprint:
                return "google_tv"
        
        # Check for Android TV characteristics
        if "tv" in characteristics or "television" in characteristics:
            return "android_tv"
        
        # Check for known Android TV manufacturers
        for mfr in self.ANDROID_TV_MANUFACTURERS:
            if mfr in manufacturer or mfr in brand or mfr in model:
                return "android_tv"
        
        # Check build characteristics for TV
        if "tv" in characteristics:
            return "android_tv"
        
        return "unknown"
    
    def _calculate_compatibility(self, identity: DeviceIdentity):
        """Calculate compatibility score and generate notes."""
        score = 0
        notes = []
        supported = []
        unsupported = []
        
        # Platform type scoring
        if identity.platform_type == "android_tv":
            score += 40
            supported.append("Android TV platform detected")
        elif identity.platform_type == "google_tv":
            score += 45
            supported.append("Google TV platform detected (best compatibility)")
        elif identity.platform_type == "fire_tv":
            score -= 30
            unsupported.append("Fire OS / Fire TV — not supported by TV Freedom")
            notes.append("Amazon Fire TV devices cannot be safely modified")
        else:
            score += 10
            notes.append("Platform type unknown — compatibility uncertain")
        
        # API level scoring
        if identity.api_level > 0:
            if identity.api_level >= self.RECOMMENDED_API_LEVEL:
                score += 25
                supported.append(f"Android API {identity.api_level} (Android {identity.android_release}) — full feature support")
            elif identity.api_level >= self.MIN_API_LEVEL:
                score += 15
                supported.append(f"Android API {identity.api_level} — basic feature support")
                notes.append("Some features may be limited on Android 10/11")
            else:
                score -= 20
                unsupported.append(f"Android API {identity.api_level} below minimum (API {self.MIN_API_LEVEL})")
                notes.append("Launcher replacement and package management not supported on Android 9 or earlier")
        else:
            notes.append("Could not determine Android API level")
        
        # Storage scoring
        if identity.storage_free_gb > 0:
            if identity.storage_free_gb >= 2:
                score += 15
                supported.append(f"Sufficient storage: {identity.storage_free_gb:.1f} GB free")
            elif identity.storage_free_gb >= 1:
                score += 5
                notes.append(f"Low storage: {identity.storage_free_gb:.1f} GB free — backups may be limited")
            else:
                score -= 10
                notes.append(f"Critically low storage: {identity.storage_free_gb:.1f} GB free — operations may fail")
                unsupported.append("Insufficient storage for safe operations")
        else:
            notes.append("Could not determine storage information")
        
        # Memory scoring
        if identity.memory_total_mb > 0:
            if identity.memory_total_mb >= 2048:  # 2GB+
                score += 10
                supported.append(f"Good memory: {identity.memory_total_mb} MB total")
            elif identity.memory_total_mb >= 1024:  # 1GB+
                score += 5
                notes.append(f"Limited memory: {identity.memory_total_mb} MB total")
            else:
                notes.append(f"Very low memory: {identity.memory_total_mb} MB total")
        else:
            notes.append("Could not determine memory information")
        
        # CPU architecture
        if identity.cpu_abi and identity.cpu_abi != "Unknown":
            if "arm64" in identity.cpu_abi.lower() or "x86_64" in identity.cpu_abi.lower():
                score += 5
                supported.append(f"64-bit architecture: {identity.cpu_abi}")
            else:
                notes.append(f"32-bit architecture: {identity.cpu_abi} — some features may be limited")
        
        # Launcher detection
        if identity.default_launcher != "Unknown":
            supported.append(f"Current launcher: {identity.default_launcher}")
        
        # Clamp score
        identity.compatibility_score = max(0, min(100, score))
        identity.compatibility_notes = notes
        identity.supported_features = supported
        identity.unsupported_features = unsupported
    
    def get_compatibility_summary(self, identity: DeviceIdentity) -> dict:
        """Get a summary of compatibility assessment."""
        if identity.compatibility_score >= 80:
            level = "Excellent"
            color = "green"
        elif identity.compatibility_score >= 60:
            level = "Good"
            color = "blue"
        elif identity.compatibility_score >= 40:
            level = "Limited"
            color = "orange"
        else:
            level = "Poor / Unsupported"
            color = "red"
        
        return {
            "score": identity.compatibility_score,
            "level": level,
            "color": color,
            "is_compatible": identity.compatibility_score >= 50,
            "platform_type": identity.platform_type,
            "notes": identity.compatibility_notes,
            "supported": identity.supported_features,
            "unsupported": identity.unsupported_features,
        }


def create_device_identifier(adb_manager: ADBManager) -> DeviceIdentifier:
    """Factory function to create a DeviceIdentifier."""
    return DeviceIdentifier(adb_manager)