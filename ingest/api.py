import os
import threading
from concurrent.futures import ThreadPoolExecutor
from time import sleep

import requests
from dotenv import load_dotenv

load_dotenv()

API = "https://api.brawlstars.com/v1"

# reaproveita a conexão entre chamadas: ~0,3 s por chamada em vez de ~0,8 s
sessao = requests.Session()
# no paralelo, cada thread usa a própria sessão: a Session não é garantida entre threads
_local = threading.local()


def cabecalho():
    return {"Authorization": f"Bearer {os.environ['BRAWL_TOKEN']}"}


def codificar_tag(tag):
    return tag.replace("#", "%23")


def sessao_da_thread():
    if not hasattr(_local, "sessao"):
        _local.sessao = requests.Session()
    return _local.sessao


def requisitar(caminho, tentativas=5):
    for tentativa in range(tentativas):
        resposta = sessao_da_thread().get(f"{API}{caminho}", headers=cabecalho(), timeout=30)
        if resposta.status_code != 429:
            break
        # 429 = passou do limite de chamadas; a API não diz quanto esperar, então a espera dobra
        sleep(2 ** tentativa)
    return resposta


def coletar_em_paralelo(coletar, tags, threads=5):
    def coletar_sem_quebrar(tag):
        try:
            return coletar(tag)
        except requests.RequestException as erro:
            print(f"{tag}: falhou ({erro})")
            return None

    with ThreadPoolExecutor(max_workers=threads) as executor:
        resultados = list(executor.map(coletar_sem_quebrar, tags))
    return {tag: resultado for tag, resultado in zip(tags, resultados) if resultado is not None}
