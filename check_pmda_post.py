import requests
from bs4 import BeautifulSoup

url = "https://www.pmda.go.jp/PmdaSearch/iyakuSearch/"
params = {"keyword": "オプジーボ", "search": "検索"}
headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
}

resp = requests.post(url, data=params, headers=headers)
print(f"Status: {resp.status_code}")
soup = BeautifulSoup(resp.text, "html.parser")
links = soup.select("a")
print(f"Total links found: {len(links)}")
for a in links[:50]:
    href = a.get("href", "")
    text = a.get_text(strip=True)
    if ".pdf" in href.lower() or "オプジーボ" in text:
        print(f" - {text}: {href}")
