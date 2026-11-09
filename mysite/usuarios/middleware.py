from django.utils.cache import patch_vary_headers


class NoCacheForDynamicPagesMiddleware:
    """
    Garante que respostas HTML dinâmicas nunca fiquem retidas no cache do navegador (BFCache / disk cache)
    ou em proxies intermediários, evitando que dados de um usuário (sidebar, avatar, painel) ou
    notificações antigas apareçam fora de hora, além de injetar cabeçalhos rígidos de segurança HTTP.
    """
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
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
                "default-src 'none'; img-src 'self' data:; style-src 'none'; script-src 'none'; sandbox"
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
                "connect-src 'self'; "
                "frame-ancestors 'none'; "
                "base-uri 'self'; "
                "form-action 'self'; "
                "object-src 'none'"
            )
            patch_vary_headers(response, ['Cookie'])

            # Se a resposta é uma página HTML renderizada (não redirect 3xx) e ainda havia cookie
            # de mensagens antigo na requisição sem novas mensagens enfileiradas, força a limpeza do cookie.
            status_code = getattr(response, 'status_code', 200)
            if not (300 <= status_code < 400) and 'messages' in request.COOKIES:
                storage = getattr(request, '_messages', None)
                queued = getattr(storage, '_queued_messages', None) if storage is not None else None
                if not queued:
                    response.delete_cookie('messages')
        return response
