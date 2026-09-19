from django.contrib import admin
from .models import Bookmaker,Market,OddSnapshot
admin.site.register([Bookmaker,Market,OddSnapshot])
