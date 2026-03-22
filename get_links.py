from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options

options = Options()
options.add_argument('--headless')
options.add_argument("--no-sandbox")
options.add_argument("--disable-dev-shm-usage")

d = webdriver.Chrome(service=Service(), options=options)
d.get('https://www.pmda.go.jp/PmdaSearch/iyakuDetail/GeneralList/4291427')

links = []
for a in d.find_elements(By.TAG_NAME, 'a'):
    href = a.get_attribute('href')
    text = a.text
    if href and '.pdf' in href.lower():
        links.append(f"{text}: {href}")

with open('links.txt', 'w') as f:
    f.write('\n'.join(links))

d.quit()
