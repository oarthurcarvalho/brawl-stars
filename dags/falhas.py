import subprocess
from pathlib import Path

# este arquivo também entra por link simbólico na pasta de DAGs, que o Airflow põe no sys.path,
# então as DAGs fazem "from falhas import avisar_falha"
REPO = Path(__file__).resolve().parent.parent
PYTHON_BRAWL = str(REPO / ".venv" / "bin" / "python")
AVISO = str(REPO / "ingest" / "aviso.py")


def avisar_falha(context):
    # o Airflow chama isto quando a tarefa falha de vez, depois de esgotar os retries
    ti = context["task_instance"]
    texto = (
        f"❌ {ti.dag_id} › {ti.task_id} falhou\n"
        f"run: {ti.run_id}\n"
        "o motivo está no log da tarefa no Airflow"
    )
    # o envio roda no Python do projeto, que tem o requests e lê o .env, como as tarefas.
    # Se o aviso falhar, só registra: o callback não pode levantar erro
    try:
        resultado = subprocess.run([PYTHON_BRAWL, AVISO, texto], capture_output=True, text=True, timeout=60)
    except subprocess.TimeoutExpired:
        print("aviso no Telegram: tempo esgotado")
        return
    if resultado.returncode != 0:
        print(f"aviso no Telegram falhou: {resultado.stderr.strip()[-300:]}")
