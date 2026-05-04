from pathlib import Path
from unittest.mock import patch

from django.contrib.auth.models import Group, User
from django.db import connection
from django.db.utils import OperationalError
from django.test import TestCase
from django.urls import reverse

from core.migration_utils import add_column_if_missing
from core.models import Department, Group as StudyGroup, Subject
from core.models import AdminLog
from users.models import Student, Teacher


class LogoutBehaviorTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='logout_user', password='pass12345')

    def test_get_logout_returns_405(self):
        self.client.login(username='logout_user', password='pass12345')
        response = self.client.get(reverse('logout'))
        self.assertEqual(response.status_code, 405)

    def test_post_logout_returns_redirect(self):
        self.client.login(username='logout_user', password='pass12345')
        response = self.client.post(reverse('logout'))
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, '/')


class DashboardResilienceTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='admin_case', password='pass12345', is_superuser=True)
        self.client.login(username='admin_case', password='pass12345')

    def test_dashboard_handles_operational_error_on_teacher_count(self):
        with patch(
            'core.views.Teacher.objects.count',
            side_effect=OperationalError('no such column: users_teacher.department_id'),
        ):
            response = self.client.get(reverse('dashboard'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Схема БД не обновлена: выполните')


class InterfaceCleanupTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='ui_admin', password='pass12345', is_superuser=True)
        self.client.login(username='ui_admin', password='pass12345')

    def test_sidebar_has_no_departments_link(self):
        response = self.client.get(reverse('dashboard'))
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, 'Кафедры')
        self.assertNotContains(response, '/departments/')

    def test_group_form_has_no_department_field(self):
        response = self.client.get(reverse('group_add'))
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, 'name="department"', html=False)
        self.assertNotContains(response, 'Кафедра')

    def test_subject_form_has_no_department_field(self):
        response = self.client.get(reverse('subject_add'))
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, 'name="department"', html=False)
        self.assertNotContains(response, 'Кафедра')


class StudentSidebarTests(TestCase):
    def setUp(self):
        student_group, _ = Group.objects.get_or_create(name='Student')
        self.user = User.objects.create_user(username='student_sidebar', password='pass12345')
        self.user.groups.add(student_group)

        study_group = StudyGroup.objects.create(name='P-1-24')
        self.student = Student.objects.create(user=self.user, group=study_group)

    def test_student_sidebar_shows_only_profile_link(self):
        self.client.login(username='student_sidebar', password='pass12345')
        response = self.client.get(reverse('student_detail', kwargs={'pk': self.student.pk}))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Профиль студента')
        self.assertNotContains(response, 'Дашборд')
        self.assertNotContains(response, 'Курсы')


class SchemaSmokeTests(TestCase):
    def test_can_create_department_group_subject_teacher(self):
        department = Department.objects.create(name='Тестовое отделение')
        user = User.objects.create_user(username='teacher_smoke', password='pass12345')

        group = StudyGroup.objects.create(name='SMK-01', department=department)
        subject = Subject.objects.create(name='Smoke Subject', department=department)
        teacher = Teacher.objects.create(user=user, department=department)

        self.assertEqual(group.department_id, department.id)
        self.assertEqual(subject.department_id, department.id)
        self.assertEqual(teacher.department_id, department.id)


class MigrationUtilsTests(TestCase):
    def test_add_column_if_missing(self):
        table_name = 'tmp_migration_utils'
        with connection.cursor() as cursor:
            cursor.execute(f'DROP TABLE IF EXISTS {table_name}')
            cursor.execute(f'CREATE TABLE {table_name} (id INTEGER PRIMARY KEY)')

        class DummySchemaEditor:
            def __init__(self, conn):
                self.connection = conn

            def quote_name(self, value):
                return f'"{value}"'

            def execute(self, sql):
                with self.connection.cursor() as cursor:
                    cursor.execute(sql)

        schema_editor = DummySchemaEditor(connection)
        created = add_column_if_missing(schema_editor, table_name, 'department_id', 'INTEGER')
        created_again = add_column_if_missing(schema_editor, table_name, 'department_id', 'INTEGER')

        with connection.cursor() as cursor:
            description = connection.introspection.get_table_description(cursor, table_name)
            columns = [column.name for column in description]
            cursor.execute(f'DROP TABLE IF EXISTS {table_name}')

        self.assertTrue(created)
        self.assertFalse(created_again)
        self.assertIn('department_id', columns)


