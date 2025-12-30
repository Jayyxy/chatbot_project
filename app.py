import streamlit as st
from page import project1 as p1
from page import project2 as p2
from page import intro

# ★ [추가 1] 챗봇 파일 불러오기 (같은 폴더에 streamlit_ollama.py가 있어야 함)
import streamlit_ollama as chatbot 

st.title('Project')

# ★ [추가 2] 메뉴 목록에 'item3' 추가
item_list = ['item0', 'item1', 'item2', 'item3']

# ★ [추가 3] 메뉴 이름에 'TFT 챗봇' 추가
item_labels = {
    'item0': '개발환경구축', 
    'item1': '스트림릿', 
    'item2': 'Diagram', 
    'item3': '🐧 TFT 챗봇'  # 원하시는 이름으로 변경 가능
}

FIL = lambda x : item_labels[x]
item = st.sidebar.selectbox('항목을 골라요.', item_list, format_func=FIL)

if item == 'item1':
    p1.app()
elif item == 'item2':
    p2.app()
elif item == 'item0':
    intro.app()
# ★ [추가 4] 챗봇 실행 로직 연결
elif item == 'item3':
    chatbot.main()