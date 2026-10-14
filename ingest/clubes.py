import requests

from api import API, cabecalho


def coletar_ranking_clubs(pais="BR"):
    resposta = requests.get(f"{API}/rankings/{pais}/clubs", headers=cabecalho(), timeout=30)
    resposta.raise_for_status()
    return resposta.json()


if __name__ == "__main__":
    resposta = coletar_ranking_clubs("BR")
    clubes = resposta["items"]
    print(len(clubes), "clubes")
    print([c["tag"] for c in clubes[:5]])
    print(list(clubes[0].keys()))
