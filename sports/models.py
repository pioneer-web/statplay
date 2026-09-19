from django.db import models
class Sport(models.Model):
    name=models.CharField(max_length=80); slug=models.SlugField(unique=True); active=models.BooleanField(default=True)
    def __str__(self): return self.name
class Competition(models.Model):
    sport=models.ForeignKey(Sport,on_delete=models.CASCADE); name=models.CharField(max_length=120); country=models.CharField(max_length=80,blank=True); external_id=models.CharField(max_length=120,blank=True)
    def __str__(self): return self.name
class Team(models.Model):
    sport=models.ForeignKey(Sport,on_delete=models.CASCADE); name=models.CharField(max_length=120); external_id=models.CharField(max_length=120,blank=True)
    def __str__(self): return self.name
class Event(models.Model):
    STATUS=[('scheduled','Agendado'),('live','Ao vivo'),('finished','Finalizado'),('cancelled','Cancelado')]
    competition=models.ForeignKey(Competition,on_delete=models.CASCADE); home_team=models.ForeignKey(Team,on_delete=models.CASCADE,related_name='home_events'); away_team=models.ForeignKey(Team,on_delete=models.CASCADE,related_name='away_events')
    starts_at=models.DateTimeField(db_index=True); status=models.CharField(max_length=20,choices=STATUS,default='scheduled'); external_id=models.CharField(max_length=120,blank=True,db_index=True)
    home_score=models.PositiveSmallIntegerField(null=True,blank=True); away_score=models.PositiveSmallIntegerField(null=True,blank=True)
    created_at=models.DateTimeField(auto_now_add=True); updated_at=models.DateTimeField(auto_now=True)
    def __str__(self): return f'{self.home_team} x {self.away_team}'
class TeamMatchStats(models.Model):
    event=models.ForeignKey(Event,on_delete=models.CASCADE,related_name='team_stats'); team=models.ForeignKey(Team,on_delete=models.CASCADE)
    corners=models.PositiveSmallIntegerField(default=0); shots=models.PositiveSmallIntegerField(default=0); shots_on_target=models.PositiveSmallIntegerField(default=0); possession=models.DecimalField(max_digits=5,decimal_places=2,null=True,blank=True); cards=models.PositiveSmallIntegerField(default=0); xg=models.DecimalField(max_digits=6,decimal_places=3,null=True,blank=True)
