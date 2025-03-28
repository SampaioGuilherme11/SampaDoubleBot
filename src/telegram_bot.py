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
log_path = os.path.join(os.path.dirname(__file__), 'dist', 'data', 'logs.txt')
os.makedirs(os.path.dirname(log_path), exist_ok=True)

saldo_dia = 0
apostas_realizadas = 0
usuario_logado = None

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
        # Criação da tabela 'apostas'
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS apostas (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                data TEXT,
                valor REAL,
                resultado TEXT
            )
        """)
        # Criação da tabela 'usuarios'
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS usuarios (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nome TEXT NOT NULL,
                senha TEXT NOT NULL,
                banca REAL NOT NULL,
                data_criacao DATETIME DEFAULT CURRENT_TIMESTAMP,
                data_ultima_edicao DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)
        conn.commit()
        conn.close()
        logging.info("Tabelas verificadas ou criadas com sucesso.")
    except Exception as e:
        logging.error(f"Erro ao criar/verificar tabelas: {e}")

def cadastrar_usuario(nome, senha, banca):
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO usuarios (nome, senha, banca) 
            VALUES (?, ?, ?)
        """, (nome, senha, banca))
        conn.commit()
        conn.close()
        logging.info("Usuário cadastrado com sucesso!")
        return "Cadastro realizado com sucesso!"
    except Exception as e:
        logging.error(f"Erro ao cadastrar usuário: {e}")
        return "Erro ao cadastrar usuário."
    
def atualizar_banca(nome, senha, nova_banca):
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        # Verifica se o nome e senha correspondem ao registro
        cursor.execute("""
            SELECT * FROM usuarios WHERE nome = ? AND senha = ?
        """, (nome, senha))
        usuario = cursor.fetchone()

        if not usuario:
            conn.close()
            return "Nome ou senha incorretos. Atualização não realizada."

        # Atualiza o valor da banca
        cursor.execute("""
            UPDATE usuarios
            SET banca = ?, data_ultima_edicao = CURRENT_TIMESTAMP
            WHERE nome = ? AND senha = ?
        """, (nova_banca, nome, senha))
        conn.commit()
        conn.close()
        logging.info(f"Banca do usuário {nome} atualizada para R${nova_banca:.2f}")
        return "Banca atualizada com sucesso!"
    except Exception as e:
        logging.error(f"Erro ao atualizar banca: {e}")
        return "Erro ao atualizar banca."
    
def obter_banca_atual(nome, senha):
    """Busca o valor atual da banca do usuário com base no nome e senha."""
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        # Localiza o usuário pelo nome e senha
        cursor.execute("""
            SELECT banca FROM usuarios WHERE nome = ? AND senha = ?
        """, (nome, senha))
        usuario = cursor.fetchone()
        conn.close()

        if usuario:
            return usuario[0]  # Retorna o valor da banca
        else:
            logging.warning("Usuário não encontrado ou credenciais inválidas.")
            return None
    except Exception as e:
        logging.error(f"Erro ao obter a banca atual: {e}")
        return None
    
def exibir_dados_usuario(nome, senha):
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute("""
            SELECT * FROM usuarios WHERE nome = ? AND senha = ?
        """, (nome, senha))
        usuario = cursor.fetchone()
        conn.close()
        if usuario:
            return {
                "id": usuario[0],
                "nome": usuario[1],
                "banca": usuario[3],
                "data_criacao": usuario[4],
                "data_ultima_edicao": usuario[5]
            }
        else:
            return "Usuário não encontrado ou senha incorreta."
    except Exception as e:
        logging.error(f"Erro ao exibir dados do usuário: {e}")
        return "Erro ao buscar dados do usuário."

def obter_saldo_do_dia():
    """Retorna o saldo acumulado de apostas para o dia de hoje."""
    global saldo_dia
    try:
        # Conectar ao banco de dados
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        # Obter a soma dos resultados para o dia de hoje
        hoje = datetime.now().strftime("%Y-%m-%d")
        cursor.execute("SELECT SUM(resultado) FROM apostas WHERE data = ?", (hoje,))
        resultado = cursor.fetchone()
        conn.close()

        # Atualizar o saldo diário global
        saldo_dia = resultado[0] if resultado[0] is not None else 0
        logging.info(f"Saldo do dia atualizado: R${saldo_dia:.2f}")
        return saldo_dia

    except Exception as e:
        logging.error(f"Erro ao obter saldo do dia: {e}")
        return 0

def obter_saldo_do_dia():
    """Retorna o saldo acumulado de apostas para o dia de hoje."""
    global saldo_dia
    try:
        # Conectar ao banco de dados
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        # Obter a soma dos resultados para o dia de hoje
        hoje = datetime.now().strftime("%Y-%m-%d")
        cursor.execute("SELECT SUM(resultado) FROM apostas WHERE data = ?", (hoje,))
        resultado = cursor.fetchone()
        conn.close()

        # Atualizar o saldo diário global
        saldo_dia = resultado[0] if resultado[0] is not None else 0
        logging.info(f"Saldo do dia atualizado: R${saldo_dia:.2f}")
        return saldo_dia

    except Exception as e:
        logging.error(f"Erro ao obter saldo do dia: {e}")
        return 0

