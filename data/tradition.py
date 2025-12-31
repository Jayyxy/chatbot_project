import json
import os
import re

# ==========================================
# [설정] 데이터 폴더
# ==========================================
TARGET_ROOT_FOLDER = "data" 

# ==========================================
# [1] 챔피언 이름 매핑 (CHAMP_MAP)
# ==========================================
CHAMP_MAP = {
    # --- [기존 목록] ---
    "Caitlyn": "케이틀린", "Garen": "가렌", "Illaoi": "일라오이", "Jarvan IV": "자르반 4세",
    "Jax": "잭스", "Kog'Maw": "코그모", "Wukong": "오공", "Neeko": "니코", 
    "Briar": "브라이어", # 수정됨 (브라이언 -> 브라이어)
    "Poppy": "뽀삐", "Singed": "신지드", "Skarner": "스카너", "Swain": "스웨인",
    "Vi": "바이", "Volibear": "볼리베어", "Warwick": "워윅", "Galio": "갈리오", "Sion": "사이온",
    "Fizz": "피즈", "Braum": "브라움", "Lissandra": "리산드라",
    "Kennen": "케넨", "Senna": "세나", "Seraphine": "세라핀", "Shen": "쉔",
    "Taric": "타릭", "Yone": "요네", "Ahri": "아리", "Bard": "바드",
    "Ekko": "에코", "Lulu": "룰루", "Miss Fortune": "미스 포츈", "Nidalee": "니달리",
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
    "Loris": "로리스", "Zaahen": "자헨", "Brock": "브록", "Yunara": "유나라", "Tibbers": "티버",
    "Azir": "아지르", "Aurelion Sol": "아우렐리온 솔", "Aatrox": "아트록스",
    "Blitzcrank": "블리츠크랭크", "Darius": "다리우스", "Rek'Sai": "렉사이"
}

# ==========================================
# [2] 특성/시너지 매핑 (TRAIT_MAP)
# ==========================================
TRAIT_MAP = {
    # --- [제공된 데이터 기반 추가] ---
    "Brawler": "난동꾼",
    "Gunslinger": "사격수",
    "Shadowisles": "그림자 군도",
    "Explorer": "이쉬탈",      # (밀리오, 니코, 키아나 포함 특성)
    "Longshot": "백발백중",     # (저격수 계열)
    "Theboss": "우두머리",      # 세트
    "Blacksmith": "대장장이",   # 오른
    "Glutton": "대식가",        # 탐 켄치
    "Runemage": "룬 마법사",    # 라이즈
    "Caretaker": "관리자",      # 바드 (또는 정령의 친구)
    "Huntress": "사냥꾼",       # 니달리
    "Heroic": "영웅",           # 가렌/데마시아 관련
    "Chronokeeper": "시간의 수호자", # 질리언
    "Hexmech": "헥스 메카",     # 하이머딩거/T-헥스
    "Darkinweapon": "다르킨의 검", # 아트록스
    "Sylastrait": "추방자",     # 사일러스 (임의 번역)
    "Kaisaunique": "정찰대",    # 카이사 고유
    "Baronunique": "내셔 남작",
    "Aatroxunique": "세계의 종결자",
    "Aurelionsolunique": "성위", # 아우솔 고유
    "Shyvanaunique": "용의 강림",
    "Darkchild": "어둠의 아이",  # 애니
    "Empress": "여제",          # 벨베스
    
    # --- [기존 목록] ---
    "Magus": "마법사",
    "Quickstriker": "기동타격대", 
    "Defender": "엄호대",
    "Sorcerer": "비전 마법사", 
    "Arcanist": "비전 마법사",
    "Shurima": "슈리마", "Ionia": "아이오니아", "Demacia": "데마시아",
    "Freljord": "프렐요드", "Noxus": "녹서스", "Bilgewater": "빌지워터",
    "Piltover": "필트오버", "Shadow Isles": "그림자 군도", "Targon": "타곤",
    "Void": "공허", "Zaun": "자운", "Ixtal": "이쉬탈",
    "Challenger": "도전자", "Invoker": "기원자", "Slayer": "학살자",
    "Strategist": "책략가", "Bastion": "요새",
    "Bruiser": "난동꾼", "Juggernaut": "전쟁기계", "Gunner": "사격수",
    "Rogue": "불한당", "Deadeye": "백발백중", "Multicaster": "연쇄마법사",
    "Yordle": "요들", "Darkin": "다르킨", "Vanquisher": "토벌자", "Warden": "파수꾼"
}

