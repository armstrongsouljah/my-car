import os

from celery import Celery

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

app = Celery("my_car")
app.config_from_object("django.conf:settings", namespace="CELERY")
app.autodiscover_tasks()

# Root-level tasks.py (matches the nivo-api layout).
app.autodiscover_tasks(["tasks"], related_name=None)
