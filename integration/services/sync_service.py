from __future__ import annotations

import hashlib
import logging
from dataclasses import dataclass

from django.contrib.auth.models import Group as AuthGroup
from django.contrib.auth.models import User
from django.db import transaction
from django.utils.text import slugify
from text_unidecode import unidecode

from core.models import Group, Subject
from grading.models import Course
from users.models import Teacher

logger = logging.getLogger(__name__)

SOURCE_NAME = 'mpt.ru'


@dataclass
class SyncResult:
    created: int = 0
    updated: int = 0
    deactivated: int = 0

    def as_dict(self) -> dict:
        return {'created': self.created, 'updated': self.updated, 'deactivated': self.deactivated}


class MptSyncService:
    def __init__(self, provider) -> None:
        self.provider = provider

    def sync_groups(self, dry_run: bool = False) -> SyncResult:
        payload = self.provider.fetch_groups()
        incoming = {self._group_external_id(item['name']): item['name'] for item in payload}
        return self._sync_group_like_model(
            model=Group,
            incoming=incoming,
            fields_mapper=lambda name: {'name': name, 'source': SOURCE_NAME, 'external_id': self._group_external_id(name), 'is_active': True},
            dry_run=dry_run,
        )

    def sync_teachers(self, dry_run: bool = False) -> SyncResult:
        payload = self.provider.fetch_teachers()
        incoming = {self._teacher_external_id(item['full_name']): item['full_name'] for item in payload}

        result = SyncResult()
        existing = {
            t.external_id: t
            for t in Teacher.objects.filter(source=SOURCE_NAME, external_id__isnull=False)
        }
        incoming_ids = set(incoming.keys())

        if not dry_run:
            self._ensure_teacher_groups()

        for ext_id, full_name in incoming.items():
            teacher = existing.get(ext_id)
            if teacher is None:
                result.created += 1
                logger.info('teacher created: %s', full_name)
                if dry_run:
                    continue

                user = self._create_teacher_user(full_name)
                teacher = Teacher.objects.create(
                    user=user,
                    source=SOURCE_NAME,
                    external_id=ext_id,
                    is_active=True,
                )
                self._attach_teacher_groups(user)
            else:
                changed = False
                if not teacher.is_active:
                    teacher.is_active = True
                    changed = True
                current_full_name = self._teacher_display_name(teacher)
                if current_full_name != full_name:
                    first_name, last_name = self._split_name_for_user(full_name)
                    teacher.user.first_name = first_name
                    teacher.user.last_name = last_name
                    changed = True

                if changed:
                    result.updated += 1
                    logger.info('teacher updated: %s', full_name)
                    if not dry_run:
                        teacher.user.save(update_fields=['first_name', 'last_name'])
                        teacher.save(update_fields=['is_active'])

        for ext_id, teacher in existing.items():
            if ext_id in incoming_ids:
                continue
            if teacher.is_active:
                result.deactivated += 1
                logger.info('teacher deactivated: %s', self._teacher_display_name(teacher))
                if not dry_run:
                    teacher.is_active = False
                    teacher.save(update_fields=['is_active'])

        return result

    def sync_subjects(self, dry_run: bool = False) -> SyncResult:
        payload = self.provider.fetch_subjects()
        incoming = {self._subject_external_id(item['name']): item['name'] for item in payload}
        return self._sync_group_like_model(
            model=Subject,
            incoming=incoming,
            fields_mapper=lambda name: {'name': name, 'source': SOURCE_NAME, 'external_id': self._subject_external_id(name), 'is_active': True},
            dry_run=dry_run,
        )

    def sync_courses(self, *, semester: str, dry_run: bool = False) -> SyncResult:
        payload = self.provider.fetch_courses(semester=semester)
        result = SyncResult()

        groups = {
            g.external_id: g for g in Group.objects.filter(source=SOURCE_NAME, external_id__isnull=False)
        }
        subjects = {
            s.external_id: s for s in Subject.objects.filter(source=SOURCE_NAME, external_id__isnull=False)
        }
        teachers = {
            t.external_id: t for t in Teacher.objects.filter(source=SOURCE_NAME, external_id__isnull=False)
        }

        dry_groups = {}
        dry_subjects = {}
        dry_teachers = {}
        if dry_run:
            dry_groups = {self._group_external_id(item['name']): item['name'] for item in self.provider.fetch_groups()}
            dry_subjects = {self._subject_external_id(item['name']): item['name'] for item in self.provider.fetch_subjects()}
            dry_teachers = {self._teacher_external_id(item['full_name']): item['full_name'] for item in self.provider.fetch_teachers()}

        existing = {
            c.external_id: c
            for c in Course.objects.filter(
                source=SOURCE_NAME,
                semester=semester,
                external_id__isnull=False,
            ).select_related('group', 'subject', 'teacher')
        }

        incoming_ids: set[str] = set()

        for item in payload:
            group_id = self._group_external_id(item['group_name'])
            subject_id = self._subject_external_id(item['subject_name'])
            teacher_id = self._teacher_external_id(item['teacher_name'])

            if dry_run:
                group_name = dry_groups.get(group_id)
                subject_name = dry_subjects.get(subject_id)
                teacher_name = dry_teachers.get(teacher_id)
                if not group_name or not subject_name or not teacher_name:
                    logger.info('course skipped due to missing relation: %s', item)
                    continue
            else:
                group = groups.get(group_id)
                subject = subjects.get(subject_id)
                teacher = teachers.get(teacher_id)
                if not group or not subject or not teacher:
                    logger.info('course skipped due to missing relation: %s', item)
                    continue
                group_name = group.name
                subject_name = subject.name
                teacher_name = self._teacher_display_name(teacher)

            if not group_name or not subject_name or not teacher_name:
                logger.info('course skipped due to missing relation: %s', item)
                continue

            ext_id = self._course_external_id(
                group_name=group_name,
                teacher_name=teacher_name,
                subject_name=subject_name,
                semester=semester,
            )
            incoming_ids.add(ext_id)

            course = existing.get(ext_id)
            if course is None:
                result.created += 1
                logger.info('course created: %s | %s | %s', group_name, subject_name, teacher_name)
                if not dry_run:
                    Course.objects.create(
                        group=group,
                        subject=subject,
                        teacher=teacher,
                        semester=semester,
                        source=SOURCE_NAME,
                        external_id=ext_id,
                        is_active=True,
                    )
                continue

            changed = False
            if not course.is_active:
                course.is_active = True
                changed = True
            if changed:
                result.updated += 1
                logger.info('course updated: %s', course)
                if not dry_run:
                    course.save(update_fields=['is_active'])

        for ext_id, course in existing.items():
            if ext_id in incoming_ids:
                continue
            if course.is_active:
                result.deactivated += 1
                logger.info('course deactivated: %s', course)
                if not dry_run:
                    course.is_active = False
                    course.save(update_fields=['is_active'])

        return result

    @transaction.atomic
    def sync_catalog(self, *, semester: str, dry_run: bool = False) -> dict:
        groups = self.sync_groups(dry_run=dry_run)
        teachers = self.sync_teachers(dry_run=dry_run)
        subjects = self.sync_subjects(dry_run=dry_run)
        courses = self.sync_courses(semester=semester, dry_run=dry_run)
        return {
            'groups': groups.as_dict(),
            'teachers': teachers.as_dict(),
            'subjects': subjects.as_dict(),
            'courses': courses.as_dict(),
        }

    def _sync_group_like_model(self, *, model, incoming: dict, fields_mapper, dry_run: bool) -> SyncResult:
        result = SyncResult()
        existing = {
            obj.external_id: obj
            for obj in model.objects.filter(source=SOURCE_NAME, external_id__isnull=False)
        }
        incoming_ids = set(incoming.keys())

        for ext_id, name in incoming.items():
            obj = existing.get(ext_id)
            if obj is None:
                result.created += 1
                logger.info('%s created: %s', model.__name__.lower(), name)
                if not dry_run:
                    model.objects.create(**fields_mapper(name))
                continue

            changed = False
            if getattr(obj, 'name', None) != name:
                obj.name = name
                changed = True
            if hasattr(obj, 'is_active') and not obj.is_active:
                obj.is_active = True
                changed = True

            if changed:
                result.updated += 1
                logger.info('%s updated: %s', model.__name__.lower(), name)
                if not dry_run:
                    fields = ['is_active']
                    if hasattr(obj, 'name'):
                        fields.append('name')
                    obj.save(update_fields=fields)

        for ext_id, obj in existing.items():
            if ext_id in incoming_ids:
                continue
            if getattr(obj, 'is_active', True):
                result.deactivated += 1
                logger.info('%s deactivated: %s', model.__name__.lower(), obj)
                if not dry_run:
                    obj.is_active = False
                    obj.save(update_fields=['is_active'])

        return result

    @staticmethod
    def _group_external_id(name: str) -> str:
        base = slugify(unidecode(name), allow_unicode=False)
        if base:
            return base
        return hashlib.sha1(name.encode('utf-8')).hexdigest()[:16]

    @staticmethod
    def _teacher_external_id(full_name: str) -> str:
        base = slugify(unidecode(full_name), allow_unicode=False)
        if base:
            return base
        return hashlib.sha1(full_name.encode('utf-8')).hexdigest()[:16]

    @staticmethod
    def _subject_external_id(name: str) -> str:
        base = slugify(unidecode(name), allow_unicode=False)
        if base:
            return base
        return hashlib.sha1(name.encode('utf-8')).hexdigest()[:16]

    @staticmethod
    def _course_external_id(*, group_name: str, teacher_name: str, subject_name: str, semester: str) -> str:
        raw = f'{group_name}|{teacher_name}|{subject_name}|{semester}'
        return hashlib.sha1(raw.encode('utf-8')).hexdigest()

    @staticmethod
    def _teacher_display_name(teacher: Teacher) -> str:
        full = f'{teacher.user.first_name} {teacher.user.last_name}'.strip()
        return full or teacher.user.username

    @staticmethod
    def _split_name_for_user(full_name: str) -> tuple[str, str]:
        parts = full_name.split(' ')
        if len(parts) == 1:
            return parts[0], ''
        return ' '.join(parts[:-1]), parts[-1]

    def _create_teacher_user(self, full_name: str) -> User:
        slug = slugify(unidecode(full_name), allow_unicode=False) or 'teacher'
        digest = hashlib.sha1(full_name.encode('utf-8')).hexdigest()[:8]
        username_base = f'{slug}_{digest}'
        username = username_base[:150]

        if User.objects.filter(username=username).exists():
            username = f'{username_base[:140]}_{hashlib.sha1(username_base.encode()).hexdigest()[:6]}'

        first_name, last_name = self._split_name_for_user(full_name)
        user = User.objects.create(username=username, first_name=first_name, last_name=last_name)
        user.set_unusable_password()
        user.save(update_fields=['password'])
        return user

    @staticmethod
    def _ensure_teacher_groups() -> None:
        AuthGroup.objects.get_or_create(name='Teachers')
        AuthGroup.objects.get_or_create(name='Teacher')

    @staticmethod
    def _attach_teacher_groups(user: User) -> None:
        teachers_group = AuthGroup.objects.get(name='Teachers')
        teacher_group = AuthGroup.objects.get(name='Teacher')
        user.groups.add(teachers_group, teacher_group)
