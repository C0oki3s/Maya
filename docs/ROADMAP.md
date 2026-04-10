# Roadmap

> Living document — updated as features are completed or priorities shift.

---

## Current Status

Maya has a functional multi-agent framework with 40+ security tools, a skill system, Docker sandbox execution, and an Android companion app. See [PHASE_TRACKER.md](PHASE_TRACKER.md) for detailed implementation status and [SPEC_GAP_CHECKLIST.md](SPEC_GAP_CHECKLIST.md) for spec gap analysis.

---

## Planned Features

### iOS Companion — Full Implementation
**Priority**: High

Complete the iOS companion service from scaffold to fully functional jailbreak-side service with module parity to the Android companion.

- [ ] Keychain dumper integration (keychain-dumper or custom Objective-C bridge)
- [ ] Filesystem inspector with sandbox traversal
- [ ] App data export (IPA extraction, plist dumping, container enumeration)
- [ ] NSURLSession / URLSession traffic hooking
- [ ] Data protection class enumeration
- [ ] Entitlements extraction and analysis
- [ ] Binary cookie reader
- [ ] Pasteboard monitoring
- [ ] Background task inspector
- [ ] Full HTTP server (matching Android Ktor architecture)

---

### Whitebox Testing — Source Code Analysis
**Priority**: High

Add a source-code-aware mode where Maya can analyze application source code directly, not just compiled binaries.

- [ ] Source code ingestion tool (accept directory path or git repo)
- [ ] Language-aware parsing (Java/Kotlin for Android, Swift/ObjC for iOS)
- [ ] Semgrep rule pack for mobile security (custom rules beyond defaults)
- [ ] Taint analysis skills — trace data from user input to sensitive sinks
- [ ] Correlate static source findings with dynamic runtime behavior
- [ ] New agent role: `whitebox` with source-code-specific skills
- [ ] Hardcoded secrets scanner (API keys, credentials, tokens in source)
- [ ] Dependency vulnerability scanning (Gradle/CocoaPods/SPM)

---

### CI/CD Integration
**Priority**: High

Provide ready-to-use pipeline templates so teams can run Maya as part of their CI/CD.

- [ ] GitHub Actions reusable workflow (`.github/workflows/maya-scan.yml`)
- [ ] GitLab CI template (`.gitlab-ci.yml`)
- [ ] Azure DevOps pipeline template
- [ ] SARIF output format for GitHub Security tab integration
- [ ] JUnit XML output for test framework integration
- [ ] Exit codes for CI gates (0 = pass, 1 = findings above threshold)
- [ ] Configurable severity threshold (`--fail-on critical,high`)
- [ ] Compare mode — diff findings between runs/branches
- [ ] Slack/Teams webhook notifications for scan results

---

### Emulator Support
**Priority**: Medium

First-class support for Android emulators (AVD) and iOS Simulator, removing the need for a physical device during development and CI.

- [ ] Auto-detect emulator vs physical device
- [ ] AVD management tools (create, start, snapshot, restore)
- [ ] Emulator-optimized Frida setup (no root required on emulator)
- [ ] iOS Simulator support for non-jailbreak static analysis
- [ ] Corellium cloud device integration
- [ ] Genymotion SaaS integration
- [ ] Pre-configured emulator images with Frida + companion pre-installed
- [ ] Headless emulator mode for CI (no GPU required)

---

### Dynamic Frida Scripts
**Priority**: Medium

Move beyond static pre-built scripts to intelligent, adaptive Frida instrumentation.

- [ ] **AI-Generated Scripts** — Agent generates custom Frida hooks based on decompiled code analysis
  - Analyze class structure → identify interesting methods → generate targeted hooks
  - Template-based generation with LLM filling in class/method specifics
