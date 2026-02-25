# Учет успеваемости (Django 5)

Полностью рабочее веб-приложение для учета успеваемости, посещаемости и отчетности.

## Стек
- Python 3.11+
- Django 5.x
- SQLite по умолчанию
- PostgreSQL через переменные окружения
- Django Templates + Bootstrap 5
- Django ORM, Forms, Validators
- Аутентификация Django + роли через Groups/Permissions
- DRF (read-only endpoints)

## Структура проекта

```text
курсач 3.0/
  manage.py
  requirements.txt
  README.md
  config/
    settings.py
    urls.py
    asgi.py
    wsgi.py
  core/
    models.py
    forms.py
    views.py
    urls.py
    permissions.py
    admin.py
    migrations/0001_initial.py
    templates/core/
      dashboard.html
      form.html
      confirm_delete.html
      group_list.html
      subject_list.html
      reports_index.html
  users/
    models.py
    forms.py
    views.py
    urls.py
    admin.py
    tests.py
    migrations/0001_initial.py
    management/commands/seed_demo_data.py
    templates/users/
      teacher_list.html
      student_list.html
      student_detail.html
  grading/
    models.py
    forms.py
    views.py
    urls.py
    serializers.py
    api_views.py
    admin.py
    tests.py
    migrations/0001_initial.py
    templates/grading/
      course_list.html
      course_detail.html
      attendance_mark.html
  reports/
    views.py
    urls.py
    forms.py
    templates/reports/
      group_statement.html
      top_students.html
      attendance_report.html
  templates/
    base.html
    registration/login.html
```

## Основные роли
- `Admin`: полный доступ
- `Teacher`: свои курсы/группы, ввод оценок и посещаемости
- `Student`: только свой профиль и свои данные

## Быстрый запуск

### 1. Создать и активировать venv

Windows (PowerShell):
```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

Linux/macOS:
```bash
python -m venv .venv
source .venv/bin/activate
```

### 2. Установить зависимости
```bash
pip install -r requirements.txt
```

### 3. Применить миграции
```bash
python manage.py makemigrations
python manage.py migrate
```

Диагностика миграций:
```bash
python manage.py showmigrations core
python manage.py migrate --plan
python manage.py sqlmigrate core 0005
```

Ошибка `no such column: core_subject.department_id` обычно означает, что миграция добавления поля не применена
или история миграций в БД разошлась с кодом.

### 4. Создать суперпользователя
```bash
python manage.py createsuperuser
```

### 5. Инициализировать приложение одной командой (опционально)
```bash
python manage.py init_app
```

Команда `init_app`:
- безопасно повторно запускает `migrate`
- создает группы ролей `Teachers`, `Students`, `Admins` (если их нет)
- создает базовое отделение `Общее отделение` (если его нет)

### 6. Загрузить данные с сайта МПТ (без демо)
```bash
python manage.py sync_mpt_catalog --semester "2025/2026-2"
```

### 7. (Опционально) Загрузить демо-данные
```bash
python manage.py seed_demo_data
```

### 8. Запустить сервер
```bash
python manage.py runserver
```

Если база еще не инициализирована, дашборд покажет предупреждение:
`База данных не инициализирована. Выполните: python manage.py migrate`

## Демо-логины
- `admin / admin123`
- `teacher1 / teacher123`
- `teacher2 / teacher123`
- `student1 / student123`

## Переключение на PostgreSQL
По умолчанию используется SQLite. Для PostgreSQL:

```powershell
$env:DB_ENGINE='postgres'
$env:POSTGRES_DB='performance_db'
$env:POSTGRES_USER='postgres'
$env:POSTGRES_PASSWORD='postgres'
$env:POSTGRES_HOST='localhost'
$env:POSTGRES_PORT='5432'
python manage.py migrate
```

## Основные URL
- `/` — ролевой дашборд
- `/groups/`, `/students/`, `/teachers/`, `/subjects/`, `/courses/`
- `/courses/<id>/` — детали курса
- `/students/<id>/` — профиль студента
- `/reports/` — индекс отчетов
- `/reports/group-statement/`
- `/reports/top-students/`
- `/reports/attendance/`
- `/api/my-grades/`
- `/api/my-courses/`

## Тесты
```bash
python manage.py test
```

Покрыты:
- расчет среднего балла
- проверка прав доступа (студент не видит чужой профиль)

## Расширение
- Новый тип оценки: добавить значение в `grading.models.Grade.GradeType`.
- Новый формат семестра: поменять валидацию поля `Course.semester`.
- Новый экспорт: добавить обработчик `?export=csv`/`xlsx` в `reports/views.py`.

## Система оценивания 2-5

Используется 5-балльная шкала:
- `2` — неудовлетворительно
- `3` — удовлетворительно
- `4` — хорошо
- `5` — отлично

Миграция `grading.0003_grade_value_five_point_scale` конвертирует старые оценки:
- `90–100 -> 5`
- `75–89 -> 4`
- `60–74 -> 3`
- `0–59 -> 2`

Если в базе уже шкала `2..5`, данные не меняются.  
Если в базе шкала `1..5`, значение `1` нормализуется до `2`.

## Синхронизация с mpt.ru

Источник: `https://mpt.ru/raspisanie/` (основной), с уважением `robots.txt`.

### Команды

```bash
python manage.py sync_mpt_catalog --semester "2025/2026-2"
python manage.py sync_mpt_catalog --dry-run
python manage.py sync_mpt_groups --dry-run
python manage.py sync_mpt_teachers --dry-run
```

Дополнительно:
- `--delay 0.5` (пауза между запросами)
- `--timeout 15` (таймаут HTTP)

### Настройки

В `config/settings.py`:
- `MPT_SYNC_BASE_URL="https://mpt.ru"`
- `MPT_SYNC_SCHEDULE_PATH="/raspisanie/"`
- `MPT_SYNC_TIMEOUT=15`
- `MPT_SYNC_DELAY_SECONDS=0.5`
- `MPT_SYNC_USER_AGENT="mpt-progress-tracker/1.0 (educational project)"`
- `MPT_DEFAULT_SEMESTER="2025/2026-2"`

### Как поменять семестр

- Через аргумент команды: `--semester "2025/2026-2"`
- Или через `MPT_DEFAULT_SEMESTER` в settings/env.

### Если HTML на сайте изменится

- Основная точка: `integration/providers/mpt_schedule_provider.py`
- Обновить методы:
  - `_find_group_anchors`
  - `_extract_group_blocks`
  - `_parse_tables`
  - `_parse_text_lines`
- После изменений прогнать:
  - `python manage.py test integration.tests.test_parsing`
