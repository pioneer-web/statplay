from django.db import models
from sports.models import Event
from odds.models import Market
class ModelVersion(models.Model):
    name=models.CharField(max_length=100); version=models.CharField(max_length=40); algorithm=models.CharField(max_length=80); trained_at=models.DateTimeField(null=True,blank=True); active=models.BooleanField(default=True)
    def __str__(self): return f'{self.name} {self.version}'
class Prediction(models.Model):
    event=models.ForeignKey(Event,on_delete=models.CASCADE,related_name='predictions'); market=models.ForeignKey(Market,on_delete=models.PROTECT); model_version=models.ForeignKey(ModelVersion,on_delete=models.PROTECT)
    selection=models.CharField(max_length=120); line=models.DecimalField(max_digits=8,decimal_places=2,null=True,blank=True); probability=models.DecimalField(max_digits=5,decimal_places=2,db_index=True); confidence=models.DecimalField(max_digits=5,decimal_places=2,default=0)
    fair_odd=models.DecimalField(max_digits=8,decimal_places=3,null=True,blank=True); created_at=models.DateTimeField(auto_now_add=True,db_index=True); locked=models.BooleanField(default=True)
    result=models.CharField(max_length=10,choices=[('pending','Pendente'),('win','Acerto'),('loss','Erro'),('void','Anulada')],default='pending'); settled_at=models.DateTimeField(null=True,blank=True)
    class Meta: indexes=[models.Index(fields=['-probability','created_at'])]
    def save(self,*args,**kwargs):
        if self.probability and not self.fair_odd: self.fair_odd=round(100/float(self.probability),3)
        super().save(*args,**kwargs)
