import requests
import sqlite3
import os
import time
from datetime import datetime

# Criar diretório se não existir
os.makedirs("data", exist_ok=True)

# Função para criar a tabela no banco de dados
def criar_tabela():
    conn = sqlite3.connect("data/blaze_double.db")
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS resultados (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            numero INTEGER,
            cor TEXT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            created_at TEXT UNIQUE
        )
    """)
    conn.commit()
    conn.close()

# Configuração dos Headers para a API da Blaze
headers = {
    'accept': 'application/json, text/plain, */*',
    'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/134.0.0.0 Safari/537.36',
}

# Função para obter o último `created_at` salvo no banco
def obter_ultimo_created_at():
    conn = sqlite3.connect("data/blaze_double.db")
    cursor = conn.cursor()
    cursor.execute("SELECT created_at FROM resultados ORDER BY created_at DESC LIMIT 1")
    ultimo = cursor.fetchone()
    conn.close()
    return ultimo[0] if ultimo else None

# Função para coletar os resultados do jogo Double da Blaze via API
def coletar_resultados():
    url = "https://blaze.bet.br/api/singleplayer-originals/originals/roulette_games/recent/1"
    
    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        data = response.json()

        for result in data:
            numero = result.get("roll", "Desconhecido")
            cor_codigo = result.get("color", -1)
            created_at = result.get("created_at", "")

            # Convertendo a data da API para um formato sem fração de segundos
            if created_at:
                try:
                    created_at = datetime.strptime(created_at, "%Y-%m-%dT%H:%M:%S.%fZ").strftime("%Y-%m-%d %H:%M:%S")
                except ValueError:
                    created_at = None

            # Mapeamento das cores baseado no código
            cores = {2: "Preto", 1: "Vermelho", 0: "Branco"}
            cor = cores.get(cor_codigo, "Desconhecido")

            return (numero, cor, created_at)  # Retorna apenas o mais recente

        return None
    except requests.exceptions.RequestException as e:
        print(f"Erro na requisição: {e}")
        return None

# Função para salvar um novo resultado no banco
def salvar_resultado(numero, cor, created_at):
    conn = sqlite3.connect("data/blaze_double.db")
    cursor = conn.cursor()

    try:
        cursor.execute("INSERT INTO resultados (numero, cor, created_at) VALUES (?, ?, ?)", (numero, cor, created_at))
        conn.commit()
        print(f"🔥 Novo resultado salvo: Número {numero}, Cor {cor}, Hora {created_at}")
    except sqlite3.IntegrityError:
        print(f"⚠️ Resultado já estava no banco: Número {numero}, Cor {cor}, Hora {created_at}")
    finally:
        conn.close()

# Função principal para monitorar os novos resultados
def coletar_e_salvar_continuamente():
    print("🎰 Iniciando monitoramento da Blaze Double...")
    while True:
        ultimo_created_at = obter_ultimo_created_at()
        resultado = coletar_resultados()

        if resultado:
            numero, cor, created_at = resultado

            # Se não há registros ou se o novo é mais recente, salvamos
            if ultimo_created_at is None or created_at > ultimo_created_at:
                salvar_resultado(numero, cor, created_at)
            else:
                print("⏳ Nenhum novo resultado detectado.")

        print("🔄 Aguardando 15 segundos para a próxima verificação...\n")
        time.sleep(15)  # Aguarda 10 segundos antes da próxima consulta

# Criar a tabela se não existir
criar_tabela()

# Iniciar a coleta contínua dos resultados
coletar_e_salvar_continuamente()
