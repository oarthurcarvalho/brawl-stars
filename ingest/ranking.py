import os
import requests
from dotenv import load_dotenv

load_dotenv()

def coletar(country="BR"):
    
    token = os.getenv("BRAWL_TOKEN")

    header = {
        'Authorization': f'Bearer {token}'
    }

    url = f'https://api.brawlstars.com/v1/rankings/{country}/players'

    response = requests.get(url=url, headers=header)

    print(response.json())

if __name__ == '__main__':
    coletar()
