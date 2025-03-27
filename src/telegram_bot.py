import os
import sys
import sqlite3
import logging
import asyncio
from datetime import datetime
from telegram import Bot
from telegram.ext import Updater, CommandHandler
import random  # Apenas como exemplo, substitua por sua lógica real de análise

# Adicionando o diretório "src" ao sys.path para evitar erros de importação
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Importando configurações do arquivo config.py
from config.config import TOKEN, CHAT_ID

# Banco de Dados
db_path = os.path.join(os.path.dirname(__file__), 'dist', 'data', 'blaze_double.db')

# Configuração de Logs
log_path = os.path.join(os.path.dirname(__file__), 'logs.txt')
os.makedirs(os.path.dirname(log_path), exist_ok=True)

logging.basicConfig(filename=log_path, level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

if not TOKEN or not CHAT_ID:
    raise ValueError("Erro: TOKEN do Telegram ou CHAT_ID não configurado corretamente. Verifique o config.py!")

bot = Bot(token=TOKEN)

STOP_WIN = 5
STOP_LOSS = -5
APOSTA_PADRAO = 2
APOSTAS_MAX = 3

saldo_dia = 0
apostas_realizadas = 0

# Função de análise de apostas - Lógica aprimorada para análise de tendência
def gerar_sinal_aposta():
    """Análise aprimorada baseada em resultados anteriores para gerar o sinal de aposta"""
    resultados = obter_resultados_do_banco(100)  # Últimos 100 resultados
    if not resultados:
        return None, 0  # Se não houver dados, retorna "nenhuma aposta"

    cor_contagem = {"vermelho": 0, "preto": 0}
    for cor in resultados:
        if cor in cor_contagem:
            cor_contagem[cor] += 1

    prob_red = cor_contagem["vermelho"] / len(resultados)
    prob_black = cor_contagem["preto"] / len(resultados)

    logging.info(f"Probabilidades: Vermelho {prob_red:.2%}, Preto {prob_black:.2%}")

    if prob_red > prob_black:
        return "vermelho", APOSTA_PADRAO
    else:
        return "preto", APOSTA_PADRAO

# Funções de Banco de Dados
def obter_resultados_do_banco(limite=100):
    """Obtém os últimos resultados armazenados no banco de dados Blaze."""
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT cor FROM resultados ORDER BY datetime(created_at) DESC LIMIT ?", (limite,))
        resultados = cursor.fetchall()
        conn.close()
        return [r[0] for r in resultados]  # Retorna uma lista de cores
    except Exception as e:
        logging.error(f"Erro ao buscar resultados do banco: {e}")
        return []

def criar_tabelas():
    """Cria as tabelas necessárias no banco de dados."""
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS apostas (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                data TEXT,
                valor REAL,
                resultado TEXT
            )
        """)
        conn.commit()
        conn.close()
        logging.info("Banco de dados verificado com sucesso.")
    except Exception as e:
        logging.error(f"Erro ao criar/verificar banco de dados: {e}")

def obter_saldo_do_dia():
    """Retorna o saldo acumulado de apostas para o dia de hoje."""
    global saldo_dia
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        hoje = datetime.now().strftime("%Y-%m-%d")
        cursor.execute("SELECT SUM(resultado) FROM apostas WHERE data = ?", (hoje,))
        resultado = cursor.fetchone()
        conn.close()
        saldo_dia = resultado[0] if resultado[0] is not None else 0
        return saldo_dia
    except Exception as e:
        logging.error(f"Erro ao obter saldo do dia: {e}")
        return 0

def registrar_aposta(valor, resultado):
    """Registra uma aposta no banco de dados e atualiza o saldo do dia."""
    global saldo_dia, apostas_realizadas
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        hoje = datetime.now().strftime("%Y-%m-%d")
        cursor.execute("INSERT INTO apostas (data, valor, resultado) VALUES (?, ?, ?)", (hoje, valor, resultado))
        conn.commit()
        conn.close()
        saldo_dia += resultado
        apostas_realizadas += 1
        verificar_limites()
    except Exception as e:
        logging.error(f"Erro ao registrar aposta: {e}")

def verificar_limites():
    """Verifica se os limites de Stop Win ou Stop Loss foram atingidos."""
    global saldo_dia
    try:
        if saldo_dia >= STOP_WIN:
            enviar_mensagem(f"🎉 Meta diária alcançada! Lucro de R${saldo_dia:.2f}. Encerrando as apostas por hoje! ✅")
            logging.info("STOP WIN atingido. Apostas encerradas.")
            return True
        elif saldo_dia <= STOP_LOSS:
            enviar_mensagem(f"⚠️ Stop-loss atingido! Prejuízo de R${saldo_dia:.2f}. Parando as apostas. ❌")
            logging.warning("STOP LOSS atingido. Apostas encerradas.")
            return True
    except Exception as e:
        logging.error(f"Erro ao verificar limites: {e}")
    return False

def obter_resultado_do_jogo(horario_entrada):
    """Busca o resultado baseado na hora de entrada registrada no banco."""
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT cor FROM resultados WHERE datetime(created_at) >= datetime(?) ORDER BY created_at LIMIT 1", (horario_entrada,))
        resultado = cursor.fetchone()
        conn.close()

        if resultado:
            return "win" if resultado[0] == "vermelho" else "loss"  # Exemplo de lógica
        else:
            logging.warning(f"Nenhum resultado encontrado após {horario_entrada}")
            return "pendente"
    except Exception as e:
        logging.error(f"Erro ao buscar resultado do jogo: {e}")
        return "erro"

# Função para registrar a aposta e verificar o resultado após a entrada
async def registrar_aposta_e_verificar_resultado(cor, valor_aposta):
    global saldo_dia, apostas_realizadas
    try:
        horario_entrada = datetime.now().strftime("%Y-%m-%d %H:%M:%S")  # Hora atual precisa

        # Registrar aposta no banco com campo "pendente" para o resultado
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute("INSERT INTO apostas (data, valor, resultado) VALUES (?, ?, ?)",
                       (horario_entrada, valor_aposta, "pendente"))
        conn.commit()
        conn.close()

        # Simular espera e buscar resultado
        await asyncio.sleep(30)  # Tempo de espera antes de verificar o resultado
        resultado = obter_resultado_do_jogo(horario_entrada)  # Nova função para buscar o resultado no banco

        # Atualizar saldo e resultado no banco de dados
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute("UPDATE apostas SET resultado = ? WHERE data = ?", (resultado, horario_entrada))
        conn.commit()
        conn.close()

        # Atualizar saldo e enviar mensagem no Telegram
        if resultado == "win":
            saldo_dia += valor_aposta
            logging.info(f"Aposta WIN! Lucro de R${valor_aposta:.2f}.")
        elif resultado == "loss":
            saldo_dia -= valor_aposta
            logging.info(f"Aposta LOSS! Prejuízo de R${valor_aposta:.2f}.")

        await enviar_mensagem(f"🎯 Resultado da aposta: {resultado.upper()} 💰\n"
                               f"Valor apostado: R${valor_aposta:.2f}\n"
                               f"Saldo do dia: R${saldo_dia:.2f}")

        apostas_realizadas += 1
        verificar_limites()

    except Exception as e:
        logging.error(f"Erro ao registrar aposta ou verificar resultado: {e}")

# Função para obter o resultado da aposta no banco de dados baseado na hora de entrada
def obter_resultado_por_hora(horario_entrada):
    """Verifica se a aposta foi win ou loss com base no horário de entrada registrado no banco de dados"""
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT resultado FROM apostas WHERE data = ?", (horario_entrada,))
        resultado = cursor.fetchone()
        conn.close()
        if resultado:
            return resultado[0]  # Retorna 'win' ou 'loss'
        else:
            logging.warning(f"Nenhum resultado encontrado para o horário de entrada {horario_entrada}")
            return "pendente"
    except Exception as e:
        logging.error(f"Erro ao buscar resultado da aposta: {e}")
        return "erro"

# Função para enviar o sinal de aposta via Telegram
async def enviar_sinal():
    global saldo_dia
    try:
        if verificar_limites():
            logging.info("Tentativa de envio de sinal bloqueada devido a stop-win, stop-loss ou número máximo de apostas.")
            return

        cor, valor_aposta = gerar_sinal_aposta()  # Chama a função de análise para gerar o sinal
        horario_entrada = datetime.now().strftime("%H:%M:%S")  # Hora do próximo sorteio

        # Mensagem para aposta futura
        mensagem = (
            f"🎯 Sinal de Aposta: Apostar no **{cor.upper()}** 💰\n"
            f"💵 Valor: R${valor_aposta:.2f}\n"
            f"🕒 Hora da entrada: {horario_entrada}\n"
            f"📊 Saldo do dia: R${saldo_dia:.2f}\n\n"
            "🔄 Aguardando o resultado da rodada..."
        )
        await enviar_mensagem(mensagem)
        logging.info(f"Sinal enviado: {cor} - R${valor_aposta:.2f} - Hora: {horario_entrada}")

        # Registrar aposta e verificar resultado
        await registrar_aposta_e_verificar_resultado(cor, valor_aposta)

    except Exception as e:
        logging.error(f"Erro ao enviar sinal: {e}")

# Função para enviar a mensagem no Telegram
async def enviar_mensagem(texto):
    try:
        if not TOKEN or not CHAT_ID:
            raise ValueError("Erro: Telegram TOKEN ou CHAT_ID inválidos. Verifique suas configurações!")

        await bot.send_message(chat_id=CHAT_ID, text=texto)
        logging.info(f"Mensagem enviada para o Telegram: {texto}")
    except Exception as e:
        logging.error(f"Erro ao enviar mensagem no Telegram: {e}")

# Função principal para rodar o bot continuamente
async def run_bot():
    try:
        criar_tabelas()
        await enviar_mensagem("✅ Bot iniciado com sucesso! Verificando conexões...")

        while True:
            await enviar_sinal()  # Envia o sinal com base na análise
            await asyncio.sleep(60)  # Espera antes de verificar novamente

    except Exception as e:
        logging.error(f"Erro ao rodar o bot: {e}")

if __name__ == "__main__":
    asyncio.run(run_bot())  # Executa o bot de forma assíncrona
