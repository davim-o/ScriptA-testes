import json
import re
import unicodedata
import urllib.error
import urllib.parse
import urllib.request


SUAP_BASE_URL = "https://suap.ifrn.edu.br"
SUAP_USER_AGENT = "Mozilla/5.0 (compatible; ScriptA-IFRN/3.0; +https://scripta.pythonanywhere.com)"

# 4 contas fixas de líderes por diretoria (padrão Matrícula: Diatinf / Senha: diatinf)
CONTAS_ADM_DIRETORIAS = {
    "diatinf": {
        "matricula": "Diatinf",
        "nome": "Diatinf",
        "diretoria": "Diatinf",
        "senha_padrao": "diatinf",
    },
    "diaren": {
        "matricula": "Diaren",
        "nome": "Diaren",
        "diretoria": "Diaren",
        "senha_padrao": "diaren",
    },
    "diacon": {
        "matricula": "Diacon",
        "nome": "Diacon",
        "diretoria": "Diacon",
        "senha_padrao": "diacon",
    },
    "diacin": {
        "matricula": "Diacin",
        "nome": "Diacin",
        "diretoria": "Diacin",
        "senha_padrao": "diacin",
    },
}

MATRICULAS_ADM_FIXAS = {"admin"} | set(CONTAS_ADM_DIRETORIAS.keys())


def _normalizar_texto(valor):
    """Remove acentos, converte para minúsculas e normaliza espaços para comparação precisa."""
    if not valor:
        return ""
    s = unicodedata.normalize("NFD", str(valor))
    s = "".join(ch for ch in s if unicodedata.category(ch) != "Mn")
    return " ".join(s.lower().split())


def _extrair_texto_campo(valor):
    """Extrai string segura mesmo que o SUAP retorne dict/lista aninhados em algum campo."""
    if not valor:
        return ""
    if isinstance(valor, str):
        return valor.strip()
    if isinstance(valor, (int, float)):
        return str(valor)
    if isinstance(valor, dict):
        partes_dict = []
        for chave in (
            "sigla", "nome", "descricao", "nome_usual", "titulo",
            "diretoria", "curso", "setor_suap",
        ):
            if valor.get(chave):
                res = _extrair_texto_campo(valor.get(chave))
                if res and res not in partes_dict:
                    partes_dict.append(res)
        return " ".join(partes_dict).strip()
    if isinstance(valor, list):
        partes = [_extrair_texto_campo(v) for v in valor]
        return " ".join(p for p in partes if p).strip()
    return ""


def _extrair_lista_suap(dados):
    """Normaliza retornos paginados ({results: [...]}) ou listas diretas do SUAP."""
    if isinstance(dados, list):
        return dados
    if isinstance(dados, dict) and isinstance(dados.get("results"), list):
        return dados["results"]
    return []


def _contem_termo(texto_norm, termo_norm, exigir_fronteira=True):
    """Verifica ocorrência exata de sigla ou expressão sem falsos positivos por substring parcial."""
    if not texto_norm or not termo_norm:
        return False
    if exigir_fronteira:
        padrao = r"(?<![a-z0-9])" + re.escape(termo_norm) + r"(?![a-z0-9])"
        return bool(re.search(padrao, texto_norm))
    return termo_norm in texto_norm


