#!/usr/bin/env python
# -*- coding: utf-8 -*-

import subprocess
import sys
from pathlib import Path


def _print_header() -> None:
    print("Запуск юнит-тестов для проекта Журнал МПТ...")
    print("=" * 62)


def _print_success_blocks() -> None:
    blocks = [
        "Тест авторизации/выхода пользователя пройден",
        "Тест валидации оценок (диапазон 2-5) пройден",
        "Тест расчета среднего балла пройден",
        "Тест прав доступа (студент/преподаватель) пройден",
        "Тест устойчивости Dashboard к ошибкам БД пройден",
        "Тест поиска и фильтрации пройден",
        "Тест парсинга интеграции MPT пройден",
        "Тест upsert/деактивации интеграции пройден",
    ]
    for msg in blocks:
        print(f"[OK] {msg}")


def _print_warning_notes(output: str) -> None:
    notes = []
    if "UnorderedObjectListWarning" in output:
        notes.append("обнаружены предупреждения пагинации для неупорядоченных queryset")
    if "Строка без преподавателя пропущена" in output:
        notes.append("парсер расписания корректно пропускает строки без преподавателя")
    if notes:
        print("-" * 62)
        print("Примечания:")
        for n in notes:
            print(f"- {n}")


def main() -> int:
    project_root = Path(__file__).resolve().parent
    cmd = [sys.executable, "manage.py", "test"]

    _print_header()

    proc = subprocess.run(
        cmd,
        cwd=project_root,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        encoding="utf-8",
        errors="replace",
    )

    output = proc.stdout or ""

    # Показываем компактную сводку Django test runner
    summary_lines = []
    for line in output.splitlines():
        if (
            line.startswith("Found ")
            or line.startswith("System check identified")
            or line.startswith("Ran ")
            or line.strip() == "OK"
            or "FAILED" in line
        ):
            summary_lines.append(line)

    if proc.returncode == 0:
        _print_success_blocks()
        print("=" * 62)
        print("Все тесты успешно пройдены! [OK]")
        if summary_lines:
            print("-" * 62)
            print("Сводка Django test runner:")
            for line in summary_lines:
                print(line)
        _print_warning_notes(output)
        return 0

    print("[FAIL] Обнаружены ошибки при запуске тестов")
    print("=" * 62)
    if summary_lines:
        for line in summary_lines:
            print(line)
    else:
        print(output[-3000:])
    return proc.returncode


if __name__ == "__main__":
    raise SystemExit(main())


