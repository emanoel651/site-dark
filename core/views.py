import subprocess
import random
import os
import platform
import textwrap
import re
from django.shortcuts import render, redirect
from django.http import HttpResponse
from django.contrib.auth.decorators import login_required
from .forms import GeradorForm
from .models import VideoBase, MusicaBase, VideoGerado
from django.conf import settings
from google.cloud import texttospeech_v1beta1 as texttospeech  # Alterado para v1beta1 para suportar timepoints
from PIL import Image, ImageDraw, ImageFont

# Lembre-se de autenticar o gcloud localmente, esta linha deve ficar comentada
# os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = os.path.join(settings.BASE_DIR, 'gcloud-auth.json')

FONT_PATHS = {
    'Windows': {
        'cunia': os.path.join(settings.BASE_DIR, 'core', 'static', 'fonts', 'Cunia.ttf'),
        'arial': 'C:/Windows/Fonts/arial.ttf',
        'arialbd': 'C:/Windows/Fonts/arialbd.ttf',
    },
    'Linux': { 'arial': '/usr/share/fonts/truetype/msttcorefonts/Arial.ttf', },
}

def create_text_image(texto, cor_da_fonte, data):
    """Cria uma imagem PNG transparente com o texto formatado usando Pillow."""
    target_size = (1080, 1920)
    w, h = target_size
    sistema_op = platform.system()
    nome_fonte = data.get('texto_fonte', 'cunia')
    caminho_da_fonte = FONT_PATHS.get(sistema_op, {}).get(nome_fonte, FONT_PATHS['Windows']['cunia'])
    tamanho_fonte = data.get('texto_tamanho', 70)
    
    try:
        if data.get('texto_negrito', False):
            if nome_fonte == 'arial': caminho_da_fonte = FONT_PATHS[sistema_op].get('arialbd', caminho_da_fonte)
        font = ImageFont.truetype(caminho_da_fonte, size=tamanho_fonte)
    except Exception:
        print(f"AVISO: Fonte '{caminho_da_fonte}' não encontrada. A usar fonte padrão.")
        font = ImageFont.load_default(size=tamanho_fonte)
    
    texto_quebrado = textwrap.fill(texto, width=30)
    
    img = Image.new("RGBA", target_size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    
    espacamento_entre_linhas = 15
    bbox = draw.textbbox((0, 0), texto_quebrado, font=font, align="center", spacing=espacamento_entre_linhas)
    text_w, text_h = bbox[2] - bbox[0], bbox[3] - bbox[1]
    x, y = (w - text_w) / 2, (h - text_h) / 2
    
    cor_rgba = (0, 0, 0, 255) if cor_da_fonte == 'black' else (255, 255, 255, 255)
    
    draw.text((x + 2, y + 2), texto_quebrado, font=font, fill=(0, 0, 0, 128), align="center", spacing=espacamento_entre_linhas)
    draw.text((x, y), texto_quebrado, font=font, fill=cor_rgba, align="center", spacing=espacamento_entre_linhas)
    
    if data.get('texto_sublinhado', False):
        num_linhas = len(texto_quebrado.split('\n'))
        altura_total_texto_sem_espaco = text_h - (espacamento_entre_linhas * (num_linhas - 1))
        altura_linha_unica = altura_total_texto_sem_espaco / num_linhas
        
        for i, linha_texto in enumerate(texto_quebrado.split('\n')):
            linha_y = y + (i * (altura_linha_unica + espacamento_entre_linhas))
            bbox_linha = draw.textbbox((0, 0), linha_texto, font=font)
            largura_linha = bbox_linha[2] - bbox_linha[0]
            x_linha = (w - largura_linha) / 2
            underline_y = linha_y + altura_linha_unica + 2
            draw.line((x_linha, underline_y, x_linha + largura_linha, underline_y), fill=cor_rgba, width=2)

    temp_dir = os.path.join(settings.MEDIA_ROOT, 'text_temp')
    os.makedirs(temp_dir, exist_ok=True)
    caminho_imagem_texto = os.path.join(temp_dir, f"texto_{random.randint(1000,9999)}.png")
    img.save(caminho_imagem_texto)
    return caminho_imagem_texto


def gerar_audio_e_tempos(texto, nome_da_voz, velocidade, tom, obter_tempos=False):
    print(f"--- A gerar áudio. Obter tempos: {obter_tempos} ---")
    try:
        client = texttospeech.TextToSpeechClient()
        
        if obter_tempos:
            palavras = texto.split()
            ssml_texto = "<speak>"
            for i, palavra in enumerate(palavras):
                ssml_texto += f'{palavra} <mark name="word_{i}"/> '
            ssml_texto += "</speak>"
            synthesis_input = texttospeech.SynthesisInput(ssml=ssml_texto)
        else:
            synthesis_input = texttospeech.SynthesisInput(text=texto)

        voice = texttospeech.VoiceSelectionParams(language_code="pt-BR", name=nome_da_voz)
        audio_config = texttospeech.AudioConfig(
            audio_encoding=texttospeech.AudioEncoding.MP3,
            speaking_rate=velocidade / 100.0, 
            pitch=float(tom)
        )
        
        request = texttospeech.SynthesizeSpeechRequest(
            input=synthesis_input,
            voice=voice,
            audio_config=audio_config
        )
        
        if obter_tempos:
            request.enable_time_pointing = [texttospeech.SynthesizeSpeechRequest.TimepointType.SSML_MARK]

        response = client.synthesize_speech(request=request)
        
        timepoints = response.timepoints if obter_tempos else None
        
        narrador_temp_dir = os.path.join(settings.MEDIA_ROOT, 'narrador_temp')
        os.makedirs(narrador_temp_dir, exist_ok=True)
        nome_arquivo_narrador = f"narrador_{random.randint(10000, 99999)}.mp3"
        caminho_narrador_input = os.path.join(narrador_temp_dir, nome_arquivo_narrador)
        with open(caminho_narrador_input, "wb") as out: 
            out.write(response.audio_content)
            
        return caminho_narrador_input, timepoints
    except Exception as e:
        print(f"--- ERRO GERAL AO GERAR ÁUDIO DO NARRADOR ---")
        print(e)
        return None, None


def formatar_tempo_ass(segundos):
    """Formata segundos para o padrão de tempo do .ASS (H:MM:SS.cs)."""
    h = int(segundos // 3600)
    m = int((segundos % 3600) // 60)
    s = int(segundos % 60)
    cs = int((segundos - int(segundos)) * 100)
    return f"{h}:{m:02d}:{s:02d}.{cs:02d}"


def gerar_ficheiro_legenda_ass(timepoints, texto_original, data, cor_da_fonte):
    """Gera um arquivo de legenda no formato .ASS a partir dos timepoints, com efeito de karaoke."""
    sistema_op = platform.system()
    nome_fonte = data.get('texto_fonte', 'cunia')
    caminho_fonte = FONT_PATHS.get(sistema_op, {}).get(nome_fonte, FONT_PATHS['Windows']['cunia'])
    nome_fonte_ass = os.path.splitext(os.path.basename(caminho_fonte))[0].replace('_', ' ')
    
    tamanho = data.get('texto_tamanho', 70)
    negrito = -1 if data.get('texto_negrito', False) else 0
    sublinhado = -1 if data.get('texto_sublinhado', False) else 0
    
    if cor_da_fonte == 'white':
        cor_primaria = '&H808080'  # Cinza (não falado)
        cor_secundaria = '&HFFFFFF'  # Branco (falado/destaque)
        cor_outline = '&H000000'  # Contorno preto
    else:
        cor_primaria = '&H808080'  # Cinza
        cor_secundaria = '&H000000'  # Preto
        cor_outline = '&HFFFFFF'  # Contorno branco
    
    cor_back = '&H00000000'  # Transparente
    
    header = (
        f"[Script Info]\nTitle: Video Gerado\nScriptType: v4.00+\nPlayResX: 1080\nPlayResY: 1920\n\n"
        f"[V4+ Styles]\n"
        f"Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding\n"
        f"Style: Default,{nome_fonte_ass},{tamanho},{cor_primaria},{cor_secundaria},{cor_outline},{cor_back},{negrito},0,{sublinhado},0,100,100,0,0,1,2,2,5,10,10,10,1\n\n"
        f"[Events]\nFormat: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text\n"
    )

    palavras = texto_original.split()
    if not timepoints or len(timepoints) != len(palavras):
        print(f"--- AVISO: Número de timepoints ({len(timepoints)}) não corresponde ao número de palavras ({len(palavras)}). Legenda não gerada. ---")
        return None

    texto_quebrado = textwrap.fill(texto_original, width=30)
    linhas = texto_quebrado.splitlines()
    
    linhas_dialogo = []
    word_index = 0
    
    for linha in linhas:
        words_in_line = linha.split()
        num_words = len(words_in_line)
        if num_words == 0:
            continue
        
        start_time = 0.0 if word_index == 0 else timepoints[word_index - 1].time_seconds
        end_time = timepoints[word_index + num_words - 1].time_seconds
        
        karaoke_text = ""
        prev_time = start_time
        for j in range(num_words):
            tp = timepoints[word_index + j]
            dur = tp.time_seconds - prev_time
            dur_cs = max(1, int(dur * 100))  # Pelo menos 1 centissegundo
            word = words_in_line[j]
            karaoke_text += f"{{\\k{dur_cs}}}{word} "
            prev_time = tp.time_seconds
        
        karaoke_text = karaoke_text.strip()
        
        start_str = formatar_tempo_ass(start_time)
        end_str = formatar_tempo_ass(end_time)
        
        linhas_dialogo.append(f"Dialogue: 0,{start_str},{end_str},Default,,0,0,0,,{karaoke_text}")
        
        word_index += num_words

    conteudo_ass = header + "\n".join(linhas_dialogo)
    legenda_temp_dir = os.path.join(settings.MEDIA_ROOT, 'legenda_temp')
    os.makedirs(legenda_temp_dir, exist_ok=True)
    caminho_legenda = os.path.join(legenda_temp_dir, f"legenda_{random.randint(1000,9999)}.ass")
    with open(caminho_legenda, 'w', encoding='utf-8') as f: f.write(conteudo_ass)
    return caminho_legenda


def preview_voz(request, nome_da_voz):
    """Gera um preview de áudio de uma voz específica."""
    texto_exemplo = "Esta é uma demonstração da minha voz."
    try:
        client = texttospeech.TextToSpeechClient()
        synthesis_input = texttospeech.SynthesisInput(text=texto_exemplo)
        voice = texttospeech.VoiceSelectionParams(language_code="pt-BR", name=nome_da_voz)
        audio_config = texttospeech.AudioConfig(audio_encoding=texttospeech.AudioEncoding.MP3)
        response = client.synthesize_speech(input=synthesis_input, voice=voice, audio_config=audio_config)
        return HttpResponse(response.audio_content, content_type='audio/mpeg')
    except Exception as e:
        print(f"--- ERRO AO GERAR PREVIEW DA VOZ: {nome_da_voz} ---"); print(e)
        return HttpResponse(status=500)


@login_required
def pagina_gerador(request):
    if request.method == 'POST':
        form = GeradorForm(request.POST)
        if form.is_valid():
            data = form.cleaned_data
            caminho_narrador_input, timepoints, caminho_legenda_ass, caminho_imagem_texto = None, None, None, None
            
            obter_tempos = data.get('legenda_sincronizada', False) and data.get('narrador_texto')

            if data.get('narrador_texto'):
                caminho_narrador_input, timepoints = gerar_audio_e_tempos(
                    data['narrador_texto'], data['narrador_voz'],
                    data['narrador_velocidade'], data['narrador_tom'],
                    obter_tempos=obter_tempos
                )

            video_base = VideoBase.objects.filter(categoria=data['categoria_video']).order_by('?').first()
            musica_base = MusicaBase.objects.filter(categoria=data['categoria_musica']).order_by('?').first()
            if not video_base or not musica_base:
                return redirect('pagina_gerador')

            caminho_video_input = video_base.arquivo_video.path
            caminho_musica_input = musica_base.arquivo_musica.path
            nome_arquivo_saida = f"video_{request.user.id}_{random.randint(1000, 9999)}.mp4"
            caminho_video_output = os.path.join(settings.MEDIA_ROOT, 'videos_gerados', nome_arquivo_saida)
            os.makedirs(os.path.dirname(caminho_video_output), exist_ok=True)

            cmd = ['ffmpeg', '-y']
            if data.get('loop_video', False):
                cmd.extend(['-stream_loop', '-1', '-i', caminho_video_input])
            else:
                cmd.extend(['-i', caminho_video_input])
            
            cor_da_fonte = 'black' if data.get('plano_de_fundo') == 'claro' else 'white'

            video_filter_parts = []
            audio_filter_parts = []
            input_files = []
            map_audio = ""
            
            # Mapeamento de streams
            video_map_idx = 0
            text_map_idx = -1
            music_map_idx = -1
            narrator_map_idx = -1

            if obter_tempos and timepoints and caminho_narrador_input:
                caminho_legenda_ass = gerar_ficheiro_legenda_ass(timepoints, data['narrador_texto'], data, cor_da_fonte)
                if caminho_legenda_ass:
                    caminho_legenda_ffmpeg = caminho_legenda_ass.replace('\\', '/').replace(':', '\\:')
                    video_filter_parts.append(f"[{video_map_idx}:v]scale=1080:1920:force_original_aspect_ratio=decrease,pad=1080:1920:-1:-1,setsar=1,ass='{caminho_legenda_ffmpeg}'[v]")
                else:
                    video_filter_parts.append(f"[{video_map_idx}:v]scale=1080:1920:force_original_aspect_ratio=decrease,pad=1080:1920:-1:-1,setsar=1[v]")
            elif data.get('texto_overlay'):
                caminho_imagem_texto = create_text_image(data['texto_overlay'], cor_da_fonte, data)
                input_files.append(caminho_imagem_texto)
                text_map_idx = len(input_files)
                video_filter_parts.append(f"[{video_map_idx}:v]scale=1080:1920:force_original_aspect_ratio=decrease,pad=1080:1920:-1:-1,setsar=1[base];[base][{text_map_idx}:v]overlay=(W-w)/2:(H-h)/2[v]")
            else:
                video_filter_parts.append(f"[{video_map_idx}:v]scale=1080:1920:force_original_aspect_ratio=decrease,pad=1080:1920:-1:-1,setsar=1[v]")
            
            input_files.append(caminho_musica_input)
            music_map_idx = len(input_files)
            if caminho_narrador_input:
                input_files.append(caminho_narrador_input)
                narrator_map_idx = len(input_files)
            
            volume_musica_decimal = data.get('volume_musica', 50) / 100.0
            if narrator_map_idx != -1:
                audio_filter_parts.append(f"[{music_map_idx}:a]volume={volume_musica_decimal}[a1];[{narrator_map_idx}:a]volume=1.0[a2];[a1][a2]amix=inputs=2:duration=longest[aout]")
                map_audio = "-map [aout]"
            else:
                audio_filter_parts.append(f"[{music_map_idx}:a]volume={volume_musica_decimal}[aout]")
                map_audio = "-map [aout]"

            for f in input_files:
                cmd.extend(['-i', f])

            filter_complex_str = f"{''.join(video_filter_parts)}{';' if video_filter_parts and audio_filter_parts else ''}{''.join(audio_filter_parts)}"
            
            cmd.extend(['-filter_complex', filter_complex_str])
            cmd.extend(['-map', '[v]'])
            if map_audio:
                cmd.extend(map_audio.split(' '))
            
            cmd.extend([
                '-t', str(data.get('duracao_segundos', 30)), 
                '-c:v', 'libx264', '-pix_fmt', 'yuv420p', '-c:a', 'aac', '-b:a', '192k', 
                '-shortest'
            ])
            cmd.append(caminho_video_output)
            
            try:
                print("--- A executar o comando FFmpeg ---"); print(' '.join(cmd))
                resultado = subprocess.run(cmd, check=True, text=True, capture_output=True, encoding='utf-8')
                
                VideoGerado.objects.create(
                    usuario=request.user,
                    status='CONCLUIDO',
                    arquivo_final=os.path.join('videos_gerados', nome_arquivo_saida),
                    # ... (preencha os outros campos do modelo aqui)
                )
            except subprocess.CalledProcessError as e:
                print(f"--- ERRO NO FFMPEG ---")
                print(f"Comando que falhou: {' '.join(e.cmd)}")
                print(f"Saída de Erro (stderr):\n{e.stderr}")
                VideoGerado.objects.create(usuario=request.user, status='ERRO', texto_overlay=data.get('texto_overlay', ''))
            finally:
                if caminho_narrador_input and os.path.exists(caminho_narrador_input): os.remove(caminho_narrador_input)
                if caminho_legenda_ass and os.path.exists(caminho_legenda_ass): os.remove(caminho_legenda_ass)
                if caminho_imagem_texto and os.path.exists(caminho_imagem_texto): os.remove(caminho_imagem_texto)

            return redirect('meus_videos')
    else:
        form = GeradorForm()

    return render(request, 'core/gerador.html', {'form': form})

# --- VIEWS DAS PÁGINAS ESTÁTICAS ---
@login_required
def meus_videos(request):
    videos = VideoGerado.objects.filter(usuario=request.user).order_by('-criado_em')
    return render(request, 'core/meus_videos.html', {'videos': videos})
def index(request):
    return render(request, 'core/home.html')
def como_funciona(request):
    return render(request, 'core/como_funciona.html')
def planos(request):
    return render(request, 'core/planos.html')
def cadastre_se(request):
    return render(request, 'core/cadastre-se.html')
def login_view(request):
    return render(request, 'core/login.html')
def suporte(request):
    return render(request, 'core/suporte.html')