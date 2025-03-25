import time
from src.coletor import coletar_resultados
from src.analisador import analisar_padroes
from src.telegram_bot import enviar_sinal, registrar_resultado, obter_saldo_do_dia

def main():
    print("🚀 Iniciando o Bot Blaze Double...")
    
    saldo = obter_saldo_do_dia()  # Pega o saldo atual

    while True:
        resultados = coletar_resultados()

        if not resultados:
            print("⚠️ Erro ao coletar resultados, tentando novamente...")
            time.sleep(10)  # Espera antes de tentar novamente
            continue

        aposta, cor = analisar_padroes(resultados)

        if aposta:
            enviar_sinal(cor, aposta)
            time.sleep(10)  # Aguarda o tempo para aposta ser feita

            # Aqui poderíamos validar o resultado no banco
            # Exemplo: Se a aposta foi feita, registrar o resultado
            resultado = 2 if cor == "red" else -2  # Simulação, precisa pegar da API
            registrar_resultado(resultado)

        time.sleep(30)  # Aguarda um pouco antes de verificar de novo

if __name__ == "__main__":
    main()
