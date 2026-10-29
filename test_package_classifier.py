from unittest.mock import Mock

from package_classifier import ActionType, PackageClassifier, SafetyLevel
from package_inventory import PackageCategory, PackageInfo, PackageInventory, PackageSource


def test_google_tv_launcher_is_classified_as_critical():
    package = PackageInfo(
        package_name="com.google.android.apps.tv.launcherx",
        display_name="Google TV",
        source=PackageSource.SYSTEM,
    )
    inventory = PackageInventory(Mock())

    inventory._classify_package(package)
    assessment = PackageClassifier().assess_package(package, inventory)

    assert package.category == PackageCategory.LAUNCHER
    assert assessment.safety_level == SafetyLevel.CRITICAL
    assert not assessment.can_disable()
    assert not assessment.can_uninstall()


def test_launcher_flag_stays_critical_if_category_is_misclassified():
    package = PackageInfo(
        package_name="com.example.tv.home",
        display_name="TV Home",
        category=PackageCategory.STREAMING,
        source=PackageSource.SYSTEM,
        is_launcher=True,
    )

    assessment = PackageClassifier().assess_package(package, Mock())

    assert assessment.safety_level == SafetyLevel.CRITICAL
    assert ActionType.DISABLE not in assessment.allowed_actions
    assert ActionType.UNINSTALL not in assessment.allowed_actions
