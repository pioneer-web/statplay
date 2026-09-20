from datetime import timedelta

from django.contrib.auth.decorators import (
    login_required,
)
from django.shortcuts import (
    get_object_or_404,
    render,
)
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


CATEGORY_LABEL = {
    "result":
        "Resultado",

    "double_chance":
        "Dupla chance",

    "goals":
        "Gols",

    "corners":
        "Escanteios",

    "cards":
        "Cartões",
}


def current_model():
    return (
        ModelVersion.objects
        .filter(
            name="StatPlay Core",
            version=MODEL_VERSION,
        )
        .order_by(
            "-id"
        )
        .first()
    )


def decorate(prediction):
    price = best_odd(
        prediction
    )

    prediction.best_odd = None
    prediction.market_probability = None
    prediction.edge = None

    if price:
        prediction.best_odd = (
            price["odd"]
        )

        prediction.edge = (
            price["edge"]
        )

        prediction.market_probability = (
            price[
                "market_probability"
            ]
            or price[
                "raw_implied"
            ]
        )

    return prediction


def should_show(
    prediction,
    mode,
):
    if mode == "60":
        return (
            float(
                prediction.probability
            )
            >= 60
        )

    if mode == "value":
        return (
            prediction.edge
            is not None
            and prediction.edge
            >= VALUE_EDGE
        )

    return True


def group_markets(
    predictions,
):
    grouped = {}

    for prediction in predictions:
        category = (
            prediction.market.category
        )

        grouped.setdefault(
            category,
            [],
        ).append(
            prediction
        )

    output = []

    for category, items in sorted(
        grouped.items(),
        key=lambda item:
            CATEGORY_ORDER.get(
                item[0],
                99,
            ),
    ):
        output.append({
            "category":
                category,

            "label":
                CATEGORY_LABEL.get(
                    category,
                    category.title(),
                ),

            "items":
                items,
        })

    return output


def group_games(
    predictions,
    mode,
):
    games = {}

    for prediction in predictions:
        competition = (
            prediction.event.competition
        )

        if not is_target_competition(
            competition.name,
            competition.country,
        ):
            continue

        decorate(
            prediction
        )

        if not should_show(
            prediction,
            mode,
        ):
            continue

        event_id = (
            prediction.event_id
        )

        if event_id not in games:
            games[event_id] = {
                "event":
                    prediction.event,

                "predictions":
                    [],
            }

        games[event_id][
            "predictions"
        ].append(
            prediction
        )

    output = []

    for game in games.values():
        game["groups"] = (
            group_markets(
                game[
                    "predictions"
                ]
            )
        )

        output.append(
            game
        )

    output.sort(
        key=lambda game:
            game["event"].starts_at
    )

    return output


@login_required
def dashboard(request):
    today = (
        timezone.localdate()
    )

    tomorrow = (
        today
        + timedelta(days=1)
    )

    mode = request.GET.get(
        "f",
        "all",
    )

    if mode not in (
        "all",
        "60",
        "value",
    ):
        mode = "all"

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
                "model_version",
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

    today_predictions = []
    tomorrow_predictions = []

    for prediction in predictions:
        day = (
            timezone.localtime(
                prediction.event.starts_at
            ).date()
        )

        if day == today:
            today_predictions.append(
                prediction
            )

        elif day == tomorrow:
            tomorrow_predictions.append(
                prediction
            )

    return render(
        request,
        "core/dashboard.html",
        {
            "today":
                today,

            "tomorrow":
                tomorrow,

            "mode":
                mode,

            "today_games":
                group_games(
                    today_predictions,
                    mode,
                ),

            "tomorrow_games":
                group_games(
                    tomorrow_predictions,
                    mode,
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
        decorate(
            prediction
        )

    return render(
        request,
        "core/event_detail.html",
        {
            "event":
                event,

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
    )

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
