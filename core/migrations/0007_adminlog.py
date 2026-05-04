# Generated manually for the project admin panel.

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('contenttypes', '0002_remove_content_type_name'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('core', '0006_group_department_repair'),
    ]

    operations = [
        migrations.CreateModel(
            name='AdminLog',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('object_id', models.CharField(db_index=True, max_length=64, verbose_name='ID объекта')),
                ('object_repr', models.CharField(max_length=255, verbose_name='Объект')),
                (
                    'action',
                    models.CharField(
                        choices=[('create', 'Создание'), ('update', 'Изменение'), ('delete', 'Удаление')],
                        max_length=12,
                        verbose_name='Действие',
                    ),
                ),
                ('changed_fields', models.JSONField(blank=True, default=dict, verbose_name='Измененные поля')),
                ('created_at', models.DateTimeField(auto_now_add=True, db_index=True, verbose_name='Дата и время')),
                (
                    'content_type',
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        to='contenttypes.contenttype',
                        verbose_name='Тип объекта',
                    ),
                ),
                (
                    'user',
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name='admin_logs',
                        to=settings.AUTH_USER_MODEL,
                        verbose_name='Пользователь',
                    ),
                ),
            ],
            options={
                'verbose_name': 'Запись истории админки',
                'verbose_name_plural': 'История админки',
                'ordering': ['-created_at'],
            },
        ),
    ]
