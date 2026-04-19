import streamlit as st
import google.generativeai as genai
import fitz 
import glob
import os
import re

# 1. PDF 처리 (제한 해제 및 구분 강화)
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
                # AI가 페이지 번호를 절대 놓치지 않도록 아주 명확하게 표시합니다.
                combined_text += f"\n\n### [문서:{pdf_file} / 페이지:{page_num + 1}] ###\n{text}\n"
                
                img_path = f"temp_imgs/{pdf_file}_p{page_num + 1}.png"
                if not os.path.exists(img_path):
                    pix = page.get_pixmap(matrix=fitz.Matrix(2, 2))
                    pix.save(img_path)
        except Exception as e:
            st.error(f"오류: {e}")
            
    # 글자 수 제한을 50만 자로 대폭 늘려 모든 교재를 다 읽게 합니다.
    return combined_text[:500000]

# 2. 메인 화면 및 사이드바 (기존과 동일)
st.markdown("### 🎬 영상문법기초 AI 조교")
if "selected_question_idx" not in st.session_state:
    st.session_state["selected_question_idx"] = None

# (사이드바 로직 생략 - 기존 코드 유지 가능)

# 3. AI 설정 (지시문 대폭 강화)
try:
    API_KEY = st.secrets["GEMINI_API_KEY"].strip()
    genai.configure(api_key=API_KEY)
    all_knowledge = process_selected_pdfs()
    
    system_instruction = f"""
    너는 김철현 교수님의 영상 제작 수업 조교야. 
    학생들의 질문에 답할 때, 각 개념(숏의 종류 등)이 설명될 때마다 반드시 그 직후에 출처를 적어줘.
    
    [규칙]
    1. 답변 본문에 각 항목마다 '[출처: 파일명 / X페이지]'를 반드시 포함해.
    2. 설명하는 내용과 그림이 일치해야 해. 엉뚱한 페이지를 적지 마.
    3. 예: "미디엄 숏은 허리 위를 찍습니다. [출처: 기초이론1.pdf / 35페이지]"
    
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

# 4. 메시지 출력 함수 (텍스트 숨김 및 이미지 다중 출력)
def display_clean_message(role, raw_text):
    with st.chat_message(role):
        # 출처 텍스트 모두 추출
        matches = re.findall(r"\[출처:\s*(.*?)\s*/\s*(\d+)페이지\]", raw_text)
        # 화면에는 텍스트 숨기기
        cleaned_text = re.sub(r"\[출처:.*?/ \d+페이지\]", "", raw_text).strip()
        st.markdown(cleaned_text)
        
        # 각 출처에 맞는 모든 이미지를 순서대로 출력
        if role == "assistant" and matches:
            # 중복 제거하되 순서는 유지
            seen = set()
            unique_matches = [x for x in matches if not (x in seen or seen.add(x))]
            
            for file_name, p_num in unique_matches:
                img_path = f"temp_imgs/{file_name}_p{p_num}.png"
                if os.path.exists(img_path):
                    st.image(img_path, caption=f"강의 자료 발췌: {file_name} ({p_num}p)")

# (이하 대화 표시 및 입력 로직 기존과 동일하게 연결)
# 5. 기존 대화 및 새 질문 처리
if "chat_session" not in st.session_state:
    st.session_state["chat_session"] = model.start_chat(history=[])

for message in st.session_state.chat_session.history:
    display_clean_message("assistant" if message.role == "model" else "user", message.parts[0].text)

if prompt := st.chat_input("질문을 입력하세요!"):
    display_clean_message("user", prompt)
    response = st.session_state.chat_session.send_message(prompt)
    display_clean_message("assistant", response.text)
