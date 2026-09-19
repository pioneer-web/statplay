from django.contrib import admin
from .models import Sport,Competition,Team,Event,TeamMatchStats
admin.site.register([Sport,Competition,Team,Event,TeamMatchStats])
