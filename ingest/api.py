import os

from dotenv import load_dotenv

load_dotenv()

API = "https://api.brawlstars.com/v1"


def cabecalho():
    return {"Authorization": f"Bearer {os.environ['BRAWL_TOKEN']}"}
