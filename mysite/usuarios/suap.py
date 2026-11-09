import json
import urllib.request
import urllib.error


SUAP_BASE_URL = "https://suap.ifrn.edu.br"

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
        for chave, cfg in CONTAS_ADM_DIRETORIAS.items():
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

# Mapeamento de códigos de curso na matrícula do SUAP/IFRN -> (Diretoria, Nome do Curso)
CODIGOS_CURSO_MATRICULA = {
    # Diatinf
    "01111": ("Diatinf", "Técnico em Informática para Internet"),
    "1111":  ("Diatinf", "Técnico em Informática para Internet"),
    "01140": ("Diatinf", "Técnico em Informática para Internet"),
    "1140":  ("Diatinf", "Técnico em Informática para Internet"),
    "01112": ("Diatinf", "Técnico em Manutenção e Suporte em Informática"),
    "1112":  ("Diatinf", "Técnico em Manutenção e Suporte em Informática"),
    "01141": ("Diatinf", "Técnico em Manutenção e Suporte em Informática"),
    "01113": ("Diatinf", "Técnico em Redes de Computadores"),
    "1113":  ("Diatinf", "Técnico em Redes de Computadores"),
    "01142": ("Diatinf", "Técnico em Redes de Computadores"),
    "01159": ("Diatinf", "Tecnologia em Análise e Desenvolvimento de Sistemas"),
    "0159":  ("Diatinf", "Tecnologia em Análise e Desenvolvimento de Sistemas"),
    "01160": ("Diatinf", "Tecnologia em Redes de Computadores"),
    "0160":  ("Diatinf", "Tecnologia em Redes de Computadores"),
    # Diaren
    "01101": ("Diaren", "Técnico em Controle Ambiental"),
    "1101":  ("Diaren", "Técnico em Controle Ambiental"),
    "0101":  ("Diaren", "Técnico em Controle Ambiental"),
    "01102": ("Diaren", "Técnico em Geologia"),
    "1102":  ("Diaren", "Técnico em Geologia"),
    "0102":  ("Diaren", "Técnico em Geologia"),
    "01103": ("Diaren", "Técnico em Mineração"),
    "1103":  ("Diaren", "Técnico em Mineração"),
    "0103":  ("Diaren", "Técnico em Mineração"),
    "01151": ("Diaren", "Tecnologia em Gestão Ambiental"),
    "0151":  ("Diaren", "Tecnologia em Gestão Ambiental"),
    # Diacon
    "01201": ("Diacon", "Técnico em Edificações"),
    "1201":  ("Diacon", "Técnico em Edificações"),
    "01121": ("Diacon", "Técnico em Edificações"),
    "0201":  ("Diacon", "Técnico em Edificações"),
    "01202": ("Diacon", "Técnico em Estradas"),
    "1202":  ("Diacon", "Técnico em Estradas"),
    "01122": ("Diacon", "Técnico em Estradas"),
    "0202":  ("Diacon", "Técnico em Estradas"),
    "01152": ("Diacon", "Engenharia Civil"),
    "0152":  ("Diacon", "Engenharia Civil"),
    # Diacin
    "01301": ("Diacin", "Técnico em Administração"),
    "1301":  ("Diacin", "Técnico em Administração"),
    "01131": ("Diacin", "Técnico em Administração"),
    "0301":  ("Diacin", "Técnico em Administração"),
    "01302": ("Diacin", "Técnico em Eletrotécnica"),
    "1302":  ("Diacin", "Técnico em Eletrotécnica"),
    "01132": ("Diacin", "Técnico em Eletrotécnica"),
    "0302":  ("Diacin", "Técnico em Eletrotécnica"),
    "01303": ("Diacin", "Técnico em Mecânica"),
    "1303":  ("Diacin", "Técnico em Mecânica"),
    "01133": ("Diacin", "Técnico em Mecânica"),
    "0303":  ("Diacin", "Técnico em Mecânica"),
    "01304": ("Diacin", "Técnico em Comércio"),
    "1304":  ("Diacin", "Técnico em Comércio"),
    "01134": ("Diacin", "Técnico em Comércio"),
    "0304":  ("Diacin", "Técnico em Comércio"),
}

PALAVRAS_CHAVE_DIRETORIA = [
    ("Diatinf", [
        "diatinf", "informática", "informatica", "manutenção e suporte",
        "manutencao e suporte", "redes de computadores", "desenvolvimento de sistemas",
        "tads", "sistemas para internet", "tecnologia da informação", "tecnologia da informacao",
    ]),
    ("Diaren", [
        "diaren", "controle ambiental", "geologia", "mineração", "mineracao",
        "gestão ambiental", "gestao ambiental", "recursos naturais",
    ]),
    ("Diacon", [
        "diacon", "edificações", "edificacoes", "estradas", "construção civil",
        "construcao civil", "engenharia civil", "construção de edifícios",
    ]),
    ("Diacin", [
        "diacin", "administração", "administracao", "eletrotécnica", "eletrotecnica",
        "mecânica", "mecanica", "mecatrônica", "mecatronica", "comércio", "comercio",
        "energias renováveis", "engenharia de energia", "física", "fisica", "matemática",
    ]),
]


