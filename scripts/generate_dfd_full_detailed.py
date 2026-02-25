from pathlib import Path
from xml.sax.saxutils import escape


def vertex(cell_id: str, value: str, style: str, x: int, y: int, w: int, h: int) -> str:
    return (
        f'<mxCell id="{cell_id}" value="{escape(value)}" style="{style}" vertex="1" parent="1">'
        f'<mxGeometry x="{x}" y="{y}" width="{w}" height="{h}" as="geometry"/>'
        f"</mxCell>"
    )


def edge(cell_id: str, value: str, style: str, source: str, target: str) -> str:
    return (
        f'<mxCell id="{cell_id}" value="{escape(value)}" style="{style}" edge="1" parent="1" source="{source}" target="{target}">'
        f'<mxGeometry relative="1" as="geometry"/>'
        f"</mxCell>"
    )


def build_xml() -> str:
    cube_style = "shape=cube;whiteSpace=wrap;html=1;boundedLbl=1;backgroundOutline=1;darkOpacity=0.05;darkOpacity2=0.1;strokeWidth=2;fontSize=14;"
    proc_style = "rounded=1;whiteSpace=wrap;html=1;strokeWidth=2;fontSize=12;"
    store_style = "shape=partialRectangle;whiteSpace=wrap;html=1;right=0;strokeWidth=2;fontSize=11;"
    edge_style = "endArrow=classic;html=1;rounded=0;edgeStyle=orthogonalEdgeStyle;fontSize=10;"

    cells: list[str] = []
    cells.append(vertex("title", "DFD полная детализированная (как в примере)", "text;html=1;strokeColor=none;fillColor=none;align=center;verticalAlign=middle;fontStyle=1;fontSize=20;", 1400, 20, 1600, 30))
    cells.append(vertex("student", "Студент", cube_style, 80, 80, 1300, 110))
    cells.append(vertex("teacher", "Преподаватель", cube_style, 1420, 80, 1200, 110))
    cells.append(vertex("admin", "Администратор", cube_style, 2660, 80, 1200, 110))
    cells.append(vertex("zone", "Декомпозиция входных потоков и решений", "rounded=1;whiteSpace=wrap;html=1;strokeWidth=2;fontStyle=1;fontSize=13;dashed=1;", 80, 230, 3780, 1500))
    cells.append(vertex("core", "Ядро системы\nЖурнал МПТ", "rounded=1;whiteSpace=wrap;html=1;strokeWidth=2;fontStyle=1;fontSize=14;", 3340, 860, 500, 280))

    stores = [
        ("d_users", "D1\nПользователи и роли", 2920, 320),
        ("d_course", "D2\nКурсы и группы", 2920, 500),
        ("d_lessons", "D3\nЗанятия", 2920, 680),
        ("d_grades", "D4\nОценки и посещаемость", 2920, 860),
        ("d_files", "D5\nРаботы и комментарии", 2920, 1040),
        ("d_reports", "D6\nОтчеты и выгрузки", 2920, 1220),
    ]
    for sid, label, x, y in stores:
        cells.append(vertex(sid, label, store_style, x, y, 260, 110))
        cells.append(edge(f"core_{sid}", "чтение/запись", edge_style, "core", sid))

    # lane schema: input actor -> p1 -> deny/allow -> d1 -> p2 -> d2 -> p3 -> core
    lanes = [
        # student
        ("s_login", "student", 160, "Логин и пароль", "Проверить учетные данные", "Отказать во входе", "Разрешить вход", "Журнал авторизаций", "Проверить роль студента", "Пользователи и роли", "Выдать статус входа"),
        ("s_course", "student", 500, "Выбранный курс", "Проверить доступность курса", "Отказать в доступе к курсу", "Разрешить просмотр курса", "Журнал курсов", "Проверить наличие занятий", "Журнал занятий", "Вывести занятия"),
        ("s_stats", "student", 840, "Запрос статистики", "Проверить доступ к аналитике", "Отказать в доступе", "Разрешить просмотр статистики", "Журнал оценок", "Проверить данные по предметам", "Журнал посещаемости", "Вывести статистику"),
        # teacher
        ("t_grade", "teacher", 1280, "Оценка/посещаемость", "Проверить права преподавателя", "Отказать в изменении", "Разрешить изменение", "Журнал преподавателей", "Проверить диапазон оценки", "Журнал оценок", "Сохранить оценку"),
        ("t_topic", "teacher", 1620, "Тема занятия", "Проверить доступ к занятию", "Отказать в изменении", "Разрешить редактирование", "Журнал занятий", "Проверить формат темы", "История изменений", "Сохранить тему"),
        ("t_import", "teacher", 1960, "Файл импорта XLSX", "Проверить формат файла", "Отклонить файл", "Разрешить импорт", "Журнал импортов", "Проверить ФИО студентов", "Список студентов", "Создать записи студентов"),
        # admin
        ("a_users", "admin", 2360, "Управление пользователями", "Проверить права администратора", "Отказать в операции", "Разрешить операцию", "Пользователи и роли", "Проверить корректность данных", "Журнал пользователей", "Сохранить пользователя"),
        ("a_sync", "admin", 2700, "Запуск синхронизации", "Проверить параметры синхронизации", "Остановить синхронизацию", "Разрешить синхронизацию", "История синхронизации", "Сопоставить группы и курсы", "Каталог курсов", "Обновить данные MPT"),
    ]

    for code, actor, x, in_label, p1, deny, allow, d1, p2, d2, p3 in lanes:
        y = 340
        cells.append(vertex(f"{code}_p1", p1, proc_style, x, y, 250, 70))
        cells.append(vertex(f"{code}_deny", deny, "rounded=1;whiteSpace=wrap;html=1;strokeWidth=1.5;fontSize=11;", x + 140, y + 90, 170, 50))
        cells.append(vertex(f"{code}_allow", allow, "rounded=1;whiteSpace=wrap;html=1;strokeWidth=1.5;fontSize=11;", x + 140, y + 150, 170, 50))
        cells.append(vertex(f"{code}_d1", d1, store_style, x + 20, y + 230, 220, 95))
        cells.append(vertex(f"{code}_p2", p2, proc_style, x, y + 350, 250, 70))
        cells.append(vertex(f"{code}_d2", d2, store_style, x + 20, y + 445, 220, 95))
        cells.append(vertex(f"{code}_p3", p3, proc_style, x, y + 570, 250, 70))

        # input from actor
        actor_pos = {
            "student": 0.10 + (x - 160) / 3400.0,
            "teacher": 0.10 + (x - 1280) / 2200.0,
            "admin": 0.10 + (x - 2360) / 2200.0,
        }[actor]
        cells.append(edge(f"{code}_in", in_label, edge_style + f"exitX={actor_pos:.3f};exitY=1;entryX=0.5;entryY=0;", actor, f"{code}_p1"))
        cells.append(edge(f"{code}_e1", "нет", edge_style, f"{code}_p1", f"{code}_deny"))
        cells.append(edge(f"{code}_e2", "да", edge_style, f"{code}_p1", f"{code}_allow"))
        cells.append(edge(f"{code}_e3", "", edge_style, f"{code}_allow", f"{code}_d1"))
        cells.append(edge(f"{code}_e4", "идентификатор", edge_style, f"{code}_d1", f"{code}_p2"))
        cells.append(edge(f"{code}_e5", "", edge_style, f"{code}_p2", f"{code}_d2"))
        cells.append(edge(f"{code}_e6", "", edge_style, f"{code}_d2", f"{code}_p3"))
        cells.append(edge(f"{code}_e7", "в ядро", edge_style, f"{code}_p3", "core"))

    # outputs from core
    cells.append(edge("out_s1", "Уведомление о входе", edge_style + "exitX=0.02;exitY=0.10;entryX=0.90;entryY=1;", "core", "student"))
    cells.append(edge("out_s2", "Журнал и средний балл", edge_style + "exitX=0.02;exitY=0.28;entryX=0.98;entryY=1;", "core", "student"))
    cells.append(edge("out_t1", "Статус сохранения", edge_style + "exitX=0.46;exitY=0.01;entryX=0.75;entryY=1;", "core", "teacher"))
    cells.append(edge("out_t2", "Отчеты преподавателя", edge_style + "exitX=0.58;exitY=0.01;entryX=0.90;entryY=1;", "core", "teacher"))
    cells.append(edge("out_a1", "Сводка и статус синхронизации", edge_style + "exitX=0.98;exitY=0.20;entryX=0.85;entryY=1;", "core", "admin"))

    xml = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        '<mxfile host="app.diagrams.net" agent="Mozilla/5.0" version="29.5.1">',
        '  <diagram name="DFD полная детализированная" id="dfd-full-detailed">',
        '    <mxGraphModel dx="2400" dy="1400" grid="1" gridSize="10" guides="1" tooltips="1" connect="1" arrows="1" fold="1" page="1" pageScale="1" pageWidth="4200" pageHeight="1900" math="0" shadow="0">',
        "      <root>",
        '        <mxCell id="0"/>',
        '        <mxCell id="1" parent="0"/>',
    ]
    xml.extend("        " + c for c in cells)
    xml.extend(
        [
            "      </root>",
            "    </mxGraphModel>",
            "  </diagram>",
            "</mxfile>",
        ]
    )
    return "\n".join(xml)


def main() -> None:
    output = Path.cwd() / "dfd_mpt_full_detailed.drawio"
    output.write_text(build_xml(), encoding="utf-8")
    print(output)


if __name__ == "__main__":
    main()

