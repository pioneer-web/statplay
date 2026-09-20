from django.shortcuts import render

from billing.models import Plan


def landing(request):
    plans = (
        Plan.objects
        .all()
        .order_by(
            "monthly_price",
            "name",
        )
    )

    return render(
        request,
        "public/landing.html",
        {
            "plans": plans,
        },
    )
