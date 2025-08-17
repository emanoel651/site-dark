import subprocess
import random
import os
import platform
import textwrap
from django.shortcuts import render, redirect
from django.http import HttpResponse
from django.contrib.auth.decorators import login_required
from .forms import GeradorForm
from .models import VideoBase, MusicaBase, VideoGerado
from django.conf import settings
from google.cloud import texttospeech
from PIL import Image, ImageDraw, ImageFont

os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = os.path.join(settings.BASE_DIR, 'gcloud-auth.json')

FONT_PATHS = {
    'Windows': {
        'arial': 'C:/Windows/Fonts/arial.ttf',
        'arialbd': 'C:/Windows/Fonts/arialbd.ttf',
        'times': 'C:/Windows/Fonts/times.ttf',
        'timesbd': 'C:/Windows/Fonts/timesbd.ttf',
        'courier': 'C:/Windows/Fonts/cour.ttf',
        'impact': 'C:/Windows/Fonts/impact.ttf',
        'verdana': 'C:/Windows/Fonts/verdana.ttf',
        'georgia': 'C:/Windows/Fonts/georgia.ttf',
        'cunia': os.path.join(settings.BASE_DIR, 'core', 'static', 'fonts', 'Cunia.ttf'),
    },
    'Linux': { 'arial': '/usr/share/fonts/truetype/msttcorefonts/Arial.ttf', },
}

