from django.contrib.auth.decorators import login_required
from django.db.models import Avg, Count, Q
from django.http import HttpResponse
from django.shortcuts import render

from core.models import Group, Subject
from grading.models import Attendance, Course
from reports.export_utils import export_csv_response, export_pdf_response, export_xlsx_response
from users.models import Student, Teacher


def _is_admin(user):
    return user.is_superuser or user.groups.filter(name="Admin").exists()


def _is_teacher(user):
    return user.groups.filter(name="Teacher").exists()


def _teacher_profile(user):
    if not _is_teacher(user):
        return None
    return Teacher.objects.filter(user=user).first()


def _can_view_reports(user):
    return _is_admin(user) or _is_teacher(user)


@login_required
def group_statement_report(request):
    if not _can_view_reports(request.user):
        return HttpResponse("РќРµС‚ РґРѕСЃС‚СѓРїР°", status=403)

    qs = Course.objects.select_related("subject", "group", "teacher__user")
    teacher = _teacher_profile(request.user)
    if teacher and not _is_admin(request.user):
        qs = qs.filter(teacher=teacher)

    group_id = request.GET.get("group")
    semester = request.GET.get("semester")
    subject_id = request.GET.get("subject")

    if group_id:
        qs = qs.filter(group_id=group_id)
    if semester:
        qs = qs.filter(semester=semester)
    if subject_id:
        qs = qs.filter(subject_id=subject_id)

    rows = []
    for course in qs.order_by("group__name", "subject__name"):
        students = (
            Student.objects.filter(group=course.group)
            .select_related("user")
            .annotate(avg=Avg("grades__value", filter=Q(grades__course=course)))
            .order_by("user__last_name", "user__first_name")
        )
        for student in students:
            avg_value = student.avg or 0
            rows.append({"course": course, "student": student, "avg": avg_value, "final": round(avg_value)})

    export_format = request.GET.get("export")
    if export_format in {"csv", "xlsx", "pdf"}:
        headers = ["Курс", "Студент", "Средний", "Итог"]
        export_rows = [[row["course"], row["student"], round(row["avg"], 2), row["final"]] for row in rows]
        if export_format == "csv":
            return export_csv_response("group_statement", headers, export_rows)
        if export_format == "xlsx":
            return export_xlsx_response("group_statement", "Ведомость", headers, export_rows)
        return export_pdf_response("group_statement", "Ведомость группы", headers, export_rows)

    courses_for_filters = Course.objects.select_related("subject", "group", "teacher__user")
    if teacher and not _is_admin(request.user):
        courses_for_filters = courses_for_filters.filter(teacher=teacher)

    context = {
        "rows": rows,
        "groups": Group.objects.filter(courses__in=courses_for_filters).distinct().order_by("name"),
        "subjects": Subject.objects.filter(courses__in=courses_for_filters).distinct().order_by("name"),
        "semesters": courses_for_filters.values_list("semester", flat=True).distinct().order_by("semester"),
        "selected": {"group": group_id or "", "subject": subject_id or "", "semester": semester or ""},
    }
    return render(request, "reports/group_statement.html", context)


