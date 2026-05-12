# LongPathGuard

LongPathGuard v0.1 is a small Windows Server 2022 application that watches a file share folder and helps administrators audit newly created or changed files and folders with long names or long full paths.

The core safety rule for v0.1: audit mode only. The application never deletes, moves, renames, or modifies files.

## Features

- Watchdog-based monitoring for `created`, `renamed`, and debounced `modified` events.
- Full path length and file/folder name length checks.
- SQLite event database at `data/longpathguard.db`.
- FastAPI and Jinja2 web UI without React or Docker.
- Russian by default, with RU/EN language switching.
- CSV event export.
- Manual safe scanner for existing files.
- Telegram and Email notification stubs with safe failure handling.
- Windows Service installation through NSSM.

## Requirements

- Windows Server 2022.
- Python 3.12.
- Administrator rights for service installation.

## Install Python 3.12

1. Download Python 3.12 from https://www.python.org/downloads/windows/
2. Enable `Add python.exe to PATH` during installation.
3. Verify:

```powershell
python --version
```

## First Run

Open PowerShell in the project root and run:

```powershell
Set-ExecutionPolicy -Scope Process Bypass
.\scripts\run_dev.ps1
```

The script creates `.venv`, installs dependencies, and starts the server:

```text
http://server-ip:8787
```

On the same server, open:

```text
http://localhost:8787
```

## Watched Folder

The default folder is:

```yaml
watcher:
  root_path: D:\fs
```

Change it in `config/config.yaml` or on the `Settings` page.

If the folder does not exist, the app keeps running, shows a dashboard error, and does not start the watcher until the path is fixed.

## Manual Scan

The scanner does not run automatically. Open `Scan` and press `Start scan`.

The scanner only reads the directory tree and writes detected long paths as events with `event_type = scan_detected`. The limit is controlled by:

```yaml
scanner:
  max_scan_items: 10000
```

## Windows Service Installation

LongPathGuard uses NSSM.

1. Download NSSM from https://nssm.cc/download
2. Put `nssm.exe` here:

```text
scripts\tools\nssm.exe
```

Or add `nssm.exe` to `PATH`.

3. Install and start the service from an Administrator PowerShell:

```powershell
Set-ExecutionPolicy -Scope Process Bypass
.\scripts\install_service.ps1
.\scripts\start_service.ps1
```

Stop:

```powershell
.\scripts\stop_service.ps1
```

Uninstall:

```powershell
.\scripts\uninstall_service.ps1
```

## Logs and Data

- Database: `data/longpathguard.db`
- Application log: `data/longpathguard.log`
- NSSM service logs: `data/service.out.log`, `data/service.err.log`

## Default Thresholds

```yaml
thresholds:
  max_full_path_warning: 220
  max_full_path_danger: 240
  max_full_path_critical: 260
  max_name_length: 120
```

Severity values:

- `ok`
- `warning`
- `danger`
- `critical`
- `long_name`
- `critical_long_name`

## Out of Scope for v0.1

- No quarantine.
- No file deletion.
- No file rename.
- No file move.
- No filesystem driver.
- No Docker, PostgreSQL, or React.
