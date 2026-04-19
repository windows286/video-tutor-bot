import streamlit as st
import google.generativeai as genai

# 1. 제미나이 API 설정
API_KEY = "AIzaSyDu8dITx7gZYOSvlNLLJGR1varL5l_WWzI"
genai.configure(api_key=API_KEY)

# 2. AI 모델 및 조교 역할 설정
system_instruction = """
너는 방송영상편집 및 촬영 기법 과목의 친절하고 전문적인 AI 전담 조교야.
학생들이 프리미어 프로, 다빈치 리졸브, 카메라 세팅, 조명 등 영상 제작에 관해 질문하면 이해하기 쉽게 설명해줘.
모르는 내용은 모른다고 솔직하게 답하고, 항상 교수님(김철현 교수님)께 추가로 여쭤보라고 안내해줘.
"""

model = genai.GenerativeModel(
    model_name="gemini-1.5-flash",
    system_instruction=system_instruction
)

# 3. 웹페이지 화면 구성
st.set_page_config(page_title="영상제작실습 AI 조교", page_icon="🎬")
st.title("🎬 영상제작실습 AI 조교")
st.caption("프리미어 프로, 다빈치 리졸브, 카메라 장비 등 궁금한 것을 편하게 물어보세요!")

if "chat_session" not in st.session_state:
    st.session_state["chat_session"] = model.start_chat(history=[])

for message in st.session_state.chat_session.history:
    role = "assistant" if message.role == "model" else "user"
    with st.chat_message(role):
        st.markdown(message.parts[0].text)

# 4. 사용자 질문 입력 및 답변 출력
if prompt := st.chat_input("질문을 입력하세요 (예: 프리미어에서 컷 편집 단축키가 뭐야?)"):
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        with st.spinner("조교가 답변을 작성하고 있습니다..."):
            response = st.session_state.chat_session.send_message(prompt)
            st.markdown(response.text)