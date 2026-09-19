from django.contrib.auth.decorators import login_required
from django.shortcuts import render
from django.utils import timezone

from odds.models import OddSnapshot
from predictions.models import Prediction


@login_required
def dashboard(request):
    band = request.GET.get("band", "70")
    mins = {"70": 70, "80": 80, "90": 90}
    min_p = mins.get(band, 70)

    predictions = list(
        Prediction.objects.select_related(
            "event",
            "event__home_team",
            "event__away_team",
            "event__competition",
            "market",
        )
        .filter(
            event__starts_at__gte=timezone.now(),
            probability__gte=min_p,
        )
        .order_by("-probability", "event__starts_at")[:50]
    )

    for prediction in predictions:
        odds = OddSnapshot.objects.filter(
            event=prediction.event,
            market=prediction.market,
            selection=prediction.selection,
        )

        if prediction.line is None:
            odds = odds.filter(line__isnull=True)
        else:
            odds = odds.filter(line=prediction.line)

        best = odds.select_related("bookmaker").order_by("-odd").first()

        prediction.best_odd = None
        prediction.best_bookmaker = None
        prediction.implied_probability = None
        prediction.edge = None

        if best:
            odd = float(best.odd)
            implied = 100 / odd

            prediction.best_odd = best.odd
            prediction.best_bookmaker = best.bookmaker.name
            prediction.implied_probability = round(implied, 1)
            prediction.edge = round(float(prediction.probability) - implied, 1)

    return render(
        request,
        "core/dashboard.html",
        {
            "predictions": predictions,
            "band": band,
            "min_p": min_p,
        },
    )
