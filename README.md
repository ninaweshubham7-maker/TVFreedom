# TV Freedom

A Windows application that helps non-technical users safely diagnose and customise compatible Android TV and Google TV devices.

> **Tagline:** Take control of your smart TV.

## Current Status

**Version 0.4.0-dev (Feature Preview)** — This version includes real ADB connectivity for compatible Android TV and Google TV devices, supporting USB and network connections, along with device analysis, package safety classification, recommendations, performance monitoring, state snapshots, and activity logging. It is an early preview: physical-TV compatibility and the Android launcher have not been validated on hardware.

**NEW in 0.3.0:** 📦 **Bundled ADB** — No manual ADB installation required! TV Freedom includes Android SDK Platform Tools.  
**NEW in 0.3.0:** 📱 **Installed Apps & Safety Classification** — View all installed packages with safety assessments!  
**NEW in 0.3.0:** ✨ **Recommendations Engine** — Get personalized, reversible improvement suggestions!  
**NEW in 0.3.0:** 📊 **Performance Monitor** — Track CPU, memory, storage, battery, and thermal metrics!  
**NEW in 0.3.0:** 💾 **Backups & Recovery** — Create full device state backups before any changes!  
**NEW in 0.3.0:** 📜 **Safety & Activity Log** — Complete audit trail of all device operations!

**Also included:** 🔌 **Real ADB Integration** — Connect physical devices via USB or Wi-Fi!  
**Also included:** 🧪 **Virtual TV Demo Mode** — Develop and test without a physical television!

## Features (Implemented)

- 📦 **Bundled ADB** — Android SDK Platform Tools included; no manual download, extraction, or PATH configuration needed
- 🔌 **ADB Connectivity** — USB and network (Wi-Fi/Ethernet) connections to real devices
- 📋 **Device Diagnostics** — Comprehensive device identification (manufacturer, model, Android version, storage, CPU, build fingerprint, screen resolution, platform type, compatibility scoring)
- 📱 **Installed Apps & Safety Classification** — Complete package inventory with safety levels (Critical, Protected, Caution, Safe, User App) and allowed actions
- ✨ **Recommendations Engine** — Personalized, reversible improvement suggestions (storage, ad reduction, bloatware, privacy, performance, launcher, maintenance) with full transparency
- 📊 **Performance Monitor** — Read-only metrics collection (CPU, memory, storage, uptime, battery, thermal zones) with historical tracking
- 💾 **Backups & Recovery** — Full device state backups (identity, diagnostics, packages, assessments, settings) with selective restore
- 📜 **Safety & Activity Log** — Complete audit trail of all device-changing operations with reversal instructions
- 🧪 **Virtual TV Demo Mode** — Six simulated device profiles for testing without hardware
- 🛡️ **Safety First** — Read-only diagnostics plus separately allowlisted package actions with explicit confirmation
- 🧰 **Package Actions (early preview)** — Disable/enable eligible packages; uninstall is restricted to eligible user-installed apps
- 🎨 **Clean Launcher (debug preview)** — Native Android launcher source and a locally built debug APK are present under `launcher-android/`; the APK is also included in the verified Windows distribution. It is not a release build or hardware-validated.

## Feature Preview and Remaining Work

- 🎨 **Clean Launcher** — Android source and a locally built debug APK are included. The APK has not been validated on physical TV hardware and does not automatically replace the default launcher.
- 📦 **Package Management** — Guarded disable/enable actions are available with explicit confirmation and a pre-action snapshot; uninstall is restricted to eligible user-installed apps.
- 🔧 **System Tweaks** — Adjust hidden settings for better performance
- 📊 **Resource Monitoring** — View real-time CPU, memory, and network usage (foundation implemented)
- 💾 **Pre-action Snapshots** — Package/device-state snapshots are created before package changes; they do not contain APK binaries or app-private data.
- 🔄 **Package Recovery** — Re-enable eligible packages that were disabled; this is not a full-device restore.

## Safety First

TV Freedom is built on core safety principles:

1. **Read-only by default** — inventory and diagnostics do not modify the TV; package actions require a separate explicit confirmation
2. **System package protection** — Critical packages are never listed for removal
3. **Automatic backups** — Created before every change
4. **Compatibility verification** — Checks device support before suggesting changes
5. **Transparent operations** — Shows exactly what will change and how to undo it

## Requirements

- Windows 10 or 11
- Python 3.11 or newer
- Android TV or Google TV device (for real ADB features)
- **No physical TV required for Demo Mode**
- **No NVIDIA API key, internet access, or paid services required**
- **No manual ADB installation required** — TV Freedom includes bundled Platform Tools

