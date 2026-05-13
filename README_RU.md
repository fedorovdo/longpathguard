# LongPathGuard

LongPathGuard v0.1.0 - микро-приложение для Windows Server 2022, которое устанавливается на файловый сервер и помогает администратору контролировать новые файлы и папки со слишком длинными именами или путями.

Главный принцип: v0.1.0 работает только в режиме аудита. Приложение ничего не удаляет, не перемещает, не переименовывает и не меняет в файловой системе.

## Возможности

- Наблюдение за новыми событиями `created`, `renamed`, `modified` через watchdog.
- Проверка длины полного пути и имени файла или папки.
- Получение владельца объекта через Windows ACL при наличии pywin32.
- SQLite-журнал событий в `data/longpathguard.db`.
- Web UI на FastAPI и Jinja2 без React, Docker и PostgreSQL.
- Русский интерфейс по умолчанию, переключение RU/EN.
- CSV-экспорт событий.
- Ручной безопасный сканер существующих файлов.
- Установка как Windows Service через NSSM.

## Установка Python 3.12

1. Скачайте Python 3.12: https://www.python.org/downloads/windows/
2. Во время установки включите `Add python.exe to PATH`.
3. Проверьте:

```powershell
python --version
```

## Создание venv и dev-запуск

Откройте PowerShell в корне проекта:

```powershell
Set-ExecutionPolicy -Scope Process Bypass
.\scripts\run_dev.ps1
```

Скрипт создаст `.venv`, установит зависимости и запустит uvicorn на host/port из `config/config.yaml`.

По умолчанию интерфейс доступен только на сервере:

```text
http://127.0.0.1:8787
```

Для доступа из локальной сети нужно явно изменить `app.host` на `0.0.0.0` и открыть порт `8787` в Windows Firewall:

```yaml
app:
  host: 0.0.0.0
  port: 8787
```

## Конфигурация

Для GitHub используется пример `config/config.example.yaml`. Локальный `config/config.yaml` игнорируется git и может содержать настройки конкретного сервера.

По умолчанию наблюдаемая папка:

```yaml
watcher:
  root_path: D:\fs
```

Если папка не существует, приложение не падает: dashboard покажет ошибку, watcher не стартует до исправления пути.

## Шум событий

По умолчанию LongPathGuard хранит только нарушения и ошибки:

```yaml
events:
  store_ok_events: false
  store_modified_events: false
```

- `store_ok_events: false` не записывает события с `severity = ok`.
- `store_modified_events: false` не записывает `modified` события, если они не являются warning/danger/critical/long_name.

Так база по умолчанию не заполняется обычными изменениями файлов.

## Скан существующих файлов

Скан не запускается автоматически. Откройте страницу `Сканирование` и нажмите `Запустить сканирование`.

Сканер только читает дерево каталогов и пишет найденные проблемы в события с `event_type = scan_detected`. Он не меняет файлы. Лимит задается так:

```yaml
scanner:
  max_scan_items: 10000
```

## Установка как Windows Service

Служба устанавливается через NSSM.

1. Скачайте NSSM: https://nssm.cc/download
2. Положите `nssm.exe` в:

```text
scripts\tools\nssm.exe
```

Или добавьте `nssm.exe` в `PATH`.

3. Запустите PowerShell от администратора:

```powershell
Set-ExecutionPolicy -Scope Process Bypass
.\scripts\install_service.ps1
.\scripts\start_service.ps1
```

Скрипт установит зависимости, создаст службу `LongPathGuard`, настроит автозапуск и restart on failure через NSSM. Служба запускает uvicorn на host/port из `config/config.yaml`; по умолчанию это `127.0.0.1:8787`.

Остановка:

```powershell
.\scripts\stop_service.ps1
```

Удаление:

```powershell
.\scripts\uninstall_service.ps1
```

## Логи и данные

- База данных: `data/longpathguard.db`
- Лог приложения: `data/longpathguard.log`
- Логи службы NSSM: `data/service.out.log`, `data/service.err.log`

## Audit only

LongPathGuard v0.1.0:

- не делает карантин;
- не удаляет файлы;
- не переименовывает файлы;
- не перемещает файлы;
- не устанавливает драйвер файловой системы;
- не использует Docker, PostgreSQL или React.
