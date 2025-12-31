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
TARGET_URL = "https://www.metatft.com/comps"
OUTPUT_FILE = "data/meta/metatft_comps_final.json"

def clean_text(text):
    if not text: return ""
    return text.strip().replace("\n", " ").replace("\r", "")

def crawl_metatft():
    chrome_options = Options()
    
    # ★ [핵심 1] 페이지 로드 전략 변경: 'normal'(기본값) -> 'eager'
    # eager: 이미지/광고 로딩 안 기다림. HTML만 뜨면 바로 진행.
    chrome_options.page_load_strategy = 'eager' 
    
    # 창 크기 설정
    chrome_options.add_argument("--window-size=1920,1080")
    
    # 봇 탐지 회피 (기본적인 것만)
    chrome_options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
    chrome_options.add_argument("--disable-blink-features=AutomationControlled")

    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=chrome_options)
    
    deck_list = []
    seen_decks = set()

    try:
        print(f">>> MetaTFT 접속 (Fast Mode): {TARGET_URL}")
        driver.get(TARGET_URL)

        # ★ [핵심 2] 무한 로딩 끊기
        # 사이트 전체 로딩을 기다리지 않고, 덱 정보(.CompRow)가 하나라도 보이면 바로 멈춤
        try:
            print(">>> 핵심 데이터 대기 중...")
            WebDriverWait(driver, 15).until(
                EC.presence_of_element_located((By.CLASS_NAME, "CompRow"))
            )
            # 강제로 나머지 로딩(광고 등) 중단시킴
            driver.execute_script("window.stop();")
            print(">>> 로딩 강제 중단 및 스크롤 시작!")
        except Exception as e:
            print(">>> 대기 시간 초과 (데이터가 없을 수도 있음)")

        # ---------------------------------------------------------
        # 스크롤 로직 (빠르게)
        # ---------------------------------------------------------
        current_position = 0
        scroll_step = 1000 
        max_scroll_attempts = 20
        scroll_count = 0

        while scroll_count < max_scroll_attempts:
            driver.execute_script(f"window.scrollBy(0, {scroll_step});")
            current_position += scroll_step
            scroll_count += 1
            
            # eager 모드라 렌더링 시간이 조금 필요할 수 있음 (1초면 충분)
            time.sleep(1)
            
            total_height = driver.execute_script("return document.body.scrollHeight")
            visible_height = driver.execute_script("return window.innerHeight")
            
            if current_position + visible_height >= total_height:
                time.sleep(1) # 끝에서 잠깐 대기
                if driver.execute_script("return document.body.scrollHeight") <= total_height + 100:
                    break

        # ---------------------------------------------------------
        # 데이터 추출
        # ---------------------------------------------------------
        print(">>> 데이터 추출 중...")
        soup = BeautifulSoup(driver.page_source, "html.parser")
        
        rows = soup.find_all("div", class_=lambda x: x and "CompRow" in x and "CompRowPlaceholder" not in x)
        print(f">>> 발견된 덱: {len(rows)}개")

        for row in rows:
            try:
                # 1. 기본 정보
                tier_badge = row.select_one(".CompRowTierBadge")
                tier = clean_text(tier_badge.get_text()) if tier_badge else "Unknown"
                name_div = row.select_one(".Comp_Title")
                deck_name = clean_text(name_div.get_text()) if name_div else ""
                tags = [clean_text(tag.get_text()) for tag in row.select(".CompRowTag")]

                # 중복 체크
                deck_identifier = (tier, deck_name, tuple(sorted(tags)))
                if deck_identifier in seen_decks: continue
                seen_decks.add(deck_identifier)

                # 2. 통계 정보
                def get_stat_value(label):
                    stat_label = row.find("span", string=lambda text: text and label in text)
                    if stat_label:
                        number_el = stat_label.find_next(class_="Stat_Number")
                        if number_el:
                            return clean_text(number_el.get_text())
                    return "-"

                avg_place = get_stat_value("Avg Place")
                win_rate = get_stat_value("Win Rate")
                top4_rate = get_stat_value("Top 4 Rate")
                
                if avg_place == "-" and win_rate == "-": continue

                # 3. 챔피언 & 아이템
                champions = []
                unit_wrappers = row.select(".Unit_Wrapper")
                for unit in unit_wrappers:
                    if unit.select_one(".UnitFiller"): continue
                    
                    champ_name = ""
                    name_el = unit.select_one(".UnitNames")
                    if name_el: champ_name = clean_text(name_el.get_text())
                    
                    if not champ_name:
                        img_el = unit.select_one(".Unit_img")
                        if img_el: champ_name = img_el.get("alt", "Unknown")

                    items = [img.get('alt') for img in unit.select(".ItemsContainer_Inline img.Item_img") if img.get('alt')]
                    star = 3 if unit.select_one(".stars_div img") else 2
                    
                    champions.append({"name": champ_name, "star": star, "items": items})
                
                if not champions: continue

                # 4. [시너지 추출]
                synergies = []
                trait_elements = row.select(".CompUnitTraitsContainer .TraitCompact")
                for trait in trait_elements:
                    # 개수 (4, 2 등)
                    count = clean_text(trait.get_text())
                    
                    # 스타일 (gold, silver 등)
                    style = "Normal"
                    for cls in trait.get("class", []):
                        if cls in ["bronze", "silver", "gold", "platinum", "chromatic", "unique"]:
                            style = cls
                            break
                    
                    # 이름 (이미지 URL 파싱)
                    trait_name = "Unknown"
                    icon_div = trait.select_one(".TraitCompactIconContainer")
                    if icon_div and icon_div.has_attr("style"):
                        # style="mask-image: url('.../traits/sorcerer.png');"
                        match = re.search(r'traits/([^/]+)\.png', icon_div["style"])
                        if match:
                            trait_name = match.group(1).replace("%20", " ").title()
                    
                    synergies.append({"name": trait_name, "count": count, "style": style})

                # 5. 덱 이름 생성
                if not deck_name or deck_name == "Unknown Deck":
                    carries = [c['name'] for c in champions if len(c['items']) >= 2]
                    if not carries and champions: carries = [champions[0]['name']]
                    deck_name = f"{' & '.join(carries)} Deck"

                deck_list.append({
                    "tier": tier,
                    "name": deck_name,
                    "tags": tags,
                    "avg_place": avg_place,
                    "win_rate": win_rate,
                    "top4_rate": top4_rate,
                    "synergies": synergies,
                    "champions": champions
                })

            except Exception as e:
                continue

        # 저장
        if not os.path.exists("data"): os.makedirs("data")
        with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
            json.dump(deck_list, f, indent=4, ensure_ascii=False)

        print(f"\n✅ 완료! 총 {len(deck_list)}개 덱 수집됨.")
        print(f"📄 저장 경로: {OUTPUT_FILE}")

    except Exception as e:
        print(f"❌ 오류 발생: {e}")
    finally:
        driver.quit()

if __name__ == "__main__":
    crawl_metatft()