from django.conf import settings
from django.db import models
class AlertPreference(models.Model):
    user=models.OneToOneField(settings.AUTH_USER_MODEL,on_delete=models.CASCADE); min_probability=models.DecimalField(max_digits=5,decimal_places=2,default=70); telegram_enabled=models.BooleanField(default=True); whatsapp_enabled=models.BooleanField(default=False); telegram_chat_id=models.CharField(max_length=100,blank=True); whatsapp_number=models.CharField(max_length=30,blank=True)
class AlertDelivery(models.Model):
    user=models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.CASCADE); channel=models.CharField(max_length=20); payload=models.JSONField(default=dict); status=models.CharField(max_length=20,default='pending'); created_at=models.DateTimeField(auto_now_add=True); sent_at=models.DateTimeField(null=True,blank=True)
