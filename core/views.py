from django.contrib.auth.decorators import login_required
from django.db.models import Avg, Count, Q
from django.db.utils import OperationalError, ProgrammingError
from django.core.paginator import Paginator
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse_lazy
from django.utils.decorators import method_decorator
from django.views.generic import CreateView, DeleteView, ListView, UpdateView
from openpyxl import Workbook

from core.forms import GroupForm, SubjectForm
from core.models import Group, Subject
from core.permissions import AdminRequiredMixin
from grading.models import Attendance, Course, Grade
from users.models import Parent, Student, Teacher


def _contains_casefold(haystack, needle):
    return needle.casefold() in (haystack or '').casefold()



def _build_admin_chart_data():
    students_by_group = list(
        Group.objects.annotate(total_students=Count('students'))
        .values('name', 'total_students')
        .order_by('-total_students', 'name')[:10]
    )

    courses_by_semester = list(
        Course.objects.values('semester')
        .annotate(total_courses=Count('id'))
        .order_by('semester')
    )

    avg_grade_by_subject = list(
        Grade.objects.values('course__subject__name')
        .annotate(avg_grade=Avg('value'), grades_total=Count('id'))
        .order_by('-avg_grade', 'course__subject__name')[:10]
    )

    attendance_by_group = list(
        Attendance.objects.values('lesson__course__group__name')
        .annotate(
            total=Count('id'),
            present=Count(
                'id',
                filter=Q(
                    status__in=[Attendance.Status.PRESENT, Attendance.Status.LATE]
                ),
            ),
        )
        .order_by('lesson__course__group__name')
    )

    return {
        'students_by_group': {
            'labels': [row['name'] for row in students_by_group],
            'values': [row['total_students'] for row in students_by_group],
        },
        'courses_by_semester': {
            'labels': [row['semester'] or 'N/A' for row in courses_by_semester],
            'values': [row['total_courses'] for row in courses_by_semester],
        },
        'avg_grade_by_subject': {
            'labels': [row['course__subject__name'] for row in avg_grade_by_subject],
            'values': [round(float(row['avg_grade']), 2) for row in avg_grade_by_subject],
            'totals': [row['grades_total'] for row in avg_grade_by_subject],
        },
        'attendance_by_group': {
            'labels': [row['lesson__course__group__name'] for row in attendance_by_group],
            'values': [round((row['present'] / row['total']) * 100, 2) if row['total'] else 0 for row in attendance_by_group],
            'totals': [row['total'] for row in attendance_by_group],
        },
    }


def _safe_int(value):
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _attendance_kpi(attendance_qs, grade_qs):
    total_attendance = attendance_qs.count()
    present_attendance = attendance_qs.filter(
        status__in=[Attendance.Status.PRESENT, Attendance.Status.LATE]
    ).count()
    grades_count = grade_qs.count()
    avg_grade = grade_qs.aggregate(avg=Avg('value'))['avg']
    return {
        'total_attendance': total_attendance,
        'present_attendance': present_attendance,
        'attendance_percent': round((present_attendance / total_attendance) * 100, 2) if total_attendance else 0,
        'grades_count': grades_count,
        'avg_grade': avg_grade,
    }


