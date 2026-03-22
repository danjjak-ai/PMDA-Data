from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
import time

def check_pmda_selenium():
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    
    try:
        driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=chrome_options)
        print("Driver initialized.")
        
        driver.get("https://www.pmda.go.jp/PmdaSearch/iyakuSearch/")
        print(f"Page Title: {driver.title}")
        
        # Find input
        wait = WebDriverWait(driver, 10)
        input_field = wait.until(EC.presence_of_element_located((By.NAME, "nameWord")))
        input_field.send_keys("オプジーボ")
        
        # Search button
        search_btn = driver.find_element(By.NAME, "btnA")
        search_btn.click()
        
        # Wait for results
        print("Waiting for results...")
        time.sleep(5) # Simple wait
        
        print(f"Current URL: {driver.current_url}")
        
        # Check for results
        results = driver.find_elements(By.CSS_SELECTOR, "table.result-table a")
        print(f"Results found: {len(results)}")
        for i, res in enumerate(results[:5]):
            print(f"  {i+1}: {res.text} -> {res.get_attribute('href')}")
            
        driver.quit()
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    check_pmda_selenium()
