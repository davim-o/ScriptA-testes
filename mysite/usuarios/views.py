# pyrefly: ignore [missing-import]
from django.shortcuts import render, redirect, get_object_or_404
# pyrefly: ignore [missing-import]
from django.http import JsonResponse
# pyrefly: ignore [missing-import]
from django.contrib.auth.hashers import make_password, check_password
from decimal import Decimal, InvalidOperation
import os
import time
import uuid
from urllib.parse import urlsplit, urlunsplit, parse_qsl, urlencode, unquote
# pyrefly: ignore [missing-import]
from django.db import models, IntegrityError, transaction
from django.db.models import Count, Q, F
from django.contrib import messages
from django.core import signing
from django.core.cache import cache
from .context_processors import gerar_token_usuario, decodificar_token_usuario
from .models import (
    Usuario, Publicacao, Curtida, Tarefa, ParticipacaoTarefa,
    SolicitacaoArea, ObservacaoTarefa, ConclusaoTarefa, DoacaoTampinhas,
    MensagemArea, CurtidaMensagemArea, MetaTampinhas
)
from .suap import (
    CONTAS_ADM_DIRETORIAS,
    MATRICULAS_ADM_FIXAS,
    garantir_lideres_diretorias,
    identificar_diretoria_e_curso,
    consultar_api_suap,
)

AREAS_INFO = {
    "Cenário":     "Planejamento e montagem do ambiente visual do evento.",
    "Staff":       "Organização e gerenciamento da equipe de apoio.",
    "Dança":       "Coordenação das apresentações coreográficas.",
    "Figurino":    "Definição e controle das roupas e caracterizações.",
    "Sonoplastia": "Gerenciamento de músicas, efeitos e áudio do evento.",
    "Tampinhas":   "Gerenciamento e coleta de recursos recicláveis.",
    "Roteiro":     "Estruturação da sequência e organização das apresentações.",
}
TODAS_AREAS = list(AREAS_INFO.keys())

AREAS_ICONES = {
    "Cenário":     "imgs/icone-cenario.png",
    "Staff":       "imgs/icone-staff.png",
    "Dança":       "imgs/icone-danca.png",
    "Figurino":    "imgs/icone-figurino.png",
    "Sonoplastia": "imgs/icone-sonoplastia.png",
    "Tampinhas":   "imgs/icone-tampinhas.png",
    "Roteiro":     "imgs/icone-roteiro.png",
}

DIRETORIAS = ["Diaren", "Diatinf", "Diacon", "Diacin"]
ADMIN_MATRICULA = "admin"
META_TAMPINHAS_KG = Decimal("40.0")
LIMITE_CARACTERES_FEED = 3000
LIMITE_CARACTERES_CHAT = 300
EXTENSOES_IMAGEM_PERMITIDAS = (".jpg", ".jpeg", ".png", ".webp", ".gif")
TAMANHO_MAXIMO_IMAGEM_BYTES = 5 * 1024 * 1024


def _obter_ip_cliente(request):
    """Obtém o endereço IP do cliente de forma segura para controle de taxa (rate-limit)."""
    xff = (request.META.get("HTTP_X_FORWARDED_FOR") or "").strip()
    if xff:
        return xff.split(",")[0].strip()[:64]
    return (request.META.get("REMOTE_ADDR") or "local").strip()[:64]


def _verificar_bloqueio_tentativas(request, escopo, identificador="", limite=8):
    """Verifica se o IP ou identificador atingiu o limite de tentativas malsucedidas."""
    try:
        ip = _obter_ip_cliente(request)
        chave_id = f"rl:{escopo}:{ip}:{(identificador or '').lower()}"
        chave_ip = f"rl:{escopo}:ip:{ip}"
        tentativas_id = cache.get(chave_id, 0) if identificador else 0
        tentativas_ip = cache.get(chave_ip, 0)
        return tentativas_id >= limite or tentativas_ip >= (limite * 4)
    except Exception:
        return False


def _registrar_tentativa_falha(request, escopo, identificador="", janela_segundos=300):
    """Registra uma tentativa malsucedida para proteção contra força bruta."""
    try:
        ip = _obter_ip_cliente(request)
        if identificador:
            chave_id = f"rl:{escopo}:{ip}:{identificador.lower()}"
            cache.set(chave_id, cache.get(chave_id, 0) + 1, timeout=janela_segundos)
        chave_ip = f"rl:{escopo}:ip:{ip}"
        cache.set(chave_ip, cache.get(chave_ip, 0) + 1, timeout=janela_segundos)
    except Exception:
        pass


def _limpar_tentativas_falhas(request, escopo, identificador=""):
    """Limpa o contador de falhas após autenticação bem-sucedida."""
    try:
        ip = _obter_ip_cliente(request)
        if identificador:
            cache.delete(f"rl:{escopo}:{ip}:{identificador.lower()}")
    except Exception:
        pass


def validar_e_sanitizar_imagem(arquivo):
    """
    Valida rigorosamente qualquer arquivo de imagem enviado (extensão, MIME,
    assinatura binária magic-bytes e tamanho máximo de 5 MB) e renomeia com UUID
    para impedir Path Traversal, execução de scripts ou XSS via SVG/HTML.
    Retorna `(True, None)` se válido ou `(False, mensagem_erro)` se inválido.
    """
    if not arquivo:
        return False, "Nenhum arquivo enviado."

    tamanho = getattr(arquivo, "size", 0) or 0
    if tamanho <= 0:
        return False, "O arquivo enviado está vazio."
    if tamanho > TAMANHO_MAXIMO_IMAGEM_BYTES:
        return False, "A imagem deve ter no máximo 5 MB."

    nome_original = os.path.basename(getattr(arquivo, "name", "") or "").lower()
    _, ext = os.path.splitext(nome_original)
    if ext not in EXTENSOES_IMAGEM_PERMITIDAS:
        return False, "Formato de imagem não permitido. Utilize apenas JPG, PNG, WEBP ou GIF."

    content_type = (getattr(arquivo, "content_type", "") or "").lower()
    tipos_aceitos = {"image/jpeg", "image/jpg", "image/png", "image/webp", "image/gif"}
    if content_type and content_type not in tipos_aceitos:
        return False, "Tipo de arquivo inválido. Envie apenas imagens JPG, PNG, WEBP ou GIF."

    try:
        pos_inicial = arquivo.tell() if hasattr(arquivo, "tell") else 0
        cabecalho = arquivo.read(32)
        if hasattr(arquivo, "seek"):
            arquivo.seek(pos_inicial)
    except Exception:
        return False, "Não foi possível ler o arquivo de imagem enviado."

    assinatura_valida = (
        cabecalho.startswith(b"\xff\xd8\xff")
        or cabecalho.startswith(b"\x89PNG\r\n\x1a\n")
        or cabecalho.startswith(b"GIF87a")
        or cabecalho.startswith(b"GIF89a")
        or (cabecalho.startswith(b"RIFF") and cabecalho[8:12] == b"WEBP")
    )
    if not assinatura_valida:
        return False, "O conteúdo do arquivo não corresponde a uma imagem válida (JPG, PNG, WEBP ou GIF)."

    ext_limpa = ".jpg" if ext == ".jpeg" else ext
    arquivo.name = f"{uuid.uuid4().hex}{ext_limpa}"
    return True, None


def mesma_diretoria_usuarios(u1, u2):
    """
    Verifica se dois usuários pertencem à mesma diretoria.
    Isola completamente Diaren, Diatinf, Diacon e Diacin entre si.
    """
    if u1 is None or u2 is None:
        return False
    d1 = (getattr(u1, "diretoria", "") or "").strip()
    d2 = (getattr(u2, "diretoria", "") or "").strip()
    if d1 in DIRETORIAS and d2 in DIRETORIAS:
        return d1.lower() == d2.lower()
    return True


def filtrar_qs_diretoria(qs, usuario, campo_diretoria="diretoria"):
    """Filtra um QuerySet pela diretoria do usuário logado quando aplicável."""
    diret = (getattr(usuario, "diretoria", "") or "").strip()
    if diret in DIRETORIAS:
        return qs.filter(**{f"{campo_diretoria}__iexact": diret})
    return qs


def formatar_kg(valor, is_gramas=True):
    if valor is None:
        return "0Kg"
    if is_gramas:
        d = Decimal(str(valor)) / Decimal("1000")
    else:
        d = Decimal(str(valor))
    s = f"{d:.3f}".rstrip("0").rstrip(".")
    if not s or s == "-0":
        s = "0"
    return f"{s}Kg"


def obter_total_doacoes_kg_formatado(com_unidade=True, diretoria=None):
    doacoes_qs = DoacaoTampinhas.objects.filter(
        usuario__aprovado=True
    ).exclude(
        usuario__matricula="admin"
    )
    usuarios_qs = Usuario.objects.filter(aprovado=True).exclude(matricula="admin")
    if diretoria and diretoria in DIRETORIAS:
        doacoes_qs = doacoes_qs.filter(usuario__diretoria__iexact=diretoria)
        usuarios_qs = usuarios_qs.filter(diretoria__iexact=diretoria)

    total_gramas = doacoes_qs.aggregate(total=models.Sum("quantidade_gramas"))["total"]

    if total_gramas is None:
        total_kg = usuarios_qs.aggregate(total=models.Sum("doacao_tampinhas"))["total"] or 0
        d = Decimal(str(total_kg))
    else:
        d = Decimal(total_gramas) / Decimal("1000")

    s = f"{d:.3f}".rstrip("0").rstrip(".")
    if not s or s == "-0":
        s = "0"
    return f"{s}Kg" if com_unidade else s


def obter_meta_tampinhas_kg(diretoria=None):
    """Retorna a meta de arrecadação de tampinhas (em Kg) ativa para a diretoria no banco ou o valor padrão."""
    try:
        qs = MetaTampinhas.objects.all()
        if diretoria and diretoria in DIRETORIAS:
            qs_dir = qs.filter(atualizado_por__diretoria__iexact=diretoria)
            if qs_dir.exists():
                qs = qs_dir
            else:
                return META_TAMPINHAS_KG
        registro = qs.order_by("-atualizado_em", "-id").first()
        if registro and registro.meta_kg and registro.meta_kg > 0:
            return Decimal(str(registro.meta_kg))
    except Exception:
        pass
    return META_TAMPINHAS_KG


def obter_membros_da_area(nome_area, diretoria=None):
    """
    Retorna exclusivamente os membros aprovados vinculados à área e à diretoria informadas
    (excluindo o líder geral), garantindo isolamento entre áreas e entre diretorias.
    """
    if not nome_area or nome_area not in TODAS_AREAS:
        return []
    aprovados = Usuario.objects.filter(aprovado=True).order_by("matricula")
    if diretoria and diretoria in DIRETORIAS:
        aprovados = aprovados.filter(diretoria__iexact=diretoria)
    return [
        m for m in aprovados
        if not m.eh_administrador()
        and (nome_area in m.get_areas_list() or (m.sub_lider and m.sublider_de == nome_area))
    ]


def limpar_mensagens(request):
    """Consome e esvazia completamente mensagens pendentes para evitar notificações acumuladas ou atrasadas."""
    try:
        storage = messages.get_messages(request)
        for _ in storage:
            pass
        if hasattr(storage, "_loaded_data"):
            storage._loaded_data = []
        if hasattr(storage, "_queued_messages"):
            storage._queued_messages = []
        storage.used = True
        storage.modified = True
        if hasattr(request, "session") and "_messages" in request.session:
            del request.session["_messages"]
        request._ultima_mensagem_obj = None
    except Exception:
        pass


