import requests
import json
import time

PMDA_SEARCH_API = "https://www.pmda.go.jp/rs-search/pharma"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept-Language": "ja,en;q=0.9",
}

def search(name, name_type):
    params = {
        "name": name,
        "nameType": str(name_type),
        "category": "medical",
        "_dc": str(int(time.time() * 1000)),
    }
    resp = requests.get(PMDA_SEARCH_API, params=params, headers=HEADERS)
    print(f"Status ({name_type}): {resp.status_code}")
    data = resp.json()
    print(json.dumps(data, indent=2, ensure_ascii=False))

print("--- Searching for オプジーボ ---")
search("オプジーボ", 1)
search("オプジーボ", 2)
