import csv
from datetime import datetime, timezone

import requests

from armazenamento import COLETA_DIR, baixar_r2, enviar_r2, salvar_bruto
from clubes import coletar_membros_clubes, coletar_ranking_clubs
from ranking import PAISES, coletar_ranking_players

ARQUIVO_PAINEL = COLETA_DIR / "painel" / "brawl_tags.csv"
CHAVE_PAINEL = "painel/brawl_tags.csv"
CAMPOS = ["tag", "origem", "pais", "data_entrada"]


def coletar_pais(pais):
    jogadores = coletar_ranking_players(pais)
    clubes = coletar_ranking_clubs(pais)
    membros = coletar_membros_clubes([c["tag"] for c in clubes["items"]])
    for fonte, dados in [
        ("brawl_ranking_players", jogadores),
        ("brawl_ranking_clubs", clubes),
        ("brawl_club_members", membros),
    ]:
        enviar_r2(salvar_bruto(fonte, dados, pais))
    return jogadores, membros


def montar_painel(paises=PAISES):
    # o CSV do R2 manda: se a coleta rodar em outra máquina, nenhuma linha se perde
    baixar_r2(CHAVE_PAINEL, ARQUIVO_PAINEL)
    ja_no_painel = set()
    if ARQUIVO_PAINEL.exists():
        with open(ARQUIVO_PAINEL, newline="", encoding="utf-8") as f:
            ja_no_painel = {linha["tag"] for linha in csv.DictReader(f)}

    hoje = datetime.now(timezone.utc).date().isoformat()
    novas = {}
    coletados = 0
    for pais in paises:
        try:
            jogadores, membros = coletar_pais(pais)
        except requests.RequestException as erro:
            print(f"{pais}: falhou ({erro})")
            continue
        coletados += 1
        tags = [(j["tag"], "ranking_players") for j in jogadores["items"]]
        tags += [(m["tag"], "club_members") for resposta in membros.values() for m in resposta["items"]]
        antes = len(novas)
        for tag, origem in tags:
            if tag not in ja_no_painel and tag not in novas:
                novas[tag] = {"tag": tag, "origem": origem, "pais": pais, "data_entrada": hoje}
        print(pais, len(novas) - antes, "tags novas")
    if coletados == 0:
        raise RuntimeError("nenhum país foi coletado")

    # só acrescenta linhas ao fim do arquivo; nunca reescreve as antigas
    novo_arquivo = not ARQUIVO_PAINEL.exists()
    ARQUIVO_PAINEL.parent.mkdir(parents=True, exist_ok=True)
    with open(ARQUIVO_PAINEL, "a", newline="", encoding="utf-8") as f:
        escritor = csv.DictWriter(f, fieldnames=CAMPOS)
        if novo_arquivo:
            escritor.writeheader()
        escritor.writerows(novas.values())
    enviar_r2(ARQUIVO_PAINEL, CHAVE_PAINEL)
    return len(ja_no_painel) + len(novas)


if __name__ == "__main__":
    print(montar_painel(), "tags no painel")
