from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.models import Group, User
from django.db.models import Avg, Count, Q
from django.http import HttpResponseForbidden
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse_lazy
from django.utils.text import slugify
from django.views.generic import CreateView, DeleteView, DetailView, ListView, TemplateView, UpdateView
from openpyxl import load_workbook

from core.permissions import AdminRequiredMixin
from grading.models import Attendance, Course, Grade, Lesson
from users.forms import StudentForm, TeacherForm, StudentImportForm
from users.models import Student, Teacher


def _contains_casefold(haystack, needle):
    return needle.casefold() in (haystack or '').casefold()


class TeacherListView(AdminRequiredMixin, ListView):
    model = Teacher
    template_name = 'users/teacher_list.html'
    paginate_by = 20

    def get_queryset(self):
        qs = Teacher.objects.select_related('user', 'department')
        q = (self.request.GET.get('q') or '').strip()
        if q:
            matched_ids = []
            for obj in qs:
                fio = (obj.user.get_full_name() or '').strip()
                if (
                    _contains_casefold(fio, q)
                    or _contains_casefold(obj.user.first_name, q)
                    or _contains_casefold(obj.user.last_name, q)
                    or _contains_casefold(obj.user.username, q)
                ):
                    matched_ids.append(obj.id)
            qs = qs.filter(id__in=matched_ids)
        return qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['q'] = (self.request.GET.get('q') or '').strip()
        return context


class TeacherCreateView(AdminRequiredMixin, CreateView):
    model = Teacher
    form_class = TeacherForm
    template_name = 'core/form.html'
    success_url = reverse_lazy('teacher_list')


class TeacherUpdateView(AdminRequiredMixin, UpdateView):
    model = Teacher
    form_class = TeacherForm
    template_name = 'core/form.html'
    success_url = reverse_lazy('teacher_list')


class TeacherDeleteView(AdminRequiredMixin, DeleteView):
    model = Teacher
    template_name = 'core/confirm_delete.html'
    success_url = reverse_lazy('teacher_list')


class StudentListView(AdminRequiredMixin, ListView):
    model = Student
    template_name = 'users/student_list.html'
    paginate_by = 20

    def get_queryset(self):
        qs = Student.objects.select_related('user', 'group')
        q = (self.request.GET.get('q') or '').strip()
        if q:
            matched_ids = []
            for obj in qs:
                fio = (obj.user.get_full_name() or '').strip()
                if (
                    _contains_casefold(fio, q)
                    or _contains_casefold(obj.user.first_name, q)
                    or _contains_casefold(obj.user.last_name, q)
                    or _contains_casefold(obj.user.username, q)
                ):
                    matched_ids.append(obj.id)
            qs = qs.filter(id__in=matched_ids)
        group = self.request.GET.get('group')
        if group:
            qs = qs.filter(group_id=group)
        return qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['q'] = (self.request.GET.get('q') or '').strip()
        return context


class StudentCreateView(AdminRequiredMixin, CreateView):
    model = Student
    form_class = StudentForm
    template_name = 'core/form.html'
    success_url = reverse_lazy('student_list')


class StudentUpdateView(AdminRequiredMixin, UpdateView):
    model = Student
    form_class = StudentForm
    template_name = 'core/form.html'
    success_url = reverse_lazy('student_list')


class StudentDeleteView(AdminRequiredMixin, DeleteView):
    model = Student
    template_name = 'core/confirm_delete.html'
    success_url = reverse_lazy('student_list')


class StudentDetailView(LoginRequiredMixin, DetailView):
    model = Student
    template_name = 'users/student_detail.html'

    def get_queryset(self):
        return Student.objects.select_related('user', 'group')

    def dispatch(self, request, *args, **kwargs):
        student = self.get_object()
        if not _can_access_student_profile(request.user, student):
            return HttpResponseForbidden('Нет доступа к профилю студента')
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        student = self.object
        context['subjects'] = (
            Course.objects.filter(group=student.group)
            .select_related('subject', 'teacher__user')
            .annotate(
                avg_grade=Avg('grades__value', filter=Q(grades__student=student)),
                grades_count=Count('grades', filter=Q(grades__student=student)),
            )
            .order_by('subject__name')
        )
        return context


