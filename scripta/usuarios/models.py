from django.db import models

class Usuario(models.Model):

    matricula = models.CharField(max_length=20, unique=True)

    senha = models.CharField(max_length=255)

    diretoria = models.CharField(max_length=50)

    areas = models.TextField()

    def __str__(self):
        return self.matricula