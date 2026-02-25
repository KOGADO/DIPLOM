from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db import transaction
from django.db.models import Avg, Count, Q, Value
from django.db.models.functions import Concat
from django.forms import modelform_factory
from django.http import HttpResponseForbidden, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse, reverse_lazy
from django.utils.dateparse import parse_date
from django.views.generic import CreateView, DeleteView, DetailView, ListView, UpdateView
import re

from core.permissions import AdminRequiredMixin
from grading.forms import LessonForm
from grading.models import Attendance, Course, Grade, Lesson
from users.models import Student

CourseForm = modelform_factory(Course, fields=['subject', 'teacher', 'group', 'semester', 'year'])


def is_admin(user):
    return user.is_superuser or user.groups.filter(name='Admin').exists()


def is_teacher(user):
    return user.groups.filter(name='Teacher').exists()


TEACHER_TOKEN_RE = re.compile(r'[А-ЯЁA-Z]\.\s*[А-ЯЁA-Z]\.\s*[А-ЯЁA-Z][а-яёa-z\-]+')


def _split_teacher_name(raw_name):
    normalized = ' '.join((raw_name or '').replace(';', ',').split())
    if not normalized:
        return []

    parts = [p.strip() for p in normalized.split(',') if p.strip()]
    if len(parts) > 1:
        return parts

    matches = [m.group(0).replace('  ', ' ').strip() for m in TEACHER_TOKEN_RE.finditer(normalized)]
    if len(matches) > 1:
        return matches

    return [normalized]


def _teacher_filter_choices(courses_qs):
    names = set()
    for first_name, last_name in courses_qs.values_list('teacher__user__first_name', 'teacher__user__last_name'):
        combined = ' '.join([part for part in (first_name, last_name) if part]).strip()
        for item in _split_teacher_name(combined):
            names.add(item)
    return sorted(names)


class CourseListView(LoginRequiredMixin, ListView):
    model = Course
    template_name = 'grading/course_list.html'
    paginate_by = 20

    def get_queryset(self):
        user = self.request.user
        qs = Course.objects.select_related('subject', 'teacher__user', 'group')

        if not is_admin(user):
            if is_teacher(user):
                qs = qs.filter(teacher__user=user)
            else:
                qs = qs.filter(group__students__user=user).distinct()

        for param in ('semester', 'group', 'subject'):
            value = self.request.GET.get(param)
            if value:
                field = f'{param}_id' if param != 'semester' else 'semester'
                qs = qs.filter(**{field: value})

        teacher_name = (self.request.GET.get('teacher') or '').strip()
        if teacher_name:
            teacher_tokens = [token.strip() for token in teacher_name.split() if token.strip()]
            qs = qs.annotate(
                teacher_full_name=Concat('teacher__user__first_name', Value(' '), 'teacher__user__last_name')
            ).filter(
                Q(teacher_full_name__icontains=teacher_name)
                | Q(teacher__user__first_name__icontains=teacher_name)
                | Q(teacher__user__last_name__icontains=teacher_name)
                | Q(teacher__user__username__icontains=teacher_name)
            )
            for token in teacher_tokens:
                qs = qs.filter(
                    Q(teacher__user__first_name__icontains=token)
                    | Q(teacher__user__last_name__icontains=token)
                    | Q(teacher__user__username__icontains=token)
                )
        return qs

    def get_context_data(self, **kwargs):
        from core.models import Group, Subject

        context = super().get_context_data(**kwargs)
        user = self.request.user

        base_courses = Course.objects.select_related('teacher__user')
        if not is_admin(user):
            if is_teacher(user):
                base_courses = base_courses.filter(teacher__user=user)
            else:
                base_courses = base_courses.filter(group__students__user=user).distinct()

        if is_admin(user):
            teachers = _teacher_filter_choices(base_courses)
            groups = Group.objects.all()
            subjects = Subject.objects.all()
        elif is_teacher(user):
            teachers = _teacher_filter_choices(base_courses)
            groups = Group.objects.filter(courses__teacher__user=user).distinct()
            subjects = Subject.objects.filter(courses__teacher__user=user).distinct()
        else:
            groups = Group.objects.filter(students__user=user).distinct()
            subjects = Subject.objects.filter(courses__group__students__user=user).distinct()
            teachers = _teacher_filter_choices(base_courses)

        context['teachers'] = teachers
        context['groups'] = groups
        context['subjects'] = subjects
        context['semesters'] = (
            self.get_queryset().values_list('semester', flat=True).distinct().order_by('semester')
        )
        context['can_manage'] = is_admin(user)
        context['selected'] = {
            'semester': self.request.GET.get('semester', ''),
            'teacher': self.request.GET.get('teacher', ''),
            'group': self.request.GET.get('group', ''),
            'subject': self.request.GET.get('subject', ''),
        }
        return context


