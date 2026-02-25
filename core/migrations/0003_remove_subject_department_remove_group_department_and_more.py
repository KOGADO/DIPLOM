from django.db import migrations, models


def merge_duplicate_subjects(apps, schema_editor):
    Subject = apps.get_model('core', 'Subject')
    Course = apps.get_model('grading', 'Course')
    StudentCourse = apps.get_model('grading', 'StudentCourse')
    Lesson = apps.get_model('grading', 'Lesson')
    Grade = apps.get_model('grading', 'Grade')

    duplicate_names = (
        Subject.objects.values('name')
        .order_by()
        .annotate(total=models.Count('id'))
        .filter(total__gt=1)
        .values_list('name', flat=True)
    )

    for name in duplicate_names:
        subjects = list(Subject.objects.filter(name=name).order_by('id'))
        primary_subject = subjects[0]

        for duplicate_subject in subjects[1:]:
            duplicate_courses = Course.objects.filter(subject_id=duplicate_subject.id).order_by('id')
            for duplicate_course in duplicate_courses:
                target_course = Course.objects.filter(
                    subject_id=primary_subject.id,
                    teacher_id=duplicate_course.teacher_id,
                    group_id=duplicate_course.group_id,
                    semester=duplicate_course.semester,
                ).first()

                if target_course:
                    for student_course in StudentCourse.objects.filter(course_id=duplicate_course.id):
                        StudentCourse.objects.get_or_create(
                            student_id=student_course.student_id,
                            course_id=target_course.id,
                        )

                    Lesson.objects.filter(course_id=duplicate_course.id).update(course_id=target_course.id)
                    Grade.objects.filter(course_id=duplicate_course.id).update(course_id=target_course.id)
                    duplicate_course.delete()
                else:
                    duplicate_course.subject_id = primary_subject.id
                    duplicate_course.save(update_fields=['subject_id'])

            duplicate_subject.delete()


class Migration(migrations.Migration):
    dependencies = [
        ('core', '0002_group_external_id_group_is_active_group_source_and_more'),
        ('users', '0003_remove_teacher_department'),
        ('grading', '0003_grade_value_five_point_scale'),
    ]

    operations = [
        migrations.RemoveConstraint(
            model_name='subject',
            name='uniq_subject_name_department',
        ),
        migrations.RemoveField(
            model_name='subject',
            name='department',
        ),
        migrations.RemoveField(
            model_name='group',
            name='department',
        ),
        migrations.RunPython(merge_duplicate_subjects, migrations.RunPython.noop),
        migrations.AlterField(
            model_name='subject',
            name='name',
            field=models.CharField(max_length=255, unique=True, verbose_name='Название предмета'),
        ),
        migrations.DeleteModel(
            name='Department',
        ),
    ]
