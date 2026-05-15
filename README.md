# Журнал МПТ

Django-приложение для учета учебной успеваемости: группы, студенты, преподаватели, дисциплины, курсы, оценки, посещаемость, отчеты, чаты и REST API.

## Что нужно установить

- Python 3.12+
- PostgreSQL 16, если приложение запускается с настройками по умолчанию
- Docker Desktop, если нужен запуск через Docker

## Быстрый запуск через Docker

```powershell
docker compose up --build
```

После запуска приложение доступно по адресу:

```text
http://localhost:8000/
```

Docker поднимает PostgreSQL, применяет миграции и при пустой базе загружает начальные данные из `docker/seed/initial_data.json`.

## Локальный запуск без Docker

Создать и активировать виртуальное окружение:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

Установить зависимости:

```powershell
pip install -r requirements.txt
```

По умолчанию проект ожидает PostgreSQL:

```text
database: performance_db
user: postgres
password: 1
host: localhost
port: 5432
```

Применить миграции и создать базовые роли:

```powershell
python manage.py init_app
```

При необходимости создать демо-данные:

```powershell
python manage.py seed_demo_data
```

Запустить сервер:

```powershell
python manage.py runserver
```

## Запуск с SQLite

Для локальной разработки можно переключиться на SQLite:

```powershell
$env:DB_ENGINE = "sqlite"
python manage.py init_app
python manage.py seed_demo_data
python manage.py runserver
```

База будет храниться в `db.sqlite3` в корне проекта.

## Пользователи системы с тестовыми данными


| Роль | Логин | Пароль |
| --- | --- | --- |
| Администратор | `kogado` | `admin123` |
| Преподаватель | `on-shestakova_37164e75` | `teacher123` |
| Студент | `student_96_10` | `QWERTbvcxz12` |
| Родитель | `Мама` | `parent123` |

## Основные адреса

- `/` - главная страница приложения
- `/admin/` - стандартная админ-панель Django
- `/control/` - пользовательская административная панель
- `/accounts/login/` - вход в систему
- `/api/` - корень REST API
- `/api/docs/` - Swagger-документация API
- `/api/schema/` - OpenAPI-схема

## Важные команды

```powershell
python manage.py init_app
python manage.py seed_demo_data
python manage.py createsuperuser
python manage.py test
python manage.py spectacular --file schema.yml
```

Команды интеграции с расписанием МПТ:

```powershell
python manage.py sync_mpt_catalog
python manage.py sync_mpt_groups
python manage.py sync_mpt_teachers
```

## Настройки окружения

Основные переменные:

| Переменная | Назначение | Значение по умолчанию |
| --- | --- | --- |
| `DJANGO_SECRET_KEY` | секретный ключ Django | `dev-secret-key-change-me` |
| `DJANGO_DEBUG` | режим отладки, `1` или `0` | `1` |
| `DJANGO_ALLOWED_HOSTS` | разрешенные хосты через запятую | `*` |
| `DB_ENGINE` | `postgres` или `sqlite` | `postgres` |
| `POSTGRES_DB` | имя базы PostgreSQL | `performance_db` |
| `POSTGRES_USER` | пользователь PostgreSQL | `postgres` |
| `POSTGRES_PASSWORD` | пароль PostgreSQL | `1` |
| `POSTGRES_HOST` | хост PostgreSQL | `localhost` |
| `POSTGRES_PORT` | порт PostgreSQL | `5432` |
| `MPT_SYNC_BASE_URL` | базовый URL для синхронизации | `https://mpt.ru` |
| `MPT_DEFAULT_SEMESTER` | семестр по умолчанию | `2025/2026-2` |

## Desktop-версия

Проект содержит desktop-обертку на `pywebview`.

Для подготовки базы под desktop-приложение:

```powershell
.\scripts\start_desktop_db.ps1
```

Скрипт поднимет PostgreSQL через Docker и загрузит seed-данные. После этого можно запускать собранное приложение из `dist\MPT Journal\MPT Journal.exe`.

Сборка desktop-версии:

```powershell
.\scripts\build_desktop.ps1
```

## Структура проекта

- `config/` - настройки Django, URL, API router, сериализаторы
- `core/` - базовые справочники, главная страница, административная панель
- `users/` - пользователи, студенты, преподаватели, родители, чаты
- `grading/` - курсы, оценки, занятия, посещаемость
- `reports/` - отчеты и экспорт
- `integration/` - синхронизация с внешними источниками
- `templates/` - общие шаблоны
- `docker/` - entrypoint и seed-данные для Docker
- `scripts/` - вспомогательные скрипты сборки и документации

## Проверка работоспособности

Минимальная проверка после установки:

```powershell
python manage.py check
python manage.py test
```

Если используется Docker:

```powershell
docker compose ps
docker compose logs web
```
