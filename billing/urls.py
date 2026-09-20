from django.urls import path

from billing.views import account


app_name = "billing"


urlpatterns = [
    path(
        "",
        account,
        name="account",
    ),
]
