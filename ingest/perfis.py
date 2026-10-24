import csv
import gzip
import json
import random
from collections import Counter

from api import codificar_tag, coletar_em_paralelo, requisitar
from armazenamento import COLETA_DIR, baixar_r2, enviar_r2, salvar_bruto

# pool de candidatos montado em battlelog.py (montar_candidatos); fica aqui para o battlelog
# poder importar amostra -> perfis sem import circular
ARQUIVO_CANDIDATOS = COLETA_DIR / "painel" / "candidatos.csv"
CHAVE_CANDIDATOS = "painel/candidatos.csv"
FONTE = "brawl_players"
TAMANHO_LOTE = 1000
PRIMEIRA_RODADA = 10000
POR_FAIXA = 3500
FAIXAS = ("iniciante", "intermediario", "topo")
# troféus da conta que separam as faixas, escolhidos no histograma dos 10 mil primeiros perfis:
# iniciante < 20 mil (abaixo do 1º decil do pool) e topo >= 100 mil (~22% do pool)
CORTES = (20_000, 100_000)
ARQUIVO_HISTOGRAMA = COLETA_DIR / "painel" / "histograma_trofeus.csv"
CHAVE_HISTOGRAMA = "painel/histograma_trofeus.csv"


def coletar_perfil(tag):
    resposta = requisitar(f"/players/{codificar_tag(tag)}")
    if resposta.status_code == 404:
        return None
    resposta.raise_for_status()
    return resposta.json()


def coletar_perfis(tags, threads=5):
    return coletar_em_paralelo(coletar_perfil, tags, threads=threads)


def conta_jogada(perfil):
    # contas sem XP nunca jogaram: nome "Brawler", só a Shelly nível 1, zero vitórias (bots/fantasmas
    # que aparecem nas batalhas); eram 7% dos 10 mil primeiros perfis e ficam fora das faixas
    return perfil["expPoints"] > 0


def faixa(trofeus):
    if trofeus < CORTES[0]:
        return "iniciante"
    if trofeus < CORTES[1]:
        return "intermediario"
    return "topo"


def contar_faixas(trofeus):
    return Counter(faixa(t) for t in trofeus.values())


def arquivos_do_pool():
    return sorted((COLETA_DIR / FONTE).glob("dt=*/candidatos*.json.gz"))


def trofeus_validos(perfis):
    return {tag: perfil["trophies"] for tag, perfil in perfis.items() if conta_jogada(perfil)}


def ler_coletados():
    # lê os lotes do pool do disco local, e o limpar_local apaga brutos com mais de 7 dias (estão no R2).
    # Serviu para montar o pool e a amostra em 20 e 21/10; o que roda depois não deve depender dele
    coletados, trofeus = set(), {}
    for arquivo in arquivos_do_pool():
        with gzip.open(arquivo, "rt", encoding="utf-8") as f:
            perfis = json.load(f)["dados"]
        coletados.update(perfis)
        trofeus.update(trofeus_validos(perfis))
    return coletados, trofeus


def terminou(trofeus):
    if CORTES is None:
        return len(trofeus) >= PRIMEIRA_RODADA
    contagem = contar_faixas(trofeus)
    return all(contagem[f] >= POR_FAIXA for f in FAIXAS)


def salvar_histograma(trofeus, largura=5000):
    contagem = Counter(t // largura * largura for t in trofeus.values())
    ARQUIVO_HISTOGRAMA.parent.mkdir(parents=True, exist_ok=True)
    with open(ARQUIVO_HISTOGRAMA, "w", newline="", encoding="utf-8") as f:
        escritor = csv.writer(f)
        escritor.writerow(["trofeus_de", "trofeus_ate", "perfis"])
        for inicio in range(0, max(contagem) + largura, largura):
            escritor.writerow([inicio, inicio + largura - 1, contagem[inicio]])
    enviar_r2(ARQUIVO_HISTOGRAMA, CHAVE_HISTOGRAMA)


def classificar_pool():
    baixar_r2(CHAVE_CANDIDATOS, ARQUIVO_CANDIDATOS)
    with open(ARQUIVO_CANDIDATOS, newline="", encoding="utf-8") as f:
        candidatos = [linha["tag"] for linha in csv.DictReader(f)]
    # ordem sorteada: no teste de 20/10, começar pelo menor troféu de brawler trazia contas mais fortes
    # (mediana de 66 mil troféus contra 55 mil no sorteio), por causa do prestígio dos brawlers
    random.Random(42).shuffle(candidatos)

    # retoma de onde parou: os lotes já salvos no disco dizem quem já foi coletado
    coletados, trofeus = ler_coletados()
    pendentes = [tag for tag in candidatos if tag not in coletados]
    numero = len(arquivos_do_pool())
    while pendentes and not terminou(trofeus):
        lote, pendentes = pendentes[:TAMANHO_LOTE], pendentes[TAMANHO_LOTE:]
        numero += 1
        perfis = coletar_perfis(lote)
        enviar_r2(salvar_bruto(FONTE, perfis, f"candidatos{numero:03d}"))
        coletados.update(perfis)
        trofeus.update(trofeus_validos(perfis))
        progresso = dict(contar_faixas(trofeus)) if CORTES else ""
        print(f"lote {numero}: {len(perfis)} perfis, {len(trofeus)} válidos no total {progresso}")
    salvar_histograma(trofeus)
    return trofeus


if __name__ == "__main__":
    trofeus = classificar_pool()
    if CORTES is None:
        print(f"{len(trofeus)} perfis; escolha os CORTES em {ARQUIVO_HISTOGRAMA} e rode de novo")
    else:
        print(f"{len(trofeus)} perfis válidos; por faixa: {dict(contar_faixas(trofeus))}")
