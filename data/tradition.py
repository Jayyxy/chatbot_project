import json
import os
import re

# ==========================================
# [설정] 데이터 폴더
# ==========================================
TARGET_ROOT_FOLDER = "data" 

# ==========================================
# [1] 통합 매핑 테이블 (챔피언 + 아이템 + 지역/특성)
# ==========================================
# 지역/특성 이름도 추가해야 완벽하게 바뀝니다.
TRAIT_MAP = {
    # ★ 여기에 추가했습니다 ★
    "Quickstriker": "기동타격대", 
    "Defender": "엄호대",
    "Sorcerer": "비전 마법사", 
    "Arcanist": "비전 마법사", # 혼용될 경우 대비

    # --- 기존 목록 ---
    "Shurima": "슈리마", "Ionia": "아이오니아", "Demacia": "데마시아",
    "Freljord": "프렐요드", "Noxus": "녹서스", "Bilgewater": "빌지워터",
    "Piltover": "필트오버", "Shadow Isles": "그림자 군도", "Targon": "타곤",
    "Void": "공허", "Zaun": "자운", "Ixtal": "이쉬탈",
    "Challenger": "도전자", "Invoker": "기원자", "Slayer": "학살자",
    "Strategist": "책략가", "Bastion": "요새",
    "Bruiser": "난동꾼", "Juggernaut": "전쟁기계", "Gunner": "사격수",
    "Rogue": "불한당", "Deadeye": "백발백중", "Multicaster": "연쇄마법사",
    "Yordle": "요들", "Darkin": "다르킨", "Empress": "여제",
    "Reaper": "사신", "Vanquisher": "토벌자", "Warden": "파수꾼"
}

CHAMP_MAP = {
    # (기존 챔피언 매핑 전체 포함 - 생략 없이 다 넣으세요)
    "Caitlyn": "케이틀린", "Garen": "가렌", "Illaoi": "일라오이", "Jarvan IV": "자르반 4세",
    "Jax": "잭스", "Kog'Maw": "코그모", "Wukong": "오공", "Neeko": "니코",
    "Poppy": "뽀삐", "Singed": "신지드", "Skarner": "스카너", "Swain": "스웨인",
    "Vi": "바이", "Volibear": "볼리베어", "Warwick": "워윅", "Galio": "갈리오",
    "Kennen": "케넨", "Senna": "세나", "Seraphine": "세라핀", "Shen": "쉔",
    "Taric": "타릭", "Yone": "요네", "Ahri": "아리", "Bard": "바드",
    "Ekko": "에코", "Lulu": "룰루", "Miss Fortune": "미스 포츈",
    "Thresh": "쓰레쉬", "Twisted Fate": "트위스티드 페이트", "Viego": "비에고",
    "Nautilus": "노틸러스", "Ornn": "오른", "Sylas": "사일러스", "Sett": "세트",
    "Yorick": "요릭", "Kindred": "킨드레드", "Aphelios": "아펠리오스", "Ashe": "애쉬",
    "Diana": "다이애나", "Annie": "애니", "Rumble": "럼블", "Tahm Kench": "탐 켄치",
    "Tristana": "트리스타나", "Zoe": "조이", "Teemo": "티모", "Jinx": "징크스",
    "Sona": "소나", "Ziggs": "직스", "Jhin": "진", "Draven": "드레이븐",
    "Gangplank": "갱플랭크", "Gwen": "그웬", "Kai'Sa": "카이사", "Kalista": "칼리스타",
    "LeBlanc": "르블랑", "Lux": "럭스", "Malzahar": "말자하", "Milio": "밀리오",
    "Nasus": "나서스", "Orianna": "오리아나", "Qiyana": "키아나", "Ryze": "라이즈",
    "Sejuani": "세주아니", "Shyvana": "쉬바나", "Tryndamere": "트린다미어",
    "Vayne": "베인", "Veigar": "베이가", "Xerath": "제라스", "Xin Zhao": "신 짜오",
    "Yasuo": "야스오", "Zilean": "질리언", "Baron Nashor": "내셔 남작",
    "Rift Herald": "협곡의 전령", "T-Hex": "T-헥스", "Kobuko": "코부코",
    "Lucian & Senna": "루시안과 세나", "Kobuko & Yuumi": "코부코와 유미",
    "Ambessa": "암베사", "Mel": "멜", "Renekton": "레넥톤", "Leona": "레오나",
    "Cho'Gath": "초가스", "Dr. Mundo": "문도 박사", "Graves": "그레이브즈",
    "Bel'Veth": "벨베스", "Anivia": "애니비아", "Fiddlesticks": "피들스틱",
    "Loris": "로리스", "Zaahen": "자헨", "Brock": "브록", "Yunara": "유나라", "Tibbers": "티버"
}

