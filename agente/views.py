import json
import os
import time
import traceback
import requests
from bs4 import BeautifulSoup
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from google import genai
from dotenv import load_dotenv

load_dotenv()

def extrair_conteudo_url(url):
    """Descarrega o HTML da URL e extrai o título e o texto dos parágrafos."""
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        }
        response = requests.get(url, headers=headers, timeout=6)
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Remove elementos indesejados (scripts, estilos, menus)
            for element in soup(["script", "style", "nav", "footer", "header"]):
                element.decompose()
                
            # Extrai o título da página
            titulo = soup.find('h1')
            titulo_texto = titulo.get_text().strip() if titulo else ""
            
            # Extrai os parágrafos do corpo da notícia
            paragrafos = soup.find_all('p')
            texto_pagina = " ".join([p.get_text().strip() for p in paragrafos])
            
            if len(texto_pagina) > 50:
                return f"Título da Página: {titulo_texto}\n\nConteúdo da Notícia:\n{texto_pagina}"
    except Exception as e:
        print(f"Erro ao raspar URL: {e}")
    
    return None

@csrf_exempt
def analisar_conteudo(request):
    if request.method != 'POST':
        return JsonResponse({'error': 'Método não permitido'}, status=405)

    try:
        data = json.loads(request.body)
        entrada = data.get('conteudo', '').strip()

        if not entrada:
            return JsonResponse({'error': 'O conteúdo fornecido está vazio.'}, status=400)

        conteudo_para_analise = entrada

        # Se o utilizador enviou um link, fazemos o scraping do conteúdo real
        if entrada.startswith("http://") or entrada.startswith("https://"):
            conteudo_extraido = extrair_conteudo_url(entrada)
            if conteudo_extraido:
                conteudo_para_analise = f"Link analisado: {entrada}\n\n{conteudo_extraido}"
            else:
                conteudo_para_analise = f"Link analisado: {entrada} (A página bloqueou a leitura automática ou é inacessível, analise com cautela)."

        api_key = os.environ.get("GEMINI_API_KEY")
        if not api_key:
            return JsonResponse({'error': 'Chave GEMINI_API_KEY não encontrada no .env ou ambiente.'}, status=500)

        client = genai.Client(api_key=api_key)

        prompt = f"""
        Você é um agente especialista em fact-checking e verificação de notícias.
        Contexto temporal atual: Estamos em Outubro de 2026. Notícias com datas recentes de 2026 são atuais e válidas.
        
        Analise o texto/conteúdo fornecido abaixo e determine se é verdadeiro, falso, manipulado ou suspeito.
        Baseie-se estritamente no conteúdo extraído da página. Retorne a resposta de forma clara e detalhada.

        Conteúdo para analisar:
        {conteudo_para_analise}
        """

        # Chamada ao modelo com tentativas automáticas para o erro 503
        max_tentativas = 4
        response = None
        ultimo_erro = None

        for tentativa in range(1, max_tentativas + 1):
            try:
                response = client.models.generate_content(
                    model='gemini-3.8-flash',
                    contents=prompt,
                )
                if response and response.text:
                    break
            except Exception as err:
                ultimo_erro = err
                erro_str = str(err)
                if "503" in erro_str or "UNAVAILABLE" in erro_str:
                    if tentativa < max_tentativas:
                        time.sleep(2 * tentativa)
                        continue
                break

        if not response or not response.text:
            raise ultimo_erro

        analise_texto = response.text

        resposta_estruturada = {
            "veredito": "Análise Concluída",
            "nivel_confianca": "Alta",
            "resumo_analise": analise_texto
        }

        return JsonResponse({"resultado": resposta_estruturada}, status=200)

    except Exception as e:
        traceback.print_exc()
        erro_str = str(e)
        
        if "429" in erro_str or "RESOURCE_EXHAUSTED" in erro_str:
            mensagem = "Limite diário gratuito atingido (20 requisições). Aguarde o reset ou use um novo projeto."
            status_code = 429
        elif "503" in erro_str or "UNAVAILABLE" in erro_str:
            mensagem = "Servidores da Google com alta procura persistente (Erro 503). Tente novamente em instantes."
            status_code = 503
        else:
            mensagem = f"Erro na análise: {erro_str}"
            status_code = 500

        return JsonResponse({'error': mensagem}, status=status_code)