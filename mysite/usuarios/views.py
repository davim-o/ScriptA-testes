# pyrefly: ignore [missing-import]
from django.shortcuts import render, redirect, get_object_or_404
# pyrefly: ignore [missing-import]
from django.http import JsonResponse
# pyrefly: ignore [missing-import]
from django.contrib.auth.hashers import make_password, check_password
# pyrefly: ignore [missing-import]
from django.db import models, IntegrityError
from django.db.models import Count, Q, F
from django.contrib import messages
from .models import (
    Usuario, Publicacao, Curtida, Tarefa, ParticipacaoTarefa,
    SolicitacaoArea, ObservacaoTarefa, ConclusaoTarefa
)

AREAS_INFO = {
    "Cenário":     "Planejamento e montagem do ambiente visual do evento.",
    "Staff":       "Organização e gerenciamento da equipe de apoio.",
    "Figurino":    "Definição e controle das roupas e caracterizações.",
    "Dança":       "Coordenação das apresentações coreográficas.",
    "Sonoplastia": "Gerenciamento de músicas, efeitos e áudio do evento.",
    "Tampinhas":   "Gerenciamento e coleta de recursos recicláveis.",
    "Roteiro":     "Estruturação da sequência e organização das apresentações.",
}
TODAS_AREAS = list(AREAS_INFO.keys())
DIRETORIAS = ["Diaren", "Diatinf", "Diacon", "Diacin"]
ADMIN_MATRICULA = "admin"


def matricula_valida(matricula):
    return True


def usuario_logado(request):
    usuario_id = request.session.get("usuario")
    if not usuario_id:
        return None
    try:
        return Usuario.objects.get(id=usuario_id)
    except Usuario.DoesNotExist:
        request.session.flush()
        return None


def cadastro(request):
    contexto = {"erro": None, "form": {}}
    if request.method == "POST":
        matricula = request.POST.get("matricula", "").strip()
        senha = request.POST.get("senha", "")
        diretoria = request.POST.get("diretoria", "").strip()
        areas_selecionadas = [a for a in request.POST.getlist("areas") if a in TODAS_AREAS]
        contexto["form"] = {
            "matricula": matricula,
            "diretoria": diretoria,
            "areas": areas_selecionadas,
        }

        erro = None
        if not matricula:
            erro = "Informe a matrícula."
        elif len(matricula) > 20:
            erro = "A matrícula deve ter no máximo 20 números."
        elif not senha:
            erro = "Informe a senha."
        elif diretoria not in DIRETORIAS:
            erro = "Selecione uma diretoria."
        elif Usuario.objects.filter(matricula=matricula).exists():
            erro = "Essa matrícula já está cadastrada."

        if erro is None:
            try:
                Usuario.objects.create(
                    matricula=matricula,
                    senha=make_password(senha),
                    diretoria=diretoria,
                    areas=",".join(areas_selecionadas),
                    aprovado=False
                )
            except IntegrityError:
                # Cadastro simultâneo com a mesma matrícula
                erro = "Essa matrícula já está cadastrada."
            else:
                return redirect("login")

        contexto["erro"] = erro
    return render(request, "cadastro.html", contexto)


def login_usuario(request):
    erro = None
    if request.method == "POST":
        matricula = request.POST.get("matricula", "").strip()
        senha = request.POST.get("senha", "")
        if not matricula:
            erro = "Informe a matrícula."
        if erro:
            return render(request, "login.html", {"erro": erro, "matricula": matricula})
        try:
            usuario = Usuario.objects.get(matricula=matricula)
            if check_password(senha, usuario.senha):
                if not usuario.aprovado:
                    erro = "Seu cadastro ainda está aguardando aprovação da diretoria."
                else:
                    request.session["usuario"] = usuario.id
                    return redirect("feed")
            else:
                erro = "Matrícula ou senha inválida."
        except Usuario.DoesNotExist:
            erro = "Matrícula ou senha inválida."
    return render(request, "login.html", {"erro": erro, "matricula": matricula if request.method == "POST" else ""})