def garantir_lideres_diretorias():
    """
    Garante que as 4 contas de líderes das diretorias (Diatinf/diatinf, Diaren/diaren,
    Diacon/diacon, Diacin/diacin) existam e estejam aprovadas no banco de dados,
    e remove contas inseguras legadas (como superusuário 'admin'/'admin' do Django).
    """
    import sys
    if "test" in sys.argv:
        return
    try:
        from django.contrib.auth.models import User as DjangoAdminUser
        DjangoAdminUser.objects.filter(username__iexact="admin").delete()
    except Exception:
        pass
    try:
        from django.contrib.auth.hashers import make_password, check_password
        from .models import Usuario
        Usuario.objects.filter(matricula__iexact="admin").delete()
        for cfg in CONTAS_ADM_DIRETORIAS.values():
            lider = Usuario.objects.filter(matricula__iexact=cfg["matricula"]).first()
            if not lider:
                Usuario.objects.create(
                    nome=cfg["nome"],
                    matricula=cfg["matricula"],
                    senha=make_password(cfg["senha_padrao"]),
                    diretoria=cfg["diretoria"],
                    areas="",
                    aprovado=True,
                )
            else:
                campos_atualizar = []
                if lider.matricula != cfg["matricula"]:
                    lider.matricula = cfg["matricula"]
                    campos_atualizar.append("matricula")
                if lider.diretoria != cfg["diretoria"]:
                    lider.diretoria = cfg["diretoria"]
                    campos_atualizar.append("diretoria")
                if not lider.aprovado:
                    lider.aprovado = True
                    campos_atualizar.append("aprovado")
                if not check_password(cfg["senha_padrao"], lider.senha):
                    lider.senha = make_password(cfg["senha_padrao"])
                    campos_atualizar.append("senha")
                if campos_atualizar:
                    lider.save(update_fields=campos_atualizar)
    except Exception:
        pass


# Apenas códigos confirmados (sem suposições que joguem alunos para diretorias erradas)
CODIGOS_CURSO_MATRICULA = {
    "01111": ("Diatinf", "Técnico em Informática para Internet"),
    "01404": ("Diatinf", "Tecnologia em Análise e Desenvolvimento de Sistemas"),
}

# 1. Siglas oficiais de diretorias do CNAT
SIGLAS_DIRETORIA_EXATAS = [
    ("Diatinf", ["diatinf", "diatadm"]),
    ("Diaren",  ["diaren"]),
    ("Diacon",  ["diacon", "diacci"]),
    ("Diacin",  ["diacin", "diatel"]),
]

# 2. Nomes oficiais das diretorias do IFRN CNAT
NOMES_DIRETORIA_OFICIAIS = [
    ("Diatinf", ["diretoria academica de gestao e tecnologia da informacao", "gestao e tecnologia da informacao"]),
    ("Diaren",  ["diretoria academica de recursos naturais"]),
    ("Diacon",  ["diretoria academica de construcao civil"]),
    ("Diacin",  ["diretoria academica de industria"]),
]

# 3. Termos compostos específicos primeiro (evita colisões), depois cursos oficiais do CNAT
PALAVRAS_CHAVE_CURSOS_ESPECIFICOS = [
    ("Diatinf", [
        "mineracao de dados", "ciencia de dados", "gestao publica", "gestao empresarial",
        "comercio exterior", "informatica para internet", "manutencao e suporte em informatica",
        "manutencao de equipamentos de informatica", "manutencao de computadores",
        "redes de computadores", "analise e desenvolvimento de sistemas",
        "desenvolvimento de sistemas", "desenvolvimento web", "desenvolvimento de software",
        "sistemas para internet", "sistemas de informacao",
    ]),
    ("Diaren", [
        "recursos naturais", "controle ambiental", "meio ambiente", "gestao ambiental",
        "engenharia sanitaria e ambiental", "saneamento ambiental", "tecnologia ambiental",
        "ensino de geociencias", "geologia e mineracao", "tratamento de minerios",
        "rochas ornamentais", "licenciamento ambiental", "uso sustentavel de recursos naturais",
    ]),
    ("Diacon", [
        "construcao civil", "construcao de edificios", "producao da construcao civil",
        "construcao predial", "desenho de projetos de edificacoes", "desenho de construcao",
        "tecnologia em construcao", "servicos condominiais", "transporte e trafego",
        "engenharia civil",
    ]),
    ("Diacin", [
        "petroleo e gas", "industria do petroleo", "manutencao na industria do petroleo",
        "operacao e manutencao da producao de petroleo", "seguranca do trabalho",
        "automacao industrial", "automacao e controle", "fabricacao mecanica",
        "engenharia de energia", "engenharia eletrica", "engenharia mecanica",
        "energias renovaveis", "eficiencia energetica", "manutencao industrial",
        "sistemas fotovoltaicos", "energia eolica", "comandos eletricos",
    ]),
]

