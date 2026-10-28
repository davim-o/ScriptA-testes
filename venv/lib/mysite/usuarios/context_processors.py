from django.core import signing


def user_token_processor(request):
    """
    Injeta um token criptografado contendo o ID do usuário ativo na aba/página atual.
    Evita colisões de sessão e trocas acidentais de conta quando o desenvolvedor/usuário
    utiliza múltiplas abas com perfis diferentes (ex: Admin em uma aba e Sub-Líder em outra).
    """
    try:
        usuario_id = request.session.get("usuario")
        if usuario_id:
            token = signing.dumps({"usuario": usuario_id})
            return {"user_token": token}
    except Exception:
        pass
    return {"user_token": ""}