# ==========================================
# [3] 아이템 매핑 (ITEM_MAP)
# ==========================================
ITEM_MAP = {
    # --- [제공된 데이터 기반 추가] ---
    "Striker's Flail": "타격대의 철퇴",
    "Kraken's Fury": "크라켄의 학살자", # (찬란한/오른 아이템)
    "Adaptive Helm": "적응형 투구",
    "Spirit Visage": "정령의 형상",
    "Captain's Brew": "선장의 술통",         # 빌지워터 아이템
    "Dead Man's Dagger": "망자의 단검",      # 빌지워터 아이템
    "First Mate's Flintlock": "일등항해사의 머스킷", # 빌지워터 아이템
    "Lucky Doubloon": "행운의 주화",         # 빌지워터 아이템
    "Pile O' Citrus": "귤",                 # 탐켄치/빌지워터
    "Barknuckles": "따개비 주먹",            # 빌지워터 아이템
    "Blackmarket Explosives": "암시장 폭발물", # 빌지워터 아이템
    "Tactician's Shield": "전술가의 방패",

    # --- [기존 목록] ---
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

# 모든 매핑 합치기
ALL_REPLACE_MAP = {**CHAMP_MAP, **ITEM_MAP, **TRAIT_MAP}
SORTED_KEYS = sorted(ALL_REPLACE_MAP.keys(), key=len, reverse=True)

# -----------------------------------------------------------
# [유틸] 치환 함수들
# -----------------------------------------------------------
def replace_english_terms(text):
    if not text or not isinstance(text, str):
        return text
    if not re.search(r'[a-zA-Z]', text):
        return text
    for key in SORTED_KEYS:
        pattern = re.compile(r'\b' + re.escape(key) + r'\b', re.IGNORECASE)
        if pattern.search(text):
            text = pattern.sub(ALL_REPLACE_MAP[key], text)
    return text

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

        # [1] 덱 이름 변환
        if "name" in entry:
            original = entry["name"]
            new_name = replace_english_terms(original)
            if original != new_name:
                entry["name"] = new_name
                converted = True
        
        # [2] 챔피언 이름 변환
        for k in ["champion"]:
            if k in entry and entry[k] in CHAMP_MAP:
                entry[k] = CHAMP_MAP[entry[k]]
                converted = True

        # [3] 아이템 리스트 변환 (get_korean_item_name 사용)
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

        # [4] 내부 챔피언 리스트 변환 (champions)
        if "champions" in entry and isinstance(entry["champions"], list):
            for champ in entry["champions"]:
                # 챔피언 이름
                if "name" in champ:
                    original = champ["name"]
                    new_name = replace_english_terms(original)
                    if original != new_name:
                        champ["name"] = new_name
                        converted = True
                # 아이템 리스트
                if "items" in champ:
                    new_items = []
                    for c_item in champ["items"]:
                         clean_text = c_item.split(" (")[0].strip()
                         # 아이템은 replace_english_terms보다 get_korean_item_name이 우선
                         new_items.append(get_korean_item_name(clean_text))
                    champ["items"] = new_items
                    converted = True

        # [5] 시너지(Synergies) 리스트 변환
        if "synergies" in entry and isinstance(entry["synergies"], list):
            for synergy in entry["synergies"]:
                if "name" in synergy:
                    original = synergy["name"]
                    # 특성 이름은 replace_english_terms로 처리
                    new_name = replace_english_terms(original)
                    if original != new_name:
                        synergy["name"] = new_name
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