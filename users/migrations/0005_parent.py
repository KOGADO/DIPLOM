# Generated manually for parent role support.

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0004_teacher_department_repair'),
    ]

    operations = [
        migrations.CreateModel(
            name='Parent',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                (
                    'user',
                    models.OneToOneField(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name='parent_profile',
                        to='auth.user',
                        verbose_name='Пользователь',
                    ),
                ),
                (
                    'children',
                    models.ManyToManyField(
                        blank=True,
                        related_name='parents',
                        to='users.student',
                        verbose_name='Дети',
                    ),
                ),
            ],
            options={
                'verbose_name': 'Родитель',
                'verbose_name_plural': 'Родители',
            },
        ),
    ]
