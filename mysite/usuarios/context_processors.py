from django.core import signing

TOKEN_SALT = "scripta.user.tab"


def gerar_token_usuario(usuario_id):
    if not usuario_id:
        return ""
    try:
        return signing.dumps({"usuario": int(usuario_id)}, salt=TOKEN_SALT)
    except Exception:
        return ""


def decodificar_token_usuario(token, max_age=1209600):
    if not token or not isinstance(token, str):
        return None
    try:
        # Tenta com o salt específico da aba e faz fallback para sem salt (compatibilidade)
        try:
            data = signing.loads(token, salt=TOKEN_SALT, max_age=max_age)
        except Exception:
            data = signing.loads(token, max_age=max_age)
        if isinstance(data, dict) and "usuario" in data:
            return int(data["usuario"])
    except Exception:
        pass
    return None


def user_token_processor(request):
    """
    Injeta o token criptografado e o ID do usuário autenticado na requisição/aba atual.
    Prioriza sempre a instância `_cached_usuario` resolvida pela view para garantir
    consistência absoluta entre o HTML renderizado e o token da aba.
    """
    try:
        usuario = getattr(request, "_cached_usuario", None)
        if usuario is not None and getattr(usuario, "id", None):
            usuario_id = usuario.id
        else:
            usuario_id = getattr(request, "_resolved_usuario_id", None) or request.session.get("usuario")
        if usuario_id:
            token = gerar_token_usuario(usuario_id)
            return {
                "user_token": token,
                "user_id_atual": int(usuario_id),
            }
    except Exception:
        pass
    return {"user_token": "", "user_id_atual": ""}