def definir_mensagem(request, nivel_fn, texto):
    """
    Garante que apenas uma única notificação correspondente à ação atual seja emitida,
    vinculando ID único, usuário, timestamp e página de destino para nunca aparecer fora de hora.
    """
    limpar_mensagens(request)
    uid_atual = getattr(request, "_resolved_usuario_id", None)
    if not uid_atual:
        u_cache = getattr(request, "_cached_usuario", None)
        if u_cache is not None and getattr(u_cache, "id", None):
            uid_atual = u_cache.id
        elif hasattr(request, "session"):
            try:
                uid_atual = request.session.get("usuario")
            except Exception:
                uid_atual = None
    msg_id = uuid.uuid4().hex[:12]
    ts = f"{time.time():.3f}"
    uid_str = str(uid_atual) if uid_atual is not None else "anon"
    extra = f"nid:{msg_id}|uid:{uid_str}|ts:{ts}"
    nivel_fn(request, texto, extra_tags=extra)
    try:
        storage = getattr(request, "_messages", None)
        if storage is not None and getattr(storage, "_queued_messages", None):
            request._ultima_mensagem_obj = storage._queued_messages[-1]
    except Exception:
        pass


def matricula_valida(matricula):
    return True


def obter_token_requisicao(request):
    """Extrai o token assinado da aba a partir de POST, GET ou cabeçalho HTTP."""
    token = None
    if request.method == "POST":
        token = request.POST.get("_user_token")
    if not token:
        token = request.GET.get("_user_token")
    if not token:
        if hasattr(request, "headers"):
            token = request.headers.get("X-User-Token")
        if not token and hasattr(request, "META"):
            token = request.META.get("HTTP_X_USER_TOKEN")
    return token.strip() if isinstance(token, str) and token.strip() else None


def anexar_token_em_url(url_str, token):
    if not url_str or not token:
        return url_str
    try:
        partes = urlsplit(url_str)
        # Proteção contra Open Redirect: nunca anexa token de sessão a URLs externas
        if partes.scheme or partes.netloc:
            return "/"
        if partes.path in ("/", "/sair/", "/cadastro/"):
            return url_str
        query_params = dict(parse_qsl(partes.query, keep_blank_values=True))
        query_params["_user_token"] = token
        nova_query = urlencode(query_params)
        return urlunsplit(("", "", partes.path, nova_query, partes.fragment))
    except Exception:
        return url_str


def redirect_autenticado(request, destino, *args, **kwargs):
    """
    Redireciona preservando o `_user_token` da aba ativa quando presente na requisição,
    evitando que um redirect (302 -> GET) caia no cookie compartilhado de outra aba,
    e vincula a notificação recém-emitida exclusivamente ao caminho de destino do redirect.
    """
    response = redirect(destino, *args, **kwargs)
    if "Location" in response:
        msg_obj = getattr(request, "_ultima_mensagem_obj", None)
        if msg_obj is not None:
            try:
                caminho_alvo = unquote(urlsplit(response["Location"]).path or "")
                if caminho_alvo:
                    tags_atuais = getattr(msg_obj, "extra_tags", "") or ""
                    if "|path:" not in tags_atuais:
                        msg_obj.extra_tags = f"{tags_atuais}|path:{caminho_alvo}" if tags_atuais else f"path:{caminho_alvo}"
                        storage = getattr(request, "_messages", None)
                        if storage is not None:
                            storage.modified = True
            except Exception:
                pass
        token = getattr(request, "_explicit_user_token", None)
        if token:
            response["Location"] = anexar_token_em_url(response["Location"], token)
    return response


def usuario_logado(request):
    if hasattr(request, "_cached_usuario") and request._cached_usuario is not None:
        return request._cached_usuario

    usuario_id = None
    token = obter_token_requisicao(request)
    if token:
        uid_token = decodificar_token_usuario(token)
        if uid_token:
            usuario_id = uid_token
            request._explicit_user_token = gerar_token_usuario(usuario_id)
            request._resolved_usuario_id = usuario_id
            try:
                if "usuario" not in request.session:
                    request.session["usuario"] = usuario_id
                    request.session.modified = True
            except Exception:
                pass

    if not usuario_id:
        try:
            usuario_id = request.session.get("usuario")
            if usuario_id:
                request._resolved_usuario_id = usuario_id
        except Exception:
            usuario_id = None

    if not usuario_id:
        request._cached_usuario = None
        return None

    try:
        u = Usuario.objects.get(id=usuario_id)
        if not u.aprovado and not u.eh_administrador():
            request._cached_usuario = None
            return None
        request._cached_usuario = u
        request._resolved_usuario_id = u.id
        return u
    except Usuario.DoesNotExist:
        request._cached_usuario = None
        return None
    except Exception:
        request._cached_usuario = None
        return None



def verificar_suap_matricula(request):
    """
    Endpoint AJAX para identificar a diretoria, curso e nome do aluno a partir da matrícula
    (e opcionalmente senha via POST) do SUAP durante o preenchimento do cadastro.
    """
    matricula = (request.POST.get("matricula") or request.GET.get("matricula") or "").strip()[:30]
    # Nunca aceita senha via query string (GET) para evitar vazamento em logs de acesso
    senha = request.POST.get("senha") or ""
    if not matricula:
        return JsonResponse({"diretoria": None, "curso": "", "nome": ""})

    if _verificar_bloqueio_tentativas(request, "suap_check", matricula, limite=15):
        return JsonResponse({
            "autenticado_suap": False,
            "credenciais_invalidas": False,
            "erro": "Muitas tentativas em sequência. Aguarde alguns minutos e tente novamente.",
            "nome": "",
            "diretoria": None,
            "curso": "",
        }, status=429)

    diretoria_mat, curso_mat = identificar_diretoria_e_curso(matricula)
    if senha and request.method == "POST":
        dados_suap = consultar_api_suap(matricula, senha, timeout=3.5)
        if dados_suap.get("credenciais_invalidas"):
            _registrar_tentativa_falha(request, "suap_check", matricula, janela_segundos=180)
        return JsonResponse({
            "autenticado_suap": bool(dados_suap.get("autenticado_suap")),
            "credenciais_invalidas": bool(dados_suap.get("credenciais_invalidas")),
            "erro": dados_suap.get("erro") or "",
            "nome": dados_suap.get("nome") or "",
            "diretoria": dados_suap.get("diretoria") or diretoria_mat,
            "curso": dados_suap.get("curso") or curso_mat,
        })

    return JsonResponse({
        "autenticado_suap": False,
        "credenciais_invalidas": False,
        "erro": "",
        "nome": "",
        "diretoria": diretoria_mat,
        "curso": curso_mat,
    })


def cadastro(request):
    limpar_mensagens(request)
    contexto = {"erro": None, "form": {}}
    if request.method == "POST":
        nome = request.POST.get("nome", "").strip()
        matricula = request.POST.get("matricula", "").strip()
        senha = request.POST.get("senha", "")
        diretoria = request.POST.get("diretoria", "").strip()
        areas_selecionadas = [a for a in request.POST.getlist("areas") if a in TODAS_AREAS]

        erro = None
        dados_suap = {}
        diretoria_suap, curso_suap = identificar_diretoria_e_curso(matricula)

        if _verificar_bloqueio_tentativas(request, "cadastro", matricula, limite=10):
            erro = "Muitas tentativas de cadastro em sequência. Aguarde alguns minutos e tente novamente."
        elif len(nome) > 100:
            erro = "O nome deve ter no máximo 100 caracteres."
        elif not matricula:
            erro = "Informe a sua matrícula do SUAP."
        elif len(matricula) > 20:
            erro = "A matrícula deve ter no máximo 20 caracteres."
        elif matricula.lower() in MATRICULAS_ADM_FIXAS:
            erro = "Essa matrícula é reservada para a administração."
        elif not senha:
            erro = "Informe a sua senha do SUAP."
        elif len(senha) > 128:
            erro = "A senha informada excede o limite permitido."
        elif Usuario.objects.filter(matricula__iexact=matricula).exists():
            erro = "Essa matrícula já está cadastrada."
        elif diretoria_suap and diretoria and diretoria != diretoria_suap:
            detalhe_curso = f" ({curso_suap})" if curso_suap else ""
            erro = (
                f"A matrícula {matricula} pertence à diretoria {diretoria_suap}{detalhe_curso}, "
                f"e não à diretoria {diretoria} selecionada."
            )
            diretoria = diretoria_suap
        else:
            dados_suap = consultar_api_suap(matricula, senha)
            if dados_suap.get("credenciais_invalidas"):
                _registrar_tentativa_falha(request, "cadastro", matricula)
                erro = dados_suap.get("erro") or "Matrícula ou senha do SUAP inválida."
            else:
                if dados_suap.get("diretoria"):
                    diretoria_suap = dados_suap["diretoria"]
                if dados_suap.get("curso"):
                    curso_suap = dados_suap["curso"]

                if diretoria_suap:
                    if diretoria and diretoria != diretoria_suap:
                        detalhe_curso = f" ({curso_suap})" if curso_suap else ""
                        erro = (
                            f"A matrícula {matricula} pertence à diretoria {diretoria_suap}{detalhe_curso}, "
                            f"e não à diretoria {diretoria} selecionada."
                        )
                        diretoria = diretoria_suap
                    else:
                        diretoria = diretoria_suap
                elif diretoria not in DIRETORIAS:
                    erro = "Não foi possível identificar a diretoria pela matrícula informada. Verifique sua matrícula do SUAP."

        nome_final = nome or (dados_suap.get("nome") or "").strip() or matricula
        contexto["form"] = {
            "nome": nome or (dados_suap.get("nome") or "").strip(),
            "matricula": matricula,
            "diretoria": diretoria,
            "areas": areas_selecionadas,
        }

        if erro is None:
            try:
                with transaction.atomic():
                    # Como a diretoria é identificada automaticamente pela matrícula do SUAP,
                    # o membro já entra aprovado na sua diretoria; apenas as áreas solicitadas
                    # aguardam aprovação dos respectivos sub-líderes/líder.
                    novo_usuario = Usuario.objects.create(
                        nome=nome_final[:100],
                        matricula=matricula,
                        senha=make_password(senha),
                        diretoria=diretoria,
                        areas="",
                        aprovado=True,
                    )
                    for area_nome in areas_selecionadas:
                        if area_nome in TODAS_AREAS:
                            SolicitacaoArea.objects.get_or_create(
                                usuario=novo_usuario,
                                area=area_nome,
                            )
            except IntegrityError:
                # Cadastro simultâneo com a mesma matrícula
                erro = "Essa matrícula já está cadastrada."
            else:
                _limpar_tentativas_falhas(request, "cadastro", matricula)
                return redirect("login")

        contexto["erro"] = erro
    return render(request, "cadastro.html", contexto)


