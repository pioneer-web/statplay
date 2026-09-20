from django.urls import path

from accounts.views import signup


urlpatterns = [
    path(
        "cadastro/",
        signup,
        name="signup",
    ),
]
