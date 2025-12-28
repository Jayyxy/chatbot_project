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
TARGET_URL = "https://www.metatft.com/comps"
OUTPUT_FILE = "data/metatft_comps.json"

def crawl_metatft():
    # 1. 브라우저 옵션 강화 (안전장치 추가)
    chrome_options = Options()
    
    # [중요 1] 페이지 로딩 전략 변경 ('eager': DOM만 로딩되면 바로 진행. 이미지/광고 로딩 안 기다림)
    chrome_options.page_load_strategy = 'eager' 
    
    # [중요 2] 봇 탐지 회피 및 안정성 옵션
    chrome_options.add_argument("--headless") # 화면 없이 실행 (디버깅 시 주석 처리)
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--window-size=1920,1080") # 화면 크기 고정 (반응형 로딩 방지)
    chrome_options.add_argument("--disable-blink-features=AutomationControlled") # 자동화 탐지 방지
    chrome_options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36")

    print(">>> 드라이버 초기화 중...")
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=chrome_options)
    
    # [중요 3] 타임아웃 시간 넉넉하게 설정 (기본 30초 -> 120초)
    driver.set_page_load_timeout(120)
    driver.set_script_timeout(120)
    
    deck_list = []

    try:
        print(f">>> MetaTFT 접속 시도 (Eager Mode): {TARGET_URL}")
        try:
            driver.get(TARGET_URL)
        except Exception:
            # Eager 모드에서는 로딩 중에도 제어권이 넘어오므로 타임아웃 나도 무시하고 진행
            print("...페이지 로딩 시간이 길어지지만 계속 진행합니다.")

        # 2. 핵심 컨텐츠 로딩 대기 (최대 30초)
        print(">>> 데이터 렌더링 대기 중...")
        try:
            WebDriverWait(driver, 30).until(
                EC.presence_of_element_located((By.CLASS_NAME, "CompRow"))
            )
        except:
            print("⚠️ 경고: CompRow를 찾지 못했습니다. 스크롤을 시도합니다.")

        # 스크롤 다운 (데이터 로딩 유도)
        print(">>> 스크롤 다운 수행...")
        for _ in range(3):
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(2)

        # 3. HTML 파싱
        print(">>> HTML 파싱 시작...")
        soup = BeautifulSoup(driver.page_source, "html.parser")
        
        # MetaTFT의 각 덱 행(Row) 찾기
        rows = soup.find_all("div", class_=lambda x: x and "CompRow" in x)
        
        print(f">>> 총 {len(rows)}개의 덱을 발견했습니다.")

        for idx, row in enumerate(rows):
            try:
                # --- A. 덱 티어 & 태그 ---
                tier_badge = row.find("div", class_=lambda x: x and "Tier" in x)
                tier = tier_badge.get_text(strip=True) if tier_badge else "Unknown"

                tags = []
                tag_elements = row.find_all("div", class_=lambda x: x and "Tag" in x)
                for tag in tag_elements:
                    tags.append(tag.get_text(strip=True))

                # --- B. 챔피언 목록 & 별 개수 & 아이템 ---
                units_container = row.find("div", class_=lambda x: x and "UnitList" in x)
                champion_list = []
                
                if units_container:
                    # 챔피언 슬롯 찾기 (구조 유연하게 검색)
                    # UnitWrapper 또는 단순 img 태그 기반 검색
                    unit_slots = units_container.find_all("div", class_=lambda x: x and "Unit" in x and "Wrapper" in x)
                    if not unit_slots:
                        imgs = units_container.find_all("img", class_=lambda x: x and "Champion" in x)
                        unit_slots = [img.parent for img in imgs]

                    for slot in unit_slots:
                        # 1. 챔피언 이름
                        champ_img = slot.find("img")
                        if not champ_img: continue
                        
                        champ_name = champ_img.get('alt', 'Unknown')
                        if not champ_name:
                            src = champ_img.get('src', '')
                            # URL에서 이름 추출 (예: /TFT10_Ahri.png)
                            champ_name = src.split('/')[-1].split('.')[0].replace("%20", " ").split("_")[-1]

                        # 2. 별 레벨
                        is_3_star = False
                        if slot.find(class_=lambda x: x and "Star" in x) or slot.find("img", src=lambda x: x and "star" in x):
                            is_3_star = True
                        star_level = 3 if is_3_star else 2 

                        # 3. 착용 아이템
                        items = []
                        item_imgs = slot.find_all("img", class_=lambda x: x and "Item" in x)
                        for item_img in item_imgs:
                            item_name = item_img.get('alt') or item_img.get('title')
                            if item_name:
                                items.append(item_name)

                        champion_list.append({
                            "name": champ_name,
                            "star": star_level,
                            "items": items
                        })

                # 데이터 저장 구조
                deck_info = {
                    "tier": tier,
                    "tags": tags,
                    "champions": champion_list
                }
                deck_list.append(deck_info)
                
            except Exception as e:
                # 개별 덱 파싱 에러는 무시하고 진행
                continue

        # 4. JSON 파일 저장
        if not os.path.exists("data"):
            os.makedirs("data")

        with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
            json.dump(deck_list, f, indent=4, ensure_ascii=False)

        print(f"\n✅ [MetaTFT] 크롤링 완료!")
        print(f"📄 저장 경로: {OUTPUT_FILE} (수집된 덱: {len(deck_list)}개)")

    except Exception as e:
        print(f"❌ 전체 프로세스 에러: {e}")
    finally:
        driver.quit()

if __name__ == "__main__":
    crawl_metatft()