import sys
from django.utils.cache import patch_vary_headers


_SCHEMA_VERIFICADO = False


def _garantir_schema_sqlite():
    """
    Garante que o banco SQLite possua as colunas mais recentes caso o projeto seja
    atualizado em nuvem antes da execução manual do comando migrate.
    """
    global _SCHEMA_VERIFICADO
    if _SCHEMA_VERIFICADO or "test" in sys.argv:
        _SCHEMA_VERIFICADO = True
        return
    try:
        from django.db import connection
        if connection.vendor != "sqlite":
            _SCHEMA_VERIFICADO = True
            return
        alteracoes = [
            ("usuarios_usuario", "banner", "ALTER TABLE usuarios_usuario ADD COLUMN banner varchar(100) NULL"),
            ("usuarios_usuario", "curso", "ALTER TABLE usuarios_usuario ADD COLUMN curso varchar(150) NOT NULL DEFAULT ''"),
            ("usuarios_usuario", "session_version", "ALTER TABLE usuarios_usuario ADD COLUMN session_version integer unsigned NOT NULL DEFAULT 1"),
            ("usuarios_publicacao", "imagem", "ALTER TABLE usuarios_publicacao ADD COLUMN imagem varchar(100) NULL"),
            ("usuarios_publicacao", "resposta_a_id", "ALTER TABLE usuarios_publicacao ADD COLUMN resposta_a_id integer NULL REFERENCES usuarios_publicacao(id)"),
            ("usuarios_observacaotarefa", "imagem", "ALTER TABLE usuarios_observacaotarefa ADD COLUMN imagem varchar(100) NULL"),
            ("usuarios_mensagemarea", "imagem", "ALTER TABLE usuarios_mensagemarea ADD COLUMN imagem varchar(100) NULL"),
        ]
        with connection.cursor() as cur:
            tabelas = {r[0] for r in cur.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()}
            if "usuarios_usuario" not in tabelas:
                return
            for tbl, col, sql in alteracoes:
                if tbl in tabelas:
                    cols = {r[1] for r in cur.execute(f"PRAGMA table_info({tbl})").fetchall()}
                    if col not in cols:
                        cur.execute(sql)
            cur.execute("CREATE INDEX IF NOT EXISTS usuarios_publicacao_resposta_a_id_idx ON usuarios_publicacao (resposta_a_id)")
        _SCHEMA_VERIFICADO = True
    except Exception:
        pass


class NoCacheForDynamicPagesMiddleware:
    """
    Garante que respostas HTML dinâmicas nunca fiquem retidas no cache do navegador (BFCache / disk cache)
    ou em proxies intermediários, evitando que dados de um usuário (sidebar, avatar, painel) ou
    notificações antigas apareçam fora de hora, além de injetar cabeçalhos rígidos de segurança HTTP.
    """
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if not request.path.startswith('/static/') and not request.path.startswith('/media/'):
            _garantir_schema_sqlite()

        response = self.get_response(request)

        # Cabeçalhos universais de proteção contra Sniffing, Clickjacking e vazamento de Referrer
        response['X-Content-Type-Options'] = 'nosniff'
        response['X-Frame-Options'] = 'DENY'
        response['Referrer-Policy'] = 'same-origin'
        response['Permissions-Policy'] = 'camera=(), microphone=(), geolocation=(), payment=(), usb=()'
        response['Cross-Origin-Opener-Policy'] = 'same-origin'

        if request.path.startswith('/media/'):
            # Isola totalmente arquivos enviados por usuários (impede execução de scripts em mídia)
            response['Content-Security-Policy'] = (
                "default-src 'none'; img-src 'self' data: blob:; style-src 'none'; script-src 'none'; sandbox"
            )
            return response

        if not request.path.startswith('/static/'):
            response['Cache-Control'] = 'private, no-cache, no-store, must-revalidate, max-age=0'
            response['Pragma'] = 'no-cache'
            response['Expires'] = '0'
            response['Content-Security-Policy'] = (
                "default-src 'self'; "
                "img-src 'self' data: blob:; "
                "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; "
                "font-src 'self' https://fonts.gstatic.com data:; "
                "script-src 'self' 'unsafe-inline'; "
                "connect-src 'self' https://suap.ifrn.edu.br; "
                "frame-ancestors 'none'; "
                "base-uri 'self'; "
                "form-action 'self'; "
                "object-src 'none'"
            )
            patch_vary_headers(response, ['Cookie'])

            status_code = getattr(response, 'status_code', 200)
            if not (300 <= status_code < 400) and 'messages' in request.COOKIES:
                storage = getattr(request, '_messages', None)
                queued = getattr(storage, '_queued_messages', None) if storage is not None else None
                if not queued:
                    response.delete_cookie('messages')
        return response
