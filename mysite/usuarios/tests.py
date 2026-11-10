from decimal import Decimal
from django.contrib.auth.hashers import make_password
from django.test import TestCase
from django.urls import reverse

from .models import (
    ParticipacaoTarefa, Tarefa, Usuario, DoacaoTampinhas,
    MensagemArea, CurtidaMensagemArea, SolicitacaoArea, Publicacao, MetaTampinhas
)
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

    def test_area_and_nome_are_optional(self):
        response = self.client.post(reverse("cadastro"), self.dados)
        self.assertRedirects(response, reverse("login"))
        self.assertTrue(Usuario.objects.filter(matricula="202499").exists())

    def test_wrong_diretoria_for_suap_matricula_notifies_user(self):
        response = self.client.post(
            reverse("cadastro"),
            {
                "matricula": "20241011110029",
                "senha": "Senha123",
                "diretoria": "Diaren",
            },
        )
        self.assertContains(response, "pertence à diretoria Diatinf")
        self.assertFalse(Usuario.objects.filter(matricula="20241011110029").exists())

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
            diretoria="Diatinf",
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
            diretoria="Diatinf",
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
        self.membro2 = Usuario.objects.create(matricula="202402", senha=make_password(self.senha), diretoria="Diatinf", areas="Tampinhas", aprovado=True)
        self.membro3 = Usuario.objects.create(matricula="202403", senha=make_password(self.senha), diretoria="Diatinf", areas="Tampinhas", aprovado=True)
        self.membro4 = Usuario.objects.create(matricula="202404", senha=make_password(self.senha), diretoria="Diatinf", areas="Tampinhas", aprovado=True)
        self.membro_zero = Usuario.objects.create(matricula="202405", senha=make_password(self.senha), diretoria="Diatinf", areas="Tampinhas", aprovado=True)
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


class MultiTabSessionIsolationTests(TestCase):
    def setUp(self):
        self.senha = "Senha123"
        self.admin = Usuario.objects.create(
            matricula="admin",
            senha=make_password(self.senha),
            diretoria="Líder",
            areas="",
            aprovado=True,
        )
        self.sublider_202409 = Usuario.objects.create(
            matricula="202409",
            senha=make_password(self.senha),
            diretoria="Diatinf",
            areas="Tampinhas",
            aprovado=True,
            sub_lider=True,
            sublider_de="Tampinhas",
        )

    def test_clicking_painel_administrativo_keeps_202409_even_if_cookie_is_admin(self):
        from .context_processors import gerar_token_usuario

        token_202409 = gerar_token_usuario(self.sublider_202409.id)
        # Simula que o cookie de sessão compartilhado do navegador foi sobrescrito pelo admin em outra aba
        self.client.post(reverse("login"), {"matricula": "admin", "senha": self.senha})

        # Aba do perfil 202409 clica em "Painel administrativo" (GET com _user_token da aba)
        response = self.client.get(
            reverse("painel_administrativo"),
            {"_user_token": token_202409},
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["usuario"].matricula, "202409")
        self.assertContains(response, "Registrar doação")
        self.assertNotContains(response, "Promover Sub-Líderes")


