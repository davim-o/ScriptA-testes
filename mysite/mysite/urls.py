import os
from django.contrib import admin
from django.urls import path, include, re_path
from django.conf import settings
from django.conf.urls.static import static
from django.views.static import serve
from django.views.generic.base import RedirectView

urlpatterns = [
    path('favicon.ico', RedirectView.as_view(url='/static/imgs/favicon.ico', permanent=True)),
    path('', include('usuarios.urls')),
    re_path(r'^media/(?P<path>.*)$', serve, {'document_root': settings.MEDIA_ROOT}),
    re_path(r'^static/(?P<path>.*)$', serve, {'document_root': settings.STATIC_ROOT}),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

# O painel /admin/ nativo do Django fica desativado por padrão por segurança.
# Só é habilitado caso uma rota secreta seja definida explicitamente via variável de ambiente.
_admin_secret_path = os.environ.get('DJANGO_ADMIN_SECRET_PATH', '').strip().strip('/')
if _admin_secret_path and _admin_secret_path != 'admin':
    urlpatterns.append(path(f'{_admin_secret_path}/', admin.site.urls))