def _build_admin_focus_data(request):
    detail_scope = request.GET.get('admin_scope') or 'student'
    if detail_scope not in {'student', 'group', 'teacher'}:
        detail_scope = 'student'

    def _empty_block(title=''):
        return {
            'title': title,
            'kpi': {'attendance_percent': 0, 'avg_grade': None, 'total_attendance': 0, 'grades_count': 0},
            'rows': [],
            'row_title': '',
            'empty_message': 'Нет данных для отображения.',
        }

    students = Student.objects.select_related('user', 'group').order_by('user__last_name', 'user__first_name')
    groups = Group.objects.order_by('name')
    teachers = Teacher.objects.select_related('user').order_by('user__last_name', 'user__first_name')

    selected_student_id = _safe_int(request.GET.get('admin_student')) or (students.first().id if students.exists() else None)
    selected_group_id = _safe_int(request.GET.get('admin_group')) or (groups.first().id if groups.exists() else None)
    selected_teacher_id = _safe_int(request.GET.get('admin_teacher')) or (teachers.first().id if teachers.exists() else None)

    selected_student = students.filter(id=selected_student_id).first() if selected_student_id else None
    selected_group = groups.filter(id=selected_group_id).first() if selected_group_id else None
    selected_teacher = teachers.filter(id=selected_teacher_id).first() if selected_teacher_id else None

    focus = {
        'scope': detail_scope,
        'students': students,
        'groups': groups,
        'teachers': teachers,
        'selected_student_id': selected_student.id if selected_student else '',
        'selected_group_id': selected_group.id if selected_group else '',
        'selected_teacher_id': selected_teacher.id if selected_teacher else '',
        'student': _empty_block(),
        'group': _empty_block(),
        'teacher': _empty_block(),
    }

    if selected_student:
        attendance_qs = Attendance.objects.filter(student=selected_student)
        grade_qs = Grade.objects.filter(student=selected_student)
        focus['student']['title'] = f'Студент: {selected_student}'
        focus['student']['row_title'] = 'Показатели по предметам'
        focus['student']['kpi'] = _attendance_kpi(attendance_qs, grade_qs)

        attendance_subject_rows = (
            attendance_qs.values('lesson__course__subject__name')
            .annotate(
                total=Count('id'),
                present=Count('id', filter=Q(status__in=[Attendance.Status.PRESENT, Attendance.Status.LATE])),
            )
            .order_by('lesson__course__subject__name')
        )
        grade_subject_rows = (
            grade_qs.values('course__subject__name')
            .annotate(avg_grade=Avg('value'), grades_count=Count('id'))
            .order_by('course__subject__name')
        )

        attendance_map = {
            row['lesson__course__subject__name']: row for row in attendance_subject_rows
        }
        grade_map = {row['course__subject__name']: row for row in grade_subject_rows}
        subjects = sorted(set(attendance_map.keys()) | set(grade_map.keys()))
        for subject_name in subjects:
            att_row = attendance_map.get(subject_name, {})
            grd_row = grade_map.get(subject_name, {})
            total = att_row.get('total', 0)
            present = att_row.get('present', 0)
            focus['student']['rows'].append(
                {
                    'name': subject_name,
                    'attendance_percent': round((present / total) * 100, 2) if total else 0,
                    'attendance_total': total,
                    'grades_count': grd_row.get('grades_count', 0),
                    'avg_grade': grd_row.get('avg_grade'),
                }
            )

    if selected_group:
        attendance_qs = Attendance.objects.filter(student__group=selected_group)
        grade_qs = Grade.objects.filter(student__group=selected_group)
        focus['group']['title'] = f'Группа: {selected_group.name}'
        focus['group']['row_title'] = 'Показатели по студентам группы'
        focus['group']['kpi'] = _attendance_kpi(attendance_qs, grade_qs)

        attendance_rows = (
            attendance_qs.values('student_id')
            .annotate(
                total=Count('id'),
                present=Count('id', filter=Q(status__in=[Attendance.Status.PRESENT, Attendance.Status.LATE])),
            )
        )
        grades_rows = grade_qs.values('student_id').annotate(avg_grade=Avg('value'), grades_count=Count('id'))
        att_map = {row['student_id']: row for row in attendance_rows}
        grd_map = {row['student_id']: row for row in grades_rows}

        group_students = Student.objects.filter(group=selected_group).select_related('user').order_by(
            'user__last_name', 'user__first_name'
        )
        for student in group_students:
            att = att_map.get(student.id, {})
            grd = grd_map.get(student.id, {})
            total = att.get('total', 0)
            present = att.get('present', 0)
            focus['group']['rows'].append(
                {
                    'name': str(student),
                    'attendance_percent': round((present / total) * 100, 2) if total else 0,
                    'attendance_total': total,
                    'grades_count': grd.get('grades_count', 0),
                    'avg_grade': grd.get('avg_grade'),
                }
            )

    if selected_teacher:
        attendance_qs = Attendance.objects.filter(lesson__course__teacher=selected_teacher)
        grade_qs = Grade.objects.filter(course__teacher=selected_teacher)
        focus['teacher']['title'] = f'Преподаватель: {selected_teacher}'
        focus['teacher']['row_title'] = 'Показатели по группам преподавателя'
        focus['teacher']['kpi'] = _attendance_kpi(attendance_qs, grade_qs)

        attendance_rows = (
            attendance_qs.values('lesson__course__group_id', 'lesson__course__group__name')
            .annotate(
                total=Count('id'),
                present=Count('id', filter=Q(status__in=[Attendance.Status.PRESENT, Attendance.Status.LATE])),
            )
        )
        grades_rows = grade_qs.values('course__group_id').annotate(avg_grade=Avg('value'), grades_count=Count('id'))
        att_map = {row['lesson__course__group_id']: row for row in attendance_rows}
        grd_map = {row['course__group_id']: row for row in grades_rows}

        teacher_groups = Group.objects.filter(courses__teacher=selected_teacher).distinct().order_by('name')
        for group in teacher_groups:
            att = att_map.get(group.id, {})
            grd = grd_map.get(group.id, {})
            total = att.get('total', 0)
            present = att.get('present', 0)
            focus['teacher']['rows'].append(
                {
                    'name': group.name,
                    'attendance_percent': round((present / total) * 100, 2) if total else 0,
                    'attendance_total': total,
                    'grades_count': grd.get('grades_count', 0),
                    'avg_grade': grd.get('avg_grade'),
                }
            )

    focus['title'] = focus[detail_scope]['title']
    focus['kpi'] = focus[detail_scope]['kpi']
    focus['rows'] = focus[detail_scope]['rows']
    focus['row_title'] = focus[detail_scope]['row_title']
    focus['empty_message'] = focus[detail_scope]['empty_message']

    return focus


