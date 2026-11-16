import os
import sqlite3
from datetime import datetime
tabela_sqlite = """CREATE TABLE IF NOT EXISTS atendimentos (
id INTEGER PRIMARY KEY AUTOINCREMENT,
conversa_id TEXT,
data_hora TEXT,
mensagem_cliente TEXT,
intencao TEXT,
urgencia TEXT,
resposta TEXT,
transferir_humano INTEGER,
origem_analise TEXT)"""
tabela_postgres = """CREATE TABLE IF NOT EXISTS atendimentos (
id SERIAL PRIMARY KEY,
conversa_id TEXT,
data_hora TEXT,
mensagem_cliente TEXT,
intencao TEXT,
urgencia TEXT,
resposta TEXT,
transferir_humano INTEGER,
origem_analise TEXT)"""

def usando_postgres():
    # se DATABASE_URL existir usa PostgreSQL (dados nao somem no deploy), senao usa SQLite
    return bool(os.environ.get("DATABASE_URL"))

def conectar():
    if usando_postgres():
        import psycopg
        from psycopg.rows import dict_row
        conexao = psycopg.connect(os.environ["DATABASE_URL"], row_factory=dict_row)
        conexao.execute(tabela_postgres)
        conexao.commit()
        return conexao
    # o nome do banco pode ser trocado por variavel de ambiente (os testes usam isso)
    nome_do_banco = os.environ.get("BANCO_ATENDIMENTOS", "atendimentos.db")
    conexao = sqlite3.connect(nome_do_banco)
    conexao.row_factory = sqlite3.Row
    conexao.execute(tabela_sqlite)
    return conexao

def executar(conexao, comando_sql, parametros=()):
    # o SQLite usa ? para os parametros e o PostgreSQL usa %s; o resto do SQL e igual
    if usando_postgres():
        comando_sql = comando_sql.replace("?", "%s")
    return conexao.execute(comando_sql, parametros)

def salvar_atendimento(conversa_id, mensagem, resultado):
    conexao = conectar()
    try:
        linha = executar(conexao, "INSERT INTO atendimentos (conversa_id, data_hora, mensagem_cliente, intencao, urgencia, resposta, transferir_humano, origem_analise) VALUES (?, ?, ?, ?, ?, ?, ?, ?) RETURNING id",
            (conversa_id, datetime.now().strftime("%Y-%m-%d %H:%M:%S"), mensagem, resultado["intencao"], resultado["urgencia"], resultado["resposta"], resultado["transferir_humano"], resultado["origem"])).fetchone()
        conexao.commit()
        return linha["id"]
    finally:
        conexao.close()

def buscar_historico(conversa_id, limite=6):
    # pega as ultimas mensagens da conversa e devolve da mais antiga para a mais nova
    conexao = conectar()
    try:
        linhas = executar(conexao, "SELECT mensagem_cliente, resposta FROM atendimentos WHERE conversa_id = ? ORDER BY id DESC LIMIT ?", (conversa_id, limite)).fetchall()
    finally:
        conexao.close()
    lista = [dict(linha) for linha in linhas]
    lista.reverse()
    return lista

def listar_atendimentos(limite=20, somente_humano=False):
    conexao = conectar()
    try:
        if somente_humano:
            linhas = executar(conexao, "SELECT * FROM atendimentos WHERE transferir_humano = 1 ORDER BY id DESC LIMIT ?", (limite,)).fetchall()
        else:
            linhas = executar(conexao, "SELECT * FROM atendimentos ORDER BY id DESC LIMIT ?", (limite,)).fetchall()
    finally:
        conexao.close()
    return [dict(linha) for linha in linhas]

def gerar_relatorio():
    conexao = conectar()
    try:
        total = executar(conexao, "SELECT COUNT(*) AS quantidade FROM atendimentos").fetchone()["quantidade"]
        para_humano = executar(conexao, "SELECT COUNT(*) AS quantidade FROM atendimentos WHERE transferir_humano = 1").fetchone()["quantidade"]
        por_intencao = {}
        for linha in executar(conexao, "SELECT intencao, COUNT(*) AS quantidade FROM atendimentos GROUP BY intencao ORDER BY quantidade DESC").fetchall():
            por_intencao[linha["intencao"]] = linha["quantidade"]
        por_urgencia = {}
        for linha in executar(conexao, "SELECT urgencia, COUNT(*) AS quantidade FROM atendimentos GROUP BY urgencia ORDER BY quantidade DESC").fetchall():
            por_urgencia[linha["urgencia"]] = linha["quantidade"]
    finally:
        conexao.close()
    percentual_humano = 0
    if total > 0:
        percentual_humano = round(para_humano * 100 / total, 1)
    return {"total": total, "para_humano": para_humano, "percentual_humano": percentual_humano, "por_intencao": por_intencao, "por_urgencia": por_urgencia}
