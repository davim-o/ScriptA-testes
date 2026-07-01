from django.shortcuts import render, redirect
from django.contrib.auth.hashers import make_password, check_password
from .models import Usuario

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

    return render(request,"cadastro.html")


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

                return redirect("home")

        except Usuario.DoesNotExist:

            pass

    return render(request,"login.html")


def home(request):

    if "usuario" not in request.session:

        return redirect("login")

    return render(request,"home.html")