class ChatAreaTests(TestCase):
    def setUp(self):
        self.senha = "Senha123"
        self.membro_cenario_1 = Usuario.objects.create(
            matricula="Maria Joaquina",
            senha=make_password(self.senha),
            diretoria="Diatinf",
            areas="Cenário",
            aprovado=True,
        )
        self.membro_cenario_2 = Usuario.objects.create(
            matricula="Cirilo Jr.",
            senha=make_password(self.senha),
            diretoria="Diatinf",
            areas="Cenário",
            aprovado=True,
        )
        self.membro_staff = Usuario.objects.create(
            matricula="Jorginho Staff",
            senha=make_password(self.senha),
            diretoria="Diaren",
            areas="Staff",
            aprovado=True,
        )

    def test_chat_is_isolated_per_area(self):
        self.client.post(reverse("login"), {"matricula": self.membro_cenario_1.matricula, "senha": self.senha})
        self.client.post(
            reverse("publicar_chat_area", args=["Cenário"]),
            {"texto": "Mensagem exclusiva do Cenário!"},
        )
        self.assertEqual(MensagemArea.objects.filter(area="Cenário").count(), 1)
        self.assertEqual(MensagemArea.objects.filter(area="Staff").count(), 0)

        resp_cenario = self.client.get(reverse("chat_area", args=["Cenário"]))
        self.assertEqual(resp_cenario.status_code, 200)
        self.assertContains(resp_cenario, "Mensagem exclusiva do Cenário!")

        # Membro de outra área (Staff) não vê a mensagem no chat de Staff e não acessa Cenário
        self.client.post(reverse("login"), {"matricula": self.membro_staff.matricula, "senha": self.senha})
        resp_staff = self.client.get(reverse("chat_area", args=["Staff"]))
        self.assertEqual(resp_staff.status_code, 200)
        self.assertNotContains(resp_staff, "Mensagem exclusiva do Cenário!")

        resp_bloqueado = self.client.get(reverse("chat_area", args=["Cenário"]))
        self.assertRedirects(resp_bloqueado, reverse("feed"))

    def test_reply_and_like_in_area_chat(self):
        self.client.post(reverse("login"), {"matricula": self.membro_cenario_1.matricula, "senha": self.senha})
        msg_original = MensagemArea.objects.create(
            usuario=self.membro_cenario_2,
            area="Cenário",
            texto="Vamos ganhar esse ano!",
        )

        # Responder à mensagem
        self.client.post(
            reverse("publicar_chat_area", args=["Cenário"]),
            {"texto": "Vamos!!!!!", "resposta_a": str(msg_original.id)},
        )
        resposta = MensagemArea.objects.filter(area="Cenário", texto="Vamos!!!!!").first()
        self.assertIsNotNone(resposta)
        self.assertEqual(resposta.resposta_a_id, msg_original.id)

        # Curtir a mensagem
        resp_like = self.client.post(reverse("curtir_mensagem_area", args=[msg_original.id]))
        self.assertEqual(resp_like.status_code, 200)
        self.assertEqual(resp_like.json(), {"curtido": True, "curtidas": 1})


