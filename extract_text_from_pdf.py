def extract_text_from_pdf(file_path):
text = ""
try:
with open(file_path, "rb") as f:
reader = PyPDF2.PdfReader(f)
for page in reader.pages:
content = page.extract_text()
if content:
text += content
except Exception:
text = "지식 베이스를 불러오는 중 오류가 발생했습니다."
return text