def login_usuario(request):
    limpar_mensagens(request)
    garantir_lideres_diretorias()
    if request.method == "GET" and (request.GET.get("trocar") or request.GET.get("sair")):
        request.session.flush()
        if hasattr(request, "_cached_usuario"):
            delattr(request, "_cached_usuario")

    erro = None
    if request.method == "POST":
        matricula = request.POST.get("matricula", "").strip()
        senha = request.POST.get("senha", "")
        if not matricula:
            erro = "Informe a matrícula."
        elif not senha:
            erro = "Informe a senha."
        elif _verificar_bloqueio_tentativas(request, "login", matricula, limite=8):
            erro = "Muitas tentativas de login malsucedidas. Por segurança, aguarde 5 minutos antes de tentar novamente."
        else:
            mat_lower = matricula.lower()
            if mat_lower in CONTAS_ADM_DIRETORIAS:
                cfg_adm = CONTAS_ADM_DIRETORIAS[mat_lower]
                usuario_adm = Usuario.objects.filter(matricula__iexact=cfg_adm["matricula"]).first()
                if not usuario_adm and senha == cfg_adm["senha_padrao"]:
                    usuario_adm = Usuario.objects.create(
                        nome=cfg_adm["nome"],
                        matricula=cfg_adm["matricula"],
                        senha=make_password(cfg_adm["senha_padrao"]),
                        diretoria=cfg_adm["diretoria"],
                        areas="",
                        aprovado=True,
                    )

            usuario = Usuario.objects.filter(matricula__iexact=matricula).first()
            if not usuario:
                _registrar_tentativa_falha(request, "login", matricula)
                erro = "Matrícula ou senha inválida."
            else:
                senha_valida = check_password(senha, usuario.senha)
                if not senha_valida and not usuario.eh_administrador():
                    dados_suap = consultar_api_suap(matricula, senha)
                    if dados_suap.get("autenticado_suap"):
                        usuario.senha = make_password(senha)
                        if dados_suap.get("nome") and (not usuario.nome or usuario.nome == usuario.matricula):
                            usuario.nome = dados_suap["nome"][:100]
                        usuario.save(update_fields=["senha", "nome"])
                        senha_valida = True

                if not senha_valida:
                    _registrar_tentativa_falha(request, "login", matricula)
                    erro = "Matrícula ou senha inválida."
                elif not usuario.aprovado and not usuario.eh_administrador():
                    erro = "Seu cadastro ainda está aguardando aprovação da diretoria."
                else:
                    _limpar_tentativas_falhas(request, "login", matricula)
                    limpar_mensagens(request)
                    request.session.flush()
                    request.session["usuario"] = usuario.id
                    request.session.modified = True
                    request._cached_usuario = usuario
                    request._resolved_usuario_id = usuario.id
                    if request.POST.get("_from_browser") == "1":
                        request._explicit_user_token = gerar_token_usuario(usuario.id)
                    return redirect_autenticado(request, "feed")
    return render(request, "login.html", {"erro": erro, "matricula": matricula if request.method == "POST" else ""})


def feed(request):
    usuario = usuario_logado(request)
    if usuario is None:
        return redirect("login")
    if usuario.diretoria in DIRETORIAS:
        publicacoes = (
            Publicacao.objects.filter(usuario__diretoria__iexact=usuario.diretoria)
            .select_related("usuario")
            .prefetch_related("curtidas")
            .order_by("-data")
        )
    else:
        publicacoes = Publicacao.objects.select_related("usuario").prefetch_related("curtidas").order_by("-data")
    curtidas = Curtida.objects.filter(usuario=usuario).values_list("publicacao_id", flat=True)
    return render(request, "feed.html", {
        "usuario": usuario,
        "publicacoes": publicacoes,
        "curtidas": curtidas
    })


def publicar(request):
    usuario = usuario_logado(request)
    if usuario is None:
        return redirect("login")
    if request.method == "POST":
        texto = request.POST.get("texto", "").strip()
        if not texto:
            definir_mensagem(request, messages.error, "Digite uma mensagem antes de publicar no feed.")
        elif len(texto) > LIMITE_CARACTERES_FEED:
            definir_mensagem(
                request,
                messages.error,
                f"A publicação excede o limite de {LIMITE_CARACTERES_FEED} caracteres ({len(texto)}/{LIMITE_CARACTERES_FEED}).",
            )
        else:
            Publicacao.objects.create(usuario=usuario, texto=texto)
    return redirect_autenticado(request, "feed")


def editar_publicacao(request, id_publicacao):
    usuario = usuario_logado(request)
    if usuario is None:
        return redirect("login")
    if request.method == "POST":
        publicacao = get_object_or_404(Publicacao.objects.select_related("usuario"), id=id_publicacao)
        if publicacao.usuario_id != usuario.id or not mesma_diretoria_usuarios(usuario, publicacao.usuario):
            definir_mensagem(request, messages.error, "Você só pode editar as suas próprias publicações.")
            return redirect_autenticado(request, "feed")
        texto = request.POST.get("texto", "").strip()
        if not texto:
            definir_mensagem(request, messages.error, "O texto da publicação não pode ficar vazio.")
        elif len(texto) > LIMITE_CARACTERES_FEED:
            definir_mensagem(
                request,
                messages.error,
                f"A publicação excede o limite de {LIMITE_CARACTERES_FEED} caracteres ({len(texto)}/{LIMITE_CARACTERES_FEED}).",
            )
        else:
            publicacao.texto = texto
            publicacao.editado = True
            publicacao.save(update_fields=["texto", "editado"])
            definir_mensagem(request, messages.success, "Publicação atualizada com sucesso!")
    return redirect_autenticado(request, "feed")


def curtir(request, id_publicacao):
    if request.method != "POST":
        return JsonResponse({"erro": "Método inválido. Use uma requisição POST."}, status=405)
    usuario = usuario_logado(request)
    if usuario is None:
        return JsonResponse({"erro": "Sua sessão expirou. Faça login novamente."}, status=401)
    publicacao = get_object_or_404(Publicacao.objects.select_related("usuario"), id=id_publicacao)
    if (
        usuario.diretoria in DIRETORIAS
        and publicacao.usuario.diretoria in DIRETORIAS
        and publicacao.usuario.diretoria.lower() != usuario.diretoria.lower()
    ):
        return JsonResponse({"erro": "Esta publicação pertence ao feed de outra diretoria."}, status=403)
    curtida = Curtida.objects.filter(usuario=usuario, publicacao=publicacao)
    if curtida.exists():
        curtida.delete()
        curtido = False
    else:
        Curtida.objects.create(usuario=usuario, publicacao=publicacao)
        curtido = True
    return JsonResponse({"curtido": curtido, "curtidas": publicacao.total_curtidas()})


def excluir_publicacao(request, id_publicacao):
    usuario = usuario_logado(request)
    if usuario is None:
        return redirect("login")
    if request.method == "POST":
        publicacao = get_object_or_404(Publicacao.objects.select_related("usuario"), id=id_publicacao)
        mesma_diretoria = (
            usuario.diretoria not in DIRETORIAS
            or publicacao.usuario.diretoria not in DIRETORIAS
            or publicacao.usuario.diretoria.lower() == usuario.diretoria.lower()
        )
        if publicacao.usuario_id == usuario.id or (usuario.eh_administrador() and mesma_diretoria):
            publicacao.delete()
            definir_mensagem(request, messages.success, "Publicação excluída com sucesso.")
        else:
            definir_mensagem(request, messages.error, "Você só pode excluir as suas próprias publicações.")
    return redirect_autenticado(request, "feed")


def painel_administrativo(request):
    usuario = usuario_logado(request)
    if usuario is None:
        return redirect("login")
    if not usuario.tem_acesso_painel():
        definir_mensagem(request, messages.error, "Você não possui permissão para acessar o Painel Administrativo.")
        return redirect_autenticado(request, "feed")

    todos_aprovados = filtrar_qs_diretoria(
        Usuario.objects.filter(aprovado=True), usuario, "diretoria"
    ).order_by("matricula")
    total_doacoes = obter_total_doacoes_kg_formatado(com_unidade=False, diretoria=usuario.diretoria)
    membros_elegiveis_doacao = [m for m in todos_aprovados if not m.eh_administrador()]
    meta_atual_d = obter_meta_tampinhas_kg(diretoria=usuario.diretoria)
    meta_tampinhas_atual_str = f"{meta_atual_d:.3f}".rstrip("0").rstrip(".") or "40"
    meta_tampinhas_formatada = formatar_kg(meta_atual_d, is_gramas=False)

    if usuario.sub_lider and not usuario.eh_administrador():
        membros = obter_membros_da_area(usuario.sublider_de, diretoria=usuario.diretoria)
        pendentes = Usuario.objects.none()
        tarefas_base = filtrar_qs_diretoria(
            Tarefa.objects.filter(area=usuario.sublider_de),
            usuario,
            "criada_por__diretoria",
        ).prefetch_related("conclusoes")
        tarefas = tarefas_base.filter(encerrada=False).annotate(
            total_concl=Count("conclusoes", filter=~Q(conclusoes__usuario=F("criada_por")), distinct=True)
        ).order_by("-criada_em")
        tarefas_concluidas = tarefas_base.filter(encerrada=True).annotate(
            total_concl=Count("conclusoes", filter=~Q(conclusoes__usuario=F("criada_por")), distinct=True)
        ).order_by("-criada_em")
        solicitacoes_area = filtrar_qs_diretoria(
            SolicitacaoArea.objects.filter(area=usuario.sublider_de),
            usuario,
            "usuario__diretoria",
        ).select_related("usuario").order_by("solicitado_em")
        total_membros = len(membros)
        total_pendentes = solicitacoes_area.count()
    else:
        membros = todos_aprovados
        pendentes = filtrar_qs_diretoria(
            Usuario.objects.filter(aprovado=False), usuario, "diretoria"
        ).order_by("matricula")
        tarefas = filtrar_qs_diretoria(
            Tarefa.objects.filter(encerrada=False), usuario, "criada_por__diretoria"
        ).order_by("-criada_em")
        tarefas_concluidas = Tarefa.objects.none()
        solicitacoes_area = filtrar_qs_diretoria(
            SolicitacaoArea.objects.select_related("usuario"), usuario, "usuario__diretoria"
        ).order_by("area", "solicitado_em")
        total_membros = membros.count()
        total_pendentes = solicitacoes_area.count() + pendentes.count()

    return render(request, "admin.html", {
        "usuario": usuario,
        "membros": membros,
        "pendentes": pendentes,
        "total_membros": total_membros,
        "total_pendentes": total_pendentes,
        "total_doacoes": total_doacoes,
        "membros_elegiveis_doacao": membros_elegiveis_doacao,
        "meta_tampinhas_atual": meta_tampinhas_atual_str,
        "meta_tampinhas_formatada": meta_tampinhas_formatada,
        "tarefas": tarefas,
        "tarefas_concluidas": tarefas_concluidas,
        "solicitacoes_area": solicitacoes_area,
    })


def stats_painel(request):
    usuario = usuario_logado(request)
    if usuario is None or not usuario.tem_acesso_painel():
        return JsonResponse({"erro": "Não autorizado."}, status=403)
    if usuario.sub_lider and not usuario.eh_administrador():
        total_membros = len(obter_membros_da_area(usuario.sublider_de, diretoria=usuario.diretoria))
        total_pendentes = filtrar_qs_diretoria(
            SolicitacaoArea.objects.filter(area=usuario.sublider_de),
            usuario,
            "usuario__diretoria",
        ).count()
    else:
        total_membros = filtrar_qs_diretoria(
            Usuario.objects.filter(aprovado=True), usuario, "diretoria"
        ).count()
        pendentes_membros = filtrar_qs_diretoria(
            Usuario.objects.filter(aprovado=False), usuario, "diretoria"
        ).count()
        pendentes_areas = filtrar_qs_diretoria(
            SolicitacaoArea.objects.all(), usuario, "usuario__diretoria"
        ).count()
        total_pendentes = pendentes_areas + pendentes_membros
    doacoes_formatado = obter_total_doacoes_kg_formatado(com_unidade=True, diretoria=usuario.diretoria)
    return JsonResponse({
        "membros": total_membros,
        "pendentes": total_pendentes,
        "doacoes": doacoes_formatado,
    })


