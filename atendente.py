import sys
from datetime import datetime
import banco
import analise

def atender(conversa_id, mensagem):
    historico = banco.buscar_historico(conversa_id)
    resultado = analise.analisar(mensagem, historico)
    banco.salvar_atendimento(conversa_id, mensagem, resultado)
    print("Atendente: " + resultado["resposta"])
    texto_humano = "nao"
    if resultado["transferir_humano"]:
        texto_humano = "SIM"
    print("  [intencao=" + resultado["intencao"] + " | urgencia=" + resultado["urgencia"] + " | humano=" + texto_humano + " | analise=" + resultado["origem"] + "]")

def mostrar_relatorio():
    relatorio = banco.gerar_relatorio()
    print("Total de atendimentos: " + str(relatorio["total"]))
    print("Transferidos para humano: " + str(relatorio["para_humano"]) + " (" + str(relatorio["percentual_humano"]) + "%)")
    print("Por intencao: " + str(relatorio["por_intencao"]))
    print("Por urgencia: " + str(relatorio["por_urgencia"]))

mensagens_de_exemplo = [
    "Oi, meu pedido ainda nao chegou, ja faz 10 dias",
    "Quero trocar o tenis que comprei, ficou grande",
    "Fui cobrado duas vezes no cartao, isso e um absurdo, vou no procon",
    "Nao consigo fazer login no site, aparece erro",
    "Parabens pelo atendimento, adorei a compra!",
    "Voces vendem para outro pais?"]

if len(sys.argv) > 1 and sys.argv[1] == "demo":
    numero = 1
    for mensagem_exemplo in mensagens_de_exemplo:
        print("\nCliente: " + mensagem_exemplo)
        atender("demo-" + str(numero), mensagem_exemplo)
        numero = numero + 1
    print("\n----- RELATORIO -----")
    mostrar_relatorio()
else:
    conversa_atual = "terminal-" + datetime.now().strftime("%Y%m%d%H%M%S")
    print("Agente de atendimento da Loja Aurora. Digite 'relatorio' ou 'sair'.")
    while True:
        mensagem_digitada = input("\nCliente: ").strip()
        if mensagem_digitada == "sair":
            break
        if mensagem_digitada == "relatorio":
            mostrar_relatorio()
        elif mensagem_digitada != "":
            atender(conversa_atual, mensagem_digitada)
