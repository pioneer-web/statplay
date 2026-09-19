from django.db import models
from sports.models import Event
class Bookmaker(models.Model):
    name=models.CharField(max_length=100,unique=True); slug=models.SlugField(unique=True); active=models.BooleanField(default=True); website=models.URLField(blank=True)
    def __str__(self): return self.name
class Market(models.Model):
    code=models.CharField(max_length=80,unique=True); name=models.CharField(max_length=120); category=models.CharField(max_length=50)
    def __str__(self): return self.name
class OddSnapshot(models.Model):
    event=models.ForeignKey(Event,on_delete=models.CASCADE,related_name='odds'); bookmaker=models.ForeignKey(Bookmaker,on_delete=models.CASCADE); market=models.ForeignKey(Market,on_delete=models.CASCADE)
    selection=models.CharField(max_length=120); line=models.DecimalField(max_digits=8,decimal_places=2,null=True,blank=True); odd=models.DecimalField(max_digits=8,decimal_places=3); captured_at=models.DateTimeField(auto_now_add=True,db_index=True)
    class Meta: indexes=[models.Index(fields=['event','market','selection','-captured_at'])]