def create_text_image(texto, cor_da_fonte, data):
    """Cria uma imagem PNG transparente com o texto formatado usando Pillow."""
    target_size = (1080, 1920)
    w, h = target_size
    sistema_op = platform.system()
    nome_fonte = data['texto_fonte']
    caminho_da_fonte = FONT_PATHS.get(sistema_op, {}).get(nome_fonte, FONT_PATHS['Windows']['arial'])
    tamanho_fonte = data['texto_tamanho']
    try:
        if data['texto_negrito']:
            if nome_fonte == 'arial': caminho_da_fonte = FONT_PATHS[sistema_op].get('arialbd', caminho_da_fonte)
            elif nome_fonte == 'times': caminho_da_fonte = FONT_PATHS[sistema_op].get('timesbd', caminho_da_fonte)
        font = ImageFont.truetype(caminho_da_fonte, size=tamanho_fonte)
    except Exception:
        print(f"AVISO: Fonte '{caminho_da_fonte}' não encontrada. A usar fonte padrão.")
        font = ImageFont.load_default()
    
    texto_quebrado = textwrap.fill(texto, width=30)
    img = Image.new("RGBA", target_size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    
    espacamento_entre_linhas = 15
    bbox = draw.textbbox((0, 0), texto_quebrado, font=font, align="center", spacing=espacamento_entre_linhas)
    text_w, text_h = bbox[2] - bbox[0], bbox[3] - bbox[1]
    x, y = (w - text_w) / 2, (h - text_h) / 2
    
    cor_rgba = (0, 0, 0, 255) if cor_da_fonte == 'black' else (255, 255, 255, 255)
    
    # Desenha o texto com sombra para melhor legibilidade
    draw.text((x + 2, y + 2), texto_quebrado, font=font, fill=(0, 0, 0, 128), align="center", spacing=espacamento_entre_linhas)
    draw.text((x, y), texto_quebrado, font=font, fill=cor_rgba, align="center", spacing=espacamento_entre_linhas)
    
    if data['texto_sublinhado']:
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
    # ... (código igual ao anterior)
    print(f"--- A gerar áudio. Obter tempos: {obter_tempos} ---")
    try:
        client = texttospeech.TextToSpeechClient()
        synthesis_input = texttospeech.SynthesisInput(text=texto)
        voice = texttospeech.VoiceSelectionParams(language_code="pt-BR", name=nome_da_voz)
        audio_config = texttospeech.AudioConfig(
            audio_encoding=texttospeech.AudioEncoding.MP3,
            speaking_rate=velocidade / 100.0, pitch=float(tom)
        )
        response, timepoints = None, None
        can_get_timepoints = hasattr(texttospeech, 'SynthesizeSpeechRequest')
        if obter_tempos and can_get_timepoints:
            try:
                request = texttospeech.SynthesizeSpeechRequest(
                    input=synthesis_input, voice=voice, audio_config=audio_config,
                    enable_time_pointing=[texttospeech.SynthesizeSpeechRequest.TimepointType.WORD]
                )
                response = client.synthesize_speech(request=request)
                timepoints = response.timepoints
            except Exception: response = None
        if response is None:
            response = client.synthesize_speech(input=synthesis_input, voice=voice, audio_config=audio_config)
        
        narrador_temp_dir = os.path.join(settings.MEDIA_ROOT, 'narrador_temp')
        os.makedirs(narrador_temp_dir, exist_ok=True)
        nome_arquivo_narrador = f"narrador_{random.randint(10000, 99999)}.mp3"
        caminho_narrador_input = os.path.join(narrador_temp_dir, nome_arquivo_narrador)
        with open(caminho_narrador_input, "wb") as out: out.write(response.audio_content)
        return caminho_narrador_input, timepoints
    except Exception as e:
        print(f"--- ERRO GERAL AO GERAR ÁUDIO DO NARRADOR ---"); print(e)
        return None, None

def gerar_ficheiro_legenda_ass(timepoints, data, cor_da_fonte):
    # ... (código igual ao anterior)
    sistema_op = platform.system(); nome_fonte = data['texto_fonte']
    caminho_fonte = FONT_PATHS.get(sistema_op, {}).get(nome_fonte, FONT_PATHS['Windows']['arial'])
    nome_fonte_ass = os.path.splitext(os.path.basename(caminho_fonte))[0].replace('_', ' ')
    tamanho = data['texto_tamanho']; negrito = -1 if data['texto_negrito'] else 0
    sublinhado = -1 if data['texto_sublinhado'] else 0
    cor_primaria = f"&H00FFFFFF" if cor_da_fonte == 'white' else f"&H00000000"
    header = f"[Script Info]\nTitle: Video Gerado\nScriptType: v4.00+\nPlayResX: 1080\nPlayResY: 1920\n\n[V4+ Styles]\nFormat: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding\nStyle: Default,{nome_fonte_ass},{tamanho},{cor_primaria},&H000000FF,&H00000000,&H99000000,{negrito},0,{sublinhado},0,100,100,0,0,1,2,2,5,10,10,10,1\n\n[Events]\nFormat: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text\n"
    linhas_dialogo = [f"Dialogue: 0,{formatar_tempo_ass(p.time_seconds)},{formatar_tempo_ass(p.time_seconds + 1.5)},Default,,0,0,0,,{p.word}" for p in timepoints]
    conteudo_ass = header + "\n".join(linhas_dialogo)
    legenda_temp_dir = os.path.join(settings.MEDIA_ROOT, 'legenda_temp')
    os.makedirs(legenda_temp_dir, exist_ok=True)
    caminho_legenda = os.path.join(legenda_temp_dir, f"legenda_{random.randint(1000,9999)}.ass")
    with open(caminho_legenda, 'w', encoding='utf-8') as f: f.write(conteudo_ass)
    return caminho_legenda

def formatar_tempo_ass(segundos):
    h = int(segundos // 3600); m = int((segundos % 3600) // 60); s = int(segundos % 60)
    cs = int((segundos - int(segundos)) * 100)
    return f"{h}:{m:02d}:{s:02d}.{cs:02d}"

def preview_voz(request, nome_da_voz):
    # ... (código igual ao anterior)
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
            
            if data['narrador_texto']:
                caminho_narrador_input, timepoints = gerar_audio_e_tempos(
                    data['narrador_texto'], data['narrador_voz'],
                    data['narrador_velocidade'], data['narrador_tom'],
                    obter_tempos=data.get('acompanhar_texto', False)
                )

            video_base = VideoBase.objects.filter(categoria=data['categoria_video']).order_by('?').first()
            musica_base = MusicaBase.objects.filter(categoria=data['categoria_musica']).order_by('?').first()
            if not video_base or not musica_base: return redirect('pagina_gerador')

            caminho_video_input = video_base.arquivo_video.path
            caminho_musica_input = musica_base.arquivo_musica.path
            nome_arquivo_saida = f"video_{request.user.id}_{random.randint(1000, 9999)}.mp4"
            caminho_video_output = os.path.join(settings.MEDIA_ROOT, 'videos_gerados', nome_arquivo_saida)
            os.makedirs(os.path.dirname(caminho_video_output), exist_ok=True)

            cmd = ['ffmpeg', '-y']
            if data['loop_video']: cmd.extend(['-stream_loop', '-1', '-i', caminho_video_input])
            else: cmd.extend(['-i', caminho_video_input])
            
            cor_da_fonte = 'white'
            if data['plano_de_fundo'] == 'claro': cor_da_fonte = 'black'

            texto_para_mostrar = None
            if data.get('acompanhar_texto') and data['narrador_texto']:
                texto_para_mostrar = data['narrador_texto']
            elif data['texto_overlay']:
                texto_para_mostrar = data['texto_overlay']

            filtros_video = ""
            map_video = "0:v"

            if data.get('acompanhar_texto') and timepoints:
                caminho_legenda_ass = gerar_ficheiro_legenda_ass(timepoints, data, cor_da_fonte)
                cmd.extend(['-i', caminho_musica_input])
                if caminho_narrador_input: cmd.extend(['-i', caminho_narrador_input])
                
                caminho_legenda_ffmpeg = caminho_legenda_ass.replace('\\', '/').replace(':', '\\:')
                filtros_video = f"[0:v]scale=1080:1920:force_original_aspect_ratio=decrease,pad=1080:1920:(ow-iw)/2:(oh-ih)/2,setsar=1,ass='{caminho_legenda_ffmpeg}'[v]"
                map_video = "[v]"
            elif texto_para_mostrar:
                caminho_imagem_texto = create_text_image(texto_para_mostrar, cor_da_fonte, data)
                cmd.extend(['-i', caminho_imagem_texto])
                cmd.extend(['-i', caminho_musica_input])
                if caminho_narrador_input: cmd.extend(['-i', caminho_narrador_input])
                
                filtros_video = "[0:v]scale=1080:1920:force_original_aspect_ratio=decrease,pad=1080:1920:(ow-iw)/2:(oh-ih)/2,setsar=1[base];[base][1:v]overlay=(W-w)/2:(H-h)/2[v]"
                map_video = "[v]"
            
            volume_musica_decimal = data['volume_musica'] / 100.0
            filtro_audio = ""
            if caminho_narrador_input:
                idx_musica = cmd.count('-i') - (1 if texto_para_mostrar and not timepoints else 0) - 1
                idx_narrador = cmd.count('-i') - 1
                filtro_audio = f"[{idx_musica}:a]volume={volume_musica_decimal}[a1]; [a1][{idx_narrador}:a]amix=inputs=2:duration=longest[aout]"
                map_audio = "-map [aout]"
            else:
                idx_musica = cmd.count('-i') - (1 if texto_para_mostrar and not timepoints else 0) -1
                filtro_audio = f"[{idx_musica}:a]volume={volume_musica_decimal}[aout]"
                map_audio = "-map [aout]"

            cmd.extend(['-filter_complex', f"{filtros_video}{';' if filtro_audio and filtros_video else ''}{filtro_audio}"])
            cmd.extend(['-map', map_video])
            if 'map_audio' in locals(): cmd.extend(map_audio.split(' '))
            
            cmd.extend(['-t', str(data['duracao_segundos']), '-c:v', 'libx264', '-pix_fmt', 'yuv420p', '-c:a', 'aac', '-b:a', '192k', '-shortest'])
            cmd.append(caminho_video_output)
            
            try:
                print("--- A executar o comando FFmpeg ---"); print(' '.join(cmd))
                resultado = subprocess.run(cmd, check=True, text=True, capture_output=True, encoding='utf-8')
                
                VideoGerado.objects.create(
                    usuario=request.user, texto_overlay=data['texto_overlay'],
                    duracao_minutos=data['duracao_segundos'] / 60, loop=data['loop_video'],
                    status='CONCLUIDO', arquivo_final=os.path.join('videos_gerados', nome_arquivo_saida),
                    narrador_texto=data['narrador_texto'], volume_musica=data['volume_musica'],
                    narrador_voz=data['narrador_voz'], narrador_velocidade=data['narrador_velocidade'],
                    narrador_tom=data['narrador_tom'], plano_de_fundo=data['plano_de_fundo'],
                    texto_fonte=data['texto_fonte'], texto_tamanho=data['texto_tamanho'],
                    texto_negrito=data['texto_negrito'], texto_sublinhado=data['texto_sublinhado'],
                    legenda_sincronizada=data.get('acompanhar_texto', False)
                )
            except subprocess.CalledProcessError as e:
                print(f"--- ERRO NO FFMPEG ---"); print(f"Comando que falhou: {' '.join(e.cmd)}"); print(f"Saída de Erro (stderr):\n{e.stderr}")
                VideoGerado.objects.create(usuario=request.user, status='ERRO', texto_overlay=data['texto_overlay'])
            finally:
                if caminho_narrador_input and os.path.exists(caminho_narrador_input): os.remove(caminho_narrador_input)
                if caminho_legenda_ass and os.path.exists(caminho_legenda_ass): os.remove(caminho_legenda_ass)
                if caminho_imagem_texto and os.path.exists(caminho_imagem_texto): os.remove(caminho_imagem_texto)

            return redirect('meus_videos')
    else:
        form = GeradorForm()

    return render(request, 'core/gerador.html', {'form': form})

@login_required
def meus_videos(request):
    videos = VideoGerado.objects.filter(usuario=request.user).order_by('-criado_em')
    return render(request, 'core/meus_videos.html', {'videos': videos})
