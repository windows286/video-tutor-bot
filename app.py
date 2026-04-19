import streamlit as st
import google.generativeai as genai
import fitz  # PyPDF2보다 그림 추출에 강력한 PyMuPDF
import glob
import os
import re

# 1. 모든 PDF 처리 및 이미지 생성 (문서별 구분)
@st.cache_resource
def process_all_pdfs():
    combined_text = ""
    pdf_files = glob.glob("*.pdf")
    if not os.path.exists("temp_imgs"):
        os.makedirs("temp_imgs")
    
    for pdf_file in pdf_files:
        try:
            doc = fitz.open(pdf_file)
            combined_text += f"\n\n[문서명 시작: {pdf_file}]\n"
            for page_num, page in enumerate(doc):
                text = page.get_text()
                # AI가 문서명과 페이지를 정확히 매칭하도록 지문을 남깁니다.
                combined_text += f"<{pdf_file} / {page_num + 1}페이지>\n{text}\n"
                
                # 이미지 저장 시 파일명을 포함하여 중복 방지
                img_path = f"temp_imgs/{pdf_file}_p{page_num + 1}.png"
                if not os.path.exists(img_path):
                    pix = page.get_pixmap(matrix=fitz.Matrix(2, 2))
                    pix.save(img_path)
            combined_text += f"[문서명 끝: {pdf_file}]\n"
        except Exception as e:
            st.error(f"{pdf_file} 처리 중 오류: {e}")
            
    return combined_text[:30000] # 토큰 제한 고려

# 2. 화면 구성
st.markdown("### 🎬 영상문법기초 AI 조교")
st.caption("여러 권의 강의 자료를 분석하여 정확한 시각 자료를 찾아드립니다.")

# 3. AI 설정
try:
    API_KEY = st.secrets["GEMINI_API_KEY"].strip()
    genai.configure(api_key=API_KEY)
    all_knowledge = process_all_pdfs()
    
    # 지시문: 파일명과 페이지를 동시에 말하도록 교육
    system_instruction = f"""
    너는 김철현 교수님의 영상 제작 수업 조교야. 
    자료가 여러 권이니, 답변할 때 반드시 어떤 파일의 몇 페이지인지 아래 형식으로 알려줘.
    
    형식: [출처: 파일명 / X페이지]
    예: "익스트림 롱숏은 장소를 제시합니다. [출처: 영상문법기초_2주차_기초이론1.pdf / 45페이지]"
    
    [강의 자료 정보]
    {all_knowledge}
    """

    model = genai.GenerativeModel(
        model_name="models/gemini-flash-latest",
        system_instruction=system_instruction
    )
except Exception as e:
    st.error(f"설정 에러: {e}")
    st.stop()

# 4. 채팅 기록 관리
if "chat_session" not in st.session_state:
    st.session_state["chat_session"] = model.start_chat(history=[])

for message in st.session_state.chat_session.history:
    role = "assistant" if message.role == "model" else "user"
    with st.chat_message(role):
        st.markdown(message.parts[0].text)

# 5. 질문 답변 및 이미지 매칭 출력
if prompt := st.chat_input("어떤 내용이 궁금하신가요?"):
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        response = st.session_state.chat_session.send_message(prompt)
        answer_text = response.text
        st.markdown(answer_text)
        
        # 정교한 정규식으로 [출처: 파일명 / 페이지] 추출
        # 예: [출처: 영상문법기초_2주차_기초이론1.pdf / 45페이지]
        matches = re.findall(r"\[출처:\s*(.*?)\s*/\s*(\d+)페이지\]", answer_text)
        
        if matches:
            # 중복 제거 (set 사용)
            unique_matches = list(set(matches))
            for file_name, p_num in unique_matches:
                img_path = f"temp_imgs/{file_name}_p{p_num}.png"
                if os.path.exists(img_path):
                    st.image(img_path, caption=f"출처: {file_name} ({p_num}페이지)")
                else:
                    # 혹시 파일명이 미묘하게 다를 경우를 대비한 검색
                    st.warning(f"참조된 이미지({file_name}, {p_num}p)를 찾는 중입니다...")

# --- 왼쪽 사이드바: 질문 목록 리스트 ---
with st.sidebar:
    st.markdown("### 📂 질문 기록")
    st.divider() # 가로 줄 하나 긋기
    
    if "chat_session" in st.session_state:
        # 대화 기록 중 사용자가 질문한 내용만 추출
        questions = [m.parts[0].text for m in st.session_state.chat_session.history if m.role == "user"]
        
        if not questions:
            st.caption("아직 질문 기록이 없습니다.")
        else:
            # 최근 질문이 위로 오게 하려면 reversed(questions)를 사용하세요.
            for i, q in enumerate(questions):
                # 질문이 너무 길면 잘라서 표시 (20자 제한)
                short_q = q[:20] + "..." if len(q) > 20 else q
                st.write(f"{i+1}. {short_q}")
# -----------------------------------
