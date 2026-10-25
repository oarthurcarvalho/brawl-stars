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
    dag_id="brawlstars_perfis",
    schedule="30 7 * * 0",
    start_date=pendulum.datetime(2026, 10, 24, tz="America/Sao_Paulo"),
    catchup=False,
    # um Trigger manual e a execução de domingo nunca rodam juntos
    max_active_runs=1,
    default_args={"retries": 2, "retry_delay": pendulum.duration(minutes=15)},
    tags=["brawl-stars"],
)
def brawlstars_perfis():
    @task.external_python(python=PYTHON_BRAWL, expect_airflow=False)
    def coletar(pasta_ingest):
        import sys

        sys.path.insert(0, pasta_ingest)
        from amostra import coletar_perfis_amostra

        return coletar_perfis_amostra()

    @task.external_python(python=PYTHON_BRAWL, expect_airflow=False)
    def limpar(pasta_ingest):
        import sys

        sys.path.insert(0, pasta_ingest)
        from armazenamento import limpar_local

        return limpar_local(dias=7)

    coletar(PASTA_INGEST) >> limpar(PASTA_INGEST)


brawlstars_perfis()
