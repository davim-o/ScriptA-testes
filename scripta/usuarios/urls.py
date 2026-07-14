from django.urls import path
from . import views

urlpatterns=[

    path("",views.login_usuario,name="login"),

    path("cadastro/",views.cadastro,name="cadastro"),

    path("feed/",views.feed,name="feed"),

    path("publicar/",views.publicar,name="publicar"),

    path(
        "curtir/<int:id_publicacao>/",
        views.curtir,
        name="curtir"
    ),

    path(
        "excluir/<int:id_publicacao>/",
        views.excluir_publicacao,
        name="excluir_publicacao"
    ),

    path("sair/",views.sair,name="sair"),

    path(
        "painel-administrativo/",
        views.painel_administrativo,
        name="painel_administrativo"
    ),

    path(
        "painel-administrativo/aprovar/<int:id_usuario>/",
        views.aprovar_membro,
        name="aprovar_membro"
    ),

    path(
        "painel-administrativo/recusar/<int:id_usuario>/",
        views.recusar_membro,
        name="recusar_membro"
    ),

    path(
        "painel-administrativo/promover/",
        views.promover_sublider,
        name="promover_sublider"
    ),

]