PALAVRAS_CHAVE_AREAS_GERAIS = [
    ("Diatinf", [
        "tecnologia da informacao", "informatica", "tads", "computacao",
        "administracao", "comercio", "secretariado", "logistica", "financas",
        "multimidia", "jogos digitais",
    ]),
    ("Diaren", [
        "geologia", "mineracao", "geociencias", "geoprocessamento", "minerais",
        "lavra", "mineralogia", "sondagem", "ecologia", "hidrologia", "ambiental",
    ]),
    ("Diacon", [
        "edificacoes", "estradas", "obras", "topografia", "agrimensura",
        "pavimentacao", "concreto", "alvenaria", "infraestrutura", "arquitetura",
        "design de interiores",
    ]),
    ("Diacin", [
        "eletrotecnica", "mecanica", "mecatronica", "automacao", "eletromecanica",
        "eletronica", "eletroeletronica", "eletricidade", "industria", "industrial",
        "soldagem", "usinagem", "refrigeracao", "tecnologia em materiais",
    ]),
]

SIGLAS_DISCIPLINAS_DIRETORIA = [
    ("Diaren",  ["camb", "geol", "miner", "mamb", "rnat", "diaren", "geoap"]),
    ("Diacon",  ["edif", "estr", "cciv", "diacon", "topo", "cad"]),
    ("Diacin",  ["elet", "meca", "mect", "indu", "diacin", "ener", "petg", "segtrab"]),
    ("Diatinf", ["info", "tads", "admn", "prog", "web", "redes", "diatinf"]),
]


def _buscar_diretoria_no_texto(texto_bruto):
    """Identifica a diretoria a partir do nome oficial do curso, setor ou sigla do SUAP."""
    texto = _normalizar_texto(texto_bruto)
    if not texto:
        return None

    for diretoria, siglas in SIGLAS_DIRETORIA_EXATAS:
        for sigla in siglas:
            if _contem_termo(texto, sigla, exigir_fronteira=True):
                return diretoria

    for diretoria, nomes in NOMES_DIRETORIA_OFICIAIS:
        for nome in nomes:
            if nome in texto:
                return diretoria

    for diretoria, termos in PALAVRAS_CHAVE_CURSOS_ESPECIFICOS:
        for termo in termos:
            if termo in texto:
                return diretoria

    for diretoria, termos in PALAVRAS_CHAVE_AREAS_GERAIS:
        for termo in termos:
            if _contem_termo(texto, termo, exigir_fronteira=True):
                return diretoria

    return None


def identificar_diretoria_e_curso(
    matricula,
    curso_suap="",
    setor_suap="",
    extras_texto="",
    diretoria_explicita="",
    **_kwargs,
):
    """
    Identifica a Diretoria (Diatinf, Diaren, Diacon ou Diacin) e o Curso oficial
    com base nos dados retornados pela API do SUAP (curso, diretoria, boletim/turmas).
    """
    mat = (matricula or "").strip()
    dir_expl_limpa = _extrair_texto_campo(diretoria_explicita)
    curso_limpo = _extrair_texto_campo(curso_suap)
    setor_limpo = _extrair_texto_campo(setor_suap)
    extras_limpo = _extrair_texto_campo(extras_texto)

    # Prioridade 1: Diretoria explícita retornada pelo SUAP
    if dir_expl_limpa:
        dir_exp = _buscar_diretoria_no_texto(dir_expl_limpa)
        if dir_exp:
            return dir_exp, (curso_limpo or f"Curso vinculado à {dir_exp}")

    # Prioridade 2: Nome / sigla oficial do curso retornado pelo SUAP
    if curso_limpo:
        dir_curso = _buscar_diretoria_no_texto(curso_limpo)
        if dir_curso:
            return dir_curso, curso_limpo

    # Prioridade 3: Setor acadêmico se veio no JSON
    if setor_limpo:
        dir_setor = _buscar_diretoria_no_texto(setor_limpo)
        if dir_setor:
            return dir_setor, (curso_limpo or setor_limpo)

    # Prioridade 4: Boletim / Turmas virtuais / Diários com pontuação ponderada
    if extras_limpo:
        placar = {"Diatinf": 0, "Diaren": 0, "Diacon": 0, "Diacin": 0}
        blocos = [b.strip() for b in re.split(r"[|\n;]+", extras_limpo) if b.strip()] or [extras_limpo]
        for bloco in blocos:
            d_bloco = _buscar_diretoria_no_texto(bloco)
            norm_b = _normalizar_texto(bloco)
            if d_bloco:
                peso = 1 if ("informatica basica" in norm_b or "informatica aplicada" in norm_b) else 3
                placar[d_bloco] += peso
            else:
                for diretoria, cods in SIGLAS_DISCIPLINAS_DIRETORIA:
                    for c in cods:
                        if _contem_termo(norm_b, c, exigir_fronteira=True):
                            placar[diretoria] += 2
                            break
        vencedora, maior_pts = max(placar.items(), key=lambda par: par[1])
        if maior_pts > 0:
            return vencedora, (curso_limpo or f"Curso vinculado à {vencedora}")

    # Fallback offline estrito (apenas códigos confirmados)
    if mat.isdigit() and len(mat) >= 10:
        meio = mat[5:-4] if len(mat) >= 11 else mat[4:-4]
        for candidato in (meio, mat[5:10], mat[5:9], mat[4:9], mat[4:8]):
            if candidato in CODIGOS_CURSO_MATRICULA:
                dir_fb, curso_fb = CODIGOS_CURSO_MATRICULA[candidato]
                return dir_fb, (curso_limpo or curso_fb)

    return None, curso_limpo


