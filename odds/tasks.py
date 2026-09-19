from celery import shared_task
@shared_task
def refresh_odds():
    # Adaptador para agregadores/feed de odds.
    return {'status':'odds_provider_not_configured'}
