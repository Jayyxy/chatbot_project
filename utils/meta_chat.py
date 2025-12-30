import json
from langchain_community.vectorstores import FAISS
from langchain_openai import OpenAIEmbeddings
from langchain.docstore.document import Document

# 1. 데이터 로드
with open("data/meta/merged_decks.json", "r", encoding="utf-8") as f:
    deck_data = json.load(f)

with open("data/item/lolchess_items.json", "r", encoding="utf-8") as f:
    item_data = json.load(f)

# 2. 덱 데이터를 LLM이 읽기 좋은 텍스트로 변환 (Document 생성)
deck_documents = []
for deck in deck_data:
    # 챔피언 리스트를 문자열로 변환
    champs_str = ", ".join([c["name"] for c in deck.get("champions", [])])
    
    # 핵심 아이템 정보 추출 (MetaTFT 통계 or 롤체지지 가이드)
    items_str = ""
    if "champions" in deck:
        for c in deck["champions"]:
            if c.get("items"):
                items_str += f"{c['name']}({', '.join(c['items'])}), "
    
    # 검색에 걸릴 텍스트 내용 구성
    page_content = f"""
    덱 이름: {deck.get('name_kr', deck.get('name'))}
    티어: {deck.get('tier', 'Unknown')}
    평균 등수: {deck.get('avg_place', '-')}
    승률: {deck.get('win_rate', '-')}
    HOT 여부: {deck.get('is_hot', False)}
    구성 챔피언: {champs_str}
    핵심 아이템 세팅: {items_str}
    운영 가이드: {str(deck.get('guide', ''))}
    """
    
    # 메타데이터 (필터링용)
    metadata = {
        "name": deck.get("name"),
        "tier": deck.get("tier"),
        "champions": champs_str
    }
    
    deck_documents.append(Document(page_content=page_content, metadata=metadata))

# 3. 아이템 조합 정보도 Document로 변환 (아이템 질문 대응용)
item_documents = []
for item in item_data:
    # 예: "구인수의 격노검 조합법: 곡궁 + 쓸데없이 큰 지팡이"
    recipe_str = ", ".join(item.get("recipe", []))
    content = f"아이템: {item['name']} \n조합법: {recipe_str} \n효과: {item.get('effect', '')}"
    item_documents.append(Document(page_content=content, metadata={"type": "item"}))

# 4. 벡터 DB 저장 (Deck + Item 정보 모두 통합)
embeddings = OpenAIEmbeddings()
vector_store = FAISS.from_documents(deck_documents + item_documents, embeddings)
retriever = vector_store.as_retriever(search_kwargs={"k": 4}) # 관련성 높은 4개 추출