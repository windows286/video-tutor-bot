import streamlit as st
import google.generativeai as genai
import fitz  # PyMuPDF
import glob
import os

# 1. PDF에서 텍스트 추출 및 페이지를 이미지로 변환 (캐싱)
@st.cache_resource
def process_pdfs():
    combined_text = ""
    pdf_files = glob.glob("*.pdf")
    
    # 이미지 저장용 폴더 생성
    if not os.path.exists("temp_imgs"):
        os.makedirs("temp_imgs")
    
    for pdf_file in pdf_files:
        doc = fitz.open(pdf_file)
        combined_text += f"\n\n[파일: {pdf_file}]\n"
        
        for page_num, page in enumerate(doc):
            # 텍스트 추출 (조교가 페이지 번호를 알 수 있게 표기)
            text = page.get_text()
            combined_text += f"--- [페이지 {page_num + 1}] ---\n{text}\n"
            
            # 페이지를 이미지로 저장 (나중에 불러올 용도)
            pix = page.get_pixmap(matrix=fitz.Matrix(2, 2)) # 화질 2배
            pix.save(f"temp_imgs/{pdf_file}_page_{page_num + 1}.png")
            
    return combined_text[:30000]

# 2. 설정 및 조교 교육
st.set_page_config(page_title="영상문법기초 AI 조교", page_icon="🎬")
st.title("🎬 영상문법기초 AI 조교 (시각 자료 지원)")

try:
    API_KEY = st.secrets["GEMINI_API_KEY"].strip()
    genai.configure(api_key=API_KEY)
    
    all_knowledge = process_pdfs()
    
    # 조교에게 페이지 번호를 반드시 언급하라고 강력하게 지시합니다.
    system_instruction = f"""
    너는 김철현 교수님의 영상 제작 수업 조교야. 
    반드시 아래 제공된 [강의 자료]를 바탕으로 답해줘.
    
    **중요 지시**: 설명하는 내용이 특정 페이지에 있다면, 답변 끝에 반드시 "[페이지 번호]" 형식으로 적어줘.
    예: "익스트림 롱숏은 장소를 제시하는 목적으로 쓰입니다. [페이지 45]"
    
    [강의 자료]
    {all_knowledge}
    """

    model = genai.GenerativeModel(
        model_name="models/gemini-flash-latest",
        system_instruction=system_instruction
    )
except Exception as e:
    st.error(f"설정 에러: {e}")
    st.stop()

# 3. 채팅 로직
if "chat_session" not in st.session_state:
    st.session_state["chat_session"] = model.start_chat(history=[])

for message in st.session_state.chat_session.history:
    role = "assistant" if message.role == "model" else "user"
    with st.chat_message(role):
        st.markdown(message.parts[0].text)

if prompt := st.chat_input("궁금한 것을 물어보세요!"):
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        response = st.session_state.chat_session.send_message(prompt)
        answer_text = response.text
        st.markdown(answer_text)
        
        # 답변에서 [페이지 X] 형식을 찾아 해당 이미지 출력
        import re
        page_matches = re.findall(r"\[페이지 (\d+)\]", answer_text)
        if page_matches:
            for p_num in page_matches:
                # 첫 번째 PDF 파일의 해당 페이지 이미지를 찾아서 표시
                pdf_name = glob.glob("*.pdf")[0] # 첫 번째 PDF 기준
                img_path = f"temp_imgs/{pdf_name}_page_{p_num}.png"
                if os.path.exists(img_path):
                    st.image(img_path, caption=f"강의 자료 {p_num}페이지 발췌")
