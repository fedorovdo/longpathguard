# LongPathGuard

LongPathGuard v0.1.0 is a small Windows Server 2022 application for file servers. It helps administrators audit newly created files and folders with long names or long full paths.

The core rule: v0.1.0 is audit only. The application never deletes, moves, renames, or modifies files.

## Features

- Watchdog monitoring for new `created`, `renamed`, and `modified` events.
- Full path length and file/folder name length checks.
- Windows ACL owner lookup through pywin32 when available.
- SQLite event database at `data/longpathguard.db`.
- FastAPI and Jinja2 web UI without React, Docker, or PostgreSQL.
- Russian by default, with RU/EN language switching.
- CSV event export.
- Manual safe scanner for existing files.
- Windows Service installation through NSSM.

## Install Python 3.12

1. Download Python 3.12: https://www.python.org/downloads/windows/
2. Enable `Add python.exe to PATH` during installation.
3. Verify:

```powershell
python --version
```

## Create venv and Run Dev

Open PowerShell in the project root:

```powershell
Set-ExecutionPolicy -Scope Process Bypass
.\scripts\run_dev.ps1
```

The script creates `.venv`, installs dependencies, and starts uvicorn on the host/port from `config/config.yaml`.

By default, the web UI is available only on the server:

```text
http://127.0.0.1:8787
```

To access the UI from the local network, explicitly change `app.host` to `0.0.0.0` and open port `8787` in Windows Firewall:

```yaml
app:
  host: 0.0.0.0
  port: 8787
```

## Configuration

GitHub includes `config/config.example.yaml`. Local `config/config.yaml` is ignored by git and can contain server-specific settings.

The default watched folder is:

```yaml
watcher:
  root_path: D:\fs
```

If the folder does not exist, the app keeps running: the dashboard shows an error and the watcher does not start until the path is fixed.

## Event Noise

By default, LongPathGuard stores only problems and errors:

```yaml
events:
  store_ok_events: false
  store_modified_events: false
```

- `store_ok_events: false` skips events with `severity = ok`.
- `store_modified_events: false` skips `modified` events unless they are warning/danger/critical/long_name.

This keeps the database focused on violations instead of normal file activity.

## Manual Scan

The scanner does not run automatically. Open `Scan` and press `Start scan`.

The scanner only reads the directory tree and writes detected problems as events with `event_type = scan_detected`. It does not change files. The limit is controlled by:

```yaml
scanner:
  max_scan_items: 10000
```

## Windows Service Installation

LongPathGuard uses NSSM.

1. Download NSSM: https://nssm.cc/download
2. Put `nssm.exe` here:

```text
scripts\tools\nssm.exe
```

Or add `nssm.exe` to `PATH`.

3. Run PowerShell as Administrator:

```powershell
Set-ExecutionPolicy -Scope Process Bypass
.\scripts\install_service.ps1
.\scripts\start_service.ps1
```

The script installs dependencies, creates the `LongPathGuard` service, enables auto-start, and configures NSSM restart on failure. The service starts uvicorn on the host/port from `config/config.yaml`; by default this is `127.0.0.1:8787`.

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

## Audit Only

LongPathGuard v0.1.0:

- does not quarantine files;
- does not delete files;
- does not rename files;
- does not move files;
- does not install a filesystem driver;
- does not use Docker, PostgreSQL, or React.
