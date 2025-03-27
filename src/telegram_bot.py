import os
import sqlite3
import logging
from telegram import Bot
from datetime import datetime, timedelta
import time

# Configuração do log
logging.basicConfig(filename="data/logs.txt", level=logging.INFO, format="%(asctime)s - %(message)s")

# Configurações do Telegram
TOKEN = os.getenv("TELEGRAM_TOKEN", "SEU_TOKEN_AQUI")  # Usa variável de ambiente se disponível
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "SEU_CHAT_ID_AQUI")  # Permite definir via ambiente/config
bot = Bot(token=TOKEN)

# Definições de meta
STOP_WIN = 5  # Lucro alvo diário (exemplo: R$5)
STOP_LOSS = -5  # Perda máxima diária (exemplo: R$-5)
APOSTA_PADRAO = 2  # Valor inicial da aposta

# Inicializa o saldo do dia
saldo_dia = 0
apostas_realizadas = 0

# Função para criar tabelas se não existirem
def criar_tabelas():
    conn = sqlite3.connect('data/blaze_double.db')
    cursor = conn.cursor()
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS apostas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            data TEXT,
            valor REAL,
            resultado REAL
        )
    """)
    
    conn.commit()
    conn.close()

# Obtém o saldo acumulado do dia
def obter_saldo_do_dia():
    global saldo_dia
    conn = sqlite3.connect('data/blaze_double.db')
    cursor = conn.cursor()
    
    hoje = datetime.now().strftime("%Y-%m-%d")
    cursor.execute("SELECT SUM(resultado) FROM apostas WHERE data = ?", (hoje,))
    resultado = cursor.fetchone()
    
    conn.close()
    
    saldo_dia = resultado[0] if resultado[0] is not None else 0
    return saldo_dia

# Salva a aposta no banco de dados
def registrar_aposta(valor, resultado):
    global saldo_dia, apostas_realizadas

    conn = sqlite3.connect('data/blaze_double.db')
    cursor = conn.cursor()
    
    hoje = datetime.now().strftime("%Y-%m-%d")
    cursor.execute("INSERT INTO apostas (data, valor, resultado) VALUES (?, ?, ?)", (hoje, valor, resultado))
    
    conn.commit()
    conn.close()

    saldo_dia += resultado
    apostas_realizadas += 1

    # Verifica se atingiu stop-win ou stop-loss
    verificar_limites()

# Verifica se atingiu os limites e interrompe as apostas
def verificar_limites():
    global saldo_dia

    if saldo_dia >= STOP_WIN:
        bot.send_message(chat_id=CHAT_ID, text=f"🎉 Meta diária alcançada! Lucro de R${saldo_dia:.2f}. Encerrando as apostas por hoje! ✅")
        logging.info("STOP WIN atingido. Apostas encerradas.")
        return True
    elif saldo_dia <= STOP_LOSS:
        bot.send_message(chat_id=CHAT_ID, text=f"⚠️ Stop-loss atingido! Prejuízo de R${saldo_dia:.2f}. Parando as apostas. ❌")
        logging.warning("STOP LOSS atingido. Apostas encerradas.")
        return True
    
    return False

# Envia um sinal de aposta para o grupo do Telegram com hora exata
def enviar_sinal(cor, valor_aposta):
    global saldo_dia

    if verificar_limites():
        logging.info(f"Tentativa de envio de sinal bloqueada. Stop-win/loss atingido. (Saldo: R${saldo_dia:.2f})")
        return  # Evita enviar sinais se o limite foi atingido

    # Calcula o horário do próximo sorteio, que ocorre a cada 30 segundos
    now = datetime.now()
    next_sorteio = (now + timedelta(seconds=30 - now.second % 30))  # Próximo múltiplo de 30 segundos
    horario_entrada = next_sorteio.strftime("%H:%M:%S")  # Formato HH:MM:SS

    mensagem = f"🎯 Sinal de Aposta: Apostar no **{cor.upper()}** 💰\n"
    mensagem += f"💵 Valor: R${valor_aposta:.2f}\n"
    mensagem += f"🕒 Hora da entrada: {horario_entrada}\n"
    mensagem += f"📊 Saldo do dia: R${saldo_dia:.2f}"

    bot.send_message(chat_id=CHAT_ID, text=mensagem)
    logging.info(f"Enviado sinal: {cor} - R${valor_aposta:.2f} - Hora da entrada: {horario_entrada}")

# Registra o resultado da aposta e atualiza o saldo
def registrar_resultado(resultado):
    if resultado > 0:
        bot.send_message(chat_id=CHAT_ID, text=f"✅ Ganhamos! Lucro de R${resultado:.2f}.")
        logging.info(f"Lucro registrado: R${resultado:.2f}")
    else:
        bot.send_message(chat_id=CHAT_ID, text=f"❌ Perdemos! Perda de R${-resultado:.2f}.")
        logging.warning(f"Perda registrada: R${-resultado:.2f}")

    registrar_aposta(APOSTA_PADRAO, resultado)

# Criar tabelas ao iniciar
criar_tabelas()

# Exemplo de uso (remova os comentários para testar):
# enviar_sinal("red", 2)
# registrar_resultado(2)  # Ganhou
# registrar_resultado(-2) # Perdeu
