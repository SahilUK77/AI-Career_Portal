import os
from celery import Celery
from celery.schedules import crontab

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core_project.settings')

app = Celery('core_project')
app.config_from_object('django.conf:settings', namespace='CELERY')
app.autodiscover_tasks()

# Scheduled periodic ingestion tasks
app.conf.beat_schedule = {
    'scrape-govt-schemes-nightly': {
        'task': 'career_app.tasks.run_govt_schemes_scraper',
        'schedule': crontab(hour=2, minute=0),  # Runs daily at 2:00 AM IST
    },
    'scrape-courses-nightly': {
        'task': 'career_app.tasks.run_courses_scraper',
        'schedule': crontab(hour=3, minute=0),  # Runs daily at 3:00 AM IST
    },
}