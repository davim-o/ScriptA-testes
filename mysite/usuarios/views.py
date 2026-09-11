from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse
from django.contrib.auth.hashers import make_password, check_password
from django.db import models
from .models import Usuario, Publicacao, Curtida, Tarefa


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


def usuario_logado(request):
    if "usuario" not in request.session:
        return None
    return Usuario.objects.get(id=request.session["usuario"])


def painel_administrativo(request):
    usuario = usuario_logado(request)
    if usuario is None:
        return redirect("login")
    if not usuario.tem_acesso_painel():
        return redirect("feed")

    membros = Usuario.objects.filter(aprovado=True).order_by("matricula")
    pendentes = Usuario.objects.filter(aprovado=False).order_by("matricula")
    total_doacoes = membros.aggregate(total=models.Sum("doacao_tampinhas"))["total"] or 0
    tarefas = Tarefa.objects.filter(encerrada=False).order_by("-criada_em")

    return render(request, "admin.html", {
        "usuario": usuario,
        "membros": membros,
        "pendentes": pendentes,
        "total_membros": membros.count(),
        "total_pendentes": pendentes.count(),
        "total_doacoes": total_doacoes,
        "tarefas": tarefas,
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
            criada_por=usuario
        )
        if tipo == "fixa":
            tarefa.data = request.POST.get("data") or None
            tarefa.horario = request.POST.get("horario") or None
        else:
            tarefa.data_inicio = request.POST.get("data_inicio") or None
            tarefa.data_fim = request.POST.get("data_fim") or None
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
        tarefa.save()
        return redirect("painel_administrativo")
    return render(request, "editar_tarefa.html", {
        "usuario": usuario,
        "tarefa": tarefa,
    })


def encerrar_tarefa(request, id_tarefa):
    usuario = usuario_logado(request)
    if usuario is None or not usuario.tem_acesso_painel():
        return redirect("login")
    if request.method == "POST":
        tarefa = get_object_or_404(Tarefa, id=id_tarefa)
        tarefa.encerrada = True
        tarefa.save()
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


def sair(request):
    request.session.flush()
    return redirect("login")
