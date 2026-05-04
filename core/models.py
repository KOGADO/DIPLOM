from django.contrib.auth.models import User
from django.conf import settings
from django.contrib.contenttypes.models import ContentType
from django.db import models


class Department(models.Model):
    name = models.CharField('Название отделения', max_length=255, unique=True)

    class Meta:
        verbose_name = 'Отделение'
        verbose_name_plural = 'Отделения'
        ordering = ['name']

    def __str__(self):
        return self.name


class Group(models.Model):
    name = models.CharField('Название группы', max_length=100, unique=True)
    department = models.ForeignKey(
        Department,
        on_delete=models.SET_NULL,
        related_name='groups',
        null=True,
        blank=True,
        verbose_name='Отделение',
    )
    curator = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        related_name='curated_groups',
        null=True,
        blank=True,
        verbose_name='Куратор (пользователь преподавателя)',
    )
    source = models.CharField('Источник', max_length=50, default='mpt.ru', db_index=True)
    external_id = models.CharField('Внешний ID', max_length=255, null=True, blank=True, db_index=True)
    is_active = models.BooleanField('Активна', default=True)

    class Meta:
        verbose_name = 'Учебная группа'
        verbose_name_plural = 'Учебные группы'
        ordering = ['name']
        constraints = [
            models.UniqueConstraint(fields=['source', 'external_id'], name='uniq_group_source_external_id'),
        ]

    def __str__(self):
        return self.name


class Subject(models.Model):
    name = models.CharField('Название предмета', max_length=255, unique=True)
    department = models.ForeignKey(
        Department,
        on_delete=models.SET_NULL,
        related_name='subjects',
        null=True,
        blank=True,
        verbose_name='Отделение',
    )
    source = models.CharField('Источник', max_length=50, default='mpt.ru', db_index=True)
    external_id = models.CharField('Внешний ID', max_length=255, null=True, blank=True, db_index=True)
    is_active = models.BooleanField('Активен', default=True)

    class Meta:
        verbose_name = 'Предмет'
        verbose_name_plural = 'Предметы'
        ordering = ['name']
        constraints = [
            models.UniqueConstraint(fields=['source', 'external_id'], name='uniq_subject_source_external_id'),
        ]

    def __str__(self):
        return self.name


class AdminLog(models.Model):
    class Action(models.TextChoices):
        CREATE = 'create', 'Создание'
        UPDATE = 'update', 'Изменение'
        DELETE = 'delete', 'Удаление'

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='admin_logs',
        verbose_name='Пользователь',
    )
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE, verbose_name='Тип объекта')
    object_id = models.CharField('ID объекта', max_length=64, db_index=True)
    object_repr = models.CharField('Объект', max_length=255)
    action = models.CharField('Действие', max_length=12, choices=Action.choices)
    changed_fields = models.JSONField('Измененные поля', default=dict, blank=True)
    created_at = models.DateTimeField('Дата и время', auto_now_add=True, db_index=True)

    class Meta:
        verbose_name = 'Запись истории админки'
        verbose_name_plural = 'История админки'
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.get_action_display()}: {self.object_repr}'
