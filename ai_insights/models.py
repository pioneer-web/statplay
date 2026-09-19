from django.db import models
from predictions.models import Prediction
class AIInsight(models.Model):
    prediction=models.OneToOneField(Prediction,on_delete=models.CASCADE,related_name='ai_insight'); provider=models.CharField(max_length=50,blank=True); summary=models.TextField(); factors=models.JSONField(default=dict); generated_at=models.DateTimeField(auto_now_add=True)
