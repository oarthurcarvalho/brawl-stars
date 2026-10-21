import csv
import random
from collections import Counter
from datetime import datetime, timezone

from armazenamento import COLETA_DIR, baixar_r2, enviar_r2
from perfis import FAIXAS, faixa, ler_coletados

ARQUIVO_AMOSTRA = COLETA_DIR / "painel" / "amostra.csv"
CHAVE_AMOSTRA = "painel/amostra.csv"
POR_FAIXA = 3333
SEMENTE = 42
CAMPOS = ["tag", "faixa", "trofeus", "data_entrada"]


def sortear_amostra(trofeus):
    grupos = {f: [] for f in FAIXAS}
    for tag, t in trofeus.items():
        grupos[faixa(t)].append(tag)
    for f in FAIXAS:
        if len(grupos[f]) < POR_FAIXA:
            raise RuntimeError(f"faixa {f} tem só {len(grupos[f])} perfis; precisa de {POR_FAIXA}")

    hoje = datetime.now(timezone.utc).date().isoformat()
    rng = random.Random(SEMENTE)
    linhas = []
    # sorted() antes do sample: a mesma semente só repete o sorteio se a entrada vier na mesma ordem
    for f in FAIXAS:
        for tag in rng.sample(sorted(grupos[f]), POR_FAIXA):
            linhas.append({"tag": tag, "faixa": f, "trofeus": trofeus[tag], "data_entrada": hoje})
    return linhas


def ler_amostra():
    # só lê: a coleta diária nunca pode sortear uma amostra nova por engano
    if not baixar_r2(CHAVE_AMOSTRA, ARQUIVO_AMOSTRA):
        raise RuntimeError(f"{CHAVE_AMOSTRA} não está no R2; rode escolher_amostra() antes")
    with open(ARQUIVO_AMOSTRA, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def escolher_amostra():
    # a amostra é fixa: se já está no R2, só lê; sortear de novo quebraria as coortes
    if baixar_r2(CHAVE_AMOSTRA, ARQUIVO_AMOSTRA):
        with open(ARQUIVO_AMOSTRA, newline="", encoding="utf-8") as f:
            return list(csv.DictReader(f))

    _, trofeus = ler_coletados()
    linhas = sortear_amostra(trofeus)
    ARQUIVO_AMOSTRA.parent.mkdir(parents=True, exist_ok=True)
    with open(ARQUIVO_AMOSTRA, "w", newline="", encoding="utf-8") as f:
        escritor = csv.DictWriter(f, fieldnames=CAMPOS)
        escritor.writeheader()
        escritor.writerows(linhas)
    enviar_r2(ARQUIVO_AMOSTRA, CHAVE_AMOSTRA)
    return linhas


if __name__ == "__main__":
    linhas = escolher_amostra()
    print(len(linhas), "jogadores na amostra;", dict(Counter(linha["faixa"] for linha in linhas)))