class PerfilTests(TestCase):
    def setUp(self):
        self.senha = "Senha123"
        self.membro = Usuario.objects.create(
            nome="João Dias",
            matricula="202450",
            senha=make_password(self.senha),
            diretoria="Diatinf",
            areas="Cenário,Staff",
            aprovado=True,
            bio="Participante da equipe de Cenário!",
        )
        self.sublider = Usuario.objects.create(
            nome="Maria Joaquina",
            matricula="202451",
            senha=make_password(self.senha),
            diretoria="Diatinf",
            areas="Cenário",
            aprovado=True,
            sub_lider=True,
            sublider_de="Cenário",
        )
        DoacaoTampinhas.objects.create(usuario=self.membro, quantidade_gramas=1500)

    def test_cadastro_saves_nome(self):
        response = self.client.post(reverse("cadastro"), {
            "nome": "Cirilo Jr.",
            "matricula": "202488",
            "senha": "Senha123",
            "diretoria": "Diatinf",
            "areas": ["Cenário"],
        })
        self.assertRedirects(response, reverse("login"))
        novo = Usuario.objects.get(matricula="202488")
        self.assertEqual(novo.nome, "Cirilo Jr.")

    def test_meu_perfil_and_edit_nome_and_bio(self):
        self.client.post(reverse("login"), {"matricula": self.membro.matricula, "senha": self.senha})
        resp = self.client.get(reverse("meu_perfil"))
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "João Dias")
        self.assertContains(resp, "202450")
        self.assertContains(resp, "Membro")
        self.assertContains(resp, "1.5Kg")
        self.assertContains(resp, "secao-editar-perfil")

        # Editar nome e bio
        resp_edit = self.client.post(reverse("editar_perfil"), {
            "nome": "João Dias Silva",
            "bio": "Nova bio atualizada no perfil!",
        })
        self.assertRedirects(resp_edit, reverse("meu_perfil"))
        self.membro.refresh_from_db()
        self.assertEqual(self.membro.nome, "João Dias Silva")
        self.assertEqual(self.membro.bio, "Nova bio atualizada no perfil!")

    def test_other_user_can_view_profile_readonly(self):
        self.client.post(reverse("login"), {"matricula": self.membro.matricula, "senha": self.senha})
        resp = self.client.get(reverse("ver_perfil", args=[self.sublider.id]))
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "Maria Joaquina")
        self.assertContains(resp, "202451")
        self.assertContains(resp, "Sub-Líder")
        self.assertNotContains(resp, "secao-editar-perfil")

    def test_profile_does_not_show_feed_posts_or_duplicate_cargo_card(self):
        Publicacao.objects.create(usuario=self.membro, texto="Postagem exclusiva do feed")
        self.client.post(reverse("login"), {"matricula": self.membro.matricula, "senha": self.senha})
        resp = self.client.get(reverse("meu_perfil"))
        self.assertEqual(resp.status_code, 200)
        self.assertNotContains(resp, "Publicações no Feed")
        self.assertNotContains(resp, "Postagem exclusiva do feed")
        self.assertNotContains(resp, "Cargo &amp; Matrícula")
        self.assertNotContains(resp, "Cargo & Matrícula")
        self.assertContains(resp, "Contribuição com Tampinhas")

    def test_area_request_displays_member_name_in_admin_panel(self):
        admin = Usuario.objects.create(
            nome="Líder Geral",
            matricula="admin",
            senha=make_password(self.senha),
            diretoria="Líder",
            areas="",
            aprovado=True,
        )
        SolicitacaoArea.objects.create(usuario=self.membro, area="Cenário")

        # Sub-líder vê o nome do solicitante
        self.client.post(reverse("login"), {"matricula": self.sublider.matricula, "senha": self.senha})
        resp_sub = self.client.get(reverse("painel_administrativo"))
        self.assertContains(resp_sub, "João Dias")
        self.assertContains(resp_sub, "202450")

        # Admin também vê o nome do solicitante na seção de solicitações de áreas
        self.client.post(reverse("login"), {"matricula": admin.matricula, "senha": self.senha})
        resp_adm = self.client.get(reverse("painel_administrativo"))
        self.assertContains(resp_adm, "João Dias")
        self.assertContains(resp_adm, "202450")

    def test_sublider_can_delete_completed_task_but_not_active_task(self):
        tarefa_ativa = Tarefa.objects.create(
            titulo="Tarefa Ativa Cenário",
            descricao="Em andamento",
            limite_participantes=2,
            criada_por=self.sublider,
            area="Cenário",
            encerrada=False,
        )
        tarefa_concluida = Tarefa.objects.create(
            titulo="Tarefa Concluída Cenário",
            descricao="Finalizada",
            limite_participantes=2,
            criada_por=self.sublider,
            area="Cenário",
            encerrada=True,
            concluida=True,
        )

        self.client.post(reverse("login"), {"matricula": self.sublider.matricula, "senha": self.senha})

        # Não deve excluir tarefa ativa
        resp_ativa = self.client.post(reverse("excluir_tarefa_concluida", args=[tarefa_ativa.id]))
        self.assertRedirects(resp_ativa, reverse("painel_administrativo"))
        self.assertTrue(Tarefa.objects.filter(id=tarefa_ativa.id).exists())

        # Deve excluir tarefa já encerrada/concluída
        resp_concl = self.client.post(reverse("excluir_tarefa_concluida", args=[tarefa_concluida.id]))
        self.assertRedirects(resp_concl, reverse("painel_administrativo"))
        self.assertFalse(Tarefa.objects.filter(id=tarefa_concluida.id).exists())

    def test_profile_pluralization_and_scoped_notifications(self):
        self.client.post(reverse("login"), {"matricula": self.membro.matricula, "senha": self.senha})

        # 1 doação registrada no setUp -> deve exibir "1 doação" (e não "1 doaçãoões")
        resp_perfil = self.client.get(reverse("meu_perfil"))
        self.assertContains(resp_perfil, "(1 doação)")
        self.assertNotContains(resp_perfil, "doaçãoões")

        # Ao atualizar o perfil, a notificação não deve vazar caso o usuário navegue para outra página (ex: /feed/)
        self.client.post(reverse("editar_perfil"), {
            "nome": "João Dias",
            "bio": "Bio atualizada",
        })
        resp_feed = self.client.get(reverse("feed"))
        self.assertNotContains(resp_feed, "Perfil atualizado com sucesso!")

        # E ao atualizar o perfil seguindo diretamente para /perfil/, aparece apenas uma vez
        resp_follow = self.client.post(reverse("editar_perfil"), {
            "nome": "João Dias",
            "bio": "Bio atualizada 2",
        }, follow=True)
        self.assertContains(resp_follow, "Perfil atualizado com sucesso!")

        # Navegações subsequentes para /perfil/ ou /tampinhas/ não repetem a notificação
        resp_perfil_depois = self.client.get(reverse("meu_perfil"))
        self.assertNotContains(resp_perfil_depois, "Perfil atualizado com sucesso!")
        resp_tampinhas = self.client.get(reverse("tampinhas"))
        self.assertNotContains(resp_tampinhas, "Perfil atualizado com sucesso!")


