import os

import requests
from dotenv import load_dotenv

load_dotenv()

API = "https://api.brawlstars.com/v1"

# reaproveita a conexão entre chamadas: ~0,3 s por chamada em vez de ~0,8 s
sessao = requests.Session()


def cabecalho():
    return {"Authorization": f"Bearer {os.environ['BRAWL_TOKEN']}"}


def codificar_tag(tag):
    return tag.replace("#", "%23")
