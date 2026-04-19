import streamlit as st
import google.generativeai as genai
import fitz 
import glob
import os
import re

# 1. 수업용 PDF만 처리 (개인 교재는 지식 베이스에서 아예 제외)
@st.cache_resource
def process_selected_pdfs():
    combined_text = ""
    pdf_files = glob.glob("*.pdf")
    
    # [보안] 학생들에게 공개하지 않을 개인 교재 파일명
    exclude_files = ["영상문법기초 교재 기본 책.pdf"]
    
    if not os.path.exists("temp_imgs"):
        os.makedirs("temp_imgs")
    
    for pdf_file in pdf_files:
        if pdf_file in exclude_files:
            continue
            
        try:
            doc = fitz.open(pdf_file)
            combined_text += f"\n\n[문서명 시작: {pdf_file}]\n"
            for page_num, page in enumerate(doc):
                text = page.get_text()
                # AI가 내부적으로 인덱싱할 수 있도록 지문을 남깁니다.
                combined_text += f"<{pdf_file} / {page_num + 1}페이지>\n{text}\n"
                
                img_path = f"temp_imgs/{pdf_file}_p{page_num + 1}.png"
                if not os.path.exists(img_path):
                    pix = page.get_pixmap(matrix=fitz.Matrix(2, 2))
                    pix.save(img_path)
            combined_text += f"[문서명 끝: {pdf_file}]\n"
        except Exception as e:
            st.error(f"{pdf_file} 처리 중 오류: {e}")
            
    return combined_text[:30000]

# 2. 사이드바: 지난 질문 목록 및 클릭 기능
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
                # 목록에서도 출처 텍스트가 섞여있다면 제거하고 표시
                clean_q = re.sub(r"\[출처:.*?/ \d+페이지\]", "", q_text).strip()
                short_q = clean_q[:15] + "..." if len(clean_q) > 15 else clean_q
                
                if st.button(short_q, key=f"q_btn_{i}", use_container_width=True):
                    st.session_state["selected_question_idx"] = i
        else:
            st.caption("새 대화를 시작해보세요.")
    
    if st.session_state["selected_question_idx"] is not None:
        if st.sidebar.button("🗑️ 현재 대화로 돌아가기"):
            st.session_state["selected_question_idx"] = None
            st.rerun()

# 3. 메인 화면 구성
st.markdown("### 🎬 영상문법기초 AI 조교")
st.caption("수업용 강의 자료를 바탕으로 답변해 드립니다.")

# 4. AI 설정
try:
    API_KEY = st.secrets["GEMINI_API_KEY"].strip()
    genai.configure(api_key=API_KEY)
    all_knowledge = process_selected_pdfs()
    
    # 지시문: 내부 처리용 출처를 남기되, 형식은 엄격히 유지하도록 합니다.
    system_instruction = f"""
    너는 김철현 교수님의 영상 제작 수업 조교야. 
    제공된 [수업 자료]만 분석해서 답해. '영상문법기초 교재 기본 책.pdf'는 절대 참조하지 마.
    
    모든 답변의 맨 마지막 줄에만 반드시 아래 형식을 한 번 포함해줘.
    형식: [출처: 파일명 / X페이지]
    
    [수업 자료 정보]
    {all_knowledge}
    """

    model = genai.GenerativeModel(
        model_name="models/gemini-flash-latest",
        system_instruction=system_instruction
    )
except Exception as e:
    st.error(f"설정 에러: {e}")
    st.stop()

# 5. 채팅 세션 및 출력 로직
if "chat_session" not in st.session_state:
    st.session_state["chat_session"] = model.start_chat(history=[])

# [함수] 텍스트에서 출처 정보를 읽고 그림을 띄우되, 텍스트는 숨기는 기능
def display_clean_message(role, raw_text):
    with st.chat_message(role):
        # 1. 이미지 검색용 출처 추출
        matches = re.findall(r"\[출처:\s*(.*?)\s*/\s*(\d+)페이지\]", raw_text)
        # 2. 학생에게 보여줄 텍스트에서 출처 정보 삭제
        cleaned_text = re.sub(r"\[출처:.*?/ \d+페이지\]", "", raw_text).strip()
        
        st.markdown(cleaned_text)
        
        # 3. 그림 출력 (중복 제거)
        if role == "assistant" and matches:
            for file_name, p_num in list(set(matches)):
                img_path = f"temp_imgs/{file_name}_p{p_num}.png"
                if os.path.exists(img_path):
                    st.image(img_path, caption=f"수업 자료 발췌: {file_name}")

# 과거 질문 선택 시 상단 표시
if st.session_state["selected_question_idx"] is not None:
    idx = st.session_state["selected_question_idx"]
    history = st.session_state.chat_session.history
    st.info("📍 선택하신 과거 질문 내용입니다.")
    display_clean_message("user", history[idx].parts[0].text)
    display_clean_message("assistant", history[idx + 1].parts[0].text)
    st.divider()

# 전체 대화 내역 표시
for message in st.session_state.chat_session.history:
    role = "assistant" if message.role == "model" else "user"
    display_clean_message(role, message.parts[0].text)

# 6. 새 질문 입력 처리
if prompt := st.chat_input("수업 내용 중 궁금한 것을 물어보세요!"):
    st.session_state["selected_question_idx"] = None
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        response = st.session_state.chat_session.send_message(prompt)
        display_clean_message("assistant", response.text)
