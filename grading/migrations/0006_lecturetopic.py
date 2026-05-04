# Generated manually for lecture topic import support.

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('grading', '0005_alter_grade_grade_type'),
    ]

    operations = [
        migrations.CreateModel(
            name='LectureTopic',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('title', models.CharField(max_length=255, verbose_name='Тема лекции')),
                ('order', models.PositiveIntegerField(default=0, verbose_name='Порядок')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='Создана')),
                (
                    'course',
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name='lecture_topics',
                        to='grading.course',
                        verbose_name='Курс',
                    ),
                ),
            ],
            options={
                'verbose_name': 'Тема лекции',
                'verbose_name_plural': 'Темы лекций',
                'ordering': ['order', 'title'],
                'constraints': [
                    models.UniqueConstraint(fields=('course', 'title'), name='uniq_lecture_topic_course_title'),
                ],
            },
        ),
    ]