class _NoRedirectPostHandler(urllib.request.HTTPRedirectHandler):
    """Evita conversão de POST em GET em redirecionamentos HTTP."""
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        if req.get_method() == "POST":
            return None
        return super().redirect_request(req, fp, code, msg, headers, newurl)


_OPENER_SEGURO = urllib.request.build_opener(_NoRedirectPostHandler)


def _fazer_requisicao_json(url, method="GET", headers=None, payload=None, timeout=6.0):
    """Executa requisição HTTP para o SUAP com tratamento seguro de JSON e erros HTTP."""
    req = urllib.request.Request(
        url,
        data=payload,
        headers=headers or {},
        method=method,
    )
    try:
        with _OPENER_SEGURO.open(req, timeout=timeout) as resp:
            raw = resp.read().decode("utf-8", errors="replace")
            return resp.status, json.loads(raw)
    except urllib.error.HTTPError as e:
        corpo_erro = None
        try:
            raw_err = e.read().decode("utf-8", errors="replace")
            corpo_erro = json.loads(raw_err)
        except Exception:
            corpo_erro = None
        return e.code, corpo_erro
    except Exception:
        return None, None


def _get_suap_autenticado(url, token, scheme_preferido="Bearer", timeout=6.0):
    """Faz GET autenticado no SUAP usando `Bearer` e tenta fallback `JWT` caso receba 401."""
    esquemas = [scheme_preferido, "JWT" if scheme_preferido != "JWT" else "Bearer"]
    ultimo_status, ultimo_corpo = None, None
    for idx, esc in enumerate(esquemas):
        headers = {
            "Authorization": f"{esc} {token}",
            "Accept": "application/json",
            "User-Agent": SUAP_USER_AGENT,
        }
        st, corpo = _fazer_requisicao_json(url, method="GET", headers=headers, timeout=timeout)
        ultimo_status, ultimo_corpo = st, corpo
        if st == 200:
            return st, corpo, esc
        if st != 401 or idx == len(esquemas) - 1:
            break
    return ultimo_status, ultimo_corpo, scheme_preferido


