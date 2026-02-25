from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ('core', '0002_group_external_id_group_is_active_group_source_and_more'),
        ('grading', '0001_initial'),
        ('users', '0002_teacher_external_id_teacher_is_active_teacher_source_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='course',
            name='source',
            field=models.CharField('Источник', max_length=50, default='mpt.ru', db_index=True),
        ),
        migrations.AddField(
            model_name='course',
            name='external_id',
            field=models.CharField('Внешний ID', max_length=255, null=True, blank=True, db_index=True),
        ),
        migrations.AddField(
            model_name='course',
            name='is_active',
            field=models.BooleanField('Активен', default=True),
        ),
        migrations.AddConstraint(
            model_name='course',
            constraint=models.UniqueConstraint(fields=('source', 'external_id'), name='uniq_course_source_external_id'),
        ),
    ]
