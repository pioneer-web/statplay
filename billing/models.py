from django.conf import settings
from django.db import models
class Plan(models.Model):
    code=models.CharField(max_length=20,unique=True,choices=[('PRO','PRO'),('PRO_PLUS','PRO+')])
    name=models.CharField(max_length=50); monthly_price=models.DecimalField(max_digits=8,decimal_places=2)
    min_probability=models.DecimalField(max_digits=5,decimal_places=2,default=70)
    whatsapp_alerts=models.BooleanField(default=False); telegram_alerts=models.BooleanField(default=True); ai_explanations=models.BooleanField(default=True)
    def __str__(self): return self.name
class Subscription(models.Model):
    user=models.OneToOneField(settings.AUTH_USER_MODEL,on_delete=models.CASCADE)
    plan=models.ForeignKey(Plan,on_delete=models.PROTECT)
    status=models.CharField(max_length=20,default='active'); started_at=models.DateTimeField(auto_now_add=True); expires_at=models.DateTimeField(null=True,blank=True)
