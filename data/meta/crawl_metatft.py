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
OUTPUT_FILE = "data/metatft_comps_final.json"

def clean_text(text):
    if not text: return ""
    return text.strip().replace("\n", " ").replace("\r", "")

def crawl_metatft():
    chrome_options = Options()
    chrome_options.page_load_strategy = 'normal' # 로딩 확실하게
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--window-size=1920,1080")
    chrome_options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36")

    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=chrome_options)
    
    deck_list = []
    # [추가된 부분 1] 중복 체크를 위한 집합(Set) 초기화
    seen_decks = set()

    try:
        print(f">>> MetaTFT 접속 시도: {TARGET_URL}")
        driver.get(TARGET_URL)

        # ---------------------------------------------------------
        # [Step 1] 점진적 스크롤 (Incremental Scroll)
        # ---------------------------------------------------------
        print(">>> 데이터를 놓치지 않기 위해 천천히 스크롤합니다...")
        
        # 초기 로딩 대기
        try:
            WebDriverWait(driver, 20).until(
                EC.presence_of_element_located((By.CLASS_NAME, "Stat_Number"))
            )
        except:
            print("   (경고: 초기 로딩이 늦습니다)")

        # 현재 스크롤 위치
        current_position = 0
        # 한 번에 내릴 높이 (모니터 높이 정도)
        scroll_step = 900 
        
        while True:
            # 1. 스크롤을 조금 내림
            driver.execute_script(f"window.scrollBy(0, {scroll_step});")
            current_position += scroll_step
            
            # 2. 중간 로딩 대기 (이 시간이 있어야 중간 데이터가 렌더링됨)
            time.sleep(1.5) 
            
            # 3. 페이지 끝에 도달했는지 확인
            total_height = driver.execute_script("return document.body.scrollHeight")
            visible_height = driver.execute_script("return window.innerHeight")
            
            # 현재 위치가 전체 높이보다 크거나 같으면 종료
            if current_position + visible_height >= total_height:
                # 혹시 모르니 끝에서 한 번 더 대기하고 높이 재확인 (무한 스크롤 대비)
                time.sleep(2)
                new_total_height = driver.execute_script("return document.body.scrollHeight")
                if new_total_height == total_height:
                    print(">>> 페이지 끝 도달 완료!")
                    break
                else:
                    total_height = new_total_height # 페이지가 더 길어졌으면 계속 진행

            print(f"   ... 스크롤 진행 중 ({current_position}/{total_height})")

        # ---------------------------------------------------------
        # [Step 2] HTML 파싱
        # ---------------------------------------------------------
        print(">>> 전체 HTML 파싱 시작...")
        soup = BeautifulSoup(driver.page_source, "html.parser")
        
        # Placeholder와 광고 제외
        rows = soup.find_all("div", class_=lambda x: x and "CompRow" in x and "CompRowPlaceholder" not in x)
        
        print(f">>> 유효 덱 {len(rows)}개 발견. 데이터 추출 및 중복 제거 시작...")

        valid_count = 0
        duplicate_count = 0 # 중복 카운트
        
        for idx, row in enumerate(rows):
            try:
                # --- A. 기본 정보 ---
                tier_badge = row.select_one(".CompRowTierBadge")
                tier = clean_text(tier_badge.get_text()) if tier_badge else "Unknown"

                name_div = row.select_one(".Comp_Title")
                deck_name = clean_text(name_div.get_text()) if name_div else ""

                tags = [clean_text(tag.get_text()) for tag in row.select(".CompRowTag")]

                # [추가된 부분 2] 중복 제거 로직
                # 덱 식별 키 생성: (티어, 덱이름, 태그들)
                # 태그 순서가 다를 수 있으므로 정렬하여 튜플로 변환
                deck_identifier = (tier, deck_name, tuple(sorted(tags)))

                if deck_identifier in seen_decks:
                    # 이미 수집된 덱이면 건너뜀
                    duplicate_count += 1
                    continue
                
                # 새로운 덱이면 식별 키 등록
                seen_decks.add(deck_identifier)

                # --- B. 통계 정보 ---
                def get_stat_value(label):
                    # 텍스트로 찾고 -> 다음 숫자 찾기
                    stat_label = row.find("span", string=lambda text: text and label in text)
                    if stat_label:
                        # find_next는 DOM 트리 순서상 뒤에 있는 요소를 찾음
                        number_el = stat_label.find_next(class_="Stat_Number")
                        if number_el:
                            val = clean_text(number_el.get_text())
                            return val if val else "-"
                    return "-"

                avg_place = get_stat_value("Avg Place")
                win_rate = get_stat_value("Win Rate")
                top4_rate = get_stat_value("Top 4 Rate")
                
                # 검증: 통계가 없으면 껍데기로 간주하고 패스
                if avg_place == "-" and win_rate == "-":
                    continue

                # --- C. 챔피언 ---
                champions = []
                unit_wrappers = row.select(".Unit_Wrapper")
                
                for unit in unit_wrappers:
                    if unit.select_one(".UnitFiller"): continue

                    # 이름
                    champ_name = ""
                    name_el = unit.select_one(".UnitNames")
                    if name_el:
                        champ_name = clean_text(name_el.get_text())
                    
                    if not champ_name:
                        link_el = unit.find("a", href=True)
                        if link_el:
                            champ_name = link_el['href'].split("/")[-1].replace("%20", " ")
                        else:
                            img_el = unit.select_one(".Unit_img")
                            if img_el:
                                champ_name = img_el.get("alt", "Unknown")

                    # 아이템
                    items = []
                    for item_img in unit.select(".ItemsContainer_Inline img.Item_img"):
                        item_alt = item_img.get('alt')
                        if item_alt:
                            items.append(item_alt)

                    # 별 레벨 (3성)
                    star_level = 2
                    stars_div = unit.select_one(".stars_div")
                    if stars_div and stars_div.find("img"):
                        star_level = 3
                    
                    champions.append({
                        "name": champ_name,
                        "star": star_level,
                        "items": items
                    })

                if not champions: continue

                # 덱 이름 자동 생성 (없을 경우)
                if not deck_name or deck_name == "Unknown Deck":
                    carries = [c['name'] for c in champions if len(c['items']) >= 2]
                    if not carries: carries = [champions[0]['name']]
                    deck_name = f"{' & '.join(carries)} Deck"

                deck_data = {
                    "tier": tier,
                    "name": deck_name,
                    "tags": tags,
                    "avg_place": avg_place,
                    "win_rate": win_rate,
                    "top4_rate": top4_rate,
                    "champions": champions
                }
                deck_list.append(deck_data)
                valid_count += 1

            except Exception as e:
                print(f"⚠️ Row Parsing Error: {e}")
                continue

        # 4. 저장
        if not os.path.exists("data"):
            os.makedirs("data")

        with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
            json.dump(deck_list, f, indent=4, ensure_ascii=False)

        print(f"\n✅ [MetaTFT] 최종 정제 완료!")
        print(f"   - 전체 발견 행: {len(rows)}")
        print(f"   - 중복 제거됨: {duplicate_count}")
        print(f"   - 최종 저장: {valid_count}")
        print(f"📄 저장 경로: {OUTPUT_FILE}")
        
    except Exception as e:
        print(f"❌ 크롤링 실패: {e}")
    finally:
        driver.quit()

if __name__ == "__main__":
    crawl_metatft()