def verificar_limites():
    """Verifica se os limites de Stop Win ou Stop Loss foram atingidos e encerra apostas se necessário."""
    global saldo_dia, usuario_logado
    try:
        # Verificar se há um usuário logado
        if usuario_logado is None:
            logging.warning("Tentativa de verificar limites sem usuário logado.")
            return False

        # Verificar limites de Stop Win e Stop Loss
        if saldo_dia >= STOP_WIN:
            enviar_mensagem(
                f"🎉 Meta diária alcançada! Lucro de R${saldo_dia:.2f}. Encerrando as apostas por hoje! ✅"
            )
            logging.info("STOP WIN atingido. Apostas encerradas.")
            return True
        elif saldo_dia <= STOP_LOSS:
            enviar_mensagem(
                f"⚠️ Stop-loss atingido! Prejuízo de R${saldo_dia:.2f}. Parando as apostas. ❌"
            )
            logging.warning("STOP LOSS atingido. Apostas encerradas.")
            return True

        # Limites não atingidos
        return False
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
    global saldo_dia, apostas_realizadas, usuario_logado
    try:
        # Verificar se há um usuário logado
        if usuario_logado is None:
            await enviar_mensagem("❌ Você precisa fazer login para continuar. Use o comando /login Nome Senha.")
            return

        # Obter as credenciais do usuário logado
        nome_usuario = usuario_logado["nome"]
        senha_usuario = usuario_logado["senha"]

        # Definir o horário de entrada
        horario_entrada = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        # Registrar a aposta no banco com status "pendente"
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute("INSERT INTO apostas (data, valor, resultado) VALUES (?, ?, ?)", 
                       (horario_entrada, valor_aposta, "pendente"))
        conn.commit()
        conn.close()

        # Simular a espera para buscar o resultado
        await asyncio.sleep(30)
        resultado = obter_resultado_do_jogo(horario_entrada)  # Buscar o resultado da aposta

        # Atualizar o resultado no banco de dados
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute("UPDATE apostas SET resultado = ? WHERE data = ?", (resultado, horario_entrada))
        conn.commit()
        conn.close()

        # Obter a banca atual antes de atualizar
        banca_atual = obter_banca_atual(nome_usuario, senha_usuario)

        if banca_atual is None:
            logging.error("Não foi possível carregar a banca. Verifique seu cadastro.")
            await enviar_mensagem("❌ Erro ao carregar a banca. Operação pausada!")
            return

        # Atualizar saldo e banca com base no resultado
        if resultado == "win":
            saldo_dia += valor_aposta
            nova_banca = banca_atual + valor_aposta
            logging.info(f"Aposta WIN! Lucro de R${valor_aposta:.2f}.")
        elif resultado == "loss":
            saldo_dia -= valor_aposta
            nova_banca = banca_atual - valor_aposta
            logging.info(f"Aposta LOSS! Prejuízo de R${valor_aposta:.2f}.")
        else:
            logging.warning("Resultado pendente ou erro. Nenhuma atualização realizada.")
            return

        # Atualizar a banca no banco de dados
        atualizar_banca(nome_usuario, senha_usuario, nova_banca)

        # Enviar mensagem no Telegram com o resultado
        await enviar_mensagem(f"🎯 Resultado da aposta: {resultado.upper()} 💰\n"
                               f"Valor apostado: R${valor_aposta:.2f}\n"
                               f"Saldo do dia: R${saldo_dia:.2f}\n"
                               f"Nova banca: R${nova_banca:.2f}")

        # Incrementar número de apostas realizadas e verificar limites
        apostas_realizadas += 1
        verificar_limites()

    except Exception as e:
        logging.error(f"Erro ao registrar aposta ou verificar resultado: {e}")

# Função para obter o resultado da aposta no banco de dados baseado na hora de entrada
def obter_resultado_por_hora(horario_entrada):
    """Verifica se a aposta foi win ou loss com base no horário de entrada registrado no banco de dados."""
    try:
        # Conectar ao banco de dados
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        # Buscar o resultado da aposta com base no horário de entrada
        cursor.execute("SELECT resultado FROM apostas WHERE data = ?", (horario_entrada,))
        resultado = cursor.fetchone()
        conn.close()

        # Processar o resultado retornado
        if resultado:
            return resultado[0]  # Retorna 'win' ou 'loss'
        else:
            logging.warning(f"Nenhum resultado encontrado para o horário de entrada: {horario_entrada}")
            return "pendente"

    except Exception as e:
        logging.error(f"Erro ao buscar resultado da aposta: {e}")
        return "erro"
    
