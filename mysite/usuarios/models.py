from django.db import models

class Usuario(models.Model):

    matricula=models.CharField(
        max_length=20,
        unique=True
    )

    senha=models.CharField(
        max_length=255
    )

    diretoria=models.CharField(
        max_length=50
    )

    areas=models.TextField()

    aprovado=models.BooleanField(
        default=True
    )

    sub_lider=models.BooleanField(
        default=False
    )

    sublider_de=models.CharField(
        max_length=50,
        null=True,
        blank=True
    )

    doacao_tampinhas=models.FloatField(
        default=0
    )

    def eh_administrador(self):
        return self.matricula=="admin" or self.diretoria=="Líder"

    def tem_acesso_painel(self):
        return self.eh_administrador() or self.sub_lider

    def get_areas_list(self):
        if self.areas:
            return [a.strip() for a in self.areas.split(",") if a.strip()]
        return []

    def __str__(self):
        return self.matricula


class Publicacao(models.Model):

    usuario=models.ForeignKey(
        Usuario,
        on_delete=models.CASCADE,
        related_name="publicacoes"
    )

    texto=models.TextField()

    data=models.DateTimeField(
        auto_now_add=True
    )

    editado=models.BooleanField(
        default=False
    )

    def total_curtidas(self):
        return self.curtidas.count()

    def __str__(self):
        return f"{self.usuario.matricula} - {self.id}"


class Curtida(models.Model):

    usuario=models.ForeignKey(
        Usuario,
        on_delete=models.CASCADE
    )

    publicacao=models.ForeignKey(
        Publicacao,
        on_delete=models.CASCADE,
        related_name="curtidas"
    )

    class Meta:
        unique_together=("usuario","publicacao")

    def __str__(self):
        return f"{self.usuario.matricula} curtiu {self.publicacao.id}"


class Tarefa(models.Model):

    TIPO_CHOICES = [
        ("fixa", "Fixa"),
        ("prolongada", "Prolongada"),
    ]

    titulo=models.CharField(max_length=200)

    tipo=models.CharField(
        max_length=20,
        choices=TIPO_CHOICES,
        default="fixa"
    )

    # Campos para tarefa FIXA
    data=models.DateField(null=True, blank=True)
    horario=models.TimeField(null=True, blank=True)

    # Campos para tarefa PROLONGADA
    data_inicio=models.DateField(null=True, blank=True)
    data_fim=models.DateField(null=True, blank=True)

    descricao=models.TextField(blank=True)

    limite_participantes=models.IntegerField(default=2)

    area=models.CharField(max_length=50, blank=True)

    encerrada=models.BooleanField(default=False)

    criada_por=models.ForeignKey(
        Usuario,
        on_delete=models.CASCADE,
        related_name="tarefas_criadas"
    )

    criada_em=models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.titulo
