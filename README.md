# LongPathGuard

LongPathGuard is a small audit-only application for Windows Server 2022. It watches new filesystem activity and helps administrators find full paths and file or folder names that exceed configured thresholds.

The application never deletes, moves, or renames files. Existing directory trees are inspected only when an administrator explicitly starts a manual scan.

## Screenshots

A screenshot location is prepared under `docs/screenshots/`. Add `dashboard.png`, `events.png`, `scan.png`, and `settings.png` there before publishing project screenshots.

## Features

- watchdog monitoring for `created`, `renamed`, and optionally `modified` events;
- `ok`, `warning`, `danger`, `critical`, `long_name`, and `critical_long_name` severities;
- SQLite event history and filtered CSV export;
- dashboard statistics and recent events;
- safe manual scan with an item limit;
- Windows ACL owner lookup through pywin32;
- Russian and English FastAPI/Jinja2 UI;
- local execution and NSSM Windows Service installation;
- Telegram and Email notifications when configured.

## Limitations

- Audit mode only: no quarantine or automatic remediation;
- no built-in web authentication;
- not a filesystem driver;
- manual scans run synchronously and are limited by `max_scan_items`;
- NSSM is not bundled or downloaded automatically.

## Requirements

- Windows Server 2022 or a compatible Windows version;
- 64-bit Python 3.12, 3.13, or 3.14 available in `PATH`;
- read permission for the watched folder;
- administrator rights only when installing the Windows Service;
- NSSM for service mode.

## Quick Start

```powershell
Set-ExecutionPolicy -Scope Process Bypass
.\scripts\setup.ps1
.\scripts\run.ps1
```

`setup.ps1` validates Python 3.12, 3.13, or 3.14, creates `.venv`, installs dependencies, creates `config` and `data`, and copies `config/config.example.yaml` to `config/config.yaml` only when the local config is missing. An existing config is never overwritten.

`run.ps1` uses the existing `.venv`, reads host/port from config, and does not reinstall dependencies on every normal start. `run_dev.ps1` remains as a compatibility wrapper around setup and run.

The UI listens locally by default:

```text
http://127.0.0.1:8787
```

## First Run

The public configuration intentionally has no watched folder:

```yaml
watcher:
  root_path: ""
  excluded_paths: []
```

This is a normal state. The application starts, but the watcher and manual scan remain inactive until a folder is selected in `Settings`.

LongPathGuard accepts absolute local paths and UNC paths. It normalizes surrounding quotes, environment variables, and trailing backslashes. Relative paths are rejected. It never creates the user-entered directory automatically.

Examples:

```text
D:\FileShare
"D:\Folder With Spaces\"
\\fileserver\share
%LPG_SHARE_ROOT%\Archive
```

Before saving, the application checks that the path exists, is a directory, and can be opened for reading. A candidate watcher starts before the previous watcher is stopped. If validation, watcher startup, or config saving fails, the previous config and watcher keep running.

## Main Configuration

Local config: `config/config.yaml`. Public example: `config/config.example.yaml`.

```yaml
app:
  language: ru
  audit_mode: true
  host: 127.0.0.1
  port: 8787
events:
  store_ok_events: false
  store_modified_events: false
watcher:
  root_path: ""
  excluded_paths: []
scanner:
  max_scan_items: 10000
```

With `store_ok_events: false`, normal OK events are skipped. With `store_modified_events: false`, normal modified events are skipped while path/name violations are still stored.

The application `data` directory is always excluded internally, even when it is not listed in `excluded_paths`.

## Local and UNC Paths

A local folder such as `D:\FileShare` is available only when the service account has suitable NTFS permissions.

A UNC path such as `\\server\share` works only when the `LongPathGuard` Windows Service account has access to both the SMB share and filesystem. `LocalSystem` is generally not appropriate for remote network shares.

Configure the service account using either:

1. `nssm edit LongPathGuard`, then the `Log on` tab;
2. `services.msc`, open `LongPathGuard` properties, then the `Log On` tab.