def cadastrar_usuario(nome, senha, banca):
    """Registra um usuário no banco de dados."""
    try:
        if not nome or not senha:
            logging.warning("Nome ou senha não fornecidos. Operação abortada.")
            return "❌ Nome ou senha não podem estar vazios."

        if banca <= 0:
            logging.warning("Valor da banca inválido. Operação abortada.")
            return "❌ O valor da banca deve ser maior que 0."

        # Conectar ao banco de dados
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        # Inserir o usuário na tabela
        cursor.execute("""
            INSERT INTO usuarios (nome, senha, banca)
            VALUES (?, ?, ?)
        """, (nome, senha, banca))
        conn.commit()
        conn.close()

        logging.info(f"Usuário cadastrado com sucesso: Nome={nome}, Banca=R${banca:.2f}")
        return "✅ Cadastro realizado com sucesso!"
    except sqlite3.IntegrityError:
        logging.error(f"Erro de integridade ao cadastrar usuário: Nome={nome}.")
        return "❌ Usuário já existe ou dados inválidos."
    except Exception as e:
        logging.error(f"Erro ao cadastrar usuário: {e}")
        return "❌ Ocorreu um erro inesperado ao cadastrar o usuário."

def login_usuario(update, context):
    global usuario_logado
    try:
        dados = context.args
        if len(dados) != 2:
            update.message.reply_text(
                "❌ Formato inválido! Use: /login Nome Senha\n"
                "Exemplo: /login pedro 1415"
            )
            return

        nome, senha = dados[0], dados[1]
        banca_atual = obter_banca_atual(nome, senha)

        if banca_atual is not None:
            usuario_logado = {"nome": nome, "senha": senha}
            update.message.reply_text(f"✅ Login realizado com sucesso!\n📊 Banca atual: R${banca_atual:.2f}")
        else:
            update.message.reply_text("❌ Nome ou senha inválidos. Tente novamente.")
    except Exception as e:
        logging.error(f"Erro no login: {e}")
        update.message.reply_text("❌ Erro ao fazer login.")

# Função para enviar o sinal de aposta via Telegram
async def enviar_sinal():
    global saldo_dia, usuario_logado
    try:
        # Verificar se há um usuário logado
        if usuario_logado is None:
            await enviar_mensagem("❌ Você precisa fazer login para continuar. Use o comando /login Nome Senha.")
            return

        # Obter informações do usuário logado
        nome_usuario = usuario_logado["nome"]
        senha_usuario = usuario_logado["senha"]
        banca_atual = obter_banca_atual(nome_usuario, senha_usuario)

        # Verificar se a banca está configurada
        if banca_atual is None:
            logging.error("Banca não encontrada. Operações pausadas.")
            await enviar_mensagem(
                "❌ Banca não encontrada! Use o comando /registrar para criar uma conta com sua banca inicial:\n"
                "Exemplo: /registrar pedro 1415 100.00"
            )
            return

        # Verificar limites antes de continuar
        if verificar_limites():
            logging.info("Tentativa de envio de sinal bloqueada devido a stop-win ou stop-loss.")
            return

        # Calcular o valor da aposta como uma porcentagem da banca
        percentual_aposta = 0.02  # 2% da banca
        valor_aposta = banca_atual * percentual_aposta

        # Obter o sinal de aposta
        cor, _ = gerar_sinal_aposta()  # Função para análise e geração do sinal
        horario_entrada = datetime.now().strftime("%H:%M:%S")  # Hora do próximo sorteio

        # Criar e enviar mensagem sobre o sinal
        mensagem = (
            f"🎯 Sinal de Aposta: Apostar no **{cor.upper()}** 💰\n"
            f"💵 Valor: R${valor_aposta:.2f}\n"
            f"🕒 Hora da entrada: {horario_entrada}\n"
            f"📊 Saldo do dia: R${saldo_dia:.2f}\n\n"
            "🔄 Aguardando o resultado da rodada..."
        )
        await enviar_mensagem(mensagem)
        logging.info(f"Sinal enviado: {cor} - R${valor_aposta:.2f} - Hora: {horario_entrada}")

        # Registrar aposta no banco de dados e verificar o resultado
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
    global usuario_logado  # Garantir que estamos usando a variável global
    try:
        # Criar tabelas necessárias no banco de dados
        criar_tabelas()

        # Enviar mensagem inicial ao Telegram pedindo login ou registro
        await enviar_mensagem(
            "👋 Bem-vindo ao bot de apostas!\n"
            "Para começar, faça login ou registre-se:\n\n"
            "1️⃣ Use **/login Nome Senha** para acessar sua conta.\n"
            "2️⃣ Use **/registrar Nome Senha BancaInicial** para criar uma nova conta."
        )

        # Iniciar o loop contínuo para envio de sinais
        while True:
            if usuario_logado:
                await enviar_sinal()  # Envia o sinal apenas se o usuário estiver logado
            else:
                logging.info("Aguardando login do usuário antes de enviar sinais.")
                await asyncio.sleep(30)  # Intervalo para verificar novamente
    except Exception as e:
        logging.error(f"Erro ao rodar o bot: {e}")

if __name__ == "__main__":
    asyncio.run(run_bot())  # Executa o bot de forma assíncrona
