from celery import shared_task
@shared_task
def refresh_upcoming_events():
    # Adaptador de API esportiva entra aqui. Nunca gravar chaves no código.
    return {'status':'adapter_not_configured'}
