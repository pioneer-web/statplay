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
from sports.services.competition_scope import (
    is_target_competition,
)


def current_model():
    return (
        ModelVersion.objects
        .filter(
            name="StatPlay Core",
            version="1.1.0",
        )
        .order_by("-id")
        .first()
    )


def prepare_prediction(prediction):
    odd = best_odd(prediction)

    prediction.best_odd = None
    prediction.best_bookmaker = None
    prediction.edge = None

    if odd:
        prediction.best_odd = (
            odd["odd"]
        )
        prediction.best_bookmaker = (
            odd["bookmaker"]
        )
        prediction.edge = (
            odd["edge"]
        )

    return prediction


@login_required
def dashboard(request):
    today = timezone.localdate()

    tomorrow = (
        today
        + timedelta(days=1)
    )

    model = current_model()

    queryset = (
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
            probability__gte=60,
            result="pending",
            event__starts_at__gte=timezone.now(),
            event__starts_at__date__gte=today,
            event__starts_at__date__lte=tomorrow,
        )
        .order_by(
            "event__starts_at",
            "-probability",
        )
    )

    if model:
        queryset = queryset.filter(
            model_version=model
        )

    today_predictions = []
    tomorrow_predictions = []

    for prediction in queryset:
        competition = (
            prediction.event.competition
        )

        if not is_target_competition(
            competition.name,
            competition.country,
        ):
            continue

        prepare_prediction(
            prediction
        )

        local_date = (
            timezone.localtime(
                prediction.event.starts_at
            ).date()
        )

        if local_date == today:
            today_predictions.append(
                prediction
            )

        elif local_date == tomorrow:
            tomorrow_predictions.append(
                prediction
            )

    return render(
        request,
        "core/dashboard.html",
        {
            "today": today,
            "tomorrow": tomorrow,
            "today_predictions": (
                today_predictions
            ),
            "tomorrow_predictions": (
                tomorrow_predictions
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
        probability__gte=60,
    )

    explanation = (
        build_explanation(
            prediction
        )
    )

    return render(
        request,
        "core/prediction_detail.html",
        {
            "prediction": prediction,
            "explanation": explanation,
        },
    )
