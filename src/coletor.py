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
    
    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()  # Levanta um erro se o código de status não for 200 (sucesso)
    except requests.exceptions.RequestException as e:
        print(f"Erro na requisição: {e}")
        return None
    
    try:
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Encontrar o histórico de resultados (div main -> div entries)
        entries = soup.find("div", class_="main").find("div", class_="entries")
        
        # Coletar os números e as cores dos resultados
        resultados = []
        for entry in entries.find_all("div", class_=["red", "black", "white"]):
            numero_div = entry.find("div", class_="number")
            
            if entry.get("class")[0] == "white":
                cor = "white"
                resultados.append((0, cor))  # Representa o branco com número 0
            elif numero_div:
                numero = int(numero_div.text.strip())  # Pega o número
                cor = entry.get("class")[0]  # A classe da div indica a cor
                resultados.append((numero, cor))
        
        return resultados
    except Exception as e:
        print(f"Erro ao processar os dados: {e}")
        return None

# Função para salvar os resultados no banco de dados
def salvar_resultados(resultados):
    if not resultados:
        print("Nenhum resultado para salvar.")
        return
    
    conn = sqlite3.connect('data/blaze_double.db')
    cursor = conn.cursor()
    
    try:
        for numero, cor in resultados:
            cursor.execute("INSERT INTO resultados (numero, cor) VALUES (?, ?)", (numero, cor))
        conn.commit()
        print(f"Resultados salvos: {resultados}")
    except sqlite3.Error as e:
        print(f"Erro ao salvar no banco de dados: {e}")
    finally:
        conn.close()

# Função principal para coletar e salvar os resultados
def coletar_e_salvar_resultados():
    # Coleta os resultados
    resultados = coletar_resultados()
    
    if resultados:
        # Se os resultados foram coletados, salva no banco de dados
        salvar_resultados(resultados)
    else:
        print("Erro ao coletar os resultados.")

# Criar a tabela se não existir
criar_tabela()

# Chamada para coletar e salvar os resultados (pode ser agendada para rodar a cada X minutos)
coletar_e_salvar_resultados()
