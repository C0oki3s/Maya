# Security Policy

## Supported Versions

| Version | Supported          |
|---------|--------------------|
| latest  | :white_check_mark: |

## Reporting a Vulnerability

**Please do NOT open a public issue for security vulnerabilities.**

If you discover a security vulnerability in Maya, please report it responsibly:

1. **Email**: Send details to the maintainers (add your security contact email here)
2. **GitHub Security Advisories**: Use the [private vulnerability reporting](https://github.com/USER/MOBSEC/security/advisories/new) feature

### What to Include

- Description of the vulnerability
- Steps to reproduce
- Potential impact
- Suggested fix (if any)

### Response Timeline

- **Acknowledgment**: Within 48 hours
- **Triage**: Within 1 week
- **Fix**: Depends on severity — critical issues are prioritized immediately

### Scope

Maya is a security testing tool. Vulnerabilities in the tool itself (e.g., sandbox escapes, command injection in tool execution, credential leakage) are in scope. Issues in third-party tools installed inside the Docker sandbox (Frida, Nuclei, etc.) should be reported to their respective projects.

## Security Practices

- All dangerous tool execution happens inside Docker sandboxes
- No credentials are stored in code — env vars or config files only
- CodeQL analysis runs on every PR
- Dependencies are monitored via Dependabot
