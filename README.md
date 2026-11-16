# Agente de Atendimento com IA

![testes](https://github.com/matheuswilton/Atendente-IA/actions/workflows/testes.yml/badge.svg)

API REST em Python que simula um agente de atendimento ao cliente, como os chatbots que a Blip constrói: entende a mensagem com IA, responde, lembra da conversa, passa para um humano quando precisa e gera relatórios com SQL. Tem uma página de chat para testar no navegador.

**Demo no ar:** _(coloque aqui o link depois do deploy)_

## O que ele faz
1. **Entende a mensagem** com IA (API da Anthropic): intenção (rastreio, troca, pagamento, suporte, elogio, outro) e urgência (baixa, média, alta).
2. **Responde o cliente** seguindo as regras da loja.
3. **Lembra da conversa**: as últimas mensagens de cada `conversa_id` vão junto para a IA.
4. **Transfere para humano** quando a urgência é alta ou a intenção não é reconhecida.
5. **Guarda tudo no SQLite** e gera relatório com consultas SQL.
6. **Não fica fora do ar**: se não houver chave, ou a IA falhar ou devolver algo inválido, um plano B por regras responde no lugar (e o motivo da falha vai para o log).
7. **Protege os dados**: as rotas que mostram atendimentos exigem uma chave, e o envio de mensagens tem limite por minuto por IP.

## Tecnologias
Python 3 · FastAPI · SQLite/SQL · API REST (`requests`) · pytest · GitHub Actions · Docker

## Como rodar
```bash
git clone https://github.com/matheuswilton/Atendente-IA
cd Atendente-IA
pip install -r requirements.txt
python atendente.py demo          # demonstração no terminal
uvicorn api:app --reload          # sobe a API e a página de chat em http://localhost:8000
```
Documentação interativa da API: `http://localhost:8000/docs`

### Variáveis de ambiente
| Variável | Para quê | Obrigatória |
|---|---|---|
| `ANTHROPIC_API_KEY` | liga a IA (sem ela usa o plano B por regras) | não |
| `CHAVE_DO_SERVICO` | protege `/atendimentos` (GET) e `/relatorio` com o cabeçalho `x-chave` | recomendada em produção |
| `LIMITE_POR_MINUTO` | mensagens por minuto por IP (padrão 10) | não |
| `BANCO_ATENDIMENTOS` | caminho do arquivo SQLite (padrão `atendimentos.db`) | não |

```bash
# Windows (PowerShell)
$env:ANTHROPIC_API_KEY="sua-chave"
# Linux/Mac
export ANTHROPIC_API_KEY="sua-chave"
```

## Endpoints
| Método | Rota | O que faz | Exige chave |
|---|---|---|---|
| GET | `/` | página de chat de demonstração | não |
| POST | `/atendimentos` | recebe `{"conversa_id", "mensagem"}` e devolve a análise e a resposta | não (tem limite por minuto) |
| GET | `/atendimentos` | lista atendimentos (`?limite=20&somente_humano=true`) | sim |
| GET | `/relatorio` | total, % para humano, contagem por intenção e urgência | sim |
| GET | `/saude` | verifica se a API está no ar | não |

```bash
curl -X POST localhost:8000/atendimentos -H "content-type: application/json" \
  -d '{"conversa_id": "5562999990000", "mensagem": "meu pedido nao chegou"}'
curl localhost:8000/relatorio -H "x-chave: SUA_CHAVE_DO_SERVICO"
```

## Estrutura
```
api.py          rotas FastAPI, validação, chave de acesso e limite por minuto
analise.py      IA (API REST), plano B por regras e regra de transferência
banco.py        SQLite: salvar, histórico, listagem e relatório SQL
atendente.py    versão de terminal (demo e conversa)
static/         página de chat
testes/         20 testes automáticos (rodam no GitHub Actions a cada push)
Dockerfile      empacota o projeto para rodar em qualquer servidor
render.yaml     configuração para publicar no Render
```

## Testes
```bash
pip install -r requirements-dev.txt
python -m pytest -v
```
Os testes cobrem as regras, o banco, a API (entradas inválidas, chave, limite por minuto) e a IA com respostas simuladas, inclusive quando ela devolve texto quebrado ou uma intenção inventada.

## Publicar no ar (Render)
1. Suba o projeto para o GitHub.
2. No Render: **New > Blueprint**, escolha este repositório (ele lê o `render.yaml`).
3. Preencha `ANTHROPIC_API_KEY`. A `CHAVE_DO_SERVICO` é gerada automaticamente.
4. Depois do deploy, abra a URL do serviço.

## Decisões de projeto
- **IA responde em JSON** e o código valida os valores antes de usar. Nunca confio cegamente na saída do modelo.
- **Plano B** garante que o cliente sempre recebe resposta.
- **Texto do cliente tratado como dado** no prompt, para reduzir o risco de alguém dar ordens para a IA.
- **Limite de 1000 caracteres**, limite por minuto e chave nas rotas com dados de clientes.

## Limitações e próximos passos
- O plano B por palavras-chave é simples.
- Só as últimas 6 mensagens entram como contexto.
- No plano gratuito de hospedagem o banco SQLite é apagado quando o serviço reinicia. Próximo passo: PostgreSQL.
- Próximos passos: integração real com WhatsApp, base de perguntas frequentes e painel de relatório.

## Autor
Matheus Wilton, estudante de Gestão da TI.