- [ ] **Frida CodeShare Integration** — Fetch community scripts from [codeshare.frida.re](https://codeshare.frida.re)
  - Search CodeShare by keyword/tag
  - Download, validate, and execute CodeShare scripts
  - Cache fetched scripts locally for offline use
- [ ] **Smart Script Selection** — Agent picks the right script based on context
  - App framework detection → select framework-specific scripts
  - Security control detection → select appropriate bypass scripts
  - Automatic version-aware script selection (Frida 15.x vs 16.x APIs)
- [ ] **Script Composition** — Combine multiple scripts into a single injection
  - Hook chaining: bypass root detection + SSL pinning + crypto logging in one attach
  - Conflict detection: warn if two scripts hook the same method
- [ ] **Runtime Script Editor** — Modify scripts on-the-fly during a scan
  - Agent adjusts hook parameters based on observed behavior
  - Iterative refinement: hook → observe → adjust → re-hook

---

### Skill System Improvements
**Priority**: Medium

Evolve the skill system towards a community marketplace model.

- [ ] **Community Skill Packs** — Downloadable skill bundles
  - `maya skills install owasp-mobile-top10`
  - `maya skills install fintech-testing`
  - Version pinning and compatibility checks
- [ ] **Skill Auto-Updates** — Check for updated skills on scan start
- [ ] **Skill Marketplace / Registry** — Central index of community skills
  - GitHub-based registry (skill packs as repos)
  - Star/download counts, compatibility badges
- [ ] **Skill Testing Framework** — Validate skills against known-vulnerable apps
  - "This skill should find X in DIVA, Y in InsecureBankv2"
  - CI for skill packs
- [ ] **Skill Composition** — Compose complex methodologies from atomic skills
- [ ] **Skill Analytics** — Track which skills produce the most findings

---

### MobSF Deep Integration
**Priority**: Medium

Tighter coupling with Mobile Security Framework for comprehensive static analysis.

- [ ] Auto-upload APK/IPA to MobSF on scan start
- [ ] Pull MobSF findings into Maya's finding deduplication system
- [ ] Correlate MobSF static findings with Maya's dynamic verification
- [ ] Use MobSF's decompiled code cache instead of re-decompiling
- [ ] MobSF as a skill source (convert MobSF rules to Maya skills)

---

### Reporting Enhancements
**Priority**: Low

- [ ] PDF report generation
- [ ] Executive summary mode (non-technical)
- [ ] OWASP MASVS/MASTG compliance mapping
- [ ] Finding confidence scores
- [ ] Screenshot evidence auto-embedding
- [ ] Remediation code snippets (not just description)
- [ ] Trend tracking across multiple scans

---

### TUI / Dashboard
**Priority**: Low

- [ ] Real-time terminal UI showing agent tree, live findings, tool execution
- [ ] Web dashboard for multi-scan management
- [ ] The "Silent Sentinel" design system (see [DESIGN.md](DESIGN.md))

---

## Completed Milestones

| Phase | Status | What was delivered |
|-------|--------|--------------------|
| Phase 0 | ✅ Done | Core package skeleton, agent loop, tools, tests |
| Phase 1 | ✅ Done | Agent graph tools, LiteLLM config, env/CLI overrides |
| Phase 2 | ✅ Done | Frida, APK, device bridge, Caido, MobSF, Objection, Reflutter tool modules |
| Phase 3 | ✅ Done | External skill loading, role-based prompt tiers, dynamic skills tools |
| Phase 4 | ✅ Done | DockerRuntime, FastAPI tool_server, host setup, Dockerfile |
| Phase 5 | ✅ Scaffold | Android companion (Ktor/HTTP), iOS companion (Swift scaffold) |
| Phase 6 | ✅ Done | CLI args, output artifacts, tracer report generation |
| Phase 7 | ✅ Smoke | Smoke tests across CLI/runtime/shared-context/request-queue |

---

## How to Contribute to the Roadmap

1. **Pick a feature** from the list above
2. **Open an issue** to discuss the approach before coding
3. **Reference this roadmap** in your PR description
4. See [contributing.md](contributing.md) for the full contribution guide

Feature requests and new roadmap ideas are welcome as [GitHub Issues](https://github.com/USER/MOBSEC/issues/new?template=feature_request.md).
