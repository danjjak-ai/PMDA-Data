import requests
from bs4 import BeautifulSoup

url = "https://www.pmda.go.jp/PmdaSearch/iyakuSearch/"
headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
}

s = requests.Session()
s.headers.update(headers)

# Get initial
r = s.get(url)
soup = BeautifulSoup(r.text, "html.parser")
form = soup.find("form", attrs={"name": "iyakuSearchActionForm"})
if form:
    print(f"Form Action: {form.get('action')}")
    data = {}
    for inp in form.find_all("input"):
        n = inp.get('name')
        v = inp.get('value', '')
        if n:
            data[n] = v
    print(f"Data: {data}")
    
    # Try Search
    data["nameWord"] = "オプジーボ"
    data["iyakuHowtoNameSearchRadioValue"] = "1"
    data["btnA.x"] = "10"
    data["btnA.y"] = "10"
    
    resp = s.post("https://www.pmda.go.jp" + form.get('action'), data=data)
    print(f"Search status: {resp.status_code}")
    if "ResultDataSet" in resp.text:
        print("SUCCESS!")
    else:
        print("FAILED.")
        with open("fail.html", "w", encoding="utf-8") as f:
            f.write(resp.text)
else:
    print("No form found!")
