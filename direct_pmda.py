import requests
from bs4 import BeautifulSoup

url = "https://www.pmda.go.jp/PmdaSearch/iyakuSearch/iyakuSearch/" # Note the extra /
# Or check the action: action="/PmdaSearch/iyakuSearch"
url = "https://www.pmda.go.jp/PmdaSearch/iyakuSearch" # This is the action

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Referer": "https://www.pmda.go.jp/PmdaSearch/iyakuSearch/",
    "Origin": "https://www.pmda.go.jp",
    "Content-Type": "application/x-www-form-urlencoded"
}

data = {
    "nameWord": "オプジーボ",
    "iyakuHowtoNameSearchRadioValue": "1",
    "btnA": "検索",
    "ListRows": "50",
    # Try adding common hidden fields if needed
}

session = requests.Session()
# Must get cookies first
session.get("https://www.pmda.go.jp/PmdaSearch/iyakuSearch/")

resp = session.post(url, data=data, headers=headers)
print(f"Status: {resp.status_code}")
print(f"URL: {resp.url}")

soup = BeautifulSoup(resp.text, "html.parser")
with open("debug_results.html", "w", encoding="utf-8") as f:
    f.write(resp.text)

# Check for the results table
table = soup.select_one("table.result-table")
if table:
    print("SUCCESS: Found Result Table!")
else:
    print("FAILED: No table found.")
    # Check for direct links anyway
    links = [a for a in soup.find_all("a", href=True) if "ResultDataSet" in a["href"]]
    print(f"Direct links found: {len(links)}")
