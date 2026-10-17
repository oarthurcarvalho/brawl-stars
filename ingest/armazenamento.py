import gzip
import json
import os
from datetime import datetime, timezone
from pathlib import Path

import boto3
from botocore.exceptions import ClientError
from dotenv import load_dotenv

load_dotenv()

COLETA_DIR = Path(os.environ.get("COLETA_DIR", "~/dados/brawl-stars")).expanduser()
BUCKET = "oarthurcarvalho-lake"


def salvar_bruto(fonte, dados, pais):
    agora = datetime.now(timezone.utc)
    arquivo = COLETA_DIR / fonte / f"dt={agora:%Y-%m-%d}" / f"{pais}_{agora:%H%M%S}.json.gz"
    arquivo.parent.mkdir(parents=True, exist_ok=True)
    envelope = {
        "fonte": fonte,
        "pais": pais,
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


if __name__ == "__main__":
    from ranking import coletar_ranking_players

    arquivo = salvar_bruto("brawl_ranking_players", coletar_ranking_players("BR"), "BR")
    print(arquivo)
    print(enviar_r2(arquivo))