def feed(request):
    if "usuario" not in request.session:
        return redirect("login")
    usuario = usuario_logado(request)
    if usuario is None:
        return redirect("login")
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
        if texto:
            Publicacao.objects.create(usuario=usuario, texto=texto)
    return redirect("feed")


def curtir(request, id_publicacao):
    if request.method != "POST":
        return JsonResponse({"erro": "Método inválido"}, status=405)
    usuario = usuario_logado(request)
    if usuario is None:
        return JsonResponse({"erro": "Sessão expirada"}, status=401)
    publicacao = get_object_or_404(Publicacao, id=id_publicacao)
    curtida = Curtida.objects.filter(usuario=usuario, publicacao=publicacao)
    if curtida.exists():
        curtida.delete()
        curtido = False
    else:
        Curtida.objects.create(usuario=usuario, publicacao=publicacao)
        curtido = True
    return JsonResponse({"curtido": curtido, "curtidas": publicacao.total_curtidas()})


def excluir_publicacao(request, id_publicacao):
    if "usuario" not in request.session:
        return redirect("login")
    publicacao = get_object_or_404(Publicacao, id=id_publicacao)
    if publicacao.usuario.id == request.session["usuario"]:
        publicacao.delete()
    return redirect("feed")


def painel_administrativo(request):
    usuario = usuario_logado(request)
    if usuario is None:
        return redirect("login")
    if not usuario.tem_acesso_painel():
        return redirect("feed")

    membros = Usuario.objects.filter(aprovado=True).order_by("matricula")
    pendentes = Usuario.objects.filter(aprovado=False).order_by("matricula")
    total_doacoes = membros.aggregate(total=models.Sum("doacao_tampinhas"))["total"] or 0

    if usuario.sub_lider:
        tarefas_base = Tarefa.objects.filter(area=usuario.sublider_de).prefetch_related("conclusoes")
        tarefas = tarefas_base.filter(encerrada=False).annotate(
            total_concl=Count("conclusoes", filter=~Q(conclusoes__usuario=F("criada_por")), distinct=True)
        ).order_by("-criada_em")
        tarefas_concluidas = tarefas_base.filter(encerrada=True).annotate(
            total_concl=Count("conclusoes", filter=~Q(conclusoes__usuario=F("criada_por")), distinct=True)
        ).order_by("-criada_em")
        solicitacoes_area = SolicitacaoArea.objects.filter(
            area=usuario.sublider_de
        ).select_related("usuario").order_by("solicitado_em")
    else:
        tarefas = Tarefa.objects.filter(encerrada=False).order_by("-criada_em")
        tarefas_concluidas = Tarefa.objects.none()
        solicitacoes_area = None

    return render(request, "admin.html", {
        "usuario": usuario,
        "membros": membros,
        "pendentes": pendentes,
        "total_membros": membros.count(),
        "total_pendentes": pendentes.count(),
        "total_doacoes": total_doacoes,
        "tarefas": tarefas,
        "tarefas_concluidas": tarefas_concluidas,
        "solicitacoes_area": solicitacoes_area,
    })


