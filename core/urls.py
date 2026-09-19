from django.urls import path

from .views import (
    dashboard,
    prediction_detail,
)


urlpatterns = [
    path(
        "",
        dashboard,
        name="dashboard",
    ),
    path(
        "previsao/<int:prediction_id>/",
        prediction_detail,
        name="prediction_detail",
    ),
]
