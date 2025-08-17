from django.db import models
from django.contrib.auth.models import User

class CategoriaVideo(models.Model):
    nome = models.CharField(max_length=100, unique=True)
    def __str__(self): return self.nome

class CategoriaMusica(models.Model):
    nome = models.CharField(max_length=100, unique=True)
    def __str__(self): return self.nome

class VideoBase(models.Model):
    titulo = models.CharField(max_length=200)
    categoria = models.ForeignKey(CategoriaVideo, on_delete=models.PROTECT)
    arquivo_video = models.FileField(upload_to='videos_base/')
    def __str__(self): return self.titulo

class MusicaBase(models.Model):
    titulo = models.CharField(max_length=200)
    categoria = models.ForeignKey(CategoriaMusica, on_delete=models.PROTECT)
    arquivo_musica = models.FileField(upload_to='musicas_base/')
    def __str__(self): return self.titulo

class VideoGerado(models.Model):
    STATUS_CHOICES = [('PROCESSANDO', 'Processando'), ('CONCLUIDO', 'Concluído'), ('ERRO', 'Erro')]
    usuario = models.ForeignKey(User, on_delete=models.CASCADE)
    texto_overlay = models.TextField(blank=True, null=True)
    duracao_minutos = models.IntegerField(default=1)
    loop = models.BooleanField(default=False)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PROCESSANDO')
    arquivo_final = models.FileField(upload_to='videos_gerados/', blank=True, null=True)
    criado_em = models.DateTimeField(auto_now_add=True)
    narrador_texto = models.TextField(blank=True, null=True)
    volume_musica = models.IntegerField(default=70)
    narrador_voz = models.CharField(max_length=50, default='pt-BR-Wavenet-B')
    narrador_velocidade = models.IntegerField(default=100)
    narrador_tom = models.FloatField(default=0.0)
    plano_de_fundo = models.CharField(max_length=10, default='normal')
    texto_fonte = models.CharField(max_length=50, default='arial')
    texto_tamanho = models.IntegerField(default=50)
    texto_negrito = models.BooleanField(default=False)
    texto_sublinhado = models.BooleanField(default=False)

    # --- CAMPO EM FALTA ADICIONADO AQUI ---
    legenda_sincronizada = models.BooleanField(default=False)
    # --- FIM DO CAMPO ADICIONADO ---

    def __str__(self):
        return f"Vídeo de {self.usuario.username} - {self.status}"
