from celery import shared_task
@shared_task
def dispatch_alerts():
    # Disparadores Telegram/WhatsApp entram por adaptadores dedicados.
    return {'status':'alert_dispatch_cycle_completed'}