def criar_tarefa(request):
    usuario = usuario_logado(request)
    if usuario is None or not usuario.sub_lider:
        return redirect("login")
    if request.method == "POST":
        tipo = request.POST.get("tipo", "fixa")
        titulo = request.POST.get("titulo", "").strip()
        try:
            limite = int(request.POST.get("limite_participantes", 2))
        except (TypeError, ValueError):
            limite = 0

        if tipo not in {"fixa", "prolongada"} or not titulo or limite < 1:
            messages.error(request, "Preencha os dados da tarefa corretamente.")
            return redirect("painel_administrativo")

        tarefa = Tarefa(
            titulo=titulo,
            tipo=tipo,
            descricao=request.POST.get("descricao", "").strip(),
            limite_participantes=limite,
            criada_por=usuario,
            area=usuario.sublider_de or ""
        )
        if tipo == "fixa":
            tarefa.data = request.POST.get("data") or None
            tarefa.horario = request.POST.get("horario") or None
        else:
            tarefa.data_inicio = request.POST.get("data_inicio") or None
            tarefa.data_fim = request.POST.get("data_fim") or None
            if tarefa.data_inicio and tarefa.data_fim and tarefa.data_fim < tarefa.data_inicio:
                messages.error(request, "O prazo não pode ser anterior à data inicial.")
                return redirect("painel_administrativo")
        if "imagem" in request.FILES:
            tarefa.imagem = request.FILES["imagem"]
        tarefa.save()
        ParticipacaoTarefa.objects.get_or_create(usuario=usuario, tarefa=tarefa)
    return redirect("painel_administrativo")


def editar_tarefa(request, id_tarefa):
    usuario = usuario_logado(request)
    if usuario is None or not usuario.sub_lider:
        return redirect("login")
    tarefa = get_object_or_404(Tarefa, id=id_tarefa, area=usuario.sublider_de)
    if request.method == "POST":
        tipo = request.POST.get("tipo", tarefa.tipo)
        titulo = request.POST.get("titulo", "").strip()
        try:
            limite = int(request.POST.get("limite_participantes", 2))
        except (TypeError, ValueError):
            limite = 0

        if tipo not in {"fixa", "prolongada"} or not titulo or limite < 1:
            messages.error(request, "Preencha os dados da tarefa corretamente.")
            return redirect("painel_administrativo")

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
                messages.error(request, "O prazo não pode ser anterior à data inicial.")
                return redirect("painel_administrativo")
        if "imagem" in request.FILES:
            tarefa.imagem = request.FILES["imagem"]
        tarefa.save()
        return redirect("painel_administrativo")
    return render(request, "editar_tarefa.html", {"usuario": usuario, "tarefa": tarefa})

def encerrar_tarefa(request, id_tarefa):
    usuario = usuario_logado(request)
    if usuario is None or not usuario.tem_acesso_painel():
        return redirect("login")
    if request.method == "POST":
        if usuario.eh_administrador():
            tarefa = get_object_or_404(Tarefa, id=id_tarefa)
        else:
            tarefa = get_object_or_404(Tarefa, id=id_tarefa, area=usuario.sublider_de)
        tarefa.encerrada = True
        tarefa.save(update_fields=["encerrada"])
    return redirect("painel_administrativo")


def pagina_area(request, nome_area):
    usuario = usuario_logado(request)
    if usuario is None:
        return redirect("login")
    if not usuario.tem_acesso_area(nome_area):
        return redirect("feed")
    ids_concluidos = ConclusaoTarefa.objects.filter(usuario=usuario).values_list("tarefa_id", flat=True)
    if usuario.eh_administrador():
        tarefas = Tarefa.objects.filter(area=nome_area).prefetch_related("participacoes").order_by("-criada_em")
    else:
        tarefas = Tarefa.objects.filter(area=nome_area, encerrada=False).exclude(id__in=ids_concluidos).prefetch_related("participacoes").order_by("-criada_em")
    
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


def participar_tarefa(request, id_tarefa):
    usuario = usuario_logado(request)
    if usuario is None:
        return redirect("login")
    if request.method == "POST":
        tarefa = get_object_or_404(Tarefa, id=id_tarefa)
        if not usuario.tem_acesso_area(tarefa.area):
            return redirect("feed")
        if tarefa.encerrada:
            return redirect("pagina_area", nome_area=tarefa.area)
        if tarefa.eh_criador(usuario):
            # O criador já participa da própria tarefa; não entra na contagem
            return redirect("pagina_area", nome_area=tarefa.area)
        ja_inscrito = ParticipacaoTarefa.objects.filter(usuario=usuario, tarefa=tarefa).exists()
        if not ja_inscrito and tarefa.tem_vaga():
            ParticipacaoTarefa.objects.create(usuario=usuario, tarefa=tarefa)
        return redirect("pagina_area", nome_area=tarefa.area)


