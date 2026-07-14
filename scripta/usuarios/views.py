from django.shortcuts import render,redirect,get_object_or_404
from django.http import JsonResponse
from django.contrib.auth.hashers import make_password,check_password
from .models import Usuario,Publicacao,Curtida


def cadastro(request):

    if request.method=="POST":

        Usuario.objects.create(
            matricula=request.POST["matricula"],
            senha=make_password(request.POST["senha"]),
            diretoria=request.POST["diretoria"],
            areas=",".join(request.POST.getlist("areas"))
        )

        return redirect("login")

    return render(request,"cadastro.html")


def login_usuario(request):

    

    if request.method=="POST":

        try:

            usuario=Usuario.objects.get(
                matricula=request.POST["matricula"]
            )

            if check_password(
                request.POST["senha"],
                usuario.senha
            ):

                request.session["usuario"]=usuario.id

                return redirect("feed")

        except Usuario.DoesNotExist:

            pass

    return render(request,"login.html")


def feed(request):

    if "usuario" not in request.session:
        return redirect("login")

    usuario=Usuario.objects.get(id=request.session["usuario"])

    publicacoes=Publicacao.objects.select_related(
        "usuario"
    ).prefetch_related(
        "curtidas"
    ).order_by("-data")

    curtidas=Curtida.objects.filter(
        usuario=usuario
    ).values_list(
        "publicacao_id",
        flat=True
    )

    return render(
        request,
        "feed.html",
        {
            "usuario":usuario,
            "publicacoes":publicacoes,
            "curtidas":curtidas
        }
    )

def publicar(request):

    if "usuario" not in request.session:

        return redirect("login")

    if request.method=="POST":

        Publicacao.objects.create(

            usuario=Usuario.objects.get(
                id=request.session["usuario"]
            ),

            texto=request.POST["texto"]

        )

    return redirect("feed")


def curtir(request,id_publicacao):

    if request.method!="POST":

        return JsonResponse(
            {"erro":"Método inválido"},
            status=405
        )

    if "usuario" not in request.session:

        return JsonResponse(
            {"erro":"Sessão expirada"},
            status=401
        )

    usuario=Usuario.objects.get(
        id=request.session["usuario"]
    )

    publicacao=get_object_or_404(
        Publicacao,
        id=id_publicacao
    )

    curtida=Curtida.objects.filter(
        usuario=usuario,
        publicacao=publicacao
    )

    if curtida.exists():

        curtida.delete()

        curtido=False

    else:

        Curtida.objects.create(
            usuario=usuario,
            publicacao=publicacao
        )

        curtido=True

    return JsonResponse({

        "curtido":curtido,

        "curtidas":publicacao.total_curtidas()

    })


def excluir_publicacao(request,id_publicacao):

    if "usuario" not in request.session:

        return redirect("login")

    publicacao=get_object_or_404(
        Publicacao,
        id=id_publicacao
    )

    if publicacao.usuario.id==request.session["usuario"]:

        publicacao.delete()

    return redirect("feed")


def sair(request):

    request.session.flush()

    return redirect("login")