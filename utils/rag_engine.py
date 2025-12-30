# utils/rag_engine.py

import json
import os
from langchain_community.vectorstores import FAISS
from langchain_openai import OpenAIEmbeddings
from langchain_core.documents import Document

from dotenv import load_dotenv
load_dotenv()

# [디버깅] 키가 잘 로드됐는지 확인 (로그에 출력됨)
if not os.environ.get("OPENAI_API_KEY"):
    print("❌ [오류] OPENAI_API_KEY가 없습니다! .env 파일을 확인하세요.")
else:
    print("✅ [성공] API Key 로드 완료")

# 경로 설정
DECK_FILE = "data/meta/merged_decks.json"
ITEM_FILE = "data/item/lolchess_items.json"
CHAMP_FILE = "data/champion/champion_data.json" # ★ 병합된 챔피언 파일 추가

def load_data_as_documents():
    docs = []
    
    # [1] 덱 데이터 로드 (기존과 동일)
    if os.path.exists(DECK_FILE):
        with open(DECK_FILE, "r", encoding="utf-8") as f:
            decks = json.load(f)
        for d in decks:
            champs = ", ".join([c["name"] for c in d.get("champions", [])])
            content = f"""
            [덱 정보]
            이름: {d.get('name_kr', d.get('name'))}
            티어: {d.get('tier', '-')} | 승률: {d.get('win_rate', '-')}
            HOT: {d.get('is_hot')}
            챔피언: {champs}
            가이드: {d.get('guide', {})}
            """
            docs.append(Document(page_content=content, metadata={"type": "deck"}))

    # [2] 아이템 데이터 로드 (기존과 동일)
    if os.path.exists(ITEM_FILE):
        with open(ITEM_FILE, "r", encoding="utf-8") as f:
            items = json.load(f)
        for i in items:
            content = f"[아이템 정보] 이름: {i['name']} \n조합: {', '.join(i.get('recipe', []))} \n효과: {i.get('effect')}"
            docs.append(Document(page_content=content, metadata={"type": "item"}))

    # [3] ★ 챔피언 데이터 로드 (신규 추가) ★
    if os.path.exists(CHAMP_FILE):
        with open(CHAMP_FILE, "r", encoding="utf-8") as f:
            champs_data = json.load(f)
        
        for c in champs_data:
            # LLM이 읽을 핵심 텍스트 구성
            content = f"""
            [챔피언 정보]
            이름: {c.get('name')}
            비용(Cost): {c.get('cost')}코스트
            특성(Traits): {', '.join(c.get('traits', []))}
            통계 티어: {c.get('tier')} (평균등수: {c.get('avg_place')})
            추천 아이템: {', '.join(c.get('popular_items', []))}
            """
            # 메타데이터에 이름을 넣어두면 검색 정확도 향상
            docs.append(Document(page_content=content, metadata={"type": "champion", "name": c.get('name')}))
            
    return docs

# (build_retriever 함수는 기존과 동일)
def build_retriever():
    docs = load_data_as_documents()
    if not docs: return None
    embeddings = OpenAIEmbeddings()
    vectorstore = FAISS.from_documents(docs, embeddings)
    return vectorstore.as_retriever(search_kwargs={"k": 5}) # 검색 개수를 5개로 늘림