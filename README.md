# Projeto de Retenção e Segmentação de jogadores de Brawl Stars

## Como rodar

```bash
pip install -r requirements.txt
python ingest/painel.py
```

O `.env` na raiz do repositório precisa de:

| Variável | Para quê |
|---|---|
| `BRAWL_TOKEN` | token da API do Brawl Stars (liberado para o IP da máquina que coleta) |
| `R2_ACCOUNT_ID` | conta da Cloudflare, usada no endpoint do R2 |
| `R2_ACCESS_KEY_ID` | chave de acesso do R2 |
| `R2_SECRET_ACCESS_KEY` | segredo da chave do R2 |
| `COLETA_DIR` | opcional; pasta dos arquivos brutos (padrão `~/dados/brawl-stars`) |

A DAG `dags/brawlstars_painel.py` roda `montar_painel()` toda segunda às 5h (America/Sao_Paulo).
