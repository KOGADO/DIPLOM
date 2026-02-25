from datetime import date

from django.contrib.auth.models import Group, User
from django.core.exceptions import ValidationError
from django.db.models import Avg
from django.test import TestCase
from django.urls import reverse

from core.models import Group as StudyGroup, Subject
from grading.models import Course, Grade
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