class CourseCreateView(AdminRequiredMixin, CreateView):
    model = Course
    form_class = CourseForm
    template_name = 'core/form.html'
    success_url = reverse_lazy('course_list')


class CourseUpdateView(AdminRequiredMixin, UpdateView):
    model = Course
    form_class = CourseForm
    template_name = 'core/form.html'
    success_url = reverse_lazy('course_list')


class CourseDeleteView(AdminRequiredMixin, DeleteView):
    model = Course
    template_name = 'core/confirm_delete.html'
    success_url = reverse_lazy('course_list')


class CourseDetailView(LoginRequiredMixin, DetailView):
    model = Course
    template_name = 'grading/course_detail.html'

    def get_queryset(self):
        return Course.objects.select_related('subject', 'teacher__user', 'group').prefetch_related(
            'lessons', 'grades', 'group__students__user'
        )

    def dispatch(self, request, *args, **kwargs):
        course = self.get_object()
        user = request.user
        if is_admin(user):
            return super().dispatch(request, *args, **kwargs)
        if is_teacher(user) and course.teacher.user == user:
            return super().dispatch(request, *args, **kwargs)
        if course.group.students.filter(user=user).exists():
            return super().dispatch(request, *args, **kwargs)
        return HttpResponseForbidden('Нет доступа к курсу')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        course = self.object
        students = (
            Student.objects.filter(group=course.group)
            .select_related('user')
            .annotate(
                avg_grade=Avg('grades__value', filter=Q(grades__course=course)),
                attendance_total=Count('attendances', filter=Q(attendances__lesson__course=course)),
                attendance_present=Count(
                    'attendances',
                    filter=Q(
                        attendances__lesson__course=course,
                        attendances__status__in=[Attendance.Status.PRESENT, Attendance.Status.LATE],
                    ),
                ),
            )
            .order_by('user__last_name', 'user__first_name')
        )

        context['students'] = students
        context['grades'] = Grade.objects.filter(course=course).select_related('student__user').order_by('-date')
        context['lessons'] = Lesson.objects.filter(course=course).order_by('-date')

        user = self.request.user
        context['can_edit'] = is_admin(user) or (is_teacher(user) and course.teacher.user == user)
        context['can_view_student_profiles'] = is_admin(user)
        context['course_avg'] = Grade.objects.filter(course=course).aggregate(avg=Avg('value'))['avg']
        return context


