import os
import logging
import shutil
import socket
import sys
import threading
import traceback
import urllib.request
from contextlib import closing
from pathlib import Path
from wsgiref.simple_server import WSGIRequestHandler, make_server

import webview
from django.contrib.staticfiles.handlers import StaticFilesHandler
from django.core.management import call_command
from django.core.wsgi import get_wsgi_application


APP_TITLE = "\u0416\u0443\u0440\u043d\u0430\u043b \u041c\u041f\u0422"
HOST = "127.0.0.1"


def get_runtime_dir():
    return Path(os.getenv("MPT_RUNTIME_DIR", Path(os.getenv("LOCALAPPDATA", Path.cwd())) / "MPT Journal"))


LOG_FILE = get_runtime_dir() / "desktop.log"


class QuietRequestHandler(WSGIRequestHandler):
    def log_message(self, format, *args):
        return


def find_free_port():
    with closing(socket.socket(socket.AF_INET, socket.SOCK_STREAM)) as sock:
        sock.bind((HOST, 0))
        return sock.getsockname()[1]


def configure_environment():
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
    os.environ.setdefault("DJANGO_DEBUG", "1")
    os.environ.setdefault("DJANGO_ALLOWED_HOSTS", "127.0.0.1,localhost,*")
    os.environ.setdefault("DB_ENGINE", "postgres")
    os.environ.setdefault("POSTGRES_DB", "performance_db")
    os.environ.setdefault("POSTGRES_USER", "postgres")
    os.environ.setdefault("POSTGRES_PASSWORD", "1")
    os.environ.setdefault("POSTGRES_HOST", "localhost")
    os.environ.setdefault("POSTGRES_PORT", "5432")


def configure_logging():
    LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
    logging.basicConfig(
        filename=LOG_FILE,
        level=logging.DEBUG,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )
    logging.getLogger(__name__).info("Desktop launcher started")
    logging.getLogger(__name__).info("Frozen=%s MEIPASS=%s", getattr(sys, "frozen", False), getattr(sys, "_MEIPASS", None))


def seed_runtime_media():
    if not getattr(sys, "frozen", False):
        return
    from django.conf import settings

    bundled_media = Path(getattr(sys, "_MEIPASS", "")) / "media"
    target_media = Path(settings.MEDIA_ROOT)
    if not bundled_media.exists() or target_media.exists():
        return
    shutil.copytree(bundled_media, target_media)


class LoggedExceptionMiddleware:
    def __init__(self, application):
        self.application = application

    def __call__(self, environ, start_response):
        try:
            return self.application(environ, start_response)
        except Exception:
            logging.getLogger(__name__).exception("Unhandled WSGI exception")
            body = (
                "A server error occurred.\n\n"
                f"Log file: {LOG_FILE}\n\n"
                f"{traceback.format_exc()}"
            ).encode("utf-8", errors="replace")
            start_response(
                "500 Internal Server Error",
                [("Content-Type", "text/plain; charset=utf-8"), ("Content-Length", str(len(body)))],
            )
            return [body]


def build_application():
    application = get_wsgi_application()
    return LoggedExceptionMiddleware(StaticFilesHandler(application))


def run_migrations():
    call_command("migrate", interactive=False, verbosity=0)


def start_server(application, port):
    server = make_server(HOST, port, application, handler_class=QuietRequestHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    return server


def run_smoke_check(port):
    with urllib.request.urlopen(f"http://{HOST}:{port}/", timeout=10) as response:
        content = response.read(500).decode("utf-8", errors="replace")
        print(f"HTTP {response.status}")
        print(content)


def main():
    configure_environment()
    configure_logging()
    try:
        seed_runtime_media()
        application = build_application()
        run_migrations()
        port = find_free_port()
        server = start_server(application, port)
    except Exception:
        logging.getLogger(__name__).exception("Failed to start desktop application")
        raise
    try:
        if os.getenv("MPT_DESKTOP_SMOKE") == "1":
            run_smoke_check(port)
            return
        webview.create_window(
            APP_TITLE,
            f"http://{HOST}:{port}/",
            width=1280,
            height=820,
            min_size=(1024, 680),
        )
        webview.start()
    finally:
        server.shutdown()
        server.server_close()


if __name__ == "__main__":
    main()
