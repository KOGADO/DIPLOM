import base64
import os
import random
from datetime import date, timedelta

from locust import HttpUser, between, task


def _basic_auth_header(username: str, password: str) -> dict[str, str]:
    raw = f"{username}:{password}".encode("utf-8")
    token = base64.b64encode(raw).decode("ascii")
    return {"Authorization": f"Basic {token}"}


class GradebookApiUser(HttpUser):
    """
    Load profile:
    - GET /api/courses/ -> weight 1
    - POST /api/lessons/ -> weight 4
    """

    wait_time = between(0.2, 1.0)

    def on_start(self) -> None:
        username = os.getenv("LOADTEST_USERNAME", "admin")
        password = os.getenv("LOADTEST_PASSWORD", "admin123")
        self.headers = _basic_auth_header(username, password)
        self.course_ids = self._fetch_course_ids()

    def _fetch_course_ids(self) -> list[int]:
        with self.client.get(
            "/api/courses/",
            headers=self.headers,
            name="GET /api/courses/",
            catch_response=True,
        ) as response:
            if response.status_code != 200:
                response.failure(f"Cannot load courses, status={response.status_code}")
                return []
            data = response.json()
            if isinstance(data, dict):
                results = data.get("results", [])
            else:
                results = data
            ids = [item.get("id") for item in results if isinstance(item, dict) and item.get("id")]
            if not ids:
                response.failure("No courses available for POST /api/lessons/")
            return ids

    def _generate_lesson_payload(self) -> dict[str, str | int]:
        start = date.today() - timedelta(days=30)
        lesson_date = start + timedelta(days=random.randint(0, 60))
        topic_suffix = random.randint(1000, 9999)
        return {
            "course": random.choice(self.course_ids),
            "date": lesson_date.isoformat(),
            "topic": f"Load topic {topic_suffix}",
        }

    @task(1)
    def get_courses(self) -> None:
        self.client.get("/api/courses/", headers=self.headers, name="GET /api/courses/")

    @task(4)
    def create_lesson(self) -> None:
        if not self.course_ids:
            self.course_ids = self._fetch_course_ids()
        if not self.course_ids:
            return
        payload = self._generate_lesson_payload()
        self.client.post(
            "/api/lessons/",
            json=payload,
            headers=self.headers,
            name="POST /api/lessons/",
        )
