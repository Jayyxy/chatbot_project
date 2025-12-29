import json
import os
import re

# ==========================================
# [설정] 파일 경로
# ==========================================
LOLCHESS_FILE = "data/meta/lolchess_guide_structured.json"
METATFT_FILE = "data/meta/metatft_comps_final.json"
OUTPUT_FILE = "data/meta/merged_decks.json"

# 유사도 기준 (0.65 ~ 0.75 추천)
# 너무 높으면 같은 덱인데도 안 합쳐지고, 너무 낮으면 다른 덱이 합쳐짐
SIMILARITY_THRESHOLD = 0.65 

# 비교 시 무시할 유닛 (소환물 등)
IGNORE_LIST = [
    "황제의근위대", "얼어붙은포탑", "티버", "thex", "t헥스", 
    "훈련봇", "공허의피조물", "아이템", "대상", "유닛"
]

def load_json(path):
    if not os.path.exists(path):
        print(f"❌ 파일 없음: {path}")
        return []
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

def normalize_name(name):
    """한글/영문/숫자 유지, 특수문자/공백 제거"""
    if not name: return ""
    return re.sub(r'[\s\(\)\.\'\"\[\]]', '', str(name).lower())

def get_champions_set(deck_data):
    """
    덱 데이터에서 챔피언 이름 집합(Set) 추출
    (MetaTFT의 champions 키와 Lolchess의 positioning 키 모두 대응)
    """
    champs = set()
    
    # 1. MetaTFT 구조 (champions: [ {name: ...}, ... ])
    if "champions" in deck_data:
        for c in deck_data["champions"]:
            raw = c.get("name") if isinstance(c, dict) else c
            norm = normalize_name(raw)
            if norm and norm not in IGNORE_LIST:
                champs.add(norm)
                
    # 2. Lolchess 구조 (positioning: [ {champion: ...}, ... ])
    if "positioning" in deck_data:
        for p in deck_data["positioning"]:
            raw = p.get("champion")
            norm = normalize_name(raw)
            if norm and norm not in IGNORE_LIST:
                champs.add(norm)
                
    return champs

def calculate_similarity(set1, set2):
    """자카드 유사도 계산"""
    if not set1 or not set2: return 0.0
    intersection = len(set1 & set2)
    union = len(set1 | set2)
    return intersection / union

def main():
    print(">>> 데이터 병합 시작...")
    
    # 데이터 로드
    lolchess_list = load_json(LOLCHESS_FILE)
    metatft_list = load_json(METATFT_FILE)
    
    if not metatft_list:
        print("⚠️ MetaTFT 데이터가 없어 병합할 수 없습니다.")
        return

    merged_results = []
    
    # 이미 병합된 Lolchess 덱 인덱스 추적 (중복 병합 방지)
    merged_lolchess_indices = set()

    # 1. MetaTFT 데이터를 기준으로 순회 (Tier 정보가 중요하므로)
    for meta_deck in metatft_list:
        meta_champs = get_champions_set(meta_deck)
        
        best_match_idx = -1
        best_score = 0.0
        
        # 2. Lolchess 데이터와 비교
        for idx, lol_deck in enumerate(lolchess_list):
            # 이미 다른 덱과 합쳐졌으면 스킵 (선택 사항)
            # if idx in merged_lolchess_indices: continue 
            
            lol_champs = get_champions_set(lol_deck)
            score = calculate_similarity(meta_champs, lol_champs)
            
            if score > best_score:
                best_score = score
                best_match_idx = idx
        
        # 3. 유사도가 기준을 넘으면 합체!
        final_deck = meta_deck.copy() # MetaTFT 데이터를 베이스로
        
        if best_score >= SIMILARITY_THRESHOLD:
            lol_match = lolchess_list[best_match_idx]
            merged_lolchess_indices.add(best_match_idx)
            
            print(f"✅ [병합 성공] {meta_deck.get('name')} 🔗 {lol_match.get('detail_deck_name') or lol_match.get('meta_info', {}).get('name')} (유사도: {best_score:.2f})")
            
            # --- 데이터 합치기 ---
            # 1) 가이드/운영법 (Lolchess가 더 좋음)
            final_deck["guide"] = lol_match.get("guide", {})
            
            # 2) 배치 정보 (Lolchess Positioning이 좌표가 있어 더 좋음)
            if "positioning" in lol_match:
                final_deck["positioning"] = lol_match["positioning"]
            
            # 3) 증강체 정보 (둘 다 있다면 합치거나 Lolchess 우선)
            if "augments" in lol_match:
                final_deck["augments"] = lol_match["augments"]
            
            # 4) 한글 덱 이름 (Lolchess가 더 정확할 수 있음)
            lol_name = lol_match.get("detail_deck_name") or lol_match.get("meta_info", {}).get("name")
            if lol_name:
                final_deck["name_kr"] = lol_name
                
            # 5) 출처 표기
            final_deck["data_source"] = ["MetaTFT", "LoLCHESS"]
            
        else:
            # 매칭되는 가이드를 못 찾음 -> 통계 데이터만 유지
            # print(f"ℹ️ [단독 유지] {meta_deck.get('name')} (매칭되는 가이드 없음)")
            final_deck["data_source"] = ["MetaTFT"]
            final_deck["guide"] = None # 가이드 없음 표시

        merged_results.append(final_deck)

    # 4. (선택) 매칭되지 않은 Lolchess 덱들도 결과에 포함할까?
    # 통계(Tier)는 없지만 가이드만 있는 덱도 중요하다면 추가
    for idx, lol_deck in enumerate(lolchess_list):
        if idx not in merged_lolchess_indices:
            # MetaTFT 형식을 맞춰서 추가
            new_deck = {
                "name": lol_deck.get("detail_deck_name") or lol_deck.get("meta_info", {}).get("name"),
                "tier": "Unranked", # 티어 정보 없음
                "avg_place": "-",
                "win_rate": "-",
                "guide": lol_deck.get("guide", {}),
                "positioning": lol_deck.get("positioning", []),
                "augments": lol_deck.get("augments", {}),
                "data_source": ["LoLCHESS"]
            }
            # 챔피언 리스트 생성 (검색용)
            champs_list = []
            if "positioning" in lol_deck:
                for p in lol_deck["positioning"]:
                    if "champion" in p: champs_list.append({"name": p["champion"]})
            new_deck["champions"] = champs_list
            
            merged_results.append(new_deck)
            # print(f"➕ [가이드만 추가] {new_deck['name']}")

    # 저장
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(merged_results, f, indent=4, ensure_ascii=False)

    print(f"\n🎉 최종 완료! 총 {len(merged_results)}개의 통합 덱이 생성되었습니다.")
    print(f"📄 저장 위치: {OUTPUT_FILE}")

if __name__ == "__main__":
    main()