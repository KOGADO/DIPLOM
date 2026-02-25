import csv

from django.contrib.auth.decorators import login_required
from django.db.models import Avg, Count, Q
from django.http import HttpResponse
from django.shortcuts import render

from core.models import Group, Subject
from grading.models import Attendance, Course, Grade
from users.models import Student, Teacher


def _is_admin(user):
    return user.is_superuser or user.groups.filter(name='Admin').exists()


def _is_teacher(user):
    return user.groups.filter(name='Teacher').exists()


def _teacher_profile(user):
    if not _is_teacher(user):
        return None
    return Teacher.objects.filter(user=user).first()


def _can_view_reports(user):
    return _is_admin(user) or _is_teacher(user)


@login_required
def group_statement_report(request):
    if not _can_view_reports(request.user):
        return HttpResponse('Нет доступа', status=403)

    qs = Course.objects.select_related('subject', 'group', 'teacher__user')
    teacher = _teacher_profile(request.user)
    if teacher and not _is_admin(request.user):
        qs = qs.filter(teacher=teacher)

    group_id = request.GET.get('group')
    semester = request.GET.get('semester')
    subject_id = request.GET.get('subject')

    if group_id:
        qs = qs.filter(group_id=group_id)
    if semester:
        qs = qs.filter(semester=semester)
    if subject_id:
        qs = qs.filter(subject_id=subject_id)

    rows = []
    for course in qs.order_by('group__name', 'subject__name'):
        students = (
            Student.objects.filter(group=course.group)
            .select_related('user')
            .annotate(avg=Avg('grades__value', filter=Q(grades__course=course)))
            .order_by('user__last_name', 'user__first_name')
        )
        for student in students:
            avg_value = student.avg or 0
            rows.append({'course': course, 'student': student, 'avg': avg_value, 'final': round(avg_value)})

    if request.GET.get('export') == 'csv':
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="group_statement.csv"'
        writer = csv.writer(response)
        writer.writerow(['Курс', 'Студент', 'Средний', 'Итог'])
        for row in rows:
            writer.writerow([row['course'], row['student'], row['avg'], row['final']])
        return response

    courses_for_filters = Course.objects.select_related('subject', 'group', 'teacher__user')
    if teacher and not _is_admin(request.user):
        courses_for_filters = courses_for_filters.filter(teacher=teacher)

    context = {
        'rows': rows,
        'groups': Group.objects.filter(courses__in=courses_for_filters).distinct().order_by('name'),
        'subjects': Subject.objects.filter(courses__in=courses_for_filters).distinct().order_by('name'),
        'semesters': courses_for_filters.values_list('semester', flat=True).distinct().order_by('semester'),
        'selected': {'group': group_id or '', 'subject': subject_id or '', 'semester': semester or ''},
    }
    return render(request, 'reports/group_statement.html', context)


@login_required
def top_students_report(request):
    if not _can_view_reports(request.user):
        return HttpResponse('Нет доступа', status=403)

    teacher = _teacher_profile(request.user)
    students = Student.objects.select_related('user', 'group')

    if teacher and not _is_admin(request.user):
        students = students.filter(group__courses__teacher=teacher).distinct()

    group_id = request.GET.get('group')
    if group_id:
        students = students.filter(group_id=group_id)

    students = students.annotate(avg_grade=Avg('grades__value'))
    top = students.order_by('-avg_grade', 'user__last_name')[:5]
    bottom = students.order_by('avg_grade', 'user__last_name')[:5]

    if request.GET.get('export') == 'csv':
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="top_bottom_students.csv"'
        writer = csv.writer(response)
        writer.writerow(['Категория', 'Студент', 'Группа', 'Средний'])
        for student in top:
            writer.writerow(['TOP', student, student.group, student.avg_grade or 0])
        for student in bottom:
            writer.writerow(['ANTI-TOP', student, student.group, student.avg_grade or 0])
        return response

    groups = Group.objects.all()
    if teacher and not _is_admin(request.user):
        groups = groups.filter(courses__teacher=teacher).distinct()

    return render(
        request,
        'reports/top_students.html',
        {'top': top, 'bottom': bottom, 'groups': groups.order_by('name'), 'selected_group': group_id or ''},
    )


@login_required
def attendance_report(request):
    if not _can_view_reports(request.user):
        return HttpResponse('Нет доступа', status=403)

    teacher = _teacher_profile(request.user)
    group_id = request.GET.get('group')
    course_id = request.GET.get('course')

    attendance_qs = Attendance.objects.select_related(
        'student__user', 'student__group', 'lesson__course__group', 'lesson__course__subject'
    )

    if teacher and not _is_admin(request.user):
        attendance_qs = attendance_qs.filter(lesson__course__teacher=teacher)
    if group_id:
        attendance_qs = attendance_qs.filter(student__group_id=group_id)
    if course_id:
        attendance_qs = attendance_qs.filter(lesson__course_id=course_id)

    by_students = (
        attendance_qs.values('student__id', 'student__user__first_name', 'student__user__last_name', 'student__group__name')
        .annotate(
            total=Count('id'),
            present=Count('id', filter=Q(status__in=[Attendance.Status.PRESENT, Attendance.Status.LATE])),
        )
        .order_by('student__group__name', 'student__user__last_name')
    )

    by_lessons = (
        attendance_qs.values('lesson__id', 'lesson__date', 'lesson__course__subject__name', 'lesson__course__group__name')
        .annotate(
            total=Count('id'),
            present=Count('id', filter=Q(status__in=[Attendance.Status.PRESENT, Attendance.Status.LATE])),
        )
        .order_by('-lesson__date')
    )

    if request.GET.get('export') == 'csv':
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="attendance_report.csv"'
        writer = csv.writer(response)
        writer.writerow(['Секция', 'Сущность', 'Посещаемость %'])
        for row in by_students:
            full_name = f"{row['student__user__last_name']} {row['student__user__first_name']}".strip()
            present = round((row['present'] / row['total']) * 100, 2) if row['total'] else 0
            writer.writerow(['Студент', f"{full_name} ({row['student__group__name']})", present])
        for row in by_lessons:
            present = round((row['present'] / row['total']) * 100, 2) if row['total'] else 0
            writer.writerow(['Занятие', f"{row['lesson__date']} {row['lesson__course__subject__name']} [{row['lesson__course__group__name']}]", present])
        return response

    courses = Course.objects.select_related('subject', 'group')
    groups = Group.objects.order_by('name')
    if teacher and not _is_admin(request.user):
        courses = courses.filter(teacher=teacher)
        groups = groups.filter(courses__teacher=teacher).distinct()

    return render(
        request,
        'reports/attendance_report.html',
        {
            'by_students': by_students,
            'by_lessons': by_lessons,
            'courses': courses.order_by('group__name', 'subject__name'),
            'groups': groups,
            'selected': {'group': group_id or '', 'course': course_id or ''},
        },
    )
