from django.urls import path

from .views import (
    dashboard,
    event_detail,
    prediction_detail,
)


urlpatterns = [
    path(
        "",
        dashboard,
        name="dashboard",
    ),

    path(
        "jogo/<int:event_id>/",
        event_detail,
        name="event_detail",
    ),

    path(
        "previsao/<int:prediction_id>/",
        prediction_detail,
        name="prediction_detail",
    ),
]
