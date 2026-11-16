import os
import re
import json
import unicodedata
pasta_do_projeto = os.path.dirname(os.path.abspath(__file__))
arquivo_de_perguntas = os.path.join(pasta_do_projeto, "perguntas_frequentes.json")

def normalizar(texto):
    # deixa tudo minusculo e sem acento, para "Cartão" e "cartao" serem a mesma palavra
    sem_acento = unicodedata.normalize("NFKD", texto).encode("ascii", "ignore").decode("ascii")
    return sem_acento.lower()

def carregar_perguntas():
    with open(arquivo_de_perguntas, encoding="utf-8") as arquivo:
        return json.load(arquivo)

def contar_palavras_encontradas(texto_normalizado, palavras_chave):
    # a palavra-chave precisa comecar no inicio de uma palavra ("nf" nao conta dentro de "informar")
    quantidade = 0
    for palavra in palavras_chave:
        if re.search(r"\b" + re.escape(normalizar(palavra)), texto_normalizado):
            quantidade = quantidade + 1
    return quantidade

def buscar_perguntas_parecidas(mensagem, quantidade_maxima=3):
    # devolve as perguntas frequentes que mais combinam com a mensagem, da melhor para a pior
    texto = normalizar(mensagem)
    encontradas = []
    for item in carregar_perguntas():
        pontos = contar_palavras_encontradas(texto, item["palavras_chave"])
        if pontos > 0:
            encontradas.append({"pergunta": item["pergunta"], "resposta": item["resposta"], "pontos": pontos})
    encontradas.sort(key=lambda item: item["pontos"], reverse=True)
    return encontradas[:quantidade_maxima]
