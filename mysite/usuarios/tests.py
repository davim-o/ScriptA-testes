from decimal import Decimal
from django.contrib.auth.hashers import make_password
from django.test import TestCase
from django.urls import reverse

from .models import ParticipacaoTarefa, Tarefa, Usuario, DoacaoTampinhas
from .views import formatar_kg, META_TAMPINHAS_KG


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
        self.assertContains(response, "Selecione pelo menos uma área")
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
        response = self.client.get(reverse("minhas_tarefas", args=["Cenário"]))
        self.assertContains(response, "Ver tarefa")


class TampinhasAccessAndPermissionTests(TestCase):
    def setUp(self):
        self.senha = "Senha123"
        self.admin = Usuario.objects.create(
            matricula="admin",
            senha=make_password(self.senha),
            diretoria="Líder",
            areas="",
            aprovado=True,
        )
        self.sublider_tampinhas = Usuario.objects.create(
            matricula="202410",
            senha=make_password(self.senha),
            diretoria="Diatinf",
            areas="Tampinhas",
            aprovado=True,
            sub_lider=True,
            sublider_de="Tampinhas",
        )
        self.sublider_cenario = Usuario.objects.create(
            matricula="202411",
            senha=make_password(self.senha),
            diretoria="Diatinf",
            areas="Cenário",
            aprovado=True,
            sub_lider=True,
            sublider_de="Cenário",
        )
        self.membro = Usuario.objects.create(
            matricula="202412",
            senha=make_password(self.senha),
            diretoria="Diaren",
            areas="Staff",
            aprovado=True,
        )

    def test_anonymous_redirected_to_login(self):
        response = self.client.get(reverse("tampinhas"))
        self.assertRedirects(response, reverse("login"))

    def test_authenticated_membro_can_access_ranking(self):
        self.client.post(reverse("login"), {"matricula": self.membro.matricula, "senha": self.senha})
        response = self.client.get(reverse("tampinhas"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Tampinhas")

    def test_authenticated_sublider_can_access_ranking(self):
        self.client.post(reverse("login"), {"matricula": self.sublider_tampinhas.matricula, "senha": self.senha})
        response = self.client.get(reverse("tampinhas"))
        self.assertEqual(response.status_code, 200)

    def test_authenticated_admin_can_access_ranking(self):
        self.client.post(reverse("login"), {"matricula": self.admin.matricula, "senha": self.senha})
        response = self.client.get(reverse("tampinhas"))
        self.assertEqual(response.status_code, 200)

    def test_querying_ranking_is_read_only(self):
        self.client.post(reverse("login"), {"matricula": self.membro.matricula, "senha": self.senha})
        count_before = DoacaoTampinhas.objects.count()
        self.client.get(reverse("tampinhas"))
        self.assertEqual(DoacaoTampinhas.objects.count(), count_before)

    def test_only_sublider_tampinhas_can_register_donation(self):
        self.client.post(reverse("login"), {"matricula": self.sublider_tampinhas.matricula, "senha": self.senha})
        response = self.client.post(reverse("registrar_doacao"), {
            "membro_id": self.membro.id,
            "quantidade": "500",
        })
        self.assertRedirects(response, reverse("painel_administrativo"))
        self.assertTrue(DoacaoTampinhas.objects.filter(usuario=self.membro, quantidade_gramas=500).exists())

    def test_membro_comum_cannot_register_donation(self):
        self.client.post(reverse("login"), {"matricula": self.membro.matricula, "senha": self.senha})
        response = self.client.post(reverse("registrar_doacao"), {
            "membro_id": self.membro.id,
            "quantidade": "500",
        })
        self.assertEqual(DoacaoTampinhas.objects.count(), 0)

    def test_sublider_other_area_cannot_register_donation(self):
        self.client.post(reverse("login"), {"matricula": self.sublider_cenario.matricula, "senha": self.senha})
        response = self.client.post(reverse("registrar_doacao"), {
            "membro_id": self.membro.id,
            "quantidade": "500",
        })
        self.assertEqual(DoacaoTampinhas.objects.count(), 0)

    def test_admin_cannot_register_donation(self):
        self.client.post(reverse("login"), {"matricula": self.admin.matricula, "senha": self.senha})
        response = self.client.post(reverse("registrar_doacao"), {
            "membro_id": self.membro.id,
            "quantidade": "500",
        })
        self.assertEqual(DoacaoTampinhas.objects.count(), 0)

    def test_card_registrar_doacao_visible_only_for_tampinhas_sublider(self):
        # Tampinhas sub-leader sees card
        self.client.post(reverse("login"), {"matricula": self.sublider_tampinhas.matricula, "senha": self.senha})
        resp = self.client.get(reverse("painel_administrativo"))
        self.assertContains(resp, "Registrar doação")

        # Admin does NOT see card
        self.client.post(reverse("login"), {"matricula": self.admin.matricula, "senha": self.senha})
        resp = self.client.get(reverse("painel_administrativo"))
        self.assertNotContains(resp, "Registrar doação")

        # Cenário sub-leader does NOT see card
        self.client.post(reverse("login"), {"matricula": self.sublider_cenario.matricula, "senha": self.senha})
        resp = self.client.get(reverse("painel_administrativo"))
        self.assertNotContains(resp, "Registrar doação")


class TampinhasValidationAndAccountingTests(TestCase):
    def setUp(self):
        self.senha = "Senha123"
        self.sublider_tampinhas = Usuario.objects.create(
            matricula="202410",
            senha=make_password(self.senha),
            diretoria="Diatinf",
            areas="Tampinhas",
            aprovado=True,
            sub_lider=True,
            sublider_de="Tampinhas",
        )
        self.membro = Usuario.objects.create(
            matricula="202420",
            senha=make_password(self.senha),
            diretoria="Diaren",
            areas="Staff",
            aprovado=True,
        )
        self.admin = Usuario.objects.create(
            matricula="admin",
            senha=make_password(self.senha),
            diretoria="Líder",
            areas="",
            aprovado=True,
        )
        self.pendente = Usuario.objects.create(
            matricula="202430",
            senha=make_password(self.senha),
            diretoria="Diacon",
            areas="Staff",
            aprovado=False,
        )
        self.client.post(reverse("login"), {"matricula": self.sublider_tampinhas.matricula, "senha": self.senha})

    def test_valid_donation_updates_member_total(self):
        response = self.client.post(reverse("registrar_doacao"), {
            "membro_id": self.membro.id,
            "quantidade": "500",
        })
        self.assertRedirects(response, reverse("painel_administrativo"))
        self.membro.refresh_from_db()
        self.assertEqual(self.membro.doacao_tampinhas, 0.5)

    def test_consecutive_donations_sum_correctly(self):
        # 500g + 250g = 750g = 0.75 Kg
        self.client.post(reverse("registrar_doacao"), {"membro_id": self.membro.id, "quantidade": "500"})
        self.client.post(reverse("registrar_doacao"), {"membro_id": self.membro.id, "quantidade": "250"})
        self.membro.refresh_from_db()
        self.assertEqual(self.membro.doacao_tampinhas, 0.75)
        self.assertEqual(formatar_kg(750, is_gramas=True), "0.75Kg")

    def test_reject_zero_quantity(self):
        self.client.post(reverse("registrar_doacao"), {"membro_id": self.membro.id, "quantidade": "0"})
        self.assertEqual(DoacaoTampinhas.objects.count(), 0)

    def test_reject_negative_quantity(self):
        self.client.post(reverse("registrar_doacao"), {"membro_id": self.membro.id, "quantidade": "-500"})
        self.assertEqual(DoacaoTampinhas.objects.count(), 0)

    def test_reject_decimal_quantity(self):
        self.client.post(reverse("registrar_doacao"), {"membro_id": self.membro.id, "quantidade": "50.5"})
        self.assertEqual(DoacaoTampinhas.objects.count(), 0)

    def test_reject_text_quantity(self):
        self.client.post(reverse("registrar_doacao"), {"membro_id": self.membro.id, "quantidade": "cinquenta"})
        self.assertEqual(DoacaoTampinhas.objects.count(), 0)

    def test_reject_empty_quantity(self):
        self.client.post(reverse("registrar_doacao"), {"membro_id": self.membro.id, "quantidade": ""})
        self.assertEqual(DoacaoTampinhas.objects.count(), 0)

    def test_reject_above_100000_grams(self):
        self.client.post(reverse("registrar_doacao"), {"membro_id": self.membro.id, "quantidade": "100001"})
        self.assertEqual(DoacaoTampinhas.objects.count(), 0)

    def test_accept_100000_grams(self):
        self.client.post(reverse("registrar_doacao"), {"membro_id": self.membro.id, "quantidade": "100000"})
        self.assertEqual(DoacaoTampinhas.objects.count(), 1)
        self.membro.refresh_from_db()
        self.assertEqual(self.membro.doacao_tampinhas, 100.0)

    def test_reject_admin_as_recipient(self):
        self.client.post(reverse("registrar_doacao"), {"membro_id": self.admin.id, "quantidade": "500"})
        self.assertEqual(DoacaoTampinhas.objects.count(), 0)

    def test_reject_unapproved_member_as_recipient(self):
        self.client.post(reverse("registrar_doacao"), {"membro_id": self.pendente.id, "quantidade": "500"})
        self.assertEqual(DoacaoTampinhas.objects.count(), 0)

    def test_reject_nonexistent_member(self):
        self.client.post(reverse("registrar_doacao"), {"membro_id": 999999, "quantidade": "500"})
        self.assertEqual(DoacaoTampinhas.objects.count(), 0)

    def test_totals_consistency_panel_and_stats(self):
        self.client.post(reverse("registrar_doacao"), {"membro_id": self.membro.id, "quantidade": "26600"})
        resp_painel = self.client.get(reverse("painel_administrativo"))
        self.assertContains(resp_painel, "26.6Kg")

        resp_stats = self.client.get(reverse("stats_painel"))
        self.assertEqual(resp_stats.json()["doacoes"], "26.6Kg")

        resp_ranking = self.client.get(reverse("tampinhas"))
        self.assertContains(resp_ranking, "26.6Kg")


class TampinhasRankingAndPresentationTests(TestCase):
    def setUp(self):
        self.senha = "Senha123"
        self.membro1 = Usuario.objects.create(matricula="202401", senha=make_password(self.senha), diretoria="Diatinf", areas="Tampinhas", aprovado=True)
        self.membro2 = Usuario.objects.create(matricula="202402", senha=make_password(self.senha), diretoria="Diaren", areas="Tampinhas", aprovado=True)
        self.membro3 = Usuario.objects.create(matricula="202403", senha=make_password(self.senha), diretoria="Diacon", areas="Tampinhas", aprovado=True)
        self.membro4 = Usuario.objects.create(matricula="202404", senha=make_password(self.senha), diretoria="Diacin", areas="Tampinhas", aprovado=True)
        self.membro_zero = Usuario.objects.create(matricula="202405", senha=make_password(self.senha), diretoria="Diaren", areas="Tampinhas", aprovado=True)
        self.admin = Usuario.objects.create(matricula="admin", senha=make_password(self.senha), diretoria="Líder", areas="", aprovado=True)
        self.client.post(reverse("login"), {"matricula": self.membro1.matricula, "senha": self.senha})

    def test_empty_ranking_state(self):
        response = self.client.get(reverse("tampinhas"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "0Kg")
        self.assertContains(response, "Nenhuma doação registrada ainda.")

    def test_tiebreaker_by_matricula_ascending(self):
        # Both have 5000g, member 202401 should precede 202402
        DoacaoTampinhas.objects.create(usuario=self.membro2, quantidade_gramas=5000)
        DoacaoTampinhas.objects.create(usuario=self.membro1, quantidade_gramas=5000)

        response = self.client.get(reverse("tampinhas"))
        self.assertEqual(response.context["primeiro"]["matricula"], "202401")
        self.assertEqual(response.context["segundo"]["matricula"], "202402")

    def test_ordering_by_total_descending(self):
        DoacaoTampinhas.objects.create(usuario=self.membro1, quantidade_gramas=3000)
        DoacaoTampinhas.objects.create(usuario=self.membro2, quantidade_gramas=7000)
        DoacaoTampinhas.objects.create(usuario=self.membro3, quantidade_gramas=5000)

        response = self.client.get(reverse("tampinhas"))
        self.assertEqual(response.context["primeiro"]["matricula"], "202402")  # 7Kg
        self.assertEqual(response.context["segundo"]["matricula"], "202403")   # 5Kg
        self.assertEqual(response.context["terceiro"]["matricula"], "202401")  # 3Kg

    def test_zero_donations_and_admin_excluded_from_ranking(self):
        DoacaoTampinhas.objects.create(usuario=self.membro1, quantidade_gramas=1000)
        DoacaoTampinhas.objects.create(usuario=self.admin, quantidade_gramas=9000)

        response = self.client.get(reverse("tampinhas"))
        ranking_matriculas = [item["matricula"] for item in [response.context["primeiro"], response.context["segundo"], response.context["terceiro"]] if item]
        self.assertIn("202401", ranking_matriculas)
        self.assertNotIn("admin", ranking_matriculas)
        self.assertNotIn("202405", ranking_matriculas)

    def test_fewer_than_three_participants_handled_gracefully(self):
        DoacaoTampinhas.objects.create(usuario=self.membro1, quantidade_gramas=2000)
        response = self.client.get(reverse("tampinhas"))
        self.assertEqual(response.status_code, 200)
        self.assertIsNotNone(response.context["primeiro"])
        self.assertIsNone(response.context["segundo"])
        self.assertIsNone(response.context["terceiro"])
        self.assertContains(response, "2Kg")

    def test_fourth_place_and_beyond_in_demais_participantes(self):
        DoacaoTampinhas.objects.create(usuario=self.membro1, quantidade_gramas=5000)
        DoacaoTampinhas.objects.create(usuario=self.membro2, quantidade_gramas=4000)
        DoacaoTampinhas.objects.create(usuario=self.membro3, quantidade_gramas=3000)
        DoacaoTampinhas.objects.create(usuario=self.membro4, quantidade_gramas=2000)

        response = self.client.get(reverse("tampinhas"))
        self.assertEqual(len(response.context["demais_participantes"]), 1)
        self.assertEqual(response.context["demais_participantes"][0]["posicao"], 4)
        self.assertEqual(response.context["demais_participantes"][0]["matricula"], "202404")

    def test_progress_bar_capped_at_100_percent_when_exceeding_goal(self):
        # Goal is 40 Kg (40,000g). Give 50,000g.
        DoacaoTampinhas.objects.create(usuario=self.membro1, quantidade_gramas=50000)
        response = self.client.get(reverse("tampinhas"))
        self.assertEqual(response.context["progresso_porcentagem"], 100.0)
        self.assertEqual(response.context["total_geral_kg"], "50Kg")