def cancelar_participacao(request, id_tarefa):
    usuario = usuario_logado(request)
    if usuario is None:
        return redirect("login")
    if request.method == "POST":
        tarefa = get_object_or_404(Tarefa, id=id_tarefa)
        if not tarefa.encerrada and not tarefa.eh_criador(usuario):
            ParticipacaoTarefa.objects.filter(usuario=usuario, tarefa=tarefa).delete()
        return redirect("pagina_area", nome_area=tarefa.area)


# ─── Minhas Tarefas ───────────────────────────────────────────────────────────

def minhas_tarefas(request, nome_area, id_tarefa=None):
    usuario = usuario_logado(request)
    if usuario is None:
        return redirect("login")
    if not usuario.tem_acesso_area(nome_area):
        return redirect("feed")

    # Tarefas em que o usuário participa + tarefas que ele mesmo criou
    # (o sub-líder já participa de todas as que cria).
    todas = Tarefa.objects.filter(
        Q(participacoes__usuario=usuario) | Q(criada_por=usuario)
    ).filter(area=nome_area).distinct().order_by("-criada_em")

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
    ja_concluiu = False
    eh_criador = False

    if id_tarefa:
        tarefa_selecionada = get_object_or_404(Tarefa, id=id_tarefa)
        eh_criador = tarefa_selecionada.eh_criador(usuario)
        # O usuário precisa participar da tarefa ou ser o criador dela
        participa = ParticipacaoTarefa.objects.filter(usuario=usuario, tarefa=tarefa_selecionada).exists()
        if not (participa or eh_criador):
            return redirect("minhas_tarefas", nome_area=nome_area)
        if eh_criador and aba_ativa == "concluir":
            aba_ativa = "detalhes"
        observacoes = tarefa_selecionada.observacoes.select_related("usuario").order_by("criada_em")
        conclusao = ConclusaoTarefa.objects.filter(usuario=usuario, tarefa=tarefa_selecionada).first()
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
        participa = ParticipacaoTarefa.objects.filter(usuario=usuario, tarefa=tarefa).exists()
        if not participa and not tarefa.eh_criador(usuario):
            return redirect("minhas_tarefas", nome_area=nome_area)
        texto = request.POST.get("texto", "").strip()
        if texto:
            ObservacaoTarefa.objects.create(usuario=usuario, tarefa=tarefa, texto=texto)
        return redirect(f"/area/{nome_area}/minhas-tarefas/{id_tarefa}/?aba=observacao")


def concluir_tarefa_usuario(request, nome_area, id_tarefa):
    usuario = usuario_logado(request)
    if usuario is None:
        return redirect("login")
    if request.method == "POST":
        tarefa = get_object_or_404(Tarefa, id=id_tarefa)
        if (
            tarefa.encerrada
            or tarefa.eh_criador(usuario)
            or not ParticipacaoTarefa.objects.filter(usuario=usuario, tarefa=tarefa).exists()
        ):
            return redirect("minhas_tarefas", nome_area=nome_area)
        comentario = request.POST.get("comentario", "").strip()
        conclusao, criada = ConclusaoTarefa.objects.get_or_create(
            usuario=usuario, tarefa=tarefa,
            defaults={"comentario": comentario}
        )
        if not criada:
            conclusao.comentario = comentario
        if "imagem" in request.FILES:
            conclusao.imagem = request.FILES["imagem"]
        conclusao.save()

        total_concluidos = tarefa.total_conclusoes()
        if total_concluidos >= tarefa.limite_participantes:
            tarefa.encerrada = True
            tarefa.concluida = True
            tarefa.save(update_fields=["encerrada", "concluida"])

        return redirect(f"/area/{nome_area}/minhas-tarefas/{id_tarefa}/?aba=concluir")