class SubliderPanelAndMetaTampinhasTests(TestCase):
    def setUp(self):
        self.senha = "Senha123"
        self.admin = Usuario.objects.create(
            nome="Líder Geral",
            matricula="admin",
            senha=make_password(self.senha),
            diretoria="Líder",
            areas="",
            aprovado=True,
        )
        self.sub_cenario = Usuario.objects.create(
            nome="Sub Cenário",
            matricula="202460",
            senha=make_password(self.senha),
            diretoria="Diatinf",
            areas="Cenário",
            aprovado=True,
            sub_lider=True,
            sublider_de="Cenário",
        )
        self.sub_tampinhas = Usuario.objects.create(
            nome="Sub Tampinhas",
            matricula="202461",
            senha=make_password(self.senha),
            diretoria="Diaren",
            areas="Tampinhas",
            aprovado=True,
            sub_lider=True,
            sublider_de="Tampinhas",
        )
        self.membro_cenario_staff = Usuario.objects.create(
            nome="Membro Cenário e Staff",
            matricula="202462",
            senha=make_password(self.senha),
            diretoria="Diatinf",
            areas="Cenário,Staff",
            aprovado=True,
        )
        self.membro_tampinhas = Usuario.objects.create(
            nome="Membro Tampinhas",
            matricula="202463",
            senha=make_password(self.senha),
            diretoria="Diaren",
            areas="Tampinhas",
            aprovado=True,
        )
        self.membro_apenas_staff = Usuario.objects.create(
            nome="Membro Exclusivo Staff",
            matricula="202464",
            senha=make_password(self.senha),
            diretoria="Diacin",
            areas="Staff",
            aprovado=True,
        )

    def test_member_counter_and_list_isolated_per_area(self):
        # Líder geral vê todos os 6 usuários aprovados
        self.client.post(reverse("login"), {"matricula": "admin", "senha": self.senha})
        resp_admin = self.client.get(reverse("painel_administrativo"))
        self.assertEqual(resp_admin.context["total_membros"], 6)
        self.assertContains(resp_admin, "Membro Cenário e Staff")
        self.assertContains(resp_admin, "Membro Tampinhas")
        self.assertContains(resp_admin, "Membro Exclusivo Staff")
        stats_admin = self.client.get(reverse("stats_painel")).json()
        self.assertEqual(stats_admin["membros"], 6)

        # Sub-líder de Cenário vê apenas os 2 membros de Cenário (sub_cenario + membro_cenario_staff)
        self.client.post(reverse("login"), {"matricula": "202460", "senha": self.senha})
        resp_cenario = self.client.get(reverse("painel_administrativo"))
        self.assertEqual(resp_cenario.context["total_membros"], 2)
        self.assertContains(resp_cenario, "Sub Cenário")
        self.assertContains(resp_cenario, "Membro Cenário e Staff")
        self.assertNotContains(resp_cenario, "Membro Tampinhas")
        self.assertNotContains(resp_cenario, "Membro Exclusivo Staff")
        self.assertContains(resp_cenario, "202462 - Cenário")
        stats_cenario = self.client.get(reverse("stats_painel")).json()
        self.assertEqual(stats_cenario["membros"], 2)

        # Sub-líder de Tampinhas vê apenas os 2 membros de Tampinhas na seção Membros
        self.client.post(reverse("login"), {"matricula": "202461", "senha": self.senha})
        resp_tamp = self.client.get(reverse("painel_administrativo"))
        self.assertEqual(resp_tamp.context["total_membros"], 2)
        stats_tamp = self.client.get(reverse("stats_painel")).json()
        self.assertEqual(stats_tamp["membros"], 2)

    def test_sublider_can_remove_member_from_own_area_without_deleting_user(self):
        self.client.post(reverse("login"), {"matricula": "202460", "senha": self.senha})
        # Tenta remover membro de outra área -> bloqueado
        self.client.post(reverse("remover_membro", args=[self.membro_apenas_staff.id]))
        self.membro_apenas_staff.refresh_from_db()
        self.assertEqual(self.membro_apenas_staff.areas, "Staff")

        # Remove membro_cenario_staff da área Cenário -> preserva Staff e mantém usuário no banco
        self.client.post(reverse("remover_membro", args=[self.membro_cenario_staff.id]))
        self.membro_cenario_staff.refresh_from_db()
        self.assertEqual(self.membro_cenario_staff.areas, "Staff")
        resp_cenario = self.client.get(reverse("painel_administrativo"))
        self.assertEqual(resp_cenario.context["total_membros"], 1)

    def test_tampinhas_goal_definition_replacement_and_progress_bar(self):
        # Sub-líder de Cenário e Admin não podem alterar a meta de Tampinhas
        self.client.post(reverse("login"), {"matricula": "202460", "senha": self.senha})
        self.client.post(reverse("definir_meta_tampinhas"), {"meta_kg": "60"})
        self.assertEqual(MetaTampinhas.objects.count(), 0)

        self.client.post(reverse("login"), {"matricula": "admin", "senha": self.senha})
        self.client.post(reverse("definir_meta_tampinhas"), {"meta_kg": "60"})
        self.assertEqual(MetaTampinhas.objects.count(), 0)

        # Sub-líder de Tampinhas define meta de 50Kg e depois substitui por 80Kg
        self.client.post(reverse("login"), {"matricula": "202461", "senha": self.senha})
        self.client.post(reverse("definir_meta_tampinhas"), {"meta_kg": "50"})
        self.assertEqual(MetaTampinhas.objects.count(), 1)
        self.assertEqual(MetaTampinhas.objects.first().meta_kg, Decimal("50.000"))

        self.client.post(reverse("definir_meta_tampinhas"), {"meta_kg": "80"})
        self.assertEqual(MetaTampinhas.objects.count(), 1)
        self.assertEqual(MetaTampinhas.objects.first().meta_kg, Decimal("80.000"))

        # Registra 20.000g (20Kg) de doação -> 25% da meta de 80Kg
        self.client.post(reverse("registrar_doacao"), {
            "membro_id": self.membro_tampinhas.id,
            "quantidade": "20000",
        })

        resp_ranking = self.client.get(reverse("tampinhas"))
        self.assertEqual(resp_ranking.status_code, 200)
        self.assertEqual(resp_ranking.context["total_geral_kg"], "20Kg")
        self.assertEqual(resp_ranking.context["meta_kg"], Decimal("80.000"))
        self.assertEqual(resp_ranking.context["meta_kg_formatada"], "80Kg")
        self.assertEqual(resp_ranking.context["progresso_porcentagem"], 25.0)
        self.assertContains(resp_ranking, "20Kg")
        self.assertContains(resp_ranking, "80Kg")
        self.assertContains(resp_ranking, "width: 25.00%;")






