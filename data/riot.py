import os
import json
import requests
from dotenv import load_dotenv

# 1. 환경변수 로드
load_dotenv()
API_KEY = os.getenv("RIOT_API_KEY")
HEADERS = {"X-Riot-Token": API_KEY}

# ---------------------------------------------------------
# [Helper] 문자열 정리 함수
# ---------------------------------------------------------
def clean_id(text):
    if not isinstance(text, str): return text
    if "Item_" in text: return text.split("Item_")[-1]
    if "_" in text: return text.split("_")[-1]
    return text

# ---------------------------------------------------------
# [Core] 데이터 파서
# ---------------------------------------------------------
def parse_match_data(raw_data):
    info = raw_data.get('info', {})
    participants = info.get('participants', [])
    
    parsed_game = {
        "match_id": raw_data['metadata']['match_id'],
        "game_version": info.get('game_version'),
        "players": []
    }

    # 등수 순서대로 정렬 (1등부터)
    sorted_participants = sorted(participants, key=lambda x: x['placement'])

    for p in sorted_participants:
        # 유닛
        units_clean = []
        for u in p.get('units', []):
            units_clean.append({
                "name": clean_id(u.get('character_id')),
                "tier": u.get('tier'),
                "items": [clean_id(i) for i in u.get('itemNames', [])]
            })

        # 시너지 (활성화된 것만)
        traits_clean = []
        for t in p.get('traits', []):
            if t.get('tier_current', 0) > 0:
                traits_clean.append({
                    "name": clean_id(t.get('name')),
                    "level": t.get('tier_current')
                })

        # 증강체
        augments_clean = [clean_id(a) for a in p.get('augments', [])]

        parsed_game['players'].append({
            "placement": p.get('placement'),
            "level": p.get('level'),
            "gold_left": p.get('gold_left'),
            "augments": augments_clean,
            "traits": traits_clean,
            "units": units_clean
        })
    
    return parsed_game

# ---------------------------------------------------------
# [Main] 수정된 실행 로직 (Step 2 제거됨)
# ---------------------------------------------------------
def main():
    print("🚀 TFT 데이터 수집기 (Optimized Version)...")

    # 1. 챌린저 리스트 조회 -> 바로 PUUID 획득!
    url_league = "https://kr.api.riotgames.com/tft/league/v1/challenger"
    res = requests.get(url_league, headers=HEADERS)
    
    if res.status_code != 200:
        return print(f"❌ League API Error: {res.status_code}")
    
    entries = res.json()['entries']
    if not entries:
        return print("❌ 챌린저 유저가 없습니다.")

    # 첫 번째 유저의 PUUID 바로 추출 (summonerId 조회 불필요)
    target_entry = entries[0]
    puuid = target_entry.get('puuid') 
    
    # 만약 puuid가 없다면 summonerId로 우회해야 하지만, 로그상 puuid가 있음
    if not puuid:
        print("❌ PUUID를 찾을 수 없습니다. API 응답 구조가 또 변경되었을 수 있습니다.")
        return

    print(f"1️⃣ PUUID 즉시 확보 완료: {puuid[:10]}...")

    # 2. 매치 ID 조회 (Step 3 -> Step 2로 승격)
    # 한국(KR) 유저의 매치 데이터는 'asia' 라우팅을 사용해야 함
    url_match_list = f"https://asia.api.riotgames.com/tft/match/v1/matches/by-puuid/{puuid}/ids?start=0&count=1"
    res_match = requests.get(url_match_list, headers=HEADERS)
    
    if res_match.status_code != 200:
        return print(f"❌ Match List Error: {res_match.status_code}")

    match_ids = res_match.json()
    if not match_ids:
        return print("❌ 최근 플레이한 매치 기록이 없습니다.")
    
    match_id = match_ids[0]
    print(f"2️⃣ 최신 매치 ID 확보: {match_id}")

    # 3. 매치 상세 조회 및 저장
    url_detail = f"https://asia.api.riotgames.com/tft/match/v1/matches/{match_id}"
    res_detail = requests.get(url_detail, headers=HEADERS)
    
    if res_detail.status_code != 200:
        return print(f"❌ Match Detail Error: {res_detail.status_code}")

    raw_data = res_detail.json()
    clean_data = parse_match_data(raw_data)

    # 폴더가 없으면 생성
    if not os.path.exists("data"):
        os.makedirs("data")
        
    save_path = f"data/clean_{match_id}.json"
    with open(save_path, 'w', encoding='utf-8') as f:
        json.dump(clean_data, f, indent=4, ensure_ascii=False)
    
    print(f"\n✅ 데이터 수집 성공! -> {save_path}")

if __name__ == "__main__":
    main()