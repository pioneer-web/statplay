from django.contrib.auth.decorators import login_required
from django.shortcuts import render
from django.utils import timezone
from predictions.models import Prediction
@login_required
def dashboard(request):
    band=request.GET.get('band','70')
    mins={'70':70,'80':80,'90':90}; min_p=mins.get(band,70)
    qs=Prediction.objects.select_related('event','event__home_team','event__away_team','market').filter(event__starts_at__gte=timezone.now(),probability__gte=min_p).order_by('-probability','event__starts_at')[:50]
    return render(request,'core/dashboard.html',{'predictions':qs,'band':band,'min_p':min_p})
