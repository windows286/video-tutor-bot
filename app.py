import streamlit as st
import google.generativeai as genai
import PyPDF2
import os
import glob

# 1. 여러 PDF 파일에서 텍스트를 추출하여 합치는 함수
@st.cache_resource
def load_all_pdfs():
    combined_text = ""
    # 현재 폴더에 있는 모든 .pdf 파일을 찾습니다.
    pdf_files = glob.glob("*.pdf")
    
    for pdf_file in pdf_files:
        try:
            with open(pdf_file, "rb") as f:
                reader = PyPDF2.PdfReader(f)
                combined_text += f"\n\n[파일 이름: {pdf_file}]\n" # 출처 구분용
                for page in reader.pages:
                    content = page.extract_text()
                    if content:
                        combined_text += content
        except Exception as e:
            st.error(f"{pdf_file} 파일을 읽는 중 오류가 발생했습니다: {e}")
            
    return combined_text

# 2. 제미나이 API 설정
API_KEY = st.secrets["GEMINI_API_KEY"]
genai.configure(api_key=API_KEY)

# 3. 모든 PDF 지식 베이스 로드
with st.spinner("지식 베이스를 구축하고 있습니다. 잠시만 기다려 주세요..."):
    all_knowledge = load_all_pdfs()

# 4. AI 모델 설정 (지시문에 모든 텍스트 포함)
system_instruction = f"""
너는 김철현 교수님의 영상 제작 과목 전담 조교야. 
학생들이 질문하면 아래 제공된 [강의 자료]를 바탕으로 아주 상세하고 친절하게 답변해줘.

[강의 자료]
{all_knowledge}

자료에 없는 내용이라면 모른다고 답하고, 교수님께 직접 여쭤보도록 안내해줘.
"""

model = genai.GenerativeModel(
    model_name="gemini-1.5-flash",
    system_instruction=system_instruction
)

# 5. 웹페이지 화면 구성
st.set_page_config(page_title="영상문법기초 AI 조교", page_icon="🎬")
st.title("🎬 영상문법기초 AI 조교")
st.caption("영상문법기초 수업 내용에 궁금한 것을 편하게 물어보세요!")

if "chat_session" not in st.session_state:
    st.session_state["chat_session"] = model.start_chat(history=[])

for message in st.session_state.chat_session.history:
    role = "assistant" if message.role == "model" else "user"
    with st.chat_message(role):
        st.markdown(message.parts[0].text)

# 6. 사용자 질문 입력 및 답변 출력
if prompt := st.chat_input("질문을 입력하세요 (예: 가장 기본 숏 3가지는 무엇인가요?)"):
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        with st.spinner("조교가 답변을 작성하고 있습니다..."):
            response = st.session_state.chat_session.send_message(prompt)
            st.markdown(response.text)
