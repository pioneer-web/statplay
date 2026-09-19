from celery import shared_task

from sports.providers.sofascore import SofaScoreProvider


@shared_task
def refresh_upcoming_events():
    provider = SofaScoreProvider()
    return provider.sync_upcoming(days=3)