def _extrair_info_dados_suap(dados):
    """Extrai nome, curso, sigla de curso, diretoria e campus dos formatos JSON retornados pelo SUAP."""
    if not isinstance(dados, dict):
        return {}

    vinculo = dados.get("vinculo") if isinstance(dados.get("vinculo"), dict) else {}
    vinculos_lista = dados.get("vinculos") if isinstance(dados.get("vinculos"), list) else []

    nome = (
        _extrair_texto_campo(dados.get("nome_usual"))
        or _extrair_texto_campo(vinculo.get("nome"))
        or _extrair_texto_campo(dados.get("nome_registro"))
        or _extrair_texto_campo(dados.get("nome_completo"))
        or _extrair_texto_campo(dados.get("nome_usuario"))
        or _extrair_texto_campo(dados.get("nome"))
    )

    curso_partes = [
        _extrair_texto_campo(vinculo.get("curso")),
        _extrair_texto_campo(dados.get("curso")),
        _extrair_texto_campo(dados.get("descricao_curso")),
        _extrair_texto_campo(vinculo.get("descricao")),
        _extrair_texto_campo(dados.get("sigla_curso")),
        _extrair_texto_campo(vinculo.get("sigla_curso")),
        _extrair_texto_campo(dados.get("matriz")),
        _extrair_texto_campo(vinculo.get("matriz")),
    ]
    curso_principal = next((c for c in curso_partes if c and len(c) > 2), "")

    setor_partes = [
        _extrair_texto_campo(vinculo.get("setor_suap")),
        _extrair_texto_campo(dados.get("setor_suap")),
        _extrair_texto_campo(vinculo.get("setor")),
        _extrair_texto_campo(dados.get("setor")),
    ]

    diretoria_partes = [
        _extrair_texto_campo(vinculo.get("diretoria")),
        _extrair_texto_campo(dados.get("diretoria")),
        _extrair_texto_campo(dados.get("diretoria_academica")),
    ]

    for v_item in vinculos_lista:
        if isinstance(v_item, dict):
            c_v = _extrair_texto_campo(v_item.get("curso"))
            d_v = _extrair_texto_campo(v_item.get("diretoria"))
            if c_v:
                curso_partes.append(c_v)
                if not curso_principal:
                    curso_principal = c_v
            if d_v:
                diretoria_partes.append(d_v)

    campus = (
        _extrair_texto_campo(vinculo.get("campus_sigla"))
        or _extrair_texto_campo(vinculo.get("campus"))
        or _extrair_texto_campo(dados.get("campus_sigla"))
        or _extrair_texto_campo(dados.get("sigla_campus"))
        or _extrair_texto_campo(dados.get("campus"))
        or _extrair_texto_campo(vinculo.get("uo"))
    )

    return {
        "identificacao": _extrair_texto_campo(dados.get("identificacao")) or _extrair_texto_campo(dados.get("matricula")),
        "nome": nome,
        "curso": curso_principal,
        "curso_completo_busca": " | ".join(p for p in curso_partes if p),
        "setor": " | ".join(p for p in setor_partes if p),
        "diretoria_explicita": " | ".join(p for p in diretoria_partes if p),
        "campus": campus,
    }


def _em_ambiente_teste():
    import sys
    return "test" in sys.argv


