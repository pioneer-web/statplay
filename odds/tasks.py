from celery import shared_task

from odds.providers.the_odds_api import TheOddsApiProvider


@shared_task
def refresh_odds():

    provider = TheOddsApiProvider()

    return provider.sync()
