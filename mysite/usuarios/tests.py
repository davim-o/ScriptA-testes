from decimal import Decimal
import struct
import zlib
from unittest.mock import patch
from django.contrib.auth.hashers import make_password
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.urls import reverse

from .models import (
    ParticipacaoTarefa, Tarefa, Usuario, DoacaoTampinhas,
    MensagemArea, CurtidaMensagemArea, SolicitacaoArea, Publicacao, MetaTampinhas,
    ObservacaoTarefa, TarefaConclusao,
)
from .context_processors import gerar_token_usuario, decodificar_token_usuario
from .suap import identificar_diretoria_e_curso, _extrair_info_dados_suap
from .templatetags.usuarios_extras import formatar_texto
from .views import formatar_kg, META_TAMPINHAS_KG


def _png_1x1_valido():
    def _chunk(tag, data):
        return struct.pack(">I", len(data)) + tag + data + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF)
    ihdr = struct.pack(">IIBBBBB", 1, 1, 8, 2, 0, 0, 0)
    idat = zlib.compress(b"\x00\xff\x00\x00")
    return b"\x89PNG\r\n\x1a\n" + _chunk(b"IHDR", ihdr) + _chunk(b"IDAT", idat) + _chunk(b"IEND", b"")


PNG_1X1_VALIDO = _png_1x1_valido()


def _mock_suap_offline(*args, **kwargs):
    return {
        "sucesso": False,
        "autenticado_suap": False,
        "credenciais_invalidas": False,
        "nome": None,
        "diretoria": None,
        "curso": None,
        "campus": None,
        "erro": None,
    }


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


@patch("usuarios.views.consultar_api_suap", side_effect=_mock_suap_offline)
class CadastroTests(TestCase):
    dados = {
        "matricula": "202499",
        "senha": "Senha123",
        "diretoria": "Diaren",
    }

    def test_area_and_nome_are_optional(self, mock_suap):
        response = self.client.post(reverse("cadastro"), self.dados)
        self.assertRedirects(response, reverse("login"))
        self.assertTrue(Usuario.objects.filter(matricula="202499").exists())

    def test_wrong_diretoria_for_suap_matricula_notifies_user(self, mock_suap):
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

    def test_duplicate_matricula_is_rejected(self, mock_suap):
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


class TokenAndLogoutSecurityTests(TestCase):
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

    def test_token_is_not_exposed_in_url_or_html_and_query_token_is_rejected(self):
        resp_login = self.client.post(
            reverse("login"),
            {"matricula": "admin", "senha": self.senha},
        )
        self.assertEqual(resp_login.status_code, 302)
        self.assertNotIn("_user_token", resp_login["Location"])

        token_202409 = gerar_token_usuario(self.sublider_202409.id, self.sublider_202409.session_version)
        # Mesmo enviando _user_token na querystring, não deve trocar o usuário autenticado na sessão
        response = self.client.get(
            reverse("painel_administrativo"),
            {"_user_token": token_202409},
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["usuario"].matricula, "admin")
        self.assertNotContains(response, "_user_token")

    def test_logout_revokes_session_and_invalidates_prior_token(self):
        self.client.post(reverse("login"), {"matricula": "202409", "senha": self.senha})
        self.sublider_202409.refresh_from_db()
        session = self.client.session
        token_antes = gerar_token_usuario(
            self.sublider_202409.id,
            self.sublider_202409.session_version,
            session.get("session_nonce", ""),
        )
        self.assertIsNotNone(decodificar_token_usuario(token_antes))

        resp_sair = self.client.get(reverse("sair"))
        self.assertRedirects(resp_sair, reverse("login"))

        # Após logout, sessão e token anterior ficam inválidos
        self.assertIsNone(decodificar_token_usuario(token_antes))
        resp_protegido = self.client.get(reverse("painel_administrativo"))
        self.assertRedirects(resp_protegido, reverse("login"))


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

    @patch("usuarios.views.consultar_api_suap", side_effect=_mock_suap_offline)
    def test_cadastro_saves_nome(self, mock_suap):
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


