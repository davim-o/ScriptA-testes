from django.db import models

class Usuario(models.Model):

    nome=models.CharField(max_length=100, blank=True, default="")
    matricula=models.CharField(max_length=20, unique=True)
    senha=models.CharField(max_length=255)
    diretoria=models.CharField(max_length=50)
    areas=models.TextField()
    aprovado=models.BooleanField(default=True)
    sub_lider=models.BooleanField(default=False)
    sublider_de=models.CharField(max_length=50, null=True, blank=True)
    doacao_tampinhas=models.FloatField(default=0)
    foto=models.ImageField(upload_to="perfis/", null=True, blank=True)
    banner=models.ImageField(upload_to="banners/", null=True, blank=True)
    bio=models.TextField(blank=True, default="")
    curso=models.CharField(max_length=150, blank=True, default="")
    session_version=models.PositiveIntegerField(default=1)

    def nome_exibicao(self):
        if self.nome and self.nome.strip():
            return self.nome.strip()
        return self.matricula

    def inicial_perfil(self):
        base = (self.nome_exibicao() or "U").strip()
        return base[0].upper() if base else "U"

    def cargo_tag(self):
        if self.eh_administrador():
            return "ADM"
        if self.sub_lider:
            return "Sub-Líder"
        return "Membro"

    def cargo_detalhado(self):
        if self.eh_administrador():
            return "Administrador Geral"
        if self.sub_lider and self.sublider_de:
            return f"Sub-Líder • {self.sublider_de}"
        if self.sub_lider:
            return "Sub-Líder"
        return "Membro"

    def cargo_classe(self):
        if self.eh_administrador():
            return "tag-adm"
        if self.sub_lider:
            return "tag-sublider"
        return "tag-membro"

    def total_tampinhas_gramas(self):
        from decimal import Decimal
        tot_g = self.doacoes_tampinhas.aggregate(tot=models.Sum("quantidade_gramas"))["tot"]
        if tot_g is None and self.doacao_tampinhas and self.doacao_tampinhas > 0:
            tot_g = int(Decimal(str(self.doacao_tampinhas)) * Decimal("1000"))
        return tot_g or 0

    def total_tampinhas_formatado(self):
        from decimal import Decimal
        tot_g = self.total_tampinhas_gramas()
        d = Decimal(tot_g) / Decimal("1000")
        s = f"{d:.3f}".rstrip("0").rstrip(".")
        if not s or s == "-0":
            s = "0"
        return f"{s}Kg"

    def eh_administrador(self):
        from .suap import MATRICULAS_ADM_FIXAS
        mat = (self.matricula or "").strip().lower()
        diret = (self.diretoria or "").strip().lower()
        return mat in MATRICULAS_ADM_FIXAS or diret in ["líder", "lider", "líder geral", "lider geral"]

    def curso_exibicao(self):
        if self.eh_administrador():
            return ""
        if self.curso and self.curso.strip():
            return self.curso.strip()
        from .suap import identificar_diretoria_e_curso
        _, curso = identificar_diretoria_e_curso(self.matricula)
        return curso or ""

    def tem_acesso_painel(self):
        return self.eh_administrador() or self.sub_lider

    def get_areas_list(self):
        if self.areas:
            return [a.strip() for a in self.areas.split(",") if a.strip()]
        return []

    def get_areas_ordenadas(self):
        areas = self.get_areas_list()
        if self.sub_lider and self.sublider_de and self.sublider_de in areas:
            areas = [self.sublider_de] + [a for a in areas if a != self.sublider_de]
        return areas

    def get_areas_sidebar(self):
        if self.eh_administrador():
            return ["Cenário", "Staff", "Dança", "Figurino", "Sonoplastia", "Tampinhas", "Roteiro"]
        return self.get_areas_ordenadas()

    def tem_acesso_area(self, area):
        if self.eh_administrador():
            return True
        if self.sub_lider and self.sublider_de == area:
            return True
        return area in self.get_areas_list()

    def __str__(self):
        return self.matricula


class Publicacao(models.Model):

    usuario=models.ForeignKey(Usuario, on_delete=models.CASCADE, related_name="publicacoes")
    texto=models.TextField(blank=True, default="")
    imagem=models.ImageField(upload_to="feed/", null=True, blank=True)
    resposta_a=models.ForeignKey(
        "self",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="respostas",
    )
    data=models.DateTimeField(auto_now_add=True)
    editado=models.BooleanField(default=False)

    def total_curtidas(self):
        return self.curtidas.count()

    def __str__(self):
        return f"{self.usuario.matricula} - {self.id}"


class Curtida(models.Model):

    usuario=models.ForeignKey(Usuario, on_delete=models.CASCADE)
    publicacao=models.ForeignKey(Publicacao, on_delete=models.CASCADE, related_name="curtidas")

    class Meta:
        unique_together=("usuario","publicacao")

    def __str__(self):
        return f"{self.usuario.matricula} curtiu {self.publicacao.id}"