class CoreMigrationFilesTests(TestCase):
    def test_core_initial_migration_exists(self):
        migration_path = Path(__file__).resolve().parent / 'migrations' / '0001_initial.py'
        self.assertTrue(migration_path.exists())

    def test_subject_department_repair_migration_exists(self):
        migration_path = Path(__file__).resolve().parent / 'migrations' / '0005_subject_department_repair.py'
        self.assertTrue(migration_path.exists())

    def test_group_department_repair_migration_exists(self):
        migration_path = Path(__file__).resolve().parent / 'migrations' / '0006_group_department_repair.py'
        self.assertTrue(migration_path.exists())


class SubjectSearchTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='admin_subject_search', password='pass12345', is_superuser=True)
        self.client.login(username='admin_subject_search', password='pass12345')
        Subject.objects.create(name='Алгоритмы')
        Subject.objects.create(name='Базы данных')

    def test_subject_list_search_by_name(self):
        response = self.client.get(reverse('subject_list'), {'q': 'Базы'})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Базы данных')
        self.assertNotContains(response, 'Алгоритмы')

    def test_subject_list_search_is_case_insensitive(self):
        response = self.client.get(reverse('subject_list'), {'q': 'бАЗЫ'})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Базы данных')


class GroupSearchTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='admin_group_search', password='pass12345', is_superuser=True)
        self.client.login(username='admin_group_search', password='pass12345')
        StudyGroup.objects.create(name='П-1-23')
        StudyGroup.objects.create(name='БД-1-23')

    def test_group_list_search_by_name(self):
        response = self.client.get(reverse('group_list'), {'q': 'бд'})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'БД-1-23')
        self.assertNotContains(response, 'П-1-23')


class AdminPanelTests(TestCase):
    def setUp(self):
        self.admin = User.objects.create_superuser('control_admin', 'admin@example.com', 'pass12345')
        self.client.login(username='control_admin', password='pass12345')

    def test_index_lists_registered_entities(self):
        response = self.client.get(reverse('admin_panel:index'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'core.group')
        self.assertContains(response, 'grading.grade')

    def test_create_update_and_history_log_changes(self):
        create_response = self.client.post(
            reverse('admin_panel:add', kwargs={'model_key': 'core.subject'}),
            {'name': 'Админ-тест', 'source': 'manual', 'external_id': '', 'is_active': 'on', '_save': '1'},
        )
        self.assertEqual(create_response.status_code, 302)
        subject = Subject.objects.get(name='Админ-тест')

        update_response = self.client.post(
            reverse('admin_panel:change', kwargs={'model_key': 'core.subject', 'pk': subject.pk}),
            {'name': 'Админ-тест 2', 'source': 'manual', 'external_id': '', 'is_active': 'on', '_save': '1'},
        )
        self.assertEqual(update_response.status_code, 302)
        subject.refresh_from_db()
        self.assertEqual(subject.name, 'Админ-тест 2')
        self.assertEqual(AdminLog.objects.filter(object_id=str(subject.pk)).count(), 2)

        history_response = self.client.get(reverse('admin_panel:history', kwargs={'model_key': 'core.subject', 'pk': subject.pk}))
        self.assertEqual(history_response.status_code, 200)
        self.assertContains(history_response, 'История изменений')

    def test_bulk_delete(self):
        first = Subject.objects.create(name='Bulk A')
        second = Subject.objects.create(name='Bulk B')
        response = self.client.post(
            reverse('admin_panel:list', kwargs={'model_key': 'core.subject'}),
            {'action': 'bulk_delete', 'selected': [str(first.pk), str(second.pk)]},
        )
        self.assertEqual(response.status_code, 302)
        self.assertFalse(Subject.objects.filter(pk__in=[first.pk, second.pk]).exists())
        self.assertEqual(AdminLog.objects.filter(action=AdminLog.Action.DELETE).count(), 2)

    def test_can_set_user_password(self):
        user = User.objects.create_user('password_target', password='oldpass123')
        response = self.client.post(
            reverse('admin_panel:change', kwargs={'model_key': 'auth.user', 'pk': user.pk}),
            {
                'username': 'password_target',
                'first_name': '',
                'last_name': '',
                'email': '',
                'is_active': 'on',
                'password1': 'newpass123',
                'password2': 'newpass123',
                '_save': '1',
            },
        )
        self.assertEqual(response.status_code, 302)
        user.refresh_from_db()
        self.assertTrue(user.check_password('newpass123'))
        self.assertFalse(user.check_password('oldpass123'))

    def test_student_cannot_open_control_panel(self):
        self.client.logout()
        student_user = User.objects.create_user('control_student', password='pass12345')
        student_group, _ = Group.objects.get_or_create(name='Student')
        student_user.groups.add(student_group)
        self.client.login(username='control_student', password='pass12345')
        response = self.client.get(reverse('admin_panel:index'))
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, 'core.group')
