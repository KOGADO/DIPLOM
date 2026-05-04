from datetime import date

from io import BytesIO

from django.contrib.auth.models import Group, User
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.db.models import Avg
from django.test import TestCase
from django.urls import reverse
from openpyxl import Workbook

from core.models import Group as StudyGroup, Subject
from grading.models import Attendance, Course, Grade, LectureTopic, Lesson
from users.models import Student, Teacher


class GradeScaleTests(TestCase):
    def setUp(self):
        group = StudyGroup.objects.create(name='ТЕСТ-AVG')
        subject = Subject.objects.create(name='Тестовый предмет')

        self.teacher_user = User.objects.create_user(username='teacher_avg', password='pass12345')
        teacher_group, _ = Group.objects.get_or_create(name='Teacher')
        self.teacher_user.groups.add(teacher_group)
        teacher = Teacher.objects.create(user=self.teacher_user)

        s_user = User.objects.create_user(username='student_avg', password='pass12345')
        self.student = Student.objects.create(user=s_user, group=group)

        self.course = Course.objects.create(subject=subject, teacher=teacher, group=group, semester='2025/2026-1', year=2025)

    def test_grade_validation_2_to_5(self):
        valid_grade = Grade(student=self.student, course=self.course, grade_type=Grade.GradeType.GRADE, value=5, date=date(2025, 9, 1))
        valid_grade.full_clean()

        invalid_low = Grade(student=self.student, course=self.course, grade_type=Grade.GradeType.GRADE, value=1, date=date(2025, 9, 1))
        with self.assertRaises(ValidationError):
            invalid_low.full_clean()

        invalid_high = Grade(student=self.student, course=self.course, grade_type=Grade.GradeType.GRADE, value=6, date=date(2025, 9, 1))
        with self.assertRaises(ValidationError):
            invalid_high.full_clean()

    def test_average_grade_calculation(self):
        Grade.objects.create(student=self.student, course=self.course, grade_type=Grade.GradeType.GRADE, value=5, date=date(2025, 9, 1))
        Grade.objects.create(student=self.student, course=self.course, grade_type=Grade.GradeType.GRADE, value=4, date=date(2025, 9, 8))
        Grade.objects.create(student=self.student, course=self.course, grade_type=Grade.GradeType.GRADE, value=4, date=date(2025, 9, 15))

        avg = Grade.objects.filter(student=self.student, course=self.course).aggregate(avg=Avg('value'))['avg']
        self.assertEqual(round(float(avg), 2), 4.33)


