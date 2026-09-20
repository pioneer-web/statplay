from django.contrib.auth import login
from django.shortcuts import (
    redirect,
    render,
)

from accounts.forms import SignupForm


def signup(request):
    selected_plan = (
        request.POST.get("plan")
        or request.GET.get("plan")
        or ""
    )

    if request.user.is_authenticated:
        if selected_plan:
            return redirect(
                f"/conta/?plano={selected_plan}"
            )

        return redirect("/app/")

    if request.method == "POST":
        form = SignupForm(
            request.POST
        )

        if form.is_valid():
            user = form.save()

            login(
                request,
                user,
            )

            if selected_plan:
                return redirect(
                    f"/conta/?plano={selected_plan}"
                )

            return redirect("/app/")

    else:
        form = SignupForm()

    return render(
        request,
        "registration/signup.html",
        {
            "form": form,
            "selected_plan":
                selected_plan,
        },
    )
