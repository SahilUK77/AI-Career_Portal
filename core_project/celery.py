import os

from celery import Celery
from celery.schedules import crontab

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "core_project.settings")

app = Celery("core_project")
app.config_from_object("django.conf:settings", namespace="CELERY")
app.autodiscover_tasks()

# Periodic beat schedule for nightly data refresh
app.conf.beat_schedule = {
    "refresh-opportunities-nightly": {
        # Refreshes opportunities for all active profiles at 2 AM IST daily
        "task": "career_app.tasks.nightly_refresh_all_profiles",
        "schedule": crontab(hour=2, minute=0),
    },
}
