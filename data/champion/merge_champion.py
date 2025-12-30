import json
import os
import re

# ==========================================
# [설정] 파일 경로 (본인의 폴더 구조에 맞게 수정 가능)
# ==========================================
# 1. 기본 스탯 정보 파일 (champion 키 사용)
BASIC_INFO_FILE = "data/champion/lolchess_champion_stats.json" 

# 2. 통계 정보 파일 (name 키 사용)
STATS_INFO_FILE = "data/champion/metatft_units_stats.json" 

# 3. 결과 저장 파일
OUTPUT_FILE = "data/champion/champion_data.json"

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
    """
    이름 비교를 위해 공백과 특수문자를 제거하는 함수
    예: "Kog'Maw" -> "kogmaw", "공허의 피조물" -> "공허의피조물"
    """
    if not name: return ""
    # 한글, 영문, 숫자만 남기고 소문자로 변환
    return re.sub(r'[^가-힣a-zA-Z0-9]', '', str(name).lower())

def main():
    print(">>> ⚔️ 챔피언 데이터 병합 시작...")

    # 1. 데이터 로드
    basic_data = load_json(BASIC_INFO_FILE)
    stats_data = load_json(STATS_INFO_FILE)

    if not basic_data:
        print("❌ 기본 챔피언 데이터가 비어있습니다.")
        return

    print(f"   - 기본 정보: {len(basic_data)}명")
    print(f"   - 통계 정보: {len(stats_data)}명")

    # 2. 통계 데이터를 검색하기 쉽도록 딕셔너리로 변환 (Key: 정규화된 이름)
    #    list -> dict { "가렌": {stats...}, "다리우스": {stats...} }
    stats_map = {}
    for item in stats_data:
        # 통계 파일의 'name' 키를 사용
        raw_name = item.get("name")
        if raw_name:
            norm_name = normalize_name(raw_name)
            stats_map[norm_name] = item

    merged_list = []
    matched_count = 0

    # 3. 기본 데이터를 순회하며 통계 데이터 합치기
    for champ in basic_data:
        # 기본 파일의 'champion' 키를 사용
        raw_name = champ.get("champion")
        if not raw_name:
            continue
            
        norm_name = normalize_name(raw_name)
        
        # 병합될 새로운 객체 생성
        merged_champ = champ.copy()
        
        # 키 통일: 'champion' -> 'name'으로 변경 (LLM이 이해하기 더 쉬움)
        merged_champ["name"] = raw_name
        if "champion" in merged_champ:
            del merged_champ["champion"]

        # 통계 데이터가 있는지 확인 (Inner Join에 가까운 Left Join)
        if norm_name in stats_map:
            stats = stats_map[norm_name]
            
            # 통계 정보 병합 (tier, win_rate, popular_items 등)
            merged_champ["tier"] = stats.get("tier", "Unranked")
            merged_champ["avg_place"] = stats.get("avg_place", "-")
            merged_champ["win_rate"] = stats.get("win_rate", "-")
            merged_champ["pick_rate"] = stats.get("pick_rate", "-")
            merged_champ["popular_items"] = stats.get("popular_items", [])
            
            matched_count += 1
        else:
            # 통계가 없는 경우 (신규 챔피언 or 이름 불일치)
            merged_champ["tier"] = "Unranked"
            merged_champ["popular_items"] = []
            # print(f"⚠️ 통계 매칭 실패: {raw_name}")

        merged_list.append(merged_champ)

    # 4. 결과 저장
    if merged_list:
        with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
            json.dump(merged_list, f, indent=4, ensure_ascii=False)
        
        print("\n" + "="*40)
        print(f"🎉 병합 완료!")
        print(f"   - 총 챔피언: {len(merged_list)}명")
        print(f"   - 통계 매칭 성공: {matched_count}명")
        print(f"   - 저장 경로: {OUTPUT_FILE}")
        print("="*40)
        
        # 미리보기
        print("\n[미리보기: 첫 번째 데이터]")
        print(json.dumps(merged_list[0], indent=4, ensure_ascii=False))
    else:
        print("❌ 병합된 데이터가 없습니다.")

if __name__ == "__main__":
    main()