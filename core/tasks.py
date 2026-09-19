from datetime import timedelta

from celery import shared_task
from django.utils import timezone

from core.pipeline import run_pipeline
from predictions.settlement import settle_pending
from sports.providers.sofascore import SofaScoreProvider


@shared_task
def run_statplay_pipeline():
    today = timezone.localdate()
    tomorrow = today + timedelta(days=1)

    return [
        run_pipeline(today),
        run_pipeline(tomorrow),
    ]


@shared_task
def settle_statplay_predictions():
    provider = SofaScoreProvider()

    return settle_pending(provider)
