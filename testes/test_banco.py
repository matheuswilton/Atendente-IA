import os
import pytest
import banco
# os mesmos testes rodam no SQLite e no PostgreSQL
# o PostgreSQL so e testado quando TESTE_POSTGRES_URL existe (no GitHub Actions ele existe)
url_postgres_de_teste = os.environ.get("TESTE_POSTGRES_URL")

@pytest.fixture(params=["sqlite", "postgres"])
def banco_vazio(request, tmp_path, monkeypatch):
    if request.param == "sqlite":
        monkeypatch.delenv("DATABASE_URL", raising=False)
        monkeypatch.setenv("BANCO_ATENDIMENTOS", str(tmp_path / "teste.db"))
    else:
        if not url_postgres_de_teste:
            pytest.skip("TESTE_POSTGRES_URL nao definida")
        monkeypatch.setenv("DATABASE_URL", url_postgres_de_teste)
        conexao = banco.conectar()
        conexao.execute("DROP TABLE atendimentos")
        conexao.commit()
        conexao.close()
    return request.param

def resultado_de_exemplo(intencao, urgencia, transferir):
    return {"intencao": intencao, "urgencia": urgencia, "resposta": "ok", "transferir_humano": transferir, "origem": "regras"}

def test_usa_postgres_so_com_database_url(monkeypatch):
    monkeypatch.delenv("DATABASE_URL", raising=False)
    assert banco.usando_postgres() is False
    monkeypatch.setenv("DATABASE_URL", "postgresql://usuario@servidor/banco")
    assert banco.usando_postgres() is True

def test_salvar_devolve_ids_em_sequencia(banco_vazio):
    assert banco.salvar_atendimento("a", "oi", resultado_de_exemplo("outro", "baixa", 1)) == 1
    assert banco.salvar_atendimento("a", "tchau", resultado_de_exemplo("elogio", "baixa", 0)) == 2

def test_historico_vem_do_mais_antigo_para_o_mais_novo(banco_vazio):
    for numero in range(8):
        banco.salvar_atendimento("a", "mensagem " + str(numero), resultado_de_exemplo("outro", "baixa", 0))
    historico = banco.buscar_historico("a")
    assert len(historico) == 6
    assert historico[0]["mensagem_cliente"] == "mensagem 2"
    assert historico[-1]["mensagem_cliente"] == "mensagem 7"

def test_listar_somente_humano(banco_vazio):
    banco.salvar_atendimento("a", "oi", resultado_de_exemplo("outro", "baixa", 1))
    banco.salvar_atendimento("b", "adorei", resultado_de_exemplo("elogio", "baixa", 0))
    assert len(banco.listar_atendimentos()) == 2
    somente_humano = banco.listar_atendimentos(somente_humano=True)
    assert [item["conversa_id"] for item in somente_humano] == ["a"]

def test_relatorio_conta_por_intencao_e_urgencia(banco_vazio):
    banco.salvar_atendimento("a", "1", resultado_de_exemplo("pagamento", "alta", 1))
    banco.salvar_atendimento("b", "2", resultado_de_exemplo("pagamento", "media", 0))
    banco.salvar_atendimento("c", "3", resultado_de_exemplo("elogio", "baixa", 0))
    banco.salvar_atendimento("d", "4", resultado_de_exemplo("outro", "baixa", 1))
    relatorio = banco.gerar_relatorio()
    assert relatorio["total"] == 4
    assert relatorio["para_humano"] == 2
    assert relatorio["percentual_humano"] == 50.0
    assert relatorio["por_intencao"] == {"pagamento": 2, "elogio": 1, "outro": 1}
    assert relatorio["por_urgencia"]["baixa"] == 2

def test_relatorio_vazio(banco_vazio):
    relatorio = banco.gerar_relatorio()
    assert relatorio["total"] == 0
    assert relatorio["percentual_humano"] == 0
