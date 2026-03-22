from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
from bs4 import BeautifulSoup
import time
import os

def scrape_pmda(keyword):
    print(f"Searching for: {keyword}...")
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    # Add User Agent
    chrome_options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
    
    try:
        driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=chrome_options)
        driver.get("https://www.pmda.go.jp/PmdaSearch/iyakuSearch/")
        
        # Select 'Partial Match' and 'Both Name Types'
        # These are usually defaults, but let's be sure.
        
        input_field = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.NAME, "nameWord"))
        )
        input_field.send_keys(keyword)
        
        # Click search
        search_btn = driver.find_element(By.NAME, "btnA")
        search_btn.click()
        
        print("Waiting for results...")
        # PMDA results open in a new tab due to target="_blank"
        # Wait until a second handle exists or wait on the current page if it doesn't open new tab
        time.sleep(10) # 넉넉하게 기다림
        
        if len(driver.window_handles) > 1:
            driver.switch_to.window(driver.window_handles[1])
            print("Switched to result tab.")
        
        print(f"Current URL: {driver.current_url}")
        page_source = driver.page_source
        with open("selenium_results.html", "w", encoding="utf-8") as f:
            f.write(page_source)
            
        soup = BeautifulSoup(page_source, "html.parser")
        # Update your selectors here if needed
        # PMDA result table typically has links within td.ResultDataSet
        links = []
        for a in soup.find_all("a", href=True):
            href = a["href"]
            text = a.get_text(strip=True)
            if "ResultDataSet" in href:
                links.append({"name": text, "url": href})
        
        print(f"Found {len(links)} results.")
        for l in links[:10]:
            print(f"  Result: {l['name']} -> {l['url']}")
            
        driver.quit()
        return links
    except Exception as e:
        print(f"Error: {e}")
        return []

if __name__ == "__main__":
    scrape_pmda("オプジーボ")
