import requests
from bs4 import BeautifulSoup
import urllib.parse

url = "https://www.pmda.go.jp/PmdaSearch/iyakuSearch/"
headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Referer": "https://www.pmda.go.jp/PmdaSearch/iyakuSearch/"
}

session = requests.Session()
session.headers.update(headers)

# 1. Get initial page
resp = session.get(url)
soup = BeautifulSoup(resp.text, "html.parser")

# 2. Extract hidden fields
data = {}
for input_tag in soup.find_all("input"):
    name = input_tag.get("name")
    value = input_tag.get("value", "")
    if name:
        data[name] = value

# 3. Fill search terms
data["nameWord"] = "オプジーボ"
data["iyakuHowtoNameSearchRadioValue"] = "1"
data["btnA"] = "検索"
data["ListRows"] = "50"

# Remove any empty name tags or specific ones that might interfere
data = {k: v for k, v in data.items() if k}

print(f"Post Data: {data}")

# 4. Perform POST
resp = session.post(url, data=data)
print(f"Response Status: {resp.status_code}")
print(f"Response URL: {resp.url}")

with open("search_result_v2.html", "w", encoding="utf-8") as f:
    f.write(resp.text)

# 5. Analyze results
soup_res = BeautifulSoup(resp.text, "html.parser")
table = soup_res.select_one("table.result-table")
if table:
    print("Found Result Table!")
    for tr in table.select("tr"):
        links = tr.select("a")
        if links:
            print(f"Row: {[a.get_text(strip=True) for a in links]}")
            for a in links:
                print(f"  Link: {a.get('href')}")
else:
    print("No Result Table found.")
    # Maybe results are in a different structure
    for a in soup_res.find_all("a", href=True):
        if "ResultDataSet" in a["href"]:
            print(f"Direct link found: {a.get_text(strip=True)} -> {a['href']}")
