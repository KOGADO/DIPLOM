from django.contrib.auth.models import User
from django.test import TestCase

from core.models import Group, Subject
from grading.models import Course
from integration.services.sync_service import MptSyncService
from users.models import Teacher


class FakeProvider:
    def __init__(self, *, groups, teachers, subjects, courses):
        self._groups = groups
        self._teachers = teachers
        self._subjects = subjects
        self._courses = courses

    def fetch_groups(self):
        return self._groups

    def fetch_teachers(self):
        return self._teachers

    def fetch_subjects(self):
        return self._subjects

    def fetch_courses(self, semester: str):
        return [dict(item, semester=semester) for item in self._courses]


class MptUpsertTests(TestCase):
    def setUp(self):
        self.semester = '2025/2026-2'
        self.payload = {
            'groups': [{'name': 'Э-2-22'}],
            'teachers': [{'full_name': 'А.А. Сердцева'}],
            'subjects': [{'name': 'Математика'}],
            'courses': [
                {
                    'group_name': 'Э-2-22',
                    'teacher_name': 'А.А. Сердцева',
                    'subject_name': 'Математика',
                }
            ],
        }

    def build_service(self, payload):
        provider = FakeProvider(
            groups=payload['groups'],
            teachers=payload['teachers'],
            subjects=payload['subjects'],
            courses=payload['courses'],
        )
        return MptSyncService(provider)

    def test_repeated_sync_does_not_create_duplicates(self):
        service = self.build_service(self.payload)
        service.sync_catalog(semester=self.semester, dry_run=False)
        service.sync_catalog(semester=self.semester, dry_run=False)

        self.assertEqual(Group.objects.filter(source='mpt.ru').count(), 1)
        self.assertEqual(Teacher.objects.filter(source='mpt.ru').count(), 1)
        self.assertEqual(Subject.objects.filter(source='mpt.ru').count(), 1)
        self.assertEqual(Course.objects.filter(source='mpt.ru', semester=self.semester).count(), 1)

    def test_missing_entities_are_soft_deactivated(self):
        service = self.build_service(self.payload)
        service.sync_catalog(semester=self.semester, dry_run=False)

        empty_payload = {'groups': [], 'teachers': [], 'subjects': [], 'courses': []}
        service_empty = self.build_service(empty_payload)
        service_empty.sync_catalog(semester=self.semester, dry_run=False)

        self.assertFalse(Group.objects.get(source='mpt.ru').is_active)
        self.assertFalse(Teacher.objects.get(source='mpt.ru').is_active)
        self.assertFalse(Subject.objects.get(source='mpt.ru').is_active)
        self.assertFalse(Course.objects.get(source='mpt.ru', semester=self.semester).is_active)

        # User remains in DB and keeps unusable password
        teacher = Teacher.objects.get(source='mpt.ru')
        self.assertIsInstance(teacher.user, User)
        self.assertFalse(teacher.user.has_usable_password())
