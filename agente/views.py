import json
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from google import genai
from google.genai import types
from .models import VerificacaoFato
import os

# Inicializa o cliente do Gemini utilizando a chave do ambiente (.env)
client = genai.Client(api_key=os.environ.get("GEMINI_API_KEY"))

@csrf_exempt
def analisar_conteudo(request):
    if request.method == 'POST':
        try:
            # 1. Recebe os dados enviados pelo front-end do site
            data = json.loads(request.body)
            tipo_conteudo = data.get('tipo_conteudo', 'texto') # 'texto', 'link' ou 'pdf'
            conteudo = data.get('conteudo', '')

            if not conteudo:
                return JsonResponse({'erro': 'O campo de conteúdo não pode estar vazio.'}, status=400)

            # 2. Engenharia de Prompt focada em Fact-Checking
            prompt = f"""
            Você é um assistente especialista em fact-checking, jornalismo investigativo e análise crítica de fake news.
            Analise rigorosamente o seguinte conteúdo fornecido e verifique se há indícios de falsidade, manipulação, exagero ou falta de fontes confiáveis:

            Tipo de Conteúdo: {tipo_conteudo}
            Conteúdo a ser analisado:
            {conteudo}

            Retorne obrigatoriamente um JSON puro (sem markdown extra, apenas o objeto JSON) contendo exatamente estas chaves:
            {{
                "veredito": "Verdadeiro / Falso / Parcialmente Falso / Exagerado / Não Verificável",
                "nivel_confianca": "Alta / Média / Baixa",
                "resumo_analise": "Explicação detalhada e fundamentada do porquê dessa conclusão...",
                "pontos_atencao": ["Ponto crítico ou inconsistência 1", "Ponto crítico ou inconsistência 2"]
            }}
            """

            # 3. Chamada à API do Gemini com fallback automático entre modelos Flash
            resposta_ia = None
            modelos_para_tentar = ['gemini-2.5-flash', 'gemini-2.5-flash-lite']
            
            for modelo in modelos_para_tentar:
                try:
                    response = client.models.generate_content(
                        model=modelo,
                        contents=prompt,
                        config=types.GenerateContentConfig(
                            response_mime_type="application/json",
                            temperature=0.2 # Baixa temperatura para respostas mais objetivas e analíticas
                        )
                    )
                    resposta_ia = response.text
                    break
                except Exception as e:
                    continue

            if not resposta_ia:
                return JsonResponse({'erro': 'Serviço de IA temporariamente indisponível.'}, status=503)

            # 4. Converte a resposta da IA de string para dicionário Python (JSON)
            dados_json = json.loads(resposta_ia)

            # 5. Salva permanentemente no Banco de Dados Relacional
            verificacao = VerificacaoFato.objects.create(
                tipo_conteudo=tipo_conteudo,
                conteudo=conteudo,
                veredito=dados_json.get('veredito', 'Indefinido'),
                nivel_confianca=dados_json.get('nivel_confianca', 'Baixa'),
                resumo_analise=dados_json.get('resumo_analise', '')
            )

            # 6. Retorna o resultado estruturado para o Front-end
            return JsonResponse({
                'sucesso': True,
                'id_analise': verificacao.id,
                'resultado': dados_json
            }, status=200)

        except json.JSONDecodeError:
            return JsonResponse({'erro': 'Formato JSON inválido na requisição.'}, status=400)
        except Exception as e:
            return JsonResponse({'erro': str(e)}, status=500)

    return JsonResponse({'erro': 'Método HTTP não permitido. Utilize POST.'}, status=405)   