def registrar_doacao(request):
    usuario = usuario_logado(request)
    if usuario is None:
        return redirect("login")

    if request.method != "POST":
        return redirect_autenticado(request, "painel_administrativo")

    # Apenas o sub-líder da área Tampinhas pode registrar doações
    if not (usuario.sub_lider and usuario.sublider_de == "Tampinhas"):
        definir_mensagem(request, messages.error, "Apenas o sub-líder da área Tampinhas pode registrar doações.")
        if usuario.tem_acesso_painel():
            return redirect_autenticado(request, "painel_administrativo")
        return redirect_autenticado(request, "feed")

    membro_id = request.POST.get("membro_id")
    if not membro_id:
        definir_mensagem(request, messages.error, "Selecione um membro para receber a doação.")
        return redirect_autenticado(request, "painel_administrativo")

    try:
        membro = Usuario.objects.get(id=membro_id)
    except (Usuario.DoesNotExist, ValueError):
        definir_mensagem(request, messages.error, "Membro selecionado não encontrado.")
        return redirect_autenticado(request, "painel_administrativo")

    if not membro.aprovado or membro.eh_administrador() or not mesma_diretoria_usuarios(usuario, membro):
        definir_mensagem(request, messages.error, "Apenas membros aprovados da sua diretoria podem receber doações.")
        return redirect_autenticado(request, "painel_administrativo")

    qtd_str = request.POST.get("quantidade", "").strip()
    if not qtd_str:
        definir_mensagem(request, messages.error, "Informe a quantidade em gramas.")
        return redirect_autenticado(request, "painel_administrativo")

    if not qtd_str.isdigit():
        definir_mensagem(request, messages.error, "A quantidade deve ser um número inteiro positivo entre 1 e 100.000 gramas.")
        return redirect_autenticado(request, "painel_administrativo")

    try:
        qtd_gramas = int(qtd_str)
    except (ValueError, TypeError):
        definir_mensagem(request, messages.error, "Quantidade inválida.")
        return redirect_autenticado(request, "painel_administrativo")

    if qtd_gramas < 1 or qtd_gramas > 100000:
        definir_mensagem(request, messages.error, "A quantidade deve ser um número inteiro positivo entre 1 e 100.000 gramas.")
        return redirect_autenticado(request, "painel_administrativo")

    try:
        with transaction.atomic():
            DoacaoTampinhas.objects.create(
                usuario=membro,
                quantidade_gramas=qtd_gramas,
                registrado_por=usuario,
            )
            total_membro_gramas = DoacaoTampinhas.objects.filter(usuario=membro).aggregate(
                tot=models.Sum("quantidade_gramas")
            )["tot"] or 0
            membro.doacao_tampinhas = round(float(total_membro_gramas) / 1000.0, 4)
            membro.save(update_fields=["doacao_tampinhas"])
    except Exception as e:
        definir_mensagem(request, messages.error, f"Erro ao registrar doação: {str(e)}")
        return redirect_autenticado(request, "painel_administrativo")

    novo_total_formatado = formatar_kg(total_membro_gramas, is_gramas=True)
    definir_mensagem(
        request,
        messages.success,
        f"Doação de {qtd_gramas}g registrada com sucesso para {membro.matricula}! Novo total: {novo_total_formatado}."
    )
    return redirect_autenticado(request, "painel_administrativo")


def definir_meta_tampinhas(request):
    usuario = usuario_logado(request)
    if usuario is None:
        return redirect("login")

    if request.method != "POST":
        return redirect_autenticado(request, "painel_administrativo")

    # Apenas o sub-líder da área Tampinhas pode definir a meta de arrecadação
    if not (usuario.sub_lider and usuario.sublider_de == "Tampinhas"):
        definir_mensagem(request, messages.error, "Apenas o sub-líder da área Tampinhas pode definir a meta de arrecadação.")
        if usuario.tem_acesso_painel():
            return redirect_autenticado(request, "painel_administrativo")
        return redirect_autenticado(request, "feed")

    meta_str = (request.POST.get("meta_kg") or "").strip().replace(",", ".")
    if not meta_str:
        definir_mensagem(request, messages.error, "Informe a meta de arrecadação em quilogramas (Kg).")
        return redirect_autenticado(request, "painel_administrativo")

    try:
        nova_meta = Decimal(meta_str)
    except (InvalidOperation, ValueError, TypeError):
        definir_mensagem(request, messages.error, "Informe um valor numérico válido para a meta em Kg.")
        return redirect_autenticado(request, "painel_administrativo")

    if nova_meta <= Decimal("0") or nova_meta > Decimal("100000"):
        definir_mensagem(request, messages.error, "A meta deve ser um valor positivo entre 0,1 Kg e 100.000 Kg.")
        return redirect_autenticado(request, "painel_administrativo")

    nova_meta = nova_meta.quantize(Decimal("0.001"))

    try:
        with transaction.atomic():
            if usuario.diretoria in DIRETORIAS:
                MetaTampinhas.objects.filter(atualizado_por__diretoria__iexact=usuario.diretoria).delete()
            else:
                MetaTampinhas.objects.all().delete()
            MetaTampinhas.objects.create(
                meta_kg=nova_meta,
                atualizado_por=usuario,
            )
    except Exception as e:
        definir_mensagem(request, messages.error, f"Erro ao salvar a meta: {str(e)}")
        return redirect_autenticado(request, "painel_administrativo")

    meta_formatada = formatar_kg(nova_meta, is_gramas=False)
    definir_mensagem(
        request,
        messages.success,
        f"Meta de arrecadação atualizada para {meta_formatada} com sucesso!"
    )
    return redirect_autenticado(request, "painel_administrativo")


def tampinhas(request):
    usuario = usuario_logado(request)
    if usuario is None:
        return redirect("login")

    meta_kg = obter_meta_tampinhas_kg(diretoria=usuario.diretoria)
    meta_kg_formatada = formatar_kg(meta_kg, is_gramas=False)

    qs_doacoes = filtrar_qs_diretoria(
        DoacaoTampinhas.objects.filter(usuario__aprovado=True).exclude(usuario__matricula="admin"),
        usuario,
        "usuario__diretoria",
    )
    total_gramas_geral = qs_doacoes.aggregate(tot=models.Sum("quantidade_gramas"))["tot"]

    if total_gramas_geral is None:
        qs_usu = filtrar_qs_diretoria(
            Usuario.objects.filter(aprovado=True).exclude(matricula="admin"),
            usuario,
            "diretoria",
        )
        total_kg_db = qs_usu.aggregate(tot=models.Sum("doacao_tampinhas"))["tot"] or 0
        total_geral_d = Decimal(str(total_kg_db))
    else:
        total_geral_d = Decimal(total_gramas_geral) / Decimal("1000")

    s_tot = f"{total_geral_d:.3f}".rstrip("0").rstrip(".")
    if not s_tot or s_tot == "-0":
        s_tot = "0"
    total_geral_kg = f"{s_tot}Kg"

    if meta_kg > 0:
        progresso_porcentagem = min(100.0, float((total_geral_d / meta_kg) * Decimal("100")))
    else:
        progresso_porcentagem = 0.0

    membros = filtrar_qs_diretoria(
        Usuario.objects.filter(aprovado=True).exclude(matricula="admin"),
        usuario,
        "diretoria",
    )
    membros_validos = [m for m in membros if not m.eh_administrador()]

    ranking = []
    for m in membros_validos:
        tot_g = DoacaoTampinhas.objects.filter(usuario=m).aggregate(
            tot=models.Sum("quantidade_gramas")
        )["tot"]
        if tot_g is None and m.doacao_tampinhas > 0:
            tot_g = int(Decimal(str(m.doacao_tampinhas)) * Decimal("1000"))

        if tot_g and tot_g > 0:
            d_membro = Decimal(tot_g) / Decimal("1000")
            s_membro = f"{d_membro:.3f}".rstrip("0").rstrip(".")
            if not s_membro or s_membro == "-0":
                s_membro = "0"
            ranking.append({
                "usuario": m,
                "matricula": m.matricula,
                "total_gramas": tot_g,
                "total_kg": d_membro,
                "total_formatado": f"{s_membro}Kg",
            })

    # Ordenação decrescente de doações, desempate por matrícula crescente
    ranking.sort(key=lambda x: (-x["total_gramas"], x["matricula"]))

    primeiro = ranking[0] if len(ranking) > 0 else None
    segundo = ranking[1] if len(ranking) > 1 else None
    terceiro = ranking[2] if len(ranking) > 2 else None

    demais_participantes = []
    for idx, item in enumerate(ranking[3:], start=4):
        item_com_posicao = dict(item)
        item_com_posicao["posicao"] = idx
        demais_participantes.append(item_com_posicao)

    return render(request, "tampinhas.html", {
        "usuario": usuario,
        "total_geral_kg": total_geral_kg,
        "progresso_porcentagem": progresso_porcentagem,
        "progresso_porcentagem_css": f"{progresso_porcentagem:.2f}",
        "meta_kg": meta_kg,
        "meta_kg_formatada": meta_kg_formatada,
        "primeiro": primeiro,
        "segundo": segundo,
        "terceiro": terceiro,
        "demais_participantes": demais_participantes,
        "total_participantes": len(ranking),
        "pagina_ativa": "tampinhas",
    })


def criar_tarefa(request):
    usuario = usuario_logado(request)
    if usuario is None:
        return redirect("login")
    if not (usuario.eh_administrador() or usuario.sub_lider):
        if request.method == "POST":
            definir_mensagem(request, messages.error, "Apenas o líder ou os sub-líderes podem criar tarefas.")
        return redirect_autenticado(request, "painel_administrativo")
    if request.method == "POST":
        tipo = request.POST.get("tipo", "fixa")
        titulo = request.POST.get("titulo", "").strip()
        try:
            limite = int(request.POST.get("limite_participantes", 2))
        except (TypeError, ValueError):
            limite = 0

        if not titulo:
            definir_mensagem(request, messages.error, "Informe o título da tarefa.")
            return redirect_autenticado(request, "painel_administrativo")
        if len(titulo) > 100:
            definir_mensagem(request, messages.error, "O título da tarefa deve ter no máximo 100 caracteres.")
            return redirect_autenticado(request, "painel_administrativo")
        if tipo not in {"fixa", "prolongada"}:
            definir_mensagem(request, messages.error, "Selecione um tipo de tarefa válido (Rápida ou Prolongada).")
            return redirect_autenticado(request, "painel_administrativo")
        if limite < 1:
            definir_mensagem(request, messages.error, "O limite de participantes deve ser de pelo menos 1 pessoa.")
            return redirect_autenticado(request, "painel_administrativo")

        area_tarefa = (usuario.sublider_de or request.POST.get("area", "") or "Cenário").strip()
        tarefa = Tarefa(
            titulo=titulo,
            tipo=tipo,
            descricao=request.POST.get("descricao", "").strip(),
            limite_participantes=limite,
            criada_por=usuario,
            area=area_tarefa
        )
        if tipo == "fixa":
            tarefa.data = request.POST.get("data") or None
            tarefa.horario = request.POST.get("horario") or None
        else:
            tarefa.data_inicio = request.POST.get("data_inicio") or None
            tarefa.data_fim = request.POST.get("data_fim") or None
            if tarefa.data_inicio and tarefa.data_fim and tarefa.data_fim < tarefa.data_inicio:
                definir_mensagem(request, messages.error, "A data de término (prazo) não pode ser anterior à data inicial.")
                return redirect_autenticado(request, "painel_administrativo")
        if "imagem" in request.FILES:
            img_ok, img_erro = validar_e_sanitizar_imagem(request.FILES["imagem"])
            if not img_ok:
                definir_mensagem(request, messages.error, img_erro)
                return redirect_autenticado(request, "painel_administrativo")
            tarefa.imagem = request.FILES["imagem"]
        tarefa.save()
        ParticipacaoTarefa.objects.get_or_create(usuario=usuario, tarefa=tarefa)
        definir_mensagem(request, messages.success, f"Tarefa \"{titulo}\" criada com sucesso!")
    return redirect_autenticado(request, "painel_administrativo")


