from django.apps import AppConfig
from django.db.backends.signals import connection_created


def ativar_sqlite_wal(sender, connection, **kwargs):
    if connection.vendor == 'sqlite':
        try:
            with connection.cursor() as cursor:
                cursor.execute('PRAGMA journal_mode = WAL;')
                cursor.execute('PRAGMA synchronous = NORMAL;')
                cursor.execute('PRAGMA busy_timeout = 60000;')
        except Exception:
            pass


class UsuariosConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = "usuarios"

    def ready(self):
        connection_created.connect(ativar_sqlite_wal)

