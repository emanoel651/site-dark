from django.contrib import admin
from .models import CategoriaVideo, CategoriaMusica, VideoBase, MusicaBase, VideoGerado

admin.site.register(CategoriaVideo)
admin.site.register(CategoriaMusica)
admin.site.register(VideoBase)
admin.site.register(MusicaBase)
admin.site.register(VideoGerado)