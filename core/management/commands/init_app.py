from django.contrib.auth.models import Group
from django.core.management import BaseCommand, call_command

from core.models import Department, Group as StudyGroup, Subject
from users.models import Teacher


class Command(BaseCommand):
    help = 'Initializes database: migrate, role groups, and base reference data.'

    def handle(self, *args, **options):
        self.stdout.write(self.style.NOTICE('Running migrations...'))
        call_command('migrate', interactive=False)

        for role_name in ('Admin', 'Teacher', 'Student', 'Parent'):
            _, created = Group.objects.get_or_create(name=role_name)
            action = 'created' if created else 'exists'
            self.stdout.write(self.style.SUCCESS(f'Role group {role_name}: {action}'))

        default_department, created = Department.objects.get_or_create(name='Общее отделение')
        action = 'created' if created else 'exists'
        self.stdout.write(self.style.SUCCESS(f'Department "Общее отделение": {action}'))

        updated_groups = StudyGroup.objects.filter(department__isnull=True).update(department=default_department)
        updated_subjects = Subject.objects.filter(department__isnull=True).update(department=default_department)
        updated_teachers = Teacher.objects.filter(department__isnull=True).update(department=default_department)
        self.stdout.write(
            self.style.SUCCESS(
                f'Filled NULL departments: groups={updated_groups}, subjects={updated_subjects}, teachers={updated_teachers}'
            )
        )

        self.stdout.write(self.style.SUCCESS('init_app completed successfully.'))
