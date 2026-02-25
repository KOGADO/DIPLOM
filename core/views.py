from django.contrib.auth.decorators import login_required
from django.db.models import Avg, Count, Q
from django.db.utils import OperationalError, ProgrammingError
from django.core.paginator import Paginator
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse_lazy
from django.utils.decorators import method_decorator
from django.views.generic import CreateView, DeleteView, ListView, UpdateView

from core.forms import GroupForm, SubjectForm
from core.models import Group, Subject
from core.permissions import AdminRequiredMixin
from grading.models import Attendance, Course, Grade
from users.models import Student, Teacher


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

        if is_student and not (is_admin or is_teacher):
            student = Student.objects.filter(user=user).only('id').first()
            if student:
                return redirect('student_detail', pk=student.id)

        return super().dispatch(request, *args, **kwargs)

    def get_queryset(self):
        user = self.request.user
        qs = Course.objects.select_related('subject', 'group', 'teacher__user')
        try:
            if user.is_superuser or user.groups.filter(name='Admin').exists():
                return qs
            if user.groups.filter(name='Teacher').exists():
                return qs.filter(teacher__user=user)
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
