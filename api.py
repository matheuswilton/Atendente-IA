import os
import time
import secrets
from fastapi import FastAPI, Header, HTTPException, Request
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field
import banco
import analise

app = FastAPI(title="Agente de Atendimento com IA", description="API REST de atendimento ao cliente com IA, historico e relatorio")
pasta_do_projeto = os.path.dirname(os.path.abspath(__file__))
registro_de_acessos = {}

class MensagemEntrada(BaseModel):
    conversa_id: str = Field(min_length=1, max_length=100, description="identifica a conversa (ex: numero do WhatsApp)")
    mensagem: str = Field(min_length=1, max_length=1000)

def conferir_chave(chave_enviada):
    # se CHAVE_DO_SERVICO estiver definida, as rotas com dados dos clientes exigem a chave no cabecalho x-chave
    chave_correta = os.environ.get("CHAVE_DO_SERVICO")
    if chave_correta:
        if not chave_enviada or not secrets.compare_digest(chave_enviada, chave_correta):
            raise HTTPException(status_code=401, detail="chave invalida ou ausente")

def limitar_acessos(requisicao):
    # limite simples por IP para ninguem gastar a chave da IA com spam
    limite_por_minuto = int(os.environ.get("LIMITE_POR_MINUTO", "10"))
    ip_do_cliente = requisicao.client.host if requisicao.client else "desconhecido"
    agora = time.time()
    acessos_recentes = [momento for momento in registro_de_acessos.get(ip_do_cliente, []) if agora - momento < 60]
    if len(acessos_recentes) >= limite_por_minuto:
        raise HTTPException(status_code=429, detail="muitas mensagens, espere um minuto")
    acessos_recentes.append(agora)
    registro_de_acessos[ip_do_cliente] = acessos_recentes

@app.get("/", include_in_schema=False)
def pagina_inicial():
    return FileResponse(os.path.join(pasta_do_projeto, "static", "index.html"))

@app.get("/saude")
def verificar_saude():
    return {"status": "ok"}

@app.post("/atendimentos")
def criar_atendimento(entrada: MensagemEntrada, requisicao: Request):
    limitar_acessos(requisicao)
    historico = banco.buscar_historico(entrada.conversa_id)
    resultado = analise.analisar(entrada.mensagem, historico)
    novo_id = banco.salvar_atendimento(entrada.conversa_id, entrada.mensagem, resultado)
    resultado["id"] = novo_id
    resultado["conversa_id"] = entrada.conversa_id
    return resultado

@app.get("/atendimentos")
def listar(limite: int = 20, somente_humano: bool = False, x_chave: str = Header(default=None)):
    conferir_chave(x_chave)
    limite = max(1, min(limite, 100))
    return banco.listar_atendimentos(limite, somente_humano)

@app.get("/relatorio")
def relatorio(x_chave: str = Header(default=None)):
    conferir_chave(x_chave)
    return banco.gerar_relatorio()
