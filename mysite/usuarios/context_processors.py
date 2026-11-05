import time
from urllib.parse import unquote
from django.contrib import messages
from django.core import signing

TOKEN_SALT = "scripta.user.tab"
JANELA_MAXIMA_NOTIFICACAO_SEGUNDOS = 10.0


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


def _extrair_metadados_tags(extra_tags):
    meta = {}
    if not extra_tags or not isinstance(extra_tags, str):
        return meta
    for parte in extra_tags.split("|"):
        if ":" in parte:
            chave, valor = parte.split(":", 1)
            meta[chave.strip()] = valor.strip()
    return meta


def consumir_notificacoes_validas(request, usuario_id):
    """
    Consome imediatamente a fila de mensagens da requisição e retorna apenas a notificação
    que foi gerada na ação imediatamente anterior (dentro da janela de tempo), pertencente
    ao usuário atual e destinada especificamente à rota que está sendo renderizada.
    Qualquer mensagem antiga, sem metadados ou de outra página é descartada na hora.
    """
    notificacoes = []
    try:
        storage = messages.get_messages(request)
        mensagens_brutas = list(storage)
        if hasattr(storage, "_loaded_data"):
            storage._loaded_data = []
        if hasattr(storage, "_queued_messages"):
            storage._queued_messages = []
        storage.used = True
        if hasattr(request, "session") and "_messages" in request.session:
            del request.session["_messages"]

        agora = time.time()
        caminho_atual = unquote(getattr(request, "path", "") or "").rstrip("/") or "/"
        uid_atual_str = str(usuario_id) if usuario_id else "anon"

        for msg in mensagens_brutas:
            texto = str(msg).strip()
            if not texto:
                continue
            meta = _extrair_metadados_tags(getattr(msg, "extra_tags", ""))
            nid = meta.get("nid")
            ts_str = meta.get("ts")
            if not nid or not ts_str:
                # Descarta mensagens legadas sem carimbo de ação
                continue
            try:
                ts = float(ts_str)
            except (ValueError, TypeError):
                continue
            if (agora - ts) > JANELA_MAXIMA_NOTIFICACAO_SEGUNDOS or (ts - agora) > 5.0:
                # Descarta mensagens atrasadas/acumuladas
                continue

            uid_msg = meta.get("uid", "")
            if uid_msg and uid_msg != "anon" and usuario_id and uid_msg != uid_atual_str:
                continue

            path_msg = unquote(meta.get("path", "") or "").rstrip("/") or ""
            if path_msg and caminho_atual and path_msg != caminho_atual:
                continue

            level_tag = getattr(msg, "level_tag", "info") or "info"
            notificacoes.append({
                "id": nid,
                "texto": texto,
                "level_tag": level_tag,
            })
    except Exception:
        return []

    return notificacoes[-1:]


def user_token_processor(request):
    """
    Injeta o token criptografado, o ID do usuário autenticado e apenas as notificações
    estritamente válidas para a ação recém-executada na requisição/aba atual.
    """
    usuario_id = None
    token = ""
    try:
        usuario = getattr(request, "_cached_usuario", None)
        if usuario is not None and getattr(usuario, "id", None):
            usuario_id = usuario.id
        else:
            usuario_id = getattr(request, "_resolved_usuario_id", None) or request.session.get("usuario")
        if usuario_id:
            token = gerar_token_usuario(usuario_id)
    except Exception:
        usuario_id = None
        token = ""

    notificacoes_ativas = consumir_notificacoes_validas(request, usuario_id)

    return {
        "user_token": token,
        "user_id_atual": int(usuario_id) if usuario_id else "",
        "notificacoes_ativas": notificacoes_ativas,
    }
