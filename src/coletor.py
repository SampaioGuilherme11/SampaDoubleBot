import requests
from bs4 import BeautifulSoup
import sqlite3

# Função para criar a tabela no banco de dados
def criar_tabela():
    conn = sqlite3.connect('data/blaze_double.db')
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS resultados (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            numero INTEGER,
            cor TEXT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()
    conn.close()

# Função para coletar os resultados do jogo Double da Blaze
def coletar_resultados():
    url = "https://blaze.com/pt/games/double"
    headers = {"User-Agent": "Mozilla/5.0"}
    
    response = requests.get(url, headers=headers)
    if response.status_code != 200:
        return None
    
    soup = BeautifulSoup(response.text, 'html.parser')
    
    # Encontrar o histórico de resultados (div main -> div entries)
    entries = soup.find("div", class_="main").find("div", class_="entries")
    
    # Coletar os números e as cores dos resultados
    resultados = []
    for entry in entries.find_all("div", class_=["red", "black", "white"]):
        numero_div = entry.find("div", class_="number")
        
        # Se for a cor branca, atribuímos o número 0, pois não há número real
        if entry.get("class")[0] == "white":
            cor = "white"
            resultados.append((0, cor))  # Representa o branco com número 0
        elif numero_div:
            numero = int(numero_div.text.strip())  # Pega o número
            cor = entry.get("class")[0]  # A classe da div indica a cor
            resultados.append((numero, cor))
    
    return resultados

# Função para salvar os resultados no banco de dados
def salvar_resultados(resultados):
    conn = sqlite3.connect('data/blaze_double.db')
    cursor = conn.cursor()
    
    for numero, cor in resultados:
        cursor.execute("INSERT INTO resultados (numero, cor) VALUES (?, ?)", (numero, cor))
    
    conn.commit()
    conn.close()

# Função principal para coletar e salvar os resultados
def coletar_e_salvar_resultados():
    # Coleta os resultados
    resultados = coletar_resultados()
    
    if resultados:
        # Se os resultados foram coletados, salva no banco de dados
        salvar_resultados(resultados)
        print(f"Resultados salvos: {resultados}")
    else:
        print("Erro ao coletar os resultados.")

# Criar a tabela se não existir
criar_tabela()

# Chamada para coletar e salvar os resultados (pode ser agendada para rodar a cada X minutos)
coletar_e_salvar_resultados()
