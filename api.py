import os
import time
import logging
import secrets
from fastapi import FastAPI, Header, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel, Field
import banco
import analise

# logs com data, nivel e de onde veio; o nivel pode ser trocado pela variavel NIVEL_DO_LOG (ex: DEBUG)
logging.basicConfig(level=os.environ.get("NIVEL_DO_LOG", "INFO").upper(), format="%(asctime)s %(levelname)s %(name)s: %(message)s")
registro = logging.getLogger("atendente.api")
app = FastAPI(title="Agente de Atendimento com IA", description="API REST de atendimento ao cliente com IA, historico e relatorio")
pasta_do_projeto = os.path.dirname(os.path.abspath(__file__))
registro_de_acessos = {}

@app.exception_handler(RequestValidationError)
def tratar_dados_invalidos(requisicao, erro):
    # explica em portugues qual campo esta errado
    problemas = []
    for item in erro.errors():
        campo = str(item["loc"][-1]) if item.get("loc") else "corpo"
        problemas.append(campo + ": " + item["msg"])
    return JSONResponse(status_code=422, content={"detail": "dados invalidos", "problemas": problemas})

def tratar_erro_do_banco(requisicao, erro):
    registro.error("Falha no banco de dados em %s: %s", requisicao.url.path, type(erro).__name__)
    return JSONResponse(status_code=503, content={"detail": "banco de dados indisponivel, tente de novo em instantes"})

for tipo_de_erro in banco.erros_de_banco:
    app.add_exception_handler(tipo_de_erro, tratar_erro_do_banco)

@app.exception_handler(Exception)
def tratar_erro_inesperado(requisicao, erro):
    # o detalhe tecnico fica so no log; o cliente recebe uma mensagem simples
    registro.exception("Erro inesperado em %s", requisicao.url.path)
    return JSONResponse(status_code=500, content={"detail": "erro interno, tente de novo"})

class MensagemEntrada(BaseModel):
    conversa_id: str = Field(min_length=1, max_length=100, description="identifica a conversa (ex: numero do WhatsApp)")
    mensagem: str = Field(min_length=1, max_length=1000)

def conferir_chave(chave_enviada):
    # se CHAVE_DO_SERVICO estiver definida, as rotas com dados dos clientes exigem a chave no cabecalho x-chave
    chave_correta = os.environ.get("CHAVE_DO_SERVICO")
    if chave_correta:
        if not chave_enviada or not secrets.compare_digest(chave_enviada, chave_correta):
            registro.warning("Acesso negado a rota protegida (chave invalida ou ausente)")
            raise HTTPException(status_code=401, detail="chave invalida ou ausente")

def limitar_acessos(requisicao):
    # limite simples por IP para ninguem gastar a chave da IA com spam
    limite_por_minuto = int(os.environ.get("LIMITE_POR_MINUTO", "10"))
    ip_do_cliente = requisicao.client.host if requisicao.client else "desconhecido"
    agora = time.time()
    acessos_recentes = [momento for momento in registro_de_acessos.get(ip_do_cliente, []) if agora - momento < 60]
    if len(acessos_recentes) >= limite_por_minuto:
        registro.warning("Limite por minuto atingido para um IP (%s mensagens)", limite_por_minuto)
        raise HTTPException(status_code=429, detail="muitas mensagens, espere um minuto")
    acessos_recentes.append(agora)
    registro_de_acessos[ip_do_cliente] = acessos_recentes

@app.get("/", include_in_schema=False)
def pagina_inicial():
    return FileResponse(os.path.join(pasta_do_projeto, "static", "index.html"))

@app.get("/painel", include_in_schema=False)
def pagina_do_painel():
    # a pagina em si e publica, mas os dados que ela mostra so chegam com a chave certa
    return FileResponse(os.path.join(pasta_do_projeto, "static", "painel.html"))

@app.get("/saude")
def verificar_saude():
    return {"status": "ok"}

@app.post("/atendimentos")
def criar_atendimento(entrada: MensagemEntrada, requisicao: Request):
    limitar_acessos(requisicao)
    inicio = time.time()
    historico = banco.buscar_historico(entrada.conversa_id)
    resultado = analise.analisar(entrada.mensagem, historico)
    novo_id = banco.salvar_atendimento(entrada.conversa_id, entrada.mensagem, resultado)
    milissegundos = round((time.time() - inicio) * 1000)
    # o texto do cliente nao vai para o log (protecao de dados), so o tamanho
    registro.info("Atendimento %s: intencao=%s urgencia=%s humano=%s origem=%s tamanho=%s tempo=%sms", novo_id, resultado["intencao"], resultado["urgencia"], resultado["transferir_humano"], resultado["origem"], len(entrada.mensagem), milissegundos)
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
