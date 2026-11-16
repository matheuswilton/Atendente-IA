import analise

def test_rastreio_de_pedido():
    resultado = analise.analisar_sem_ia("meu pedido nao chegou")
    assert resultado["intencao"] == "rastreio_pedido"
    assert resultado["urgencia"] == "media"

def test_cliente_irritado_tem_urgencia_alta():
    resultado = analise.analisar_sem_ia("isso e um absurdo, vou no procon")
    assert resultado["urgencia"] == "alta"

def test_elogio_tem_urgencia_baixa():
    resultado = analise.analisar_sem_ia("parabens, adorei")
    assert resultado["intencao"] == "elogio"
    assert resultado["urgencia"] == "baixa"

def test_mensagem_desconhecida_vai_para_humano(monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    resultado = analise.analisar("voces vendem para outro pais?")
    assert resultado["intencao"] == "outro"
    assert resultado["transferir_humano"] == 1

def test_urgencia_alta_vai_para_humano(monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    resultado = analise.analisar("cobranca errada, absurdo")
    assert resultado["transferir_humano"] == 1

def test_historico_entra_no_texto_da_ia():
    historico = [{"mensagem_cliente": "meu pedido atrasou", "resposta": "vou verificar"}]
    texto = analise.montar_texto_para_ia("ainda nada", historico)
    assert "meu pedido atrasou" in texto
    assert "Nova mensagem do cliente: ainda nada" in texto

class RespostaFalsa:
    def __init__(self, texto):
        self.texto = texto
    def raise_for_status(self):
        pass
    def json(self):
        return {"content": [{"type": "text", "text": self.texto}]}

def test_usa_a_ia_quando_ela_responde_certo(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "chave-falsa")
    json_da_ia = '{"intencao": "pagamento", "urgencia": "media", "resposta": "Claro, vou ajudar com o pagamento."}'
    monkeypatch.setattr(analise.requests, "post", lambda *args, **kwargs: RespostaFalsa(json_da_ia))
    resultado = analise.analisar("quero pagar no pix")
    assert resultado["origem"] == "ia"
    assert resultado["intencao"] == "pagamento"

def test_plano_b_quando_ia_devolve_lixo(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "chave-falsa")
    monkeypatch.setattr(analise.requests, "post", lambda *args, **kwargs: RespostaFalsa("isso nao e json"))
    resultado = analise.analisar("meu pedido nao chegou")
    assert resultado["origem"] == "regras_apos_falha_da_ia"
    assert resultado["intencao"] == "rastreio_pedido"

def test_plano_b_quando_ia_inventa_intencao(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "chave-falsa")
    json_ruim = '{"intencao": "inventada", "urgencia": "baixa", "resposta": "oi"}'
    monkeypatch.setattr(analise.requests, "post", lambda *args, **kwargs: RespostaFalsa(json_ruim))
    resultado = analise.analisar("oi")
    assert resultado["origem"] == "regras_apos_falha_da_ia"
