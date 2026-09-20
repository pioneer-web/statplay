from django.utils import timezone

from predictions.models import Prediction
from sports.models import TeamMatchStats
from sports.services.statistics import (
    save_event_statistics,
)


def prediction_result(
    prediction,
):
    event = prediction.event
    code = prediction.market.code

    if (
        event.home_score is None
        or event.away_score is None
    ):
        return None

    home = event.home_score
    away = event.away_score

    if code == "home_win":
        return home > away

    if code == "draw":
        return home == away

    if code == "away_win":
        return away > home

    if code == "double_home_draw":
        return home >= away

    if code == "double_away_draw":
        return away >= home

    if code == "double_home_away":
        return home != away

    if code == "btts_yes":
        return home > 0 and away > 0

    if code == "btts_no":
        return not (
            home > 0
            and away > 0
        )

    if code.startswith(
        "goals_"
    ):
        total = home + away

        line = float(
            code.rsplit(
                "_",
                2,
            )[-2]
            + "."
            + code.rsplit(
                "_",
                1,
            )[-1]
        )

        if "_over_" in code:
            return total > line

        if "_under_" in code:
            return total < line

    stats = list(
        TeamMatchStats.objects
        .filter(event=event)
    )

    if len(stats) != 2:
        return None

    if code.startswith(
        "corners_"
    ):
        values = [
            item.corners
            for item in stats
        ]

    elif code.startswith(
        "cards_"
    ):
        values = [
            item.cards
            for item in stats
        ]

    else:
        return None

    if any(
        value is None
        for value in values
    ):
        return None

    total = sum(values)

    pieces = (
        code.split("_")
    )

    line = float(
        pieces[-2]
        + "."
        + pieces[-1]
    )

    if "_over_" in code:
        return total > line

    if "_under_" in code:
        return total < line

    return None


def settle_pending(provider):
    pending = (
        Prediction.objects
        .filter(result="pending")
        .exclude(event__external_id="")
        .select_related(
            "event",
            "event__competition",
            "market",
        )
    )

    settled = 0
    voided = 0
    waiting = 0

    event_cache = {}

    for prediction in pending:
        event = prediction.event

        if event.id not in event_cache:
            raw_payload = provider._get(
                f"event/{event.external_id}"
            )

            if raw_payload:
                raw = (
                    raw_payload.get(
                        "event"
                    )
                    or raw_payload
                )

                event, _ = (
                    provider._save_event(
                        raw,
                        event.competition.sport,
                    )
                )

            event_cache[
                prediction.event_id
            ] = event

        event = event_cache[
            prediction.event_id
        ]

        if event.status == "cancelled":
            prediction.result = "void"
            prediction.settled_at = (
                timezone.now()
            )
            prediction.save(
                update_fields=[
                    "result",
                    "settled_at",
                ]
            )

            voided += 1
            continue

        if event.status != "finished":
            waiting += 1
            continue

        if (
            prediction.market.code.startswith(
                "cards_"
            )
            or prediction.market.code.startswith(
                "corners_"
            )
        ):
            if (
                TeamMatchStats.objects
                .filter(event=event)
                .count()
                != 2
            ):
                payload = (
                    provider.get_statistics(
                        event.external_id
                    )
                )

                save_event_statistics(
                    event,
                    payload,
                )

        outcome = prediction_result(
            prediction
        )

        if outcome is None:
            waiting += 1
            continue

        prediction.result = (
            "win"
            if outcome
            else "loss"
        )

        prediction.settled_at = (
            timezone.now()
        )

        prediction.save(
            update_fields=[
                "result",
                "settled_at",
            ]
        )

        settled += 1

    return {
        "settled": settled,
        "voided": voided,
        "waiting": waiting,
    }