class Tarefa(models.Model):

    TIPO_CHOICES = [("fixa","Rápida"),("prolongada","Prolongada")]

    titulo=models.CharField(max_length=200)
    tipo=models.CharField(max_length=20, choices=TIPO_CHOICES, default="fixa")
    area=models.CharField(max_length=50, blank=True)

    # Fixa
    data=models.DateField(null=True, blank=True)
    horario=models.TimeField(null=True, blank=True)

    # Prolongada
    data_inicio=models.DateField(null=True, blank=True)
    data_fim=models.DateField(null=True, blank=True)

    descricao=models.TextField(blank=True)
    limite_participantes=models.IntegerField(default=2)
    imagem=models.ImageField(upload_to="tarefas/", null=True, blank=True)
    encerrada=models.BooleanField(default=False)
    concluida=models.BooleanField(default=False)

    criada_por=models.ForeignKey(Usuario, on_delete=models.CASCADE, related_name="tarefas_criadas")
    criada_em=models.DateTimeField(auto_now_add=True)

    def participacoes_validas(self):
        # O criador (sub-líder) não conta como participante: ele já participa
        # de todas as tarefas que cria.
        return self.participacoes.exclude(usuario_id=self.criada_por_id)

    def total_participantes(self):
        return self.participacoes_validas().count()

    def total_conclusoes(self):
        return self.conclusoes.exclude(usuario_id=self.criada_por_id).count()

    def eh_criador(self, usuario):
        return usuario is not None and usuario.id == self.criada_por_id

    def tem_vaga(self):
        return self.total_participantes() < self.limite_participantes

    def __str__(self):
        return self.titulo


class ParticipacaoTarefa(models.Model):

    usuario=models.ForeignKey(Usuario, on_delete=models.CASCADE, related_name="participacoes")
    tarefa=models.ForeignKey(Tarefa, on_delete=models.CASCADE, related_name="participacoes")
    inscrito_em=models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together=("usuario","tarefa")

    def __str__(self):
        return f"{self.usuario.matricula} em {self.tarefa.titulo}"


class SolicitacaoArea(models.Model):

    usuario=models.ForeignKey(Usuario, on_delete=models.CASCADE, related_name="solicitacoes_area")
    area=models.CharField(max_length=50)
    solicitado_em=models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together=("usuario","area")

    def __str__(self):
        return f"{self.usuario.matricula} solicitou {self.area}"


class ObservacaoTarefa(models.Model):

    usuario=models.ForeignKey(Usuario, on_delete=models.CASCADE, related_name="observacoes")
    tarefa=models.ForeignKey(Tarefa, on_delete=models.CASCADE, related_name="observacoes")
    texto=models.TextField(blank=True, default="")
    imagem=models.ImageField(upload_to="observacoes/", null=True, blank=True)
    criada_em=models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.usuario.matricula} obs em {self.tarefa.titulo}"


class ConclusaoTarefa(models.Model):

    usuario=models.ForeignKey(Usuario, on_delete=models.CASCADE, related_name="conclusoes")
    tarefa=models.ForeignKey(Tarefa, on_delete=models.CASCADE, related_name="conclusoes")
    imagem=models.ImageField(upload_to="conclusoes/", null=True, blank=True)
    comentario=models.TextField(blank=True)
    criada_em=models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together=("usuario","tarefa")

    def __str__(self):
        return f"{self.usuario.matricula} concluiu {self.tarefa.titulo}"


class DoacaoTampinhas(models.Model):
    usuario = models.ForeignKey(Usuario, on_delete=models.CASCADE, related_name="doacoes_tampinhas")
    quantidade_gramas = models.PositiveIntegerField()
    registrado_por = models.ForeignKey(Usuario, on_delete=models.SET_NULL, null=True, blank=True, related_name="doacoes_registradas")
    data_registro = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-data_registro"]

    def __str__(self):
        return f"{self.quantidade_gramas}g para {self.usuario.matricula}"


class MensagemArea(models.Model):
    usuario = models.ForeignKey(Usuario, on_delete=models.CASCADE, related_name="mensagens_area")
    area = models.CharField(max_length=50)
    texto = models.TextField(blank=True, default="")
    imagem = models.ImageField(upload_to="chat/", null=True, blank=True)
    resposta_a = models.ForeignKey(
        "self",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="respostas",
    )
    criada_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-criada_em"]

    def total_curtidas(self):
        return self.curtidas.count()

    def __str__(self):
        return f"[{self.area}] {self.usuario.matricula} - {self.id}"


class CurtidaMensagemArea(models.Model):
    usuario = models.ForeignKey(Usuario, on_delete=models.CASCADE, related_name="curtidas_mensagem_area")
    mensagem = models.ForeignKey(MensagemArea, on_delete=models.CASCADE, related_name="curtidas")

    class Meta:
        unique_together = ("usuario", "mensagem")

    def __str__(self):
        return f"{self.usuario.matricula} curtiu msg {self.mensagem_id}"


class MetaTampinhas(models.Model):
    meta_kg = models.DecimalField(max_digits=10, decimal_places=3, default=40.0)
    atualizado_por = models.ForeignKey(
        Usuario,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="metas_tampinhas_definidas",
    )
    atualizado_em = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Meta de Tampinhas: {self.meta_kg}Kg"


