from django.urls import path
from . import views

urlpatterns=[
    path("", views.login_usuario, name="login"),
    path("cadastro/", views.cadastro, name="cadastro"),
    path("feed/", views.feed, name="feed"),
    path("publicar/", views.publicar, name="publicar"),
    path("curtir/<int:id_publicacao>/", views.curtir, name="curtir"),
    path("excluir/<int:id_publicacao>/", views.excluir_publicacao, name="excluir_publicacao"),
    path("sair/", views.sair, name="sair"),

    # Painel
    path("painel-administrativo/", views.painel_administrativo, name="painel_administrativo"),
    path("painel-administrativo/aprovar/<int:id_usuario>/", views.aprovar_membro, name="aprovar_membro"),
    path("painel-administrativo/recusar/<int:id_usuario>/", views.recusar_membro, name="recusar_membro"),
    path("painel-administrativo/promover/", views.promover_sublider, name="promover_sublider"),
    path("painel-administrativo/remover-sublider/<int:id_usuario>/", views.remover_sublider, name="remover_sublider"),
    path("painel-administrativo/remover-membro/<int:id_usuario>/", views.remover_membro, name="remover_membro"),
    path("painel-administrativo/criar-tarefa/", views.criar_tarefa, name="criar_tarefa"),
    path("painel-administrativo/editar-tarefa/<int:id_tarefa>/", views.editar_tarefa, name="editar_tarefa"),
    path("painel-administrativo/encerrar-tarefa/<int:id_tarefa>/", views.encerrar_tarefa, name="encerrar_tarefa"),
    path("painel-administrativo/aprovar-area/<int:id_solicitacao>/", views.aprovar_solicitacao_area, name="aprovar_solicitacao_area"),
    path("painel-administrativo/recusar-area/<int:id_solicitacao>/", views.recusar_solicitacao_area, name="recusar_solicitacao_area"),

    # Áreas
    path("area/<str:nome_area>/", views.pagina_area, name="pagina_area"),
    path("area/participar/<int:id_tarefa>/", views.participar_tarefa, name="participar_tarefa"),
    path("area/cancelar/<int:id_tarefa>/", views.cancelar_participacao, name="cancelar_participacao"),

    # Nova área
    path("nova-area/", views.nova_area, name="nova_area"),
    path("nova-area/solicitar/<str:nome_area>/", views.solicitar_area, name="solicitar_area"),
    path("nova-area/cancelar/<str:nome_area>/", views.cancelar_solicitacao_area, name="cancelar_solicitacao_area"),
    path("nova-area/sair/<str:nome_area>/", views.sair_da_area, name="sair_da_area"),

    # Conclusão
    path("area/conclusao/<int:id_tarefa>/", views.ver_conclusao, name="ver_conclusao"),
    path("tarefa/status/<int:id_tarefa>/", views.status_tarefa, name="status_tarefa"),

    # Minhas Tarefas
    path("minhas-tarefas/", views.minhas_tarefas, name="minhas_tarefas"),
    path("minhas-tarefas/<int:id_tarefa>/", views.minhas_tarefas, name="minhas_tarefas_detalhe"),
    path("minhas-tarefas/<int:id_tarefa>/observacao/", views.adicionar_observacao, name="adicionar_observacao"),
    path("minhas-tarefas/<int:id_tarefa>/concluir/", views.concluir_tarefa_usuario, name="concluir_tarefa_usuario"),
]