ITEM_MAP = {
    # (기존 아이템 매핑 전체 포함 - 생략 없이 다 넣으세요)
    "RedBuffItem": "붉은 덩굴정령", "IronWill": "용의 발톱",
    "LordsEdge": "죽음의 검", "Fimbulwinter": "종말의 겨울",
    "LudensEcho": "루덴의 폭풍", "TFT16": "시즌16 아이템",
    "GuinsoosRageblade": "구인수의 격노검", "RunaansHurricane": "루난의 허리케인",
    "InfinityEdge": "무한의 대검", "SpearofShojin": "쇼진의 창",
    "ArcaneGauntlet": "보석 건틀릿", "VoidStaff": "공허의 지팡이",
    "ArchangelsStaff": "대천사의 지팡이", "Bloodthirster": "피바라기",
    "BlueBuff": "블루 버프", "BrambleVest": "덤불 조끼",
    "Crownguard": "크라운가드", "Deathblade": "죽음의 검",
    "DragonsClaw": "용의 발톱", "EdgeofNight": "밤의 끝자락",
    "GargoyleStoneplate": "가고일 돌갑옷", "GiantSlayer": "거인 학살자",
    "Guardbreaker": "방패파괴자", "HandOfJustice": "정의의 손길",
    "HextechGunblade": "헥스텍 총검", "IonicSpark": "이온 충격기",
    "JeweledGauntlet": "보석 건틀릿", "LastWhisper": "최후의 속삭임",
    "Morellonomicon": "모렐로노미콘", "NashorsTooth": "내셔의 이빨",
    "ProtectorsVow": "수호자의 맹세", "Quicksilver": "수은",
    "RabadonsDeathcap": "라바돈의 죽음모자", "RapidFirecannon": "고속 연사포",
    "Redemption": "구원", "RedBuff": "붉은 덩굴정령",
    "StatikkShiv": "스태틱의 단검", "SteadfastHeart": "굳건한 심장",
    "SteraksGage": "스테락의 도전", "SunfireCape": "태양불꽃 망토",
    "TacticiansCrown": "전략가의 왕관", "ThiefsGloves": "도적의 장갑",
    "TitansResolve": "거인의 결의", "WarmogsArmor": "워모그의 갑옷",
    "Evenshroud": "저녁갑주", "GuardianAngel": "밤의 끝자락"
}

# 모든 매핑 합치기 (긴 단어부터 치환하도록 정렬)
ALL_REPLACE_MAP = {**CHAMP_MAP, **ITEM_MAP, **TRAIT_MAP}
SORTED_KEYS = sorted(ALL_REPLACE_MAP.keys(), key=len, reverse=True)

# -----------------------------------------------------------
# [유틸] 텍스트 내 영문 치환 (핵심)
# -----------------------------------------------------------
def replace_english_terms(text):
    if not text or not isinstance(text, str):
        return text
    
    # 한글만 있거나 특수문자만 있으면 패스
    if not re.search(r'[a-zA-Z]', text):
        return text

    # 문장 내 단어 치환
    for key in SORTED_KEYS:
        # 대소문자 무시하고 단어 경계(\b) 체크
        pattern = re.compile(r'\b' + re.escape(key) + r'\b', re.IGNORECASE)
        if pattern.search(text):
            text = pattern.sub(ALL_REPLACE_MAP[key], text)
            
    return text

# -----------------------------------------------------------
# [기존 유틸] 정규화 함수
# -----------------------------------------------------------
def normalize_key(text):
    if not text: return ""
    return re.sub(r'[^a-zA-Z0-9]', '', text).lower()

