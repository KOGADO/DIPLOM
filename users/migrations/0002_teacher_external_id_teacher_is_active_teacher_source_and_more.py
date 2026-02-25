import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ('core', '0002_group_external_id_group_is_active_group_source_and_more'),
        ('users', '0001_initial'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AddField(
            model_name='teacher',
            name='source',
            field=models.CharField('Источник', max_length=50, default='mpt.ru', db_index=True),
        ),
        migrations.AddField(
            model_name='teacher',
            name='external_id',
            field=models.CharField('Внешний ID', max_length=255, null=True, blank=True, db_index=True),
        ),
        migrations.AddField(
            model_name='teacher',
            name='is_active',
            field=models.BooleanField('Активен', default=True),
        ),
        migrations.AlterField(
            model_name='teacher',
            name='department',
            field=models.ForeignKey(
                'core.Department',
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='teachers',
                verbose_name='Кафедра',
                null=True,
                blank=True,
            ),
        ),
        migrations.AddConstraint(
            model_name='teacher',
            constraint=models.UniqueConstraint(fields=('source', 'external_id'), name='uniq_teacher_source_external_id'),
        ),
    ]
