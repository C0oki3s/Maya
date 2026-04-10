import org.gradle.api.GradleException
import java.io.File

plugins {
    id("com.android.application") version "8.5.2"
    kotlin("android") version "1.9.24"
    kotlin("plugin.serialization") version "1.9.24"
}

android {
    namespace = "com.mobsec.companion"
    compileSdk = 34

    defaultConfig {
        applicationId = "com.mobsec.companion"
        minSdk = 26
        targetSdk = 34
        versionCode = 1
        versionName = "2.0.0"
    }

    buildTypes {
        release {
            isMinifyEnabled = false
            proguardFiles(
                getDefaultProguardFile("proguard-android-optimize.txt"),
                "proguard-rules.pro",
            )
        }
    }

    compileOptions {
        sourceCompatibility = JavaVersion.VERSION_17
        targetCompatibility = JavaVersion.VERSION_17
    }

    kotlinOptions {
        jvmTarget = "17"
    }
}

dependencies {
    implementation("org.jetbrains.kotlinx:kotlinx-serialization-json:1.6.3")
}

val signerJar = rootDir.parentFile.parentFile.resolve("assets/signer/uber-apk-signer-1.3.0.jar")
val apkOutputDir = rootDir.parentFile.parentFile.resolve("assets/android/apk")

fun requireCommand(name: String, hint: String) {
    val isWindows = System.getProperty("os.name").contains("Windows", ignoreCase = true)
    val check = if (isWindows) listOf("cmd", "/c", "where", name) else listOf("sh", "-c", "command -v $name")
    if (providers.exec { commandLine(check) }.result.get().exitValue != 0) {
        throw GradleException("Missing required tool '$name'. $hint")
    }
}

fun requireProjectProperty(key: String): String {
    val value = findProperty(key)?.toString()?.trim().orEmpty()
    if (value.isEmpty()) {
        throw GradleException("Missing required property '$key'. Pass it with -P$key=<value>.")
    }
    return value
}

fun findBuiltApk(buildType: String, suffix: String): File {
    val dir = layout.buildDirectory.dir("outputs/apk/$buildType").get().asFile
    if (!dir.exists()) {
        throw GradleException(
            "APK output directory not found: ${dir.absolutePath}. Run assemble${buildType.replaceFirstChar { it.uppercase() }} first.",
        )
    }

    val match = dir.listFiles()?.firstOrNull { it.isFile && it.name.endsWith(suffix) }
    return match ?: throw GradleException(
        "No APK with suffix '$suffix' found in ${dir.absolutePath}. Check Gradle assemble output for errors.",
    )
}

tasks.register("validateApkBuildEnvironment") {
    doFirst {
        if (!signerJar.exists()) {
            throw GradleException(
                "Missing signer: ${signerJar.absolutePath}. Ensure assets/signer/uber-apk-signer-1.3.0.jar exists.",
            )
        }
        requireCommand("java", "Install Java 17+ and ensure it is on PATH.")
    }
}

tasks.register("copyDebugApkToAssets") {
    dependsOn("assembleDebug")
    doLast {
        apkOutputDir.mkdirs()
        val debugApk = findBuiltApk("debug", "-debug.apk")
        debugApk.copyTo(File(apkOutputDir, "maya-companion-debug.apk"), overwrite = true)
    }
}

tasks.register("copyReleaseApkToAssets") {
    dependsOn("assembleRelease")
    doLast {
        apkOutputDir.mkdirs()
        val unsignedApk = findBuiltApk("release", "-release-unsigned.apk")
        unsignedApk.copyTo(File(apkOutputDir, "maya-companion-release-unsigned.apk"), overwrite = true)
    }
}

tasks.register("signReleaseApkWithUber") {
    dependsOn("validateApkBuildEnvironment", "copyReleaseApkToAssets")
    doLast {
        val unsignedApk = File(apkOutputDir, "maya-companion-release-unsigned.apk")
        if (!unsignedApk.exists()) {
            throw GradleException("Release unsigned APK not found: ${unsignedApk.absolutePath}")
        }

        exec {
            commandLine(
                "java",
                "-jar",
                signerJar.absolutePath,
                "--apks",
                unsignedApk.absolutePath,
                "--overwrite",
            )
        }

        val sourceSigned = File(apkOutputDir, "maya-companion-release-unsigned-aligned-debugSigned.apk")
        val finalSigned = File(apkOutputDir, "maya-companion-release-signed-uber.apk")
        if (sourceSigned.exists()) {
            sourceSigned.copyTo(finalSigned, overwrite = true)
        } else {
            unsignedApk.copyTo(finalSigned, overwrite = true)
        }
    }
}

tasks.register("signReleaseApkWithKeystore") {
    dependsOn("copyReleaseApkToAssets")
    doLast {
        requireCommand("jarsigner", "Install JDK tools and ensure jarsigner is on PATH.")

        val keystorePath = requireProjectProperty("keystorePath")
        val keyAlias = requireProjectProperty("keyAlias")
        val storePass = requireProjectProperty("storePass")
        val keyPass = findProperty("keyPass")?.toString()?.trim().orEmpty()

        val unsignedApk = File(apkOutputDir, "maya-companion-release-unsigned.apk")
        val signedApk = File(apkOutputDir, "maya-companion-release-signed-keystore.apk")
        if (!unsignedApk.exists()) {
            throw GradleException("Release unsigned APK not found: ${unsignedApk.absolutePath}")
        }

        val keystore = File(keystorePath)
        if (!keystore.exists()) {
            throw GradleException("Keystore not found: ${keystore.absolutePath}")
        }

        unsignedApk.copyTo(signedApk, overwrite = true)

        val cmd = mutableListOf(
            "jarsigner",
            "-verbose",
            "-sigalg",
            "SHA256withRSA",
            "-digestalg",
            "SHA-256",
            "-keystore",
            keystore.absolutePath,
            "-storepass",
            storePass,
        )
        if (keyPass.isNotEmpty()) {
            cmd += listOf("-keypass", keyPass)
        }
        cmd += listOf(signedApk.absolutePath, keyAlias)

        exec {
            commandLine(cmd)
        }
    }
}

tasks.register("buildCompanionApks") {
    dependsOn("copyDebugApkToAssets", "copyReleaseApkToAssets")
}
