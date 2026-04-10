---
name: xamarin_analysis
description: Xamarin and .NET mobile assessment workflow
category: frameworks
version: "1.0"
last_updated: "2026-03-26"
applies_to: [static, dynamic]
platform: [android, ios]
---

# Xamarin Analysis Skill

## Detection

Detect Xamarin apps by looking for:
- `libmonosgen-2.0.so` or `libmonodroid.so` in `lib/` (Android)
- `assemblies/` directory inside APK containing `.dll` files
- `Xamarin.` prefixed assemblies (Xamarin.Essentials, Xamarin.Forms)
- `mono_` or `xamarin_` references in native libraries

## Step 1: Extract Assemblies

### Android
```
terminal_execute("unzip -o <apk_path> 'assemblies/*.dll' -d /tmp/xamarin/")
terminal_execute("ls /tmp/xamarin/assemblies/")
```

Assemblies may be compressed. If `.dll` files start with `XALZ` header:
```
terminal_execute("python3 -c \"import lz4.block; open('/tmp/out.dll','wb').write(lz4.block.decompress(open('/tmp/xamarin/assemblies/<name>.dll','rb').read()[12:], uncompressed_size=<size>))\"")
```

## Step 2: Decompile .NET Assemblies

Use `ilspycmd` or `dnSpy` (if on Windows) to decompile:
```
terminal_execute("ilspycmd /tmp/xamarin/assemblies/<AppName>.dll -o /tmp/xamarin/decompiled/")
```

Search decompiled C# for secrets:
```
terminal_execute("grep -rn 'apiKey\|secret\|password\|connection.*string\|http://\|https://' /tmp/xamarin/decompiled/ | head -40")
```

## Step 3: Configuration Files

Xamarin apps often embed configuration in:
- Embedded resources within assemblies
- `Assets/` folder XML/JSON files
- `app.config` or `web.config` style files

```
terminal_execute("unzip -o <apk_path> 'assets/*' -d /tmp/xamarin/")
terminal_execute("find /tmp/xamarin/assets/ -name '*.json' -o -name '*.xml' -o -name '*.config' | head -20")
```

## Step 4: Runtime Analysis

Xamarin uses Mono runtime. Frida can hook both:
- Managed (.NET) methods via Mono bridge
- Native methods via standard Frida Java/ObjC hooks

For Mono method hooking:
```
terminal_execute("grep -rn 'MonoClass\|MonoMethod' /tmp/jadx_out/ | head -10")
```

## Remediation

- Avoid embedding secrets in managed resources or assemblies
- Treat client validation as advisory only - enforce on server
- Use AOT compilation to raise reverse engineering difficulty
- Enable assembly linking/trimming to reduce exposed surface
- Do not store credentials in Xamarin.Essentials SecureStorage without additional encryption