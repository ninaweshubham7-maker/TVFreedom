"""
Recommendation Engine - Safe improvement suggestions for TV Freedom.

This module provides a recommendation engine that analyzes device state
and suggests safe, reversible improvements with full transparency.
"""

from dataclasses import dataclass, field
from typing import Optional
from enum import Enum
from pathlib import Path
import json

from adb_manager import ADBManager, ADBState
from device_identification import DeviceIdentifier, DeviceIdentity
from diagnostics import DiagnosticsEngine, DiagnosticResult
from package_inventory import PackageInventory, PackageInfo, PackageCategory, PackageSource
from package_classifier import PackageClassifier, PackageSafetyAssessment, SafetyLevel, ActionType
from backup_manager import BackupManager, BackupType
from action_history import ActionHistory, ActionType as HistoryActionType


class RecommendationPriority(Enum):
    """Priority level for recommendations."""
    CRITICAL = "critical"       # Security/stability issue
    HIGH = "high"               # Significant improvement
    MEDIUM = "medium"           # Moderate improvement
    LOW = "low"                 # Minor improvement
    INFO = "info"               # Informational only


class RecommendationCategory(Enum):
    """Category of recommendation."""
    STORAGE = "storage"              # Free up storage
    PRIVACY = "privacy"              # Privacy improvement
    PERFORMANCE = "performance"      # Performance improvement
    AD_REDUCTION = "ad_reduction"    # Reduce ads/recommendations
    BLOATWARE = "bloatware"          # Remove unwanted apps
    SETTINGS = "settings"            # Settings optimization
    LAUNCHER = "launcher"            # Launcher customization
    MAINTENANCE = "maintenance"      # System maintenance


@dataclass
class Recommendation:
    """A single improvement recommendation."""
    recommendation_id: str
    title: str
    description: str
    category: RecommendationCategory
    priority: RecommendationPriority
    
    # What it changes
    what_changes: str
    why_it_helps: str
    what_you_gain: str
    what_you_lose: str
    
    # Reversibility
    is_reversible: bool
    how_to_undo: str
    
    # Device compatibility
    compatible: bool
    compatibility_notes: list[str] = field(default_factory=list)
    
    # Evidence and confidence
    evidence: list[str] = field(default_factory=list)
    confidence: float = 0.0  # 0.0 to 1.0
    
    # Associated data
    target_packages: list[str] = field(default_factory=list)
    target_settings: dict = field(default_factory=dict)
    required_actions: list[ActionType] = field(default_factory=list)
    
    # Safety
    safety_level: SafetyLevel = SafetyLevel.UNKNOWN
    warnings: list[str] = field(default_factory=list)
    
    def to_dict(self) -> dict:
        return {
            "recommendation_id": self.recommendation_id,
            "title": self.title,
            "description": self.description,
            "category": self.category.value,
            "priority": self.priority.value,
            "what_changes": self.what_changes,
            "why_it_helps": self.why_it_helps,
            "what_you_gain": self.what_you_gain,
            "what_you_lose": self.what_you_lose,
            "is_reversible": self.is_reversible,
            "how_to_undo": self.how_to_undo,
            "compatible": self.compatible,
            "compatibility_notes": self.compatibility_notes,
            "evidence": self.evidence,
            "confidence": self.confidence,
            "target_packages": self.target_packages,
            "target_settings": self.target_settings,
            "required_actions": [a.value for a in self.required_actions],
            "safety_level": self.safety_level.value,
            "warnings": self.warnings,
        }


