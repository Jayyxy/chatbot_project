import json
import os
import re

# ==========================================
# [설정] 파일 경로
# ==========================================
LOLCHESS_FILE = "data/meta/lolchess_guide_structured.json"
METATFT_FILE = "data/meta/metatft_comps_final.json"
OUTPUT_FILE = "data/meta/merged_decks.json"

SIMILARITY_THRESHOLD = 0.60  # 60% 이상 일치하면 같은 덱으로 간주
SIMILARITY_THRESHOLD = 0.60  # 60% 이상 일치하면 같은 덱으로 간주

# 비교 시 무시할 유닛 (소환물, 아이템 등)
IGNORE_LIST = [
    "황제의근위대", "얼어붙은포탑", "티버", "thex", "t헥스", 
    "훈련봇", "공허의피조물", "아이템", "대상", "유닛"
]

def load_json(path):
    if not os.path.exists(path):
        print(f"❌ 파일을 찾을 수 없습니다: {path}")
        return []
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        print(f"❌ 파일 로드 오류 {path}: {e}")
        return []

def normalize_name(name):
    """한글, 영문, 숫자만 남기고 나머지 제거 (비교 정확도 향상)"""
    if not name: return ""
    return re.sub(r'[^가-힣a-zA-Z0-9]', '', str(name).lower())

def get_champions_set(deck_data):
    """덱 데이터에서 챔피언 구성(Set) 추출"""
    champs = set()
    
    # MetaTFT 구조
    if "champions" in deck_data:
        for c in deck_data["champions"]:
            raw = c.get("name") if isinstance(c, dict) else c
            norm = normalize_name(raw)
            if norm and norm not in IGNORE_LIST:
                champs.add(norm)
                
    # Lolchess 구조 (positioning 안에 champion 키가 있음)
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

def clean_champion_list(champs):
    """결과 리스트에서 소환수 제거"""
    cleaned = []
    for c in champs:
        raw = c.get("name") if isinstance(c, dict) else c
        norm = normalize_name(raw)
        if norm and norm not in IGNORE_LIST:
            cleaned.append(c)
    return cleaned

# ★ [추가됨] 시너지 리스트 정제 함수
def clean_synergy_list(synergies):
    """
    시너지 리스트에서 유효하지 않은 데이터(이름 없음, Unknown 등)를 제거합니다.
    """
    if not synergies: return []
    
    cleaned = []
    for s in synergies:
        name = s.get("name", "")
        # 이름이 존재하고, 'Unknown'이 아닌 경우만 포함
        if name and name.lower() != "unknown":
            cleaned.append(s)
    return cleaned

def main():
    print(">>> 🚀 MetaTFT 기준 병합 프로세스 시작...\n")
    
    lolchess_list = load_json(LOLCHESS_FILE)
    metatft_list = load_json(METATFT_FILE)

    if not metatft_list:
        print("❌ MetaTFT 데이터가 없습니다.")
        return

    merged_results = []
    
    # 통계 카운터
    total_metatft_count = len(metatft_list)
    merged_count = 0

    # =========================================================
    # [핵심] MetaTFT 데이터를 기준으로 순회 (Left Join 방식)
    # =========================================================
    for meta_deck in metatft_list:
        meta_champs = get_champions_set(meta_deck)
        
        # 1. 롤체지지 데이터 중 가장 유사한 덱 찾기
        best_match_idx = -1
        best_score = 0.0
        
        for idx, lol_deck in enumerate(lolchess_list):
            lol_champs = get_champions_set(lol_deck)
            score = calculate_similarity(meta_champs, lol_champs)
            
            if score > best_score:
                best_score = score
                best_match_idx = idx
        
        # 2. 결과 객체 생성 (MetaTFT 원본 유지 -> 시너지 포함됨)
        final_deck = meta_deck.copy()
        
        # [데이터 정제 1] 챔피언 리스트 청소 (소환수 제거)
        if "champions" in final_deck:
            final_deck["champions"] = clean_champion_list(final_deck["champions"])

        # [데이터 정제 2] ★ 시너지 리스트 청소 (기능 추가됨)
        if "synergies" in final_deck:
            final_deck["synergies"] = clean_synergy_list(final_deck["synergies"])

        # 3. 유사도가 기준을 넘으면 -> 가이드 & HOT 여부만 가져옴
        if best_score >= SIMILARITY_THRESHOLD:
            lol_match = lolchess_list[best_match_idx]
            
            # --- [요청사항] 롤체지지에서 가져올 데이터 ---
            # 1. 가이드
            final_deck["guide"] = lol_match.get("guide", {})
            
            # 2. HOT 여부 (meta_info 안에서 찾기)
            is_hot = False
            if "meta_info" in lol_match and isinstance(lol_match["meta_info"], dict):
                is_hot = lol_match["meta_info"].get("is_hot", False)
            final_deck["is_hot"] = is_hot
            
            # (옵션) 한글 이름도 있으면 좋으니 가져옴
            lol_name = lol_match.get("detail_deck_name") or lol_match.get("meta_info", {}).get("name")
            if lol_name:
                final_deck["name_kr"] = lol_name

            final_deck["data_source"] = ["MetaTFT", "LoLCHESS"]
            merged_count += 1
            
            # [출력] 병합된 덱 로그
            print(f"✅ [병합] 유사도 {int(best_score*100)}%")
            print(f"   ├─ MetaTFT : {meta_deck.get('name')}")
            print(f"   └─ LoLCHESS: {lol_name} (Hot: {is_hot})")
            print("-" * 50)
            
        else:
            # 매칭 실패 시 MetaTFT 데이터만 유지 (가이드 없음)
            final_deck["data_source"] = ["MetaTFT"]
            final_deck["guide"] = None
            final_deck["is_hot"] = False

        merged_results.append(final_deck)

    # =========================================================
    # 저장 및 결과 요약
    # =========================================================
    if merged_results:
        with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
            json.dump(merged_results, f, indent=4, ensure_ascii=False)
        
        print("\n" + "="*35)
        print(f"🎉 병합 작업 최종 완료")
        print(f"   - 총 MetaTFT 덱 개수 : {total_metatft_count}개")
        print(f"   - 병합 성공(가이드 포함): {merged_count}개")
        print(f"   - 병합 실패(통계만 존재): {total_metatft_count - merged_count}개")
        print(f"   - 저장 경로: {OUTPUT_FILE}")
        print("="*35)
    else:
        print("❌ 저장할 데이터가 없습니다.")

if __name__ == "__main__":
    main()