class SuapAndPasswordTests(TestCase):
    def test_classificacao_diretoria_cnat_courses(self):
        self.assertEqual(identificar_diretoria_e_curso("20241001", "Técnico Integrado em Administração")[0], "Diatinf")
        self.assertEqual(identificar_diretoria_e_curso("20241002", "Informática para Internet")[0], "Diatinf")
        self.assertEqual(identificar_diretoria_e_curso("20241003", "Controle Ambiental")[0], "Diaren")
        self.assertEqual(identificar_diretoria_e_curso("20241004", "Técnico em Geologia")[0], "Diaren")
        self.assertEqual(identificar_diretoria_e_curso("20241005", "Mineração")[0], "Diaren")
        self.assertEqual(identificar_diretoria_e_curso("20241009", "Saneamento Ambiental")[0], "Diaren")
        self.assertEqual(identificar_diretoria_e_curso("20241006", "Edificações")[0], "Diacon")
        self.assertEqual(identificar_diretoria_e_curso("20241007", "Eletrotécnica")[0], "Diacin")
        self.assertEqual(identificar_diretoria_e_curso("20241008", "Mecânica Industrial")[0], "Diacin")
        self.assertEqual(identificar_diretoria_e_curso("20241010", "Técnico em Petróleo e Gás")[0], "Diacin")
        self.assertEqual(identificar_diretoria_e_curso("20241011", "Técnico em Segurança do Trabalho")[0], "Diacin")

        # Matrícula sem suposição fixa de curso não deve chutar Diacin nem nenhuma outra diretoria
        dir_2024, _ = identificar_diretoria_e_curso("20241013010032")
        self.assertIsNone(dir_2024)

        # Disciplina genérica Informática Básica no boletim não pode sobrepor curso técnico de Edificações
        dir_bol, _ = identificar_diretoria_e_curso(
            "20251099990001",
            extras_texto="Informática Básica | Desenho Técnico e Edificações | Construção de Edifícios",
        )
        self.assertEqual(dir_bol, "Diacon")

        info = _extrair_info_dados_suap({
            "nome_usual": "Ana Costa",
            "vinculo": {"curso": "Controle Ambiental", "campus": "CNAT"},
        })
        self.assertEqual(info["nome"], "Ana Costa")
        self.assertEqual(info["curso"], "Controle Ambiental")
        self.assertEqual(info["campus"], "CNAT")

    @patch("usuarios.suap._em_ambiente_teste", return_value=False)
    @patch("usuarios.suap._fazer_requisicao_json")
    def test_consultar_api_suap_identifica_aluno_via_ensino_meus_dados_aluno(self, mock_req, mock_teste):
        from .suap import consultar_api_suap

        def fake_suap(url, method="GET", headers=None, payload=None, timeout=6.0):
            if url.endswith("/api/token/pair") and method == "POST":
                return 200, {"access": "tok_alu", "refresh": "ref"}
            if "/api/rh/eu/" in url:
                return 200, {
                    "identificacao": "20241013010032",
                    "nome_usual": "Maria Souza",
                    "campus": "CNAT",
                    "tipo_usuario": "Aluno",
                }
            if "/api/rh/meus-vinculos/" in url:
                return 200, {"results": []}
            if "/api/ensino/meus-dados-aluno/" in url:
                return 200, {"curso": "Técnico de Nível Médio em Mecânica Integrado", "matriz": "2025"}
            return 404, None

        mock_req.side_effect = fake_suap
        res = consultar_api_suap("20241013010032", "SenhaSuap123")
        self.assertTrue(res["autenticado_suap"])
        self.assertEqual(res["diretoria"], "Diacin")
        self.assertIn("Mecânica", res["curso"])
        self.assertEqual(res["nome"], "Maria Souza")

    @patch("usuarios.views.consultar_api_suap")
    def test_cadastro_uses_suap_data_diretoria_and_same_password(self, mock_suap):
        mock_suap.return_value = {
            "autenticado_suap": True,
            "credenciais_invalidas": False,
            "offline": False,
            "matricula_oficial": "20241099000011",
            "nome": "Aluno Teste Diaren",
            "diretoria": "Diaren",
            "curso": "Técnico em Controle Ambiental",
            "campus": "CNAT",
        }
        resp = self.client.post(reverse("cadastro"), {
            "matricula": "20241099000011",
            "senha": "MinhaSenhaSuap99",
            "diretoria": "Diatinf",  # Diretoria real do SUAP (Diaren) deve prevalecer
        })
        self.assertRedirects(resp, reverse("login"))
        user = Usuario.objects.get(matricula="20241099000011")
        self.assertEqual(user.diretoria, "Diaren")
        self.assertEqual(user.curso, "Técnico em Controle Ambiental")
        self.assertEqual(user.nome, "Aluno Teste Diaren")
        # Mesmo usuário consegue logar com a mesma senha do SUAP
        resp_login = self.client.post(reverse("login"), {
            "matricula": "20241099000011",
            "senha": "MinhaSenhaSuap99",
        })
        self.assertRedirects(resp_login, reverse("feed"))

    @patch("usuarios.views.consultar_api_suap")
    def test_cadastro_aceita_dados_suap_cors_quando_backend_offline(self, mock_suap):
        mock_suap.return_value = {
            "autenticado_suap": False,
            "credenciais_invalidas": False,
            "offline": True,
            "erro": "Proxy bloqueado",
        }
        resp = self.client.post(reverse("cadastro"), {
            "matricula": "20241013010032",
            "senha": "SenhaAluno123",
            "diretoria": "Diatinf",  # Deve ser sobrescrita pelo curso real validado no servidor
            "suap_verificado_cliente": "1",
            "suap_nome": "Lucas Mendes",
            "suap_curso": "Técnico de Nível Médio em Controle Ambiental",
        })
        self.assertRedirects(resp, reverse("login"))
        user = Usuario.objects.get(matricula="20241013010032")
        self.assertEqual(user.diretoria, "Diaren")
        self.assertEqual(user.nome, "Lucas Mendes")

    @patch("usuarios.views.consultar_api_suap")
    def test_cadastro_rejects_invalid_suap_credentials(self, mock_suap):
        mock_suap.return_value = {
            "sucesso": False,
            "autenticado_suap": False,
            "credenciais_invalidas": True,
            "nome": None,
            "diretoria": None,
            "curso": None,
            "campus": None,
            "erro": "Matrícula ou senha do SUAP incorreta.",
        }
        resp = self.client.post(reverse("cadastro"), {
            "matricula": "20241099000022",
            "senha": "SenhaErradaSuap",
            "diretoria": "Diaren",
        })
        self.assertContains(resp, "Matrícula ou senha do SUAP incorreta.")
        self.assertFalse(Usuario.objects.filter(matricula="20241099000022").exists())


