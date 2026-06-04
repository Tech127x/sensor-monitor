# Security Policy

## Supported versions

| Version | Supported |
|---|---|
| 2.x | ✅ |
| < 2.0 | ❌ |

## Reporting a vulnerability

If you discover a security vulnerability in Sensor Monitor, please **do not** open a public issue. Instead, email the project maintainers directly, or open a GitHub Security Advisory at:

https://github.com/tech127x/sensor-monitor-ds/security/advisories/new

We'll acknowledge receipt within 48 hours and work on a fix before disclosing publicly.

## What to include

- A clear description of the vulnerability
- Steps to reproduce
- Potential impact
- Any suggested fix (if you have one)

## Scope

- The Python source code in `sensor_monitor/`
- Dependencies listed in `pyproject.toml`
- Build and install scripts in `scripts/`

Out of scope: third-party services (Companion, GitHub), your local hardware configuration, or `sm_config.yaml` contents.
