import streamlit as st
import google.generativeai as genai
import fitz 
import glob
import os
import re

# 1. 수업용 PDF만 처리 (개인 교재 제외)
@st.cache_resource
def process_selected_pdfs():
    combined_text = ""
    pdf_files = glob.glob("*.pdf")
    exclude_files = ["영상문법기초 교재 기본 책.pdf"]
    
    if not os.path.exists("temp_imgs"):
        os.makedirs("temp_imgs")
    
    for pdf_file in pdf_files:
        if pdf_file in exclude_files: continue
        try:
            doc = fitz.open(pdf_file)
            for page_num, page in enumerate(doc):
                text = page.get_text()
                combined_text += f"\n\n### [문서:{pdf_file} / 페이지:{page_num + 1}] ###\n{text}\n"
                
                img_path = f"temp_imgs/{pdf_file}_p{page_num + 1}.png"
                if not os.path.exists(img_path):
                    pix = page.get_pixmap(matrix=fitz.Matrix(2, 2))
                    pix.save(img_path)
        except Exception as e:
            st.error(f"오류: {e}")
    return combined_text[:500000]

# 2. 메인 화면 구성 및 사이드바 (질문 기록 클릭 기능 유지)
st.markdown("### 🎬 영상문법기초 AI 조교")

if "selected_question_idx" not in st.session_state:
    st.session_state["selected_question_idx"] = None

with st.sidebar:
    st.markdown("### 📂 질문 기록")
    if "chat_session" in st.session_state:
        history = st.session_state.chat_session.history
        user_indices = [i for i, m in enumerate(history) if m.role == "user"]
        if user_indices:
            for i in reversed(user_indices):
                q_text = re.sub(r"\[출처:.*?/ \d+페이지\]", "", history[i].parts[0].text).strip()
                short_q = q_text[:15] + "..." if len(q_text) > 15 else q_text
                if st.button(short_q, key=f"q_btn_{i}", use_container_width=True):
                    st.session_state["selected_question_idx"] = i
        else:
            st.caption("새 대화를 시작해보세요.")
    
    if st.session_state["selected_question_idx"] is not None:
        if st.sidebar.button("🗑️ 현재 대화로 돌아가기"):
            st.session_state["selected_question_idx"] = None
            st.rerun()

# 3. AI 설정 (지시문: 본문 출처 금지 명령)
try:
    API_KEY = st.secrets["GEMINI_API_KEY"].strip()
    genai.configure(api_key=API_KEY)
    all_knowledge = process_selected_pdfs()
    
    system_instruction = f"""
    너는 김철현 교수님의 영상 제작 수업 조교야. 
    학생의 질문에 친절히 답하되, 아래 규칙을 반드시 지켜줘.

    [규칙]
    1. **절대로 답변 본문 중간에는 출처나 페이지 번호를 적지 마.**
    2. 답변이 모두 끝난 후, **맨 마지막 줄에만** 참고한 모든 페이지를 아래 형식으로 몰아서 한 번씩 적어줘.
       형식: [출처: 파일명 / X페이지] [출처: 파일명 / Y페이지]
    3. 제공된 [수업 자료]의 내용만 사용해.

    [수업 자료]
    {all_knowledge}
    """

    model = genai.GenerativeModel(
        model_name="models/gemini-flash-latest",
        system_instruction=system_instruction
    )
except Exception as e:
    st.error(f"설정 에러: {e}")
    st.stop()

# 4. 출력 함수 (본문 정화 및 하단 이미지 출력)
def display_clean_message(role, raw_text):
    with st.chat_message(role):
        # 출처 정보 추출 (이미지 표시용)
        matches = re.findall(r"\[출처:\s*(.*?)\s*/\s*(\d+)페이지\]", raw_text)
        # 본문에서 출처 텍스트 제거 (학생용 화면)
        cleaned_text = re.sub(r"\[출처:.*?/ \d+페이지\]", "", raw_text).strip()
        
        st.markdown(cleaned_text)
        
        if role == "assistant" and matches:
            # 중복 제거 후 이미지 출력
            seen = set()
            unique_matches = [x for x in matches if not (x in seen or seen.add(x))]
            for file_name, p_num in unique_matches:
                img_path = f"temp_imgs/{file_name}_p{p_num}.png"
                if os.path.exists(img_path):
                    st.image(img_path, caption=f"수업 자료 발췌: {file_name} ({p_num}p)")

# 5. 대화 표시 로직
if "chat_session" not in st.session_state:
    st.session_state["chat_session"] = model.start_chat(history=[])

if st.session_state["selected_question_idx"] is not None:
    idx = st.session_state["selected_question_idx"]
    history = st.session_state.chat_session.history
    st.info("📍 선택하신 과거 질문 내용입니다.")
    display_clean_message("user", history[idx].parts[0].text)
    display_clean_message("assistant", history[idx + 1].parts[0].text)
    st.divider()

for message in st.session_state.chat_session.history:
    display_clean_message("assistant" if message.role == "model" else "user", message.parts[0].text)

if prompt := st.chat_input("궁금한 것을 물어보세요!"):
    st.session_state["selected_question_idx"] = None
    display_clean_message("user", prompt)
    response = st.session_state.chat_session.send_message(prompt)
    display_clean_message("assistant", response.text)
