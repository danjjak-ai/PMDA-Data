import requests
from bs4 import BeautifulSoup

url = "https://www.pmda.go.jp/PmdaSearch/iyakuSearch/"
data = {
    "nameWord": "オプジーボ",
    "iyakuHowtoNameSearchRadioValue": "1",
    "btnA": "検索"
}
headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
}

s = requests.Session()
resp = s.post(url, data=data, headers=headers)
print(f"Status: {resp.status_code}")
soup = BeautifulSoup(resp.text, "html.parser")

# Find result links
for a in soup.select("table.result-table a"):
    href = a.get("href", "")
    text = a.get_text(strip=True)
    print(f"Candidate: {text} -> {href}")

# Try to follow the first candidate
if soup.select("table.result-table a"):
    first_url = soup.select("table.result-table a")[0].get("href")
    if not first_url.startswith("http"):
        first_url = "https://www.pmda.go.jp" + first_url
    print(f"\nFetching Detail Page: {first_url}")
    detail_resp = s.get(first_url, headers=headers)
    detail_soup = BeautifulSoup(detail_resp.text, "html.parser")
    print("\nLinks on Detail Page:")
    for a in detail_soup.select("a"):
        h = a.get("href", "")
        t = a.get_text(strip=True)
        if ".pdf" in h.lower() or "添付文書" in t or "RMP" in t or "IF" in t:
            print(f" - [{t}]: {h}")
