from datetime import date

from django.contrib.auth.models import Group, User
from django.test import TestCase
from django.urls import reverse

from core.models import Group as StudyGroup
from core.models import Subject
from grading.models import Course
from users.models import Student, Teacher


class StudentAccessTests(TestCase):
    def setUp(self):
        self.student_group, _ = Group.objects.get_or_create(name='Student')
        self.teacher_group, _ = Group.objects.get_or_create(name='Teacher')

        grp = StudyGroup.objects.create(name='ТЕСТ-1')

        user1 = User.objects.create_user(username='student_a', password='pass12345')
        user1.groups.add(self.student_group)
        self.student1 = Student.objects.create(user=user1, group=grp, date_of_birth=date(2005, 1, 1))

        user2 = User.objects.create_user(username='student_b', password='pass12345')
        user2.groups.add(self.student_group)
        self.student2 = Student.objects.create(user=user2, group=grp, date_of_birth=date(2005, 1, 2))

        teacher_user = User.objects.create_user(username='teacher_profile_block', password='pass12345')
        teacher_user.groups.add(self.teacher_group)
        teacher = Teacher.objects.create(user=teacher_user)
        subject = Subject.objects.create(name='Проверка доступа')
        Course.objects.create(subject=subject, teacher=teacher, group=grp, semester='2025/2026-2', year=2026)

    def test_student_cannot_view_another_student_profile(self):
        self.client.login(username='student_a', password='pass12345')
        response = self.client.get(reverse('student_detail', kwargs={'pk': self.student2.pk}))
        self.assertEqual(response.status_code, 403)

    def test_teacher_cannot_view_student_profile(self):
        self.client.login(username='teacher_profile_block', password='pass12345')
        response = self.client.get(reverse('student_detail', kwargs={'pk': self.student1.pk}))
        self.assertEqual(response.status_code, 403)

    def test_student_dashboard_redirects_to_own_profile(self):
        self.client.login(username='student_a', password='pass12345')
        response = self.client.get('/', follow=False)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse('student_detail', kwargs={'pk': self.student1.pk}))


class ImportStudentsAccessTests(TestCase):
    def setUp(self):
        self.admin = User.objects.create_superuser('admin_import', 'a@a.a', 'pass12345')
        teacher_group, _ = Group.objects.get_or_create(name='Teacher')

        self.teacher_user = User.objects.create_user('teacher_import', password='pass12345')
        self.teacher_user.groups.add(teacher_group)
        self.teacher = Teacher.objects.create(user=self.teacher_user)

        self.other_teacher_user = User.objects.create_user('teacher_other', password='pass12345')
        self.other_teacher_user.groups.add(teacher_group)
        self.other_teacher = Teacher.objects.create(user=self.other_teacher_user)

        self.group_ok = StudyGroup.objects.create(name='IMP-OK')
        self.group_forbidden = StudyGroup.objects.create(name='IMP-NO')
        subject = Subject.objects.create(name='Импорт-Тест')
        Course.objects.create(subject=subject, teacher=self.teacher, group=self.group_ok, semester='2025/2026-2', year=2026)
        Course.objects.create(subject=subject, teacher=self.other_teacher, group=self.group_forbidden, semester='2025/2026-2', year=2026)

    def test_admin_can_open_import_page(self):
        self.client.login(username='admin_import', password='pass12345')
        response = self.client.get(reverse('group_students_import', kwargs={'group_id': self.group_ok.id}))
        self.assertEqual(response.status_code, 200)

    def test_teacher_can_open_own_group_import_page(self):
        self.client.login(username='teacher_import', password='pass12345')
        response = self.client.get(reverse('group_students_import', kwargs={'group_id': self.group_ok.id}))
        self.assertEqual(response.status_code, 200)

    def test_teacher_cannot_open_foreign_group_import_page(self):
        self.client.login(username='teacher_import', password='pass12345')
        response = self.client.get(reverse('group_students_import', kwargs={'group_id': self.group_forbidden.id}))
        self.assertEqual(response.status_code, 403)


class UsersSearchTests(TestCase):
    def setUp(self):
        self.admin = User.objects.create_superuser('admin_search_users', 'a@a.a', 'pass12345')
        self.client.login(username='admin_search_users', password='pass12345')

        group = StudyGroup.objects.create(name='ПОИСК-1')

        teacher_user = User.objects.create_user(
            username='teacher_find_me',
            first_name='Иван',
            last_name='Петров',
            password='pass12345',
        )
        self.teacher = Teacher.objects.create(user=teacher_user)

        student_user = User.objects.create_user(
            username='student_find_me',
            first_name='Мария',
            last_name='Сидорова',
            password='pass12345',
        )
        self.student = Student.objects.create(user=student_user, group=group)

    def test_teacher_list_search_by_fio(self):
        response = self.client.get(reverse('teacher_list'), {'q': 'Петров'})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Иван Петров')
        self.assertNotContains(response, 'Мария Сидорова')

    def test_student_list_search_by_fio(self):
        response = self.client.get(reverse('student_list'), {'q': 'Сидорова'})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Мария Сидорова')
        self.assertNotContains(response, 'Иван Петров')

    def test_teacher_list_search_is_case_insensitive(self):
        response = self.client.get(reverse('teacher_list'), {'q': 'пЕТРоВ'})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Иван Петров')

    def test_student_list_search_is_case_insensitive(self):
        response = self.client.get(reverse('student_list'), {'q': 'сИДОрОвА'})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Мария Сидорова')
