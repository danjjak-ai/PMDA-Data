import requests
from bs4 import BeautifulSoup
import time

url = "https://www.pmda.go.jp/PmdaSearch/iyakuSearch/"
headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Referer": "https://www.pmda.go.jp/PmdaSearch/iyakuSearch/"
}

session = requests.Session()
session.headers.update(headers)

# 1. Get the search page to get any cookies (if needed)
session.get(url)

# 2. Post search
data = {
    "nameWord": "オプジーボ",
    "iyakuHowtoNameSearchRadioValue": "1",
    "btnA": "検索",
    "ListRows": "20"
}
resp = session.post(url, data=data)
print(f"Search Status: {resp.status_code}")

with open("search_result.html", "w", encoding="utf-8") as f:
    f.write(resp.text)

soup = BeautifulSoup(resp.text, "html.parser")
# Result table links are usually in <td> with class like 'ResultDataSet' or similar
# Let's find all links and filter
links = []
for a in soup.find_all("a", href=True):
    href = a["href"]
    text = a.get_text(strip=True)
    if "ResultDataSet" in href:
        links.append((text, href))
        print(f"Found candidate: {text} -> {href}")

if links:
    # 3. Get detail page
    detail_url = links[0][1]
    if not detail_url.startswith("http"):
        detail_url = "https://www.pmda.go.jp" + detail_url
    
    print(f"\nFetching Detail Page: {detail_url}")
    detail_resp = session.get(detail_url)
    print(f"Detail Status: {detail_resp.status_code}")
    
    with open("detail_page.html", "w", encoding="utf-8") as f:
        f.write(detail_resp.text)
    
    detail_soup = BeautifulSoup(detail_resp.text, "html.parser")
    print("\nDocuments found on Detail Page:")
    for a in detail_soup.find_all("a", href=True):
        h = a["href"]
        t = a.get_text(strip=True)
        # PMDA PDF links often have 'target="_blank"' and start with '/.../xxx.pdf'
        if ".pdf" in h.lower():
            print(f" - [{t}]: {h}")
else:
    print("No candidates found in result table.")
