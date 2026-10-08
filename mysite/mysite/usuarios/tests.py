from django.contrib.auth.hashers import make_password
from django.test import TestCase
from django.urls import reverse

from .models import ParticipacaoTarefa, Tarefa, Usuario


class LoginRoutesTests(TestCase):
    def setUp(self):
        self.senha = "Senha123"
        self.admin = Usuario.objects.create(
            matricula="admin",
            senha=make_password(self.senha),
            diretoria="Líder",
            areas="",
            aprovado=True,
        )

    def test_login_page_is_available(self):
        response = self.client.get(reverse("login"))
        self.assertEqual(response.status_code, 200)

    def test_admin_can_login_with_text_matricula(self):
        response = self.client.post(
            reverse("login"),
            {"matricula": "admin", "senha": self.senha},
        )
        self.assertRedirects(response, reverse("feed"))

    def test_wrong_password_shows_error(self):
        response = self.client.post(
            reverse("login"),
            {"matricula": "admin", "senha": "errada"},
        )
        self.assertContains(response, "Matrícula ou senha inválida.")


class CadastroTests(TestCase):
    dados = {
        "matricula": "202499",
        "senha": "Senha123",
        "diretoria": "Diaren",
    }

    def test_area_is_required(self):
        response = self.client.post(reverse("cadastro"), self.dados)
        self.assertContains(response, "Selecione pelo menos uma área.")
        self.assertFalse(Usuario.objects.filter(matricula="202499").exists())

    def test_duplicate_matricula_is_rejected(self):
        dados = {**self.dados, "areas": ["Cenário"]}
        self.client.post(reverse("cadastro"), dados)
        response = self.client.post(reverse("cadastro"), dados)
        self.assertContains(response, "Essa matrícula já está cadastrada.")
        self.assertEqual(Usuario.objects.filter(matricula="202499").count(), 1)


class TarefaTests(TestCase):
    def setUp(self):
        self.sublider = Usuario.objects.create(
            matricula="202401",
            senha=make_password("Senha123"),
            diretoria="Diatinf",
            areas="Cenário",
            aprovado=True,
            sub_lider=True,
            sublider_de="Cenário",
        )
        self.membro = Usuario.objects.create(
            matricula="202402",
            senha=make_password("Senha123"),
            diretoria="Diatinf",
            areas="Cenário",
            aprovado=True,
        )
        self.tarefa = Tarefa.objects.create(
            titulo="Tarefa de teste",
            descricao="Teste",
            limite_participantes=1,
            criada_por=self.sublider,
            area="Cenário",
        )
        ParticipacaoTarefa.objects.create(usuario=self.sublider, tarefa=self.tarefa)

    def test_participation_appears_as_status(self):
        self.client.post(
            reverse("login"),
            {"matricula": "202402", "senha": "Senha123"},
        )
        self.client.post(reverse("participar_tarefa", args=[self.tarefa.id]))
        response = self.client.get(reverse("pagina_area", args=["Cenário"]))
        self.assertContains(response, "Participando")

    def test_my_tasks_has_ver_task_button(self):
        self.client.post(
            reverse("login"),
            {"matricula": "202402", "senha": "Senha123"},
        )
        self.client.post(reverse("participar_tarefa", args=[self.tarefa.id]))
        response = self.client.get(reverse("minhas_tarefas"))
        self.assertContains(response, "Ver tarefa")
