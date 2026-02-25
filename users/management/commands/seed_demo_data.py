from datetime import date, timedelta
from random import choice, randint

from django.contrib.auth.models import Group, Permission, User
from django.core.management.base import BaseCommand
from django.db import transaction

from core.models import Group as StudyGroup, Subject
from grading.models import Attendance, Course, Grade, Lesson, StudentCourse
from users.models import Student, Teacher


class Command(BaseCommand):
    help = 'Создает демо-данные для проекта учета успеваемости'

    @transaction.atomic
    def handle(self, *args, **options):
        self._create_role_groups()

        admin_user, _ = User.objects.get_or_create(username='admin', defaults={'is_staff': True, 'is_superuser': True})
        admin_user.is_staff = True
        admin_user.is_superuser = True
        admin_user.set_password('admin123')
        admin_user.save()

        teacher_users = []
        for i in range(1, 3):
            user, _ = User.objects.get_or_create(
                username=f'teacher{i}',
                defaults={'first_name': f'Преподаватель{i}', 'last_name': 'Иванов'},
            )
            user.set_password('teacher123')
            user.save()
            user.groups.add(Group.objects.get(name='Teacher'))
            teacher, _ = Teacher.objects.get_or_create(user=user)
            teacher.save()
            teacher_users.append(teacher)

        group1, _ = StudyGroup.objects.get_or_create(name='ИТ-101', defaults={'curator': teacher_users[0].user})
        group2, _ = StudyGroup.objects.get_or_create(name='МАТ-201', defaults={'curator': teacher_users[1].user})
        group1.curator = teacher_users[0].user
        group1.save()
        group2.curator = teacher_users[1].user
        group2.save()

        subjects = []
        for name in ['Алгоритмы', 'Базы данных', 'Веб-разработка', 'Линейная алгебра', 'Теория вероятностей']:
            subj, _ = Subject.objects.get_or_create(name=name)
            subjects.append(subj)

        students = []
        for i in range(1, 21):
            user, _ = User.objects.get_or_create(
                username=f'student{i}',
                defaults={'first_name': f'Студент{i}', 'last_name': 'Петров'},
            )
            user.set_password('student123')
            user.save()
            user.groups.add(Group.objects.get(name='Student'))
            group = group1 if i <= 10 else group2
            student, _ = Student.objects.get_or_create(
                user=user,
                defaults={'group': group, 'date_of_birth': date(2005, 1, 1) + timedelta(days=i)},
            )
            student.group = group
            student.save()
            students.append(student)

        admin_user.groups.add(Group.objects.get(name='Admin'))

        courses = []
        course_specs = [
            (subjects[0], teacher_users[0], group1, '2025/2026-1', 2025),
            (subjects[1], teacher_users[0], group1, '2025/2026-1', 2025),
            (subjects[2], teacher_users[0], group1, '2025/2026-2', 2026),
            (subjects[3], teacher_users[1], group2, '2025/2026-1', 2025),
            (subjects[4], teacher_users[1], group2, '2025/2026-2', 2026),
        ]

        for subject, teacher, group, semester, year in course_specs:
            course, _ = Course.objects.get_or_create(
                subject=subject,
                teacher=teacher,
                group=group,
                semester=semester,
                defaults={'year': year},
            )
            course.year = year
            course.save()
            courses.append(course)

        for course in courses:
            group_students = Student.objects.filter(group=course.group)
            for student in group_students:
                StudentCourse.objects.get_or_create(student=student, course=course)

                for idx in range(5):
                    Grade.objects.get_or_create(
                        student=student,
                        course=course,
                        grade_type=Grade.GradeType.GRADE,
                        date=date(2025, 9, 1) + timedelta(days=idx * 7),
                        defaults={'value': randint(2, 5), 'comment': 'Демо оценка'},
                    )

            for lidx in range(6):
                lesson, _ = Lesson.objects.get_or_create(
                    course=course,
                    date=date(2025, 9, 1) + timedelta(days=lidx * 7),
                    defaults={'topic': f'Тема {lidx + 1}'},
                )
                for student in group_students:
                    Attendance.objects.get_or_create(
                        lesson=lesson,
                        student=student,
                        defaults={
                            'status': choice([Attendance.Status.PRESENT, Attendance.Status.PRESENT, Attendance.Status.LATE, Attendance.Status.ABSENT]),
                            'comment': '',
                        },
                    )

        self.stdout.write(self.style.SUCCESS('Демо-данные успешно созданы'))

    def _create_role_groups(self):
        admin_group, _ = Group.objects.get_or_create(name='Admin')
        teacher_group, _ = Group.objects.get_or_create(name='Teacher')
        student_group, _ = Group.objects.get_or_create(name='Student')

        all_permissions = Permission.objects.all()
        admin_group.permissions.set(all_permissions)

        teacher_perms = Permission.objects.filter(codename__in=['view_grade', 'add_grade', 'change_grade', 'view_attendance', 'add_attendance', 'change_attendance', 'view_lesson', 'add_lesson', 'change_lesson', 'view_course'])
        teacher_group.permissions.set(teacher_perms)

        student_perms = Permission.objects.filter(codename__in=['view_grade', 'view_attendance', 'view_course'])
        student_group.permissions.set(student_perms)
