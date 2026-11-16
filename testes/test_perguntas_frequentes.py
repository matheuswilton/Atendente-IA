import analise
import perguntas_frequentes

def test_base_tem_perguntas_com_resposta_e_palavras_chave():
    for item in perguntas_frequentes.carregar_perguntas():
        assert item["pergunta"] and item["resposta"] and item["palavras_chave"]

def test_normalizar_tira_acento_e_maiuscula():
    assert perguntas_frequentes.normalizar("Cartão de CRÉDITO") == "cartao de credito"

def test_encontra_pergunta_parecida():
    encontradas = perguntas_frequentes.buscar_perguntas_parecidas("Vocês entregam em Portugal?")
    assert encontradas[0]["pergunta"] == "Voces entregam fora do Brasil?"

def test_palavra_chave_nao_conta_no_meio_de_outra_palavra():
    assert perguntas_frequentes.buscar_perguntas_parecidas("quero informar uma coisa") == []

def test_plano_b_responde_com_a_pergunta_frequente(monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    resultado = analise.analisar("voces vendem para outro pais?")
    assert resultado["intencao"] == "duvida_frequente"
    assert "apenas para enderecos no Brasil" in resultado["resposta"]
    assert resultado["transferir_humano"] == 0
    assert resultado["perguntas_consultadas"] == ["Voces entregam fora do Brasil?"]

def test_perguntas_frequentes_vao_para_a_ia(monkeypatch):
    perguntas = perguntas_frequentes.buscar_perguntas_parecidas("tem cupom de desconto?")
    texto = analise.montar_texto_para_ia("tem cupom de desconto?", [], perguntas)
    assert "Como uso um cupom de desconto?" in texto
    assert texto.endswith("Nova mensagem do cliente: tem cupom de desconto?")