@login_required
def top_students_report(request):
    if not _can_view_reports(request.user):
        return HttpResponse("РќРµС‚ РґРѕСЃС‚СѓРїР°", status=403)

    teacher = _teacher_profile(request.user)
    students = Student.objects.select_related("user", "group")

    if teacher and not _is_admin(request.user):
        students = students.filter(group__courses__teacher=teacher).distinct()

    group_id = request.GET.get("group")
    if group_id:
        students = students.filter(group_id=group_id)

    students = students.annotate(avg_grade=Avg("grades__value"))
    top = students.order_by("-avg_grade", "user__last_name")[:5]
    bottom = students.order_by("avg_grade", "user__last_name")[:5]

    export_format = request.GET.get("export")
    if export_format in {"csv", "xlsx", "pdf"}:
        headers = ["Категория", "Студент", "Группа", "Средний"]
        export_rows = []
        for student in top:
            export_rows.append(["TOP", student, student.group, round(student.avg_grade or 0, 2)])
        for student in bottom:
            export_rows.append(["ANTI-TOP", student, student.group, round(student.avg_grade or 0, 2)])
        if export_format == "csv":
            return export_csv_response("top_bottom_students", headers, export_rows)
        if export_format == "xlsx":
            return export_xlsx_response("top_bottom_students", "Топ студенты", headers, export_rows)
        return export_pdf_response("top_bottom_students", "Топ/анти-топ студентов", headers, export_rows)

    groups = Group.objects.all()
    if teacher and not _is_admin(request.user):
        groups = groups.filter(courses__teacher=teacher).distinct()

    return render(
        request,
        "reports/top_students.html",
        {"top": top, "bottom": bottom, "groups": groups.order_by("name"), "selected_group": group_id or ""},
    )


@login_required
def attendance_report(request):
    if not _can_view_reports(request.user):
        return HttpResponse("РќРµС‚ РґРѕСЃС‚СѓРїР°", status=403)

    teacher = _teacher_profile(request.user)
    group_id = request.GET.get("group")
    course_id = request.GET.get("course")

    attendance_qs = Attendance.objects.select_related(
        "student__user", "student__group", "lesson__course__group", "lesson__course__subject"
    )

    if teacher and not _is_admin(request.user):
        attendance_qs = attendance_qs.filter(lesson__course__teacher=teacher)
    if group_id:
        attendance_qs = attendance_qs.filter(student__group_id=group_id)
    if course_id:
        attendance_qs = attendance_qs.filter(lesson__course_id=course_id)

    by_students = (
        attendance_qs.values("student__id", "student__user__first_name", "student__user__last_name", "student__group__name")
        .annotate(
            total=Count("id"),
            present=Count("id", filter=Q(status__in=[Attendance.Status.PRESENT, Attendance.Status.LATE])),
        )
        .order_by("student__group__name", "student__user__last_name")
    )

    by_lessons = (
        attendance_qs.values("lesson__id", "lesson__date", "lesson__course__subject__name", "lesson__course__group__name")
        .annotate(
            total=Count("id"),
            present=Count("id", filter=Q(status__in=[Attendance.Status.PRESENT, Attendance.Status.LATE])),
        )
        .order_by("-lesson__date")
    )

    export_format = request.GET.get("export")
    if export_format in {"csv", "xlsx", "pdf"}:
        headers = ["Секция", "Сущность", "Посещаемость %"]
        export_rows = []
        for row in by_students:
            full_name = f"{row['student__user__last_name']} {row['student__user__first_name']}".strip()
            present = round((row["present"] / row["total"]) * 100, 2) if row["total"] else 0
            export_rows.append(["Студент", f"{full_name} ({row['student__group__name']})", present])
        for row in by_lessons:
            present = round((row["present"] / row["total"]) * 100, 2) if row["total"] else 0
            export_rows.append(
                [
                    "Занятие",
                    f"{row['lesson__date']} {row['lesson__course__subject__name']} [{row['lesson__course__group__name']}]",
                    present,
                ]
            )
        if export_format == "csv":
            return export_csv_response("attendance_report", headers, export_rows)
        if export_format == "xlsx":
            return export_xlsx_response("attendance_report", "Посещаемость", headers, export_rows)
        return export_pdf_response("attendance_report", "Отчет по посещаемости", headers, export_rows)

    courses = Course.objects.select_related("subject", "group")
    groups = Group.objects.order_by("name")
    if teacher and not _is_admin(request.user):
        courses = courses.filter(teacher=teacher)
        groups = groups.filter(courses__teacher=teacher).distinct()

    return render(
        request,
        "reports/attendance_report.html",
        {
            "by_students": by_students,
            "by_lessons": by_lessons,
            "courses": courses.order_by("group__name", "subject__name"),
            "groups": groups,
            "selected": {"group": group_id or "", "course": course_id or ""},
        },
    )