class StudentCourseJournalView(LoginRequiredMixin, TemplateView):
    template_name = 'users/student_course_journal.html'

    def dispatch(self, request, *args, **kwargs):
        self.student = get_object_or_404(Student.objects.select_related('user', 'group'), pk=self.kwargs['student_id'])
        self.course = get_object_or_404(
            Course.objects.select_related('subject', 'group', 'teacher__user'),
            pk=self.kwargs['course_id'],
            group=self.student.group,
        )
        if not _can_access_student_profile(request.user, self.student):
            return HttpResponseForbidden('Нет доступа к журналу студента')
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        student = self.student
        course = self.course
        lessons = list(Lesson.objects.filter(course=course).order_by('date', 'id'))
        grades_map = {g.date: g for g in Grade.objects.filter(student=student, course=course)}
        attendance_map = {a.lesson_id: a for a in Attendance.objects.filter(student=student, lesson__course=course)}

        rows = []
        for lesson in lessons:
            grade = grades_map.get(lesson.date)
            attendance = attendance_map.get(lesson.id)
            rows.append(
                {
                    'lesson': lesson,
                    'grade': grade.value if grade else None,
                    'attendance': attendance.get_status_display() if attendance else '-',
                }
            )

        context['student'] = student
        context['course'] = course
        context['rows'] = rows
        return context


def _is_admin(user):
    return user.is_superuser or user.groups.filter(name='Admin').exists()


def _can_access_student_profile(user, student):
    if _is_admin(user):
        return True
    if student.user == user:
        return True
    return False


def _teacher_can_manage_group(user, group):
    if _is_admin(user):
        return True
    return Teacher.objects.filter(user=user, courses__group=group).exists()


def _build_username(first_name, last_name, group_id):
    base = slugify(f'{last_name}_{first_name}') or f'student_{group_id}'
    username = base
    seq = 1
    while User.objects.filter(username=username).exists():
        seq += 1
        username = f'{base}_{seq}'
    return username


@login_required
def import_students_to_group_view(request, group_id):
    from core.models import Group as StudyGroup

    study_group = get_object_or_404(StudyGroup, pk=group_id)
    if not _teacher_can_manage_group(request.user, study_group):
        from django.http import HttpResponseForbidden

        return HttpResponseForbidden('Нет доступа к импорту в эту группу')

    if request.method == 'POST':
        form = StudentImportForm(request.POST, request.FILES)
        if form.is_valid():
            uploaded = form.cleaned_data['file']
            default_password = form.cleaned_data['default_password'] or 'student123'

            try:
                workbook = load_workbook(uploaded, read_only=True, data_only=True)
            except Exception:
                messages.error(request, 'Не удалось прочитать Excel файл. Проверьте, что это корректный .xlsx.')
                return redirect('group_students_import', group_id=study_group.id)

            sheet = workbook.active
            rows = list(sheet.iter_rows(values_only=True))
            if not rows:
                messages.warning(request, 'Файл пустой.')
                return redirect('group_students_import', group_id=study_group.id)

            first_row = [str(c).strip().lower() if c is not None else '' for c in rows[0]]
            fio_col = 0
            has_header = False
            for idx, value in enumerate(first_row):
                if value in {'фио', 'fio', 'фио студента', 'student'}:
                    fio_col = idx
                    has_header = True
                    break

            data_rows = rows[1:] if has_header else rows

            student_role, _ = Group.objects.get_or_create(name='Student')
            created_users = 0
            created_students = 0
            moved_students = 0
            updated_names = 0
            skipped = 0

            for row in data_rows:
                if not row:
                    continue

                fio_value = ''
                if fio_col < len(row) and row[fio_col] is not None:
                    fio_value = str(row[fio_col]).strip()

                if not fio_value:
                    skipped += 1
                    continue

                fio_value = ' '.join(fio_value.replace(',', ' ').split())
                parts = fio_value.split()
                if len(parts) < 2:
                    skipped += 1
                    continue

                last_name = parts[0]
                first_name = ' '.join(parts[1:])
                username = _build_username(parts[1], last_name, study_group.id)

                user, user_created = User.objects.get_or_create(
                    username=username,
                    defaults={'first_name': first_name, 'last_name': last_name},
                )
                if user_created:
                    user.set_password(default_password)
                    user.save(update_fields=['password'])
                    created_users += 1
                else:
                    changed = False
                    if first_name and user.first_name != first_name:
                        user.first_name = first_name
                        changed = True
                    if last_name and user.last_name != last_name:
                        user.last_name = last_name
                        changed = True
                    if changed:
                        user.save(update_fields=['first_name', 'last_name'])
                        updated_names += 1

                user.groups.add(student_role)

                student, student_created = Student.objects.get_or_create(
                    user=user,
                    defaults={'group': study_group},
                )
                if student_created:
                    created_students += 1
                elif student.group_id != study_group.id:
                    student.group = study_group
                    student.save(update_fields=['group'])
                    moved_students += 1

            messages.success(
                request,
                f'Импорт завершен: users+{created_users}, students+{created_students}, перенесено {moved_students}, '
                f'обновлено ФИО {updated_names}, пропущено {skipped}.',
            )
            return redirect('course_list')
    else:
        form = StudentImportForm()

    return render(
        request,
        'users/import_students.html',
        {'form': form, 'study_group': study_group},
    )
