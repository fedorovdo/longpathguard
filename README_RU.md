# LongPathGuard

LongPathGuard v0.1 - микро-приложение для Windows Server 2022, которое наблюдает за новыми событиями в файловой папке и помогает администратору видеть слишком длинные имена файлов, папок и полные пути.

Важный принцип v0.1: приложение работает только в режиме аудита. Оно ничего не удаляет, не перемещает, не переименовывает и не меняет в файловой системе.

## Возможности

- Watchdog-наблюдение за новыми событиями `created`, `renamed`, `modified`.
- Проверка длины полного пути и имени файла или папки.
- SQLite-журнал `data/longpathguard.db`.
- Web UI на FastAPI и Jinja2 без React и Docker.
- Русский интерфейс по умолчанию, переключение RU/EN.
- CSV-экспорт событий.
- Ручной безопасный сканер существующих файлов.
- Заготовка Telegram и Email уведомлений.
- Установка как Windows Service через NSSM.

## Требования

- Windows Server 2022.
- Python 3.12.
- Доступ администратора для установки службы.

## Установка Python 3.12

1. Скачайте Python 3.12 с официального сайта: https://www.python.org/downloads/windows/
2. Во время установки включите опцию `Add python.exe to PATH`.
3. Проверьте:

```powershell
python --version
```

## Первый запуск

Откройте PowerShell в корне проекта и выполните:

```powershell
Set-ExecutionPolicy -Scope Process Bypass
.\scripts\run_dev.ps1
```

Скрипт создаст `.venv`, установит зависимости и запустит сервер:

```text
http://server-ip:8787
```

Локально можно открыть:

```text
http://localhost:8787
```

## Настройка наблюдаемой папки

По умолчанию используется:

```yaml
watcher:
  root_path: D:\fs
```

Изменить путь можно в `config/config.yaml` или через страницу `Настройки`.

Если папка не существует, приложение продолжит работать, покажет ошибку на панели и не запустит watcher до исправления пути.

## Безопасный скан существующих файлов

Скан не запускается автоматически. Откройте страницу `Сканирование` и нажмите `Запустить сканирование`.

Сканер только читает дерево каталогов и записывает найденные длинные пути в события с типом `scan_detected`. Лимит задается параметром:

```yaml
scanner:
  max_scan_items: 10000
```

## Установка службы Windows

LongPathGuard использует NSSM.

1. Скачайте NSSM: https://nssm.cc/download
2. Положите `nssm.exe` в:

```text
scripts\tools\nssm.exe
```

Или добавьте `nssm.exe` в `PATH`.

3. Установите службу из PowerShell с правами администратора:

```powershell
Set-ExecutionPolicy -Scope Process Bypass
.\scripts\install_service.ps1
.\scripts\start_service.ps1
```

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

## Пороги по умолчанию

```yaml
thresholds:
  max_full_path_warning: 220
  max_full_path_danger: 240
  max_full_path_critical: 260
  max_name_length: 120
```

Severity:

- `ok`
- `warning`
- `danger`
- `critical`
- `long_name`
- `critical_long_name`

## Что v0.1 не делает

- Не делает карантин.
- Не удаляет файлы.
- Не переименовывает файлы.
- Не перемещает файлы.
- Не устанавливает драйвер файловой системы.
- Не использует Docker, PostgreSQL или React.
