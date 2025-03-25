import os
from dotenv import load_dotenv

# Carrega as variáveis do arquivo .env
load_dotenv()

# Configurações do Telegram
TOKEN = os.getenv("TELEGRAM_TOKEN")  # Usa a variável de ambiente
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")  # Usa a variável de ambiente

# Exemplo de como verificar se as variáveis estão corretas
if TOKEN is None or CHAT_ID is None:
    raise ValueError("Por favor, defina as variáveis TELEGRAM_TOKEN e TELEGRAM_CHAT_ID no arquivo .env")
