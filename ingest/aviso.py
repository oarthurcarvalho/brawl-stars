import os
import sys

import requests
from dotenv import load_dotenv

load_dotenv()


def enviar_aviso(texto):
    # o token vai na URL do Telegram: nenhum erro daqui pode repetir a URL, senão o token aparece no log
    try:
        resposta = requests.post(
            f"https://api.telegram.org/bot{os.environ['TELEGRAM_TOKEN']}/sendMessage",
            json={"chat_id": os.environ["TELEGRAM_CHAT_ID"], "text": texto},
            timeout=30,
        )
    except requests.RequestException as erro:
        raise RuntimeError(f"sem conexão com o Telegram ({type(erro).__name__})") from None
    if not resposta.ok:
        raise RuntimeError(f"Telegram respondeu {resposta.status_code}: {resposta.text[:200]}")


if __name__ == "__main__":
    # o callback das DAGs chama este arquivo com o texto; sem argumento, manda uma mensagem de teste
    enviar_aviso(sys.argv[1] if len(sys.argv) > 1 else "teste do aviso do coletor brawl-stars")
