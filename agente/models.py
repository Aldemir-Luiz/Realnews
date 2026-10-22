from django.db import models

class VerificacaoFato(models.Model):
    tipo_conteudo = models.CharField(max_length=50) # Ex: 'texto', 'link', 'pdf'
    conteudo = models.TextField()                   # O texto ou URL analisada
    veredito = models.CharField(max_length=100)     # Ex: 'Verdadeiro', 'Falso', 'Exagerado'
    nivel_confianca = models.CharField(max_length=50) # Ex: 'Alta', 'Média', 'Baixa'
    resumo_analise = models.TextField()             # Justificativa detalhada da IA
    criado_em = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"[{self.veredito}] - {self.criado_em.strftime('%d/%m/%Y %H:%M')}"