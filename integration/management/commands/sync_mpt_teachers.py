from django.conf import settings
from django.core.management.base import BaseCommand

from integration.providers.mpt_schedule_provider import MptScheduleProvider
from integration.services.sync_service import MptSyncService


class Command(BaseCommand):
    help = 'Синхронизация только преподавателей из расписания mpt.ru'

    def add_arguments(self, parser):
        parser.add_argument('--dry-run', action='store_true')
        parser.add_argument('--delay', type=float, default=settings.MPT_SYNC_DELAY_SECONDS)
        parser.add_argument('--timeout', type=int, default=settings.MPT_SYNC_TIMEOUT)

    def handle(self, *args, **options):
        provider = MptScheduleProvider(
            base_url=settings.MPT_SYNC_BASE_URL,
            schedule_path=settings.MPT_SYNC_SCHEDULE_PATH,
            timeout=options['timeout'],
            delay_seconds=options['delay'],
            user_agent=settings.MPT_SYNC_USER_AGENT,
        )
        service = MptSyncService(provider)
        result = service.sync_teachers(dry_run=options['dry_run'])
        self.stdout.write(self.style.SUCCESS(f'teachers: {result.as_dict()}'))
