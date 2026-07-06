from django.urls import path
from . import views

urlpatterns = [

    path("", views.login_usuario, name="home"),

    path("login/", views.login_usuario, name="login"),

    path("cadastro/", views.cadastro, name="cadastro"),

    path("feed/", views.feed, name="feed"),

    path("publicar/", views.publicar, name="publicar"),

    path("curtir/<int:id_publicacao>/", views.curtir, name="curtir"),

    path("sair/", views.sair, name="sair"),

]