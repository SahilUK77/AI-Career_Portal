import logging
import os
import re
from collections import Counter

from .models import (
    CareerRole,
    CourseRecommendation,
    InterviewQuestion,
    RoleSkill,
)

# Suppress HuggingFace and Transformers Warnings
os.environ["HF_HUB_DISABLE_SYMLINKS_WARNING"] = "1"
os.environ["TRANSFORMERS_NO_ADVISORY_WARNINGS"] = "1"

logger = logging.getLogger(__name__)

# Initialize ML Pipelines lazily so they don't block server startup
_nlp = None
_zero_shot = None
_sentence_model = None


def generate_local_cover_letter(profile, opportunity) -> str:
    candidate_skills = [skill.strip() for skill in profile.current_skills if skill]
    description = opportunity.description or ""
    matched_skills = [
        skill for skill in candidate_skills if skill.lower() in description.lower()
    ]
    highlighted_skills = matched_skills or candidate_skills[:4]
    skills_text = (
        ", ".join(highlighted_skills) or "relevant technical and collaborative skills"
    )
    candidate_name = profile.full_name or "Candidate"

    body = "These capabilities align with the opportunity's requirements and would allow me to contribute from the beginning."
    if profile.experience and len(profile.experience) > 0:
        clean_exp = str(profile.experience[0])[:150].replace("\n", " ")
        body = f"As demonstrated by my previous experience ({clean_exp}), I have consistently applied these skills to deliver results."
    elif profile.projects and len(profile.projects) > 0:
        clean_proj = str(profile.projects[0])[:150].replace("\n", " ")
        body = f"For instance, in a recent project ({clean_proj}), I applied my skills to solve complex problems and deliver a complete solution."

    return (
        f"Dear Hiring Team at {opportunity.provider},\n\n"
        f"I am writing to apply for the {opportunity.title} position. As a "
        f"{profile.target_role or 'motivated professional'}, I offer experience "
        f"with {skills_text}. {body}\n\n"
        "I am particularly interested in this opportunity because it matches my "
        "career direction and gives me the chance to apply my skills to meaningful "
        "work. I would welcome the opportunity to discuss how my background can "
        "support your team.\n\n"
        f"Thank you for your consideration.\n\nSincerely,\n{candidate_name}"
    )


