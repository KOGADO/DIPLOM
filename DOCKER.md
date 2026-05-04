# Docker запуск

Этот комплект нужен, чтобы быстро показать проект на другом компьютере.
Docker поднимает PostgreSQL, применяет миграции и один раз загружает дамп твоей текущей базы.

## Что передать коллеге

Передай всю папку проекта, кроме тяжелых временных папок:

```text
build\
dist\
.venv\
__pycache__\
database_backups\
```

Файл с данными уже лежит здесь:

```text
docker/seed/initial_data.json
```

Docker использует облегченный список зависимостей:

```text
requirements.docker.txt
```

## Веб-версия одной командой

Перед запуском должен быть открыт Docker Desktop.

```powershell
docker compose up --build
```

После запуска открыть:

```text
http://127.0.0.1:8000/
```

При первом старте контейнер:

1. дождется PostgreSQL;
2. выполнит `python manage.py migrate`;
3. загрузит `docker/seed/initial_data.json`, если база еще пустая;
4. запустит Django на `0.0.0.0:8000`.

Повторные запуски не дублируют данные: загрузка пропускается, если в базе уже есть пользователи.

## Desktop-версия через Docker PostgreSQL

Если нужно показать именно `exe`, можно поднять только базу с твоими данными:

```powershell
powershell -ExecutionPolicy Bypass -File scripts\start_desktop_db.ps1
```

После этого запустить:

```text
dist\MPT Journal\MPT Journal.exe
```

Desktop-приложение подключается к той же базе:

```text
POSTGRES_DB=performance_db
POSTGRES_USER=postgres
POSTGRES_PASSWORD=1
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
```

## Обновить дамп данными с твоего компьютера

Когда в локальной PostgreSQL появились новые данные, обнови fixture:

```powershell
powershell -ExecutionPolicy Bypass -File scripts\export_seed.ps1
```

После этого передавай проект заново.

## Сбросить Docker-базу и залить дамп заново

Команда удалит Docker volume с PostgreSQL:

```powershell
docker compose down -v
docker compose up --build
```
