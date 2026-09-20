from django.contrib import admin
from django.contrib.auth import (
    views as auth_views,
)
from django.urls import (
    include,
    path,
)

from core.public_views import landing


urlpatterns = [

    path(
        "admin/",
        admin.site.urls,
    ),

    path(
        "",
        landing,
        name="landing",
    ),

    path(
        "",
        include(
            "accounts.urls"
        ),
    ),

    path(
        "login/",
        auth_views.LoginView.as_view(
            template_name=
                "registration/login.html"
        ),
        name="login",
    ),

    path(
        "logout/",
        auth_views.LogoutView.as_view(),
        name="logout",
    ),

    path(
        "conta/",
        include(
            "billing.urls"
        ),
    ),

    path(
        "app/",
        include(
            "core.urls"
        ),
    ),
]
