#!/bin/sh
set -e

python manage.py migrate --noinput

python manage.py shell <<'PY'
import os
from django.contrib.auth import get_user_model
from django.db import IntegrityError

User = get_user_model()

email = os.getenv("SUPERUSER_EMAIL")
password = os.getenv("SUPERUSER_PASSWORD")

if email and password:
    try:
        if not User.objects.filter(email=email).exists():
            User.objects.create_superuser(
                email=email,
                password=password,
                name="StatPlay Admin",
            )
            print("Superusuário criado.")
        else:
            print("Superusuário já existe.")
    except IntegrityError:
        print("Superusuário já foi criado por outro container.")
PY

exec "$@"
