import requests
from time import sleep

from api import API, cabecalho, codificar_tag, sessao


def coletar_ranking_clubs(pais="BR"):
    resposta = sessao.get(f"{API}/rankings/{pais}/clubs", headers=cabecalho(), timeout=30)
    resposta.raise_for_status()
    return resposta.json()


def coletar_membros_clube(tag_clube):
    resposta = sessao.get(f"{API}/clubs/{codificar_tag(tag_clube)}/members", headers=cabecalho(), timeout=30)
    if resposta.status_code == 404:
        return None
    resposta.raise_for_status()
    return resposta.json()


def coletar_membros_clubes(tags_clubes):
    dados = {}
    for tag_clube in tags_clubes:
        try:
            membros = coletar_membros_clube(tag_clube)
            if membros is not None:
                dados[tag_clube] = membros
        except requests.RequestException as erro:
            print(f"{tag_clube}: falhou ({erro})")
        sleep(0.2)
    return dados


if __name__ == "__main__":
    resposta = coletar_ranking_clubs("BR")
    clubes = resposta["items"]
    print(len(clubes), "clubes")
    print([c["tag"] for c in clubes[:5]])
    print(list(clubes[0].keys()))

    membros = coletar_membros_clubes([c["tag"] for c in clubes])
    print(len(membros), "clubes com membros")
    tags = {m["tag"] for resposta in membros.values() for m in resposta["items"]}
    print(len(tags), "tags únicas de membros")