# ─── Gerenciamento de áreas ──────────────────────────────────────────────────

def nova_area(request):
    usuario = usuario_logado(request)
    if usuario is None:
        return redirect("login")
    areas_usuario = usuario.get_areas_list()
    solicitacoes_pendentes = SolicitacaoArea.objects.filter(usuario=usuario).values_list("area", flat=True)
    areas_com_status = []
    for area in TODAS_AREAS:
        if area in areas_usuario:
            status = "membro"
        elif area in solicitacoes_pendentes:
            status = "pendente"
        else:
            status = "livre"
        areas_com_status.append({"nome": area, "descricao": AREAS_INFO[area], "status": status})
    return render(request, "nova_area.html", {
        "usuario": usuario,
        "areas_com_status": areas_com_status,
        "pagina_ativa": "nova_area",
    })


def solicitar_area(request, nome_area):
    usuario = usuario_logado(request)
    if usuario is None:
        return redirect("login")
    if request.method == "POST" and nome_area in TODAS_AREAS:
        areas_usuario = usuario.get_areas_list()
        if nome_area not in areas_usuario:
            SolicitacaoArea.objects.get_or_create(usuario=usuario, area=nome_area)
    return redirect("nova_area")


def cancelar_solicitacao_area(request, nome_area):
    usuario = usuario_logado(request)
    if usuario is None:
        return redirect("login")
    if request.method == "POST":
        SolicitacaoArea.objects.filter(usuario=usuario, area=nome_area).delete()
    return redirect("nova_area")


def sair_da_area(request, nome_area):
    usuario = usuario_logado(request)
    if usuario is None:
        return redirect("login")
    if request.method == "POST":
        areas = usuario.get_areas_list()
        if nome_area in areas:
            areas.remove(nome_area)
            usuario.areas = ",".join(areas)
            if usuario.sub_lider and usuario.sublider_de == nome_area:
                usuario.sub_lider = False
                usuario.sublider_de = None
            usuario.save()
    return redirect("nova_area")


def aprovar_solicitacao_area(request, id_solicitacao):
    usuario = usuario_logado(request)
    if usuario is None or not usuario.sub_lider:
        return redirect("login")
    if request.method == "POST":
        sol = get_object_or_404(SolicitacaoArea, id=id_solicitacao, area=usuario.sublider_de)
        membro = sol.usuario
        areas = membro.get_areas_list()
        if sol.area not in areas:
            areas.append(sol.area)
            membro.areas = ",".join(areas)
            membro.save()
        sol.delete()
    return redirect("painel_administrativo")


def recusar_solicitacao_area(request, id_solicitacao):
    usuario = usuario_logado(request)
    if usuario is None or not usuario.sub_lider:
        return redirect("login")
    if request.method == "POST":
        sol = get_object_or_404(SolicitacaoArea, id=id_solicitacao, area=usuario.sublider_de)
        sol.delete()
    return redirect("painel_administrativo")


def aprovar_membro(request, id_usuario):
    usuario = usuario_logado(request)
    if usuario is None or not usuario.eh_administrador():
        return redirect("login")
    if request.method == "POST":
        membro = get_object_or_404(Usuario, id=id_usuario, aprovado=False)
        membro.aprovado = True
        membro.save()
    return redirect("painel_administrativo")


def recusar_membro(request, id_usuario):
    usuario = usuario_logado(request)
    if usuario is None or not usuario.eh_administrador():
        return redirect("login")
    if request.method == "POST":
        membro = get_object_or_404(Usuario, id=id_usuario, aprovado=False)
        membro.delete()
    return redirect("painel_administrativo")