def evaluate_local_interview_answer(question: str, answer: str) -> str:
    normalized_answer = answer.strip()
    answer_words = re.findall(r"\b\w+\b", normalized_answer)
    lower_answer = normalized_answer.lower()

    # Very short answers get poor score
    if len(answer_words) < 15:
        return f"Rating: {max(2, len(answer_words) // 3)}/10. The response is too short ({len(answer_words)} words) to demonstrate competence. Please provide a detailed answer using the STAR method."

    # Use semantic model to check if answer is relevant to question
    model = get_sentence_model()
    relevance_bonus = 0
    if model:
        try:
            embeddings = model.encode([question, answer], normalize_embeddings=True)
            similarity = sum(a * b for a, b in zip(embeddings[0], embeddings[1]))
            # If similarity is very low, the answer might be irrelevant
            if similarity < 0.2:
                return f"Rating: 3/10. The response ({len(answer_words)} words) does not appear to answer the specific question asked. Focus on the core topic."
            elif similarity > 0.5:
                relevance_bonus = 2
        except Exception as e:  # noqa: BLE001
            logger.warning(f"Semantic eval error: {e}")

    star_terms = {"situation", "task", "action", "result"}
    star_matches = star_terms.intersection(lower_answer.split())

    # Base rating based on length, maxing at 5 for just length
    rating = min(5, len(answer_words) // 15) + relevance_bonus

    if len(star_matches) >= 2:
        rating += 2
    if any(
        term in lower_answer
        for term in (
            "impact",
            "improved",
            "increased",
            "reduced",
            "led",
            "developed",
            "achieved",
        )
    ):
        rating += 1

    rating = min(rating, 10)

    structure_feedback = (
        "The answer shows some structure but could make the situation, action, and result more explicit."
        if len(star_matches) < 2
        else "The answer follows a recognizable STAR structure."
    )
    return (
        f"Rating: {rating}/10. The response addresses the question with "
        f"{len(answer_words)} words. {structure_feedback} "
        "Strengthen it with one specific example, your individual contribution, "
        "and a measurable outcome."
    )


def get_spacy():
    global _nlp
    if _nlp is None:
        try:
            import spacy

            _nlp = spacy.load("en_core_web_sm")
        except Exception as e:  # noqa: BLE001
            logger.warning(f"SpaCy load error: {e}")
            return None
    return _nlp


def get_zero_shot():
    global _zero_shot
    if _zero_shot is None:
        try:
            from transformers import pipeline

            # We use a highly efficient model for fast CPU zero-shot classification
            _zero_shot = pipeline(
                "zero-shot-classification",
                model="typeform/distilbert-base-uncased-mnli",
            )
        except Exception as e:  # noqa: BLE001
            logger.warning(f"Transformers zero-shot load error: {e}")
            return None
    return _zero_shot


def get_sentence_model():
    global _sentence_model
    if _sentence_model is None:
        try:
            from sentence_transformers import SentenceTransformer

            _sentence_model = SentenceTransformer("all-MiniLM-L6-v2")
        except Exception as e:  # noqa: BLE001
            logger.warning("Sentence-transformers load error: %s", e)
            return None
    return _sentence_model


class LocalNLPResumeParser:
    """Custom Offline Advanced NLP Model for Resume Parsing using Deep Learning."""

    def __init__(self, text: str):
        self.text = text
        self.text_lower = text.lower()
        self.nlp = get_spacy()
        self.doc = self.nlp(text) if self.nlp else None

    def extract_name(self) -> str:
        blacklist = {
            "resume",
            "cv",
            "curriculum",
            "vitae",
            "html",
            "document",
            "profile",
            "page",
            "developer",
            "engineer",
            "analyst",
        }
        # Scrub emails, urls, and phones before looking for name
        text_no_contact = re.sub(r"\S+@\S+", "", self.text)
        text_no_contact = re.sub(r"http\S+|www\.\S+|\S+\.com\S*", "", text_no_contact)
        text_no_contact = re.sub(r"\+?\d{10,15}", "", text_no_contact)

        lines = [line.strip() for line in text_no_contact.split("\n") if line.strip()]
        if not lines:
            return "Unknown Candidate"

        # Fallback: Check first 10 and last 15 lines
        for line in lines[:10] + lines[-15:]:
            clean_name = re.sub(r"[^a-zA-Z\s]", "", line).strip()
            words = clean_name.split()
            if (
                1 < len(words) <= 3
                and all(len(w) > 1 for w in words)
                and clean_name == clean_name.title()
                and clean_name.lower() not in blacklist
                and not any(b in clean_name.lower() for b in blacklist)
            ):
                return clean_name.title()

        # 2. Use SpaCy NER on the first 500 characters only as a fallback
        if self.doc:
            top_doc = self.nlp(self.text[:500]) if self.nlp else None
            if top_doc:
                for ent in top_doc.ents:
                    if ent.label_ == "PERSON":
                        clean_name = re.sub(r"[^a-zA-Z\s]", "", ent.text).strip()
                        if (
                            len(clean_name) > 3
                            and len(clean_name) < 30
                            and clean_name.lower() not in blacklist
                            and not any(b in clean_name.lower() for b in blacklist)
                        ):
                            return clean_name.title()

        return "Unknown Candidate"

    def extract_skills(self) -> list[str]:
        found_skills = set()
        roles = CareerRole.objects.prefetch_related("skills").all()
        catalog_skills = set()
        for role in roles:
            for skill_obj in role.skills.all():
                skill = skill_obj.skill_name
                catalog_skills.add(skill)
                if re.search(r"\b" + re.escape(skill.lower()) + r"\b", self.text_lower):
                    found_skills.add(skill.title())

        if self.doc:
            stops = {"The", "And", "For", "With", "This", "That", "Are", "Was"}
            chunks = [
                chunk.text.strip()
                for chunk in self.doc.noun_chunks
                if 1 <= len(chunk.text.split()) <= 4
                and chunk.text.title() not in stops
                and not re.search(r"\d", chunk.text)
            ]
            common_tech_skills = {
                "python",
                "java",
                "c++",
                "javascript",
                "react",
                "node.js",
                "django",
                "sql",
                "aws",
                "docker",
                "kubernetes",
                "machine learning",
                "data analysis",
                "html",
                "css",
                "git",
                "linux",
                "agile",
                "power bi",
                "tableau",
                "excel",
            }

            for skill in common_tech_skills:
                if re.search(r"\b" + re.escape(skill) + r"\b", self.text_lower):
                    found_skills.add(skill.title())

            for chunk in chunks:
                c_lower = chunk.lower()
                if catalog_skills and c_lower in {s.lower() for s in catalog_skills}:
                    found_skills.add(chunk.title())

        return sorted(found_skills, key=str.casefold)[:15]

    def _semantic_skill_matches(
        self, candidates: list[str], catalog_skills: set[str]
    ) -> set[str]:
        model = get_sentence_model()
        if not model or not candidates or not catalog_skills:
            return set()
        try:
            skill_list = sorted(catalog_skills, key=str.casefold)
            embeddings = model.encode(
                candidates + skill_list,
                normalize_embeddings=True,
                show_progress_bar=False,
            )
            candidate_vectors = embeddings[: len(candidates)]
            skill_vectors = embeddings[len(candidates) :]
            matches = set()
            for candidate, candidate_vector in zip(candidates, candidate_vectors):
                scores = [
                    sum(
                        left * right
                        for left, right in zip(candidate_vector, skill_vector)
                    )
                    for skill_vector in skill_vectors
                ]
                best_index = max(range(len(scores)), key=scores.__getitem__)
                if scores[best_index] >= 0.62:
                    matches.add(skill_list[best_index].title())
            return matches
        except Exception as e:  # noqa: BLE001
            logger.warning("Semantic skill extraction error: %s", e)
            return set()

    def determine_roles(self, skills: list[str]) -> list[str]:
        roles = CareerRole.objects.all()
        candidate_labels = [r.title for r in roles]

        if not candidate_labels:
            candidate_labels = ["Software Engineer", "Data Analyst"]

        top_roles = []

        # 0. Check the first few lines of the resume for an explicit title
        lines = [line.strip() for line in self.text.split("\n") if line.strip()][:10]
        explicit_roles = []
        for line in lines:
            lower_line = line.lower()
            if any(
                kw in lower_line
                for kw in ["developer", "engineer", "analyst", "scientist", "manager", "designer"]
            ):
                # Check for specific titles directly in the line
                if "data analyst" in lower_line and "Data Analyst" not in explicit_roles:
                    explicit_roles.append("Data Analyst")
                elif ("ui/ux" in lower_line or "ui ux" in lower_line) and "UI/UX Designer" not in explicit_roles:
                    explicit_roles.append("UI/UX Designer")
                elif "data scientist" in lower_line and "Data Scientist / ML Engineer" not in explicit_roles:
                    explicit_roles.append("Data Scientist / ML Engineer")
                elif "software engineer" in lower_line and "Software Engineer" not in explicit_roles:
                    explicit_roles.append("Software Engineer")
                
                # Check if this line matches a candidate label perfectly
                for label in candidate_labels:
                    if label.lower() in lower_line and label not in explicit_roles:
                        explicit_roles.append(label)

        if explicit_roles:
            top_roles.extend(explicit_roles)

        # 2. Pre-trained Transformer Fallback (Zero-shot classification)
        classifier_model = get_zero_shot()
        if classifier_model and self.text:
            try:
                result = classifier_model(self.text[:2000], candidate_labels)
                zero_shot_roles = result.get("labels", [])[:5]
                for r in zero_shot_roles:
                    if r not in top_roles:
                        top_roles.append(r)
                if top_roles:
                    return top_roles[:5]
            except Exception as e:  # noqa: BLE001
                logger.warning("Zero-shot role classification error: %s", e)

        # Classical overlap fallback if HuggingFace isn't loaded
        skill_lower = {s.lower() for s in skills}
        scores = Counter()
        for role in roles:
            role_skills = [s.skill_name.lower() for s in role.skills.all()]
            overlap = len(skill_lower.intersection(set(role_skills)))
            scores[role.title] = overlap

        top_roles = [role for role, score in scores.most_common(5) if score > 0]

        if not top_roles:
            model = get_sentence_model()
            if model and self.text and roles:
                try:
                    role_texts = [
                        f"{role.title}: {', '.join(skill.skill_name for skill in role.skills.all())}"
                        for role in roles
                    ]
                    embeddings = model.encode(
                        [self.text[:2000], *role_texts],
                        normalize_embeddings=True,
                        show_progress_bar=False,
                    )
                    resume_vector = embeddings[0]
                    ranked = sorted(
                        zip(
                            (role.title for role in roles),
                            embeddings[1:],
                        ),
                        key=lambda item: sum(
                            left * right for left, right in zip(resume_vector, item[1])
                        ),
                        reverse=True,
                    )
                    top_roles = [role for role, _ in ranked[:5]]
                except Exception as e:  # noqa: BLE001
                    logger.warning("Semantic role classification error: %s", e)

        if not top_roles and candidate_labels:
            return candidate_labels[:3]

        return top_roles

    def _get_closest_role(self, top_role: str):
        try:
            return CareerRole.objects.get(title__iexact=top_role)
        except CareerRole.DoesNotExist:
            pass

        roles = list(CareerRole.objects.all())
        if not roles:
            return None

        model = get_sentence_model()
        if model:
            try:
                role_titles = [r.title for r in roles]
                embeddings = model.encode(
                    [top_role] + role_titles, normalize_embeddings=True
                )
                target_vector = embeddings[0]
                role_vectors = embeddings[1:]
                scores = [
                    sum(l * r for l, r in zip(target_vector, rv)) for rv in role_vectors
                ]
                best_idx = max(range(len(scores)), key=scores.__getitem__)
                if scores[best_idx] > 0.4:
                    return roles[best_idx]
            except Exception as e:  # noqa: BLE001
                logger.warning(f"Role matching error: {e}")
        return None

    def find_gaps_and_courses(self, top_role: str, current_skills: list[str]):
        role_obj = self._get_closest_role(top_role)
        if role_obj:
            required = list(role_obj.skills.values_list("skill_name", flat=True))
        else:
            required = list(
                RoleSkill.objects.values_list("skill_name", flat=True)
                .distinct()
                .order_by("?")[:10]
            )
            if not required:
                required = ["Communication", "Problem Solving"]

        current = [skill.strip() for skill in current_skills if skill and skill.strip()]
        current_normalized = {skill.casefold() for skill in current}
        missing = [
            skill for skill in required if skill.casefold() not in current_normalized
        ]

        if current and missing:
            model = get_sentence_model()
            if model:
                try:
                    embeddings = model.encode(
                        current + missing,
                        normalize_embeddings=True,
                        show_progress_bar=False,
                    )
                    current_vectors = embeddings[: len(current)]
                    missing_vectors = embeddings[len(current) :]
                    semantically_missing = []
                    for skill, vector in zip(missing, missing_vectors):
                        similarity = max(
                            sum(
                                left * right
                                for left, right in zip(vector, current_vector)
                            )
                            for current_vector in current_vectors
                        )
                        if similarity < 0.78:
                            semantically_missing.append(skill)
                    missing = semantically_missing
                except Exception as e:  # noqa: BLE001
                    logger.warning("Semantic gap analysis error: %s", e)

        missing = missing[:5]
        gaps = [skill.title() for skill in missing]
        courses = []
        course_records = list(CourseRecommendation.objects.all())
        exact_courses = {
            course.skill_name.casefold(): course for course in course_records
        }
        semantic_courses = []
        for gap in missing:
            course = exact_courses.get(gap.casefold())
            if course:
                semantic_courses.append(course)

        unresolved_gaps = [
            gap for gap in missing if gap.casefold() not in exact_courses
        ]
        model = get_sentence_model() if unresolved_gaps and course_records else None
        if model and unresolved_gaps:
            try:
                course_skills = [course.skill_name for course in course_records]
                embeddings = model.encode(
                    unresolved_gaps + course_skills,
                    normalize_embeddings=True,
                    show_progress_bar=False,
                )
                gap_vectors = embeddings[: len(unresolved_gaps)]
                course_vectors = embeddings[len(unresolved_gaps) :]
                for gap, gap_vector in zip(unresolved_gaps, gap_vectors):
                    scores = [
                        sum(
                            left * right
                            for left, right in zip(gap_vector, course_vector)
                        )
                        for course_vector in course_vectors
                    ]
                    best_index = max(range(len(scores)), key=scores.__getitem__)
                    if scores[best_index] >= 0.60:
                        semantic_courses.append(course_records[best_index])
            except Exception as e:  # noqa: BLE001
                logger.warning("Semantic course matching error: %s", e)

        for course in semantic_courses[:5]:
            provider = course.provider or "Online Platform"
            courses.append(f"{provider}: {course.course_title}")
        return gaps, courses

    def generate_interview_qs(self, top_role: str) -> list[str]:
        questions = []
        role_obj = self._get_closest_role(top_role)
        if role_obj:
            questions = [q.question_text for q in role_obj.questions.all()][:5]
        else:
            questions = [
                q.question_text for q in InterviewQuestion.objects.order_by("?")[:5]
            ]

        fallback_questions = [
            f"Which project best demonstrates your readiness for a {top_role} role?",
            f"How would you approach a difficult technical problem in a {top_role} role?",
            "Describe a measurable result you achieved and how you validated it.",
            "Tell me about a time you received difficult feedback and acted on it.",
            f"What would you learn first to become more effective as a {top_role}?",
        ]
        for question in fallback_questions:
            if len(questions) >= 5:
                break
            if question not in questions:
                questions.append(question)
        return questions[:5]

    def get_improvements(self, gaps: list[str]) -> list[str]:
        improvements = []
        evidence_text = " ".join(
            self._extract_section("project") + self._extract_section("experience")
        ).lower()
        for gap in gaps:
            if gap.lower() in evidence_text:
                suggestion = (
                    f"Quantify the existing {gap} work with a concrete metric, tool, "
                    "and outcome in the relevant bullet."
                )
            else:
                suggestion = (
                    f"Add a project or experience bullet demonstrating {gap}, "
                    "including the approach, your contribution, and the result."
                )
            improvements.append(suggestion)

        general_suggestions = [
            "Start each experience and project bullet with a strong action verb and a measurable result.",
            "Add a concise professional summary that names your target role and strongest competencies.",
            "Use consistent dates, headings, and bullet formatting so the resume is easy to scan and parse.",
            "Move the most relevant skills and projects near the top of the resume for the target role.",
            "Replace generic claims with evidence such as scale, speed, quality, users, or business impact.",
        ]
        for suggestion in general_suggestions:
            if len(improvements) >= 5:
                break
            improvements.append(suggestion)
        return improvements[:5]

    def _extract_section(self, section_name: str) -> list[str]:
        lines = [line.strip() for line in self.text.split("\n") if line.strip()]
        in_section = False
        content = []
        for line in lines:
            lower_line = line.lower()
            # If we see a short line that matches the section name
            if section_name in lower_line and len(line) < 30:
                in_section = True
                continue
            # If we see another heading, stop
            elif (
                in_section
                and len(line) < 30
                and any(
                    kw in lower_line
                    for kw in [
                        "experience",
                        "education",
                        "skills",
                        "projects",
                        "summary",
                        "profile",
                        "objective",
                    ]
                )
                and section_name not in lower_line
            ):
                break

            if in_section:
                content.append(line)
        return content

    def extract_summary(self) -> str:
        summary_lines = (
            self._extract_section("summary")
            or self._extract_section("profile")
            or self._extract_section("objective")
        )
        if not summary_lines:
            return "No professional summary detected."
        # Take the first paragraph block (up to a blank line or 5 lines)
        summary = " ".join(summary_lines[:5]).strip()
        # Cap at 500 chars to avoid grabbing the whole resume
        if len(summary) > 500:
            summary = summary[:497] + "..."
        return summary

    def extract_projects(self) -> list[str]:
        return self._extract_section("project")[:3]

    def extract_experience(self) -> list[str]:
        return self._extract_section("experience")[:3]

    def extract_academic_records(self) -> list[dict]:
        edu_lines = self._extract_section("education") or self._extract_section(
            "academic"
        )
        if not edu_lines:
            return []
        return [
            {
                "degree": " ".join(edu_lines)[:150],
                "institution": "Offline Extracted",
                "graduation_year": 2024,
                "cgpa": 0.0,
            }
        ]
