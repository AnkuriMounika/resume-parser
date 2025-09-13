from fastapi import FastAPI, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
import os
import re
import PyPDF2
import docx

app = FastAPI()

# Allow frontend requests later
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

UPLOAD_DIR = "../uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)


# --- Utility functions ---
def extract_text_from_pdf(file_path):
    text = ""
    with open(file_path, "rb") as f:
        reader = PyPDF2.PdfReader(f)
        for page in reader.pages:
            text += page.extract_text() + "\n"
    return text


def extract_text_from_docx(file_path):
    doc = docx.Document(file_path)
    return "\n".join([para.text for para in doc.paragraphs])


def parse_resume(text):
    """Extracts structured data from raw text"""
    data = {}

    # Name (very simple heuristic: first line)
    lines = text.strip().split("\n")
    data["name"] = lines[0].strip() if lines else ""

    # Email
    email_match = re.search(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-z]{2,}", text)
    data["email"] = email_match.group(0) if email_match else ""

    # Phone
    phone_match = re.search(r"\+?\d[\d\s-]{8,15}", text)
    data["phone"] = phone_match.group(0) if phone_match else ""

    # Skills (basic keyword match — later we can enhance with LLM)
    skills_list = ["python", "java", "c++", "react", "node.js", "sql", "html", "css", "javascript"]
    found_skills = [skill for skill in skills_list if skill.lower() in text.lower()]
    data["skills"] = list(set(found_skills))

    # Education
    education_keywords = ["b.tech", "m.tech", "bachelor", "master", "phd", "degree", "university", "college"]
    edu_matches = [line for line in lines if any(kw in line.lower() for kw in education_keywords)]
    data["education"] = edu_matches

    # Experience
    exp_keywords = ["experience", "intern", "developer", "engineer", "company", "work"]
    exp_matches = [line for line in lines if any(kw in line.lower() for kw in exp_keywords)]
    data["experience"] = exp_matches

    return data


# --- Routes ---
@app.get("/")
def root():
    return {"message": "Resume Parser API is running 🚀"}


@app.post("/upload_resume/")
async def upload_resume(file: UploadFile = File(...)):
    # Save file
    file_path = os.path.join(UPLOAD_DIR, file.filename)
    with open(file_path, "wb") as f:
        f.write(await file.read())

    # Extract text
    if file.filename.endswith(".pdf"):
        text = extract_text_from_pdf(file_path)
    elif file.filename.endswith(".docx"):
        text = extract_text_from_docx(file_path)
    else:
        return {"error": "Only PDF and DOCX formats are supported."}

    # Parse structured data
    parsed_data = parse_resume(text)

    return {
        "file_name": file.filename,
        "extracted_text_preview": text[:500],  # first 500 chars
        "parsed_data": parsed_data,
    }
