from django.utils.cache import patch_vary_headers


class NoCacheForDynamicPagesMiddleware:
    """
    Garante que respostas HTML dinâmicas nunca fiquem retidas no cache do navegador (BFCache / disk cache)
    ou em proxies intermediários, evitando que dados de um usuário (sidebar, avatar, painel) ou
    notificações antigas apareçam fora de hora.
    """
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        if not request.path.startswith('/static/') and not request.path.startswith('/media/'):
            response['Cache-Control'] = 'private, no-cache, no-store, must-revalidate, max-age=0'
            response['Pragma'] = 'no-cache'
            response['Expires'] = '0'
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
