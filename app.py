import streamlit as st
import google.generativeai as genai
import PyPDF2
import glob

# 1. PDF 텍스트 추출 함수 (캐싱 적용으로 속도 향상)
@st.cache_resource
def load_all_pdfs():
    combined_text = ""
    pdf_files = glob.glob("*.pdf")
    for pdf_file in pdf_files:
        try:
            with open(pdf_file, "rb") as f:
                reader = PyPDF2.PdfReader(f)
                for page in reader.pages:
                    content = page.extract_text()
                    if content:
                        combined_text += content
        except Exception:
            continue
    # 텍스트가 너무 길면 API 오류가 날 수 있으므로 적절히 제한 (약 3만 자)
    return combined_text[:30000]

# 2. 웹페이지 기본 설정
st.set_page_config(page_title="영상문법기초 AI 조교", page_icon="🎬")
st.title("🎬 영상문법기초 AI 조교")
st.caption("영상문법기초 수업 내용에 궁금한 것을 편하게 물어보세요!")

# 3. 제미나이 API 및 지식 베이스 설정
try:
    # Secrets에서 키 가져오기 (공백 주의!)
    API_KEY = st.secrets["GEMINI_API_KEY"].strip()
    genai.configure(api_key=API_KEY)
    
    with st.spinner("강의 자료를 분석하고 있습니다..."):
        all_knowledge = load_all_pdfs()
    
    if not all_knowledge.strip():
        all_knowledge = "강의 자료 PDF 파일을 찾지 못했습니다. 일반적인 영상 제작 지식으로 답변해줘."

    # 모델 설정 (가장 안정적인 모델 이름으로 통일)
    # 404 에러를 피하기 위해 이름 앞에 'models/'를 붙이지 않습니다.
    model = genai.GenerativeModel(
        model_name="gemini-1.5-flash-latest", 
        system_instruction=f"너는 김철현 교수님의 영상 제작 과목 전담 조교야. 아래 자료를 바탕으로 친절하게 답해줘: {all_knowledge}"
    )
except Exception as e:
    st.error(f"설정 중 오류가 발생했습니다: {e}")
    st.stop()

# 4. 채팅 세션 초기화
if "chat_session" not in st.session_state:
    st.session_state["chat_session"] = model.start_chat(history=[])

# 5. 기존 대화 내용 표시
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
            try:
                response = st.session_state.chat_session.send_message(prompt)
                st.markdown(response.text)
            except Exception as e:
                st.error(f"답변 생성 중 오류가 발생했습니다. 상세 에러: {e}")