def editar_tarefa(request, id_tarefa):
    usuario = usuario_logado(request)
    if usuario is None:
        return redirect("login")
    if not (usuario.eh_administrador() or usuario.sub_lider):
        definir_mensagem(request, messages.error, "Apenas o líder ou os sub-líderes podem editar tarefas.")
        return redirect_autenticado(request, "painel_administrativo")
    if usuario.eh_administrador():
        tarefa = get_object_or_404(Tarefa, id=id_tarefa)
    else:
        tarefa = get_object_or_404(Tarefa, id=id_tarefa, area=usuario.sublider_de)
    if not mesma_diretoria_usuarios(usuario, tarefa.criada_por):
        definir_mensagem(request, messages.error, "Você não possui permissão para editar tarefas de outra diretoria.")
        return redirect_autenticado(request, "painel_administrativo")
    if request.method == "POST":
        tipo = request.POST.get("tipo", tarefa.tipo)
        titulo = request.POST.get("titulo", "").strip()
        try:
            limite = int(request.POST.get("limite_participantes", 2))
        except (TypeError, ValueError):
            limite = 0

        if not titulo:
            definir_mensagem(request, messages.error, "Informe o título da tarefa.")
            return redirect_autenticado(request, "painel_administrativo")
        if len(titulo) > 100:
            definir_mensagem(request, messages.error, "O título da tarefa deve ter no máximo 100 caracteres.")
            return redirect_autenticado(request, "painel_administrativo")
        if tipo not in {"fixa", "prolongada"}:
            definir_mensagem(request, messages.error, "Selecione um tipo de tarefa válido (Rápida ou Prolongada).")
            return redirect_autenticado(request, "painel_administrativo")
        if limite < 1:
            definir_mensagem(request, messages.error, "O limite de participantes deve ser de pelo menos 1 pessoa.")
            return redirect_autenticado(request, "painel_administrativo")

        tarefa.titulo = titulo
        tarefa.tipo = tipo
        tarefa.descricao = request.POST.get("descricao", "").strip()
        tarefa.limite_participantes = limite
        if tipo == "fixa":
            tarefa.data = request.POST.get("data") or None
            tarefa.horario = request.POST.get("horario") or None
            tarefa.data_inicio = None
            tarefa.data_fim = None
        else:
            tarefa.data_inicio = request.POST.get("data_inicio") or None
            tarefa.data_fim = request.POST.get("data_fim") or None
            tarefa.data = None
            tarefa.horario = None
            if tarefa.data_inicio and tarefa.data_fim and tarefa.data_fim < tarefa.data_inicio:
                definir_mensagem(request, messages.error, "A data de término (prazo) não pode ser anterior à data inicial.")
                return redirect_autenticado(request, "painel_administrativo")
        if "imagem" in request.FILES:
            img_ok, img_erro = validar_e_sanitizar_imagem(request.FILES["imagem"])
            if not img_ok:
                definir_mensagem(request, messages.error, img_erro)
                return redirect_autenticado(request, "painel_administrativo")
            tarefa.imagem = request.FILES["imagem"]
        tarefa.save()
        definir_mensagem(request, messages.success, f"Tarefa \"{titulo}\" atualizada com sucesso.")
        return redirect_autenticado(request, "painel_administrativo")
    return render(request, "editar_tarefa.html", {"usuario": usuario, "tarefa": tarefa})


def encerrar_tarefa(request, id_tarefa):
    usuario = usuario_logado(request)
    if usuario is None:
        return redirect("login")
    if not usuario.tem_acesso_painel():
        if request.method == "POST":
            definir_mensagem(request, messages.error, "Você não possui permissão para encerrar tarefas.")
        return redirect_autenticado(request, "painel_administrativo")
    if request.method == "POST":
        if usuario.eh_administrador():
            tarefa = get_object_or_404(Tarefa, id=id_tarefa)
        else:
            tarefa = get_object_or_404(Tarefa, id=id_tarefa, area=usuario.sublider_de)
        if not mesma_diretoria_usuarios(usuario, tarefa.criada_por):
            definir_mensagem(request, messages.error, "Você não possui permissão para encerrar tarefas de outra diretoria.")
            return redirect_autenticado(request, "painel_administrativo")
        tarefa.encerrada = True
        tarefa.save(update_fields=["encerrada"])
        definir_mensagem(request, messages.success, f"Tarefa \"{tarefa.titulo}\" encerrada com sucesso.")
    return redirect_autenticado(request, "painel_administrativo")


def excluir_tarefa_concluida(request, id_tarefa):
    usuario = usuario_logado(request)
    if usuario is None:
        return redirect("login")
    if not usuario.tem_acesso_painel():
        if request.method == "POST":
            definir_mensagem(request, messages.error, "Você não possui permissão para excluir tarefas.")
        return redirect_autenticado(request, "feed")

    if request.method == "POST":
        tarefa = get_object_or_404(Tarefa, id=id_tarefa)
        pode_gerenciar = (
            mesma_diretoria_usuarios(usuario, tarefa.criada_por)
            and (
                usuario.eh_administrador()
                or (usuario.sub_lider and usuario.sublider_de == tarefa.area)
                or tarefa.eh_criador(usuario)
            )
        )
        if not pode_gerenciar:
            definir_mensagem(request, messages.error, "Você só pode excluir tarefas concluídas da sua própria diretoria/área.")
            return redirect_autenticado(request, "painel_administrativo")

        if not (tarefa.encerrada or tarefa.concluida):
            definir_mensagem(
                request,
                messages.error,
                f"A tarefa \"{tarefa.titulo}\" ainda está ativa. Encerre ou conclua a tarefa antes de excluí-la."
            )
            origem = request.POST.get("origem", "").strip()
            if origem == "minhas_tarefas":
                return redirect_autenticado(request, "minhas_tarefas", nome_area=tarefa.area)
            return redirect_autenticado(request, "painel_administrativo")

        titulo_tarefa = tarefa.titulo
        area_tarefa = tarefa.area
        origem = request.POST.get("origem", "").strip()
        tarefa.delete()
        definir_mensagem(request, messages.success, f"Tarefa concluída \"{titulo_tarefa}\" excluída com sucesso.")
        if origem == "minhas_tarefas" and area_tarefa:
            return redirect_autenticado(request, "minhas_tarefas", nome_area=area_tarefa)

    return redirect_autenticado(request, "painel_administrativo")


def pagina_area(request, nome_area):
    usuario = usuario_logado(request)
    if usuario is None:
        return redirect("login")
    if not usuario.tem_acesso_area(nome_area):
        return redirect_autenticado(request, "feed")
    if request.GET.get("aba") == "chat":
        return chat_area(request, nome_area)
    ids_concluidos = ConclusaoTarefa.objects.filter(usuario=usuario).values_list("tarefa_id", flat=True)
    tarefas_base = filtrar_qs_diretoria(
        Tarefa.objects.filter(area=nome_area),
        usuario,
        "criada_por__diretoria",
    )
    if usuario.eh_administrador():
        tarefas = tarefas_base.prefetch_related("participacoes").order_by("-criada_em")
    else:
        tarefas = tarefas_base.filter(encerrada=False).exclude(id__in=ids_concluidos).prefetch_related("participacoes").order_by("-criada_em")
    
    participando = ParticipacaoTarefa.objects.filter(usuario=usuario).values_list("tarefa_id", flat=True)
    return render(request, "area.html", {
        "usuario": usuario,
        "nome_area": nome_area,
        "tarefas": tarefas,
        "participando": list(participando),
        "ids_concluidos": list(ids_concluidos),
        "area_ativa": nome_area,
        "pagina_ativa": "",
    })


def chat_area(request, nome_area):
    usuario = usuario_logado(request)
    if usuario is None:
        return redirect("login")
    if nome_area not in TODAS_AREAS or not usuario.tem_acesso_area(nome_area):
        return redirect_autenticado(request, "feed")

    mensagens = (
        filtrar_qs_diretoria(
            MensagemArea.objects.filter(area=nome_area),
            usuario,
            "usuario__diretoria",
        )
        .select_related("usuario", "resposta_a", "resposta_a__usuario")
        .prefetch_related("curtidas")
        .order_by("-criada_em")
    )
    curtidas = set(
        CurtidaMensagemArea.objects.filter(
            usuario=usuario, mensagem__area=nome_area
        ).values_list("mensagem_id", flat=True)
    )
    return render(request, "chat_area.html", {
        "usuario": usuario,
        "nome_area": nome_area,
        "mensagens": mensagens,
        "curtidas": curtidas,
        "area_ativa": nome_area,
        "pagina_ativa": "",
    })


def publicar_chat_area(request, nome_area):
    usuario = usuario_logado(request)
    if usuario is None:
        return redirect("login")
    if nome_area not in TODAS_AREAS or not usuario.tem_acesso_area(nome_area):
        if request.method == "POST":
            definir_mensagem(request, messages.error, f"Você não tem permissão para enviar mensagens no chat da área {nome_area}.")
        return redirect_autenticado(request, "feed")

    if request.method == "POST":
        texto = request.POST.get("texto", "").strip()
        resposta_a_id = (request.POST.get("resposta_a") or "").strip()
        resposta_a_obj = None
        if resposta_a_id.isdigit():
            resposta_a_obj = filtrar_qs_diretoria(
                MensagemArea.objects.filter(id=int(resposta_a_id), area=nome_area),
                usuario,
                "usuario__diretoria",
            ).first()
        if not texto:
            definir_mensagem(request, messages.error, "Digite uma mensagem antes de publicar no chat da área.")
        elif len(texto) > 300:
            definir_mensagem(request, messages.error, f"A mensagem excede o limite de 300 caracteres ({len(texto)}/300).")
        else:
            MensagemArea.objects.create(
                usuario=usuario,
                area=nome_area,
                texto=texto,
                resposta_a=resposta_a_obj,
            )
    return redirect_autenticado(request, "chat_area", nome_area=nome_area)


def curtir_mensagem_area(request, id_mensagem):
    if request.method != "POST":
        return JsonResponse({"erro": "Método inválido. Use uma requisição POST."}, status=405)
    usuario = usuario_logado(request)
    if usuario is None:
        return JsonResponse({"erro": "Sua sessão expirou. Faça login novamente."}, status=401)
    mensagem = get_object_or_404(MensagemArea, id=id_mensagem)
    if not usuario.tem_acesso_area(mensagem.area) or not mesma_diretoria_usuarios(usuario, mensagem.usuario):
        return JsonResponse({"erro": f"Você não pertence à área {mensagem.area} desta diretoria."}, status=403)

    curtida = CurtidaMensagemArea.objects.filter(usuario=usuario, mensagem=mensagem)
    if curtida.exists():
        curtida.delete()
        curtido = False
    else:
        CurtidaMensagemArea.objects.create(usuario=usuario, mensagem=mensagem)
        curtido = True
    return JsonResponse({"curtido": curtido, "curtidas": mensagem.total_curtidas()})


