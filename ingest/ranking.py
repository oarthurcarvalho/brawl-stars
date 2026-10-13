import os

import requests
from dotenv import load_dotenv

load_dotenv()

API = "https://api.brawlstars.com/v1"


def coletar_ranking_players(pais="BR"):
    
    headers = {"Authorization": f"Bearer {os.environ['BRAWL_TOKEN']}"}
    resposta = requests.get(f"{API}/rankings/{pais}/players", headers=headers, timeout=30)
    resposta.raise_for_status()
    return resposta.json()


if __name__ == "__main__":
    dados = coletar()
    print(len(dados["items"]), "jogadores")
    print([j["tag"] for j in dados["items"][:5]])