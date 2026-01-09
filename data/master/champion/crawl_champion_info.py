import json
import time
import re
import os
import pandas as pd
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
from bs4 import BeautifulSoup

# ==========================================
# [설정]
# ==========================================
TARGET_URL = "https://lolchess.gg/champions/set16/stats"
OUTPUT_FILE = "lolchess_champion_info.json"

def get_role_from_img(img_tag):
    if not img_tag:
        return "Unknown"
    
    src = img_tag.get('src', '')
    filename = src.split('/')[-1] 
    role = filename.replace('ico-', '').replace('.svg', '')
    role = re.sub(r'(?<=[a-z])(?=[A-Z])', ' ', role)
    return role

def crawl_stats():
    # 1. 브라우저 설정
    chrome_options = Options()
    # chrome_options.add_argument("--headless") 
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--window-size=1920,1080")
    chrome_options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36")

    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=chrome_options)
    
    data_list = []

    try:
        print(f">>> 접속 시도: {TARGET_URL}")
        driver.get(TARGET_URL)

        # 2. 데이터 로딩 대기
        print(">>> 데이터 로딩 대기 중...")
        WebDriverWait(driver, 20).until(
            EC.presence_of_element_located((By.TAG_NAME, "tbody"))
        )
        
        # 3. 스크롤 (전체 데이터 로딩)
        print(">>> 스크롤 진행 중...")
        last_height = driver.execute_script("return document.body.scrollHeight")
        while True:
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(1.5)
            new_height = driver.execute_script("return document.body.scrollHeight")
            if new_height == last_height:
                break
            last_height = new_height

        # 4. HTML 파싱
        print(">>> HTML 파싱 시작...")
        soup = BeautifulSoup(driver.page_source, "html.parser")
        
        rows = soup.select("tbody tr")
        print(f">>> 총 {len(rows)}개의 챔피언 행 발견.")

        for row in rows:
            try:
                # (1) 챔피언 이름
                champ_col = row.find("td", class_=lambda x: x and "champion" in x)
                name = champ_col.get_text(strip=True) if champ_col else "Unknown"

                # (2) 비용 (등급)
                cost_col = row.find("td", class_=lambda x: x and "cost" in x)
                cost = cost_col.get_text(strip=True) if cost_col else "0"

                # (3) 시너지 (수정됨: span 태그 기준으로 분리)
                # HTML 구조: td > div > div > img + span(이름)
                traits_col = row.find("td", class_=lambda x: x and "traits" in x)
                traits = []
                if traits_col:
                    # 모든 span 태그의 텍스트를 가져오면 ["엄호대", "요들"] 형태로 깔끔하게 분리됨
                    spans = traits_col.find_all("span")
                    traits = [span.get_text(strip=True) for span in spans]

                # (4) 역할군
                role_col = row.find("td", class_=lambda x: x and "role" in x)
                role_img = role_col.find("img") if role_col else None
                role = get_role_from_img(role_img)

                # (5) 사거리 (채워진 칸 수)
                range_col = row.find("td", class_=lambda x: x and "attackRange" in x)
                attack_range = 0
                if range_col:
                    filled_blocks = range_col.find_all(class_=lambda x: x and "filled" in x)
                    attack_range = len(filled_blocks)

                # (6) 공속
                as_col = row.find("td", class_=lambda x: x and "attackSpeed" in x)
                attack_speed = as_col.get_text(strip=True) if as_col else "-"

                # (7) 방어력
                armor_col = row.find("td", class_=lambda x: x and "armor" in x)
                armor = armor_col.get_text(strip=True) if armor_col else "-"

                # (8) 마나
                mana_col = row.find("td", class_=lambda x: x and "skillMana" in x)
                mana = mana_col.get_text(strip=True) if mana_col else "-"

                # 데이터 구조
                champion_data = {
                    "champion": name,
                    "cost": int(cost) if cost.isdigit() else cost,
                    "traits": traits,         # ["엄호대", "요들"]
                    "role": role,
                    "attack_range": attack_range, 
                    "attack_speed": attack_speed,
                    "armor": armor,
                    "mana": mana
                }
                
                data_list.append(champion_data)

            except Exception as e:
                # print(f"⚠️ 파싱 에러 (Skipped): {e}")
                continue

        # 5. JSON 저장
        with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
            json.dump(data_list, f, indent=4, ensure_ascii=False)

        print(f"\n✅ [성공] 총 {len(data_list)}개의 데이터가 '{OUTPUT_FILE}'로 저장되었습니다.")
        
        # 샘플 출력
        if data_list:
            print("\n[Sample Data]")
            print(json.dumps(data_list[0], indent=4, ensure_ascii=False))

    except Exception as e:
        print(f"❌ 크롤링 실패: {e}")
    finally:
        driver.quit()

if __name__ == "__main__":
    crawl_stats()