def editar_mensagem_area(request, id_mensagem):
    usuario = usuario_logado(request)
    if usuario is None:
        return redirect("login")
    mensagem = get_object_or_404(MensagemArea.objects.select_related("usuario"), id=id_mensagem)
    nome_area = mensagem.area
    if not usuario.tem_acesso_area(nome_area) or not mesma_diretoria_usuarios(usuario, mensagem.usuario):
        return redirect_autenticado(request, "feed")
    if request.method == "POST":
        if mensagem.usuario_id != usuario.id:
            definir_mensagem(request, messages.error, "Você só pode editar as suas próprias mensagens.")
            return redirect_autenticado(request, "chat_area", nome_area=nome_area)
        texto = request.POST.get("texto", "").strip()
        if not texto:
            definir_mensagem(request, messages.error, "O texto da mensagem não pode ficar vazio.")
        elif len(texto) > LIMITE_CARACTERES_CHAT:
            definir_mensagem(
                request,
                messages.error,
                f"A mensagem excede o limite de {LIMITE_CARACTERES_CHAT} caracteres ({len(texto)}/{LIMITE_CARACTERES_CHAT}).",
            )
        else:
            mensagem.texto = texto
            mensagem.save(update_fields=["texto"])
            definir_mensagem(request, messages.success, "Mensagem atualizada com sucesso.")
    return redirect_autenticado(request, "chat_area", nome_area=nome_area)


def excluir_mensagem_area(request, id_mensagem):
    usuario = usuario_logado(request)
    if usuario is None:
        return redirect("login")
    mensagem = get_object_or_404(MensagemArea, id=id_mensagem)
    nome_area = mensagem.area
    if not usuario.tem_acesso_area(nome_area) or not mesma_diretoria_usuarios(usuario, mensagem.usuario):
        if request.method == "POST":
            definir_mensagem(request, messages.error, f"Você não faz parte da área {nome_area} desta diretoria.")
        return redirect_autenticado(request, "feed")
    if request.method == "POST":
        pode_excluir = (
            mensagem.usuario_id == usuario.id
            or usuario.eh_administrador()
            or (usuario.sub_lider and usuario.sublider_de == nome_area)
        )
        if pode_excluir:
            mensagem.delete()
            definir_mensagem(request, messages.success, "Mensagem excluída do chat.")
        else:
            definir_mensagem(request, messages.error, "Você não tem permissão para excluir esta mensagem.")
    return redirect_autenticado(request, "chat_area", nome_area=nome_area)


def participar_tarefa(request, id_tarefa):
    usuario = usuario_logado(request)
    if usuario is None:
        return redirect("login")
    if request.method == "POST":
        tarefa = get_object_or_404(Tarefa, id=id_tarefa)
        if not usuario.tem_acesso_area(tarefa.area) or not mesma_diretoria_usuarios(usuario, tarefa.criada_por):
            definir_mensagem(request, messages.error, f"Você precisa fazer parte da área {tarefa.area} da sua diretoria para participar desta tarefa.")
            return redirect_autenticado(request, "feed")
        if tarefa.encerrada:
            definir_mensagem(request, messages.error, f"A tarefa \"{tarefa.titulo}\" já foi encerrada e não aceita novos participantes.")
            return redirect_autenticado(request, "pagina_area", nome_area=tarefa.area)
        if tarefa.eh_criador(usuario):
            # O criador já participa da própria tarefa; não entra na contagem
            definir_mensagem(request, messages.info, "Como responsável pela tarefa, você já acompanha sua execução.")
            return redirect_autenticado(request, "pagina_area", nome_area=tarefa.area)
        ja_inscrito = ParticipacaoTarefa.objects.filter(usuario=usuario, tarefa=tarefa).exists()
        if ja_inscrito:
            definir_mensagem(request, messages.info, f"Você já está participando da tarefa \"{tarefa.titulo}\".")
        elif not tarefa.tem_vaga():
            definir_mensagem(request, messages.error, f"As vagas para a tarefa \"{tarefa.titulo}\" já foram preenchidas.")
        else:
            ParticipacaoTarefa.objects.create(usuario=usuario, tarefa=tarefa)
            definir_mensagem(request, messages.success, f"Você entrou na tarefa \"{tarefa.titulo}\"!")
        return redirect_autenticado(request, "pagina_area", nome_area=tarefa.area)


def cancelar_participacao(request, id_tarefa):
    usuario = usuario_logado(request)
    if usuario is None:
        return redirect("login")
    if request.method == "POST":
        tarefa = get_object_or_404(Tarefa, id=id_tarefa)
        if not mesma_diretoria_usuarios(usuario, tarefa.criada_por):
            return redirect_autenticado(request, "feed")
        if tarefa.encerrada:
            definir_mensagem(request, messages.error, "Não é possível cancelar a participação em uma tarefa já encerrada.")
        elif tarefa.eh_criador(usuario):
            definir_mensagem(request, messages.error, "O criador da tarefa não pode cancelar a própria participação.")
        else:
            ParticipacaoTarefa.objects.filter(usuario=usuario, tarefa=tarefa).delete()
            definir_mensagem(request, messages.info, f"Participação na tarefa \"{tarefa.titulo}\" cancelada.")
        return redirect_autenticado(request, "pagina_area", nome_area=tarefa.area)


# ─── Minhas Tarefas ───────────────────────────────────────────────────────────

def minhas_tarefas(request, nome_area=None, id_tarefa=None):
    usuario = usuario_logado(request)
    if usuario is None:
        return redirect("login")
    if not nome_area:
        areas = usuario.get_areas_sidebar()
        if areas:
            return redirect_autenticado(request, "minhas_tarefas", nome_area=areas[0])
        return redirect_autenticado(request, "feed")
    if not usuario.tem_acesso_area(nome_area):
        return redirect_autenticado(request, "feed")

    # Tarefas em que o usuário participa + tarefas que ele mesmo criou
    # (o sub-líder já participa de todas as que cria).
    todas = filtrar_qs_diretoria(
        Tarefa.objects.filter(
            Q(participacoes__usuario=usuario) | Q(criada_por=usuario)
        ).filter(area=nome_area),
        usuario,
        "criada_por__diretoria",
    ).distinct().order_by("-criada_em")

    # IDs das tarefas que o usuário já concluiu
    ids_concluidos = set(ConclusaoTarefa.objects.filter(
        usuario=usuario
    ).values_list("tarefa_id", flat=True))

    tarefas = []             # em andamento
    tarefas_finalizadas = [] # concluídas por mim ou encerradas
    for t in todas:
        if t.encerrada or (t.id in ids_concluidos and not t.eh_criador(usuario)):
            tarefas_finalizadas.append(t)
        else:
            tarefas.append(t)

    tarefa_selecionada = None
    aba_ativa = request.GET.get("aba", "detalhes")
    observacoes = []
    conclusao = None
    conclusoes_tarefa = None
    ja_concluiu = False
    eh_criador = False

    if id_tarefa:
        tarefa_selecionada = get_object_or_404(Tarefa, id=id_tarefa)
        if not mesma_diretoria_usuarios(usuario, tarefa_selecionada.criada_por):
            return redirect_autenticado(request, "minhas_tarefas", nome_area=nome_area)
        eh_criador = tarefa_selecionada.eh_criador(usuario) or usuario.eh_administrador() or (usuario.sub_lider and usuario.sublider_de == nome_area)
        # O usuário precisa participar da tarefa ou ter privilégio de liderança/criação
        participa = ParticipacaoTarefa.objects.filter(usuario=usuario, tarefa=tarefa_selecionada).exists()
        if not (participa or eh_criador or usuario.eh_administrador()):
            return redirect_autenticado(request, "minhas_tarefas", nome_area=nome_area)
        if eh_criador and aba_ativa == "concluir":
            aba_ativa = "detalhes"
        observacoes = tarefa_selecionada.observacoes.select_related("usuario").order_by("criada_em")
        conclusao = ConclusaoTarefa.objects.filter(usuario=usuario, tarefa=tarefa_selecionada).first()
        conclusoes_tarefa = tarefa_selecionada.conclusoes.select_related("usuario").order_by("criada_em")
        ja_concluiu = conclusao is not None

    # Determinar área ativa para sidebar
    area_ativa = nome_area

    # Primeira área do usuário para o link "Tarefas" quando não há tarefa selecionada
    primeira_area = nome_area

    return render(request, "minhas_tarefas.html", {
        "usuario": usuario,
        "tarefas": tarefas,
        "tarefas_finalizadas": tarefas_finalizadas,
        "tarefa_selecionada": tarefa_selecionada,
        "eh_criador": eh_criador,
        "aba_ativa": aba_ativa,
        "observacoes": observacoes,
        "conclusao": conclusao,
        "conclusoes_tarefa": conclusoes_tarefa,
        "ja_concluiu": ja_concluiu,
        "area_ativa": area_ativa,
        "primeira_area": primeira_area,
    })


def adicionar_observacao(request, nome_area, id_tarefa):
    usuario = usuario_logado(request)
    if usuario is None:
        return redirect("login")
    if request.method == "POST":
        tarefa = get_object_or_404(Tarefa, id=id_tarefa)
        if not mesma_diretoria_usuarios(usuario, tarefa.criada_por):
            return redirect_autenticado(request, "minhas_tarefas", nome_area=nome_area)
        participa = ParticipacaoTarefa.objects.filter(usuario=usuario, tarefa=tarefa).exists()
        if not participa and not tarefa.eh_criador(usuario) and not usuario.eh_administrador():
            definir_mensagem(request, messages.error, "Apenas participantes ou o responsável pela tarefa podem adicionar observações.")
            return redirect_autenticado(request, "minhas_tarefas", nome_area=nome_area)
        texto = request.POST.get("texto", "").strip()
        if not texto:
            definir_mensagem(request, messages.error, "Digite o texto da observação antes de enviar.")
        elif len(texto) > 2000:
            definir_mensagem(request, messages.error, "A observação deve ter no máximo 2000 caracteres.")
        else:
            ObservacaoTarefa.objects.create(usuario=usuario, tarefa=tarefa, texto=texto)
        return redirect_autenticado(request, f"/area/{nome_area}/minhas-tarefas/{id_tarefa}/?aba=observacao")


def editar_observacao(request, nome_area, id_tarefa, id_obs):
    usuario = usuario_logado(request)
    if usuario is None:
        return redirect("login")
    if request.method == "POST":
        tarefa = get_object_or_404(Tarefa, id=id_tarefa)
        obs = get_object_or_404(ObservacaoTarefa, id=id_obs, tarefa=tarefa)
        if not mesma_diretoria_usuarios(usuario, tarefa.criada_por) or obs.usuario_id != usuario.id:
            definir_mensagem(request, messages.error, "Você só pode editar as suas próprias observações.")
            return redirect_autenticado(request, f"/area/{nome_area}/minhas-tarefas/{id_tarefa}/?aba=observacao")
        texto = request.POST.get("texto", "").strip()
        if not texto:
            definir_mensagem(request, messages.error, "O texto da observação não pode ficar vazio.")
        elif len(texto) > 2000:
            definir_mensagem(request, messages.error, "A observação deve ter no máximo 2000 caracteres.")
        else:
            obs.texto = texto
            obs.save(update_fields=["texto"])
            definir_mensagem(request, messages.success, "Observação atualizada com sucesso.")
    return redirect_autenticado(request, f"/area/{nome_area}/minhas-tarefas/{id_tarefa}/?aba=observacao")


