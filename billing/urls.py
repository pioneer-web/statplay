from django.urls import path

from billing.views import account


app_name = "billing"


urlpatterns = [
    path(
        "conta/",
        account,
        name="account",
    ),
]