def identificar_diretoria_e_curso(matricula, curso_suap="", setor_suap=""):
    """
    Identifica a Diretoria (Diaren, Diatinf, Diacon ou Diacin) e o nome do Curso
    a partir dos dados retornados pelo SUAP ou do código embutido na matrícula do IFRN.
    """
    mat = (matricula or "").strip()
    curso_limpo = (curso_suap or "").strip()
    setor_limpo = (setor_suap or "").strip()

    texto_busca = f"{setor_limpo} {curso_limpo}".lower()
    if texto_busca.strip():
        for diretoria, termos in PALAVRAS_CHAVE_DIRETORIA:
            for termo in termos:
                if termo in texto_busca:
                    return diretoria, (curso_limpo or f"Curso vinculado à {diretoria}")

    # Extração pelo padrão de matrícula do SUAP/IFRN (ex.: 20241011110029 -> ano 2024, sem 1, cod 01111, seq 0029)
    if mat.isdigit() and len(mat) >= 10:
        meio = mat[5:-4] if len(mat) >= 11 else mat[4:-4]
        for candidato in (meio, mat[5:10], mat[5:9], mat[4:9], mat[4:8]):
            if candidato in CODIGOS_CURSO_MATRICULA:
                return CODIGOS_CURSO_MATRICULA[candidato]

    return None, curso_limpo


def consultar_api_suap(matricula, senha, timeout=4.5):
    """
    Autentica a matrícula e senha diretamente na API REST do SUAP (suap.ifrn.edu.br)
    e retorna os dados acadêmicos do aluno (nome, diretoria e curso).
    """
    import sys
    mat = (matricula or "").strip()
    diretoria_mat, curso_mat = identificar_diretoria_e_curso(mat)
    if not mat or not senha or "test" in sys.argv or len(mat) < 10:
        return {
            "autenticado_suap": False,
            "credenciais_invalidas": False,
            "offline": True,
            "nome": "",
            "diretoria": diretoria_mat,
            "curso": curso_mat,
        }

    token_urls = [
        f"{SUAP_BASE_URL}/api/v2/autenticacao/token/",
        f"{SUAP_BASE_URL}/api/token/pair",
    ]
    payload = json.dumps({"username": mat, "password": senha}).encode("utf-8")

    access_token = None
    suap_respondeu = False

    for url in token_urls:
        req = urllib.request.Request(
            url,
            data=payload,
            headers={
                "Content-Type": "application/json",
                "Accept": "application/json",
                "User-Agent": "ScriptA-IFRN/1.0",
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                suap_respondeu = True
                corpo = json.loads(resp.read().decode("utf-8"))
                access_token = corpo.get("access") or corpo.get("token")
                if access_token:
                    break
        except urllib.error.HTTPError as e:
            if e.code in (400, 401, 403):
                return {
                    "autenticado_suap": False,
                    "credenciais_invalidas": True,
                    "offline": False,
                    "erro": "Matrícula ou senha do SUAP incorreta. Use a mesma matrícula e senha do SUAP.",
                }
        except Exception:
            continue

    diretoria_mat, curso_mat = identificar_diretoria_e_curso(mat)

    if not access_token:
        return {
            "autenticado_suap": False,
            "credenciais_invalidas": False,
            "offline": not suap_respondeu,
            "nome": "",
            "diretoria": diretoria_mat,
            "curso": curso_mat,
        }

    # Busca dados do perfil do aluno no SUAP
    nome_suap = ""
    curso_suap = ""
    setor_suap = ""
    dados_urls = [
        f"{SUAP_BASE_URL}/api/v2/minhas-informacoes/meus-dados/",
        f"{SUAP_BASE_URL}/api/rh/eu/",
    ]
    for d_url in dados_urls:
        req_dados = urllib.request.Request(
            d_url,
            headers={
                "Authorization": f"Bearer {access_token}",
                "Accept": "application/json",
                "User-Agent": "ScriptA-IFRN/1.0",
            },
            method="GET",
        )
        try:
            with urllib.request.urlopen(req_dados, timeout=timeout) as resp_d:
                dados = json.loads(resp_d.read().decode("utf-8"))
                vinculo = dados.get("vinculo") if isinstance(dados.get("vinculo"), dict) else {}
                nome_suap = (
                    dados.get("nome_usual")
                    or vinculo.get("nome")
                    or dados.get("nome_registro")
                    or dados.get("nome")
                    or ""
                ).strip()
                curso_suap = (
                    vinculo.get("curso")
                    or dados.get("curso")
                    or ""
                ).strip()
                setor_suap = (
                    vinculo.get("setor_suap")
                    or vinculo.get("setor_lotacao")
                    or dados.get("setor")
                    or ""
                ).strip()
                if nome_suap or curso_suap:
                    break
        except Exception:
            continue

    diretoria_final, curso_final = identificar_diretoria_e_curso(mat, curso_suap, setor_suap)
    return {
        "autenticado_suap": True,
        "credenciais_invalidas": False,
        "offline": False,
        "nome": nome_suap,
        "diretoria": diretoria_final or diretoria_mat,
        "curso": curso_final or curso_suap or curso_mat,
    }