def _export_admin_focus_xlsx(focus):
    workbook = Workbook()
    summary_sheet = workbook.active
    summary_sheet.title = 'Сводка'
    details_sheet = workbook.create_sheet('Детализация')

    scope = focus.get('scope') or 'student'
    scope_label = {'student': 'Студент', 'group': 'Группа', 'teacher': 'Преподаватель'}.get(scope, 'Студент')
    kpi = focus.get('kpi', {})

    summary_sheet.append(['Параметр', 'Значение'])
    summary_sheet.append(['Режим', scope_label])
    summary_sheet.append(['Объект', focus.get('title') or ''])
    summary_sheet.append(['Посещаемость, %', kpi.get('attendance_percent', 0)])
    summary_sheet.append(
        [
            'Средний балл',
            round(float(kpi['avg_grade']), 2) if kpi.get('avg_grade') is not None else 'нет данных',
        ]
    )
    summary_sheet.append(['Отметок посещаемости', kpi.get('total_attendance', 0)])
    summary_sheet.append(['Оценок', kpi.get('grades_count', 0)])

    details_sheet.append(['Объект', 'Посещаемость, %', 'Отметок посещаемости', 'Оценок', 'Средний балл'])
    for row in focus.get('rows', []):
        details_sheet.append(
            [
                row.get('name', ''),
                row.get('attendance_percent', 0),
                row.get('attendance_total', 0),
                row.get('grades_count', 0),
                round(float(row['avg_grade']), 2) if row.get('avg_grade') is not None else '',
            ]
        )

    response = HttpResponse(
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )
    response['Content-Disposition'] = f'attachment; filename=\"dashboard_report_{scope}.xlsx\"'
    workbook.save(response)
    return response


