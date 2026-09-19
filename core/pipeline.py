from datetime import date

from odds.services.sofascore_odds import (
    save_event_odds,
)
from predictions.generator import (
    generate_predictions,
)
from predictions.settlement import (
    settle_pending,
)
from sports.models import Event
from sports.providers.sofascore import (
    SofaScoreProvider,
)
from sports.services.competition_scope import (
    is_target_competition,
)
from sports.services.history_sync import (
    ensure_history,
)


def scoped_events(target_date):
    queryset = (
        Event.objects
        .filter(
            starts_at__date=target_date,
            status="scheduled",
        )
        .exclude(external_id="")
        .select_related(
            "home_team",
            "away_team",
            "competition",
        )
        .order_by("starts_at")
    )

    return [
        event
        for event in queryset
        if is_target_competition(
            event.competition.name,
            event.competition.country,
        )
    ]


def run_pipeline(target_date=None):
    target_date = (
        target_date
        or date.today()
    )

    if isinstance(target_date, str):
        target_date = date.fromisoformat(
            target_date
        )

    provider = SofaScoreProvider()

    provider.sync_date(
        target_date.isoformat()
    )

    events = scoped_events(
        target_date
    )

    history = ensure_history(
        events,
        provider,
        min_matches=10,
        fetch_matches=15,
        pages=3,
    )

    predictions = (
        generate_predictions(events)
    )

    odds_events = 0
    odds_offers = 0
    snapshots = 0

    for event in events:
        try:
            payload = (
                provider.get_odds(
                    event.external_id
                )
                or {}
            )

            result = save_event_odds(
                event,
                payload,
            )

        except Exception:
            continue

        if result["offers"]:
            odds_events += 1

        odds_offers += (
            result["offers"]
        )

        snapshots += (
            result["snapshots"]
        )

    settlement = settle_pending(
        provider
    )

    return {
        "date": target_date.isoformat(),
        "events": len(events),
        "history": history,
        "predictions": predictions,
        "odds": {
            "events": odds_events,
            "offers": odds_offers,
            "snapshots": snapshots,
        },
        "settlement": settlement,
    }
