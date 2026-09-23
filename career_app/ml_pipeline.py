# career_app/ml_pipeline.py
import os
import tempfile
from typing import List
from pydantic import BaseModel, Field
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_community.document_loaders import PyPDFLoader
from dotenv import load_dotenv

load_dotenv()

class ResumeAnalysis(BaseModel):
    extracted_skills: List[str] = Field(description="List of technical and soft skills extracted from the resume")
    target_professions: List[str] = Field(description="Top 3 suitable professions based on the extracted skills")
    skill_gaps: List[str] = Field(description="Critical industry skills missing for the target professions")
    recommended_courses: List[str] = Field(description="Names of specific SWAYAM or NPTEL courses to bridge the skill gap")

def analyze_resume(uploaded_file_bytes):
    # Ensure Windows file-lock release
    temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".pdf")
    try:
        temp_file.write(uploaded_file_bytes)
        temp_file.close()

        loader = PyPDFLoader(file_path=temp_file.name)
        docs = loader.load()
        resume_text = "\n".join([doc.page_content for doc in docs])
    finally:
        if os.path.exists(temp_file.name):
            os.remove(temp_file.name)

    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key:
        raise ValueError("GOOGLE_API_KEY environment variable is missing.")

    # Using gemini-1.5-flash for faster response and reliable structured schema parsing
    llm = ChatGoogleGenerativeAI(
        model="gemini-3.8-flash",
        google_api_key=api_key,
        temperature=0.1
    )

    structured_llm = llm.with_structured_output(ResumeAnalysis)

    prompt = f"""
    Analyze the following resume text.
    1. Extract all existing skills.
    2. Determine the top 3 suitable entry-level professions.
    3. Identify missing skills for these professions.
    4. Recommend specific SWAYAM or NPTEL courses to bridge the gaps.

    Resume Text:
    {resume_text}
    """

    return structured_llm.invoke(prompt)