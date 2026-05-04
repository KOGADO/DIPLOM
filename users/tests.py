from datetime import date

from django.contrib.auth.models import Group, User
from django.test import TestCase
from django.urls import reverse

from core.models import Group as StudyGroup
from core.models import Subject
from grading.models import Attendance, Course, Grade, Lesson
from users.models import ChatDialog, ChatMessage, Parent, Student, Teacher


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


class ParentAccessTests(TestCase):
    def setUp(self):
        parent_group, _ = Group.objects.get_or_create(name='Parent')
        student_group, _ = Group.objects.get_or_create(name='Student')

        study_group = StudyGroup.objects.create(name='РОД-1')
        other_group = StudyGroup.objects.create(name='РОД-2')
        subject = Subject.objects.create(name='Родительский тест')

        teacher_user = User.objects.create_user(username='teacher_parent_case', password='pass12345')
        teacher = Teacher.objects.create(user=teacher_user)

        child_user = User.objects.create_user(username='child_parent_case', first_name='Анна', last_name='Иванова', password='pass12345')
        child_user.groups.add(student_group)
        self.child = Student.objects.create(user=child_user, group=study_group)

        other_child_user = User.objects.create_user(username='other_child_parent_case', password='pass12345')
        self.other_child = Student.objects.create(user=other_child_user, group=other_group)

        parent_user = User.objects.create_user(username='parent_case', password='pass12345')
        parent_user.groups.add(parent_group)
        self.parent = Parent.objects.create(user=parent_user)
        self.parent.children.add(self.child)

        self.course = Course.objects.create(subject=subject, teacher=teacher, group=study_group, semester='2025/2026-2', year=2026)
        lesson = Lesson.objects.create(course=self.course, date=date(2026, 4, 20), topic='Контрольная')
        Grade.objects.create(student=self.child, course=self.course, value=5, date=date(2026, 4, 20))
        Attendance.objects.create(student=self.child, lesson=lesson, status=Attendance.Status.PRESENT)

    def test_parent_dashboard_shows_child_statistics(self):
        self.client.login(username='parent_case', password='pass12345')
        response = self.client.get(reverse('parent_dashboard'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Кабинет родителя')
        self.assertContains(response, 'Успеваемость по предметам')
        self.assertContains(response, 'Родительский тест')

    def test_parent_can_open_child_profile_and_subject_journal(self):
        self.client.login(username='parent_case', password='pass12345')
        profile_response = self.client.get(reverse('student_detail', kwargs={'pk': self.child.pk}))
        self.assertEqual(profile_response.status_code, 200)

        journal_response = self.client.get(
            reverse('student_course_journal', kwargs={'student_id': self.child.pk, 'course_id': self.course.pk})
        )
        self.assertEqual(journal_response.status_code, 200)
        self.assertContains(journal_response, 'Контрольная')

    def test_parent_cannot_open_unrelated_student_profile(self):
        self.client.login(username='parent_case', password='pass12345')
        response = self.client.get(reverse('student_detail', kwargs={'pk': self.other_child.pk}))
        self.assertEqual(response.status_code, 403)

    def test_parent_dashboard_redirects_from_root(self):
        self.client.login(username='parent_case', password='pass12345')
        response = self.client.get('/', follow=False)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse('parent_dashboard'))


class ChatTests(TestCase):
    def setUp(self):
        student_group, _ = Group.objects.get_or_create(name='Student')
        teacher_group, _ = Group.objects.get_or_create(name='Teacher')

        self.study_group = StudyGroup.objects.create(name='ЧАТ-1')
        self.other_group = StudyGroup.objects.create(name='ЧАТ-2')
        self.subject = Subject.objects.create(name='Чатология')

        self.teacher_user = User.objects.create_user(username='chat_teacher', password='pass12345')
        self.teacher_user.groups.add(teacher_group)
        self.teacher = Teacher.objects.create(user=self.teacher_user)

        self.other_teacher_user = User.objects.create_user(username='chat_other_teacher', password='pass12345')
        self.other_teacher_user.groups.add(teacher_group)
        self.other_teacher = Teacher.objects.create(user=self.other_teacher_user)

        self.student_user = User.objects.create_user(username='chat_student', password='pass12345')
        self.student_user.groups.add(student_group)
        self.student = Student.objects.create(user=self.student_user, group=self.study_group)

        self.other_student_user = User.objects.create_user(username='chat_other_student', password='pass12345')
        self.other_student_user.groups.add(student_group)
        self.other_student = Student.objects.create(user=self.other_student_user, group=self.other_group)

        self.course = Course.objects.create(
            subject=self.subject,
            teacher=self.teacher,
            group=self.study_group,
            semester='2025/2026-2',
            year=2026,
        )
        self.grade = Grade.objects.create(
            student=self.student,
            course=self.course,
            value=4,
            date=date(2026, 4, 21),
        )

    def test_student_creates_general_chat(self):
        self.client.login(username='chat_student', password='pass12345')
        response = self.client.post(
            reverse('chat_new'),
            {'teacher': self.teacher.id, 'title': 'Общий вопрос', 'message': 'Когда консультация?'},
        )
        self.assertEqual(response.status_code, 302)
        chat = ChatDialog.objects.get(title='Общий вопрос')
        self.assertIsNone(chat.related_grade)
        self.assertEqual(chat.messages.get().message, 'Когда консультация?')

    def test_student_creates_grade_chat_and_context_is_visible(self):
        Lesson.objects.create(course=self.course, date=self.grade.date, topic='Связанная тема')
        self.client.login(username='chat_student', password='pass12345')
        response = self.client.post(
            f"{reverse('chat_new')}?grade={self.grade.id}",
            {
                'grade': self.grade.id,
                'teacher': self.teacher.id,
                'title': 'Вопрос по оценке',
                'message': 'Почему 4?',
            },
        )
        self.assertEqual(response.status_code, 302)
        chat = ChatDialog.objects.get(title='Вопрос по оценке')
        self.assertEqual(chat.related_grade_id, self.grade.id)

        detail = self.client.get(reverse('chat_detail', kwargs={'pk': chat.pk}))
        self.assertContains(detail, 'Вопрос по оценке')
        self.assertContains(detail, 'Чатология')
        self.assertContains(detail, 'Оценка')
        self.assertContains(detail, '<strong>4</strong>', html=True)
        self.assertContains(detail, '21.04.2026')
        self.assertContains(detail, 'Связанная тема')
        self.assertContains(detail, f'?grade={self.grade.id}#grade-{self.grade.id}')
        self.assertNotContains(detail, 'Оценка · оценка')

    def test_teacher_can_open_linked_student_journal_for_own_course(self):
        self.client.login(username='chat_teacher', password='pass12345')
        response = self.client.get(
            reverse('student_course_journal', kwargs={'student_id': self.student.pk, 'course_id': self.course.pk})
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Журнал студента')

    def test_teacher_sees_linked_grade_marker_in_student_journal(self):
        Lesson.objects.create(course=self.course, date=self.grade.date, topic='Связанная тема')
        self.client.login(username='chat_teacher', password='pass12345')
        response = self.client.get(
            reverse('student_course_journal', kwargs={'student_id': self.student.pk, 'course_id': self.course.pk}),
            {'grade': self.grade.id},
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, f'id="grade-{self.grade.id}"')
        self.assertContains(response, 'Оценка из вопроса студента')
        self.assertContains(response, 'Связанная тема')
        self.assertContains(response, 'Вопрос студента')

    def test_teacher_replies_and_student_sees_unread(self):
        chat = ChatDialog.objects.create(student=self.student, teacher=self.teacher, title='Ответьте')
        ChatMessage.objects.create(
            chat=chat,
            sender=self.student_user,
            sender_role=ChatMessage.SenderRole.STUDENT,
            message='Здравствуйте',
        )

        self.client.login(username='chat_teacher', password='pass12345')
        response = self.client.post(reverse('chat_detail', kwargs={'pk': chat.pk}), {'message': 'Добрый день'})
        self.assertEqual(response.status_code, 302)
        self.client.logout()

        self.client.login(username='chat_student', password='pass12345')
        list_response = self.client.get(reverse('chat_list'))
        self.assertContains(list_response, 'Добрый день')
        self.assertContains(list_response, '1')

        detail_response = self.client.get(reverse('chat_detail', kwargs={'pk': chat.pk}))
        self.assertEqual(detail_response.status_code, 200)
        self.assertFalse(chat.messages.exclude(sender=self.student_user).filter(is_read=False).exists())

    def test_student_cannot_write_unrelated_teacher(self):
        self.client.login(username='chat_student', password='pass12345')
        response = self.client.post(
            reverse('chat_new'),
            {'teacher': self.other_teacher.id, 'title': 'Нельзя', 'message': 'Тест'},
        )
        self.assertEqual(response.status_code, 403)

    def test_chat_api_flow(self):
        self.client.login(username='chat_student', password='pass12345')
        create_response = self.client.post(
            '/api/chats/',
            {'teacher': self.teacher.id, 'related_grade': self.grade.id, 'title': 'API вопрос'},
            content_type='application/json',
        )
        self.assertEqual(create_response.status_code, 201)
        chat_id = create_response.json()['id']

        message_response = self.client.post(
            f'/api/chats/{chat_id}/messages/',
            {'message': 'API сообщение'},
            content_type='application/json',
        )
        self.assertEqual(message_response.status_code, 201)
        message_id = message_response.json()['id']

        self.client.logout()
        self.client.login(username='chat_teacher', password='pass12345')
        messages_response = self.client.get(f'/api/chats/{chat_id}/messages/')
        self.assertEqual(messages_response.status_code, 200)
        read_response = self.client.patch(f'/api/messages/{message_id}/read/', content_type='application/json')
        self.assertEqual(read_response.status_code, 200)
        self.assertTrue(ChatMessage.objects.get(pk=message_id).is_read)


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
