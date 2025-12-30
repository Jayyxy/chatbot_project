import streamlit as st
from langchain_openai import ChatOpenAI 
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnablePassthrough

# 모듈 가져오기
from utils.rag_engine import build_retriever
from utils.prompts import get_prompt_by_mode
from dotenv import load_dotenv  # [수정 2] 환경변수 로드

load_dotenv()

# 페이지 설정
st.set_page_config(page_title="TFT AI 덱 추천", page_icon="🐧")

# [1] 리소스 캐싱 (새로고침 때마다 DB 다시 만들지 않도록)
@st.cache_resource
def get_retriever():
    return build_retriever()

retriever = get_retriever()

# [2] 사이드바 & 세션 상태 초기화
def init_session():
    if "messages" not in st.session_state:
        st.session_state.messages = []
    if "mode" not in st.session_state:
        st.session_state.mode = "general" # 기본 모드
    if "sub_mode" not in st.session_state:
        st.session_state.sub_mode = None

init_session()

# [3] RAG 체인 실행 함수
# [수정 3] run_rag_chain 함수 내부 모델 변경
def run_rag_chain(user_input, mode, sub_mode):
    # 1. Retriever 확인
    if retriever is None:
        yield "⚠️ [시스템 오류] 데이터 파일이 로드되지 않았습니다."
        return

    # 2. 에러 핸들링을 위한 try-except 블록
    try:
        # 모델 설정 (GPT-4o-mini)
        llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)
        
        # 프롬프트 가져오기
        prompt_template = get_prompt_by_mode(mode, sub_mode)
        
        def format_docs(docs):
            # 검색된 문서가 없으면 빈 문자열 반환
            if not docs:
                return "검색된 관련 정보가 없습니다."
            return "\n\n".join([d.page_content for d in docs])

        # 체인 구성
        chain = (
            {"context": retriever | format_docs, "question": RunnablePassthrough()}
            | prompt_template
            | llm
            | StrOutputParser()
        )
        
        # 스트리밍 실행 (여기서 에러가 나면 except로 넘어감)
        for chunk in chain.stream(user_input):
            yield chunk

    except Exception as e:
        # 에러 내용을 화면에 출력
        error_message = str(e)
        
        if "401" in error_message:
            yield "🚨 [인증 오류] API Key가 틀렸습니다. .env 파일을 확인하세요."
        elif "429" in error_message:
            yield "💸 [결제 오류] OpenAI 계정의 잔액(Credit)이 부족합니다. 결제 정보를 등록했는지 확인하세요."
        elif "not found" in error_message:
            yield "❌ [모델 오류] 모델 이름을 찾을 수 없습니다. (gpt-4o-mini 철자 확인)"
        else:
            yield f"⚠️ [알 수 없는 오류 발생] \n\n{error_message}"
            
# [4] 메인 UI 구성
def main():
    st.title("🐧 TFT 롤체 도우미 (RAG)")
    
    # --- 모드 선택 버튼 영역 ---
    st.markdown("### 무엇을 도와드릴까요?")
    col1, col2, col3 = st.columns(3)
    
    if col1.button("🃏 덱 추천", use_container_width=True):
        st.session_state.mode = "deck_rec"
        st.session_state.sub_mode = "champion" # 기본값
        
    if col2.button("⚔️ 아이템 추천", use_container_width=True):
        st.session_state.mode = "item_rec"
        st.session_state.sub_mode = "champion"
        
    if col3.button("💎 증강 추천", use_container_width=True):
        st.session_state.mode = "augment_rec"
        st.session_state.sub_mode = None

    # --- 세부 상황 선택 (Radio Button) ---
    if st.session_state.mode == "deck_rec":
        st.info("현재 모드: **덱 추천**")
        st.session_state.sub_mode = st.radio(
            "어떤 상황인가요?",
            ["챔피언 기반 (잘 뜬 기물)", "아이템 기반 (보유 아이템)", "상징/특성 기반"],
            horizontal=True
        )
    elif st.session_state.mode == "item_rec":
        st.info("현재 모드: **아이템 추천**")
        st.session_state.sub_mode = st.radio(
            "어떤 상황인가요?",
            ["특정 챔피언에게 줄 아이템", "현재 덱에 남는 아이템 처리"],
            horizontal=True
        )
    elif st.session_state.mode == "augment_rec":
        st.info("현재 모드: **증강체 추천**")

    st.divider()

    # --- 채팅 인터페이스 ---
    # 1. 이전 대화 출력
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    # 2. 사용자 입력 처리
    if prompt := st.chat_input("질문을 입력하세요..."):
        # 사용자 메시지 표시
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        # AI 답변 생성
        with st.chat_message("assistant"):
            response_placeholder = st.empty()
            full_response = ""
            
            # 스트리밍으로 답변 받아오기
            mode = st.session_state.mode
            sub = st.session_state.sub_mode
            
            # RAG 실행
            stream = run_rag_chain(prompt, mode, sub)
            
            for chunk in stream:
                full_response += chunk
                response_placeholder.markdown(full_response + "▌")
            
            response_placeholder.markdown(full_response)
        
        # 대화 저장
        st.session_state.messages.append({"role": "assistant", "content": full_response})

if __name__ == '__main__':
    main()