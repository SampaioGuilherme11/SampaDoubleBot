import sqlite3
import logging

# Configuração do log
logging.basicConfig(filename="data/logs.txt", level=logging.INFO, format="%(asctime)s - %(message)s")

def obter_ultimos_resultados(limite=100):
    """Obtém os últimos resultados do banco de dados."""
    conn = sqlite3.connect('data/blaze_double.db')
    cursor = conn.cursor()
    cursor.execute(f"SELECT numero, cor FROM resultados ORDER BY created_at DESC LIMIT {limite}")
    dados = cursor.fetchall()
    conn.close()

    if not dados:
        logging.warning("Nenhum resultado encontrado no banco de dados.")
        return []

    return [(res[0], res[1]) for res in dados]  # Retorna lista de tuplas (numero, cor)

def analisar_padroes(limite=100):
    """Analisa a frequência de cada cor e retorna as probabilidades."""
    resultados = obter_ultimos_resultados(limite)

    if not resultados:
        return None, None, None

    total = len(resultados)
    if total == 0:
        return None, None, None

    contagem_cores = {"red": 0, "black": 0, "white": 0}

    for _, cor in resultados:
        contagem_cores[cor] = contagem_cores.get(cor, 0) + 1

    prob_red = contagem_cores["red"] / total
    prob_black = contagem_cores["black"] / total
    prob_white = contagem_cores["white"] / total

    logging.info(f"Probabilidades (Últimos {limite} jogos): Vermelho {prob_red:.2%}, Preto {prob_black:.2%}, Branco {prob_white:.2%}")

    return prob_red, prob_black, prob_white

def calcular_aposta(banca, probabilidade, odds):
    """Usa o Kelly Criterion para determinar o valor da aposta."""
    kelly_fraction = (probabilidade * odds - (1 - probabilidade)) / odds
    valor_aposta = banca * kelly_fraction

    # Nunca apostar mais que 5% da banca por segurança e evitar valores negativos
    return max(1, min(banca * 0.05, max(0, valor_aposta)))

def melhor_aposta(banca, limite=100):
    """Define a melhor aposta com base nas probabilidades analisadas."""
    prob_red, prob_black, prob_white = analisar_padroes(limite)

    if prob_red is None:
        return None, 0  # Se não há dados, não apostar

    if prob_red > prob_black:
        return "red", calcular_aposta(banca, prob_red, 2)
    elif prob_black > prob_red:
        return "black", calcular_aposta(banca, prob_black, 2)
    else:
        return "white", calcular_aposta(banca, prob_white, 14)

# Exemplo de uso
if __name__ == "__main__":
    banca = 50  # Banca inicial
    cor_escolhida, aposta = melhor_aposta(banca)

    if cor_escolhida:
        print(f"🎯 Melhor aposta: {cor_escolhida.upper()} - Valor: R${aposta:.2f}")
        logging.info(f"Aposta recomendada: {cor_escolhida.upper()} - R${aposta:.2f}")
    else:
        print("⚠️ Nenhum dado disponível para análise.")