class FeedReplyAndMediaTests(TestCase):
    def setUp(self):
        self.senha = "Senha123"
        self.autor = Usuario.objects.create(
            matricula="202471",
            nome="Alice",
            senha=make_password(self.senha),
            diretoria="Diaren",
            areas="Cenário",
            aprovado=True,
        )
        self.outro = Usuario.objects.create(
            matricula="202472",
            nome="Bruno",
            senha=make_password(self.senha),
            diretoria="Diatinf",
            areas="Cenário",
            aprovado=True,
        )

    def test_feed_reply_and_image_upload(self):
        self.client.post(reverse("login"), {"matricula": self.autor.matricula, "senha": self.senha})
        img_pub = SimpleUploadedFile("foto_feed.png", PNG_1X1_VALIDO, content_type="image/png")
        resp = self.client.post(reverse("publicar"), {"texto": "", "imagem": img_pub})
        self.assertRedirects(resp, reverse("feed"))
        pub_orig = Publicacao.objects.first()
        self.assertIsNotNone(pub_orig)
        self.assertTrue(bool(pub_orig.imagem))

        # Outro usuário responde à publicação
        self.client.post(reverse("login"), {"matricula": self.outro.matricula, "senha": self.senha})
        self.client.post(reverse("publicar"), {"texto": "Muito bom!", "resposta_a": str(pub_orig.id)})

        # Autor original vê destaque de resposta para ele
        self.client.post(reverse("login"), {"matricula": self.autor.matricula, "senha": self.senha})
        resp_feed = self.client.get(reverse("feed"))
        self.assertEqual(len(resp_feed.context["respostas_para_mim"]), 1)
        self.assertContains(resp_feed, "Respondeu a você")
        self.assertContains(resp_feed, "Responderam a você")

    def test_chat_area_and_observacao_image_upload(self):
        self.client.post(reverse("login"), {"matricula": self.autor.matricula, "senha": self.senha})
        img_chat = SimpleUploadedFile("chat.png", PNG_1X1_VALIDO, content_type="image/png")
        resp_chat = self.client.post(
            reverse("publicar_chat_area", args=["Cenário"]),
            {"texto": "Foto no chat", "imagem": img_chat},
        )
        self.assertRedirects(resp_chat, reverse("chat_area", args=["Cenário"]))
        msg = MensagemArea.objects.first()
        self.assertIsNotNone(msg)
        self.assertTrue(bool(msg.imagem))

        tarefa = Tarefa.objects.create(
            titulo="Tarefa Obs",
            descricao="Desc",
            limite_participantes=3,
            criada_por=self.outro,
            area="Cenário",
        )
        ParticipacaoTarefa.objects.create(usuario=self.autor, tarefa=tarefa)
        img_obs = SimpleUploadedFile("obs.png", PNG_1X1_VALIDO, content_type="image/png")
        resp_obs = self.client.post(
            reverse("adicionar_observacao", args=["Cenário", tarefa.id]),
            {"texto": "", "imagem": img_obs},
        )
        self.assertEqual(resp_obs.status_code, 302)
        obs = ObservacaoTarefa.objects.filter(tarefa=tarefa).first()
        self.assertIsNotNone(obs)
        self.assertTrue(bool(obs.imagem))


