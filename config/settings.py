import os
from pathlib import Path
BASE_DIR = Path(__file__).resolve().parent.parent
SECRET_KEY = os.getenv('DJANGO_SECRET_KEY', 'dev-only-key')
DEBUG = os.getenv('DJANGO_DEBUG', '0') == '1'
ALLOWED_HOSTS = [h.strip() for h in os.getenv('DJANGO_ALLOWED_HOSTS','localhost,127.0.0.1').split(',') if h.strip()]
INSTALLED_APPS = [
    'django.contrib.admin','django.contrib.auth','django.contrib.contenttypes','django.contrib.sessions','django.contrib.messages','django.contrib.staticfiles',
    'accounts','sports','predictions','odds','alerts','ai_insights','billing','core',
]
MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware','whitenoise.middleware.WhiteNoiseMiddleware','django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware','django.middleware.csrf.CsrfViewMiddleware','django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware','django.middleware.clickjacking.XFrameOptionsMiddleware',
]
ROOT_URLCONF='config.urls'
TEMPLATES=[{'BACKEND':'django.template.backends.django.DjangoTemplates','DIRS':[BASE_DIR/'templates'],'APP_DIRS':True,'OPTIONS':{'context_processors':['django.template.context_processors.request','django.contrib.auth.context_processors.auth','django.contrib.messages.context_processors.messages']}}]
WSGI_APPLICATION='config.wsgi.application'
ASGI_APPLICATION='config.asgi.application'
DATABASES={'default':{'ENGINE':'django.db.backends.postgresql','NAME':os.getenv('POSTGRES_DB','statplay'),'USER':os.getenv('POSTGRES_USER','statplay'),'PASSWORD':os.getenv('POSTGRES_PASSWORD','statplay_dev_password'),'HOST':os.getenv('POSTGRES_HOST','db'),'PORT':os.getenv('POSTGRES_PORT','5432')}}
AUTH_USER_MODEL='accounts.User'
AUTH_PASSWORD_VALIDATORS=[]
LANGUAGE_CODE='pt-br'; TIME_ZONE='America/Recife'; USE_I18N=True; USE_TZ=True
STATIC_URL='static/'; STATIC_ROOT=BASE_DIR/'staticfiles'; STATICFILES_DIRS=[BASE_DIR/'static']
DEFAULT_AUTO_FIELD='django.db.models.BigAutoField'
LOGIN_URL='/login/'; LOGIN_REDIRECT_URL='/'; LOGOUT_REDIRECT_URL='/login/'
CELERY_BROKER_URL=os.getenv('REDIS_URL','redis://redis:6379/0'); CELERY_RESULT_BACKEND=CELERY_BROKER_URL
CELERY_BEAT_SCHEDULE={
  'refresh-upcoming-events-every-15-min': {'task':'sports.tasks.refresh_upcoming_events','schedule':900.0},
  'refresh-odds-every-10-min': {'task':'odds.tasks.refresh_odds','schedule':600.0},
  'calculate-probabilities-every-15-min': {'task':'predictions.tasks.calculate_probabilities','schedule':900.0},
  'dispatch-alerts-every-5-min': {'task':'alerts.tasks.dispatch_alerts','schedule':300.0},
}
SECURE_PROXY_SSL_HEADER=('HTTP_X_FORWARDED_PROTO','https')
CSRF_COOKIE_SECURE=not DEBUG; SESSION_COOKIE_SECURE=not DEBUG; X_FRAME_OPTIONS='DENY'
