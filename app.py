import streamlit as st
import google.generativeai as genai
import PyPDF2  # 이미지 처리가 없으므로 다시 가벼운 라이브러리로 변경
import glob
import os
import re

# 1. 수업용 PDF 텍스트만 추출 (개인 교재 제외)
@st.cache_resource
def process_text_from_pdfs():
    combined_text = ""
    pdf_files = glob.glob("*.pdf")
    
    # [보안] 분석에서 제외할 개인 교재 파일명
    exclude_files = ["영상문법기초 교재 기본 책.pdf"]
    
    for pdf_file in pdf_files:
        if pdf_file in exclude_files:
            continue
            
        try:
            with open(pdf_file, "rb") as f:
                reader = PyPDF2.PdfReader(f)
                combined_text += f"\n\n[파일: {pdf_file}]\n"
                for i, page in enumerate(reader.pages):
                    content = page.extract_text()
                    if content:
                        combined_text += f"<{i+1}페이지>\n{content}\n"
        except Exception:
            continue
            
    # AI가 한 번에 읽을 수 있는 양으로 조절 (약 10만 자)
    return combined_text[:100000]

# 2. 사이드바: 질문 기록 리스트 (클릭 시 확인 가능)
if "selected_question_idx" not in st.session_state:
    st.session_state["selected_question_idx"] = None

with st.sidebar:
    st.markdown("### 📂 질문 기록")
    if "chat_session" in st.session_state:
        history = st.session_state.chat_session.history
        user_indices = [i for i, m in enumerate(history) if m.role == "user"]
        
        if user_indices:
            for i in reversed(user_indices):
                q_text = history[i].parts[0].text
                short_q = q_text[:15] + "..." if len(q_text) > 15 else q_text
                
                if st.button(short_q, key=f"q_btn_{i}", use_container_width=True):
                    st.session_state["selected_question_idx"] = i
        else:
            st.caption("새 대화를 시작해보세요.")
    
    if st.session_state["selected_question_idx"] is not None:
        if st.sidebar.button("🗑️ 현재 대화로 돌아가기"):
            st.session_state["selected_question_idx"] = None
            st.rerun()

# 3. 메인 화면 구성 (교수님 요청대로 적당한 크기)
st.markdown("### 🎬 영상문법기초 AI 조교")
st.caption("강의 자료를 바탕으로 정확한 이론을 설명해 드립니다.")

# 4. AI 설정
try:
    API_KEY = st.secrets["GEMINI_API_KEY"].strip()
    genai.configure(api_key=API_KEY)
    all_knowledge = process_text_from_pdfs()
    
    # 지시문: 텍스트 답변에만 집중하도록 설정
    # 교수님 요청사항: ** 사용 금지, 볼드체/이텔릭체/언더라인 활용
    system_instruction = f"""
    너는 김철현 교수님의 영상 제작 수업 조교야. 
    제공된 [수업 자료]의 텍스트만 분석해서 친절하고 정확하게 답해줘.
    
    [답변 규칙]
    1. 강조할 때는 **(별표 두개)를 쓰지 마.** 2. 대신 HTML 태그를 사용해: <b>굵게</b>, <i>이텔릭</i>, <u>밑줄</u>을 사용해서 강조해줘.
    3. 모르는 내용은 솔직하게 모른다고 답해.
    4. 출처 페이지 번호는 답변 본문에 직접 쓰지 말고, 필요한 경우에만 문맥에 맞게 언급해.
    
    [수업 자료]
    {all_knowledge}
    """

    model = genai.GenerativeModel(
        model_name="models/gemini-1.5-flash", # 안정적인 최신 모델
        system_instruction=system_instruction
    )
except Exception as e:
    st.error(f"설정 에러: {e}")
    st.stop()

# 5. 채팅 기록 관리 및 출력
if "chat_session" not in st.session_state:
    st.session_state["chat_session"] = model.start_chat(history=[])

# 과거 질문 선택 시 표시
if st.session_state["selected_question_idx"] is not None:
    idx = st.session_state["selected_question_idx"]
    history = st.session_state.chat_session.history
    st.info("📍 선택하신 과거 질문입니다.")
    with st.chat_message("user"):
        st.write(history[idx].parts[0].text)
    with st.chat_message("assistant"):
        st.write(history[idx + 1].parts[0].text)
    st.divider()

# 전체 대화 표시
for message in st.session_state.chat_session.history:
    role = "assistant" if message.role == "model" else "user"
    with st.chat_message(role):
        st.write(message.parts[0].text)

# 6. 질문 처리
if prompt := st.chat_input("수업 내용 중 궁금한 것을 물어보세요!"):
    st.session_state["selected_question_idx"] = None
    with st.chat_message("user"):
        st.write(prompt)

    with st.chat_message("assistant"):
        response = st.session_state.chat_session.send_message(prompt)
        st.write(response.text)
