import requests
from bs4 import BeautifulSoup

url = "https://www.pmda.go.jp/PmdaSearch/iyakuSearch/"
headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    # Try no Referer
}

s = requests.Session()
s.headers.update(headers)

# Get initial
s.get(url)

# Try search with 'keyword'
data = {"keyword": "オプジーボ", "search": "検索"}
resp = s.post(url, data=data)
print(f"Keyword search status: {resp.status_code}")
if "ResultDataSet" in resp.text:
    print("Keyword search SUCCESS!")
else:
    print("Keyword search FAILED.")

# Try search with 'nameWord'
data2 = {"nameWord": "オプジーボ", "iyakuHowtoNameSearchRadioValue": "1", "btnA": "検索"}
resp2 = s.post(url, data=data2)
print(f"NameWord search status: {resp2.status_code}")
if "ResultDataSet" in resp2.text:
    print("NameWord search SUCCESS!")
else:
    print("NameWord search FAILED.")

if "ResultDataSet" not in resp.text and "ResultDataSet" not in resp2.text:
    print("\nExtracting all form inputs from initial page...")
    soup = BeautifulSoup(s.get(url).text, "html.parser")
    form = soup.find("form", name="iyakuSearchActionForm")
    if form:
        print(f"Form Action: {form.get('action')}")
        for inp in form.find_all("input"):
            print(f"  Input: {inp.get('name')} = {inp.get('value')}")
    else:
        print("No form found!")