class CourseTeacherFilterTests(TestCase):
    def setUp(self):
        self.admin = User.objects.create_user(username='admin_filter', password='pass12345', is_superuser=True)
        self.client.login(username='admin_filter', password='pass12345')

        group = StudyGroup.objects.create(name='ФИЛ-1-23')
        subject = Subject.objects.create(name='Тест фильтра')

        user_single = User.objects.create_user(username='t_single', first_name='М.А.', last_name='Злобина')
        user_combined = User.objects.create_user(
            username='t_combined',
            first_name='М.А. Злобина',
            last_name='Г.Н.Киселев',
        )
        teacher_single = Teacher.objects.create(user=user_single)
        teacher_combined = Teacher.objects.create(user=user_combined)

        self.course_single = Course.objects.create(
            subject=subject,
            teacher=teacher_single,
            group=group,
            semester='2025/2026-2',
            year=2026,
        )
        self.course_combined = Course.objects.create(
            subject=subject,
            teacher=teacher_combined,
            group=group,
            semester='2025/2026-2',
            year=2026,
        )

    def test_filter_by_single_teacher_includes_joint_course(self):
        response = self.client.get(reverse('course_list'), {'teacher': 'М.А. Злобина'})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, str(self.course_single.id))
        self.assertContains(response, str(self.course_combined.id))

    def test_teacher_filter_options_do_not_have_combined_value(self):
        response = self.client.get(reverse('course_list'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'value="М.А. Злобина"', count=1)
        self.assertNotContains(response, 'value="М.А. Злобина Г.Н.Киселев"')


class LectureTopicImportTests(TestCase):
    def setUp(self):
        teacher_group, _ = Group.objects.get_or_create(name='Teacher')
        self.teacher_user = User.objects.create_user(username='topic_teacher', password='pass12345')
        self.teacher_user.groups.add(teacher_group)
        self.teacher = Teacher.objects.create(user=self.teacher_user)

        group = StudyGroup.objects.create(name='ТЕМ-1')
        subject = Subject.objects.create(name='Темы лекций')
        self.course = Course.objects.create(
            subject=subject,
            teacher=self.teacher,
            group=group,
            semester='2025/2026-2',
            year=2026,
        )
        student_user = User.objects.create_user(username='topic_student', password='pass12345')
        Student.objects.create(user=student_user, group=group)

    def test_teacher_imports_topics_from_csv(self):
        self.client.login(username='topic_teacher', password='pass12345')
        uploaded = SimpleUploadedFile(
            'topics.csv',
            'Тема\nВведение в Python\nООП в Python\nВведение в Python\n'.encode('utf-8-sig'),
            content_type='text/csv',
        )
        response = self.client.post(
            reverse('course_journal', kwargs={'pk': self.course.pk}),
            {'action': 'import_topics', 'topics_file': uploaded},
            follow=True,
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Введение в Python')
        self.assertContains(response, 'ООП в Python')
        self.assertEqual(LectureTopic.objects.filter(course=self.course).count(), 2)

    def test_teacher_imports_topics_from_xlsx(self):
        workbook = Workbook()
        worksheet = workbook.active
        worksheet.append(['Тема'])
        worksheet.append(['Архитектура приложения'])
        output = BytesIO()
        workbook.save(output)
        output.seek(0)

        self.client.login(username='topic_teacher', password='pass12345')
        uploaded = SimpleUploadedFile(
            'topics.xlsx',
            output.getvalue(),
            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        )
        response = self.client.post(
            reverse('course_journal', kwargs={'pk': self.course.pk}),
            {'action': 'import_topics', 'topics_file': uploaded},
            follow=True,
        )
        self.assertEqual(response.status_code, 200)
        self.assertTrue(LectureTopic.objects.filter(course=self.course, title='Архитектура приложения').exists())


class CourseJournalAttendanceTests(TestCase):
    def setUp(self):
        teacher_group, _ = Group.objects.get_or_create(name='Teacher')
        self.teacher_user = User.objects.create_user(username='journal_teacher', password='pass12345')
        self.teacher_user.groups.add(teacher_group)
        self.teacher = Teacher.objects.create(user=self.teacher_user)

        self.group = StudyGroup.objects.create(name='ЖУР-1')
        self.subject = Subject.objects.create(name='Журнал посещаемости')
        self.course = Course.objects.create(
            subject=self.subject,
            teacher=self.teacher,
            group=self.group,
            semester='2025/2026-2',
            year=2026,
        )
        student_user = User.objects.create_user(username='journal_student', password='pass12345')
        self.student = Student.objects.create(user=student_user, group=self.group)
        self.lesson = Lesson.objects.create(course=self.course, date=date(2026, 4, 29))

    def test_late_mark_is_not_shown_or_preserved_from_journal(self):
        Attendance.objects.create(
            student=self.student,
            lesson=self.lesson,
            status=Attendance.Status.LATE,
        )

        self.client.login(username='journal_teacher', password='pass12345')
        response = self.client.get(reverse('course_journal', kwargs={'pk': self.course.pk}))
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, 'value="О"')

        response = self.client.post(
            reverse('course_journal', kwargs={'pk': self.course.pk}),
            {
                'action': 'save_grid',
                f'mark_{self.student.id}_{self.lesson.id}': 'О',
            },
            follow=True,
        )
        self.assertEqual(response.status_code, 200)
        attendance = Attendance.objects.get(student=self.student, lesson=self.lesson)
        self.assertEqual(attendance.status, Attendance.Status.PRESENT)

    def test_blank_journal_mark_saves_present_without_visible_mark(self):
        self.client.login(username='journal_teacher', password='pass12345')
        response = self.client.post(
            reverse('course_journal', kwargs={'pk': self.course.pk}),
            {
                'action': 'save_grid',
                f'mark_{self.student.id}_{self.lesson.id}': '',
            },
            follow=True,
        )
        self.assertEqual(response.status_code, 200)
        attendance = Attendance.objects.get(student=self.student, lesson=self.lesson)
        self.assertEqual(attendance.status, Attendance.Status.PRESENT)

        response = self.client.get(reverse('course_journal', kwargs={'pk': self.course.pk}))
        self.assertNotContains(response, 'value="П"')
