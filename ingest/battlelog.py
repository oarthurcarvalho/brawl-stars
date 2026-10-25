import csv
import random
import time
from datetime import datetime, timezone

import requests

from amostra import lotes_da_amostra
from api import codificar_tag, coletar_em_paralelo, requisitar
from armazenamento import baixar_r2, enviar_r2, partes_enviadas, salvar_bruto
from painel import ARQUIVO_PAINEL, CHAVE_PAINEL
from perfis import ARQUIVO_CANDIDATOS, CHAVE_CANDIDATOS

FONTE = "brawl_battlelogs"
# medido em 21/10: 5 threads -> 15 a 25 min para 10 mil; 10 threads -> ~9 min, sem nenhum 429
THREADS = 10


def coletar_battlelog(tag):
    resposta = requisitar(f"/players/{codificar_tag(tag)}/battlelog")
    if resposta.status_code == 404:
        return None
    resposta.raise_for_status()
    return resposta.json()


def coletar_battlelogs(tags):
    return coletar_em_paralelo(coletar_battlelog, tags, threads=THREADS)


def coletar_dia():
    # retomada: num retry da DAG, os lotes que já subiram hoje não são coletados de novo.
    # Funciona porque a amostra é fixa: o lote03 é sempre o mesmo grupo de 1.000 jogadores
    ja_enviados = partes_enviadas(FONTE, datetime.now(timezone.utc).date().isoformat())
    total = 0
    for parte, tags in lotes_da_amostra():
        if parte in ja_enviados:
            print(f"{parte}: já está no R2, pulando")
            continue
        battlelogs = coletar_battlelogs(tags)
        enviar_r2(salvar_bruto(FONTE, battlelogs, parte))
        total += len(battlelogs)
        print(f"{parte}: {len(battlelogs)} battlelogs")
    return total


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


def montar_candidatos(quantidade=2000):
    # rodado uma vez em 19/10: mediu o battlelog (0,444 s por chamada, 4,0 KB por jogador)
    # e montou o pool de candidatos a partir dos participantes das batalhas
    baixar_r2(CHAVE_PAINEL, ARQUIVO_PAINEL)
    with open(ARQUIVO_PAINEL, newline="", encoding="utf-8") as f:
        tags = [linha["tag"] for linha in csv.DictReader(f)]
    amostra = random.Random(42).sample(tags, quantidade)

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
    arquivo = salvar_bruto(FONTE, battlelogs, "teste")
    print(len(battlelogs), "battlelogs em", round(segundos / 60, 1), "min")
    print(round(segundos / len(amostra), 3), "s por chamada")
    print(round(arquivo.stat().st_size / 1024 / len(battlelogs), 1), "KB por jogador (.json.gz)")

    candidatos = extrair_participantes(battlelogs)
    salvar_candidatos(candidatos)
    print(len(candidatos), "candidatos em", ARQUIVO_CANDIDATOS)


if __name__ == "__main__":
    inicio = time.perf_counter()
    total = coletar_dia()
    print(f"{total} battlelogs em {(time.perf_counter() - inicio) / 60:.1f} min")
