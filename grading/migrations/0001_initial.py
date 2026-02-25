from django.db import migrations, models
import django.core.validators
import django.db.models.deletion


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        ('core', '0001_initial'),
        ('users', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='Course',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('semester', models.CharField(max_length=20, verbose_name='Семестр')),
                ('year', models.PositiveIntegerField(blank=True, null=True, verbose_name='Год')),
                ('group', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='courses', to='core.group', verbose_name='Группа')),
                ('subject', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='courses', to='core.subject', verbose_name='Предмет')),
                ('teacher', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='courses', to='users.teacher', verbose_name='Преподаватель')),
            ],
            options={
                'verbose_name': 'Курс',
                'verbose_name_plural': 'Курсы',
                'ordering': ['-year', 'semester'],
            },
        ),
        migrations.CreateModel(
            name='Lesson',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('date', models.DateField(verbose_name='Дата занятия')),
                ('topic', models.CharField(blank=True, max_length=255, verbose_name='Тема')),
                ('course', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='lessons', to='grading.course', verbose_name='Курс')),
            ],
            options={
                'verbose_name': 'Занятие',
                'verbose_name_plural': 'Занятия',
                'ordering': ['-date'],
            },
        ),
        migrations.CreateModel(
            name='Grade',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('grade_type', models.CharField(choices=[('EXAM', 'Экзамен'), ('TEST', 'Тест'), ('HW', 'Домашняя работа'), ('LAB', 'Лабораторная')], max_length=10, verbose_name='Тип оценки')),
                ('value', models.PositiveSmallIntegerField(validators=[django.core.validators.MinValueValidator(0), django.core.validators.MaxValueValidator(100)], verbose_name='Оценка')),
                ('date', models.DateField(verbose_name='Дата')),
                ('comment', models.CharField(blank=True, max_length=255, verbose_name='Комментарий')),
                ('course', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='grades', to='grading.course', verbose_name='Курс')),
                ('student', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='grades', to='users.student', verbose_name='Студент')),
            ],
            options={
                'verbose_name': 'Оценка',
                'verbose_name_plural': 'Оценки',
                'ordering': ['-date'],
            },
        ),
        migrations.CreateModel(
            name='Attendance',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('status', models.CharField(choices=[('PRESENT', 'Присутствовал'), ('ABSENT', 'Отсутствовал'), ('LATE', 'Опоздал')], max_length=10, verbose_name='Статус')),
                ('comment', models.CharField(blank=True, max_length=255, verbose_name='Комментарий')),
                ('lesson', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='attendances', to='grading.lesson', verbose_name='Занятие')),
                ('student', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='attendances', to='users.student', verbose_name='Студент')),
            ],
            options={
                'verbose_name': 'Посещаемость',
                'verbose_name_plural': 'Посещаемость',
            },
        ),
        migrations.CreateModel(
            name='StudentCourse',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('course', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='grading.course', verbose_name='Курс')),
                ('student', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='users.student', verbose_name='Студент')),
            ],
            options={
                'verbose_name': 'Запись студента на курс',
                'verbose_name_plural': 'Записи студентов на курс',
            },
        ),
        migrations.AddField(
            model_name='course',
            name='students',
            field=models.ManyToManyField(related_name='courses', through='grading.StudentCourse', to='users.student'),
        ),
        migrations.AddConstraint(
            model_name='attendance',
            constraint=models.UniqueConstraint(fields=('lesson', 'student'), name='uniq_attendance_lesson_student'),
        ),
        migrations.AddConstraint(
            model_name='course',
            constraint=models.UniqueConstraint(fields=('subject', 'teacher', 'group', 'semester'), name='uniq_course_subject_teacher_group_semester'),
        ),
        migrations.AddConstraint(
            model_name='studentcourse',
            constraint=models.UniqueConstraint(fields=('student', 'course'), name='uniq_student_course'),
        ),
    ]
