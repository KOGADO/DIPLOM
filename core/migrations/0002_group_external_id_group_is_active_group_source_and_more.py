from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ('core', '0001_initial'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AddField(
            model_name='group',
            name='source',
            field=models.CharField('Источник', max_length=50, default='mpt.ru', db_index=True),
        ),
        migrations.AddField(
            model_name='group',
            name='external_id',
            field=models.CharField('Внешний ID', max_length=255, null=True, blank=True, db_index=True),
        ),
        migrations.AddField(
            model_name='group',
            name='is_active',
            field=models.BooleanField('Активна', default=True),
        ),
        migrations.AddField(
            model_name='subject',
            name='source',
            field=models.CharField('Источник', max_length=50, default='mpt.ru', db_index=True),
        ),
        migrations.AddField(
            model_name='subject',
            name='external_id',
            field=models.CharField('Внешний ID', max_length=255, null=True, blank=True, db_index=True),
        ),
        migrations.AddField(
            model_name='subject',
            name='is_active',
            field=models.BooleanField('Активен', default=True),
        ),
        migrations.AddConstraint(
            model_name='group',
            constraint=models.UniqueConstraint(fields=('source', 'external_id'), name='uniq_group_source_external_id'),
        ),
        migrations.AddConstraint(
            model_name='subject',
            constraint=models.UniqueConstraint(fields=('source', 'external_id'), name='uniq_subject_source_external_id'),
        ),
    ]
