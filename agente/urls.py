from django.urls import path
from .views import analisar_conteudo

urlpatterns = [
    path('analisar/', analisar_conteudo, name='analisar_conteudo'),
]