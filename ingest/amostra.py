import csv
import random
from collections import Counter
from datetime import datetime, timezone

from armazenamento import COLETA_DIR, baixar_r2, enviar_r2, partes_enviadas, salvar_bruto
from perfis import FAIXAS, FONTE as FONTE_PERFIS, coletar_perfis, faixa, ler_coletados

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


def lotes_da_amostra(tamanho=1000):
    linhas = ler_amostra()
    # as 9.999 originais e os novatos em lotes separados: os novatos entram no fim do CSV toda semana,
    # e fatiar só pela posição mudaria o lote10 (que tem 999). Assim lote01..lote10 nunca mudam
    grupos = [
        ("lote", [l["tag"] for l in linhas if l["faixa"] != "novato"]),
        ("novatos", [l["tag"] for l in linhas if l["faixa"] == "novato"]),
    ]
    lotes = []
    for prefixo, tags in grupos:
        for numero, inicio in enumerate(range(0, len(tags), tamanho), start=1):
            lotes.append((f"{prefixo}{numero:02d}", tags[inicio:inicio + tamanho]))
    return lotes


def coletar_perfis_amostra():
    # perfis semanais da amostra (domingo): daqui saem as features da segmentação.
    # Mesma retomada do battlelog: num retry, as partes que já subiram hoje são puladas
    ja_enviados = partes_enviadas(FONTE_PERFIS, datetime.now(timezone.utc).date().isoformat())
    total = 0
    for parte, tags in lotes_da_amostra():
        if parte in ja_enviados:
            print(f"{parte}: já está no R2, pulando")
            continue
        perfis = coletar_perfis(tags, threads=10)
        enviar_r2(salvar_bruto(FONTE_PERFIS, perfis, parte))
        total += len(perfis)
        print(f"{parte}: {len(perfis)} perfis")
    return total


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
