from datetime import timedelta

from django.contrib.auth.decorators import login_required
from django.http import Http404
from django.shortcuts import get_object_or_404, render
from django.utils import timezone

from core.services.prediction_explanation import (
    best_odd,
    build_explanation,
)
from predictions.models import (
    ModelVersion,
    Prediction,
)
from sports.models import Event
from sports.services.competition_scope import (
    is_target_competition,
)


MODEL_VERSION = "2.0.0"
VALUE_EDGE = 3.0


CATEGORY_ORDER = {
    "result": 1,
    "double_chance": 2,
    "goals": 3,
    "corners": 4,
    "cards": 5,
}


CATEGORY_LABELS = {
    "result": "Resultado",
    "double_chance": "Dupla chance",
    "goals": "Gols",
    "corners": "Escanteios",
    "cards": "Cartões",
}


def current_model():
    return (
        ModelVersion.objects
        .filter(
            name="StatPlay Core",
            version=MODEL_VERSION,
        )
        .order_by("-id")
        .first()
    )


def decorate_prediction(prediction):
    price = best_odd(prediction)

    prediction.best_odd = None
    prediction.edge = None
    prediction.market_probability = None

    if price:
        prediction.best_odd = price["odd"]
        prediction.edge = price["edge"]

        prediction.market_probability = (
            price["market_probability"]
            or price["raw_implied"]
        )

    return prediction


def competition_allowed(event):
    return is_target_competition(
        event.competition.name,
        event.competition.country,
    )


def event_is_visible(event):
    today = timezone.localdate()
    tomorrow = today + timedelta(days=1)

    event_day = timezone.localtime(
        event.starts_at
    ).date()

    return (
        event_day in (today, tomorrow)
        and competition_allowed(event)
    )


def group_markets(predictions):
    groups = {}

    for prediction in predictions:
        category = prediction.market.category

        groups.setdefault(
            category,
            [],
        ).append(prediction)

    result = []

    for category, items in sorted(
        groups.items(),
        key=lambda item: CATEGORY_ORDER.get(
            item[0],
            99,
        ),
    ):
        result.append(
            {
                "category": category,
                "label": CATEGORY_LABELS.get(
                    category,
                    category.title(),
                ),
                "items": items,
            }
        )

    return result


def game_cards(predictions, filter_mode):
    games = {}

    for prediction in predictions:
        event = prediction.event

        if not competition_allowed(event):
            continue

        games.setdefault(
            event.id,
            {
                "event": event,
                "predictions": [],
            },
        )

        games[event.id][
            "predictions"
        ].append(prediction)

    result = []

    for game in games.values():
        rows = game["predictions"]

        above_60 = [
            p
            for p in rows
            if float(p.probability) >= 60
        ]

        value_rows = []

        if filter_mode == "value":
            for prediction in rows:
                decorate_prediction(
                    prediction
                )

                if (
                    prediction.edge is not None
                    and prediction.edge >= VALUE_EDGE
                ):
                    value_rows.append(
                        prediction
                    )

            if not value_rows:
                continue

        if (
            filter_mode == "60"
            and not above_60
        ):
            continue

        game["markets_count"] = len(rows)
        game["above_60_count"] = len(
            above_60
        )
        game["value_count"] = len(
            value_rows
        )

        game["highest_probability"] = max(
            float(p.probability)
            for p in rows
        )

        result.append(game)

    result.sort(
        key=lambda item:
            item["event"].starts_at
    )

    return result


@login_required
def dashboard(request):
    today = timezone.localdate()
    tomorrow = (
        today
        + timedelta(days=1)
    )

    filter_mode = request.GET.get(
        "f",
        "all",
    )

    if filter_mode not in (
        "all",
        "60",
        "value",
    ):
        filter_mode = "all"

    model = current_model()

    if not model:
        predictions = (
            Prediction.objects.none()
        )

    else:
        predictions = (
            Prediction.objects
            .select_related(
                "event",
                "event__home_team",
                "event__away_team",
                "event__competition",
                "market",
            )
            .filter(
                model_version=model,
                is_current=True,
                result="pending",
                event__starts_at__gte=
                    timezone.now(),
                event__starts_at__date__gte=
                    today,
                event__starts_at__date__lte=
                    tomorrow,
            )
            .order_by(
                "event__starts_at",
                "market__category",
                "-probability",
            )
        )

    today_rows = []
    tomorrow_rows = []

    for prediction in predictions:
        event_day = (
            timezone.localtime(
                prediction.event.starts_at
            ).date()
        )

        if event_day == today:
            today_rows.append(
                prediction
            )

        elif event_day == tomorrow:
            tomorrow_rows.append(
                prediction
            )

    return render(
        request,
        "core/dashboard.html",
        {
            "today": today,
            "tomorrow": tomorrow,
            "filter_mode":
                filter_mode,

            "today_games":
                game_cards(
                    today_rows,
                    filter_mode,
                ),

            "tomorrow_games":
                game_cards(
                    tomorrow_rows,
                    filter_mode,
                ),

            "value_edge":
                VALUE_EDGE,
        },
    )


@login_required
def event_detail(
    request,
    event_id,
):
    event = get_object_or_404(
        Event.objects
        .select_related(
            "home_team",
            "away_team",
            "competition",
        ),
        pk=event_id,
    )

    if not event_is_visible(event):
        raise Http404

    model = current_model()

    predictions = []

    if model:
        predictions = list(
            Prediction.objects
            .select_related(
                "market",
                "event",
                "event__home_team",
                "event__away_team",
                "event__competition",
            )
            .filter(
                event=event,
                model_version=model,
                is_current=True,
            )
            .order_by(
                "market__category",
                "-probability",
            )
        )

    for prediction in predictions:
        decorate_prediction(
            prediction
        )

    return render(
        request,
        "core/event_detail.html",
        {
            "event": event,
            "groups":
                group_markets(
                    predictions
                ),
        },
    )


@login_required
def prediction_detail(
    request,
    prediction_id,
):
    model = current_model()

    if not model:
        raise Http404

    prediction = get_object_or_404(
        Prediction.objects
        .select_related(
            "event",
            "event__home_team",
            "event__away_team",
            "event__competition",
            "market",
            "model_version",
        ),
        pk=prediction_id,
        model_version=model,
        is_current=True,
    )

    if not event_is_visible(
        prediction.event
    ):
        raise Http404

    return render(
        request,
        "core/prediction_detail.html",
        {
            "prediction":
                prediction,

            "explanation":
                build_explanation(
                    prediction
                ),
        },
    )
