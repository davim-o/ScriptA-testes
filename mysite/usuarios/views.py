from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse
from django.contrib.auth.hashers import make_password, check_password
from django.db import models
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


def usuario_logado(request):
    if "usuario" not in request.session:
        return None
    return Usuario.objects.get(id=request.session["usuario"])


def cadastro(request):
    if request.method == "POST":
        areas_selecionadas = request.POST.getlist("areas")
        Usuario.objects.create(
            matricula=request.POST["matricula"],
            senha=make_password(request.POST["senha"]),
            diretoria=request.POST["diretoria"],
            areas=",".join(areas_selecionadas),
            aprovado=False
        )
        return redirect("login")
    return render(request, "cadastro.html")


def login_usuario(request):
    erro = None
    if request.method == "POST":
        try:
            usuario = Usuario.objects.get(matricula=request.POST["matricula"])
            if check_password(request.POST["senha"], usuario.senha):
                if not usuario.aprovado:
                    erro = "Seu cadastro ainda está aguardando aprovação da diretoria."
                else:
                    request.session["usuario"] = usuario.id
                    return redirect("feed")
            else:
                erro = "Matrícula ou senha inválida."
        except Usuario.DoesNotExist:
            erro = "Matrícula ou senha inválida."
    return render(request, "login.html", {"erro": erro})


def feed(request):
    if "usuario" not in request.session:
        return redirect("login")
    usuario = Usuario.objects.get(id=request.session["usuario"])
    publicacoes = Publicacao.objects.select_related("usuario").prefetch_related("curtidas").order_by("-data")
    curtidas = Curtida.objects.filter(usuario=usuario).values_list("publicacao_id", flat=True)
    return render(request, "feed.html", {
        "usuario": usuario,
        "publicacoes": publicacoes,
        "curtidas": curtidas
    })


def publicar(request):
    if "usuario" not in request.session:
        return redirect("login")
    if request.method == "POST":
        Publicacao.objects.create(
            usuario=Usuario.objects.get(id=request.session["usuario"]),
            texto=request.POST["texto"]
        )
    return redirect("feed")


