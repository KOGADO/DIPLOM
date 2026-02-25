from __future__ import annotations

import logging
import re
import time
from dataclasses import dataclass
from typing import Iterable
from urllib.parse import urljoin, urlparse
from urllib.robotparser import RobotFileParser

import requests
from bs4 import BeautifulSoup, Tag
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from integration.providers.base import BaseScheduleProvider

logger = logging.getLogger(__name__)

DAYS_OF_WEEK = {
    'понедельник',
    'вторник',
    'среда',
    'четверг',
    'пятница',
    'суббота',
    'воскресенье',
}

HEADER_SKIP_TOKENS = {'пара', 'предмет', 'преподаватель'}
TEACHER_SKIP_VALUES = {'', '-', 'практика'}


@dataclass
class ParsedRow:
    subject: str
    teachers: list[str]


class MptScheduleProvider(BaseScheduleProvider):
    def __init__(
        self,
        *,
        base_url: str,
        schedule_path: str,
        timeout: int = 15,
        delay_seconds: float = 0.5,
        user_agent: str = 'mpt-progress-tracker/1.0 (educational project)',
        retries: int = 3,
        html_override: str | None = None,
    ) -> None:
        self.base_url = base_url.rstrip('/')
        self.schedule_path = schedule_path
        self.timeout = timeout
        self.delay_seconds = delay_seconds
        self.user_agent = user_agent
        self.retries = retries
        self.html_override = html_override

        self._session = requests.Session()
        retry = Retry(
            total=retries,
            read=retries,
            connect=retries,
            backoff_factor=0.5,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=['GET'],
        )
        self._session.mount('http://', HTTPAdapter(max_retries=retry))
        self._session.mount('https://', HTTPAdapter(max_retries=retry))
        self._session.headers.update({'User-Agent': self.user_agent})

        self._cached_parsed: list[dict] | None = None

    @property
    def schedule_url(self) -> str:
        return urljoin(f'{self.base_url}/', self.schedule_path.lstrip('/'))

    def fetch_groups(self) -> list[dict]:
        groups = {item['group_name'] for item in self._parse_schedule()}
        return [{'name': group_name} for group_name in sorted(groups)]

    def fetch_teachers(self) -> list[dict]:
        teachers: set[str] = set()
        for item in self._parse_schedule():
            teachers.update(item['teachers'])
        return [{'full_name': teacher} for teacher in sorted(teachers)]

    def fetch_subjects(self) -> list[dict]:
        subjects = {item['subject'] for item in self._parse_schedule()}
        return [{'name': subject} for subject in sorted(subjects)]

    def fetch_courses(self, semester: str) -> list[dict]:
        courses = []
        for item in self._parse_schedule():
            courses.append(
                {
                    'group_name': item['group_name'],
                    'subject_name': item['subject'],
                    'teacher_name': item['teacher'],
                    'semester': semester,
                }
            )
        return courses

    def _ensure_allowed_by_robots(self) -> None:
        parsed = urlparse(self.schedule_url)
        robots_url = f'{parsed.scheme}://{parsed.netloc}/robots.txt'
        parser = RobotFileParser()
        parser.set_url(robots_url)
        parser.read()

        if not parser.can_fetch(self.user_agent, self.schedule_url):
            raise RuntimeError(f'URL blocked by robots.txt: {self.schedule_url}')

    def _fetch_html(self) -> str:
        if self.html_override is not None:
            return self.html_override

        self._ensure_allowed_by_robots()
        time.sleep(self.delay_seconds)
        response = self._session.get(self.schedule_url, timeout=self.timeout)
        response.raise_for_status()
        return response.text

    def _parse_schedule(self) -> list[dict]:
        if self._cached_parsed is not None:
            return self._cached_parsed

        html = self._fetch_html()
        soup = BeautifulSoup(html, 'lxml')

        group_blocks = self._extract_group_blocks(soup)
        parsed_items: list[dict] = []

        for block in group_blocks:
            groups = self._split_group_names(block['group_text'])
            rows = self._extract_rows_from_nodes(block['nodes'])
            for group_name in groups:
                for row in rows:
                    for teacher in row.teachers:
                        parsed_items.append(
                            {
                                'group_name': group_name,
                                'subject': row.subject,
                                'teacher': teacher,
                                'teachers': row.teachers,
                            }
                        )

        self._cached_parsed = self._deduplicate(parsed_items)
        return self._cached_parsed

    def _extract_group_blocks(self, soup: BeautifulSoup) -> list[dict]:
        anchors = self._find_group_anchors(soup)
        blocks: list[dict] = []

        if anchors:
            for index, anchor in enumerate(anchors):
                next_anchor = anchors[index + 1] if index + 1 < len(anchors) else None
                nodes: list[Tag] = []
                for sibling in anchor.next_siblings:
                    if isinstance(sibling, Tag) and sibling == next_anchor:
                        break
                    if isinstance(sibling, Tag):
                        nodes.append(sibling)
                blocks.append({'group_text': anchor.get_text(' ', strip=True), 'nodes': nodes})
            return blocks

        logger.warning('Не найдены явные заголовки групп, используем fallback по тексту')
        text_lines = [self._normalize_spaces(line) for line in soup.get_text('\n').splitlines()]
        current_group = None
        current_lines: list[str] = []
        for line in text_lines:
            if not line:
                continue
            if re.search(r'\bГруппа\b', line, re.IGNORECASE):
                if current_group:
                    blocks.append({'group_text': current_group, 'nodes': current_lines[:]})
                current_group = line
                current_lines = []
            elif current_group:
                current_lines.append(line)

        if current_group:
            blocks.append({'group_text': current_group, 'nodes': current_lines[:]})
        return blocks

    def _find_group_anchors(self, soup: BeautifulSoup) -> list[Tag]:
        anchors: list[Tag] = []
        for tag in soup.find_all(re.compile('^h[1-6]$')):
            text = self._normalize_spaces(tag.get_text(' ', strip=True))
            if re.search(r'\bГруппа\b', text, re.IGNORECASE):
                anchors.append(tag)

        if anchors:
            return anchors

        # Secondary fallback: wrappers like <p><strong>### Группа ...</strong></p>
        for tag in soup.find_all(['p', 'div', 'strong']):
            text = self._normalize_spaces(tag.get_text(' ', strip=True))
            if re.match(r'^(#+\s*)?Группа\b', text, re.IGNORECASE):
                anchors.append(tag)
        return anchors

    def _extract_rows_from_nodes(self, nodes: Iterable[object]) -> list[ParsedRow]:
        rows: list[ParsedRow] = []

        for node in nodes:
            if isinstance(node, str):
                rows.extend(self._parse_text_lines([node]))
                continue

            if not isinstance(node, Tag):
                continue

            table_rows = self._parse_tables(node)
            if table_rows:
                rows.extend(table_rows)
                continue

            text_lines = [self._normalize_spaces(line) for line in node.get_text('\n').splitlines()]
            rows.extend(self._parse_text_lines(text_lines))

        # Remove duplicates preserving order
        unique: list[ParsedRow] = []
        seen: set[tuple[str, tuple[str, ...]]] = set()
        for row in rows:
            key = (row.subject, tuple(row.teachers))
            if key in seen:
                continue
            seen.add(key)
            unique.append(row)
        return unique

    def _parse_tables(self, node: Tag) -> list[ParsedRow]:
        parsed: list[ParsedRow] = []
        for tr in node.find_all('tr'):
            cells = [self._normalize_spaces(c.get_text(' ', strip=True)) for c in tr.find_all(['th', 'td'])]
            cells = [c for c in cells if c]
            if len(cells) < 2:
                continue

            lower_cells = [c.lower() for c in cells]
            if HEADER_SKIP_TOKENS.issubset(set(lower_cells)):
                continue
            if any('предмет' in c.lower() and 'преподаватель' in c.lower() for c in cells):
                continue

            subject = ''
            teacher_raw = ''
            if len(cells) >= 3:
                subject = cells[1]
                teacher_raw = cells[2]
            else:
                subject = cells[0]
                teacher_raw = cells[1]

            row = self._build_row(subject, teacher_raw)
            if row:
                parsed.append(row)
        return parsed

    def _parse_text_lines(self, lines: Iterable[str]) -> list[ParsedRow]:
        parsed: list[ParsedRow] = []
        for line in lines:
            line = self._normalize_spaces(line)
            if not line:
                continue

            lowered = line.lower()
            if lowered in DAYS_OF_WEEK:
                continue
            if 'пара' in lowered and 'предмет' in lowered and 'преподаватель' in lowered:
                continue

            parts = [p.strip() for p in re.split(r'\s{2,}|\t+', line) if p.strip()]
            if len(parts) >= 3:
                subject = parts[1]
                teacher_raw = parts[2]
            elif len(parts) == 2:
                subject = parts[0]
                teacher_raw = parts[1]
            else:
                # fallback regex: number + subject + teacher
                match = re.match(r'^\d+\s+(.+?)\s+([А-ЯA-Z][^\d]+)$', line)
                if not match:
                    continue
                subject = match.group(1)
                teacher_raw = match.group(2)

            row = self._build_row(subject, teacher_raw)
            if row:
                parsed.append(row)
        return parsed

    def _build_row(self, subject: str, teacher_raw: str) -> ParsedRow | None:
        subject_norm = self._normalize_spaces(subject)
        if not subject_norm:
            return None
        if subject_norm.isdigit():
            return None

        teachers = self._split_teachers(teacher_raw)
        if not teachers:
            logger.warning('Строка без преподавателя пропущена: subject=%s teacher=%s', subject_norm, teacher_raw)
            return None

        return ParsedRow(subject=subject_norm, teachers=teachers)

    def _split_group_names(self, group_text: str) -> list[str]:
        raw = self._normalize_spaces(group_text)
        raw = re.sub(r'^(#+\s*)?Группа\s*', '', raw, flags=re.IGNORECASE)
        tokens = [self._normalize_spaces(item) for item in re.split(r'[,;]', raw)]
        return [item for item in tokens if item]

    def _split_teachers(self, teachers_raw: str) -> list[str]:
        tokens = [self._normalize_spaces(item) for item in teachers_raw.split(',')]
        clean: list[str] = []
        for token in tokens:
            if token.lower() in TEACHER_SKIP_VALUES:
                continue
            clean.append(token)
        return clean

    @staticmethod
    def _normalize_spaces(value: str) -> str:
        return re.sub(r'\s+', ' ', value or '').strip()

    @staticmethod
    def _deduplicate(items: list[dict]) -> list[dict]:
        deduped: list[dict] = []
        seen: set[tuple[str, str, str]] = set()
        for item in items:
            key = (item['group_name'], item['subject'], item['teacher'])
            if key in seen:
                continue
            seen.add(key)
            deduped.append(item)
        return deduped
