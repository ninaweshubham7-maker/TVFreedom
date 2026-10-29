"""
Package Classifier - Safe app classification for TV Freedom.

This module provides conservative classification of installed packages,
erring on the side of protecting system-critical applications.
"""

from dataclasses import dataclass, field
from typing import Optional
from enum import Enum
from package_inventory import PackageInfo, PackageCategory, PackageSource, PackageInventory


class SafetyLevel(Enum):
    """Safety level for package operations."""
    CRITICAL = "critical"           # Never disable - essential for device operation
    PROTECTED = "protected"         # Strongly recommend against disabling
    CAUTION = "caution"             # May cause issues if disabled
    SAFE = "safe"                   # Generally safe to disable
    USER_APP = "user_app"           # User-installed, generally safe
    UNKNOWN = "unknown"             # Cannot determine safety


class ActionType(Enum):
    """Type of action that can be performed on a package."""
    DISABLE = "disable"             # pm disable-user
    ENABLE = "enable"               # pm enable
    UNINSTALL = "uninstall"         # pm uninstall (user apps only)
    CLEAR_DATA = "clear_data"       # pm clear
    CHANGE_SETTING = "change_setting"  # settings put
    CHANGE_MULTIPLE_SETTINGS = "change_multiple_settings"  # multiple settings put
    NONE = "none"


@dataclass
class PackageSafetyAssessment:
    """Safety assessment for a package."""
    package_name: str
    display_name: str
    safety_level: SafetyLevel
    allowed_actions: list[ActionType] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    explanation: str = ""
    reversal_info: str = ""
    confidence: float = 0.0  # 0.0 to 1.0
    
    def can_disable(self) -> bool:
        return ActionType.DISABLE in self.allowed_actions
    
    def can_uninstall(self) -> bool:
        return ActionType.UNINSTALL in self.allowed_actions
    
    def to_dict(self) -> dict:
        return {
            "package_name": self.package_name,
            "display_name": self.display_name,
            "safety_level": self.safety_level.value,
            "allowed_actions": [a.value for a in self.allowed_actions],
            "warnings": self.warnings,
            "explanation": self.explanation,
            "reversal_info": self.reversal_info,
            "confidence": self.confidence,
        }


