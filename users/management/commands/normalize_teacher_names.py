import hashlib
import re

from django.contrib.auth.models import Group, User
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils.text import slugify

from grading.models import Course
from users.models import Teacher


TOKEN_RE = re.compile(r"[А-ЯЁA-Z]\.\s*[А-ЯЁA-Z]\.\s*[А-ЯЁA-Z][а-яёa-z\-]+")


def split_teacher_name(raw_name):
    normalized = " ".join((raw_name or "").replace(";", ",").split())
    if not normalized:
        return []

    parts = [p.strip() for p in normalized.split(",") if p.strip()]
    if len(parts) > 1:
        return dedupe(parts)

    matches = [m.group(0).replace("  ", " ").strip() for m in TOKEN_RE.finditer(normalized)]
    if len(matches) > 1:
        return dedupe(matches)

    return [normalized]


def dedupe(items):
    seen = set()
    result = []
    for item in items:
        key = item.strip()
        if not key or key in seen:
            continue
        seen.add(key)
        result.append(key)
    return result


def split_fio(full_name):
    parts = full_name.split(maxsplit=1)
    if len(parts) == 1:
        return parts[0], ""
    return parts[0], parts[1]


class Command(BaseCommand):
    help = "Нормализует склеенные ФИО преподавателей и дублирует курсы для совместного ведения."

    def add_arguments(self, parser):
        parser.add_argument("--dry-run", action="store_true", help="Только показать изменения")

    def handle(self, *args, **options):
        dry_run = options["dry_run"]
        teacher_group, _ = Group.objects.get_or_create(name="Teacher")

        name_cache = {}
        for teacher in Teacher.objects.select_related("user"):
            full_name = " ".join([teacher.user.first_name or "", teacher.user.last_name or ""]).strip() or teacher.user.username
            name_cache[full_name] = teacher

        updated_teachers = 0
        created_teachers = 0
        created_courses = 0

        with transaction.atomic():
            for teacher in Teacher.objects.select_related("user").all():
                full_name = " ".join([teacher.user.first_name or "", teacher.user.last_name or ""]).strip()
                tokens = split_teacher_name(full_name)
                if not tokens:
                    continue

                primary_name = tokens[0]
                primary_first, primary_last = split_fio(primary_name)

                if len(tokens) == 1 and full_name == primary_name:
                    continue

                if dry_run:
                    self.stdout.write(f"[DRY] Teacher #{teacher.id}: '{full_name}' -> '{primary_name}' + {tokens[1:]}")
                else:
                    teacher.user.first_name = primary_first
                    teacher.user.last_name = primary_last
                    teacher.user.save(update_fields=["first_name", "last_name"])
                updated_teachers += 1
                name_cache[primary_name] = teacher

                courses = list(Course.objects.filter(teacher=teacher).select_related("subject", "group"))
                for extra_name in tokens[1:]:
                    extra_teacher = name_cache.get(extra_name)
                    if not extra_teacher:
                        extra_first, extra_last = split_fio(extra_name)
                        base_username = slugify(f"{extra_first}_{extra_last}") or "teacher"
                        salt = hashlib.sha1(extra_name.encode("utf-8")).hexdigest()[:6]
                        username = f"{base_username}_{salt}"
                        while User.objects.filter(username=username).exists():
                            salt = hashlib.sha1(f"{extra_name}{username}".encode("utf-8")).hexdigest()[:6]
                            username = f"{base_username}_{salt}"

                        if dry_run:
                            self.stdout.write(f"[DRY] create teacher '{extra_name}' ({username})")
                            extra_teacher = teacher
                        else:
                            user = User.objects.create(
                                username=username,
                                first_name=extra_first,
                                last_name=extra_last,
                            )
                            user.set_unusable_password()
                            user.save(update_fields=["password"])
                            user.groups.add(teacher_group)
                            extra_teacher = Teacher.objects.create(
                                user=user,
                                department=teacher.department,
                                source=teacher.source,
                                is_active=True,
                            )
                            name_cache[extra_name] = extra_teacher
                        created_teachers += 1

                    for course in courses:
                        if dry_run:
                            self.stdout.write(
                                f"[DRY] course copy: {course.subject} | {course.group} | {course.semester} -> {extra_name}"
                            )
                            created_courses += 1
                            continue

                        _, created = Course.objects.get_or_create(
                            subject=course.subject,
                            teacher=extra_teacher,
                            group=course.group,
                            semester=course.semester,
                            defaults={
                                "year": course.year,
                                "source": course.source,
                                "is_active": course.is_active,
                            },
                        )
                        if created:
                            created_courses += 1

            if dry_run:
                transaction.set_rollback(True)

        mode = "DRY-RUN" if dry_run else "DONE"
        self.stdout.write(
            self.style.SUCCESS(
                f"[{mode}] updated_teachers={updated_teachers}, created_teachers={created_teachers}, created_courses={created_courses}"
            )
        )
