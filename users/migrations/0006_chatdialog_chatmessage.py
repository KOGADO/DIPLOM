# Generated manually for student-teacher chat support.

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('grading', '0005_alter_grade_grade_type'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('users', '0005_parent'),
    ]

    operations = [
        migrations.CreateModel(
            name='ChatDialog',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('title', models.CharField(max_length=255, verbose_name='Тема')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='Создан')),
                ('updated_at', models.DateTimeField(auto_now=True, verbose_name='Обновлен')),
                (
                    'related_grade',
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name='chat_dialogs',
                        to='grading.grade',
                        verbose_name='Связанная оценка',
                    ),
                ),
                (
                    'student',
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name='chat_dialogs',
                        to='users.student',
                        verbose_name='Студент',
                    ),
                ),
                (
                    'teacher',
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name='chat_dialogs',
                        to='users.teacher',
                        verbose_name='Преподаватель',
                    ),
                ),
            ],
            options={
                'verbose_name': 'Диалог',
                'verbose_name_plural': 'Диалоги',
                'ordering': ['-updated_at'],
            },
        ),
        migrations.CreateModel(
            name='ChatMessage',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                (
                    'sender_role',
                    models.CharField(
                        choices=[('student', 'Студент'), ('teacher', 'Преподаватель')],
                        max_length=16,
                        verbose_name='Роль отправителя',
                    ),
                ),
                ('message', models.TextField(verbose_name='Сообщение')),
                ('attachment', models.FileField(blank=True, null=True, upload_to='chat_attachments/', verbose_name='Вложение')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='Создано')),
                ('is_read', models.BooleanField(default=False, verbose_name='Прочитано')),
                (
                    'chat',
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name='messages',
                        to='users.chatdialog',
                        verbose_name='Диалог',
                    ),
                ),
                (
                    'sender',
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name='chat_messages',
                        to=settings.AUTH_USER_MODEL,
                        verbose_name='Отправитель',
                    ),
                ),
            ],
            options={
                'verbose_name': 'Сообщение чата',
                'verbose_name_plural': 'Сообщения чата',
                'ordering': ['created_at'],
            },
        ),
    ]