class RecommendationEngine:
    """Generates safe improvement recommendations based on device analysis."""
    
    def __init__(self, adb_manager: ADBManager):
        self.adb_manager = adb_manager
        self.device_identifier = DeviceIdentifier(adb_manager)
        self.diagnostics_engine = DiagnosticsEngine(adb_manager)
        self.package_inventory = PackageInventory(adb_manager)
        self.package_classifier = PackageClassifier()
        self.backup_manager = BackupManager(adb_manager)
        self.action_history = ActionHistory()
    
    def generate_recommendations(self) -> list[Recommendation]:
        """
        Generate all applicable recommendations for the current device.
        
        Returns:
            List of Recommendation objects, sorted by priority.
        """
        if not self.adb_manager.connected_device or \
           self.adb_manager.connection_state != ADBState.CONNECTED:
            return []
        
        recommendations = []
        
        # Refresh package inventory
        self.package_inventory.refresh()
        
        # Get device identity
        device_identity = self.device_identifier.identify_device()
        compatibility = self.device_identifier.get_compatibility_summary(device_identity)
        
        # Get package assessments
        assessments = self.package_classifier.assess_all_packages(self.package_inventory)
        
        # 1. Storage recommendations
        recommendations.extend(self._generate_storage_recommendations(
            device_identity, assessments))
        
        # 2. Ad/recommendation reduction
        recommendations.extend(self._generate_ad_reduction_recommendations(
            device_identity, assessments))
        
        # 3. Bloatware removal
        recommendations.extend(self._generate_bloatware_recommendations(
            device_identity, assessments))
        
        # 4. Privacy settings
        recommendations.extend(self._generate_privacy_recommendations(
            device_identity))
        
        # 5. Performance settings
        recommendations.extend(self._generate_performance_recommendations(
            device_identity))
        
        # 6. Launcher recommendations
        recommendations.extend(self._generate_launcher_recommendations(
            device_identity, assessments))
        
        # 7. Maintenance recommendations
        recommendations.extend(self._generate_maintenance_recommendations(
            device_identity))
        
        # Sort by priority
        priority_order = {
            RecommendationPriority.CRITICAL: 0,
            RecommendationPriority.HIGH: 1,
            RecommendationPriority.MEDIUM: 2,
            RecommendationPriority.LOW: 3,
            RecommendationPriority.INFO: 4,
        }
        
        recommendations.sort(key=lambda r: priority_order[r.priority])
        
        return recommendations
    
    def _generate_storage_recommendations(self, identity: DeviceIdentity,
                                           assessments: dict) -> list[Recommendation]:
        """Generate storage-related recommendations."""
        recs = []
        
        if identity.storage_free_gb < 1.0:
            recs.append(Recommendation(
                recommendation_id="storage_critical",
                title="Critical Storage Space",
                description=f"Only {identity.storage_free_gb:.1f} GB free. Device performance and updates may fail.",
                category=RecommendationCategory.STORAGE,
                priority=RecommendationPriority.CRITICAL,
                what_changes="Identify and remove large unused apps, clear caches, move data to external storage.",
                why_it_helps="Low storage causes app crashes, failed updates, and system instability.",
                what_you_gain="Stable operation, ability to install updates, better performance.",
                what_you_lose="Some cached data, potentially unused apps.",
                is_reversible=True,
                how_to_undo="Re-install removed apps from Play Store. Caches rebuild automatically.",
                compatible=True,
                compatibility_notes=["Requires sufficient storage for backup before changes"],
                evidence=[f"Free space: {identity.storage_free_gb:.1f} GB ({identity.storage_free_percent:.1f}%)"],
                confidence=0.95,
                target_packages=[],
                required_actions=[ActionType.DISABLE, ActionType.CLEAR_DATA],
                safety_level=SafetyLevel.CAUTION,
                warnings=["Do not disable system apps to free space. Only target user apps and clearable caches."],
            ))
        
        elif identity.storage_free_gb < 2.0:
            recs.append(Recommendation(
                recommendation_id="storage_low",
                title="Low Storage Space",
                description=f"Only {identity.storage_free_gb:.1f} GB free. Consider cleaning up.",
                category=RecommendationCategory.STORAGE,
                priority=RecommendationPriority.HIGH,
                what_changes="Review installed apps, clear caches, remove unused apps.",
                why_it_helps="Prevents future storage issues and maintains performance.",
                what_you_gain="More free space, room for updates and new apps.",
                what_you_lose="Cached data, unused apps.",
                is_reversible=True,
                how_to_undo="Re-install apps from Play Store.",
                compatible=True,
                evidence=[f"Free space: {identity.storage_free_gb:.1f} GB ({identity.storage_free_percent:.1f}%)"],
                confidence=0.85,
                target_packages=[],
                required_actions=[ActionType.DISABLE, ActionType.CLEAR_DATA],
                safety_level=SafetyLevel.SAFE,
                warnings=[],
            ))
        
        return recs
    
    def _generate_ad_reduction_recommendations(self, identity: DeviceIdentity,
                                                assessments: dict) -> list[Recommendation]:
        """Generate ad/recommendation reduction recommendations."""
        recs = []
        
        # Find recommendation packages
        recommendation_packages = []
        for pkg_name, assessment in assessments.items():
            if assessment.safety_level == SafetyLevel.SAFE and \
               "recommendation" in assessment.explanation.lower() or \
               "ambient" in assessment.explanation.lower():
                recommendation_packages.append((pkg_name, assessment))
        
        if recommendation_packages:
            pkg_names = [p[0] for p in recommendation_packages]
            recs.append(Recommendation(
                recommendation_id="disable_recommendations",
                title="Disable Recommendation Services",
                description="Disable services that show sponsored content and recommendations on home screen.",
                category=RecommendationCategory.AD_REDUCTION,
                priority=RecommendationPriority.HIGH,
                what_changes=f"Disable {len(pkg_names)} recommendation/ambient content services.",
                why_it_helps="Removes sponsored rows, app recommendations, and promotional content from home screen.",
                what_you_gain="Cleaner home screen, fewer ads, reduced background data usage.",
                what_you_lose="Personalized recommendations, 'Continue watching' rows, app suggestions.",
                is_reversible=True,
                how_to_undo="Re-enable via ADB: pm enable <package> for each disabled service.",
                compatible=identity.platform_type in ("android_tv", "google_tv"),
                compatibility_notes=["May not work on Fire TV or heavily customized launchers"],
                evidence=[f"Found {len(pkg_names)} recommendation services"],
                confidence=0.85,
                target_packages=pkg_names,
                required_actions=[ActionType.DISABLE],
                safety_level=SafetyLevel.SAFE,
                warnings=["Does not block ads within streaming apps (YouTube, etc.). Use Private DNS for broader ad blocking."],
            ))
        
        # Private DNS recommendation
        recs.append(Recommendation(
            recommendation_id="private_dns",
            title="Configure Private DNS (Ad Blocking)",
            description="Use Private DNS with an ad-blocking provider to block ads system-wide.",
            category=RecommendationCategory.AD_REDUCTION,
            priority=RecommendationPriority.MEDIUM,
            what_changes="Set Private DNS hostname to an ad-blocking provider (e.g., dns.adguard.com).",
            why_it_helps="Blocks ads and trackers at DNS level across all apps and browsers.",
            what_you_gain="Reduced ads in apps, browsers, and system UI. Better privacy.",
            what_you_lose="Some legitimate content may be blocked. May affect some apps/websites.",
            is_reversible=True,
            how_to_undo="Settings → Network → Private DNS → Off (or Automatic).",
            compatible=identity.api_level >= 28,  # Android 9+
            compatibility_notes=["Requires Android 9 (API 28) or later", "Does not block YouTube ads reliably"],
            evidence=["Android 9+ supports Private DNS", "DNS-based blocking works system-wide"],
            confidence=0.7,
            target_packages=[],
            target_settings={"global.private_dns_mode": "hostname", "global.private_dns_specifier": "dns.adguard.com"},
            required_actions=[HistoryActionType.CHANGE_SETTING],
            safety_level=SafetyLevel.CAUTION,
            warnings=["Private DNS does not reliably block YouTube ads", "May affect banking apps, corporate networks", "Test thoroughly before relying on it"],
        ))
        
        return recs
    
    def _generate_bloatware_recommendations(self, identity: DeviceIdentity,
                                             assessments: dict) -> list[Recommendation]:
        """Generate bloatware removal recommendations."""
        recs = []
        
        # Find safe-to-disable packages
        safe_packages = []
        for pkg_name, assessment in assessments.items():
            if assessment.can_disable() and assessment.confidence >= 0.7:
                pkg = self.package_inventory.get_package(pkg_name)
                if pkg and pkg.source in (PackageSource.USER, PackageSource.UPDATED_SYSTEM):
                    safe_packages.append((pkg_name, assessment))
        
        if safe_packages:
            pkg_names = [p[0] for p in safe_packages]
            recs.append(Recommendation(
                recommendation_id="remove_bloatware",
                title="Remove Unwanted Pre-installed Apps",
                description=f"Disable or uninstall {len(safe_packages)} identified bloatware/promo apps.",
                category=RecommendationCategory.BLOATWARE,
                priority=RecommendationPriority.MEDIUM,
                what_changes=f"Disable {len(safe_packages)} unused pre-installed applications.",
                why_it_helps="Frees storage, reduces background activity, removes unwanted notifications.",
                what_you_gain="More storage, less background activity, cleaner app drawer.",
                what_you_lose="Access to those specific apps (can be re-enabled).",
                is_reversible=True,
                how_to_undo="Re-enable via ADB: pm enable <package> for each.",
                compatible=True,
                compatibility_notes=["Only targets apps classified as safe to disable"],
                evidence=[f"Identified {len(safe_packages)} candidate apps"],
                confidence=0.8,
                target_packages=pkg_names,
                required_actions=[ActionType.DISABLE, ActionType.UNINSTALL],
                safety_level=SafetyLevel.SAFE,
                warnings=["Review each app before disabling. Some manufacturer apps may be useful."],
            ))
        
        return recs
    
    def _generate_privacy_recommendations(self, identity: DeviceIdentity) -> list[Recommendation]:
        """Generate privacy-related recommendations."""
        recs = []
        
        # Usage stats access
        recs.append(Recommendation(
            recommendation_id="privacy_usage_stats",
            title="Review Usage Stats Access",
            description="Check which apps have permission to access your usage statistics.",
            category=RecommendationCategory.PRIVACY,
            priority=RecommendationPriority.MEDIUM,
            what_changes="Review and revoke usage stats access for unneeded apps.",
            why_it_helps="Prevents apps from tracking which apps you use and when.",
            what_you_gain="Better privacy, less data collection about your habits.",
            what_you_lose="Some features like screen time tracking may not work for those apps.",
            is_reversible=True,
            how_to_undo="Settings → Apps → Special access → Usage access → Re-enable.",
            compatible=True,
            evidence=["Usage stats permission allows detailed app usage tracking"],
            confidence=0.7,
            target_packages=[],
            required_actions=[HistoryActionType.REVOKE_PERMISSION],
            safety_level=SafetyLevel.SAFE,
            warnings=["May affect digital wellbeing features"],
        ))
        
        # Location access
        recs.append(Recommendation(
            recommendation_id="privacy_location",
            title="Review Location Permissions",
            description="Review which apps have location access and restrict to 'While in use' or deny.",
            category=RecommendationCategory.PRIVACY,
            priority=RecommendationPriority.MEDIUM,
            what_changes="Change location permissions from 'Always' to 'While in use' or 'Deny'.",
            why_it_helps="Prevents background location tracking by apps that don't need it.",
            what_you_gain="Better privacy, improved battery life.",
            what_you_lose="Some location-based features (weather, maps) may require manual refresh.",
            is_reversible=True,
            how_to_undo="Settings → Location → App permissions → Change per app.",
            compatible=True,
            evidence=["Many apps request location unnecessarily"],
            confidence=0.75,
            target_packages=[],
            required_actions=[HistoryActionType.REVOKE_PERMISSION],
            safety_level=SafetyLevel.SAFE,
            warnings=["Critical apps (maps, ride-sharing) need location access"],
        ))
        
        return recs
    
    def _generate_performance_recommendations(self, identity: DeviceIdentity) -> list[Recommendation]:
        """Generate performance optimization recommendations."""
        recs = []
        
        # Animation scales
        recs.append(Recommendation(
            recommendation_id="reduce_animations",
            title="Reduce Animation Scales",
            description="Speed up UI transitions by reducing or disabling animation scales.",
            category=RecommendationCategory.PERFORMANCE,
            priority=RecommendationPriority.LOW,
            what_changes="Set window, transition, and animator duration scales to 0.5x or off.",
            why_it_helps="Makes UI feel snappier, reduces GPU load.",
            what_you_gain="Faster perceived performance, smoother navigation.",
            what_you_lose="Visual polish of transitions.",
            is_reversible=True,
            how_to_undo="Settings → Developer options → Animation scales → Reset to 1x.",
            compatible=identity.api_level >= 21,
            evidence=["Animation scales directly affect UI rendering time"],
            confidence=0.8,
            target_packages=[],
            target_settings={
                "system.window_animation_scale": "0.5",
                "system.transition_animation_scale": "0.5",
                "system.animator_duration_scale": "0.5",
            },
            required_actions=[HistoryActionType.CHANGE_SETTING],
            safety_level=SafetyLevel.SAFE,
            warnings=["Purely cosmetic change. No functional impact."],
        ))
        
        # Background process limit
        recs.append(Recommendation(
            recommendation_id="background_limit",
            title="Limit Background Processes",
            description="Restrict maximum number of background processes to free memory.",
            category=RecommendationCategory.PERFORMANCE,
            priority=RecommendationPriority.LOW,
            what_changes="Set background process limit in Developer Options.",
            why_it_helps="Prevents memory pressure from too many background apps.",
            what_you_gain="More memory for foreground app, fewer reloads.",
            what_you_lose="Apps may restart instead of resuming from background.",
            is_reversible=True,
            how_to_undo="Settings → Developer options → Background process limit → Standard.",
            compatible=True,
            evidence=["Background process limit affects memory management"],
            confidence=0.6,
            target_packages=[],
            target_settings={},
            required_actions=[HistoryActionType.CHANGE_SETTING],
            safety_level=SafetyLevel.CAUTION,
            warnings=["May cause apps to reload more often. Test with your usage patterns."],
        ))
        
        return recs
    
    def _generate_launcher_recommendations(self, identity: DeviceIdentity,
                                            assessments: dict) -> list[Recommendation]:
        """Generate launcher-related recommendations."""
        recs = []
        
        if identity.default_launcher != "Unknown":
            recs.append(Recommendation(
                recommendation_id="launcher_info",
                title="Current Launcher Information",
                description=f"Current home app: {identity.default_launcher}",
                category=RecommendationCategory.LAUNCHER,
                priority=RecommendationPriority.INFO,
                what_changes="Informational only - no changes made.",
                why_it_helps="Knowing your current launcher helps assess customization options.",
                what_you_gain="Awareness of current launcher capabilities and limitations.",
                what_you_lose="Nothing.",
                is_reversible=True,
                how_to_undo="N/A",
                compatible=True,
                evidence=[f"Default launcher: {identity.default_launcher}"],
                confidence=1.0,
                target_packages=[],
                required_actions=[],
                safety_level=SafetyLevel.SAFE,
                warnings=[],
            ))
        
        # Third-party launcher suggestion
        if identity.platform_type in ("android_tv", "google_tv") and identity.api_level >= 29:
            recs.append(Recommendation(
                recommendation_id="third_party_launcher",
                title="Consider Third-Party Launcher",
                description="Install a custom launcher (e.g., FLauncher, ATV Launcher) for ad-free experience.",
                category=RecommendationCategory.LAUNCHER,
                priority=RecommendationPriority.INFO,
                what_changes="Install and set a third-party launcher as default home app.",
                why_it_helps="Removes stock launcher ads, recommendations, and sponsored content entirely.",
                what_you_gain="Complete control over home screen, no ads, customizable layout.",
                what_you_lose="Stock launcher features (voice search integration, etc.). Some widgets may not work.",
                is_reversible=True,
                how_to_undo="Settings → Apps → Default apps → Home app → Select stock launcher.",
                compatible=True,
                compatibility_notes=["Requires Android 10+", "Not all launchers work on all devices", "Test before committing"],
                evidence=["Third-party launchers provide ad-free experience on compatible devices"],
                confidence=0.6,
                target_packages=[],
                required_actions=[],
                safety_level=SafetyLevel.CAUTION,
                warnings=["Not all launchers support TV remote navigation", "May require mouse/keyboard for setup", "Stock launcher cannot be uninstalled, only replaced"],
            ))
        
        return recs
    
    def _generate_maintenance_recommendations(self, identity: DeviceIdentity) -> list[Recommendation]:
        """Generate maintenance recommendations."""
        recs = []
        
        # Backup recommendation
        recs.append(Recommendation(
            recommendation_id="create_backup",
            title="Create Device Backup",
            description="Create a complete backup before making any changes.",
            category=RecommendationCategory.MAINTENANCE,
            priority=RecommendationPriority.HIGH,
            what_changes="Creates a full device state backup (settings, packages, diagnostics).",
            why_it_helps="Enables full recovery if something goes wrong.",
            what_you_gain="Peace of mind, ability to undo any changes.",
            what_you_lose="Small amount of storage for backup file.",
            is_reversible=True,
            how_to_undo="N/A - backup is read-only.",
            compatible=True,
            evidence=["Backups are essential for safe modifications"],
            confidence=1.0,
            target_packages=[],
            required_actions=[],
            safety_level=SafetyLevel.SAFE,
            warnings=["Backup does not include user data (photos, downloads). Use Google Backup for that."],
        ))
        
        return recs
    
    def get_recommendation_summary(self, recommendations: list[Recommendation]) -> dict:
        """Get summary of recommendations."""
        by_priority = {}
        by_category = {}
        
        for rec in recommendations:
            by_priority[rec.priority.value] = by_priority.get(rec.priority.value, 0) + 1
            by_category[rec.category.value] = by_category.get(rec.category.value, 0) + 1
        
        return {
            "total": len(recommendations),
            "by_priority": by_priority,
            "by_category": by_category,
            "reversible_count": sum(1 for r in recommendations if r.is_reversible),
            "high_confidence": sum(1 for r in recommendations if r.confidence >= 0.8),
        }


def create_recommendation_engine(adb_manager: ADBManager) -> RecommendationEngine:
    """Factory function to create a RecommendationEngine."""
    return RecommendationEngine(adb_manager)