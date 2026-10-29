plugins {
    id("com.android.application")
    id("org.jetbrains.kotlin.android")
}

android {
    namespace = "com.tvfreedom.launcher"
    compileSdk = 35

    defaultConfig {
        applicationId = "com.tvfreedom.launcher"
        minSdk = 23
        targetSdk = 28
        versionCode = 1
        versionName = "0.1.0-preview"
    }

    compileOptions {
        sourceCompatibility = JavaVersion.VERSION_17
        targetCompatibility = JavaVersion.VERSION_17
    }

    kotlinOptions {
        jvmTarget = "17"
    }
}
