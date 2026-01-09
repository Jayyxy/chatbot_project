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

TARGET_URL = "https://lolchess.gg/items/set16/guide?type=artifact"
OUTPUT_FILE = "data/master/item/lolchess_artifacts.json"

def clean_text(text):
    if not text: return ""
    return text.strip().replace("\n", " ").replace("\r", "")

def crawl_artifacts_fixed():
    # 1. 프로세스 정리 (맥/윈도우)
    try:
        if os.name == 'nt':
            os.system("taskkill /f /im chrome.exe")
            os.system("taskkill /f /im chromedriver.exe")
        else:
            os.system("pkill -9 'Google Chrome'")
            os.system("pkill -9 'chromedriver'")
    except:
        pass

    # 2. 브라우저 설정 (빠른 로딩)
    options = Options()
    options.page_load_strategy = 'eager'
    options.add_argument("--window-size=1920,1080")
    options.add_argument("user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
    options.add_argument("--disable-blink-features=AutomationControlled")
    
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
    
    data_list = []

    try:
        print(f">>> [접속] {TARGET_URL}")
        driver.get(TARGET_URL)

        print(">>> 요소 로딩 대기 중...")
        try:
            # 이름 클래스(e14r4a8l6)가 뜰 때까지 대기
            WebDriverWait(driver, 15).until(
                EC.presence_of_element_located((By.CLASS_NAME, "e14r4a8l6"))
            )
            # 효과 클래스(e14r4a8l5)도 뜨는지 확인 (잠깐 대기)
            WebDriverWait(driver, 5).until(
                EC.presence_of_element_located((By.CLASS_NAME, "e14r4a8l5"))
            )
            driver.execute_script("window.stop();") # 로딩 중단
            print(">>> 핵심 요소 발견! 파싱 시작.")
        except:
            print("⚠️ 타임아웃: 로딩된 부분까지만 파싱 시도")

        time.sleep(1)

        # 3. HTML 파싱 (지적해주신 클래스 적용)
        soup = BeautifulSoup(driver.page_source, "html.parser")
        
        # 이름 요소들
        name_elements = soup.select(".e14r4a8l6")
        # 효과 요소들 (지적해주신 클래스)
        effect_elements = soup.select(".e14r4a8l5")
        
        print(f">>> 발견된 이름 개수: {len(name_elements)}")
        print(f">>> 발견된 효과 개수: {len(effect_elements)}")

        # 개수가 맞다면 순서대로 매핑 (zip 사용)
        for name_el, effect_el in zip(name_elements, effect_elements):
            try:
                name = clean_text(name_el.get_text())
                effect = clean_text(effect_el.get_text())

                if name:
                    data_list.append({
                        "name": name,
                        "effect": effect,
                        "type": "artifact"
                    })
            except Exception as e:
                print(f"   ⚠️ 파싱 에러: {e}")
                continue

        # 4. 저장
        if not os.path.exists("data/item"):
            os.makedirs("data/item")

        with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
            json.dump(data_list, f, indent=4, ensure_ascii=False)

        print(f"\n✅ 최종 완료! {len(data_list)}개 저장됨: {OUTPUT_FILE}")
        # 확인용 출력
        if data_list:
            print(f"🔍 첫번째 데이터 확인: {data_list[0]}")

    except Exception as e:
        print(f"❌ 오류: {e}")
    finally:
        driver.quit()

if __name__ == "__main__":
    crawl_artifacts_fixed()