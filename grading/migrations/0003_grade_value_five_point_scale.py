from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import migrations, models
from django.db.models import Case, IntegerField, Value, When


def convert_grades_to_five_point(apps, schema_editor):
    Grade = apps.get_model('grading', 'Grade')
    qs = Grade.objects.all()
    if not qs.exists():
        return

    bounds = qs.aggregate(min_value=models.Min('value'), max_value=models.Max('value'))
    min_value = bounds['min_value']
    max_value = bounds['max_value']

    if min_value is None or max_value is None:
        return

    # Already in 2..5 scale.
    if min_value >= 2 and max_value <= 5:
        return

    # If legacy 1..5 scale is present, only normalize 1 -> 2.
    if min_value >= 1 and max_value <= 5:
        Grade.objects.filter(value=1).update(value=2)
        return

    # Legacy 0..100 conversion.
    Grade.objects.update(
        value=Case(
            When(value__gte=90, value__lte=100, then=Value(5)),
            When(value__gte=75, value__lte=89, then=Value(4)),
            When(value__gte=60, value__lte=74, then=Value(3)),
            default=Value(2),
            output_field=IntegerField(),
        )
    )


class Migration(migrations.Migration):
    dependencies = [
        ('grading', '0002_course_external_id_course_is_active_course_source_and_more'),
    ]

    operations = [
        migrations.RunPython(convert_grades_to_five_point, migrations.RunPython.noop),
        migrations.AlterField(
            model_name='grade',
            name='value',
            field=models.PositiveSmallIntegerField(
                'Оценка',
                choices=[
                    (2, '2 (неудовлетворительно)'),
                    (3, '3 (удовлетворительно)'),
                    (4, '4 (хорошо)'),
                    (5, '5 (отлично)'),
                ],
                validators=[MinValueValidator(2), MaxValueValidator(5)],
            ),
        ),
    ]