def consultar_api_suap(matricula, senha, timeout=6.0):
    """
    Autentica matrícula e senha diretamente na API oficial do SUAP IFRN:
      - POST /api/token/pair (com fallback legado /api/v2/autenticacao/token/)
      - GET /api/rh/eu/ e /api/rh/meus-vinculos/
      - GET /api/ensino/meus-dados-aluno/, /api/ensino/aluno-matriculado/, /api/ensino/aluno-resumido/
      - Fallback acadêmico: /api/ensino/meus-periodos-letivos/, turmas virtuais, boletim e diários
    """
    mat = (matricula or "").strip()
    diretoria_mat, curso_mat = identificar_diretoria_e_curso(mat)
    if not mat or not senha or _em_ambiente_teste() or len(mat) < 8:
        return {
            "autenticado_suap": False,
            "credenciais_invalidas": False,
            "offline": True,
            "matricula_oficial": mat,
            "nome": "",
            "diretoria": diretoria_mat,
            "curso": curso_mat,
            "campus": "",
        }

    token_urls = [
        (f"{SUAP_BASE_URL}/api/token/pair", "Bearer"),
        (f"{SUAP_BASE_URL}/api/v2/autenticacao/token/", "JWT"),
    ]
    payload = json.dumps({"username": mat, "password": senha}).encode("utf-8")
    req_headers_post = {
        "Content-Type": "application/json",
        "Accept": "application/json",
        "User-Agent": SUAP_USER_AGENT,
    }

    access_token = None
    scheme_preferido = "Bearer"
    suap_respondeu_valido = False

    for url, scheme_padrao in token_urls:
        status, corpo = _fazer_requisicao_json(
            url, method="POST", headers=req_headers_post, payload=payload, timeout=timeout
        )
        if status == 404:
            continue
        if isinstance(corpo, dict):
            suap_respondeu_valido = True
            token_cand = corpo.get("access") or corpo.get("token")
            if token_cand:
                access_token = token_cand
                scheme_preferido = "Bearer" if corpo.get("access") else scheme_padrao
                break
        if status in (400, 401) and isinstance(corpo, dict):
            return {
                "autenticado_suap": False,
                "credenciais_invalidas": True,
                "offline": False,
                "erro": "Matrícula ou senha do SUAP incorreta.",
            }
        if status == 403 and isinstance(corpo, dict):
            return {
                "autenticado_suap": False,
                "credenciais_invalidas": True,
                "offline": False,
                "erro": "Acesso recusado pelo SUAP para estas credenciais.",
            }

    if not access_token:
        return {
            "autenticado_suap": False,
            "credenciais_invalidas": False,
            "offline": not suap_respondeu_valido,
            "matricula_oficial": mat,
            "nome": "",
            "diretoria": diretoria_mat,
            "curso": curso_mat,
            "campus": "",
        }

    matricula_oficial = mat
    nome_suap = ""
    campus_suap = ""
    curso_suap = ""
    cursos_busca = []
    setores_busca = []
    diretorias_explicitas = []
    extras_busca = []

    st_eu, dados_eu, scheme_preferido = _get_suap_autenticado(
        f"{SUAP_BASE_URL}/api/rh/eu/", access_token, scheme_preferido, timeout=timeout
    )
    if st_eu == 200 and isinstance(dados_eu, dict):
        info_eu = _extrair_info_dados_suap(dados_eu)
        if info_eu.get("identificacao"):
            matricula_oficial = info_eu["identificacao"]
        if info_eu.get("nome"):
            nome_suap = info_eu["nome"]
        if info_eu.get("campus"):
            campus_suap = info_eu["campus"]

    st_vinc, dados_vinc, scheme_preferido = _get_suap_autenticado(
        f"{SUAP_BASE_URL}/api/rh/meus-vinculos/", access_token, scheme_preferido, timeout=timeout
    )
    if st_vinc == 200:
        lista_vinc = _extrair_lista_suap(dados_vinc)
        def _peso_vinculo(v):
            if not isinstance(v, dict):
                return 0
            score = 0
            ident = str(v.get("identificador") or "").strip()
            if ident and (ident == mat or ident == matricula_oficial):
                score += 100
            if "cnat" in _normalizar_texto(v.get("campus") or ""):
                score += 20
            det = v.get("detalhamento") if isinstance(v.get("detalhamento"), dict) else {}
            if det.get("ativo") is True:
                score += 10
            if "integrado" in _normalizar_texto(det.get("modalidade") or ""):
                score += 5
            return score

        for v in sorted(lista_vinc, key=_peso_vinculo, reverse=True):
            if not isinstance(v, dict):
                continue
            if not campus_suap and v.get("campus"):
                campus_suap = str(v.get("campus")).strip()
            det = v.get("detalhamento")
            if isinstance(det, dict) and det.get("curso"):
                c_det = _extrair_texto_campo(det.get("curso"))
                if c_det:
                    cursos_busca.append(c_det)
                    if not curso_suap:
                        curso_suap = c_det

    aluno_urls = [
        f"{SUAP_BASE_URL}/api/ensino/meus-dados-aluno/",
        f"{SUAP_BASE_URL}/api/ensino/aluno-matriculado/?matricula={urllib.parse.quote(matricula_oficial)}",
        f"{SUAP_BASE_URL}/api/ensino/aluno-resumido/?matricula={urllib.parse.quote(matricula_oficial)}",
        f"{SUAP_BASE_URL}/api/v2/minhas-informacoes/meus-dados/",
    ]
    for a_url in aluno_urls:
        st_a, dados_a, scheme_preferido = _get_suap_autenticado(
            a_url, access_token, scheme_preferido, timeout=timeout
        )
        if st_a != 200:
            continue
        itens = [dados_a] if isinstance(dados_a, dict) else (dados_a if isinstance(dados_a, list) else [])
        for item in itens:
            if not isinstance(item, dict):
                continue
            alvo = item.get("aluno") if isinstance(item.get("aluno"), dict) else item
            info_a = _extrair_info_dados_suap(alvo)
            if not nome_suap and info_a.get("nome"):
                nome_suap = info_a["nome"]
            if info_a.get("curso"):
                cursos_busca.append(info_a["curso"])
                if not curso_suap:
                    curso_suap = info_a["curso"]
            if info_a.get("curso_completo_busca"):
                cursos_busca.append(info_a["curso_completo_busca"])
            if info_a.get("diretoria_explicita"):
                diretorias_explicitas.append(info_a["diretoria_explicita"])
            if info_a.get("setor"):
                setores_busca.append(info_a["setor"])
            if not campus_suap and info_a.get("campus"):
                campus_suap = info_a["campus"]

    diretoria_final, curso_final = identificar_diretoria_e_curso(
        matricula_oficial,
        curso_suap or " | ".join(cursos_busca),
        " | ".join(setores_busca),
        "",
        " | ".join(diretorias_explicitas),
    )

    if not diretoria_final or not curso_suap:
        st_p, periodos_raw, scheme_preferido = _get_suap_autenticado(
            f"{SUAP_BASE_URL}/api/ensino/meus-periodos-letivos/",
            access_token,
            scheme_preferido,
            timeout=timeout,
        )
        periodos = _extrair_lista_suap(periodos_raw) if st_p == 200 else []
        extra_endpoints = []
        for per in reversed(periodos[-2:]):
            if not isinstance(per, dict):
                continue
            ano_letivo = per.get("ano_letivo")
            periodo_letivo = per.get("periodo_letivo")
            if ano_letivo and periodo_letivo:
                extra_endpoints.extend([
                    f"{SUAP_BASE_URL}/api/ensino/minhas-turmas-virtuais/{ano_letivo}/{periodo_letivo}/",
                    f"{SUAP_BASE_URL}/api/ensino/meu-boletim/{ano_letivo}/{periodo_letivo}/",
                    f"{SUAP_BASE_URL}/api/ensino/meus-diarios/{ano_letivo}/{periodo_letivo}/",
                    f"{SUAP_BASE_URL}/api/ensino/diarios/{ano_letivo}.{periodo_letivo}/",
                ])
        extra_endpoints.append(f"{SUAP_BASE_URL}/api/ensino/meus-diarios/")

        for e_url in extra_endpoints:
            st_e, dados_e, scheme_preferido = _get_suap_autenticado(
                e_url, access_token, scheme_preferido, timeout=timeout
            )
            if st_e != 200:
                continue
            novos_extras = []
            for item in _extrair_lista_suap(dados_e)[:20]:
                if not isinstance(item, dict):
                    continue
                for k in (
                    "diretoria", "curso", "sigla", "codigo_diario",
                    "disciplina", "descricao", "componente_curricular", "local",
                ):
                    txt = _extrair_texto_campo(item.get(k))
                    if txt:
                        novos_extras.append(txt)
            if novos_extras:
                extras_busca.extend(novos_extras)
                break

        diretoria_final, curso_final = identificar_diretoria_e_curso(
            matricula_oficial,
            curso_suap or " | ".join(cursos_busca),
            " | ".join(setores_busca),
            " | ".join(extras_busca),
            " | ".join(diretorias_explicitas),
        )

    return {
        "autenticado_suap": True,
        "credenciais_invalidas": False,
        "offline": False,
        "matricula_oficial": matricula_oficial,
        "nome": nome_suap,
        "diretoria": diretoria_final,
        "curso": curso_suap or curso_final,
        "campus": campus_suap,
    }
