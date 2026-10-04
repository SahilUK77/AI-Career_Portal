import logging
import os
import tempfile

from dotenv import load_dotenv
from langchain_community.document_loaders import PyPDFLoader
from langchain_google_genai import ChatGoogleGenerativeAI
from pydantic import BaseModel, Field

from .local_nlp import LocalNLPResumeParser

logger = logging.getLogger(__name__)
load_dotenv()


class ResumeAnalysis(BaseModel):
    full_name: str = Field(
        default="Candidate", description="Full name detected on the resume"
    )
    target_professions: list[str] = Field(
        description="Top 5 recommended career roles based on resume profile"
    )
    extracted_skills: list[str] = Field(
        description="Normalized list of hard and soft technical skills"
    )
    skill_gaps: list[str] = Field(
        description="Critical skills required for industry entry that are missing"
    )
    recommended_courses: list[str] = Field(
        description="Direct names of government or university certified courses"
    )
    resume_improvements: list[str] = Field(
        description="5 actionable, specific bullet suggestions to improve resume presentation"
    )
    interview_questions: list[str] = Field(
        description="10 technical and behavioral interview questions tailored to the resume"
    )
    summary: str = Field(
        default="", description="A short professional summary of the candidate"
    )
    projects: list[str] = Field(
        default=[], description="List of projects mentioned in the resume"
    )
    experience: list[str] = Field(
        default=[], description="List of work experiences or internships"
    )
    academic_records: list[dict] = Field(
        default=[],
        description="List of dicts containing degree, institution, graduation_year, and cgpa",
    )


def _analyze_resume_locally(resume_text: str) -> ResumeAnalysis:
    parser = LocalNLPResumeParser(resume_text)
    skills = parser.extract_skills()
    target_roles = parser.determine_roles(skills)
    primary_role = target_roles[0] if target_roles else "Junior Analyst"
    skill_gaps, courses = parser.find_gaps_and_courses(primary_role, skills)

    return ResumeAnalysis(
        full_name=parser.extract_name(),
        target_professions=target_roles[:5],
        extracted_skills=skills,
        skill_gaps=skill_gaps[:5],
        recommended_courses=courses[:5],
        resume_improvements=parser.get_improvements(skill_gaps)[:5],
        interview_questions=parser.generate_interview_qs(primary_role),
        summary=parser.extract_summary(),
        projects=parser.extract_projects(),
        experience=parser.extract_experience(),
        academic_records=parser.extract_academic_records(),
    )


def analyze_resume(uploaded_file_bytes: bytes) -> ResumeAnalysis:
    """Safely extracts text from uploaded PDF bytes and prompts Gemini for structured analysis. Fallbacks to local NLP model."""
    temp_path = None
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as temp_file:
            temp_file.write(uploaded_file_bytes)
            temp_path = temp_file.name

        loader = PyPDFLoader(file_path=temp_path)
        docs = loader.load()
        resume_text = "\n".join([doc.page_content for doc in docs])
    finally:
        if temp_path and os.path.exists(temp_path):
            os.remove(temp_path)

    api_key = os.getenv("GOOGLE_API_KEY")

    if not api_key:
        logger.info("GOOGLE_API_KEY is unavailable; using local resume analysis")
        return _analyze_resume_locally(resume_text)

    try:
        model_name = os.getenv("GEMINI_MODEL", "gemini-1.5-flash")
        llm = ChatGoogleGenerativeAI(
            model=model_name,
            google_api_key=api_key,
            temperature=0.1,
            max_retries=3,
        )
        structured_llm = llm.with_structured_output(ResumeAnalysis)
        prompt = f"""
        Analyze the following resume text strictly and return clean structured data.
        1. Detect the candidate's name or assign 'Student'.
        2. Determine the top 5 best matching job titles/professions.
        3. Extract all explicit skills demonstrated in the projects and experience sections.
        4. Detect 5 to 10 critical industry skill gaps needed to succeed in their primary target role.
        5. Suggest actual SWAYAM/NPTEL certified courses for those gaps.
        6. Provide 5 high-impact resume enhancement recommendations, specifically including actionable improvements for their profile summary and projects.
        7. Provide exactly 5 realistic technical and behavioral interview practice questions.
        8. Extract a short professional summary.
        9. Extract all project details.
        10. Extract all work experience.
        11. Extract all academic records (degree, institution, graduation_year, cgpa).

        Resume Content:
        {resume_text}
        """
        return structured_llm.invoke(prompt)
    except Exception as e:  # noqa: BLE001
        logger.warning(
            "External resume analysis unavailable; using local fallback: %s", e
        )
        return _analyze_resume_locally(resume_text)


def calculate_opportunity_relevance(
    candidate_skills: list[str], target_role: str, opportunity
) -> tuple[float, list[str], str]:
    """Calculates relevance score based on skill overlap and target role keyword matching."""
    opp_skills = list(opportunity.required_skills.values_list("skill_name", flat=True))
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
