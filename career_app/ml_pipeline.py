import os
import tempfile
from typing import List
from dotenv import load_dotenv
from pydantic import BaseModel, Field
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_community.document_loaders import PyPDFLoader

load_dotenv()

class ResumeAnalysis(BaseModel):
    full_name: str = Field(default="Candidate", description="Full name detected on the resume")
    target_professions: List[str] = Field(description="Top 3 recommended career roles based on resume profile")
    extracted_skills: List[str] = Field(description="Normalized list of hard and soft technical skills")
    skill_gaps: List[str] = Field(description="Critical skills required for industry entry that are missing")
    recommended_courses: List[str] = Field(description="Direct names of government or university certified courses")
    resume_improvements: List[str] = Field(description="3 actionable, specific bullet suggestions to improve resume presentation")
    interview_questions: List[str] = Field(description="5 technical and behavioral interview questions tailored to the resume")

def analyze_resume(uploaded_file_bytes: bytes) -> ResumeAnalysis:
    """Safely extracts text from uploaded PDF bytes and prompts Gemini for structured analysis."""
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
        raise ValueError("GOOGLE_API_KEY environment variable is missing in .env")

    model_name = os.getenv("GEMINI_MODEL", "gemini-3.8-flash")

    llm = ChatGoogleGenerativeAI(
        model="gemini-3.8-flash",
        google_api_key=api_key,
        temperature=0.1
    )

    structured_llm = llm.with_structured_output(ResumeAnalysis)

    prompt = f"""
    Analyze the following resume text strictly and return clean structured data.
    1. Detect the candidate's name or assign 'Student'.
    2. Determine the top 3 best matching job titles/professions.
    3. Extract all explicit skills demonstrated in the projects and experience sections.
    4. Detect 4 to 6 critical industry skill gaps needed to succeed in their primary target role.
    5. Suggest actual SWAYAM/NPTEL certified courses for those gaps.
    6. Provide 3 high-impact resume enhancement recommendations.
    7. Provide 5 realistic interview practice questions.

    Resume Content:
    {resume_text}
    """

    return structured_llm.invoke(prompt)

def calculate_opportunity_relevance(candidate_skills: List[str], target_role: str, opportunity) -> tuple[float, List[str], str]:
    """Calculates relevance score based on skill overlap and target role keyword matching."""
    opp_skills = list(opportunity.required_skills.values_list('skill_name', flat=True))
    if not opp_skills:
        # If no skills assigned, assign neutral baseline
        return 50.0, [], "General career alignment."

    c_skills_lower = {s.lower().strip() for s in candidate_skills}
    matches = [s for s in opp_skills if s.lower().strip() in c_skills_lower]

    overlap_ratio = len(matches) / max(len(opp_skills), 1)
    base_score = overlap_ratio * 70.0  # Max 70 points for direct skill match

    # Title relevance boost (up to 30 points)
    role_words = [w.lower() for w in target_role.split() if len(w) > 3]
    role_boost = 0.0
    for word in role_words:
        if word in opportunity.title.lower() or word in opportunity.description.lower():
            role_boost = 30.0
            break

    final_score = round(min(base_score + role_boost, 100.0), 1)
    reasoning = f"Matched {len(matches)} of {len(opp_skills)} required competencies ({', '.join(matches[:3])})."
    
    return final_score, matches, reasoning