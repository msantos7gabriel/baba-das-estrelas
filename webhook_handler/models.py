from datetime import time
from django.utils import timezone
from django.db import models


class Baba(models.Model):
    nome = models.CharField(max_length=100, default="Baba das Estrelas")
    hora_inicio = models.TimeField(default=time(19, 0), blank=True, null=True)
    hora_fim = models.TimeField(default=time(23, 30), blank=True, null=True)
    local = models.CharField(max_length=50, default='Luis Viana')
    descrição = models.CharField(
        max_length=200, default='Baba na quadra do Luis Viana das 7 as 11 e 30')
    
    # Dia que o baba começa 
    dia = models.DateField(default=timezone.now, blank=True, null=True)

    # Data de Criação do Baba
    data = models.DateTimeField(auto_now_add=True, editable=True)

    # Limite de pessoas dentro de uma baba
    limite_linha = models.IntegerField(default=16)
    limite_gol = models.IntegerField(default=4)

    # Ver se o baba Está ativo
    is_active = models.BooleanField(default=False)
    def __str__(self):
        return f"{self.nome}"  # em {self.data.strftime('%d/%m/%Y %H:%M:%S')


class Jogador(models.Model):
    class Posicao(models.TextChoices):
        LINHA = 'L', 'Linha'
        GOLEIRO = 'G', 'Goleiro'
        AMBOS = 'A', 'Linha e Gol'

    nome = models.CharField(max_length=100)
    id_whatsapp = models.CharField(max_length=20)
    baba = models.ForeignKey(Baba, on_delete=models.CASCADE,
                             related_name='jogadores', null=True, blank=True)
    estrelas = models.FloatField(default=1)
    posicao = models.CharField(max_length=1, default=Posicao.LINHA)
    jogara = models.CharField(max_length=1, default=Posicao.LINHA)
    is_admin = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.nome}"

    def get_posição(self):
        if self.posicao == 'A':
            return self.Posicao.AMBOS.label
        elif self.posicao == 'G':
            return self.Posicao.GOLEIRO.label
        else:
            return self.Posicao.LINHA.label

    class Meta:
        verbose_name = "Jogador"
        verbose_name_plural = "Jogadores"