@login_required
def course_journal_view(request, pk):
    course = get_object_or_404(Course.objects.select_related('teacher__user', 'group', 'subject'), pk=pk)
    user = request.user

    if not (is_admin(user) or (is_teacher(user) and course.teacher.user == user) or course.group.students.filter(user=user).exists()):
        return HttpResponseForbidden('Нет доступа к курсу')

    can_edit = is_admin(user) or (is_teacher(user) and course.teacher.user == user)
    students = list(
        Student.objects.filter(group=course.group)
        .select_related('user')
        .order_by('user__last_name', 'user__first_name', 'user__username')
    )
    lessons = list(Lesson.objects.filter(course=course).order_by('date', 'id'))

    grade_type = Grade.GradeType.GRADE

    if request.method == 'POST' and not can_edit:
        return HttpResponseForbidden('Нет доступа')

    if request.method == 'POST' and can_edit:
        action = request.POST.get('action', 'save_grid')

        if action == 'add_lesson':
            lesson_date = parse_date(request.POST.get('lesson_date', ''))
            topic = request.POST.get('topic', '').strip()
            if not lesson_date:
                messages.error(request, 'Укажите корректную дату занятия')
            else:
                lesson, created = Lesson.objects.get_or_create(
                    course=course,
                    date=lesson_date,
                    defaults={'topic': topic},
                )
                if not created and topic and lesson.topic != topic:
                    lesson.topic = topic
                    lesson.save(update_fields=['topic'])
                messages.success(request, f'Занятие на {lesson_date} сохранено')
            return redirect(reverse('course_journal', kwargs={'pk': course.pk}))

        if action == 'update_topic':
            lesson_id_raw = request.POST.get('lesson_id', '').strip()
            topic = request.POST.get('topic', '').strip()
            try:
                lesson_id = int(lesson_id_raw)
            except (TypeError, ValueError):
                if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                    return JsonResponse({'ok': False, 'error': 'Некорректный ID занятия'}, status=400)
                messages.error(request, 'Некорректный ID занятия')
                return redirect(reverse('course_journal', kwargs={'pk': course.pk}))

            lesson = Lesson.objects.filter(course=course, id=lesson_id).first()
            if not lesson:
                if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                    return JsonResponse({'ok': False, 'error': 'Занятие не найдено'}, status=404)
                messages.error(request, 'Занятие не найдено')
                return redirect(reverse('course_journal', kwargs={'pk': course.pk}))

            lesson.topic = topic
            lesson.save(update_fields=['topic'])
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({'ok': True, 'lesson_id': lesson.id, 'topic': lesson.topic})
            return redirect(reverse('course_journal', kwargs={'pk': course.pk}))

        if action == 'save_grid':
            updated_count = 0
            with transaction.atomic():
                for student in students:
                    for lesson in lessons:
                        mark = request.POST.get(f'mark_{student.id}_{lesson.id}', '').strip().upper()
                        if len(mark) > 1:
                            mark = mark[0]

                        grade_qs = Grade.objects.filter(
                            student=student,
                            course=course,
                            grade_type=grade_type,
                            date=lesson.date,
                        ).order_by('id')
                        attendance_qs = Attendance.objects.filter(student=student, lesson=lesson)

                        if mark in {'2', '3', '4', '5'}:
                            value = int(mark)
                            grade = grade_qs.first()
                            if grade:
                                if grade.value != value:
                                    grade.value = value
                                    grade.save(update_fields=['value'])
                                    updated_count += 1
                                grade_qs.exclude(id=grade.id).delete()
                            else:
                                Grade.objects.create(
                                    student=student,
                                    course=course,
                                    grade_type=grade_type,
                                    value=value,
                                    date=lesson.date,
                                )
                                updated_count += 1

                            Attendance.objects.update_or_create(
                                student=student,
                                lesson=lesson,
                                defaults={'status': Attendance.Status.PRESENT, 'comment': ''},
                            )
                            continue

                        if mark in {'Н', 'N'}:
                            grade_qs.delete()
                            Attendance.objects.update_or_create(
                                student=student,
                                lesson=lesson,
                                defaults={'status': Attendance.Status.ABSENT, 'comment': ''},
                            )
                            updated_count += 1
                            continue

                        if mark in {'О', 'L'}:
                            grade_qs.delete()
                            Attendance.objects.update_or_create(
                                student=student,
                                lesson=lesson,
                                defaults={'status': Attendance.Status.LATE, 'comment': ''},
                            )
                            updated_count += 1
                            continue

                        if mark in {'П', 'P'}:
                            grade_qs.delete()
                            Attendance.objects.update_or_create(
                                student=student,
                                lesson=lesson,
                                defaults={'status': Attendance.Status.PRESENT, 'comment': ''},
                            )
                            updated_count += 1
                            continue

                        if mark == '':
                            grade_qs.delete()
                            attendance_qs.delete()

            messages.success(request, f'Журнал сохранен. Обновлено ячеек: {updated_count}')
            return redirect(reverse('course_journal', kwargs={'pk': course.pk}))

    date_to_lesson = {lesson.date: lesson for lesson in lessons}
    grade_map = {
        (g.student_id, g.date): g.value
        for g in Grade.objects.filter(
            course=course,
            grade_type=grade_type,
            date__in=date_to_lesson.keys(),
            student__in=students,
        ).only('student_id', 'date', 'value')
    }
    attendance_map = {
        (a.student_id, a.lesson_id): a.status
        for a in Attendance.objects.filter(lesson__in=lessons, student__in=students).only('student_id', 'lesson_id', 'status')
    }

    rows = []
    for row_idx, student in enumerate(students):
        cells = []
        for col_idx, lesson in enumerate(lessons):
            mark = ''
            grade_value = grade_map.get((student.id, lesson.date))
            if grade_value is not None:
                mark = str(grade_value)
            else:
                status = attendance_map.get((student.id, lesson.id))
                if status == Attendance.Status.ABSENT:
                    mark = 'Н'
                elif status == Attendance.Status.LATE:
                    mark = 'О'
                elif status == Attendance.Status.PRESENT:
                    mark = 'П'

            cells.append({'lesson': lesson, 'mark': mark, 'row_idx': row_idx, 'col_idx': col_idx})

        rows.append({'student': student, 'cells': cells})

    return render(
        request,
        'grading/course_journal.html',
        {
            'course': course,
            'can_edit': can_edit,
            'rows': rows,
            'lessons': lessons,
        },
    )