NORMALIZED_ITEM_MAP = {normalize_key(k): v for k, v in ITEM_MAP.items()}

def get_korean_item_name(raw_name):
    if raw_name in ITEM_MAP:
        return ITEM_MAP[raw_name]
    clean_key = normalize_key(raw_name)
    if clean_key in NORMALIZED_ITEM_MAP:
        return NORMALIZED_ITEM_MAP[clean_key]
    return raw_name

def process_file(file_path):
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception as e:
        print(f"⚠️ 읽기 실패 ({file_path}): {e}")
        return

    if isinstance(data, list):
        items_to_process = data
    elif isinstance(data, dict):
        items_to_process = [data]
    else:
        return

    converted = False
    
    for entry in items_to_process:
        if not isinstance(entry, dict): continue

        # [1] 덱 이름 변환 (meta_info.name 등) - ★ 여기가 핵심 수정됨
        if "name" in entry: # 루트 레벨의 name (MetaTFT 등)
            original = entry["name"]
            new_name = replace_english_terms(original)
            if original != new_name:
                entry["name"] = new_name
                converted = True

        if "meta_info" in entry and isinstance(entry["meta_info"], dict):
            if "name" in entry["meta_info"]:
                original = entry["meta_info"]["name"]
                new_name = replace_english_terms(original)
                if original != new_name:
                    entry["meta_info"]["name"] = new_name
                    converted = True
        
        if "detail_deck_name" in entry:
            original = entry["detail_deck_name"]
            new_name = replace_english_terms(original)
            if original != new_name:
                entry["detail_deck_name"] = new_name
                converted = True

        # [2] 챔피언 이름 변환 (단순 1:1)
        for k in ["champion"]:
            if k in entry and entry[k] in CHAMP_MAP:
                entry[k] = CHAMP_MAP[entry[k]]
                converted = True

        # [3] 아이템 리스트 변환
        for k in ["popular_items", "items"]:
            if k in entry:
                new_items = []
                changed = False
                for item in entry[k]:
                    clean_text = item.split(" (")[0].strip()
                    kr_name = get_korean_item_name(clean_text)
                    new_items.append(kr_name)
                    if item != kr_name: changed = True
                
                if changed:
                    entry[k] = new_items
                    converted = True

        # [4] 내부 챔피언 리스트 (champions 키)
        if "champions" in entry and isinstance(entry["champions"], list):
            for champ in entry["champions"]:
                if "name" in champ:
                    # 여기도 문장형 치환 적용 (ex: "Headliner Yasuo")
                    original = champ["name"]
                    new_name = replace_english_terms(original)
                    if original != new_name:
                        champ["name"] = new_name
                        converted = True
                        
                if "items" in champ:
                    new_items = []
                    for c_item in champ["items"]:
                         clean_text = c_item.split(" (")[0].strip()
                         new_items.append(get_korean_item_name(clean_text))
                    champ["items"] = new_items
                    converted = True

        # [5] 배치 정보 (positioning 키)
        if "positioning" in entry and isinstance(entry["positioning"], list):
            for pos in entry["positioning"]:
                if "champion" in pos:
                    original = pos["champion"]
                    new_name = replace_english_terms(original)
                    if original != new_name:
                        pos["champion"] = new_name
                        converted = True
                
                if "items" in pos:
                    new_p_items = []
                    for p_item in pos["items"]:
                        clean_text = p_item.split(" (")[0].strip()
                        new_p_items.append(get_korean_item_name(clean_text))
                    pos["items"] = new_p_items
                    converted = True

    if converted:
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4, ensure_ascii=False)
        print(f"✅ 변환 완료: {file_path}")
    else:
        print(f"ℹ️ 변환 없음: {file_path}")

def main():
    print(f">>> '{TARGET_ROOT_FOLDER}' 스캔 시작...")
    for root, dirs, files in os.walk(TARGET_ROOT_FOLDER):
        for file in files:
            if file.endswith(".json"):
                process_file(os.path.join(root, file))
    print("\n🎉 완료.")

if __name__ == "__main__":
    main()