class TaskLimitsFormattingAndTampinhasPrecisionTests(TestCase):
    def setUp(self):
        self.senha = "Senha123"
        self.sublider = Usuario.objects.create(
            matricula="202481",
            senha=make_password(self.senha),
            diretoria="Diatinf",
            areas="Tampinhas",
            aprovado=True,
            sub_lider=True,
            sublider_de="Tampinhas",
        )
        self.membro = Usuario.objects.create(
            matricula="202482",
            nome="Carla",
            senha=make_password(self.senha),
            diretoria="Diatinf",
            areas="Tampinhas",
            aprovado=True,
        )

    def test_create_task_allows_large_title_and_description_with_line_breaks(self):
        self.client.post(reverse("login"), {"matricula": self.sublider.matricula, "senha": self.senha})
        titulo_grande = "T" * 160
        desc_grande = "Linha 1\n\n  Linha 3 com recuo\n" + ("A" * 3000)
        resp = self.client.post(reverse("criar_tarefa"), {
            "titulo": titulo_grande,
            "tipo": "prolongada",
            "descricao": desc_grande,
            "limite_participantes": "5",
        })
        self.assertRedirects(resp, reverse("painel_administrativo"))
        tarefa = Tarefa.objects.get(titulo=titulo_grande)
        self.assertEqual(len(tarefa.descricao), len(desc_grande))
        html_fmt = str(formatar_texto("Linha 1\n\n  Linha 3"))
        self.assertIn("<br>", html_fmt)
        self.assertIn("&nbsp;&nbsp;Linha 3", html_fmt)

    def test_registrar_doacao_by_typed_matricula_and_ranking_one_decimal(self):
        self.client.post(reverse("login"), {"matricula": self.sublider.matricula, "senha": self.senha})
        resp = self.client.post(reverse("registrar_doacao"), {
            "matricula": self.membro.matricula,
            "quantidade": "1255",
        })
        self.assertRedirects(resp, reverse("painel_administrativo"))
        self.assertTrue(DoacaoTampinhas.objects.filter(usuario=self.membro, quantidade_gramas=1255).exists())

        resp_rank = self.client.get(reverse("tampinhas"))
        # 1.255 Kg arredondado para 1 casa decimal no ranking e total geral => 1.3Kg
        self.assertEqual(resp_rank.context["total_geral_kg"], "1.3Kg")
        self.assertContains(resp_rank, "1.3Kg")

    def test_editar_perfil_upload_and_remove_banner(self):
        self.client.post(reverse("login"), {"matricula": self.membro.matricula, "senha": self.senha})
        banner = SimpleUploadedFile("banner.png", PNG_1X1_VALIDO, content_type="image/png")
        resp = self.client.post(reverse("editar_perfil"), {
            "nome": "Carla Atualizada",
            "bio": "Bio",
            "banner": banner,
        })
        self.assertRedirects(resp, reverse("meu_perfil"))
        self.membro.refresh_from_db()
        self.assertTrue(bool(self.membro.banner and self.membro.banner.name))

        self.client.post(reverse("editar_perfil"), {
            "nome": "Carla Atualizada",
            "bio": "Bio",
            "remover_banner": "1",
        })
        self.membro.refresh_from_db()
        self.assertFalse(bool(self.membro.banner and self.membro.banner.name))