Restart the service after changing the account. Never store the service username or password in `config.yaml` or Git.

## Network Access

To access the UI from other computers, change:

```yaml
app:
  host: 0.0.0.0
  port: 8787
```

Do this only on a trusted network with a correctly scoped Windows Firewall rule. The current release has no advanced authentication, so do not expose the port directly to the internet.

## Manual Scan

The scan starts only from the `Scan` page and always uses the current runtime `root_path`. Exclusions and `max_scan_items` apply on every run. An access failure in one subdirectory is recorded and should not abort the remaining traversal.

When root_path is empty or unavailable, the button is disabled and no false SQLite event is created.

## CSV Export and Language

The `Events` page supports severity, event type, date range, path search, and result limit filters. `Export CSV` uses the active filters.

RU/EN can be switched from the top navigation. The selected language is stored in the local config and SQLite settings table.

## Install as a Windows Service with NSSM

1. Download NSSM manually from its official site.
2. Put `nssm.exe` at `scripts\tools\nssm.exe`, or add NSSM to `PATH`.
3. Run PowerShell as Administrator:

```powershell
Set-ExecutionPolicy -Scope Process Bypass
.\scripts\install_service.ps1
.\scripts\start_service.ps1
```

The installer calls `setup.ps1`, refuses to create a duplicate service, ensures `data` exists, reads host/port from config, enables automatic startup, and configures restart on failure.

Stop and start:

```powershell
.\scripts\stop_service.ps1
.\scripts\start_service.ps1
```

Uninstall:

```powershell
.\scripts\uninstall_service.ps1
```

The scripts never download NSSM and never store service credentials.

## Files, Data, and Logs

- configuration: `config/config.yaml`;
- public example: `config/config.example.yaml`;
- SQLite database: `data/longpathguard.db`;
- application log: `data/longpathguard.log`;
- service stdout/stderr: `data/service.out.log`, `data/service.err.log`.

The local config, database, and logs are excluded from Git.

## Backup

For a consistent backup, stop the service and copy `config/config.yaml` plus `data` to a protected destination:

```powershell
.\scripts\stop_service.ps1
Copy-Item .\config\config.yaml E:\Backups\LongPathGuard\config.yaml
Copy-Item .\data E:\Backups\LongPathGuard\data -Recurse
.\scripts\start_service.ps1
```

The destination is only an example. Do not commit backups to Git.

## Updating

1. Stop the service.
2. Back up config and data.
3. Update application files without replacing local `config/config.yaml` or `data`.
4. Run `scripts/setup.ps1` to refresh dependencies.
5. Run tests and start the service.

```powershell
.\scripts\stop_service.ps1
.\scripts\setup.ps1
.\.venv\Scripts\python.exe -m pytest
.\scripts\start_service.ps1
```

## Security

- keep the default `127.0.0.1` binding unless remote access is required;
- restrict port 8787 with Windows Firewall;
- run the service with the minimum read permissions it needs;
- never commit service passwords, SMTP credentials, or Telegram credentials;
- protect SQLite/config backups;
- remember that Audit mode reports problems but does not block or repair them.

## Troubleshooting

- `Path is required`: select an absolute folder in `Settings`.
- `Absolute path required`: use `D:\Share` or `\\server\share`, not a relative path.
- `Folder does not exist`: check spelling, drive availability, or SMB connectivity.
- `Object is not a folder`: select a directory instead of a file.
- `Access denied`: check NTFS and SMB permissions for the current process/service account.
- `Watcher failed to start`: inspect `data/longpathguard.log` and service stderr.
- `nssm.exe not found`: place it at `scripts\tools\nssm.exe`; it is intentionally excluded from Git.
- Remote UI unavailable: check host, firewall scope, and trusted-network connectivity.
- Port already in use: change `app.port` or stop the process using 8787.

## Developer Verification

```powershell
.\scripts\setup.ps1
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
.\.venv\Scripts\python.exe -m compileall app
.\.venv\Scripts\python.exe -m pytest
.\.venv\Scripts\python.exe -c "import app.main; print('import ok')"
```