def promover_sublider(request):
    usuario = usuario_logado(request)
    if usuario is None or not usuario.eh_administrador():
        return redirect("login")
    if request.method == "POST":
        matricula = request.POST.get("matricula", "").strip()
        area = request.POST.get("area", "").strip()

        if area not in TODAS_AREAS:
            messages.error(request, "Selecione uma área válida para promover o sub-líder.")
            return redirect("painel_administrativo")

        try:
            membro = Usuario.objects.get(matricula=matricula, aprovado=True)
        except Usuario.DoesNotExist:
            messages.error(request, f"Membro \"{matricula}\" não encontrado (ou ainda não aprovado).")
            return redirect("painel_administrativo")

        if membro.eh_administrador():
            messages.error(request, "O líder não pode ser promovido a sub-líder.")
        elif membro.sub_lider:
            # Só pode ser sub-líder de UMA área (mas continua podendo participar
            # das demais como membro comum).
            onde = f" de {membro.sublider_de}" if membro.sublider_de else ""
            messages.error(
                request,
                f"{membro.matricula} já é sub-líder{onde}. Cada membro só pode ser sub-líder "
                f"de uma área; remova o cargo atual antes de promovê-lo novamente."
            )
        else:
            sublider_existente = Usuario.objects.filter(sub_lider=True, sublider_de=area).first()
            if sublider_existente:
                messages.error(request, f"A área {area} já possui um sub-líder ({sublider_existente.matricula}).")
            else:
                areas_atuais = membro.get_areas_list()
                if area not in areas_atuais:
                    areas_atuais.append(area)
                membro.areas = ",".join(areas_atuais)
                membro.sub_lider = True
                membro.sublider_de = area
                membro.save()
                messages.success(request, f"{membro.matricula} agora é sub-líder de {area}.")
    return redirect("painel_administrativo")


def remover_sublider(request, id_usuario):
    usuario = usuario_logado(request)
    if usuario is None or not usuario.eh_administrador():
        return redirect("login")
    if request.method == "POST":
        membro = get_object_or_404(Usuario, id=id_usuario)
        if not membro.eh_administrador():
            membro.sub_lider = False
            membro.sublider_de = None
        membro.save()
    return redirect("painel_administrativo")


def remover_membro(request, id_usuario):
    usuario = usuario_logado(request)
    if usuario is None or not usuario.eh_administrador():
        return redirect("login")
    if request.method == "POST":
        membro = get_object_or_404(Usuario, id=id_usuario)
        if not membro.eh_administrador():
            membro.delete()
    return redirect("painel_administrativo")



def ver_conclusao(request, id_tarefa):
    usuario = usuario_logado(request)
    if usuario is None:
        return redirect("login")
    tarefa = get_object_or_404(Tarefa, id=id_tarefa)
    # Qualquer participante da área ou sub-lider pode ver
    if not usuario.tem_acesso_area(tarefa.area):
        return redirect("feed")
    conclusoes = ConclusaoTarefa.objects.filter(
        tarefa=tarefa
    ).select_related("usuario").order_by("criada_em")
    return render(request, "ver_conclusao.html", {
        "usuario": usuario,
        "tarefa": tarefa,
        "conclusoes": conclusoes,
        "area_ativa": tarefa.area,
    })


def status_tarefa(request, id_tarefa):
    usuario = usuario_logado(request)
    if usuario is None:
        return JsonResponse({"erro": "Sessão expirada"}, status=401)
    tarefa = get_object_or_404(Tarefa, id=id_tarefa)
    if not usuario.tem_acesso_area(tarefa.area):
        return JsonResponse({"erro": "Acesso negado"}, status=403)
    total_concluidos = tarefa.total_conclusoes()
    if total_concluidos >= tarefa.limite_participantes and not tarefa.encerrada:
        tarefa.encerrada = True
        tarefa.concluida = True
        tarefa.save(update_fields=["encerrada", "concluida"])
    return JsonResponse({
        "concluidos": total_concluidos,
        "limite": tarefa.limite_participantes,
        "encerrada": tarefa.encerrada,
    })


def sair(request):
    request.session.flush()
    return redirect("login")

