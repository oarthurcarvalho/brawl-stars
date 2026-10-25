import csv
import gzip
import json
import random
from datetime import datetime, timezone

from amostra import ARQUIVO_AMOSTRA, CAMPOS, CHAVE_AMOSTRA, ler_amostra
from armazenamento import BUCKET, baixar_r2, cliente_r2, enviar_r2, salvar_bruto
from battlelog import FONTE as FONTE_BATTLELOG, extrair_participantes
from painel import ARQUIVO_PAINEL, CHAVE_PAINEL
from perfis import FONTE as FONTE_PERFIS, coletar_perfis, conta_jogada

PERFIS_POR_BUSCA = 2000
# conta nova: no pool de 20/10, as contas válidas abaixo de 5 mil troféus tinham nível mediano 15
# e 17 brawlers. Revisar depois das primeiras rodadas
NOVATO_MAX_TROFEUS = 5_000
NOVATO_MAX_NIVEL = 30


def chaves_r2(prefixo):
    paginas = cliente_r2().get_paginator("list_objects_v2").paginate(Bucket=BUCKET, Prefix=prefixo)
    return [objeto["Key"] for pagina in paginas for objeto in pagina.get("Contents", [])]


def participantes_do_ultimo_dia():
    cliente = cliente_r2()
    paginas = cliente.get_paginator("list_objects_v2").paginate(
        Bucket=BUCKET, Prefix=f"raw/{FONTE_BATTLELOG}/", Delimiter="/"
    )
    dias = [p["Prefix"] for pagina in paginas for p in pagina.get("CommonPrefixes", [])]
    if not dias:
        raise RuntimeError("nenhum battlelog no R2")
    ultimo = max(dias)  # raw/brawl_battlelogs/dt=2026-10-25/
    participantes = set()
    # um lote por vez, direto do R2: o dia inteiro na memória passaria de 1 GB no Pi
    for chave in chaves_r2(ultimo):
        corpo = cliente.get_object(Bucket=BUCKET, Key=chave)["Body"].read()
        participantes.update(extrair_participantes(json.loads(gzip.decompress(corpo))["dados"]))
    return ultimo, participantes


def eh_novato(perfil):
    return (
        conta_jogada(perfil)
        and perfil["trophies"] < NOVATO_MAX_TROFEUS
        and perfil["expLevel"] <= NOVATO_MAX_NIVEL
    )


def achar_novatos(limite=300):
    hoje = datetime.now(timezone.utc).date().isoformat()
    amostra = ler_amostra()  # baixa do R2: a cópia local fica atualizada antes do acréscimo
    if any(linha["faixa"] == "novato" and linha["data_entrada"] == hoje for linha in amostra):
        print("novatos de hoje já estão na amostra")
        return 0

    dia, participantes = participantes_do_ultimo_dia()
    baixar_r2(CHAVE_PAINEL, ARQUIVO_PAINEL)
    with open(ARQUIVO_PAINEL, newline="", encoding="utf-8") as f:
        painel = {linha["tag"] for linha in csv.DictReader(f)}
    restantes = sorted(participantes - painel - {linha["tag"] for linha in amostra})
    # sorteio com a data como semente: reproduzível. O menor troféu de brawler não serve de
    # prioridade (teste de 20/10: trazia contas mais fortes, por causa do prestígio)
    sorteados = random.Random(hoje).sample(restantes, min(PERFIS_POR_BUSCA, len(restantes)))

    perfis = coletar_perfis(sorteados, threads=10)
    # bruto é bruto: esses perfis são o "dia 0" dos novatos
    enviar_r2(salvar_bruto(FONTE_PERFIS, perfis, "busca_novatos"))
    novatos = sorted(tag for tag, perfil in perfis.items() if eh_novato(perfil))[:limite]

    # só acrescenta no fim: as linhas antigas (e os lotes 01-10) nunca mudam
    with open(ARQUIVO_AMOSTRA, "a", newline="", encoding="utf-8") as f:
        csv.DictWriter(f, fieldnames=CAMPOS).writerows(
            {"tag": tag, "faixa": "novato", "trofeus": perfis[tag]["trophies"], "data_entrada": hoje}
            for tag in novatos
        )
    enviar_r2(ARQUIVO_AMOSTRA, CHAVE_AMOSTRA)
    print(f"{dia}: {len(participantes)} participantes, {len(restantes)} fora do painel e da amostra, "
          f"{len(perfis)} perfis, {len(novatos)} novatos")
    return len(novatos)


if __name__ == "__main__":
    print(achar_novatos(), "novatos acrescentados à amostra")
