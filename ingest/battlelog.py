import csv
import random
import time

import requests

from api import API, cabecalho, codificar_tag, sessao
from armazenamento import COLETA_DIR, baixar_r2, enviar_r2, salvar_bruto
from painel import ARQUIVO_PAINEL, CHAVE_PAINEL

ARQUIVO_CANDIDATOS = COLETA_DIR / "painel" / "candidatos.csv"
CHAVE_CANDIDATOS = "painel/candidatos.csv"


def coletar_battlelog(tag):
    resposta = sessao.get(f"{API}/players/{codificar_tag(tag)}/battlelog", headers=cabecalho(), timeout=30)
    if resposta.status_code == 404:
        return None
    resposta.raise_for_status()
    return resposta.json()


def extrair_participantes(battlelogs):
    menor_trofeu = {}
    for resposta in battlelogs.values():
        for item in resposta["items"]:
            batalha = item["battle"]
            # só partidas de troféus: no ranqueado (soloRanked) trophies traz o rank e no amistoso vem -1
            if batalha.get("type") != "ranked":
                continue
            jogadores = [j for equipe in batalha.get("teams", []) for j in equipe] + batalha.get("players", [])
            for jogador in jogadores:
                trofeus = jogador.get("brawler", {}).get("trophies")
                if trofeus is None:
                    continue
                tag = jogador["tag"]
                menor_trofeu[tag] = min(trofeus, menor_trofeu.get(tag, trofeus))
    return menor_trofeu


def salvar_candidatos(menor_trofeu):
    ARQUIVO_CANDIDATOS.parent.mkdir(parents=True, exist_ok=True)
    with open(ARQUIVO_CANDIDATOS, "w", newline="", encoding="utf-8") as f:
        escritor = csv.writer(f)
        escritor.writerow(["tag", "trofeus_min"])
        # ordenado só para o arquivo sair igual a cada rodada; os perfis sorteiam a ordem (ver perfis.py)
        escritor.writerows(sorted(menor_trofeu.items(), key=lambda par: par[1]))
    enviar_r2(ARQUIVO_CANDIDATOS, CHAVE_CANDIDATOS)


if __name__ == "__main__":
    baixar_r2(CHAVE_PAINEL, ARQUIVO_PAINEL)
    with open(ARQUIVO_PAINEL, newline="", encoding="utf-8") as f:
        tags = [linha["tag"] for linha in csv.DictReader(f)]
    amostra = random.Random(42).sample(tags, 2000)

    inicio = time.perf_counter()
    battlelogs = {}
    for tag in amostra:
        try:
            resposta = coletar_battlelog(tag)
            if resposta is not None:
                battlelogs[tag] = resposta
        except requests.RequestException as erro:
            print(f"{tag}: falhou ({erro})")
    segundos = time.perf_counter() - inicio

    # teste de medição: fica só no disco local, fora do R2
    arquivo = salvar_bruto("brawl_battlelogs", battlelogs, "teste")
    print(len(battlelogs), "battlelogs em", round(segundos / 60, 1), "min")
    print(round(segundos / len(amostra), 3), "s por chamada")
    print(round(arquivo.stat().st_size / 1024 / len(battlelogs), 1), "KB por jogador (.json.gz)")

    candidatos = extrair_participantes(battlelogs)
    salvar_candidatos(candidatos)
    print(len(candidatos), "candidatos em", ARQUIVO_CANDIDATOS)
