import pytest
from fastapi.testclient import TestClient
import api

@pytest.fixture
def cliente(tmp_path, monkeypatch):
    # cada teste usa um banco novo e sem chave de IA
    monkeypatch.setenv("BANCO_ATENDIMENTOS", str(tmp_path / "teste.db"))
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.delenv("CHAVE_DO_SERVICO", raising=False)
    monkeypatch.delenv("DATABASE_URL", raising=False)
    api.registro_de_acessos.clear()
    return TestClient(api.app)

def test_saude(cliente):
    assert cliente.get("/saude").json() == {"status": "ok"}

def test_criar_atendimento(cliente):
    resposta = cliente.post("/atendimentos", json={"conversa_id": "5562999990000", "mensagem": "meu pedido nao chegou"})
    assert resposta.status_code == 200
    dados = resposta.json()
    assert dados["intencao"] == "rastreio_pedido"
    assert dados["id"] == 1

def test_mensagem_vazia_e_recusada(cliente):
    resposta = cliente.post("/atendimentos", json={"conversa_id": "abc", "mensagem": ""})
    assert resposta.status_code == 422

def test_mensagem_grande_demais_e_recusada(cliente):
    resposta = cliente.post("/atendimentos", json={"conversa_id": "abc", "mensagem": "a" * 1001})
    assert resposta.status_code == 422

def test_listar_e_filtrar_humano(cliente):
    cliente.post("/atendimentos", json={"conversa_id": "a", "mensagem": "meu pedido nao chegou"})
    cliente.post("/atendimentos", json={"conversa_id": "b", "mensagem": "isso e um absurdo"})
    assert len(cliente.get("/atendimentos").json()) == 2
    somente_humano = cliente.get("/atendimentos?somente_humano=true").json()
    assert len(somente_humano) == 1
    assert somente_humano[0]["conversa_id"] == "b"

def test_relatorio(cliente):
    cliente.post("/atendimentos", json={"conversa_id": "a", "mensagem": "meu pedido nao chegou"})
    cliente.post("/atendimentos", json={"conversa_id": "b", "mensagem": "parabens, adorei"})
    relatorio = cliente.get("/relatorio").json()
    assert relatorio["total"] == 2
    assert relatorio["por_intencao"]["elogio"] == 1

def test_historico_fica_separado_por_conversa(cliente):
    import banco
    cliente.post("/atendimentos", json={"conversa_id": "a", "mensagem": "meu pedido nao chegou"})
    cliente.post("/atendimentos", json={"conversa_id": "b", "mensagem": "parabens, adorei"})
    cliente.post("/atendimentos", json={"conversa_id": "a", "mensagem": "ainda nada"})
    assert len(banco.buscar_historico("a")) == 2
    assert len(banco.buscar_historico("b")) == 1

def test_pagina_inicial_abre(cliente):
    resposta = cliente.get("/")
    assert resposta.status_code == 200
    assert "Atendente IA" in resposta.text

def test_rotas_com_dados_exigem_chave(cliente, monkeypatch):
    monkeypatch.setenv("CHAVE_DO_SERVICO", "segredo123")
    assert cliente.get("/relatorio").status_code == 401
    assert cliente.get("/atendimentos").status_code == 401
    assert cliente.get("/relatorio", headers={"x-chave": "errada"}).status_code == 401
    assert cliente.get("/relatorio", headers={"x-chave": "segredo123"}).status_code == 200

def test_enviar_mensagem_nao_exige_chave(cliente, monkeypatch):
    monkeypatch.setenv("CHAVE_DO_SERVICO", "segredo123")
    resposta = cliente.post("/atendimentos", json={"conversa_id": "a", "mensagem": "oi"})
    assert resposta.status_code == 200

def test_limite_por_minuto(cliente, monkeypatch):
    monkeypatch.setenv("LIMITE_POR_MINUTO", "3")
    for numero in range(3):
        assert cliente.post("/atendimentos", json={"conversa_id": "a", "mensagem": "oi"}).status_code == 200
    assert cliente.post("/atendimentos", json={"conversa_id": "a", "mensagem": "oi"}).status_code == 429

def test_pagina_do_painel_abre(cliente):
    resposta = cliente.get("/painel")
    assert resposta.status_code == 200
    assert "Painel de Atendimentos" in resposta.text

def test_painel_nao_mostra_dados_sem_chave(cliente, monkeypatch):
    monkeypatch.setenv("CHAVE_DO_SERVICO", "segredo123")
    cliente.post("/atendimentos", json={"conversa_id": "a", "mensagem": "isso e um absurdo"})
    assert "isso e um absurdo" not in cliente.get("/painel").text
    assert cliente.get("/atendimentos?somente_humano=true", headers={"x-chave": "errada"}).status_code == 401
    lista = cliente.get("/atendimentos?somente_humano=true", headers={"x-chave": "segredo123"}).json()
    assert lista[0]["mensagem_cliente"] == "isso e um absurdo"

def test_dados_invalidos_explicam_o_campo(cliente):
    resposta = cliente.post("/atendimentos", json={"conversa_id": "a"})
    assert resposta.status_code == 422
    assert resposta.json()["detail"] == "dados invalidos"
    assert resposta.json()["problemas"][0].startswith("mensagem:")

def test_banco_fora_do_ar_responde_503(cliente, monkeypatch):
    import sqlite3
    import banco
    def banco_quebrado(*args, **kwargs):
        raise sqlite3.OperationalError("disco cheio")
    monkeypatch.setattr(banco, "buscar_historico", banco_quebrado)
    resposta = cliente.post("/atendimentos", json={"conversa_id": "a", "mensagem": "oi"})
    assert resposta.status_code == 503
    assert "banco de dados indisponivel" in resposta.json()["detail"]

def test_erro_inesperado_responde_500_sem_detalhe_tecnico(monkeypatch, tmp_path):
    monkeypatch.setenv("BANCO_ATENDIMENTOS", str(tmp_path / "teste.db"))
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    api.registro_de_acessos.clear()
    def analise_quebrada(*args, **kwargs):
        raise RuntimeError("detalhe interno secreto")
    monkeypatch.setattr(api.analise, "analisar", analise_quebrada)
    cliente_sem_excecao = TestClient(api.app, raise_server_exceptions=False)
    resposta = cliente_sem_excecao.post("/atendimentos", json={"conversa_id": "a", "mensagem": "oi"})
    assert resposta.status_code == 500
    assert "secreto" not in resposta.text

def test_log_do_atendimento_nao_mostra_o_texto_do_cliente(cliente, caplog):
    import logging
    caplog.set_level(logging.INFO)
    cliente.post("/atendimentos", json={"conversa_id": "a", "mensagem": "meu cpf e 123.456.789-00"})
    assert "intencao=" in caplog.text
    assert "123.456.789-00" not in caplog.text