def curtir(request, id_publicacao):
    if request.method != "POST":
        return JsonResponse({"erro": "Método inválido"}, status=405)
    if "usuario" not in request.session:
        return JsonResponse({"erro": "Sessão expirada"}, status=401)
    usuario = Usuario.objects.get(id=request.session["usuario"])
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
        from django.db.models import Count, Q
        tarefas_base = Tarefa.objects.filter(area=usuario.sublider_de).prefetch_related("conclusoes")
        tarefas = tarefas_base.filter(encerrada=False).annotate(
            total_concl=Count("conclusoes", distinct=True)
        ).order_by("-criada_em")
        tarefas_concluidas = tarefas_base.filter(encerrada=True).annotate(
            total_concl=Count("conclusoes", distinct=True)
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
        tarefa = Tarefa(
            titulo=request.POST["titulo"],
            tipo=tipo,
            descricao=request.POST.get("descricao", ""),
            limite_participantes=int(request.POST.get("limite_participantes", 2)),
            criada_por=usuario,
            area=usuario.sublider_de or ""
        )
        if tipo == "fixa":
            tarefa.data = request.POST.get("data") or None
            tarefa.horario = request.POST.get("horario") or None
        else:
            tarefa.data_inicio = request.POST.get("data_inicio") or None
            tarefa.data_fim = request.POST.get("data_fim") or None
        if "imagem" in request.FILES:
            tarefa.imagem = request.FILES["imagem"]
        tarefa.save()
    return redirect("painel_administrativo")


def editar_tarefa(request, id_tarefa):
    usuario = usuario_logado(request)
    if usuario is None or not usuario.sub_lider:
        return redirect("login")
    tarefa = get_object_or_404(Tarefa, id=id_tarefa)
    if request.method == "POST":
        tipo = request.POST.get("tipo", tarefa.tipo)
        tarefa.titulo = request.POST["titulo"]
        tarefa.tipo = tipo
        tarefa.descricao = request.POST.get("descricao", "")
        tarefa.limite_participantes = int(request.POST.get("limite_participantes", 2))
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
        tarefa = get_object_or_404(Tarefa, id=id_tarefa)
        tarefa.encerrada = True
        tarefa.save()
    return redirect("painel_administrativo")


def pagina_area(request, nome_area):
    usuario = usuario_logado(request)
    if usuario is None:
        return redirect("login")
    if not usuario.tem_acesso_area(nome_area):
        return redirect("feed")
    tarefas = Tarefa.objects.filter(area=nome_area, encerrada=False).prefetch_related("participacoes").order_by("-criada_em")
    participando = ParticipacaoTarefa.objects.filter(usuario=usuario).values_list("tarefa_id", flat=True)
    ids_concluidos = ConclusaoTarefa.objects.filter(usuario=usuario).values_list("tarefa_id", flat=True)
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
        ParticipacaoTarefa.objects.filter(usuario=usuario, tarefa=tarefa).delete()
        return redirect("pagina_area", nome_area=tarefa.area)


# ─── Minhas Tarefas ───────────────────────────────────────────────────────────

def minhas_tarefas(request, id_tarefa=None):
    usuario = usuario_logado(request)
    if usuario is None:
        return redirect("login")

    # Tarefas em que o usuário participa e que não foram encerradas
    participacoes = ParticipacaoTarefa.objects.filter(
        usuario=usuario
    ).select_related("tarefa").order_by("-tarefa__criada_em")

    # IDs das tarefas que o usuário já concluiu
    ids_concluidos = ConclusaoTarefa.objects.filter(
        usuario=usuario
    ).values_list("tarefa_id", flat=True)

    tarefas = [
        p.tarefa for p in participacoes
        if not p.tarefa.encerrada and p.tarefa.id not in ids_concluidos
    ]

    tarefa_selecionada = None
    aba_ativa = request.GET.get("aba", "detalhes")
    observacoes = []
    conclusao = None
    ja_concluiu = False

    if id_tarefa:
        tarefa_selecionada = get_object_or_404(Tarefa, id=id_tarefa)
        # Verificar que o usuário participa dessa tarefa
        if not ParticipacaoTarefa.objects.filter(usuario=usuario, tarefa=tarefa_selecionada).exists():
            return redirect("minhas_tarefas")
        observacoes = tarefa_selecionada.observacoes.select_related("usuario").order_by("criada_em")
        conclusao = ConclusaoTarefa.objects.filter(usuario=usuario, tarefa=tarefa_selecionada).first()
        ja_concluiu = conclusao is not None

    # Determinar área ativa para sidebar
    area_ativa = tarefa_selecionada.area if tarefa_selecionada else None

    # Primeira área do usuário para o link "Tarefas" quando não há tarefa selecionada
    primeira_area = None
    if not tarefa_selecionada:
        areas = usuario.get_areas_ordenadas()
        primeira_area = areas[0] if areas else None

    return render(request, "minhas_tarefas.html", {
        "usuario": usuario,
        "tarefas": tarefas,
        "tarefa_selecionada": tarefa_selecionada,
        "aba_ativa": aba_ativa,
        "observacoes": observacoes,
        "conclusao": conclusao,
        "ja_concluiu": ja_concluiu,
        "area_ativa": area_ativa,
        "primeira_area": primeira_area,
    })


def adicionar_observacao(request, id_tarefa):
    usuario = usuario_logado(request)
    if usuario is None:
        return redirect("login")
    if request.method == "POST":
        tarefa = get_object_or_404(Tarefa, id=id_tarefa)
        texto = request.POST.get("texto", "").strip()
        if texto:
            ObservacaoTarefa.objects.create(usuario=usuario, tarefa=tarefa, texto=texto)
        return redirect(f"/minhas-tarefas/{id_tarefa}/?aba=observacao")


def concluir_tarefa_usuario(request, id_tarefa):
    usuario = usuario_logado(request)
    if usuario is None:
        return redirect("login")
    if request.method == "POST":
        tarefa = get_object_or_404(Tarefa, id=id_tarefa)
        if tarefa.encerrada or not ParticipacaoTarefa.objects.filter(usuario=usuario, tarefa=tarefa).exists():
            return redirect("minhas_tarefas")
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

        total_concluidos = ConclusaoTarefa.objects.filter(tarefa=tarefa).count()
        if total_concluidos >= tarefa.limite_participantes:
            tarefa.encerrada = True
            tarefa.concluida = True
            tarefa.save(update_fields=["encerrada", "concluida"])

        return redirect(f"/minhas-tarefas/{id_tarefa}/?aba=concluir")


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
        membro = get_object_or_404(Usuario, id=id_usuario)
        membro.aprovado = True
        membro.save()
    return redirect("painel_administrativo")


def recusar_membro(request, id_usuario):
    usuario = usuario_logado(request)
    if usuario is None or not usuario.eh_administrador():
        return redirect("login")
    if request.method == "POST":
        membro = get_object_or_404(Usuario, id=id_usuario)
        membro.delete()
    return redirect("painel_administrativo")


def promover_sublider(request):
    usuario = usuario_logado(request)
    if usuario is None or not usuario.eh_administrador():
        return redirect("login")
    if request.method == "POST":
        try:
            membro = Usuario.objects.get(matricula=request.POST["matricula"], aprovado=True)
            area = request.POST.get("area", "").strip()
            areas_atuais = membro.get_areas_list()
            if area and area not in areas_atuais:
                areas_atuais.append(area)
            membro.areas = ",".join(areas_atuais)
            membro.sub_lider = True
            if area:
                membro.sublider_de = area
            membro.save()
        except Usuario.DoesNotExist:
            pass
    return redirect("painel_administrativo")


def remover_sublider(request, id_usuario):
    usuario = usuario_logado(request)
    if usuario is None or not usuario.eh_administrador():
        return redirect("login")
    if request.method == "POST":
        membro = get_object_or_404(Usuario, id=id_usuario)
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
    total_concluidos = tarefa.conclusoes.count()
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