class LessonCreateView(LoginRequiredMixin, CreateView):
    model = Lesson
    form_class = LessonForm
    template_name = 'core/form.html'

    def dispatch(self, request, *args, **kwargs):
        course = get_object_or_404(Course.objects.select_related('teacher__user'), pk=self.kwargs['course_id'])
        if not (is_admin(request.user) or (is_teacher(request.user) and course.teacher.user == request.user)):
            return HttpResponseForbidden('Нет доступа')
        return super().dispatch(request, *args, **kwargs)

    def get_initial(self):
        initial = super().get_initial()
        initial['course'] = self.kwargs['course_id']
        return initial

    def get_success_url(self):
        return reverse('course_detail', kwargs={'pk': self.kwargs['course_id']})


@login_required
def attendance_mark_view(request, lesson_id):
    lesson = get_object_or_404(Lesson.objects.select_related('course__teacher__user', 'course__group'), pk=lesson_id)
    if not (is_admin(request.user) or (is_teacher(request.user) and lesson.course.teacher.user == request.user)):
        return HttpResponseForbidden('Нет доступа')

    students = Student.objects.filter(group=lesson.course.group).select_related('user').order_by('user__last_name', 'user__first_name')

    if request.method == 'POST':
        for student in students:
            status = request.POST.get(f'status_{student.id}', Attendance.Status.ABSENT)
            comment = request.POST.get(f'comment_{student.id}', '')
            Attendance.objects.update_or_create(
                lesson=lesson,
                student=student,
                defaults={'status': status, 'comment': comment},
            )
        messages.success(request, 'Посещаемость сохранена')
        return redirect('course_detail', pk=lesson.course_id)

    existing = {a.student_id: a for a in Attendance.objects.filter(lesson=lesson)}
    student_rows = [{'student': student, 'current': existing.get(student.id)} for student in students]
    return render(
        request,
        'grading/attendance_mark.html',
        {'lesson': lesson, 'student_rows': student_rows, 'statuses': Attendance.Status.choices},
    )