## Installation

```powershell
# Clone or navigate to the project directory
cd TVFreedom

# Create a virtual environment (recommended)
python -m venv .venv
.\.venv\Scripts\Activate.ps1

# Install dependencies
pip install -r requirements.txt
```

### ADB (No Manual Installation Required)

TV Freedom **includes bundled Android SDK Platform Tools** (`adb.exe`, `AdbWinApi.dll`, `AdbWinUsbApi.dll`). 
The bundled ADB is used automatically — no download, extraction, or PATH configuration needed.

If for any reason the bundled ADB is unavailable, TV Freedom will fall back to a system-installed ADB (if present in PATH). 
You can also manually install ADB via:

**Option 1: winget (Recommended)**
```powershell
winget install Google.AndroidSDKPlatformTools
```

**Option 2: Chocolatey**
```powershell
choco install adb
```

**Option 3: Manual Download**
1. Download from: https://developer.android.com/studio/releases/platform-tools
2. Extract to a folder (e.g., `C:\platform-tools`)
3. Add to System PATH:
   - Press `Win+S`, search "Environment Variables"
   - Edit "Path" under System Variables
   - Add the folder path (e.g., `C:\platform-tools`)
4. Restart terminal and verify: `adb version`

## Running the Application

```powershell
# From the project directory with virtual environment activated
streamlit run app.py
```

When started this way, the application opens in your default web browser at `http://localhost:8501`.

### Building a Windows distribution

The project can be packaged as a one-folder Windows desktop application using
PyInstaller. It runs the existing Streamlit app on loopback and displays it in
a Microsoft Edge app window without tabs or an address bar. Microsoft Edge must
be installed. The wrapper launches the installed Edge browser in app mode; this
is not an embedded WebView and does not use or require the Microsoft Edge
WebView2 Runtime. The bundled Platform Tools and launcher files remain beside
the executable.

```powershell
python -m pip install ".[packaging]"
.\packaging\build_windows.ps1
```

The executable is written to `dist\TVFreedomDesktop\TVFreedomDesktop.exe`, and
the distributable archive is
`dist\TVFreedom-0.4.0-dev-desktop-windows-x64.zip`. Run the executable from a
writable folder; it opens the app in a separate, chrome-free Edge window. The
packaged app is a portable one-folder distribution, not an installer, and the
executable is unsigned. Streamlit logs are written to
`%LOCALAPPDATA%\TVFreedom\logs\desktop-launcher.log`. Its server binds only to
loopback, so the interface is not exposed to the local network.

The Windows distribution includes the locally built launcher debug APK at
`launcher-android\app\build\outputs\apk\debug\app-debug.apk`. This is a
development artifact, not a release APK, and has not been tested on physical TV
hardware.

## Virtual TV Demo Mode

TV Freedom includes a **Virtual TV Demo Mode** for development and testing without a physical television.

### Enabling Demo Mode

1. Launch the application: `streamlit run app.py`
2. In the sidebar, toggle **🧪 Enable Virtual TV Demo Mode**
3. A **Demo Diagnostics** page will appear in the navigation

### Simulated Device Profiles

Demo Mode provides six pre-configured simulated profiles:

| Profile | Description | Compatibility |
|---------|-------------|---------------|
| **Compatible Android TV** | Modern Sony Android TV (Android 12) | ✅ Fully Compatible |
| **Compatible Google TV** | Chromecast with Google TV 4K (Android 13) | ✅ Compatible (low storage warning) |
| **Older Android TV** | TCL Android TV running Android 9 | ❌ Incompatible (API 28 < 29) |
| **Low-Storage Device** | Xiaomi Mi Box S with 512 MB free | ✅ Compatible (critical storage warnings) |
| **ADB Disabled** | NVIDIA SHIELD with USB debugging off | ❌ Connection fails |
| **Unsupported Device** | Amazon Fire TV Stick (Fire OS) | ❌ Incompatible (manufacturer restrictions) |

### Using Demo Diagnostics

1. Select a profile from the **Simulated Device Profile** dropdown
2. Click **🔌 Connect** to simulate an ADB connection
3. Click **🔍 Run Diagnostic** to generate simulated device information
4. All data is clearly marked with **🧪 DEMO DATA** badges
5. Compatibility warnings and connection errors are simulated realistically

### Demo Mode Guarantees

- ✅ **Never executes real ADB commands** — guarded by `DemoModeGuard`
- ✅ **Separate simulation logic** — `demo_simulator.py` is isolated from real device code
- ✅ **All data marked** — every diagnostic value includes `🧪 DEMO DATA` marker
- ✅ **No internet required** — works completely offline
- ✅ **No API keys needed** — purely local simulation

