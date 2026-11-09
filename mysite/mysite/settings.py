import os
import secrets
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent


def _obter_secret_key():
    """
    Obtém a chave criptográfica a partir de variável de ambiente ou gera e persiste
    uma chave aleatória exclusiva de 64 bytes no servidor (.secret_key), evitando
    qualquer chave previsível exposta em repositório público.
    """
    env_key = os.environ.get('DJANGO_SECRET_KEY', '').strip()
    if env_key:
        return env_key
    key_file = BASE_DIR / '.secret_key'
    try:
        if key_file.exists():
            stored = key_file.read_text(encoding='utf-8').strip()
            if len(stored) >= 50:
                return stored
        nova_chave = secrets.token_urlsafe(64)
        key_file.write_text(nova_chave, encoding='utf-8')
        try:
            os.chmod(key_file, 0o600)
        except Exception:
            pass
        return nova_chave
    except Exception:
        return secrets.token_urlsafe(64)


SECRET_KEY = _obter_secret_key()

IS_PRODUCTION = bool(
    os.environ.get('PYTHONANYWHERE_DOMAIN')
    or os.environ.get('PYTHONANYWHERE_SITE')
    or os.environ.get('RENDER')
    or os.environ.get('RAILWAY_ENVIRONMENT')
    # Servidor Linux de hospedagem (ex.: /home/Scripta/mysite no PythonAnywhere)
    or str(BASE_DIR).startswith('/home/')
)

DEBUG = os.environ.get('DJANGO_DEBUG', 'False' if IS_PRODUCTION else 'True').lower() in ('true', '1', 'yes')

SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')

ALLOWED_HOSTS = [
    'scripta.pythonanywhere.com',
    'pdsweb.pythonanywhere.com',
    '.pythonanywhere.com',
    'localhost',
    '127.0.0.1',
    'testserver',
    '.app.github.dev',
    '.onrender.com',
    '.railway.app',
    '.vercel.app',
    '.fly.dev',
]

CSRF_TRUSTED_ORIGINS = [
    'https://localhost:8000',
    'http://localhost:8000',
    'http://127.0.0.1:8000',
    'https://*.app.github.dev',
    'https://*.pythonanywhere.com',
    'https://*.onrender.com',
    'https://*.railway.app',
    'https://*.fly.dev',
]

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'usuarios',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'usuarios.middleware.NoCacheForDynamicPagesMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'mysite.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'usuarios.context_processors.user_token_processor',
            ],
        },
    },
]

WSGI_APPLICATION = 'mysite.wsgi.application'

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
        'OPTIONS': {
            'timeout': 60,
        },
    }
}

LANGUAGE_CODE = 'pt-br'

TIME_ZONE = 'America/Sao_Paulo'

USE_I18N = True

USE_TZ = True

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

STATIC_URL = '/static/'
MEDIA_URL = '/media/'

# Diretório para coleta de arquivos estáticos em nuvem/produção (collectstatic):
STATIC_ROOT = BASE_DIR / 'staticfiles'
MEDIA_ROOT = BASE_DIR / 'media'

# Sessão resiliente e persistente baseada em cookies assinados com SECRET_KEY exclusivo de 64 bytes
SESSION_ENGINE = 'django.contrib.sessions.backends.signed_cookies'
MESSAGE_STORAGE = 'django.contrib.messages.storage.cookie.CookieStorage'
SESSION_COOKIE_AGE = 1209600  # 2 semanas
SESSION_SAVE_EVERY_REQUEST = False
SESSION_EXPIRE_AT_BROWSER_CLOSE = False
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = 'Lax'
CSRF_COOKIE_SAMESITE = 'Lax'

# Proteções de Segurança de Alto Nível (Headers, Limites de Upload e HTTPS)
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_BROWSER_XSS_FILTER = True
X_FRAME_OPTIONS = 'DENY'
SECURE_REFERRER_POLICY = 'same-origin'
SECURE_CROSS_ORIGIN_OPENER_POLICY = 'same-origin'
DATA_UPLOAD_MAX_MEMORY_SIZE = 6 * 1024 * 1024  # Máx 6 MB por requisição
FILE_UPLOAD_MAX_MEMORY_SIZE = 6 * 1024 * 1024  # Máx 6 MB por arquivo

if IS_PRODUCTION:
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SECURE_HSTS_SECONDS = 31536000
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD = True


