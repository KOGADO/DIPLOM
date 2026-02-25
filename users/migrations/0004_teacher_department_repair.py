from django.db import migrations, models

from core.migration_utils import add_column_if_missing


def ensure_teacher_department_column(apps, schema_editor):
    add_column_if_missing(schema_editor, 'users_teacher', 'department_id', sql_type='INTEGER')


def noop_reverse(apps, schema_editor):
    return


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0005_subject_department_repair'),
        ('users', '0003_remove_teacher_department'),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            database_operations=[
                migrations.RunPython(ensure_teacher_department_column, noop_reverse),
            ],
            state_operations=[
                migrations.AddField(
                    model_name='teacher',
                    name='department',
                    field=models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=models.SET_NULL,
                        related_name='teachers',
                        to='core.department',
                        verbose_name='Отделение',
                    ),
                ),
            ],
        ),
    ]
