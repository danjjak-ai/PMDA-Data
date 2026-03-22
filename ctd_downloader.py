#!/usr/bin/env python3
import os
import re
import time
import argparse
import logging
from pathlib import Path
import requests
import urllib.parse
from bs4 import BeautifulSoup

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
from tqdm import tqdm

# 로거 설정
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger("pmda_ctd")

class CTDDownloader:
    def __init__(self, output_dir: str = "."):
        self.output_dir = Path(output_dir)
        self.session = requests.Session()
        
    def sanitize_dirname(self, name: str) -> str:
        return re.sub(r'[\\/:*?"<>|／]', "_", name).strip()

    def download_file(self, url: str, dest: Path) -> bool:
        """URLからファイルをダウンロードしてdestに保存"""
        for _ in range(3):
            try:
                resp = self.session.get(url, stream=True, timeout=60, verify=False)
                resp.raise_for_status()
                total = int(resp.headers.get("content-length", 0))
                dest.parent.mkdir(parents=True, exist_ok=True)
                with open(dest, "wb") as f, tqdm(
                    total=total, unit="B", unit_scale=True,
                    desc=dest.name, leave=False
                ) as bar:
                    for chunk in resp.iter_content(chunk_size=8192):
                        if chunk:
                            f.write(chunk)
                            bar.update(len(chunk))
                log.info(f"  ✔ 저장: {dest}")
                return True
            except Exception as e:
                time.sleep(3)
        log.warning(f"  ✘ 다운로드 실패: {url}")
        return False

    def search_and_download_ctd(self, drug_name: str):
        log.info(f"🔍 [{drug_name}] CTD (申請資料概要) 검색 중...")
        
        chrome_options = Options()
        # Google Custom Search (봇 차단 방지용으로 Headless 모드 비활성화 - 브라우저 노출 설정 및 봇 우회 로직 추가)
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--start-maximized")
        chrome_options.add_argument("--lang=ja-JP") # 번역 팝업 방지를 위해 일본어 강제
        chrome_options.add_argument("--disable-blink-features=AutomationControlled") # 자동화 봇 감지 우회
        chrome_options.add_argument("user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
        
        # 크롬 번역 팝업(Translation) 비활성화 및 기타 방해 요소 제거
        prefs = {
            "intl.accept_languages": "ja,en_US,en",
            "translate": {"enabled": False},
            "profile.default_content_setting_values.notifications": 2,
            "credentials_enable_service": False,
            "profile.password_manager_enabled": False
        }
        chrome_options.add_experimental_option("prefs", prefs)
        chrome_options.add_experimental_option("excludeSwitches", ["enable-automation", "enable-logging"])
        chrome_options.add_experimental_option('useAutomationExtension', False)
        chrome_options.add_argument("--disable-features=TranslateUI")
        chrome_options.add_argument("--disable-translate")

        
        driver = None
        target_urls = set()
        
        try:
            driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=chrome_options)
            import urllib.parse
            search_query = f"site:pmda.go.jp/drugs/ {drug_name} 申請資料概要"
            driver.get(f"https://duckduckgo.com/html/?q={urllib.parse.quote(search_query)}")
            
            try:
                # DuckDuckGo HTML 렌더링 대기
                WebDriverWait(driver, 15).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, "a.result__url"))
                )
            except Exception as search_e:
                log.warning(f"검색 진행 중 결과 찾기 실패: {search_e}")
            
            for a in driver.find_elements(By.CSS_SELECTOR, "a.result__url"):
                href = a.get_attribute("href")
                if href and ("pmda.go.jp/drugs/" in href or "pmda.go.jp%2Fdrugs" in href):
                    # Clean DuckDuckGo tracker link
                    if "//duckduckgo.com/l/?uddg=" in href:
                        try:
                            # 쿼리스트링에서 uddg(실제 목적지 URL) 추출 후 unescape 처리
                            parsed = urllib.parse.urlparse(href)
                            qs = urllib.parse.parse_qs(parsed.query)
                            if "uddg" in qs:
                                href = urllib.parse.unquote(qs["uddg"][0])
                        except:
                            pass
                    
                    if "pmda.go.jp/drugs/" in href:
                        target_urls.add(href)

                    
        except Exception as e:
            log.error(f"검색 진행 중 오류 발생: {e}")
        finally:
            if driver:
                driver.quit()
        
        if not target_urls:
            log.warning(f"[{drug_name}] 에 대한 CTD (신약승인정보) 페이지를 찾을 수 없습니다.")
            return
            
        base_folder = self.output_dir / self.sanitize_dirname(drug_name) / "CTD"
        base_folder.mkdir(parents=True, exist_ok=True)
        
        log.info(f"✅ {len(target_urls)} 개의 승인 정보 문서 후보 페이지 발견. 내부 분석 시작...")
        
        download_count = 0
        for page_url in target_urls:
            log.info(f"방문 중: {page_url}")
            try:
                # 만약 검색 결과 자체가 직접적인 PDF 링크라면 즉시 다운로드 (HTML 파싱 제외)
                if page_url.lower().split("?")[0].endswith(".pdf"):
                    filename = page_url.split("/")[-1]
                    safe_text = self.sanitize_dirname(urllib.parse.unquote(filename).replace(".pdf", ""))
                    module_folder = "CTD_직접링크"
                    if "G100" in safe_text.upper(): module_folder = "CTD_요약"
                    dest_dir = base_folder / module_folder
                    dest = dest_dir / f"{safe_text} (검색직접추출).pdf"
                    
                    if not dest.exists() and self.download_file(page_url, dest):
                        download_count += 1
                        time.sleep(2)
                    continue

                resp = self.session.get(page_url, verify=False, timeout=30)
                soup = BeautifulSoup(resp.content, "html.parser", from_encoding="utf-8")
                
                # 페이지 내의 CTD 관련 링크들 추출
                for a in soup.find_all("a", href=True):
                    text = a.get_text(strip=True)
                    href = a["href"]
                    
                    is_ctd = any(keyword in text for keyword in ["申請資料概要", "CTD", "第1部", "第2部", "第3部", "第4部", "第5部"])
                    if is_ctd and href.lower().endswith(".pdf"):
                        full_url = href if href.startswith("http") else urllib.parse.urljoin(page_url, href)
                        
                        safe_text = self.sanitize_dirname(text)
                        if not safe_text: safe_text = "CTD_Document"
                        
                        # 모듈별 폴더명 생성 (예: 第1部, 第2部 등 파싱)
                        module_folder = "기타_모듈"
                        if "第1部" in text: module_folder = "M1"
                        elif "第2部" in text: module_folder = "M2"
                        elif "第3部" in text: module_folder = "M3"
                        elif "第4部" in text: module_folder = "M4"
                        elif "第5部" in text: module_folder = "M5"
                        elif "申請資料" in text or "CTD" in text: module_folder = "CTD_요약"
                        
                        dest_dir = base_folder / module_folder
                        dest = dest_dir / f"{safe_text}.pdf"
                        
                        # 중복 파일명 방지
                        counter = 1
                        while dest.exists():
                            dest = dest_dir / f"{safe_text}_{counter}.pdf"
                            counter += 1
                            
                        if self.download_file(full_url, dest):
                            download_count += 1
                            time.sleep(2)
            except Exception as e:
                log.warning(f"페이지 분석 오류 ({page_url}): {e}")
                
        log.info(f"🎉 CTD 다운로드 프로세스 완료: 총 {download_count} 건 파싱 완료")

def main():
    parser = argparse.ArgumentParser(description="PMDA CTD (신청자료개요) 다운로더")
    parser.add_argument("--drug", "-d", type=str, required=True, help="의약품명 (예: オプジーボ)")
    args = parser.parse_args()
    
    import urllib3
    urllib3.disable_warnings() # Verify=False 경고 무시
    
    downloader = CTDDownloader()
    downloader.search_and_download_ctd(args.drug)

if __name__ == "__main__":
    main()
