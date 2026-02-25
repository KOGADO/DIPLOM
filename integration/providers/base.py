from __future__ import annotations

from abc import ABC, abstractmethod


class BaseScheduleProvider(ABC):
    @abstractmethod
    def fetch_groups(self) -> list[dict]:
        raise NotImplementedError

    @abstractmethod
    def fetch_teachers(self) -> list[dict]:
        raise NotImplementedError

    @abstractmethod
    def fetch_subjects(self) -> list[dict]:
        raise NotImplementedError

    @abstractmethod
    def fetch_courses(self, semester: str) -> list[dict]:
        raise NotImplementedError