def concluir_tarefa_usuario(request, nome_area, id_tarefa):
    usuario = usuario_logado(request)
    if usuario is None:
        return redirect("login")
    if request.method == "POST":
        tarefa = get_object_or_404(Tarefa, id=id_tarefa)
        if not mesma_diretoria_usuarios(usuario, tarefa.criada_por):
            return redirect_autenticado(request, "minhas_tarefas", nome_area=nome_area)
        participa = ParticipacaoTarefa.objects.filter(usuario=usuario, tarefa=tarefa).exists()
        if tarefa.eh_criador(usuario):
            definir_mensagem(request, messages.error, "O criador da tarefa não registra entrega individual; acompanhe as conclusões na aba Detalhes.")
            return redirect_autenticado(request, "minhas_tarefas", nome_area=nome_area)
        if not participa:
            definir_mensagem(request, messages.error, "Você precisa participar da tarefa para enviá-la como concluída.")
            return redirect_autenticado(request, "minhas_tarefas", nome_area=nome_area)

        conclusao_existente = ConclusaoTarefa.objects.filter(usuario=usuario, tarefa=tarefa).first()
        if tarefa.encerrada and not conclusao_existente:
            definir_mensagem(request, messages.error, "Esta tarefa já foi encerrada e não aceita novas conclusões.")
            return redirect_autenticado(request, "minhas_tarefas", nome_area=nome_area)

        comentario = request.POST.get("comentario", "").strip()
        if "imagem" in request.FILES:
            img_ok, img_erro = validar_e_sanitizar_imagem(request.FILES["imagem"])
            if not img_ok:
                definir_mensagem(request, messages.error, img_erro)
                return redirect_autenticado(request, f"/area/{nome_area}/minhas-tarefas/{id_tarefa}/?aba=concluir")
        conclusao, criada = ConclusaoTarefa.objects.get_or_create(
            usuario=usuario, tarefa=tarefa,
            defaults={"comentario": comentario}
        )
        if not criada and comentario:
            conclusao.comentario = comentario
        if "imagem" in request.FILES:
            conclusao.imagem = request.FILES["imagem"]
        conclusao.save()

        total_concluidos = tarefa.total_conclusoes()
        if total_concluidos >= tarefa.limite_participantes:
            tarefa.encerrada = True
            tarefa.concluida = True
            tarefa.save(update_fields=["encerrada", "concluida"])

        definir_mensagem(request, messages.success, "Conclusão da tarefa enviada com sucesso!")
        return redirect_autenticado(request, f"/area/{nome_area}/minhas-tarefas/{id_tarefa}/?aba=detalhes")


# ─── Gerenciamento de áreas ──────────────────────────────────────────────────

def nova_area(request):
    usuario = usuario_logado(request)
    if usuario is None:
        return redirect("login")
    areas_usuario = set(usuario.get_areas_list())
    solicitacoes_pendentes = set(SolicitacaoArea.objects.filter(usuario=usuario).values_list("area", flat=True))
    areas_com_status = []
    ordem_figma = ["Cenário", "Staff", "Dança", "Figurino", "Sonoplastia", "Tampinhas", "Roteiro"]
    for area in ordem_figma:
        if usuario.eh_administrador() or area in areas_usuario:
            status = "membro"
        elif area in solicitacoes_pendentes:
            status = "pendente"
        else:
            status = "livre"
        areas_com_status.append({
            "nome": area,
            "descricao": AREAS_INFO.get(area, ""),
            "icone": AREAS_ICONES.get(area, "imgs/icone-area.png"),
            "status": status,
        })
    return render(request, "nova_area.html", {
        "usuario": usuario,
        "areas_com_status": areas_com_status,
        "pagina_ativa": "nova_area",
        "area_ativa": "",
    })


def solicitar_area(request, nome_area):
    usuario = usuario_logado(request)
    if usuario is None:
        return redirect("login")
    if request.method == "POST" and nome_area in TODAS_AREAS:
        areas_usuario = usuario.get_areas_list()
        # FA04: Participante já pertence à área
        if nome_area in areas_usuario:
            definir_mensagem(request, messages.info, f"Você já participa da área {nome_area}.")
            return redirect_autenticado(request, "nova_area")
        # FA03: Solicitação já existente
        ja_solicitado = SolicitacaoArea.objects.filter(usuario=usuario, area=nome_area).exists()
        if ja_solicitado:
            definir_mensagem(request, messages.info, f"Você já possui uma solicitação pendente para {nome_area}.")
            return redirect_autenticado(request, "nova_area")
        # Fluxo Principal: Registra solicitação
        SolicitacaoArea.objects.create(usuario=usuario, area=nome_area)
        definir_mensagem(request, messages.success, f"Solicitação para {nome_area} enviada com sucesso!")
    return redirect_autenticado(request, "nova_area")


def cancelar_solicitacao_area(request, nome_area):
    usuario = usuario_logado(request)
    if usuario is None:
        return redirect("login")
    if request.method == "POST":
        # FA01: Cancelar Solicitação
        SolicitacaoArea.objects.filter(usuario=usuario, area=nome_area).delete()
        definir_mensagem(request, messages.success, f"Solicitação para {nome_area} cancelada.")
    return redirect_autenticado(request, "nova_area")


def sair_da_area(request, nome_area):
    usuario = usuario_logado(request)
    if usuario is None:
        return redirect("login")
    if request.method == "POST":
        # Validação obrigatória da matrícula para confirmar saída
        matricula_digitada = request.POST.get("matricula_confirmacao", "").strip()
        if matricula_digitada != usuario.matricula:
            definir_mensagem(request, messages.error, "Matrícula incorreta. A confirmação para sair da área falhou.")
            return redirect_autenticado(request, "nova_area")

        areas = usuario.get_areas_list()
        if nome_area in areas:
            areas.remove(nome_area)
            usuario.areas = ",".join(areas)
            if usuario.sub_lider and usuario.sublider_de == nome_area:
                usuario.sub_lider = False
                usuario.sublider_de = None
            usuario.save()
            definir_mensagem(request, messages.success, f"Você saiu da área {nome_area} com sucesso.")
        elif usuario.eh_administrador():
            definir_mensagem(request, messages.info, "Como líder geral, seu acesso é total.")
    return redirect_autenticado(request, "nova_area")


def aprovar_solicitacao_area(request, id_solicitacao):
    usuario = usuario_logado(request)
    if usuario is None:
        return redirect("login")
    if not usuario.tem_acesso_painel():
        if request.method == "POST":
            definir_mensagem(request, messages.error, "Você não tem acesso a esta funcionalidade.")
        return redirect_autenticado(request, "feed")
    if request.method == "POST":
        sol = get_object_or_404(SolicitacaoArea, id=id_solicitacao)
        if not mesma_diretoria_usuarios(usuario, sol.usuario):
            definir_mensagem(request, messages.error, "Você não tem permissão para gerenciar solicitações de outra diretoria.")
            return redirect_autenticado(request, "painel_administrativo")
        if not (usuario.eh_administrador() or (usuario.sub_lider and usuario.sublider_de == sol.area)):
            definir_mensagem(request, messages.error, "Você não tem permissão para aprovar membros nesta área.")
            return redirect_autenticado(request, "painel_administrativo")
        membro = sol.usuario
        areas = membro.get_areas_list()
        if sol.area not in areas:
            areas.append(sol.area)
            membro.areas = ",".join(areas)
            membro.save()
        sol.delete()
        definir_mensagem(request, messages.success, f"Solicitação de {membro.matricula} para {sol.area} aprovada!")
    return redirect_autenticado(request, "painel_administrativo")


def recusar_solicitacao_area(request, id_solicitacao):
    usuario = usuario_logado(request)
    if usuario is None:
        return redirect("login")
    if not usuario.tem_acesso_painel():
        if request.method == "POST":
            definir_mensagem(request, messages.error, "Você não tem acesso a esta funcionalidade.")
        return redirect_autenticado(request, "feed")
    if request.method == "POST":
        sol = get_object_or_404(SolicitacaoArea, id=id_solicitacao)
        if not mesma_diretoria_usuarios(usuario, sol.usuario):
            definir_mensagem(request, messages.error, "Você não tem permissão para gerenciar solicitações de outra diretoria.")
            return redirect_autenticado(request, "painel_administrativo")
        if not (usuario.eh_administrador() or (usuario.sub_lider and usuario.sublider_de == sol.area)):
            definir_mensagem(request, messages.error, "Você não tem permissão para recusar solicitações desta área.")
            return redirect_autenticado(request, "painel_administrativo")
        sol.delete()
        definir_mensagem(request, messages.success, "Solicitação de área recusada.")
    return redirect_autenticado(request, "painel_administrativo")


def aprovar_membro(request, id_usuario):
    usuario = usuario_logado(request)
    if usuario is None:
        return redirect("login")
    if not usuario.eh_administrador():
        if request.method == "POST":
            definir_mensagem(request, messages.error, "Apenas o líder geral pode aprovar novos participantes.")
        return redirect_autenticado(request, "painel_administrativo")
    if request.method == "POST":
        membro = get_object_or_404(Usuario, id=id_usuario)
        if not mesma_diretoria_usuarios(usuario, membro):
            definir_mensagem(request, messages.error, "Você só pode aprovar participantes da sua própria diretoria.")
            return redirect_autenticado(request, "painel_administrativo")
        if membro.aprovado:
            definir_mensagem(request, messages.info, f"O participante {membro.matricula} já está aprovado.")
            return redirect_autenticado(request, "painel_administrativo")
        # Ao aprovar o membro no sistema, cria as solicitações para os sub-líderes
        # das áreas selecionadas no cadastro. O membro tem acesso inicial apenas ao
        # feed e ao editar áreas, desbloqueando as áreas conforme cada sub-líder aprovar.
        areas_iniciais = membro.get_areas_list()
        for area_nome in areas_iniciais:
            if area_nome in TODAS_AREAS:
                SolicitacaoArea.objects.get_or_create(usuario=membro, area=area_nome)
        membro.areas = ""
        membro.aprovado = True
        membro.save()
        definir_mensagem(request, messages.success, f"Membro {membro.matricula} aprovado no sistema! Solicitações de área enviadas para os sub-líderes.")
    return redirect_autenticado(request, "painel_administrativo")


def recusar_membro(request, id_usuario):
    usuario = usuario_logado(request)
    if usuario is None:
        return redirect("login")
    if not usuario.eh_administrador():
        if request.method == "POST":
            definir_mensagem(request, messages.error, "Apenas o líder geral pode recusar participantes.")
        return redirect_autenticado(request, "painel_administrativo")
    if request.method == "POST":
        membro = get_object_or_404(Usuario, id=id_usuario)
        if not mesma_diretoria_usuarios(usuario, membro):
            definir_mensagem(request, messages.error, "Você só pode recusar participantes da sua própria diretoria.")
            return redirect_autenticado(request, "painel_administrativo")
        membro.delete()
        definir_mensagem(request, messages.success, "Cadastro do participante recusado.")
    return redirect_autenticado(request, "painel_administrativo")


