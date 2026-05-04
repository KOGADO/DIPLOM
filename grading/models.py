from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models


class Course(models.Model):
    subject = models.ForeignKey(
        'core.Subject',
        on_delete=models.CASCADE,
        related_name='courses',
        verbose_name='Предмет',
    )
    teacher = models.ForeignKey(
        'users.Teacher',
        on_delete=models.CASCADE,
        related_name='courses',
        verbose_name='Преподаватель',
    )
    group = models.ForeignKey(
        'core.Group',
        on_delete=models.CASCADE,
        related_name='courses',
        verbose_name='Группа',
    )
    semester = models.CharField('Семестр', max_length=20)
    year = models.PositiveIntegerField('Год', null=True, blank=True)
    students = models.ManyToManyField('users.Student', through='StudentCourse', related_name='courses')
    source = models.CharField('Источник', max_length=50, default='mpt.ru', db_index=True)
    external_id = models.CharField('Внешний ID', max_length=255, null=True, blank=True, db_index=True)
    is_active = models.BooleanField('Активен', default=True)

    class Meta:
        verbose_name = 'Курс'
        verbose_name_plural = 'Курсы'
        ordering = ['-year', 'semester']
        constraints = [
            models.UniqueConstraint(
                fields=['subject', 'teacher', 'group', 'semester'],
                name='uniq_course_subject_teacher_group_semester',
            ),
            models.UniqueConstraint(fields=['source', 'external_id'], name='uniq_course_source_external_id'),
        ]

    def __str__(self):
        return f'{self.subject} - {self.group} ({self.semester})'


class StudentCourse(models.Model):
    student = models.ForeignKey('users.Student', on_delete=models.CASCADE, verbose_name='Студент')
    course = models.ForeignKey(Course, on_delete=models.CASCADE, verbose_name='Курс')

    class Meta:
        verbose_name = 'Запись студента на курс'
        verbose_name_plural = 'Записи студентов на курс'
        constraints = [
            models.UniqueConstraint(fields=['student', 'course'], name='uniq_student_course'),
        ]

    def __str__(self):
        return f'{self.student} - {self.course}'


class Lesson(models.Model):
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='lessons', verbose_name='Курс')
    date = models.DateField('Дата занятия')
    topic = models.CharField('Тема', max_length=255, blank=True)

    class Meta:
        verbose_name = 'Занятие'
        verbose_name_plural = 'Занятия'
        ordering = ['-date']

    def __str__(self):
        return f'{self.course} - {self.date}'


class LectureTopic(models.Model):
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='lecture_topics', verbose_name='Курс')
    title = models.CharField('Тема лекции', max_length=255)
    order = models.PositiveIntegerField('Порядок', default=0)
    created_at = models.DateTimeField('Создана', auto_now_add=True)

    class Meta:
        verbose_name = 'Тема лекции'
        verbose_name_plural = 'Темы лекций'
        ordering = ['order', 'title']
        constraints = [
            models.UniqueConstraint(fields=['course', 'title'], name='uniq_lecture_topic_course_title'),
        ]

    def __str__(self):
        return self.title


class Attendance(models.Model):
    class Status(models.TextChoices):
        PRESENT = 'PRESENT', 'Присутствовал'
        ABSENT = 'ABSENT', 'Отсутствовал'
        LATE = 'LATE', 'Опоздал'

    lesson = models.ForeignKey(Lesson, on_delete=models.CASCADE, related_name='attendances', verbose_name='Занятие')
    student = models.ForeignKey('users.Student', on_delete=models.CASCADE, related_name='attendances', verbose_name='Студент')
    status = models.CharField('Статус', max_length=10, choices=Status.choices)
    comment = models.CharField('Комментарий', max_length=255, blank=True)

    class Meta:
        verbose_name = 'Посещаемость'
        verbose_name_plural = 'Посещаемость'
        constraints = [
            models.UniqueConstraint(fields=['lesson', 'student'], name='uniq_attendance_lesson_student'),
        ]

    def __str__(self):
        return f'{self.lesson} - {self.student} ({self.status})'


class Grade(models.Model):
    class GradeType(models.TextChoices):
        GRADE = 'GRADE', 'Оценка'

    class Value(models.IntegerChoices):
        POOR = 2, '2 (неудовлетворительно)'
        SATISFACTORY = 3, '3 (удовлетворительно)'
        GOOD = 4, '4 (хорошо)'
        EXCELLENT = 5, '5 (отлично)'

    student = models.ForeignKey('users.Student', on_delete=models.CASCADE, related_name='grades', verbose_name='Студент')
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='grades', verbose_name='Курс')
    grade_type = models.CharField('Тип оценки', max_length=10, choices=GradeType.choices, default=GradeType.GRADE)
    value = models.PositiveSmallIntegerField(
        'Оценка',
        choices=Value.choices,
        validators=[MinValueValidator(2), MaxValueValidator(5)],
    )
    date = models.DateField('Дата')
    comment = models.CharField('Комментарий', max_length=255, blank=True)

    class Meta:
        verbose_name = 'Оценка'
        verbose_name_plural = 'Оценки'
        ordering = ['-date']

    def __str__(self):
        return f'{self.student} - {self.course}: {self.value}'
