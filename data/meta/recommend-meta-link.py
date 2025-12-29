import time
import json
import os
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
from bs4 import BeautifulSoup

# 저장할 파일 경로 (JSON으로 변경됨)
OUTPUT_FILE = "data/lolchess_meta_list.json"

def fetch_meta_data():
    # 1. 브라우저 설정
    chrome_options = Options()
    # chrome_options.add_argument("--headless") # 디버깅을 위해 주석 처리 (실제 돌릴 땐 주석 해제 추천)
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/90.0.4430.212 Safari/537.36")

    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=chrome_options)
    
    deck_data_list = []

    try:
        url = "https://lolchess.gg/meta"
        print(f">>> [1단계] 메타 페이지 접속 중: {url}")
        driver.get(url)

        # 2. 로딩 대기 (메인 컨텐츠가 뜰 때까지)
        try:
            WebDriverWait(driver, 15).until(
                EC.presence_of_element_located((By.TAG_NAME, "main"))
            )
        except:
            print("Warning: 로딩이 느리거나 페이지 구조가 변경되었습니다.")

        # 스크롤을 끝까지 내려서 모든 덱 로딩 (Lazy Loading 대응)
        last_height = driver.execute_script("return document.body.scrollHeight")
        while True:
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(2)
            new_height = driver.execute_script("return document.body.scrollHeight")
            if new_height == last_height:
                break
            last_height = new_height
        
        time.sleep(1) # 최종 렌더링 대기

        # 3. HTML 파싱
        soup = BeautifulSoup(driver.page_source, "html.parser")
        
        # 덱 카드 리스트 찾기 (이전 분석 기반 클래스)
        # 만약 클래스명이 바뀌었다면 soup.find_all("div", class_="deck-card") 형태나 구조적 탐색 필요
        cards = soup.find_all("div", class_="css-3q0xzn") 
        
        if not cards:
            print("❌ 덱 카드를 찾지 못했습니다. HTML 클래스명을 확인해주세요.")
            return

        print(f">>> 총 {len(cards)}개의 추천 덱을 발견했습니다. 데이터 추출 시작...")

        for card in cards:
            # A. 덱 이름
            name_div = card.select_one(".css-1fu47ws > div")
            deck_name = name_div.get_text(strip=True) if name_div else "Unknown Deck"

            # B. HOT 태그 여부
            hot_tag = card.select_one(".tag.hot")
            is_hot = True if hot_tag else False

            # C. 최소 골드 (오른쪽 상단 코인)
            gold_span = card.select_one(".credit span")
            min_gold = gold_span.get_text(strip=True) if gold_span else "0"

            # D. 공략 상세 URL
            link_tag = card.select_one("a[href*='/builder/guide']")
            if link_tag:
                full_url = f"https://lolchess.gg{link_tag['href']}" if link_tag['href'].startswith("/") else link_tag['href']
            else:
                full_url = None

            if full_url:
                deck_info = {
                    "name": deck_name,
                    "is_hot": is_hot,
                    "min_gold": min_gold,
                    "url": full_url
                }
                deck_data_list.append(deck_info)

        # 4. 파일 저장 (JSON)
        if not os.path.exists("data"):
            os.makedirs("data")

        with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
            json.dump(deck_data_list, f, indent=4, ensure_ascii=False)

        print(f"\n✅ [성공] 메타 데이터 수집 완료!")
        print(f"📄 저장된 파일: {OUTPUT_FILE} (총 {len(deck_data_list)}개)")
        
        # 미리보기 출력
        if deck_data_list:
            print(f"🔍 첫 번째 데이터 예시: {deck_data_list[0]}")

    except Exception as e:
        print(f"❌ 에러 발생: {e}")
    finally:
        driver.quit()

if __name__ == "__main__":
    fetch_meta_data()