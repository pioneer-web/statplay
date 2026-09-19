from django.contrib import admin
from .models import AlertPreference,AlertDelivery
admin.site.register([AlertPreference,AlertDelivery])
