plugins {
    id("com.android.application")
}

android {
    namespace = "com.paperagent.mobile"
    compileSdk = 34

    defaultConfig {
        applicationId = "com.paperagent.mobile"
        minSdk = 24
        targetSdk = 34
        versionCode = 1
        versionName = "0.1.0"
        // 模拟器访问本机 H5：10.0.2.2；真机改成电脑局域网 IP
        buildConfigField("String", "H5_URL", "\"http://10.0.2.2:10086\"")
    }

    buildFeatures {
        buildConfig = true
    }

    buildTypes {
        release {
            isMinifyEnabled = false
        }
    }

    compileOptions {
        sourceCompatibility = JavaVersion.VERSION_17
        targetCompatibility = JavaVersion.VERSION_17
    }
}

dependencies {
    implementation("androidx.appcompat:appcompat:1.7.0")
    implementation("com.google.android.material:material:1.12.0")
}
