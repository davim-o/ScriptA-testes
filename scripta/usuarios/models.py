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

    doacao_tampinhas=models.FloatField(
        default=0
    )

    def eh_administrador(self):
        return self.matricula=="admin" or self.diretoria=="Líder"

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