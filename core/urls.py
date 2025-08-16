from django.urls import path
from . import views

urlpatterns = [
    path('', views.pagina_gerador, name='pagina_gerador'),
    path('meus-videos/', views.meus_videos, name='meus_videos'),
    
    # --- NOVA URL PARA O PREVIEW DA VOZ ---
    # Esta rota irá receber o nome da voz e chamar a função 'preview_voz'.
    path('preview-voz/<str:nome_da_voz>/', views.preview_voz, name='preview_voz'),
    # --- FIM DA NOVA URL ---
]
