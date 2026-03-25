#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PMDA 문서 자동 다운로더
약품명을 입력하면 PMDA 사이트에서 관련 문서를 자동으로 다운로드합니다.

필요 라이브러리 설치:
    pip install requests beautifulsoup4 selenium webdriver-manager tqdm

사용법:
    python pmda_downloader.py
    또는
    python pmda_downloader.py --drug "薬品名"
"""

import os
import re
import sys
import time
import argparse
import logging
import urllib.parse
from pathlib import Path
from typing import Optional

import requests
from bs4 import BeautifulSoup
from tqdm import tqdm

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager

# ─────────────────────────────────────────────
# 로거 설정
# ─────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
log = logging.getLogger(__name__)

# ─────────────────────────────────────────────
# 상수 / URL
# ─────────────────────────────────────────────
PMDA_BASE       = "https://www.pmda.go.jp"
PMDA_SEARCH     = "https://www.pmda.go.jp/PmdaSearch/iyakuSearch/"
PMDA_SEARCH_API = "https://www.pmda.go.jp/rs-search/pharma"
KUSURINOSHIORI  = "https://www.kusurinoshiori.or.jp"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "ja,en;q=0.9",
}

# フォルダ名マッピング
FOLDER_MAP = {
    "添付文書": "添付文書",
    "ガイド": "患者向医薬品ガイド／ワクチン接種を受ける人へのガイド",
    "IF": "インタビューフォーム",
    "RMP": "医薬品リスク管理計画（RMP）",
    "RMP資材": "RMP資材",
    "改訂指示": "改訂指示反映履歴および根拠症例",
    "審査報告書": "審査報告書／再審査報告書／最適使用推進ガイドライン等",
    "重篤副作用": "重篤副作用疾患別対応マニュアル",
    "しおり": "くすりのしおり",
    "安全性情報": "緊急安全性情報／安全性速報",
    "適正使用": "医薬品の適正使用等に関するお知らせ",
    "厚労省発表": "厚生労働省発表資料（医薬品関連）",
    "評価中リスク": "医薬品に関する評価中のリスク等の情報",
    "改訂相談": "医薬品添付文書改訂相談に基づく添付文書改訂",
    "DSU": "DSU（医薬品安全対策情報）",
    "PMDA安全情報": "PMDA医療安全情報",
    "問合せ先": "医療用医薬品問合せ先",
    "CTD": "申請資料概要",
    "その他": "その他", # 分類不可の場合
}

# ─────────────────────────────────────────────
# ユーティリティ
# ─────────────────────────────────────────────

def sanitize_dirname(name: str) -> str:
    """ディレクトリ名として使えない文字を除去"""
    # 전각 슬래시(／) 등도 디렉토리 생성시 문제가 될 수 있으므로 언더스코어로 변경
    return re.sub(r'[\\/:*?"<>|／]', "_", name).strip()


def make_session() -> requests.Session:
    s = requests.Session()
    s.headers.update(HEADERS)
    return s


def download_file(session: requests.Session, url: str, dest: Path, max_retries: int = 3) -> bool:
    """URLからファイルをダウンロードしてdestに保存 (リトライ機能付き)"""
    for attempt in range(max_retries):
        try:
            resp = session.get(url, stream=True, timeout=60)
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
            if attempt < max_retries - 1:
                log.warning(f"  ⚠ 다운로드 오류 [{url}] (재시도 {attempt+1}/{max_retries}): {e}")
                time.sleep(3)  # 再試行前に少し待機
            else:
                log.warning(f"  ✘ 다운로드 최종 실패 [{url}]: {e}")
                return False
    return False


def ensure_dirs(base: Path, subfolders: list) -> dict:
    """기본 폴더 + 서브폴더 생성 후 경로 dict 반환"""
    paths = {}
    for name in subfolders:
        p = base / name
        p.mkdir(parents=True, exist_ok=True)
        paths[name] = p
    return paths


# ─────────────────────────────────────────────
# PMDA 検索
# ─────────────────────────────────────────────

class PMDAClient:
    def __init__(self):
        self.session = make_session()

    # ── 1. 医薬品検索 ──────────────────────────
    def search_drug(self, drug_name: str) -> list[dict]:
        log.info(f"[PMDA] '{drug_name}' を検索中...(Selenium起動)")
        results = []

        chrome_options = Options()
        chrome_options.add_argument("--headless")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
        
        driver = None
        try:
            driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=chrome_options)
            driver.get(PMDA_SEARCH)
            
            input_field = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.NAME, "nameWord"))
            )
            input_field.send_keys(drug_name)
            
            # 「全チェック」ボタンをクリックして全文書のフラグを立てる
            try:
                all_check_btn = driver.find_element(By.NAME, "allCheck")
                all_check_btn.click()
                time.sleep(0.5)
            except Exception as e:
                log.warning(f"  「全チェック」ボタンのクリックに失敗しました: {e}")
            
            search_btn = driver.find_element(By.NAME, "btnA")
            search_btn.click()
            
            # 検索結果のロード待機
            time.sleep(3)
            
            # 別タブで開く場合があるため、タブ切り替え
            if len(driver.window_handles) > 1:
                driver.switch_to.window(driver.window_handles[-1])
            
            # 結果のリンクを抽出
            soup = BeautifulSoup(driver.page_source, "html.parser")
            seen = set()
            for a in soup.find_all("a", href=True):
                href = a["href"]
                text = a.get_text(strip=True)
                
                # 詳細ページ(GeneralList)へのリンクを取得
                if "/iyakuDetail/GeneralList/" in href:
                    full_url = href if href.startswith("http") else PMDA_BASE + href
                    if full_url not in seen:
                        seen.add(full_url)
                        results.append({"name": text or drug_name, "url": full_url})
                        
        except Exception as e:
            log.warning(f"  検索エラー: {e}")
        finally:
            if driver:
                driver.quit()

        log.info(f"  → {len(results)} 件の医薬品詳細ページを見つけました")
        return results

    def get_drug_page(self, drug_url: str) -> Optional[BeautifulSoup]:
        try:
            resp = self.session.get(drug_url, timeout=30)
            return BeautifulSoup(resp.text, "html.parser")
        except:
            return None

    def get_documents_from_page(self, soup: BeautifulSoup) -> dict[str, list[dict]]:
        log.info("[Scrape] 各ドキュメントを抽出中...")
        # 重複制御のために一意なカテゴリをリスト化
        unique_folders = list(set(FOLDER_MAP.values()))
        results = {folder: [] for folder in unique_folders}
        
        for a in soup.find_all("a", href=True):
            href = a["href"].strip()
            text = a.get_text(strip=True)
            
            # --- DSU 파일 뷰어 링크를 실제 PDF 링크로 변환 ---
            if "viewer.html?file=" in href:
                parsed_url = urllib.parse.urlparse(href)
                query_params = urllib.parse.parse_qs(parsed_url.query)
                if "file" in query_params:
                    filepath = query_params["file"][0]
                    # Base URL (ex: https://dsu-system.jp) 에 filepath 병합
                    base_url = f"{parsed_url.scheme}://{parsed_url.netloc}" if parsed_url.netloc else PMDA_BASE
                    if "dsu-system.jp" in href:
                        base_url = "https://dsu-system.jp"
                    href = urllib.parse.urljoin(base_url, filepath)

            if not href or ".pdf" not in href.lower():
                continue

            full_url = href if href.startswith("http") else PMDA_BASE + href
            doc = {"url": full_url, "name": text or "Untitled Document"}
            
            text_upper = text.upper()
            if "添付" in text and "相談" not in text:
                results["添付文書"].append(doc)
            elif "患者" in text or "ワクチン" in text:
                results["患者向医薬品ガイド／ワクチン接種を受ける人へのガイド"].append(doc)
            elif "IF" in text_upper or "インタビュー" in text or "interview" in href.lower():
                results["インタビューフォーム"].append(doc)
            elif "資材" in text and "RMP" in text_upper:
                results["RMP資材"].append(doc)
            elif "RMP" in text_upper or "リスク管理計画" in text:
                results["医薬品リスク管理計画（RMP）"].append(doc)
            elif "履歴" in text or "根拠症例" in text:
                results["改訂指示反映履歴および根拠症例"].append(doc)
            elif "申請資料概要" in text or "CTD" in text_upper:
                results["申請資料概要"].append(doc)
            elif "審査" in text or "最適使用" in text or "review" in href.lower():
                results["審査報告書／再審査報告書／最適使用推進ガイドライン等"].append(doc)
            elif "重篤" in text or "疾患" in text:
                results["重篤副作用疾患別対応マニュアル"].append(doc)
            elif "しおり" in text:
                results["くすりのしおり"].append(doc)
            elif "緊急" in text or "速報" in text:
                results["緊急安全性情報／安全性速報"].append(doc)
            elif "適正使用" in text and "お知らせ" in text:
                results["医薬品の適正使用等に関するお知らせ"].append(doc)
            elif "厚生" in text or "発表資料" in text:
                results["厚生労働省発表資料（医薬品関連）"].append(doc)
            elif "評価中" in text or "リスク等の情報" in text:
                results["医薬品に関する評価中のリスク等の情報"].append(doc)
            elif "改訂相談" in text:
                results["医薬品添付文書改訂相談に基づく添付文書改訂"].append(doc)
            elif "DSU" in text_upper:
                results["DSU（医薬品安全対策情報）"].append(doc)
            elif "PMDA医療安全" in text:
                results["PMDA医療安全情報"].append(doc)
            elif "問合" in text:
                results["医療用医薬品問合せ先"].append(doc)
            else:
                results["その他"].append(doc)
        
        for cat, docs in results.items():
            if docs: log.info(f"  → {cat}: {len(docs)} 件発見")
        return results

    # Legacy fetchers (Fallback)
    def get_package_inserts(self, drug_name: str) -> list[dict]:
        return [] # Placeholder

    def get_interview_forms(self, drug_name: str) -> list[dict]: return []
    def get_rmp(self, drug_name: str) -> list[dict]: return []
    def get_review_reports(self, drug_name: str) -> list[dict]: return []
    def get_ctd(self, drug_name: str) -> list[dict]: return []
    def get_kusurinoshiori(self, drug_name: str) -> list[dict]: return []
    def get_product_info(self, drug_name: str) -> list[dict]: return []


class PMDADownloader:
    SUBFOLDERS = list(set(FOLDER_MAP.values()))

    def __init__(self, output_dir: str = "."):
        self.output_dir = Path(output_dir)
        self.client = PMDAClient()

    def run(self, drug_name: str, drug_url: Optional[str] = None):
        search_target = drug_name.split('／')[0].split(' ')[0].strip()
        log.info(f"\n薬品名: {drug_name}")
        log.info(f"詳細URL: {drug_url}")

        # 약품명으로 폴더 만들 때 디렉토리 생성에 안전하도록 변환
        safe_drug_name = sanitize_dirname(drug_name)
        base = self.output_dir / safe_drug_name
        
        # 내부 하위 폴더: 사용자가 요청한 이름이 디렉토리 이름이 됨.
        # 단, 슬래시(／이나 /)가 포함되어 있으면 폴더 경로 뎁스가 깊어지므로
        # `sanitize_dirname` 처리가 된 버전으로 폴더를 생성하도록 함
        dirs = {}
        for folder_name in self.SUBFOLDERS:
            safe_folder_name = sanitize_dirname(folder_name)
            p = base / safe_folder_name
            p.mkdir(parents=True, exist_ok=True)
            dirs[folder_name] = p
        
        if drug_url:
            soup = self.client.get_drug_page(drug_url)
            if soup:
                all_docs = self.client.get_documents_from_page(soup)
                total_ok = 0
                for cat, items in all_docs.items():
                    if not items: continue
                    log.info(f"\n── {cat} ダウン로드 중 ({len(items)}건) ──")
                    for item in items:
                        url = item["url"]
                        raw_name = sanitize_dirname(item["name"])
                        
                        ext = Path(urllib.parse.urlparse(url).path).suffix or ".pdf"
                        if raw_name.endswith(ext):
                            raw_name = raw_name[:-len(ext)]
                            
                        dest = dirs[cat] / (raw_name + ext)
                        counter = 1
                        while dest.exists():
                            dest = dirs[cat] / f"{raw_name}_{counter}{ext}"
                            counter += 1
                            
                        if download_file(self.client.session, url, dest):
                            total_ok += 1
                        time.sleep(2)  # 다운로드 사이에 2초 대기
                log.info(f"\n완료! {total_ok}건 성공")
            else:
                log.warning("詳細ページの取得に失敗しました。")
        else:
            log.warning("詳細URLが見つかりません。")

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--drug", "-d", type=str)
    parser.add_argument("--output", "-o", type=str, default=".")
    args = parser.parse_args()

    drug_name = args.drug or input("薬品名: ").strip()
    client = PMDAClient()
    candidates = client.search_drug(drug_name)

    if candidates:
        selected = candidates[0]
        if len(candidates) > 1:
            print("\n候補:")
            for i, c in enumerate(candidates[:10], 1):
                print(f"  {i}. {c['name']}")
            try:
                idx = int(input("選択 (1): ") or 1)
                selected = candidates[idx-1]
            except: pass
        
        downloader = PMDADownloader(output_dir=args.output)
        downloader.run(selected["name"], selected["url"])
    else:
        print("ヒットなし。")

if __name__ == "__main__":
    main()