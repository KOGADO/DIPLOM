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


class Parent(models.Model):
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='parent_profile',
        verbose_name='Пользователь',
    )
    children = models.ManyToManyField(
        Student,
        related_name='parents',
        verbose_name='Дети',
        blank=True,
    )

    class Meta:
        verbose_name = 'Родитель'
        verbose_name_plural = 'Родители'

    def __str__(self):
        return self.user.get_full_name() or self.user.username


class ChatDialog(models.Model):
    student = models.ForeignKey(
        Student,
        on_delete=models.CASCADE,
        related_name='chat_dialogs',
        verbose_name='Студент',
    )
    teacher = models.ForeignKey(
        Teacher,
        on_delete=models.CASCADE,
        related_name='chat_dialogs',
        verbose_name='Преподаватель',
    )
    related_grade = models.ForeignKey(
        'grading.Grade',
        on_delete=models.SET_NULL,
        related_name='chat_dialogs',
        null=True,
        blank=True,
        verbose_name='Связанная оценка',
    )
    title = models.CharField('Тема', max_length=255)
    created_at = models.DateTimeField('Создан', auto_now_add=True)
    updated_at = models.DateTimeField('Обновлен', auto_now=True)

    class Meta:
        verbose_name = 'Диалог'
        verbose_name_plural = 'Диалоги'
        ordering = ['-updated_at']

    def __str__(self):
        return self.title


class ChatMessage(models.Model):
    class SenderRole(models.TextChoices):
        STUDENT = 'student', 'Студент'
        TEACHER = 'teacher', 'Преподаватель'

    chat = models.ForeignKey(
        ChatDialog,
        on_delete=models.CASCADE,
        related_name='messages',
        verbose_name='Диалог',
    )
    sender = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='chat_messages',
        verbose_name='Отправитель',
    )
    sender_role = models.CharField('Роль отправителя', max_length=16, choices=SenderRole.choices)
    message = models.TextField('Сообщение')
    attachment = models.FileField('Вложение', upload_to='chat_attachments/', null=True, blank=True)
    created_at = models.DateTimeField('Создано', auto_now_add=True)
    is_read = models.BooleanField('Прочитано', default=False)

    class Meta:
        verbose_name = 'Сообщение чата'
        verbose_name_plural = 'Сообщения чата'
        ordering = ['created_at']

    def __str__(self):
        return f'{self.sender}: {self.message[:40]}'