## Real Device Connection (ADB)

### USB Connection

1. **Enable Developer Options** on TV: Settings → System → About → Click **Build** 7 times
2. **Enable USB Debugging**: Settings → System → Developer Options → **USB debugging** ON
3. **Connect USB cable** (data-capable, not charge-only) from TV to Windows PC
4. **Authorize** on TV: Check "Always allow from this computer" → OK
5. In TV Freedom: Go to **Connect Your TV** → Click **🔄 Refresh USB Devices** → Click **Connect**

### Network Connection (Wi-Fi/Ethernet)

1. **Enable Developer Options** on TV (same as above)
2. **Enable Wireless Debugging** or **ADB over network** in Developer Options
   - Location varies by manufacturer: may be called "ADB over network", "Wireless debugging", or similar
3. **Note the IP address and port** shown on TV (typically port 5555)
4. In TV Freedom: Go to **Connect Your TV** → Enter IP and Port in **Network Connection** section → Click **Connect**
5. **Authorize** on TV if prompted

### Supported Connection States

TV Freedom clearly shows connection status:

| State | Meaning | Action |
|-------|---------|--------|
| **ADB Unavailable** | Bundled ADB missing; no system ADB | Re-install TV Freedom |
| **No Device** | No devices detected | Connect USB / check network |
| **Unauthorized** | TV needs authorization | Accept prompt on TV screen |
| **Offline** | Device not responding | Check cable / wake TV / restart ADB |
| **Connected** | Ready for diagnostics | Run diagnostics |
| **Error** | Connection failed | Check IP/port/firewall |

### Disconnecting

Click the **🔌 Disconnect** button on the Connect Your TV page to cleanly disconnect.

## Running Automated Tests

The project includes comprehensive test suites for Demo Mode, ADB Manager, and UI integration.

```powershell
# Install test dependencies (already in requirements.txt)
pip install -r requirements.txt

# Run all tests with verbose output
python -m pytest -v

# Run tests with coverage report
python -m pytest --cov=demo_simulator --cov=adb_manager --cov-report=term-missing

# Run a specific test
python -m pytest test_adb_manager.py::test_connect_usb_success -v

# Run only integration tests
python -m pytest test_app_integration.py -v

# Run only bundled ADB tests
python -m pytest test_adb_bundled.py -v
```

### Test Coverage

**Demo Simulator (30 tests):**
- ✅ All 6 simulated profiles exist with correct structure
- ✅ Connection success/failure for each profile type
- ✅ Diagnostic data generation with DEMO DATA markers
- ✅ Compatibility warnings for each scenario
- ✅ Demo Mode Guard prevents real ADB operations
- ✅ Simulator state management (connect/disconnect/diagnostic)
- ✅ Profile-specific fields (screen resolution, CPU, build ID)
- ✅ Full integration flows for compatible, incompatible, and failing devices

**ADB Manager (40+ tests with mocked subprocess):**
- ✅ ADB availability detection
- ✅ USB device discovery (authorized, unauthorized, offline, multiple)
- ✅ USB connection (success, unauthorized, offline, not found, no ADB)
- ✅ Network connection (success, invalid IP/port, refused, timeout, unauthorized, offline)
- ✅ Disconnect (USB and network)
- ✅ All devices listing (mixed USB/network, emulator handling)
- ✅ Shell command safety (allows read-only, rejects modifying commands)
- ✅ Device properties retrieval
- ✅ Storage info parsing
- ✅ Connection guidance for all states
- ✅ IP address validation
- ✅ Subprocess error handling (timeout, not found, failures)
- ✅ State transitions (connect → disconnect)
- ✅ Full USB and network flows
- ✅ **No real device modifying commands ever executed**

**UI Integration (26 tests):**
- ✅ All new page rendering functions handle disconnected devices gracefully
- ✅ All new page rendering functions handle unsupported operations gracefully
- ✅ All new page rendering functions handle ADB errors gracefully
- ✅ Demo Mode isolation preserved across all new pages
- ✅ Module factory functions called correctly
- ✅ Page routing works for all 11 navigation pages
- ✅ Session state keys properly initialized for all modules

**Bundled ADB (27 tests):**
- ✅ Application root detection (development and frozen)
- ✅ Bundled ADB path discovery (platform-tools/adb.exe)
- ✅ Fallback to system PATH when bundled unavailable
- ✅ ADB version detection
- ✅ Bundled vs system ADB detection
- ✅ Error messages reference bundled ADB
- ✅ Integration with ADBManager

## Project Structure

