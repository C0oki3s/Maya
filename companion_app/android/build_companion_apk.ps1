<#
.SYNOPSIS
  Build and sign the Maya companion APK inside Docker.

.DESCRIPTION
  Requires Docker Desktop (with BuildKit enabled, default since 20.10+).
  No local Java, Android SDK, or Gradle needed.
  Output: assets\android\apk\

.PARAMETER SignMode
  uber      – sign with uber-apk-signer debug key (default)
  keystore  – sign with a provided .jks/.p12 keystore

.PARAMETER KeystorePath   Path to keystore file (.jks or .p12). Required for keystore mode.
.PARAMETER KeyAlias       Key alias inside the keystore. Required for keystore mode.
.PARAMETER StorePass      Keystore store password. Required for keystore mode.
.PARAMETER KeyPass        Individual key password. Optional for keystore mode.

.EXAMPLE
  .\build_companion_apk.ps1

.EXAMPLE
  .\build_companion_apk.ps1 -SignMode keystore `
      -KeystorePath C:\keys\release.jks `
      -KeyAlias maya_release `
      -StorePass "storePass123" `
      -KeyPass "keyPass456"
#>
param(
    [ValidateSet("uber", "keystore")]
    [string]$SignMode = "uber",
    [string]$KeystorePath = "",
    [string]$KeyAlias = "",
    [string]$StorePass = "",
    [string]$KeyPass = ""
)

$ErrorActionPreference = "Stop"

function Fail([string]$Message) {
    Write-Error "ERROR: $Message"
    exit 1
}

# ── Preflight ────────────────────────────────────────────────────────────────
if (-not (Get-Command docker -ErrorAction SilentlyContinue)) {
    Fail "docker is not installed or not on PATH.`nInstall Docker Desktop: https://docs.docker.com/get-docker/"
}

$RepoRoot   = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path
$Dockerfile  = Join-Path $RepoRoot "containers\Dockerfile.apk-builder"
$SignerJar   = Join-Path $RepoRoot "assets\signer\uber-apk-signer-1.3.0.jar"
$OutputDir   = Join-Path $RepoRoot "assets\android\apk"

if (-not (Test-Path $Dockerfile)) {
    Fail "Missing Dockerfile: $Dockerfile"
}
if (-not (Test-Path $SignerJar)) {
    Fail "Missing signer asset: $SignerJar"
}

# ── Build argument array ─────────────────────────────────────────────────────
$BuildArgs = @("--build-arg", "SIGN_MODE=$SignMode")

if ($SignMode -eq "keystore") {
    if ([string]::IsNullOrWhiteSpace($KeystorePath)) { Fail "--KeystorePath is required for keystore mode" }
    if ([string]::IsNullOrWhiteSpace($KeyAlias))    { Fail "--KeyAlias is required for keystore mode" }
    if ([string]::IsNullOrWhiteSpace($StorePass))   { Fail "--StorePass is required for keystore mode" }
    if (-not (Test-Path $KeystorePath))             { Fail "Keystore file not found: $KeystorePath" }

    $Base64 = [Convert]::ToBase64String([IO.File]::ReadAllBytes($KeystorePath))
    $BuildArgs += @(
        "--build-arg", "KEYSTORE_BASE64=$Base64",
        "--build-arg", "KEY_ALIAS=$KeyAlias",
        "--build-arg", "STORE_PASS=$StorePass"
    )
    if (-not [string]::IsNullOrWhiteSpace($KeyPass)) {
        $BuildArgs += @("--build-arg", "KEY_PASS=$KeyPass")
    }
}

New-Item -ItemType Directory -Force -Path $OutputDir | Out-Null

# ── Run build ────────────────────────────────────────────────────────────────
Write-Host "[*] Building companion APK inside Docker (sign mode: $SignMode)..."

$env:DOCKER_BUILDKIT = "1"
& docker build `
    -f $Dockerfile `
    --target apk-output `
    --output "type=local,dest=$OutputDir" `
    @BuildArgs `
    $RepoRoot

if ($LASTEXITCODE -ne 0) {
    Fail "Docker build failed. Check output above."
}

Write-Host ""
Write-Host "[+] Done. APKs written to assets\android\apk\"
Get-ChildItem $OutputDir -Filter "*.apk" | Select-Object Name,
    @{N="Size";E={"{0:N0} KB" -f ($_.Length / 1KB)}} |
    Format-Table -AutoSize
