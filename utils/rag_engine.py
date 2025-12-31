# utils/rag_engine.py

import json
import os
from langchain_community.vectorstores import FAISS
from langchain_openai import OpenAIEmbeddings
from langchain_core.documents import Document
from langchain_core.runnables import RunnableLambda # ★ 추가됨: 커스텀 검색기용

from dotenv import load_dotenv
load_dotenv()

if not os.environ.get("OPENAI_API_KEY"):
    print("❌ [오류] OPENAI_API_KEY가 없습니다! .env 파일을 확인하세요.")
else:
    print("✅ [성공] API Key 로드 완료")

# 경로 설정
DECK_FILE = "data/meta/merged_decks.json"
ITEM_FILE = "data/item/lolchess_items.json"
CHAMP_FILE = "data/champion/champion_data.json"

# =================================================================
# [1] 전역 데이터 로드 (키워드 검색용 Raw Data)
# =================================================================
# 문서를 매번 로드하지 않고 메모리에 캐싱해둡니다.
RAW_DECKS = []
if os.path.exists(DECK_FILE):
    with open(DECK_FILE, "r", encoding="utf-8") as f:
        RAW_DECKS = json.load(f)

def load_data_as_documents():
    """벡터 DB 생성을 위한 문서(Document) 리스트 변환"""
    docs = []
    
    # 1. 덱 데이터 (RAW_DECKS 활용)
    for d in RAW_DECKS:
        champs = ", ".join([c["name"] for c in d.get("champions", [])])
        # ★ 검색 정확도를 위해 시너지 정보도 텍스트에 포함
        synergies = ", ".join([f"{s['name']}({s['count']})" for s in d.get("synergies", [])])
        
        content = f"""
        [덱 정보]
        이름: {d.get('name_kr', d.get('name'))}
        티어: {d.get('tier', '-')} | 승률: {d.get('win_rate', '-')} | 평균등수: {d.get('avg_place', '-')}
        HOT: {d.get('is_hot')}
        시너지: {synergies}
        챔피언: {champs}
        가이드: {d.get('guide', {})}
        """
        docs.append(Document(page_content=content, metadata={"type": "deck"}))

    # 2. 아이템 데이터
    if os.path.exists(ITEM_FILE):
        with open(ITEM_FILE, "r", encoding="utf-8") as f:
            items = json.load(f)
        for i in items:
            content = f"[아이템 정보] 이름: {i['name']} \n조합: {', '.join(i.get('recipe', []))} \n효과: {i.get('effect')}"
            docs.append(Document(page_content=content, metadata={"type": "item"}))

    # 3. 챔피언 데이터
    if os.path.exists(CHAMP_FILE):
        with open(CHAMP_FILE, "r", encoding="utf-8") as f:
            champs_data = json.load(f)
        for c in champs_data:
            content = f"""
            [챔피언 정보]
            이름: {c.get('name')}
            비용: {c.get('cost')}코스트
            특성: {', '.join(c.get('traits', []))}
            티어: {c.get('tier')}
            추천템: {', '.join(c.get('popular_items', []))}
            """
            docs.append(Document(page_content=content, metadata={"type": "champion", "name": c.get('name')}))
            
    return docs

# =================================================================
# [2] 하이브리드 검색 로직 (키워드 + 벡터)
# =================================================================
def build_retriever():
    """
    벡터 검색(유사도)과 키워드 검색(정확도)을 결합한 하이브리드 검색기를 반환합니다.
    """
    # 1. 벡터 저장소 빌드 (기존 로직)
    docs = load_data_as_documents()
    if not docs: return None
    
    embeddings = OpenAIEmbeddings()
    vectorstore = FAISS.from_documents(docs, embeddings)
    base_retriever = vectorstore.as_retriever(search_kwargs={"k": 3}) # 벡터는 상위 3개만

    # 2. 키워드 검색 함수 정의
    def keyword_search_decks(query):
        """질문에 포함된 챔피언/덱 이름이 있으면 해당 덱을 강제로 찾아냅니다."""
        matched_docs = []
        query = query.replace(" ", "") # 띄어쓰기 무시 (예: 밀리오덱 -> 밀리오)
        
        for d in RAW_DECKS:
            # 검색 조건: 덱 이름(KR) 또는 챔피언 리스트에 검색어가 포함되는가?
            deck_name = d.get('name_kr', '').replace(" ", "")
            champ_names = [c['name'] for c in d.get('champions', [])]
            
            is_match = False
            # 1) 덱 이름 매칭
            if deck_name and deck_name in query:
                is_match = True
            # 2) 챔피언 이름 매칭
            else:
                for c_name in champ_names:
                    if c_name in query: # 예: query="밀리오덱추천", c_name="밀리오"
                        is_match = True
                        break
            
            if is_match:
                # Document 형태로 변환 (load_data_as_documents와 형식 통일)
                champs = ", ".join([c["name"] for c in d.get("champions", [])])
                synergies = ", ".join([f"{s['name']}({s['count']})" for s in d.get("synergies", [])])
                content = f"""
                [덱 정보 (키워드 매칭됨)]
                이름: {d.get('name_kr', d.get('name'))}
                티어: {d.get('tier', '-')} | 승률: {d.get('win_rate', '-')}
                시너지: {synergies}
                챔피언: {champs}
                가이드: {d.get('guide', {})}
                """
                matched_docs.append(Document(page_content=content, metadata={"type": "deck", "source": "keyword"}))
        
        return matched_docs

    # 3. 하이브리드 검색 실행 함수 (RunnableLambda용)
    def hybrid_search(query):
        # A. 키워드로 덱 찾기 (우선순위 높음)
        keyword_results = keyword_search_decks(query)
        
        # B. 벡터로 의미 검색 (보조)
        vector_results = base_retriever.invoke(query)
        
        # C. 결과 병합 (중복 제거 로직은 간단히 생략, 키워드 결과가 앞에 오도록)
        # 키워드로 찾은게 있으면 그걸 최우선으로 보여줌
        if keyword_results:
            print(f"🔍 [Hybrid] 키워드 매칭 성공: {len(keyword_results)}개 덱")
            return keyword_results + vector_results
        
        return vector_results

    # LangChain 체인에 바로 끼울 수 있도록 Runnable로 반환
    return RunnableLambda(hybrid_search)