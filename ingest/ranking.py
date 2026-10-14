import requests
from time import sleep

from api import API, cabecalho

PAISES = ["BR", "AR", "PT", "ES", "FR", "DE", "IT", "GB", "NL", "PL"]

def coletar_ranking_players(pais="BR"):
    
    resposta = requests.get(f"{API}/rankings/{pais}/players", headers=cabecalho(), timeout=30)
    resposta.raise_for_status()
    return resposta.json()

def coletar_varios_paises(paises):
    dados = {}
    for pais in paises:
        try:
            dados[pais] = coletar_ranking_players(pais)
        except requests.RequestException as erro:
            print(f"{pais}: falhou ({erro})")
        sleep(0.5)
    if not dados:
        raise RuntimeError("nenhum país foi coletado")
    return dados


if __name__ == "__main__":
    dados = coletar_varios_paises(PAISES)
    for pais, resposta in dados.items():
        print(pais, len(resposta["items"]), "jogadores")
    tags = {j["tag"] for resposta in dados.values() for j in resposta["items"]}
    print(len(tags), "tags únicas")
