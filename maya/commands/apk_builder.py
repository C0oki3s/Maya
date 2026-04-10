"""Maya APK build and signing automation."""

from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path


def _check_command(name: str) -> bool:
    """Check if a command exists in PATH."""
    return shutil.which(name) is not None


def _check_docker_buildx() -> bool:
    """Check if Docker buildx is available."""
    try:
        result = subprocess.run(
            ["docker", "buildx", "version"],
            capture_output=True,
            timeout=5,
        )
        return result.returncode == 0
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return False


def build_apk_buildx(
    dockerfile: Path,
    output_dir: Path,
    sign_mode: str = "uber",
    keystore_path: Path | None = None,
    key_alias: str | None = None,
    store_pass: str | None = None,
    key_pass: str | None = None,
    repo_root: Path | None = None,
) -> bool:
    """Build APK using Docker buildx (modern approach)."""
    if repo_root is None:
        repo_root = Path.cwd()

    build_args = ["--build-arg", f"SIGN_MODE={sign_mode}"]

    if sign_mode == "keystore":
        if not keystore_path or not keystore_path.exists():
            print(f"ERROR: Keystore file not found: {keystore_path}", file=sys.stderr)
            return False
        if not key_alias or not store_pass:
            print("ERROR: --key-alias and --store-pass required for keystore mode", file=sys.stderr)
            return False

        with open(keystore_path, "rb") as f:
            import base64

            b64 = base64.b64encode(f.read()).decode()
        build_args.extend(
            [
                "--build-arg",
                f"KEYSTORE_BASE64={b64}",
                "--build-arg",
                f"KEY_ALIAS={key_alias}",
                "--build-arg",
                f"STORE_PASS={store_pass}",
            ]
        )
        if key_pass:
            build_args.extend(["--build-arg", f"KEY_PASS={key_pass}"])

    output_dir.mkdir(parents=True, exist_ok=True)

    cmd = [
        "docker",
        "build",
        "-f",
        str(dockerfile),
        "--target",
        "apk-output",
        "--output",
        f"type=local,dest={output_dir}",
    ] + build_args + [str(repo_root)]

    try:
        result = subprocess.run(cmd, check=False)
        return result.returncode == 0
    except FileNotFoundError:
        print("ERROR: docker command not found", file=sys.stderr)
        return False


def build_apk_traditional(
    dockerfile: Path,
    output_dir: Path,
    sign_mode: str = "uber",
    keystore_path: Path | None = None,
    key_alias: str | None = None,
    store_pass: str | None = None,
    key_pass: str | None = None,
    repo_root: Path | None = None,
) -> bool:
    """Build APK without buildx (fallback for older Docker versions)."""
    if repo_root is None:
        repo_root = Path.cwd()

    print("[*] Docker buildx not available; using traditional build + extract fallback...", file=sys.stderr)

    output_dir.mkdir(parents=True, exist_ok=True)

    # Build the builder image
    print("[*] Building builder image...", file=sys.stderr)
    build_cmd = [
        "docker",
        "build",
        "-f",
        str(dockerfile),
        "-t",
        "maya-apk-builder:latest",
        str(repo_root),
    ]

    if subprocess.run(build_cmd, check=False).returncode != 0:
        print("ERROR: Docker image build failed", file=sys.stderr)
        return False

    # Create a container to extract APKs (no buildx needed)
    print("[*] Creating extractor container...", file=sys.stderr)
    extract_cmd = [
        "docker",
        "run",
        "--name",
        "apk-tmp",
        "--entrypoint",
        "true",
        "maya-apk-builder:latest",
    ]

    if subprocess.run(extract_cmd, check=False, capture_output=True).returncode != 0:
        # Container might already exist; try to remove and retry
        subprocess.run(["docker", "rm", "apk-tmp"], capture_output=True)
        if subprocess.run(extract_cmd, check=False, capture_output=True).returncode != 0:
            print("ERROR: Failed to create extractor container", file=sys.stderr)
            return False

    # Copy APKs from container to host
    print(f"[*] Extracting APKs to {output_dir}...", file=sys.stderr)
    copy_cmd = [
        "docker",
        "cp",
        "apk-tmp:/project/assets/android/apk/.",
        str(output_dir),
    ]

    copy_ok = subprocess.run(copy_cmd, check=False).returncode == 0

    # Cleanup
    subprocess.run(["docker", "rm", "apk-tmp"], capture_output=True)

    if not copy_ok:
        print("ERROR: Failed to extract APKs from container", file=sys.stderr)
        return False

    return True


def build_apk(
    sign_mode: str = "uber",
    keystore_path: str | None = None,
    key_alias: str | None = None,
    store_pass: str | None = None,
    key_pass: str | None = None,
) -> int:
    """
    Main APK build entry point.
    Returns 0 on success, 1 on failure.
    """
    repo_root = Path.cwd()
    dockerfile = repo_root / "containers" / "Dockerfile.apk-builder"
    output_dir = repo_root / "assets" / "android" / "apk"

    if not dockerfile.exists():
        print(f"ERROR: Dockerfile not found: {dockerfile}", file=sys.stderr)
        return 1

    signer_jar = repo_root / "assets" / "signer" / "uber-apk-signer-1.3.0.jar"
    if not signer_jar.exists():
        print(f"ERROR: Signer JAR not found: {signer_jar}", file=sys.stderr)
        return 1

    if not _check_command("docker"):
        print(
            "ERROR: docker command not found. Install Docker Desktop: "
            "https://docs.docker.com/get-docker/",
            file=sys.stderr,
        )
        return 1

    keystore_p = Path(keystore_path) if keystore_path else None

    print(f"[*] Building companion APK (sign mode: {sign_mode})...", file=sys.stderr)

    # Try buildx first; fall back to traditional if unavailable
    if _check_docker_buildx():
        success = build_apk_buildx(
            dockerfile,
            output_dir,
            sign_mode=sign_mode,
            keystore_path=keystore_p,
            key_alias=key_alias,
            store_pass=store_pass,
            key_pass=key_pass,
            repo_root=repo_root,
        )
    else:
        success = build_apk_traditional(
            dockerfile,
            output_dir,
            sign_mode=sign_mode,
            keystore_path=keystore_p,
            key_alias=key_alias,
            store_pass=store_pass,
            key_pass=key_pass,
            repo_root=repo_root,
        )

    if success:
        print(f"\n[+] Success! APKs written to {output_dir}/", file=sys.stderr)
        apks = sorted(output_dir.glob("*.apk"))
        for apk in apks:
            size_mb = apk.stat().st_size / (1024 * 1024)
            print(f"    - {apk.name} ({size_mb:.2f} MB)", file=sys.stderr)
        return 0
    else:
        print("[ERROR] APK build failed. Check output above.", file=sys.stderr)
        return 1
