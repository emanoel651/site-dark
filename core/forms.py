from django import forms
from .models import CategoriaVideo, CategoriaMusica

VOZES_NARRADOR = [
    ('pt-BR-Wavenet-A', 'Feminina - Voz A (Padrão)'),
    ('pt-BR-Wavenet-C', 'Feminina - Voz C'),
    ('pt-BR-Wavenet-D', 'Feminina - Voz D'),
    ('pt-BR-Wavenet-B', 'Masculina - Voz B (Padrão)'),
    ('pt-BR-Neural2-B', 'Masculina - Voz Neural'),
]

TONS_VOZ = [(2.0, 'Agudo'), (0.0, 'Normal'), (-2.0, 'Grave')]
PLANO_DE_FUNDO_CHOICES = [('normal', 'Normal / Escuro'), ('claro', 'Claro')]

# --- MAIS OPÇÕES DE FONTE ---
FONTES_TEXTO = [
    ('arial', 'Arial Bold'), # <-- ALTERADO AQUI
    ('times', 'Times New Roman'),
    ('courier', 'Courier New'),
    ('impact', 'Impact'),
    ('verdana', 'Verdana'),
    ('georgia', 'Georgia'),
    ('cunia', 'Cunia (Decorativa)'),
]
# --- FIM DAS NOVAS OPÇÕES ---

class GeradorForm(forms.Form):
    plano_de_fundo = forms.ChoiceField(
        choices=PLANO_DE_FUNDO_CHOICES,
        label="Plano de Fundo (para cor da fonte)"
    )
    categoria_video = forms.ModelChoiceField(queryset=CategoriaVideo.objects.all(), label="Categoria do Vídeo")
    categoria_musica = forms.ModelChoiceField(queryset=CategoriaMusica.objects.all(), label="Categoria da Música")
    texto_overlay = forms.CharField(widget=forms.Textarea, required=False, label="Texto para sobrepor no vídeo")
    
    texto_fonte = forms.ChoiceField(
        choices=FONTES_TEXTO,
        label="Tipo de Letra do Texto"
    )
    texto_tamanho = forms.IntegerField(
        min_value=20,
        max_value=100,
        initial=50,
        label="Tamanho da Letra"
    )
    
    texto_negrito = forms.BooleanField(required=False, label="Negrito")
    texto_sublinhado = forms.BooleanField(required=False, label="Sublinhado")

    duracao_segundos = forms.IntegerField(min_value=10, max_value=60, initial=30, label="Duração (em segundos)")
    loop_video = forms.BooleanField(required=False, label="Repetir o vídeo (loop)?")
    narrador_texto = forms.CharField(
        widget=forms.Textarea,
        required=False,
        label="Texto do Narrador",
    )
    narrador_voz = forms.ChoiceField(
        choices=VOZES_NARRADOR,
        label="Voz do Narrador"
    )
    narrador_velocidade = forms.IntegerField(
        min_value=80,
        max_value=120,
        initial=105,
        label="Velocidade da Narração (%)",
        help_text="100% é a velocidade normal. Mais alto é mais rápido."
    )
    narrador_tom = forms.ChoiceField(
        choices=TONS_VOZ,
        initial=0.0,
        label="Tom da Narração"
    )
    volume_musica = forms.IntegerField(
        min_value=0,
        max_value=100,
        initial=50,
        label="Volume da Música de Fundo (%)",
    )
