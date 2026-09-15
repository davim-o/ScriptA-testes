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

    path(
        "painel-administrativo/remover-sublider/<int:id_usuario>/",
        views.remover_sublider,
        name="remover_sublider"
    ),

    path(
        "painel-administrativo/remover-membro/<int:id_usuario>/",
        views.remover_membro,
        name="remover_membro"
    ),

    path(
        "painel-administrativo/criar-tarefa/",
        views.criar_tarefa,
        name="criar_tarefa"
    ),

    path(
        "painel-administrativo/editar-tarefa/<int:id_tarefa>/",
        views.editar_tarefa,
        name="editar_tarefa"
    ),

    path(
        "painel-administrativo/encerrar-tarefa/<int:id_tarefa>/",
        views.encerrar_tarefa,
        name="encerrar_tarefa"
    ),

    path(
        "area/<str:nome_area>/",
        views.pagina_area,
        name="pagina_area"
    ),

    path(
        "area/participar/<int:id_tarefa>/",
        views.participar_tarefa,
        name="participar_tarefa"
    ),

    path(
        "area/cancelar/<int:id_tarefa>/",
        views.cancelar_participacao,
        name="cancelar_participacao"
    ),

]
