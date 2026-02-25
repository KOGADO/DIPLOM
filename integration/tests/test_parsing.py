from pathlib import Path

from django.test import SimpleTestCase

from integration.providers.mpt_schedule_provider import MptScheduleProvider


class MptParsingTests(SimpleTestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        fixture_path = Path(__file__).parent / 'fixtures' / 'mpt_schedule_sample.html'
        cls.fixture_html = fixture_path.read_text(encoding='utf-8')

    def build_provider(self):
        return MptScheduleProvider(
            base_url='https://mpt.ru',
            schedule_path='/raspisanie/',
            html_override=self.fixture_html,
        )

    def test_parse_groups_split_by_comma_and_semicolon(self):
        provider = self.build_provider()
        groups = provider.fetch_groups()
        names = {item['name'] for item in groups}
        self.assertIn('Э-2-22', names)
        self.assertIn('Э-11/2-23', names)
        self.assertIn('Э-2-24', names)
        self.assertIn('Э-11/2-25', names)
        self.assertEqual(len(names), 4)

    def test_parse_teachers_split_by_comma(self):
        provider = self.build_provider()
        teachers = provider.fetch_teachers()
        names = {item['full_name'] for item in teachers}
        self.assertIn('А.А. Сердцева', names)
        self.assertIn('В.В. Колесникович', names)
        self.assertIn('О.О. Орлова', names)
        self.assertIn('Р.Р. Романов', names)
        self.assertNotIn('ПРАКТИКА', names)

    def test_parse_subject_teacher_rows(self):
        provider = self.build_provider()
        courses = provider.fetch_courses(semester='2025/2026-2')
        tupled = {(item['group_name'], item['subject_name'], item['teacher_name']) for item in courses}
        self.assertIn(('Э-2-22', 'Математика', 'А.А. Сердцева'), tupled)
        self.assertIn(('Э-11/2-23', 'Математика', 'В.В. Колесникович'), tupled)
        self.assertIn(('Э-2-24', 'Русский язык', 'О.О. Орлова'), tupled)
        self.assertIn(('Э-11/2-25', 'Русский язык', 'Р.Р. Романов'), tupled)
