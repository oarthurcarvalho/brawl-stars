from pathlib import Path

import pendulum
from airflow.decorators import dag, task

# o repositório é montado no container no mesmo caminho do Pi e a DAG entra na pasta de DAGs
# por link simbólico, então resolve() aponta para o repositório tanto no Pi quanto no container
REPO = Path(__file__).resolve().parent.parent
PASTA_INGEST = str(REPO / "ingest")
# ambiente do projeto, criado com o Python do container do Airflow e com o requirements.txt instalado
PYTHON_BRAWL = str(REPO / ".venv" / "bin" / "python")


@dag(
    dag_id="brawlstars_painel",
    schedule="0 5 * * 1",
    start_date=pendulum.datetime(2026, 10, 12, tz="America/Sao_Paulo"),
    catchup=False,
    default_args={"retries": 2, "retry_delay": pendulum.duration(minutes=15)},
    tags=["brawl-stars"],
)
def brawlstars_painel():
    @task.external_python(python=PYTHON_BRAWL, expect_airflow=False)
    def montar(pasta_ingest):
        import sys

        sys.path.insert(0, pasta_ingest)
        from painel import montar_painel

        return montar_painel()

    @task.external_python(python=PYTHON_BRAWL, expect_airflow=False)
    def novatos(pasta_ingest):
        import sys

        sys.path.insert(0, pasta_ingest)
        from novatos import achar_novatos

        return achar_novatos(limite=300)

    # segunda: painel (~25 min) e novatos (~5 min) terminam antes das 6h, quando o battlelog lê a amostra
    montar(PASTA_INGEST) >> novatos(PASTA_INGEST)


brawlstars_painel()
