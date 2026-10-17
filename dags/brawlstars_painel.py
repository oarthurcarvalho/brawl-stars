from pathlib import Path

import pendulum
from airflow.sdk import dag, task

# a DAG entra na pasta de DAGs do Airflow por link simbólico, então resolve() aponta para o repositório
REPO = Path(__file__).resolve().parent.parent
PASTA_INGEST = str(REPO / "ingest")
# ambiente do projeto, criado com o mesmo Python do Airflow e com o requirements.txt instalado
PYTHON_BRAWL = str(REPO / ".venv" / "bin" / "python")


@dag(
    dag_id="brawlstars_painel",
    schedule="0 5 * * 1",
    start_date=pendulum.datetime(2026, 10, 12, tz="America/Sao_Paulo"),
    catchup=False,
    tags=["brawl-stars"],
)
def brawlstars_painel():
    @task.external_python(python=PYTHON_BRAWL, expect_airflow=False)
    def montar(pasta_ingest):
        import sys

        sys.path.insert(0, pasta_ingest)
        from painel import montar_painel

        return montar_painel()

    montar(PASTA_INGEST)


brawlstars_painel()
