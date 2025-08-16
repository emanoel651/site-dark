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

os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = os.path.join(settings.BASE_DIR, 'gcloud-auth.json')

FONT_PATHS = {
    'Windows': {
        'arial': 'C:/Windows/Fonts/arial.ttf',
        'times': 'C:/Windows/Fonts/times.ttf',
        'courier': 'C:/Windows/Fonts/cour.ttf',
        'impact': 'C:/Windows/Fonts/impact.ttf',
        'verdana': 'C:/Windows/Fonts/verdana.ttf',
        'georgia': 'C:/Windows/Fonts/georgia.ttf',
    },
    'Linux': {
        # ... (caminhos para Linux, se necessário)
    },
    'Darwin': { 
        # ... (caminhos para macOS, se necessário)
    }
}

def quebrar_texto(texto, largura=25):
    linhas = textwrap.wrap(texto, width=largura, replace_whitespace=False)
    return '\n'.join(linhas)

def gerar_audio_narrador(texto, nome_da_voz, velocidade, tom):
    # ... (código da função igual ao anterior)
    print(f"--- A tentar gerar áudio com a voz: {nome_da_voz}, Vel: {velocidade}%, Tom: {tom} ---")
    try:
        client = texttospeech.TextToSpeechClient()
        synthesis_input = texttospeech.SynthesisInput(text=texto)
        voice = texttospeech.VoiceSelectionParams(language_code="pt-BR", name=nome_da_voz)
        audio_config = texttospeech.AudioConfig(
            audio_encoding=texttospeech.AudioEncoding.MP3,
            speaking_rate=velocidade / 100.0,
            pitch=float(tom)
        )
        response = client.synthesize_speech(input=synthesis_input, voice=voice, audio_config=audio_config)
        narrador_temp_dir = os.path.join(settings.MEDIA_ROOT, 'narrador_temp')
        os.makedirs(narrador_temp_dir, exist_ok=True)
        nome_arquivo_narrador = f"narrador_{random.randint(10000, 99999)}.mp3"
        caminho_narrador_input = os.path.join(narrador_temp_dir, nome_arquivo_narrador)
        with open(caminho_narrador_input, "wb") as out:
            out.write(response.audio_content)
        return caminho_narrador_input
    except Exception as e:
        print(f"--- ERRO AO GERAR ÁUDIO DO NARRADOR COM A API DO GOOGLE ---")
        print(e)
        return None

def preview_voz(request, nome_da_voz):
    # ... (código da função igual ao anterior)
    texto_exemplo = "Esta é uma demonstração da minha voz."
    try:
        client = texttospeech.TextToSpeechClient()
        synthesis_input = texttospeech.SynthesisInput(text=texto_exemplo)
        voice = texttospeech.VoiceSelectionParams(language_code="pt-BR", name=nome_da_voz)
        audio_config = texttospeech.AudioConfig(audio_encoding=texttospeech.AudioEncoding.MP3)
        response = client.synthesize_speech(input=synthesis_input, voice=voice, audio_config=audio_config)
        return HttpResponse(response.audio_content, content_type='audio/mpeg')
    except Exception as e:
        print(f"--- ERRO AO GERAR PREVIEW DA VOZ: {nome_da_voz} ---")
        print(e)
        return HttpResponse(status=500)

