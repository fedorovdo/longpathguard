# Changelog

## Unreleased

## 0.2.0 - 2026-06-28

- Added secure Telegram and Email settings UI with secret preservation and explicit clearing.
- Added structured test-notification results for disabled, incomplete, failed, and successful delivery.
- Removed server-specific paths from defaults and the public example configuration.
- Added Windows path normalization and validation for local and UNC paths.
- Added safe two-phase watcher switching when settings change.
- Added first-run handling for an unconfigured watched folder.
- Added setup and normal-run PowerShell scripts.
- Hardened NSSM installation against duplicate services.
- Added pytest coverage and a Windows GitHub Actions workflow.
- Expanded Russian and English operations documentation.

## 0.1.0 - 2026-05-13

- Added FastAPI and Jinja2 web UI with RU/EN localization.
- Added watchdog-based audit monitoring for created, renamed, and modified filesystem events.
- Added SQLite event storage, dashboard, filters, and CSV export.
- Added safe manual scanner for existing files.
- Added Windows owner lookup support through pywin32 with safe fallbacks.
- Added default noise reduction for OK and modified events.
- Added NSSM Windows Service scripts.
- Added GitHub-ready config example and ignore rules for local data.
