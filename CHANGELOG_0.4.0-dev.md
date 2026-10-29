# TV Freedom 0.4.0-dev — Feature Preview

## Added
- Dedicated ADB package-action API, separate from read-only shell diagnostics.
- Package mutations are restricted to disable, enable, and uninstall actions with package-name validation and explicit selected-device targeting.
- Installed Apps UI now exposes confirmed disable/enable actions through the existing Action Engine, plus uninstall for eligible user-installed apps only.
- Added a native Android TV launcher source project under `launcher-android/` with a minimal app grid and HOME intent.
- Added a Clean Launcher page to guide building and installing the specific launcher APK once it has been built.

## Safety and limitations
- System-critical package protection remains classifier-driven; never disable launchers, System UI, settings, input, Google core services, or unknown packages manually.
- The local pre-action backup is a package/device-state snapshot, not a backup of APK binaries or app-private data.
- A locally built debug APK is currently present at `launcher-android/app/build/outputs/apk/debug/app-debug.apk`; this is not a release APK and has not been tested on physical TV hardware.
- Full Streamlit integration tests could not run in the Linux build environment because Streamlit is not installed there. The non-integration test suite and Python syntax checks pass in this environment.
