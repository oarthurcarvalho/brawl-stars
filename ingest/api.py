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
    # tenta de novo só no que é passageiro: 429 (limite de chamadas), 5xx (servidor) e falha de rede.
    # 401/403/404 voltam na hora, porque repetir não muda a resposta. A API não diz quanto esperar,
    # então a espera dobra a cada tentativa (1, 2, 4, 8 s)
    for tentativa in range(tentativas):
        ultima = tentativa == tentativas - 1
        try:
            resposta = sessao_da_thread().get(f"{API}{caminho}", headers=cabecalho(), timeout=30)
        except (requests.ConnectionError, requests.Timeout):
            if ultima:
                raise
        else:
            if ultima or (resposta.status_code != 429 and resposta.status_code < 500):
                return resposta
        sleep(2 ** tentativa)


def coletar_em_paralelo(coletar, tags, threads=5, minimo=0.9):
    def coletar_sem_quebrar(tag):
        try:
            return coletar(tag)
        except requests.HTTPError as erro:
            # 401/403 = token inválido ou IP não liberado: vale para todas as tags, então para tudo
            if erro.response is not None and erro.response.status_code in (401, 403):
                raise
            print(f"{tag}: falhou ({erro})")
        except requests.RequestException as erro:
            print(f"{tag}: falhou ({erro})")
        return None

    with ThreadPoolExecutor(max_workers=threads) as executor:
        resultados = list(executor.map(coletar_sem_quebrar, tags))
    dados = {tag: resultado for tag, resultado in zip(tags, resultados) if resultado is not None}
    # lote incompleto não pode virar arquivo no R2: a retomada o daria por feito e nunca o refaria.
    # 404 de conta apagada é ~0,05% no battlelog e ~1,5% nos perfis, bem abaixo do limite
    if len(dados) < minimo * len(tags):
        raise RuntimeError(f"só {len(dados)} de {len(tags)} tags vieram; o lote não foi salvo")
    return dados
