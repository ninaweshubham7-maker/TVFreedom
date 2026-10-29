# TV Freedom Home — Android launcher source preview

This is the first native Android launcher source component for TV Freedom. It provides a clean dark home screen and lists apps exposed through Android's Leanback/Launcher intents. It declares the HOME intent so Android can offer it as a home app.

## Build

1. Open this `launcher-android` folder in Android Studio (current stable version).
2. Allow Gradle sync and install Android SDK Platform 35.
3. Build `app` → `assembleDebug`.
4. The debug APK is written to `app/build/outputs/apk/debug/app-debug.apk`.
5. Install the resulting APK on a spare/compatible Android TV for testing.

On Windows, the checked-in Gradle wrapper can also build it from this directory:

```powershell
.\gradlew.bat :app:assembleDebug
```

## Important limitations

- The current workspace contains a locally built debug APK at `app/build/outputs/apk/debug/app-debug.apk`; it is not a release APK or a prebuilt hardware-verified product.
- Android TV / Google TV vendors differ in whether they permit third-party launchers to become the default home app. Fire TV and some vendor builds may restrict this.
- The first preview lists apps and launches them; it does not yet provide favourites, app hiding, settings integration, or automatic default-launcher switching.
- Set the default launcher through the TV's own Home app/default-app settings. Keep the stock launcher enabled until the replacement is confirmed working.
- Compile and test on real hardware before shipping to users.

## TV Freedom controller integration

The Windows app's **Clean Launcher** page detects the expected debug APK at `app/build/outputs/apk/debug/app-debug.apk` and offers to install that specific APK to the currently selected ADB device. It does not silently set the launcher as default or disable the stock launcher.
