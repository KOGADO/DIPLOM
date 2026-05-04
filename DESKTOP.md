# Windows desktop build

Desktop-версия запускает Django-приложение внутри локального окна Windows через `pywebview`.

## Запуск

На рабочем столе создан ярлык:

```text
Журнал МПТ.lnk
```

Готовый файл после сборки:

```text
dist\MPT Journal\MPT Journal.exe
```

Окно приложения называется `Журнал МПТ`.

## База данных

Desktop-версия использует те же настройки базы, что и веб-версия. Сейчас приложение настроено на локальный PostgreSQL:

```text
DB_ENGINE=postgres
POSTGRES_DB=performance_db
POSTGRES_USER=postgres
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
```

То есть данные не вшиваются в `.exe`, а остаются в PostgreSQL на этом компьютере.

Если нужно быстро показать desktop-версию на другом компьютере через Docker PostgreSQL, сначала выполните:

```powershell
powershell -ExecutionPolicy Bypass -File scripts\start_desktop_db.ps1
```

После этого можно запускать `dist\MPT Journal\MPT Journal.exe`.

Старый SQLite-файл убран из корня проекта в резерв:

```text
database_backups\
```

## Пересборка

```powershell
powershell -ExecutionPolicy Bypass -File scripts\build_desktop.ps1
```

## Пользовательские файлы

В desktop-режиме загруженные файлы хранятся в:

```text
%LOCALAPPDATA%\MPT Journal\media
```