def promover_sublider(request):
    usuario = usuario_logado(request)
    if usuario is None:
        return redirect("login")
    if not usuario.eh_administrador():
        if request.method == "POST":
            definir_mensagem(request, messages.error, "Apenas o líder geral pode promover sub-líderes.")
        return redirect_autenticado(request, "painel_administrativo")
    if request.method == "POST":
        matricula = request.POST.get("matricula", "").strip()
        area = request.POST.get("area", "").strip()

        if area not in TODAS_AREAS:
            definir_mensagem(request, messages.error, "Selecione uma área válida para promover o sub-líder.")
            return redirect_autenticado(request, "painel_administrativo")

        try:
            membro = Usuario.objects.get(matricula=matricula, aprovado=True)
        except Usuario.DoesNotExist:
            definir_mensagem(request, messages.error, f"Membro \"{matricula}\" não encontrado (ou ainda não aprovado).")
            return redirect_autenticado(request, "painel_administrativo")

        if not mesma_diretoria_usuarios(usuario, membro):
            definir_mensagem(request, messages.error, f"O membro \"{matricula}\" pertence a outra diretoria.")
            return redirect_autenticado(request, "painel_administrativo")

        if membro.eh_administrador():
            definir_mensagem(request, messages.error, "O líder não pode ser promovido a sub-líder.")
        elif membro.sub_lider:
            onde = f" de {membro.sublider_de}" if membro.sublider_de else ""
            definir_mensagem(
                request,
                messages.error,
                f"{membro.matricula} já é sub-líder{onde}. Cada membro só pode ser sub-líder "
                f"de uma área; remova o cargo atual antes de promovê-lo novamente."
            )
        else:
            qs_sublider = filtrar_qs_diretoria(
                Usuario.objects.filter(sub_lider=True, sublider_de=area),
                usuario,
                "diretoria",
            )
            sublider_existente = qs_sublider.first()
            if sublider_existente:
                definir_mensagem(request, messages.error, f"A área {area} já possui um sub-líder ({sublider_existente.matricula}).")
            else:
                areas_atuais = membro.get_areas_list()
                if area not in areas_atuais:
                    areas_atuais.append(area)
                membro.areas = ",".join(areas_atuais)
                membro.sub_lider = True
                membro.sublider_de = area
                membro.save()
                definir_mensagem(request, messages.success, f"{membro.matricula} agora é sub-líder de {area}.")
    return redirect_autenticado(request, "painel_administrativo")


def remover_sublider(request, id_usuario):
    usuario = usuario_logado(request)
    if usuario is None:
        return redirect("login")
    if not usuario.eh_administrador():
        if request.method == "POST":
            definir_mensagem(request, messages.error, "Apenas o líder geral pode remover sub-líderes.")
        return redirect_autenticado(request, "painel_administrativo")
    if request.method == "POST":
        membro = get_object_or_404(Usuario, id=id_usuario)
        if not mesma_diretoria_usuarios(usuario, membro):
            definir_mensagem(request, messages.error, "Você só pode gerenciar sub-líderes da sua própria diretoria.")
            return redirect_autenticado(request, "painel_administrativo")
        if not membro.eh_administrador():
            membro.sub_lider = False
            membro.sublider_de = None
            membro.save()
            definir_mensagem(request, messages.success, f"Cargo de sub-líder removido de {membro.matricula}.")
    return redirect_autenticado(request, "painel_administrativo")


def remover_membro(request, id_usuario):
    usuario = usuario_logado(request)
    if usuario is None:
        return redirect("login")
    if not usuario.tem_acesso_painel():
        if request.method == "POST":
            definir_mensagem(request, messages.error, "Você não possui permissão para remover membros.")
        return redirect_autenticado(request, "feed")
    if request.method == "POST":
        membro = get_object_or_404(Usuario, id=id_usuario)
        if not mesma_diretoria_usuarios(usuario, membro):
            definir_mensagem(request, messages.error, "Você só pode gerenciar membros da sua própria diretoria.")
            return redirect_autenticado(request, "painel_administrativo")
        if membro.eh_administrador():
            definir_mensagem(request, messages.error, "Não é permitido remover o líder geral.")
        elif usuario.eh_administrador():
            membro.delete()
            definir_mensagem(request, messages.success, "Membro removido com sucesso.")
        elif usuario.sub_lider and usuario.sublider_de:
            if membro.id == usuario.id:
                definir_mensagem(request, messages.error, "Para deixar a sua própria área, utilize a opção Sair da área.")
            else:
                areas_membro = membro.get_areas_list()
                if usuario.sublider_de not in areas_membro:
                    definir_mensagem(request, messages.error, "Você só pode remover membros vinculados à sua própria área.")
                else:
                    areas_membro.remove(usuario.sublider_de)
                    membro.areas = ",".join(areas_membro)
                    membro.save(update_fields=["areas"])
                    definir_mensagem(request, messages.success, f"Membro {membro.matricula} removido da área {usuario.sublider_de} com sucesso.")
    return redirect_autenticado(request, "painel_administrativo")



def ver_conclusao(request, id_tarefa):
    usuario = usuario_logado(request)
    if usuario is None:
        return redirect("login")
    try:
        tarefa = Tarefa.objects.get(id=id_tarefa)
    except Tarefa.DoesNotExist:
        definir_mensagem(request, messages.error, "Tarefa não encontrada.")
        return redirect_autenticado(request, "painel_administrativo" if usuario.eh_administrador() else "feed")

    if not mesma_diretoria_usuarios(usuario, tarefa.criada_por) or (tarefa.area and not usuario.tem_acesso_area(tarefa.area)):
        return redirect_autenticado(request, "painel_administrativo" if usuario.tem_acesso_painel() else "feed")

    area_nome = tarefa.area if tarefa.area else (usuario.sublider_de or "Cenário")
    conclusoes = ConclusaoTarefa.objects.filter(
        tarefa=tarefa
    ).select_related("usuario").order_by("criada_em")

    origem = request.GET.get("origem", "").strip()
    if origem == "minhas_tarefas" or (usuario.sub_lider and not origem and not usuario.eh_administrador()):
        url_voltar = f"/area/{area_nome}/minhas-tarefas/"
        nome_voltar = "Minhas Tarefas"
        aba_ativa_conclusao = "minhas_tarefas"
    elif origem == "painel" or (usuario.eh_administrador() and not origem):
        url_voltar = "/painel-administrativo/"
        nome_voltar = "Painel Administrativo"
        aba_ativa_conclusao = "tarefas"
    else:
        url_voltar = f"/area/{area_nome}/"
        nome_voltar = "Tarefas"
        aba_ativa_conclusao = "tarefas"

    token_aba = getattr(request, "_explicit_user_token", None) or gerar_token_usuario(usuario.id)
    if token_aba:
        url_voltar = anexar_token_em_url(url_voltar, token_aba)

    return render(request, "ver_conclusao.html", {
        "usuario": usuario,
        "tarefa": tarefa,
        "conclusoes": conclusoes,
        "area_ativa": area_nome,
        "url_voltar": url_voltar,
        "nome_voltar": nome_voltar,
        "aba_ativa_conclusao": aba_ativa_conclusao,
        "origem": origem,
    })


def status_tarefa(request, id_tarefa):
    usuario = usuario_logado(request)
    if usuario is None:
        return JsonResponse({"erro": "Sessão expirada."}, status=401)
    tarefa = get_object_or_404(Tarefa, id=id_tarefa)
    if not usuario.tem_acesso_area(tarefa.area) or not mesma_diretoria_usuarios(usuario, tarefa.criada_por):
        return JsonResponse({"erro": "Acesso negado."}, status=403)
    total_concluidos = tarefa.total_conclusoes()
    return JsonResponse({
        "concluidos": total_concluidos,
        "limite": tarefa.limite_participantes,
        "encerrada": tarefa.encerrada,
    })


# ─── Perfil de Usuário ───────────────────────────────────────────────────────

def meu_perfil(request):
    return ver_perfil(request, id_usuario=None)


def ver_perfil(request, id_usuario=None):
    usuario = usuario_logado(request)
    if usuario is None:
        return redirect("login")

    if id_usuario is None:
        perfil_usuario = usuario
    else:
        perfil_usuario = get_object_or_404(Usuario, id=id_usuario)
        if not mesma_diretoria_usuarios(usuario, perfil_usuario):
            definir_mensagem(request, messages.error, "Você só pode visualizar perfis de participantes da sua própria diretoria.")
            return redirect_autenticado(request, "feed")

    eh_proprio_perfil = (perfil_usuario.id == usuario.id)
    contribuicao_tampinhas_kg = perfil_usuario.total_tampinhas_formatado()
    contribuicao_tampinhas_gramas = perfil_usuario.total_tampinhas_gramas()
    total_doacoes_registradas = perfil_usuario.doacoes_tampinhas.count()

    if perfil_usuario.eh_administrador():
        lista_nomes_areas = list(TODAS_AREAS)
    else:
        lista_nomes_areas = perfil_usuario.get_areas_ordenadas()

    areas_perfil = [
        {
            "nome": area_nome,
            "icone": AREAS_ICONES.get(area_nome, "imgs/icone-area.png"),
            "eh_sublider": bool(perfil_usuario.sub_lider and perfil_usuario.sublider_de == area_nome),
        }
        for area_nome in lista_nomes_areas
    ]

    return render(request, "perfil.html", {
        "usuario": usuario,
        "perfil_usuario": perfil_usuario,
        "eh_proprio_perfil": eh_proprio_perfil,
        "contribuicao_tampinhas_kg": contribuicao_tampinhas_kg,
        "contribuicao_tampinhas_gramas": contribuicao_tampinhas_gramas,
        "total_doacoes_registradas": total_doacoes_registradas,
        "areas_perfil": areas_perfil,
        "pagina_ativa": "perfil" if eh_proprio_perfil else "",
        "area_ativa": "",
    })


def editar_perfil(request):
    usuario = usuario_logado(request)
    if usuario is None:
        return redirect("login")

    if request.method == "POST":
        nome = request.POST.get("nome", "").strip()
        bio = request.POST.get("bio", "").strip()
        remover_foto = request.POST.get("remover_foto") == "1"

        if not nome:
            definir_mensagem(request, messages.error, "O nome de exibição não pode ficar em branco.")
            return redirect_autenticado(request, "meu_perfil")
        if len(nome) > 100:
            definir_mensagem(request, messages.error, "O nome deve ter no máximo 100 caracteres.")
            return redirect_autenticado(request, "meu_perfil")
        if len(bio) > 500:
            definir_mensagem(request, messages.error, "A bio deve ter no máximo 500 caracteres.")
            return redirect_autenticado(request, "meu_perfil")

        if "foto" in request.FILES:
            img_ok, img_erro = validar_e_sanitizar_imagem(request.FILES["foto"])
            if not img_ok:
                definir_mensagem(request, messages.error, img_erro)
                return redirect_autenticado(request, "meu_perfil")

        usuario.nome = nome
        usuario.bio = bio
        if "foto" in request.FILES:
            usuario.foto = request.FILES["foto"]
        elif remover_foto:
            usuario.foto = None
        usuario.save()
        definir_mensagem(request, messages.success, "Perfil atualizado com sucesso!")

    return redirect_autenticado(request, "meu_perfil")


def sair(request):
    limpar_mensagens(request)
    request.session.flush()
    if hasattr(request, "_cached_usuario"):
        delattr(request, "_cached_usuario")
    from django.conf import settings as django_settings
    response = redirect("login")
    response.delete_cookie(django_settings.SESSION_COOKIE_NAME)
    response.delete_cookie("messages")
    return response

