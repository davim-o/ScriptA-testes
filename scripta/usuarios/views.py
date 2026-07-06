from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.hashers import make_password, check_password

from .models import Usuario
from .models import Publicacao
from .models import Curtida


def cadastro(request):

    if request.method == "POST":

        matricula = request.POST["matricula"]
        senha = make_password(request.POST["senha"])
        diretoria = request.POST["diretoria"]
        areas = request.POST.getlist("areas")

        Usuario.objects.create(

            matricula=matricula,
            senha=senha,
            diretoria=diretoria,
            areas=",".join(areas)

        )

        return redirect("login")

    return render(request, "cadastro.html")


def login_usuario(request):

    if request.method == "POST":

        matricula = request.POST["matricula"]
        senha = request.POST["senha"]

        try:

            usuario = Usuario.objects.get(
                matricula=matricula
            )

            if check_password(senha, usuario.senha):

                request.session["usuario"] = usuario.id

                return redirect("feed")

        except Usuario.DoesNotExist:

            pass

    return render(request, "login.html")


def feed(request):

    if "usuario" not in request.session:

        return redirect("login")

    usuario = Usuario.objects.get(
        id=request.session["usuario"]
    )

    publicacoes = Publicacao.objects.all().order_by("-data")

    return render(
        request,
        "feed.html",
        {
            "usuario": usuario,
            "publicacoes": publicacoes
        }
    )


def publicar(request):

    if "usuario" not in request.session:

        return redirect("login")

    if request.method == "POST":

        usuario = Usuario.objects.get(
            id=request.session["usuario"]
        )

        texto = request.POST["texto"]

        Publicacao.objects.create(
            usuario=usuario,
            texto=texto
        )

    return redirect("feed")


def curtir(request, id_publicacao):

    if "usuario" not in request.session:

        return redirect("login")

    usuario = Usuario.objects.get(
        id=request.session["usuario"]
    )

    publicacao = get_object_or_404(
        Publicacao,
        id=id_publicacao
    )

    curtida = Curtida.objects.filter(
        usuario=usuario,
        publicacao=publicacao
    )

    if curtida.exists():

        curtida.delete()

    else:

        Curtida.objects.create(
            usuario=usuario,
            publicacao=publicacao
        )

    return redirect("feed")


def sair(request):

    request.session.flush()

    return redirect("login")