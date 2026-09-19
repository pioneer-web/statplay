from django.contrib import admin
from .models import ModelVersion,Prediction
admin.site.register([ModelVersion,Prediction])
