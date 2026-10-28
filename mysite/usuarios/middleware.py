class NoCacheForDynamicPagesMiddleware:
    """
    Garante que respostas HTML dinâmicas nunca fiquem retidas no cache do navegador (BFCache / disk cache),
    evitando que dados de um usuário (sidebar, avatar, perfil) apareçam para outro usuário após logout/troca de conta.
    """
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        if not request.path.startswith('/static/') and not request.path.startswith('/media/'):
            response['Cache-Control'] = 'no-cache, no-store, must-revalidate, max-age=0'
            response['Pragma'] = 'no-cache'
            response['Expires'] = '0'
        return response
