from django.contrib.auth.models import User
from django.db import models


class Teacher(models.Model):
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='teacher_profile',
        verbose_name='Пользователь',
    )
    department = models.ForeignKey(
        'core.Department',
        on_delete=models.SET_NULL,
        related_name='teachers',
        null=True,
        blank=True,
        verbose_name='Отделение',
    )
    source = models.CharField('Источник', max_length=50, default='mpt.ru', db_index=True)
    external_id = models.CharField('Внешний ID', max_length=255, null=True, blank=True, db_index=True)
    is_active = models.BooleanField('Активен', default=True)

    class Meta:
        verbose_name = 'Преподаватель'
        verbose_name_plural = 'Преподаватели'
        constraints = [
            models.UniqueConstraint(fields=['source', 'external_id'], name='uniq_teacher_source_external_id'),
        ]

    def __str__(self):
        return self.user.get_full_name() or self.user.username


class Student(models.Model):
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='student_profile',
        verbose_name='Пользователь',
    )
    group = models.ForeignKey(
        'core.Group',
        on_delete=models.CASCADE,
        related_name='students',
        verbose_name='Группа',
    )
    date_of_birth = models.DateField('Дата рождения', null=True, blank=True)

    class Meta:
        verbose_name = 'Студент'
        verbose_name_plural = 'Студенты'

    def __str__(self):
        return self.user.get_full_name() or self.user.username
