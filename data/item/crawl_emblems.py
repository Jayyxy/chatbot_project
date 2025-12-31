import json
import time
import os
import re
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
TARGET_URL = "https://lolchess.gg/items/set16?type=trait"
OUTPUT_FILE = "data/item/lolchess_emblems.json"

# 이미지 파일명 내 영문 키워드를 한글 컴포넌트 이름으로 매핑
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
    "FryingPan": "프라이팬" 
}

def get_component_name_from_src(src_url):
    """
    이미지 URL에서 아이템 이름을 추출하여 한글로 변환
    예: ".../GiantsBelt_1658368751.png" -> "GiantsBelt" -> "거인의 허리띠"
    """
    if not src_url: return None
    
    # URL에서 파일명 부분만 추출하여 매핑 테이블과 대조
    for key, kr_name in COMPONENT_MAP.items():
        # 대소문자 구분 없이 포함 여부 확인
        if key.lower() in src_url.lower():
            return kr_name
            
    return "알 수 없음"

def crawl_emblems():
    chrome_options = Options()
    # 봇 탐지 회피 설정
    chrome_options.add_argument("--disable-blink-features=AutomationControlled")
    chrome_options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
    chrome_options.add_argument("--window-size=1920,1080")
    # chrome_options.add_argument("--headless") # 디버깅 시에는 주석 처리

    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=chrome_options)
    
    emblem_data = []

    try:
        print(f">>> 롤체지지 접속: {TARGET_URL}")
        driver.get(TARGET_URL)

        # 데이터가 로드될 때까지 대기 (특정 클래스가 보일 때까지)
        # 제공해주신 html의 class="css-1mig4xf" 등을 기다립니다.
        try:
            WebDriverWait(driver, 15).until(
                EC.presence_of_element_located((By.CLASS_NAME, "compositions"))
            )
            time.sleep(2) # 렌더링 안정화 대기
        except:
            print(">>> 로딩 시간 초과 또는 데이터 없음")

        # HTML 파싱
        soup = BeautifulSoup(driver.page_source, "html.parser")
        
        # 제공해주신 HTML 구조에 맞는 아이템 컨테이너 찾기
        # class 이름이 동적일 수 있으므로 포함된 구조로 찾습니다.
        # "div > div.content > span" 구조를 가진 모든 블록 탐색
        items_containers = soup.select("div.css-1mig4xf") # 사용자가 제공한 클래스
        
        if not items_containers:
            # 클래스명이 바뀌었을 경우를 대비한 범용 선택자
            print(">>> [정보] 제공된 클래스로 찾지 못해 범용 선택자로 다시 시도합니다.")
            items_containers = soup.select("div[class*='css-']")

        print(f">>> 발견된 아이템 개수: {len(items_containers)}")

        for container in items_containers:
            try:
                # 1. 상징 이름 추출
                name_el = container.select_one(".content span")
                if not name_el: continue
                name = name_el.get_text(strip=True)

                # 2. 조합법(Recipe) 추출
                recipe = []
                # .compositions 클래스 내부의 이미지 찾기
                composition_div = container.select_one(".compositions")
                
                if composition_div:
                    imgs = composition_div.select("img")
                    for img in imgs:
                        src = img.get("src", "")
                        comp_name = get_component_name_from_src(src)
                        if comp_name:
                            recipe.append(comp_name)
                
                # 조합법이 없는 경우 (조합 불가 상징)
                if not recipe:
                    recipe_str = "조합 불가"
                else:
                    recipe_str = " + ".join(recipe)

                # 데이터 저장
                print(f"   - {name}: {recipe_str}")
                emblem_data.append({
                    "name": name,
                    "recipe": recipe,
                    "recipe_str": recipe_str
                })

            except Exception as e:
                print(f"⚠️ 파싱 에러: {e}")
                continue

        # 파일 저장
        if not os.path.exists("data"): os.makedirs("data")
        with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
            json.dump(emblem_data, f, indent=4, ensure_ascii=False)
            
        print(f"\n✅ 크롤링 완료! 저장 경로: {OUTPUT_FILE}")

    except Exception as e:
        print(f"❌ 오류 발생: {e}")
    finally:
        driver.quit()

if __name__ == "__main__":
    crawl_emblems()