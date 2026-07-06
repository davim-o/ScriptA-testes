from django.db import models


class Usuario(models.Model):

    matricula = models.CharField(
        max_length=20,
        unique=True
    )

    senha = models.CharField(
        max_length=255
    )

    diretoria = models.CharField(
        max_length=50
    )

    areas = models.TextField()

    def __str__(self):
        return self.matricula


class Publicacao(models.Model):

    usuario = models.ForeignKey(
        Usuario,
        on_delete=models.CASCADE
    )

    texto = models.TextField()

    data = models.DateTimeField(
        auto_now_add=True
    )

    def __str__(self):
        return self.usuario.matricula


class Curtida(models.Model):

    usuario = models.ForeignKey(
        Usuario,
        on_delete=models.CASCADE
    )

    publicacao = models.ForeignKey(
        Publicacao,
        on_delete=models.CASCADE
    )

    class Meta:

        unique_together = (
            "usuario",
            "publicacao"
        )

    def __str__(self):
        return f"{self.usuario.matricula} - {self.publicacao.id}"