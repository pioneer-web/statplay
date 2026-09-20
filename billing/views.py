from django.contrib.auth.decorators import (
    login_required,
)
from django.shortcuts import render

from billing.models import (
    Plan,
    Subscription,
)


@login_required
def account(request):
    subscription = (
        Subscription.objects
        .select_related("plan")
        .filter(
            user=request.user
        )
        .first()
    )

    plans = (
        Plan.objects
        .all()
        .order_by(
            "monthly_price",
            "name",
        )
    )

    selected_plan_code = (
        request.GET.get(
            "plano"
        )
        or ""
    )

    return render(
        request,
        "billing/account.html",
        {
            "subscription":
                subscription,

            "plans":
                plans,

            "selected_plan_code":
                selected_plan_code,
        },
    )
