import os
import sqlite3
from datetime import datetime

def conectar():
    # o nome do banco pode ser trocado por variavel de ambiente (os testes usam isso)
    nome_do_banco = os.environ.get("BANCO_ATENDIMENTOS", "atendimentos.db")
    conexao = sqlite3.connect(nome_do_banco)
    conexao.row_factory = sqlite3.Row
    conexao.execute("""CREATE TABLE IF NOT EXISTS atendimentos (
id INTEGER PRIMARY KEY AUTOINCREMENT,
conversa_id TEXT,
data_hora TEXT,
mensagem_cliente TEXT,
intencao TEXT,
urgencia TEXT,
resposta TEXT,
transferir_humano INTEGER,
origem_analise TEXT)""")
    return conexao

def salvar_atendimento(conversa_id, mensagem, resultado):
    conexao = conectar()
    cursor = conexao.execute("INSERT INTO atendimentos (conversa_id, data_hora, mensagem_cliente, intencao, urgencia, resposta, transferir_humano, origem_analise) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        (conversa_id, datetime.now().strftime("%Y-%m-%d %H:%M:%S"), mensagem, resultado["intencao"], resultado["urgencia"], resultado["resposta"], resultado["transferir_humano"], resultado["origem"]))
    conexao.commit()
    novo_id = cursor.lastrowid
    conexao.close()
    return novo_id

def buscar_historico(conversa_id, limite=6):
    # pega as ultimas mensagens da conversa e devolve da mais antiga para a mais nova
    conexao = conectar()
    linhas = conexao.execute("SELECT mensagem_cliente, resposta FROM atendimentos WHERE conversa_id = ? ORDER BY id DESC LIMIT ?", (conversa_id, limite)).fetchall()
    conexao.close()
    lista = [dict(linha) for linha in linhas]
    lista.reverse()
    return lista

def listar_atendimentos(limite=20, somente_humano=False):
    conexao = conectar()
    if somente_humano:
        linhas = conexao.execute("SELECT * FROM atendimentos WHERE transferir_humano = 1 ORDER BY id DESC LIMIT ?", (limite,)).fetchall()
    else:
        linhas = conexao.execute("SELECT * FROM atendimentos ORDER BY id DESC LIMIT ?", (limite,)).fetchall()
    conexao.close()
    return [dict(linha) for linha in linhas]

def gerar_relatorio():
    conexao = conectar()
    total = conexao.execute("SELECT COUNT(*) FROM atendimentos").fetchone()[0]
    para_humano = conexao.execute("SELECT COUNT(*) FROM atendimentos WHERE transferir_humano = 1").fetchone()[0]
    por_intencao = {}
    for linha in conexao.execute("SELECT intencao, COUNT(*) FROM atendimentos GROUP BY intencao ORDER BY COUNT(*) DESC"):
        por_intencao[linha[0]] = linha[1]
    por_urgencia = {}
    for linha in conexao.execute("SELECT urgencia, COUNT(*) FROM atendimentos GROUP BY urgencia ORDER BY COUNT(*) DESC"):
        por_urgencia[linha[0]] = linha[1]
    conexao.close()
    percentual_humano = 0
    if total > 0:
        percentual_humano = round(para_humano * 100 / total, 1)
    return {"total": total, "para_humano": para_humano, "percentual_humano": percentual_humano, "por_intencao": por_intencao, "por_urgencia": por_urgencia}
