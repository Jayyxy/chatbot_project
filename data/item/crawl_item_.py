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
TARGET_URL = "https://lolchess.gg/items/set16/guide?type=normal"
OUTPUT_FILE = "lolchess_items.json"

# 이미지 파일명 -> 한글 아이템 이름 매핑 사전
COMPONENT_MAP = {
    "BFSword": "B.F. 대검",
    "RecurveBow": "곡궁",
    "NeedlesslyLargeRod": "쓸데없이 큰 지팡이",
    "TearoftheGoddess": "여신의 눈물",
    "ChainVest": "쇠사슬 조끼",
    "NegatronCloak": "음전자 망토",
    "GiantsBelt": "거인의 허리띠",
    "Spatula": "뒤집개",
    "SparringGloves": "연습용 장갑",
    "FryingPan": "프라이팬" # 최신 시즌 추가 아이템 대응
}

def get_recipe_name_from_src(src):
    """
    이미지 URL에서 파일명을 추출하여 한글 아이템 이름으로 변환
    예: .../BFSword_1658364277.png -> BFSword -> B.F. 대검
    """
    if not src: return "Unknown"
    
    try:
        # URL에서 파일명 추출 (BFSword_xxxxx.png)
        filename = src.split('/')[-1]
        
        # 언더바(_) 또는 하이픈(-) 기준으로 앞부분(영문이름)만 추출
        key = filename.split('_')[0].split('-')[0]
        
        # 매핑된 한글 이름 반환 (없으면 영문 그대로 반환)
        return COMPONENT_MAP.get(key, key)
    except:
        return "Unknown"

def crawl_items():
    chrome_options = Options()
    chrome_options.add_argument("--headless") 
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36")

    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=chrome_options)
    
    item_list = []

    try:
        print(f">>> 접속 시도: {TARGET_URL}")
        driver.get(TARGET_URL)

        print(">>> 데이터 로딩 대기 중...")
        try:
            WebDriverWait(driver, 15).until(
                EC.presence_of_element_located((By.TAG_NAME, "tbody"))
            )
        except:
            print("⚠️ 테이블 로딩 지연")

        print(">>> HTML 파싱 시작...")
        soup = BeautifulSoup(driver.page_source, "html.parser")
        
        rows = soup.select("tbody tr")
        print(f">>> 총 {len(rows)}개의 아이템 발견.")

        for row in rows:
            try:
                cols = row.find_all("td")
                if len(cols) < 2: continue

                # --- 1. 아이템 이름 ---
                col_1 = cols[0]
                # 이름이 있는 div 찾기 (css 클래스 의존도 낮춤)
                # 보통 img(36px) 옆이나 아래에 텍스트가 있음
                name_div = col_1.find("div", class_=lambda x: x and "css-1vrsxza" in x)
                
                # 백업 로직: 텍스트가 있는 div 순회
                if not name_div:
                    for div in col_1.find_all("div"):
                        if div.get_text(strip=True) and not div.find("img"):
                            name_div = div
                            break
                            
                item_name = name_div.get_text(strip=True) if name_div else "Unknown"

                # --- 2. 아이템 조합 (한글 이름 추출) ---
                # width="16"인 작은 이미지들이 재료 아이템임
                recipe_imgs = col_1.find_all("img", width="16")
                recipe_names = []
                
                for img in recipe_imgs:
                    src = img.get("src")
                    korean_name = get_recipe_name_from_src(src)
                    recipe_names.append(korean_name)

                # --- 3. 효과 ---
                col_2 = cols[1]
                effect = col_2.get_text(strip=True)

                # 저장할 데이터
                item_data = {
                    "name": item_name,
                    "recipe": recipe_names, # ["B.F. 대검", "B.F. 대검"]
                    "effect": effect
                }
                item_list.append(item_data)

            except Exception as e:
                # print(f"⚠️ 파싱 에러: {e}")
                continue

        # JSON 저장
        with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
            json.dump(item_list, f, indent=4, ensure_ascii=False)

        print(f"\n✅ [성공] 아이템 데이터 저장 완료: {OUTPUT_FILE}")
        
        if item_list:
            print("\n[Sample Data]")
            print(json.dumps(item_list[0], indent=4, ensure_ascii=False))

    except Exception as e:
        print(f"❌ 오류: {e}")
    finally:
        driver.quit()

if __name__ == "__main__":
    crawl_items()