@method_decorator(login_required, name='dispatch')
class DashboardView(ListView):
    template_name = 'core/dashboard.html'
    model = Course
    db_not_ready = False
    paginate_by = 20

    def dispatch(self, request, *args, **kwargs):
        user = request.user
        is_admin = user.is_superuser or user.groups.filter(name='Admin').exists()
        is_teacher = user.groups.filter(name='Teacher').exists()
        is_student = user.groups.filter(name='Student').exists()
        is_parent = user.groups.filter(name='Parent').exists()

        if is_student and not (is_admin or is_teacher):
            student = Student.objects.filter(user=user).only('id').first()
            if student:
                return redirect('student_detail', pk=student.id)
        if is_parent and not (is_admin or is_teacher or is_student):
            return redirect('parent_dashboard')

        return super().dispatch(request, *args, **kwargs)

    def get(self, request, *args, **kwargs):
        is_admin = request.user.is_superuser or request.user.groups.filter(name='Admin').exists()
        if is_admin and request.GET.get('focus_export') == 'xlsx':
            try:
                focus = _build_admin_focus_data(request)
                return _export_admin_focus_xlsx(focus)
            except (OperationalError, ProgrammingError):
                return HttpResponse('Схема БД не обновлена: выполните python manage.py migrate', status=503)
        return super().get(request, *args, **kwargs)

    def get_queryset(self):
        user = self.request.user
        qs = Course.objects.select_related('subject', 'group', 'teacher__user')
        try:
            if user.is_superuser or user.groups.filter(name='Admin').exists():
                return qs
            if user.groups.filter(name='Teacher').exists():
                return qs.filter(teacher__user=user)
            if user.groups.filter(name='Parent').exists():
                return qs.filter(group__students__parents__user=user).distinct()
            return qs.filter(group__students__user=user).distinct()
        except (OperationalError, ProgrammingError):
            self.db_not_ready = True
            return Course.objects.none()

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        context['is_admin'] = user.is_superuser or user.groups.filter(name='Admin').exists()
        context['is_teacher'] = user.groups.filter(name='Teacher').exists()
        context['is_student'] = user.groups.filter(name='Student').exists()
        context['is_parent'] = user.groups.filter(name='Parent').exists()
        context['db_not_ready'] = self.db_not_ready

        if self.db_not_ready:
            context.setdefault(
                'stats',
                {'Группы': 0, 'Студенты': 0, 'Преподаватели': 0, 'Предметы': 0, 'Курсы': 0},
            )
            context.setdefault('subject_avgs', [])
            context.setdefault('attendance_percent', 0)
            context.setdefault('teacher_courses', [])
            context.setdefault('teacher_stats', {'grades_count': 0, 'avg_grade': None})
            context.setdefault('student_avg', None)
            context.setdefault(
                'admin_chart_data',
                {
                    'students_by_group': {'labels': [], 'values': []},
                    'courses_by_semester': {'labels': [], 'values': []},
                    'avg_grade_by_subject': {'labels': [], 'values': [], 'totals': []},
                    'attendance_by_group': {'labels': [], 'values': [], 'totals': []},
                },
            )
            context.setdefault(
                'admin_focus',
                {
                    'scope': 'student',
                    'students': [],
                    'groups': [],
                    'teachers': [],
                    'selected_student_id': '',
                    'selected_group_id': '',
                    'selected_teacher_id': '',
                    'title': '',
                    'kpi': {'attendance_percent': 0, 'avg_grade': None, 'total_attendance': 0, 'grades_count': 0},
                    'rows': [],
                    'row_title': '',
                    'empty_message': 'Нет данных для отображения.',
                },
            )
            return context

        try:
            if context['is_student']:
                student = get_object_or_404(Student.objects.select_related('group'), user=user)
                grades = Grade.objects.filter(student=student).select_related('course__subject')
                attendance_total = Attendance.objects.filter(student=student).count()
                attendance_present = Attendance.objects.filter(student=student).filter(
                    status__in=[Attendance.Status.PRESENT, Attendance.Status.LATE]
                ).count()
                context['student'] = student
                context['student_avg'] = grades.aggregate(avg=Avg('value'))['avg']
                context['subject_avgs'] = (
                    grades.values('course__subject__name')
                    .annotate(avg=Avg('value'), total=Count('id'))
                    .order_by('course__subject__name')
                )
                context['attendance_percent'] = (
                    round((attendance_present / attendance_total) * 100, 2) if attendance_total else 0
                )

            if context['is_teacher']:
                teacher = get_object_or_404(Teacher.objects.select_related('user'), user=user)
                courses = Course.objects.filter(teacher=teacher).select_related('subject', 'group')
                context['teacher'] = teacher
                teacher_page_number = self.request.GET.get('teacher_page') or 1
                teacher_paginator = Paginator(courses, 20)
                context['teacher_courses_page'] = teacher_paginator.get_page(teacher_page_number)
                context['teacher_stats'] = Grade.objects.filter(course__teacher=teacher).aggregate(
                    grades_count=Count('id'), avg_grade=Avg('value')
                )

            if context['is_admin']:
                context['stats'] = {
                    'Группы': Group.objects.count(),
                    'Студенты': Student.objects.count(),
                    'Преподаватели': Teacher.objects.count(),
                    'Предметы': Subject.objects.count(),
                    'Курсы': Course.objects.count(),
                }
                context['admin_chart_data'] = _build_admin_chart_data()
                context['admin_focus'] = _build_admin_focus_data(self.request)
        except (OperationalError, ProgrammingError):
            context['db_not_ready'] = True
            context['stats'] = {'Группы': 0, 'Студенты': 0, 'Преподаватели': 0, 'Предметы': 0, 'Курсы': 0}
            context['subject_avgs'] = []
            context['attendance_percent'] = 0
            context['teacher_courses'] = []
            context['teacher_stats'] = {'grades_count': 0, 'avg_grade': None}
            context['student_avg'] = None
            context['admin_chart_data'] = {
                'students_by_group': {'labels': [], 'values': []},
                'courses_by_semester': {'labels': [], 'values': []},
                'avg_grade_by_subject': {'labels': [], 'values': [], 'totals': []},
                'attendance_by_group': {'labels': [], 'values': [], 'totals': []},
            }
            context['admin_focus'] = {
                'scope': 'student',
                'students': [],
                'groups': [],
                'teachers': [],
                'selected_student_id': '',
                'selected_group_id': '',
                'selected_teacher_id': '',
                'title': '',
                'kpi': {'attendance_percent': 0, 'avg_grade': None, 'total_attendance': 0, 'grades_count': 0},
                'rows': [],
                'row_title': '',
                'empty_message': 'Нет данных для отображения.',
            }

        return context