class PackageClassifier:
    """Classifies packages for safe operations."""
    
    # Package names that are ALWAYS critical (never disable)
    CRITICAL_PACKAGES = {
        # Core system
        "android",
        "android.autoinstalls.config",
        "com.android.providers.settings",
        "com.android.providers.downloads",
        "com.android.providers.media",
        "com.android.providers.telephony",
        "com.android.providers.userdictionary",
        "com.android.shell",
        "com.android.systemui",
        "com.android.keyguard",
        "com.android.settings",
        "com.android.packageinstaller",
        "com.android.permissioncontroller",
        "com.android.documentsui",
        "com.android.managedprovisioning",
        "com.android.vending",  # Play Store
        "com.google.android.gms",  # Google Play Services
        "com.google.android.gsf",  # Google Services Framework
        "com.android.bluetooth",
        "com.android.wifi",
        "com.android.nfc",
        "com.android.nfc3",
        "com.android.traceur",
        
        # Input/keyboard
        "com.android.inputmethod.latin",
        "com.google.android.inputmethod.latin",
        "com.android.inputmethod.pinyin",
        
        # Accessibility
        "com.google.android.marvin.talkback",
        "com.android.talkback",
        
        # Device setup
        "com.google.android.setupwizard",
        "com.android.provision",
        
        # TV-specific critical
        "com.google.android.tvlauncher",
        "com.google.android.leanbacklauncher",
        "com.amazon.tv.launcher",
        "com.android.tv.settings",
        "com.android.tv.remotecontrol",
        "com.android.tv.tuner",
        "com.android.tv.dvr",
    }
    
    # Package prefixes that indicate critical system components
    CRITICAL_PREFIXES = {
        "android.",
        "com.android.",
        "com.google.android.gms",
        "com.google.android.gsf",
        "com.google.android.setupwizard",
        "com.android.providers.",
        "com.android.server.",
        "com.android.internal.",
        "com.qualcomm.",
        "com.mediatek.",
        "com.samsung.android.",
        "com.sony.",
        "com.htc.",
        "com.lge.",
        "com.motorola.",
        "com.amazon.device.",
        "com.amazon.tv.",
    }
    
    # Package names that are protected (strongly recommend against)
    PROTECTED_PACKAGES = {
        "com.android.chrome",
        "com.android.browser",
        "com.android.email",
        "com.android.exchange",
        "com.android.calendar",
        "com.android.contacts",
        "com.android.dialer",
        "com.android.mms",
        "com.android.camera",
        "com.android.gallery3d",
        "com.android.music",
        "com.android.soundrecorder",
        "com.android.calculator2",
        "com.android.deskclock",
        "com.android.certinstaller",
        "com.android.keychain",
        "com.android.pacprocessor",
        "com.android.printspooler",
        "com.android.vpndialogs",
        "com.android.wallpaperbackup",
        "com.android.wallpaper.livepicker",
        "com.android.htmlviewer",
        "com.android.managedprovisioning",
        "com.android.sharedstoragebackup",
        "com.android.backupconfirm",
        "com.android.cts.priv.ctsshim",
    }
    
    # Packages that are typically safe to disable (bloatware candidates)
    SAFE_TO_DISABLE_PATTERNS = [
        # Carrier bloatware
        "carrier", "verizon", "att", "tmobile", "sprint", "vodafone", "orange", "o2",
        # Manufacturer promo apps
        "promo", "trial", "demo", "shop", "store", "assistant", "help", "tips",
        # Gaming services (if not used)
        "games", "gaming", "playgames", "gamecenter",
        # Social media pre-installs
        "facebook", "instagram", "whatsapp", "twitter", "snapchat", "tiktok",
        # News/weather
        "news", "weather", "briefing", "flipboard",
        # Cloud/storage (if alternatives exist)
        "dropbox", "onedrive", "box", "evernote",
        # Manufacturer specific
        "bixby", "svoice", "shealth", "snote", "smemo",
    ]
    
    def __init__(self):
        pass
    
    def assess_package(self, pkg: PackageInfo, inventory: PackageInventory) -> PackageSafetyAssessment:
        """
        Assess the safety of performing operations on a package.
        
        Args:
            pkg: PackageInfo to assess.
            inventory: Full package inventory for context.
            
        Returns:
            PackageSafetyAssessment with safety level and allowed actions.
        """
        assessment = PackageSafetyAssessment(
            package_name=pkg.package_name,
            display_name=pkg.display_name,
            safety_level=SafetyLevel.UNKNOWN,
        )
        
        # Check critical packages first (exact match)
        if pkg.package_name in self.CRITICAL_PACKAGES:
            assessment.safety_level = SafetyLevel.CRITICAL
            assessment.allowed_actions = [ActionType.NONE]
            assessment.explanation = "This is a critical system package required for basic device operation."
            assessment.warnings.append("Disabling this package may render your TV unusable.")
            assessment.reversal_info = "Cannot be safely reversed without factory reset."
            assessment.confidence = 1.0
            return assessment
        
        # Check critical prefixes
        for prefix in self.CRITICAL_PREFIXES:
            if pkg.package_name.startswith(prefix):
                assessment.safety_level = SafetyLevel.CRITICAL
                assessment.allowed_actions = [ActionType.NONE]
                assessment.explanation = f"This package ({prefix}*) is part of the core Android system."
                assessment.warnings.append("Disabling system packages can cause instability or boot loops.")
                assessment.reversal_info = "Re-enable via ADB: pm enable " + pkg.package_name
                assessment.confidence = 0.95
                return assessment
        
        # Check protected packages
        if pkg.package_name in self.PROTECTED_PACKAGES:
            assessment.safety_level = SafetyLevel.PROTECTED
            assessment.allowed_actions = [ActionType.NONE]
            assessment.explanation = "This is a protected system application."
            assessment.warnings.append("Disabling may remove expected functionality.")
            assessment.reversal_info = "Re-enable via ADB: pm enable " + pkg.package_name
            assessment.confidence = 0.9
            return assessment

        if pkg.is_launcher or pkg.category == PackageCategory.LAUNCHER:
            assessment.safety_level = SafetyLevel.CRITICAL
            assessment.allowed_actions = [ActionType.NONE]
            assessment.explanation = "This is a home/launcher application."
            assessment.warnings.append("Disabling the launcher will leave you without a home screen!")
            assessment.reversal_info = "Requires ADB to re-enable: pm enable " + pkg.package_name
            assessment.confidence = 1.0
            return assessment
        
        # Check by category
        if pkg.category == PackageCategory.SYSTEM:
            assessment.safety_level = SafetyLevel.PROTECTED
            assessment.allowed_actions = [ActionType.NONE]
            assessment.explanation = "System package - function unknown but likely important."
            assessment.warnings.append("Unknown system packages should not be disabled.")
            assessment.reversal_info = "Re-enable via ADB: pm enable " + pkg.package_name
            assessment.confidence = 0.7
            return assessment
        
        if pkg.category == PackageCategory.SETTINGS:
            assessment.safety_level = SafetyLevel.CRITICAL
            assessment.allowed_actions = [ActionType.NONE]
            assessment.explanation = "Settings app is required for device configuration."
            assessment.warnings.append("Without Settings, you cannot change device options.")
            assessment.reversal_info = "Re-enable via ADB: pm enable " + pkg.package_name
            assessment.confidence = 1.0
            return assessment
        
        if pkg.category == PackageCategory.INPUT:
            assessment.safety_level = SafetyLevel.CRITICAL
            assessment.allowed_actions = [ActionType.NONE]
            assessment.explanation = "Input method/keyboard required for text entry."
            assessment.warnings.append("Disabling may prevent text input entirely.")
            assessment.reversal_info = "Re-enable via ADB: pm enable " + pkg.package_name
            assessment.confidence = 0.95
            return assessment
        
        if pkg.category == PackageCategory.NETWORK:
            assessment.safety_level = SafetyLevel.PROTECTED
            assessment.allowed_actions = [ActionType.NONE]
            assessment.explanation = "Network/connectivity service - may affect Wi-Fi, Bluetooth, or remote."
            assessment.warnings.append("Disabling may break network connectivity or remote control.")
            assessment.reversal_info = "Re-enable via ADB: pm enable " + pkg.package_name
            assessment.confidence = 0.8
            return assessment
        
        if pkg.category == PackageCategory.GOOGLE_SERVICES:
            assessment.safety_level = SafetyLevel.PROTECTED
            assessment.allowed_actions = [ActionType.NONE]
            assessment.explanation = "Google Play Services - required for many apps to function."
            assessment.warnings.append("Disabling will break apps that depend on Play Services.")
            assessment.reversal_info = "Re-enable via ADB: pm enable " + pkg.package_name
            assessment.confidence = 0.9
            return assessment
        
        if pkg.category == PackageCategory.MANUFACTURER:
            assessment.safety_level = SafetyLevel.CAUTION
            assessment.allowed_actions = [ActionType.DISABLE]
            assessment.explanation = "Manufacturer-specific service - may affect device-specific features."
            assessment.warnings.append("May disable TV-specific functions (picture modes, remote, etc.).")
            assessment.reversal_info = "Re-enable via ADB: pm enable " + pkg.package_name
            assessment.confidence = 0.6
            return assessment
        
        if pkg.category == PackageCategory.RECOMMENDATIONS:
            assessment.safety_level = SafetyLevel.SAFE
            assessment.allowed_actions = [ActionType.DISABLE]
            assessment.explanation = "Recommendation/ambient content service - disabling may reduce ads/suggestions."
            assessment.warnings.append("May reduce home screen recommendations and sponsored content.")
            assessment.reversal_info = "Re-enable via ADB: pm enable " + pkg.package_name
            assessment.confidence = 0.8
            return assessment
        
        if pkg.category == PackageCategory.SCREENSAVER:
            assessment.safety_level = SafetyLevel.SAFE
            assessment.allowed_actions = [ActionType.DISABLE]
            assessment.explanation = "Screensaver/ambient mode service."
            assessment.warnings.append("Disabling will stop screensaver/ambient display.")
            assessment.reversal_info = "Re-enable via ADB: pm enable " + pkg.package_name
            assessment.confidence = 0.8
            return assessment
        
        if pkg.category == PackageCategory.STREAMING:
            assessment.safety_level = SafetyLevel.SAFE
            assessment.allowed_actions = [ActionType.DISABLE, ActionType.UNINSTALL]
            assessment.explanation = "Streaming application - safe to disable if not used."
            assessment.warnings.append("You will lose access to this streaming service.")
            assessment.reversal_info = "Re-install from app store or re-enable via ADB."
            assessment.confidence = 0.9
            return assessment
        
        # User-installed apps
        if pkg.source == PackageSource.USER:
            assessment.safety_level = SafetyLevel.USER_APP
            assessment.allowed_actions = [ActionType.DISABLE, ActionType.UNINSTALL, ActionType.CLEAR_DATA]
            assessment.explanation = "User-installed application - safe to manage."
            assessment.warnings.append("Uninstalling will remove the app and its data.")
            assessment.reversal_info = "Re-install from Play Store."
            assessment.confidence = 0.95
            return assessment
        
        # Check safe-to-disable patterns
        name_lower = pkg.package_name.lower()
        for pattern in self.SAFE_TO_DISABLE_PATTERNS:
            if pattern in name_lower:
                assessment.safety_level = SafetyLevel.SAFE
                assessment.allowed_actions = [ActionType.DISABLE, ActionType.UNINSTALL]
                assessment.explanation = f"Likely bloatware/promo app (matches '{pattern}')."
                assessment.warnings.append("Disabling should be safe but verify you don't need it.")
                assessment.reversal_info = "Re-enable via ADB: pm enable " + pkg.package_name
                assessment.confidence = 0.7
                return assessment
        
        # Unknown package - err on side of caution
        assessment.safety_level = SafetyLevel.UNKNOWN
        assessment.allowed_actions = [ActionType.NONE]
        assessment.explanation = "Cannot determine package purpose - treating as potentially critical."
        assessment.warnings.append("Unknown packages should not be disabled without research.")
        assessment.reversal_info = "Re-enable via ADB: pm enable " + pkg.package_name
        assessment.confidence = 0.3
        return assessment
    
    def assess_all_packages(self, inventory: PackageInventory) -> dict[str, PackageSafetyAssessment]:
        """Assess all packages in inventory."""
        assessments = {}
        for pkg in inventory.get_all_packages():
            assessments[pkg.package_name] = self.assess_package(pkg, inventory)
        return assessments
    
    def get_disable_candidates(self, inventory: PackageInventory, 
                                min_confidence: float = 0.7) -> list[PackageSafetyAssessment]:
        """Get packages that are safe to disable."""
        assessments = self.assess_all_packages(inventory)
        candidates = []
        for pkg_name, assessment in assessments.items():
            if assessment.can_disable() and assessment.confidence >= min_confidence:
                candidates.append(assessment)
        return candidates
    
    def get_uninstall_candidates(self, inventory: PackageInventory,
                                  min_confidence: float = 0.7) -> list[PackageSafetyAssessment]:
        """Get packages that are safe to uninstall."""
        assessments = self.assess_all_packages(inventory)
        candidates = []
        for pkg_name, assessment in assessments.items():
            if assessment.can_uninstall() and assessment.confidence >= min_confidence:
                candidates.append(assessment)
        return candidates


def create_package_classifier() -> PackageClassifier:
    """Factory function to create a PackageClassifier."""
    return PackageClassifier()