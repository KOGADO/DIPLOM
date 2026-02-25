from collections import defaultdict

from django.core.management.base import BaseCommand
from django.db import transaction

from grading.models import Course, Grade, Lesson, StudentCourse
from users.models import Teacher


def teacher_full_name(teacher):
    return " ".join(
        [(teacher.user.first_name or "").strip(), (teacher.user.last_name or "").strip()]
    ).strip() or teacher.user.username


class Command(BaseCommand):
    help = "Объединяет дубли преподавателей с одинаковым ФИО."

    def add_arguments(self, parser):
        parser.add_argument("--dry-run", action="store_true", help="Только показать изменения")

    def _merge_course_data(self, source_course, target_course, dry_run=False):
        merged_lessons = Lesson.objects.filter(course=source_course)
        merged_grades = Grade.objects.filter(course=source_course)
        merged_student_courses = StudentCourse.objects.filter(course=source_course)

        if dry_run:
            return (
                merged_lessons.count(),
                merged_grades.count(),
                merged_student_courses.count(),
            )

        lessons_count = merged_lessons.update(course=target_course)
        grades_count = merged_grades.update(course=target_course)

        student_courses_count = 0
        target_student_ids = set(
            StudentCourse.objects.filter(course=target_course).values_list("student_id", flat=True)
        )
        for student_course in merged_student_courses:
            if student_course.student_id in target_student_ids:
                student_course.delete()
                continue
            student_course.course = target_course
            student_course.save(update_fields=["course"])
            student_courses_count += 1

        return lessons_count, grades_count, student_courses_count

    def handle(self, *args, **options):
        dry_run = options["dry_run"]
        teachers = Teacher.objects.select_related("user").all().order_by("id")

        by_name = defaultdict(list)
        for teacher in teachers:
            by_name[teacher_full_name(teacher)].append(teacher)

        duplicate_groups = {name: group for name, group in by_name.items() if len(group) > 1}

        total_deleted_teachers = 0
        total_moved_courses = 0
        total_merged_courses = 0
        total_lessons = 0
        total_grades = 0
        total_student_courses = 0

        with transaction.atomic():
            for full_name, group in duplicate_groups.items():
                primary = group[0]
                duplicates = group[1:]

                self.stdout.write(
                    f"{'[DRY] ' if dry_run else ''}merge '{full_name}': primary={primary.id}, duplicates={[t.id for t in duplicates]}"
                )

                for dup_teacher in duplicates:
                    courses = list(
                        Course.objects.filter(teacher=dup_teacher).select_related("subject", "group")
                    )
                    for course in courses:
                        target_course = Course.objects.filter(
                            subject=course.subject,
                            teacher=primary,
                            group=course.group,
                            semester=course.semester,
                        ).first()
                        if target_course:
                            l_count, g_count, sc_count = self._merge_course_data(
                                course, target_course, dry_run=dry_run
                            )
                            total_lessons += l_count
                            total_grades += g_count
                            total_student_courses += sc_count
                            total_merged_courses += 1
                            if not dry_run:
                                course.delete()
                        else:
                            total_moved_courses += 1
                            if not dry_run:
                                course.teacher = primary
                                course.save(update_fields=["teacher"])

                    total_deleted_teachers += 1
                    if not dry_run:
                        dup_teacher.delete()

            if dry_run:
                transaction.set_rollback(True)

        mode = "DRY-RUN" if dry_run else "DONE"
        self.stdout.write(
            self.style.SUCCESS(
                f"[{mode}] duplicate_groups={len(duplicate_groups)}, "
                f"deleted_teachers={total_deleted_teachers}, moved_courses={total_moved_courses}, "
                f"merged_courses={total_merged_courses}, moved_lessons={total_lessons}, "
                f"moved_grades={total_grades}, moved_student_courses={total_student_courses}"
            )
        )