```
TVFreedom/
├── app.py                      # Main Streamlit application (all pages integrated)
├── demo_simulator.py           # Demo Mode simulation logic (isolated from real ADB)
├── test_demo_simulator.py      # Automated tests for Demo Mode
├── test_app_integration.py     # UI integration tests for new pages
├── test_adb_bundled.py         # Bundled ADB discovery tests
├── adb_manager.py              # Real ADB connectivity (read-only)
├── test_adb_manager.py         # Automated tests for ADB Manager (mocked)
├── adb_bundled.py              # Bundled ADB discovery & management
├── device_identification.py    # Device identity & compatibility analysis
├── diagnostics.py              # Comprehensive diagnostics engine
├── package_inventory.py        # Installed package inventory & classification
├── package_classifier.py       # Safety classification for packages
├── recommendation_engine.py    # Personalized improvement recommendations
├── performance.py              # Read-only performance monitoring
├── backup_manager.py           # Local backup & recovery system
├── action_history.py           # Action logging & undo support
├── action_engine.py            # Safe action execution with confirmation
├── pyproject.toml              # Packaging configuration (bundled binaries)
├── requirements.txt            # Python dependencies
├── README.md                   # This file
└── .gitignore                  # Git ignore rules
```

## Roadmap

| Milestone | Description |
|-----------|-------------|
| 0.1.0 | Visual interface + Demo Mode |
| 0.2.0 | ADB integration & device detection |
| 0.3.0 | Full diagnostics, apps, recommendations, performance, backups, activity log + bundled ADB |
| **0.4.0-dev** | **Guarded package actions and Android launcher source preview (current feature preview)** |
| 0.5.0 | Advanced automation & scheduling |
| 1.0.0 | Stable release with full feature set |

## Current Limitations

1. **Package actions are limited** — Eligible disable/enable actions and user-app uninstall are available through the guarded workflow. General system settings changes are not exposed as package actions.

2. **Network ADB varies by manufacturer** — Not all TVs expose "Wireless debugging" or "ADB over network" in the same way. Some require enabling via `adb tcpip 5555` over USB first.

3. **No automatic pairing for Wireless Debugging (Android 11+)** — Modern wireless debugging uses pairing codes. This version supports manual IP:port entry only. Pairing workflow may be added in a future milestone.

4. **Windows-focused** — Tested on Windows. Linux/macOS may work but are not officially supported.

5. **No persistent device storage** — Device connections are not saved between sessions.

6. **Firewall/antivirus may block ADB** — Windows Defender or third-party antivirus may interfere with ADB network connections.

7. **Demo Mode and Real ADB are mutually exclusive** — Enable one or the other, not both simultaneously.

8. **No physical device validation** — All real-device features are tested via mocked subprocess. Physical device validation is not claimed.

9. **Feature-preview limitations** — The Windows app and launcher are development previews, not stable releases. Real-device behavior and Android TV compatibility require manual testing on compatible hardware. The bundled launcher APK is a local debug build, not a release APK; TV Freedom can install it to the selected device but does not set it as default or disable the stock launcher.

## ADB Redistribution & Licensing

TV Freedom bundles **Android SDK Platform Tools** (adb.exe and associated DLLs) under the **Apache License 2.0**. 

Google's Platform Tools are distributed as part of the Android SDK under the Apache 2.0 license, which explicitly permits:
- ✅ Redistribution of binaries
- ✅ Modification
- ✅ Commercial use
- ✅ Sublicensing

**Source:** https://developer.android.com/studio/terms (Android SDK License Agreement) and the Apache 2.0 license text included in Platform Tools.

**Bundled files:**
- `platform-tools/adb.exe` — Android Debug Bridge
- `platform-tools/AdbWinApi.dll` — Windows API wrapper
- `platform-tools/AdbWinUsbApi.dll` — Windows USB API wrapper

These files are included in the `platform-tools/` directory of the TV Freedom distribution. No modifications are made to the binaries.

## Disclaimer

TV Freedom is provided as-is, without warranty. Modifying device software carries inherent risk.
By using this application, you acknowledge that you understand these risks and accept responsibility
for any changes made to your device.

TV Freedom does not:
- Root devices or unlock bootloaders
- Modify system partitions
- Install custom ROMs or kernels
- Send data to external servers
- Make changes without explicit user confirmation
- **Execute real ADB commands in Demo Mode**
- **Execute any device-modifying commands in this version without explicit confirmation and backup**

All device-changing operations require:
1. Explicit user confirmation
2. Pre-action backup creation
3. Post-action verification
4. Full audit logging with reversal instructions

## License

For educational and personal use only.

(End of file - total 398 lines)