class GroupListView(AdminRequiredMixin, ListView):
    model = Group
    template_name = 'core/group_list.html'
    paginate_by = 20

    def get_queryset(self):
        qs = Group.objects.select_related('department', 'curator')
        q = (self.request.GET.get('q') or '').strip()
        if q:
            matched_ids = [obj.id for obj in qs if _contains_casefold(obj.name, q)]
            qs = qs.filter(id__in=matched_ids)
        return qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['q'] = (self.request.GET.get('q') or '').strip()
        return context


class GroupCreateView(AdminRequiredMixin, CreateView):
    model = Group
    form_class = GroupForm
    template_name = 'core/form.html'
    success_url = reverse_lazy('group_list')


class GroupUpdateView(AdminRequiredMixin, UpdateView):
    model = Group
    form_class = GroupForm
    template_name = 'core/form.html'
    success_url = reverse_lazy('group_list')


class GroupDeleteView(AdminRequiredMixin, DeleteView):
    model = Group
    template_name = 'core/confirm_delete.html'
    success_url = reverse_lazy('group_list')


class SubjectListView(AdminRequiredMixin, ListView):
    model = Subject
    template_name = 'core/subject_list.html'
    paginate_by = 20

    def get_queryset(self):
        qs = Subject.objects.select_related('department')
        q = (self.request.GET.get('q') or '').strip()
        if q:
            matched_ids = [obj.id for obj in qs if _contains_casefold(obj.name, q)]
            qs = qs.filter(id__in=matched_ids)
        return qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['q'] = (self.request.GET.get('q') or '').strip()
        return context


class SubjectCreateView(AdminRequiredMixin, CreateView):
    model = Subject
    form_class = SubjectForm
    template_name = 'core/form.html'
    success_url = reverse_lazy('subject_list')


class SubjectUpdateView(AdminRequiredMixin, UpdateView):
    model = Subject
    form_class = SubjectForm
    template_name = 'core/form.html'
    success_url = reverse_lazy('subject_list')


class SubjectDeleteView(AdminRequiredMixin, DeleteView):
    model = Subject
    template_name = 'core/confirm_delete.html'
    success_url = reverse_lazy('subject_list')


@login_required
def reports_index(request):
    return render(request, 'core/reports_index.html')
