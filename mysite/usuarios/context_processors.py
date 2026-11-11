import time
import uuid
from urllib.parse import unquote
from django.contrib import messages
from django.core import signing
from django.core.cache import cache

TOKEN_SALT = "scripta.user.session.v2"
JANELA_MAXIMA_NOTIFICACAO_SEGUNDOS = 10.0


def gerar_token_usuario(usuario_id, session_version=None, jti=None):
    """
    Gera um token criptografado vinculado à versão da sessão do usuário no banco (`session_version`)
    e a um identificador único (`jti`), permitindo revogação imediata no logout.
    """
    if not usuario_id:
        return ""
    try:
        uid = int(usuario_id)
        if session_version is None:
            from .models import Usuario
            u = Usuario.objects.filter(id=uid).values("session_version").first()
            session_version = u["session_version"] if u else 1
        jti_final = jti or uuid.uuid4().hex
        return signing.dumps(
            {"usuario": uid, "sv": int(session_version), "jti": jti_final},
            salt=TOKEN_SALT,
        )
    except Exception:
        return ""


def decodificar_token_usuario(token, max_age=1209600):
    """
    Decodifica e valida o token verificando assinatura, expiração, lista de revogação (`jti`)
    e correspondência exata com `session_version` atual do usuário no banco.
    """
    if not token or not isinstance(token, str):
        return None
    try:
        data = signing.loads(token, salt=TOKEN_SALT, max_age=max_age)
        if not isinstance(data, dict) or "usuario" not in data:
            return None
        uid = int(data["usuario"])
        sv = data.get("sv")
        jti = data.get("jti")
        if not sv or not jti:
            return None
        if cache.get(f"revoked_jti:{jti}"):
            return None
        from .models import Usuario
        u = Usuario.objects.filter(id=uid).values("session_version", "aprovado").first()
        if not u or int(u["session_version"]) != int(sv):
            return None
        return uid
    except Exception:
        return None


def revogar_token_usuario(token=None, jti=None, max_age=1209600):
    """Invalida explicitamente um `jti` / token específico para impedir reuso após logout."""
    if jti:
        try:
            cache.set(f"revoked_jti:{jti}", True, timeout=max_age)
        except Exception:
            pass
    if token and isinstance(token, str):
        try:
            data = signing.loads(token, salt=TOKEN_SALT, max_age=max_age)
            if isinstance(data, dict) and data.get("jti"):
                cache.set(f"revoked_jti:{data['jti']}", True, timeout=max_age)
        except Exception:
            pass


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
                continue
            try:
                ts = float(ts_str)
            except (ValueError, TypeError):
                continue
            if (agora - ts) > JANELA_MAXIMA_NOTIFICACAO_SEGUNDOS or (ts - agora) > 5.0:
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
    Injeta o ID do usuário autenticado e apenas as notificações estritamente válidas
    para a ação recém-executada. Nunca expõe token de sessão em URLs ou no HTML.
    """
    usuario_id = None
    try:
        usuario = getattr(request, "_cached_usuario", None)
        if usuario is not None and getattr(usuario, "id", None):
            usuario_id = usuario.id
        else:
            usuario_id = getattr(request, "_resolved_usuario_id", None) or request.session.get("usuario")
    except Exception:
        usuario_id = None

    notificacoes_ativas = consumir_notificacoes_validas(request, usuario_id)

    return {
        "user_token": "",
        "user_id_atual": int(usuario_id) if usuario_id else "",
        "notificacoes_ativas": notificacoes_ativas,
    }
