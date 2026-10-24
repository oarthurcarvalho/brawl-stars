import gzip
import json
import os
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import boto3
from botocore.exceptions import ClientError
from dotenv import load_dotenv

load_dotenv()

COLETA_DIR = Path(os.environ.get("COLETA_DIR", "~/dados/brawl-stars")).expanduser()
BUCKET = "oarthurcarvalho-lake"


def salvar_bruto(fonte, dados, parte):
    agora = datetime.now(timezone.utc)
    arquivo = COLETA_DIR / fonte / f"dt={agora:%Y-%m-%d}" / f"{parte}_{agora:%H%M%S}.json.gz"
    arquivo.parent.mkdir(parents=True, exist_ok=True)
    # parte = país no painel, lote nos perfis; arquivos de antes de 20/10 trazem a chave "pais"
    envelope = {
        "fonte": fonte,
        "parte": parte,
        "coletado_em": agora.isoformat(timespec="seconds"),
        "dados": dados,
    }
    with gzip.open(arquivo, "wt", encoding="utf-8") as f:
        json.dump(envelope, f, ensure_ascii=False)
    return arquivo


def cliente_r2():
    return boto3.client(
        "s3",
        endpoint_url=f"https://{os.environ['R2_ACCOUNT_ID']}.r2.cloudflarestorage.com",
        aws_access_key_id=os.environ["R2_ACCESS_KEY_ID"],
        aws_secret_access_key=os.environ["R2_SECRET_ACCESS_KEY"],
        region_name="auto",
    )


def enviar_r2(arquivo, chave=None):
    if chave is None:
        chave = "raw/" + arquivo.relative_to(COLETA_DIR).as_posix()
    cliente_r2().upload_file(str(arquivo), BUCKET, chave)
    return chave


def baixar_r2(chave, arquivo):
    arquivo.parent.mkdir(parents=True, exist_ok=True)
    try:
        cliente_r2().download_file(BUCKET, chave, str(arquivo))
    except ClientError as erro:
        if erro.response["Error"]["Code"] in ("404", "NoSuchKey"):
            return False
        raise
    return True


def partes_enviadas(fonte, dia):
    resposta = cliente_r2().list_objects_v2(Bucket=BUCKET, Prefix=f"raw/{fonte}/dt={dia}/")
    # raw/brawl_battlelogs/dt=2026-10-22/lote03_091502.json.gz -> lote03
    return {objeto["Key"].rsplit("/", 1)[1].split("_")[0] for objeto in resposta.get("Contents", [])}


def tamanho_no_r2(chave, cliente):
    try:
        return cliente.head_object(Bucket=BUCKET, Key=chave)["ContentLength"]
    except ClientError as erro:
        if erro.response["Error"]["Code"] in ("404", "NoSuchKey"):
            return None
        raise


def limpar_local(dias=7, simular=False):
    # o disco do Pi guarda só os últimos dias; o R2 guarda tudo. Só os brutos: o painel/ é estado
    limite = datetime.now(timezone.utc).date() - timedelta(days=dias)
    cliente = cliente_r2()
    apagados = 0
    for arquivo in sorted(COLETA_DIR.glob("*/dt=*/*.json.gz")):
        # a idade vem da partição (data da coleta), não da data de modificação do arquivo
        if date.fromisoformat(arquivo.parent.name.removeprefix("dt=")) > limite:
            continue
        chave = "raw/" + arquivo.relative_to(COLETA_DIR).as_posix()
        # só apaga o que tem cópia inteira no R2; tamanho diferente = envio que ficou pela metade
        if tamanho_no_r2(chave, cliente) != arquivo.stat().st_size:
            print(f"mantém {chave}: não está no R2 ou está diferente")
            continue
        if simular:
            print(f"apagaria {chave}")
        else:
            arquivo.unlink()
        apagados += 1
    if not simular:
        for pasta in COLETA_DIR.glob("*/dt=*"):
            if not any(pasta.iterdir()):
                pasta.rmdir()
    return apagados


if __name__ == "__main__":
    from ranking import coletar_ranking_players

    arquivo = salvar_bruto("brawl_ranking_players", coletar_ranking_players("BR"), "BR")
    print(arquivo)
    print(enviar_r2(arquivo))
