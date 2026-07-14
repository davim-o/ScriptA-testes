from django.shortcuts import render,redirect,get_object_or_404
from django.http import JsonResponse
from django.contrib.auth.hashers import make_password,check_password
from django.db import models
from .models import Usuario,Publicacao,Curtida


def cadastro(request):

    if request.method=="POST":

        Usuario.objects.create(
            matricula=request.POST["matricula"],
            senha=make_password(request.POST["senha"]),
            diretoria=request.POST["diretoria"],
            areas=",".join(request.POST.getlist("areas")),
            aprovado=False
        )

        return redirect("login")

    return render(request,"cadastro.html")


def login_usuario(request):

    erro=None

    if request.method=="POST":

        try:

            usuario=Usuario.objects.get(
                matricula=request.POST["matricula"]
            )

            if check_password(
                request.POST["senha"],
                usuario.senha
            ):

                if not usuario.aprovado:

                    erro="Seu cadastro ainda está aguardando aprovação da diretoria."

                else:

                    request.session["usuario"]=usuario.id

                    return redirect("feed")

            else:

                erro="Matrícula ou senha inválida."

        except Usuario.DoesNotExist:

            erro="Matrícula ou senha inválida."

    return render(request,"login.html",{"erro":erro})


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


def usuario_logado(request):

    if "usuario" not in request.session:

        return None

    return Usuario.objects.get(id=request.session["usuario"])


def painel_administrativo(request):

    usuario=usuario_logado(request)

    if usuario is None:

        return redirect("login")

    if not usuario.eh_administrador():

        return redirect("feed")

    membros=Usuario.objects.filter(
        aprovado=True
    ).order_by("matricula")

    pendentes=Usuario.objects.filter(
        aprovado=False
    ).order_by("matricula")

    total_doacoes=membros.aggregate(
        total=models.Sum("doacao_tampinhas")
    )["total"] or 0

    return render(
        request,
        "admin.html",
        {
            "usuario":usuario,
            "membros":membros,
            "pendentes":pendentes,
            "total_membros":membros.count(),
            "total_pendentes":pendentes.count(),
            "total_doacoes":total_doacoes,
        }
    )


def aprovar_membro(request,id_usuario):

    usuario=usuario_logado(request)

    if usuario is None or not usuario.eh_administrador():

        return redirect("login")

    if request.method=="POST":

        membro=get_object_or_404(Usuario,id=id_usuario)
        membro.aprovado=True
        membro.save()

    return redirect("painel_administrativo")


def recusar_membro(request,id_usuario):

    usuario=usuario_logado(request)

    if usuario is None or not usuario.eh_administrador():

        return redirect("login")

    if request.method=="POST":

        membro=get_object_or_404(Usuario,id=id_usuario)
        membro.delete()

    return redirect("painel_administrativo")


def promover_sublider(request):

    usuario=usuario_logado(request)

    if usuario is None or not usuario.eh_administrador():

        return redirect("login")

    if request.method=="POST":

        try:

            membro=Usuario.objects.get(
                matricula=request.POST["matricula"],
                aprovado=True
            )

            area=request.POST.get("area","")

            areas_atuais=[a for a in membro.areas.split(",") if a]

            if area and area not in areas_atuais:

                areas_atuais.append(area)

                membro.areas=",".join(areas_atuais)

            membro.sub_lider=True
            membro.save()

        except Usuario.DoesNotExist:

            pass

    return redirect("painel_administrativo")


def sair(request):

    request.session.flush()

    return redirect("login")