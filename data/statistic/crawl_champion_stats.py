import json
import time
import os
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
TARGET_URL = "https://www.metatft.com/units"
OUTPUT_FILE = "data/metatft_units_stats.json"

def clean_text(text):
    if not text: return ""
    return text.strip().replace("\n", "").replace("%", "")

def crawl_units():
    # 1. 브라우저 설정 (Headless로 속도 향상)
    chrome_options = Options()
    chrome_options.add_argument("--headless") 
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--window-size=1920,1080")
    chrome_options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36")

    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=chrome_options)
    
    data_list = []

    try:
        print(f">>> 접속 시도: {TARGET_URL}")
        driver.get(TARGET_URL)

        # 2. 로딩 대기
        print(">>> 테이블 로딩 대기...")
        try:
            WebDriverWait(driver, 15).until(
                EC.presence_of_element_located((By.TAG_NAME, "tbody"))
            )
        except:
            print("⚠️ 로딩이 지연되었으나 진행합니다.")

        # 3. [빠른 스크롤] 전체 높이를 4등분해서 빠르게 훑기 (이미지 로딩 트리거)
        print(">>> 데이터 로딩을 위해 빠르게 스크롤합니다...")
        total_height = driver.execute_script("return document.body.scrollHeight")
        
        # 0.5초 간격으로 4번만 탁탁탁 내리고 끝냄 (총 2초 소요)
        for i in range(1, 5):
            driver.execute_script(f"window.scrollTo(0, {total_height * i / 4});")
            time.sleep(0.5) 

        # 4. HTML 파싱
        print(">>> HTML 파싱 및 데이터 추출...")
        soup = BeautifulSoup(driver.page_source, "html.parser")
        
        # 테이블 행 가져오기 (헤더 제외)
        rows = soup.select("tbody[role='rowgroup'] tr[role='row']")
        
        print(f">>> 총 {len(rows)}개의 유닛 데이터 발견.")

        for row in rows:
            try:
                cells = row.find_all("td", role="cell")
                if len(cells) < 6: continue

                # (1) 유닛 이름
                name_cell = cells[0].select_one(".TableItemRow a.StatLink")
                # 텍스트가 안 보이면 안쪽 div 텍스트라도 가져오기
                if name_cell:
                    unit_name = clean_text(name_cell.get_text())
                    # 이름에 "Unlockable Unit" 같은 불필요한 접두사가 붙는 경우 제거
                    unit_name = unit_name.replace("Unlockable Unit", "").strip()
                else:
                    unit_name = "Unknown"

                # (2) 티어
                tier_badge = cells[1].select_one(".StatTierBadge")
                tier = clean_text(tier_badge.get_text()) if tier_badge else "-"

                # (3) 평균 등수
                avg_place_div = cells[2].select_one(".TablePlacement")
                avg_place = clean_text(avg_place_div.get_text()) if avg_place_div else "-"

                # (4) 승률
                win_rate_div = cells[3].select_one(".TableNum")
                win_rate = clean_text(win_rate_div.get_text()) if win_rate_div else "-"

                # (5) 인기 아이템
                popular_items = []
                items_div = cells[5].select(".AugmentStatTopUnit") # 아이템 이미지 클래스
                for img in items_div:
                    alt_text = img.get("alt")
                    if alt_text:
                        popular_items.append(alt_text)

                # 데이터 구조화
                unit_data = {
                    "name": unit_name,
                    "tier": tier,
                    "avg_place": avg_place,
                    "win_rate": f"{win_rate}%" if win_rate != "-" else "-",
                    "popular_items": popular_items
                }
                
                data_list.append(unit_data)

            except Exception:
                continue

        # 5. 저장
        if not os.path.exists("data"):
            os.makedirs("data")

        with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
            json.dump(data_list, f, indent=4, ensure_ascii=False)

        print(f"\n✅ [완료] {len(data_list)}개 유닛 데이터 저장됨: {OUTPUT_FILE}")
        
        # 샘플 확인
        if data_list:
            print("\n[Sample]")
            print(json.dumps(data_list[0], indent=4, ensure_ascii=False))

    except Exception as e:
        print(f"❌ 오류: {e}")
    finally:
        driver.quit()

if __name__ == "__main__":
    crawl_units()