from datetime import timedelta

from celery import shared_task
from django.utils import timezone

from core.pipeline import (
    run_pipeline,
    scoped_events,
    sync_lineups,
)
from predictions.generator import (
    generate_predictions,
)
from predictions.settlement import (
    settle_pending,
)
from sports.providers.sofascore import (
    SofaScoreProvider,
)


@shared_task
def run_statplay_pipeline():
    today = timezone.localdate()

    tomorrow = (
        today
        + timedelta(days=1)
    )

    return [
        run_pipeline(today),
        run_pipeline(tomorrow),
    ]


@shared_task
def refresh_statplay_lineups():
    today = timezone.localdate()

    tomorrow = (
        today
        + timedelta(days=1)
    )

    provider = (
        SofaScoreProvider()
    )

    results = []

    for target in (
        today,
        tomorrow,
    ):
        events = scoped_events(
            target
        )

        lineups = sync_lineups(
            events,
            provider,
        )

        predictions = (
            generate_predictions(
                events
            )
        )

        results.append({
            "date":
                target.isoformat(),
            "lineups":
                lineups,
            "predictions":
                predictions,
        })

    return results


@shared_task
def settle_statplay_predictions():
    provider = (
        SofaScoreProvider()
    )

    return settle_pending(
        provider
    )
