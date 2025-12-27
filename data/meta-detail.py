import json
import time
import re
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
from bs4 import BeautifulSoup
from tqdm import tqdm

# ==========================================
# [설정] 크롤링 옵션
# ==========================================
INPUT_META_FILE = "data/lolchess_meta.txt" # 1단계에서 수집한 파일 (링크 포함)
OUTPUT_DETAIL_FILE = "data/lolchess_detail_full.json"

# ==========================================
# [헬퍼 함수] URL 추출
# ==========================================
def extract_urls_from_text(filepath):
    urls = []
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
            # 텍스트 파일에서 https://lolchess.gg... 로 시작하는 링크만 추출
            urls = re.findall(r'(https://lolchess\.gg/builder/guide/[a-zA-Z0-9]+(?:\?type=guide)?)', content)
    except FileNotFoundError:
        print("❌ 메타 데이터 파일이 없습니다. crawl_lolchess.py 먼저 실행하세요.")
    return list(set(urls)) # 중복 제거

# ==========================================
# [핵심] 상세 페이지 파서
# ==========================================
def parse_guide_detail(html_source, url):
    soup = BeautifulSoup(html_source, 'html.parser')
    data = {"url": url, "positioning": [], "guide_text": "", "augments": ""}

    try:
        # -------------------------------------------------
        # 1. 덱 배치 (Hex Grid) 수집
        # -------------------------------------------------
        # 제공된 HTML의 'Board' 클래스 식별 (css-y6vj5x)
        board = soup.find("div", class_=lambda x: x and "css-y6vj5x" in x)
        
        if board:
            slots = board.find_all("div", class_=lambda x: x and "Slot" in x)
            for idx, slot in enumerate(slots):
                # 챔피언 이름 추출 (css-16jrvsm)
                name_div = slot.find("div", class_=lambda x: x and "ed21b2i3" in x) # 이름 클래스 추정
                if not name_div:
                    # 클래스명이 바뀌었을 경우를 대비해 하위 div 텍스트 탐색
                    name_div = slot.select_one(".css-16jrvsm") 
                
                if name_div:
                    champ_name = name_div.get_text(strip=True)
                    
                    # 3성 여부 확인 (별 이미지 개수 카운트)
                    stars = len(slot.find_all("div", class_=lambda x: x and "bg-black" in x)) # 별모양 div
                    
                    # 아이템 추출 (이미지 URL에서 이름 파싱)
                    items = []
                    item_imgs = slot.find_all("img", src=True)
                    for img in item_imgs:
                        if "items" in img['src']:
                            # 예: .../Bloodthirster_1710...png -> Bloodthirster
                            item_name = img['src'].split("/")[-1].split("_")[0]
                            items.append(item_name)

                    # 배치 좌표 계산 (4줄 x 7칸 = 28슬롯)
                    row = (idx // 7) + 1
                    col = (idx % 7) + 1
                    location = "전열" if row <= 2 else "후열"

                    data["positioning"].append({
                        "champion": champ_name,
                        "star": stars if stars > 0 else 1, # 기본 1성
                        "items": items,
                        "location": f"{location} ({row}열 {col}번째)"
                    })

        # -------------------------------------------------
        # 2. 공략법 & 3. 추천 증강체 수집
        # -------------------------------------------------
        # 가이드 박스들 (css-1s5hngw)
        guide_boxes = soup.find_all("div", class_=lambda x: x and "css-1s5hngw" in x)
        
        for box in guide_boxes:
            title_tag = box.find("h2")
            if not title_tag: continue
            
            title = title_tag.get_text(strip=True)
            content_div = box.find("div", class_="challenger-comment")
            
            if not content_div: continue
            
            # 텍스트 정제 (HTML 태그 제거하고 줄바꿈 유지)
            content_text = content_div.get_text(separator="\n", strip=True)

            if "증강체" in title:
                data["augments"] = content_text
            else:
                data["guide_text"] += f"[{title}]\n{content_text}\n\n"

    except Exception as e:
        print(f"Error parsing detail: {e}")
    
    return data

# ==========================================
# [실행] 메인 로직
# ==========================================
def main():
    # 1. URL 로드
    urls = extract_urls_from_text(INPUT_META_FILE)
    if not urls:
        # 테스트용 더미 URL (파일이 없을 경우)
        print("URL을 찾을 수 없어 테스트 URL로 진행합니다.")
        urls = ["https://lolchess.gg/builder/guide/1c9abbb46b58c49ab2d851f4d74e43a99c0518c6?type=guide"]
    
    print(f">>> 총 {len(urls)}개의 상세 공략을 수집합니다.")

    # 2. 브라우저 설정
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=chrome_options)

    results = []

    # 3. 크롤링 루프
    for url in tqdm(urls):
        try:
            driver.get(url)
            # 데이터 로딩 대기 (Board나 Guide가 뜰 때까지)
            WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.CLASS_NAME, "Guide"))
            )
            time.sleep(1) # 안전 대기

            # 데이터 파싱
            detail_data = parse_guide_detail(driver.page_source, url)
            results.append(detail_data)
            
        except Exception as e:
            print(f"Failed to crawl {url}: {e}")
            continue

    driver.quit()

    # 4. 저장
    with open(OUTPUT_DETAIL_FILE, 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=4, ensure_ascii=False)
    
    print(f"\n✅ 수집 완료! {OUTPUT_DETAIL_FILE} 파일을 확인하세요.")

if __name__ == "__main__":
    main()