@login_required
def pagina_gerador(request):
    if request.method == 'POST':
        form = GeradorForm(request.POST)
        if form.is_valid():
            data = form.cleaned_data

            caminho_narrador_input = None
            if data['narrador_texto']:
                caminho_narrador_input = gerar_audio_narrador(
                    data['narrador_texto'], 
                    data['narrador_voz'],
                    data['narrador_velocidade'],
                    data['narrador_tom']
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
            if data['loop_video']:
                cmd.extend(['-stream_loop', '-1', '-i', caminho_video_input])
            else:
                cmd.extend(['-i', caminho_video_input])
            cmd.extend(['-i', caminho_musica_input])

            if caminho_narrador_input:
                cmd.extend(['-i', caminho_narrador_input])

            filter_complex = []
            filtros_video = 'scale=1080:1920:force_original_aspect_ratio=decrease,pad=1080:1920:(ow-iw)/2:(oh-ih)/2,setsar=1'
            if data['texto_overlay']:
                
                cor_da_fonte = 'white'
                if data['plano_de_fundo'] == 'claro':
                    cor_da_fonte = 'black'

                sistema_op = platform.system()
                nome_fonte_selecionada = data['texto_fonte']
                tamanho_fonte_selecionado = data['texto_tamanho']
                
                caminho_da_fonte = FONT_PATHS.get(sistema_op, {}).get(nome_fonte_selecionada, FONT_PATHS['Windows']['arial'])
                
                if not os.path.exists(caminho_da_fonte):
                    print(f"AVISO: Fonte '{caminho_da_fonte}' não encontrada. A usar Arial como padrão.")
                    caminho_da_fonte = FONT_PATHS['Windows']['arial']

                texto_quebrado = quebrar_texto(data['texto_overlay'])
                texto_sanitizado = texto_quebrado.replace("'", "’")
                
                caminho_fonte_ffmpeg = caminho_da_fonte.replace('\\', '/')
                if platform.system() == "Windows":
                    caminho_fonte_ffmpeg = caminho_fonte_ffmpeg.replace(':', '\\:')
                
                # --- LÓGICA DOS ESTILOS DE TEXTO ---
                estilos_texto = f":fontfile='{caminho_fonte_ffmpeg}':fontsize={tamanho_fonte_selecionado}:fontcolor={cor_da_fonte}:x=(w-text_w)/2:y=(h-text_h)/2:box=1:boxcolor=black@0.5:boxborderw=5"
                
                if data['texto_sublinhado']:
                    estilos_texto += ":underline=1"
                
                if data['texto_negrito']:
                    # Simulamos o negrito aumentando a espessura da borda da fonte
                    estilos_texto += ":borderw=8"
                # --- FIM DA LÓGICA ---

                filtros_video += f",drawtext=text='{texto_sanitizado}'{estilos_texto}"
            
            filter_complex.append(f"[0:v]{filtros_video}[v]")
            volume_musica_decimal = data['volume_musica'] / 100.0
            filtro_musica = f"[1:a]volume={volume_musica_decimal}[a1]"
            
            if caminho_narrador_input:
                filter_complex.append(f"{filtro_musica}; [a1][2:a]amix=inputs=2:duration=longest[aout]")
                map_audio = "-map [aout]"
            else:
                filter_complex.append(filtro_musica)
                map_audio = "-map [a1]"

            cmd.extend(['-filter_complex', ";".join(filter_complex)])
            cmd.extend(['-map', '[v]'])
            cmd.extend(map_audio.split(' '))
            cmd.extend(['-t', str(data['duracao_segundos']), '-c:v', 'libx264', '-pix_fmt', 'yuv420p', '-c:a', 'aac', '-b:a', '192k', '-shortest'])
            cmd.append(caminho_video_output)
            
            try:
                print("--- A executar o comando FFmpeg ---")
                print(' '.join(cmd))
                resultado = subprocess.run(cmd, check=True, text=True, capture_output=True, encoding='utf-8')
                
                VideoGerado.objects.create(
                    usuario=request.user,
                    texto_overlay=data['texto_overlay'],
                    duracao_minutos=data['duracao_segundos'] / 60,
                    loop=data['loop_video'],
                    status='CONCLUIDO',
                    arquivo_final=os.path.join('videos_gerados', nome_arquivo_saida),
                    narrador_texto=data['narrador_texto'],
                    volume_musica=data['volume_musica'],
                    narrador_voz=data['narrador_voz'],
                    narrador_velocidade=data['narrador_velocidade'],
                    narrador_tom=data['narrador_tom'],
                    plano_de_fundo=data['plano_de_fundo'],
                    texto_fonte=data['texto_fonte'],
                    texto_tamanho=data['texto_tamanho'],
                    # Salvamos os novos dados de estilo
                    texto_negrito=data['texto_negrito'],
                    texto_sublinhado=data['texto_sublinhado']
                )
            except subprocess.CalledProcessError as e:
                print(f"--- ERRO NO FFMPEG ---")
                print(f"Comando que falhou: {' '.join(e.cmd)}")
                print(f"Saída de Erro (stderr):\n{e.stderr}")
                VideoGerado.objects.create(usuario=request.user, status='ERRO', texto_overlay=data['texto_overlay'])
            finally:
                if caminho_narrador_input and os.path.exists(caminho_narrador_input):
                    os.remove(caminho_narrador_input)

            return redirect('meus_videos')
    else:
        form = GeradorForm()

    return render(request, 'core/gerador.html', {'form': form})


@login_required
def meus_videos(request):
    videos = VideoGerado.objects.filter(usuario=request.user).order_by('-criado_em')
    return render(request, 'core/meus_videos.html', {'videos': videos})
