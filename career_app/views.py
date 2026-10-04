import logging
import os
import traceback

from django.conf import settings
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User
from django.shortcuts import get_object_or_404
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from google.auth.transport import requests as google_requests
from google.oauth2 import id_token
from rest_framework import filters, generics, status, viewsets
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .local_nlp import evaluate_local_interview_answer, generate_local_cover_letter
from .ml_pipeline import analyze_resume
from .models import (
    AcademicRecord,
    Opportunity,
    ProfileMatch,
    ResumeAnalysis,
    StudentProfile,
)
from .serializers import (
    AcademicRecordSerializer,
    OpportunitySerializer,
    ProfileMatchSerializer,
    ResumeAnalysisSerializer,
    StudentProfileSerializer,
)
from .tasks import run_universal_scraper

logger = logging.getLogger(__name__)


class StudentProfileViewSet(viewsets.ModelViewSet):
    serializer_class = StudentProfileSerializer
    permission_classes = (IsAuthenticated,)

    def get_queryset(self):
        if not self.request.user.is_authenticated:
            return StudentProfile.objects.none()
        return StudentProfile.objects.filter(user=self.request.user)


class AcademicRecordViewSet(viewsets.ModelViewSet):
    serializer_class = AcademicRecordSerializer
    permission_classes = (IsAuthenticated,)

    def get_queryset(self):
        if not self.request.user.is_authenticated:
            return AcademicRecord.objects.none()
        return AcademicRecord.objects.filter(student__user=self.request.user)


@method_decorator(csrf_exempt, name="dispatch")
class UploadResumeAPIView(APIView):
    """Parses resume PDF, stores profile in DB, and queues match scoring."""

    def post(self, request, *args, **kwargs):
        resume_file = request.FILES.get("resume")
        if not resume_file:
            return Response(
                {"error": "No PDF file supplied."}, status=status.HTTP_400_BAD_REQUEST
            )

        try:
            # 1. AI Parsing Pipeline
            analysis = analyze_resume(resume_file.read())

            # 2. Persist to MySQL
            user_id = request.data.get("user_id")
            user_obj = request.user if request.user.is_authenticated else None

            if not user_obj and user_id:
                try:
                    user_obj = User.objects.get(id=user_id)
                except User.DoesNotExist:
                    pass

            if user_obj:
                profile, _ = StudentProfile.objects.get_or_create(user=user_obj)
                profile.full_name = analysis.full_name
            else:
                profile = StudentProfile.objects.create(full_name=analysis.full_name)

            profile.target_role = (
                analysis.target_professions[0]
                if analysis.target_professions
                else "Junior Analyst"
            )
            profile.current_skills = analysis.extracted_skills
            profile.skill_gaps = analysis.skill_gaps
            profile.resume_improvements = analysis.resume_improvements
            profile.interview_questions = analysis.interview_questions
            profile.interview_feedbacks = {}  # Clear previous feedbacks on new upload
            profile.bio = analysis.summary
            profile.projects = analysis.projects
            profile.experience = analysis.experience

            # Dynamic Readiness Calculation based on evidence
            num_skills = len(analysis.extracted_skills)
            num_gaps = len(analysis.skill_gaps)
            total_req = num_skills + num_gaps

            skill_score = (num_skills / total_req * 40) if total_req > 0 else 0
            exp_score = min(30, len(analysis.experience) * 10)
            proj_score = min(30, len(analysis.projects) * 10)

            raw_score = 30 + skill_score + exp_score + proj_score - (num_gaps * 2)
            profile.readiness_score = int(max(35, min(100, raw_score)))
            profile.save()

            # Record History
            if user_obj:
                ResumeAnalysis.objects.create(
                    user=user_obj,
                    resume_file=resume_file,
                    target_role=profile.target_role,
                    current_skills=profile.current_skills,
                    skill_gaps=profile.skill_gaps,
                    resume_improvements=profile.resume_improvements,
                    interview_questions=profile.interview_questions,
                    projects=profile.projects,
                    experience=profile.experience,
                    readiness_score=profile.readiness_score,
                )

            # Save academic records (profile must be saved first so FK exists)
            profile.academics.all().delete()
            for record in analysis.academic_records:
                try:
                    AcademicRecord.objects.create(
                        student=profile,
                        degree=str(record.get("degree", "Unknown Degree"))[:150],
                        institution=str(
                            record.get("institution", "Unknown Institution")
                        )[:200],
                        graduation_year=int(record.get("graduation_year", 2024)),
                        cgpa=float(record.get("cgpa", 0.0)),
                    )
                except Exception as e:  # noqa: BLE001
                    logger.warning(f"Failed to save academic record {record}: {e}")

            # 3. Trigger Celery Asynchronous Scraper (which chains match scoring)
            try:
                run_universal_scraper.delay(profile.id)
            except Exception as e:  # noqa: BLE001
                logger.warning(f"Background tasks skipped (Redis may be down): {e}")

            return Response(
                {
                    "profile_id": profile.id,
                    "full_name": profile.full_name,
                    "target_role": profile.target_role,
                    "readiness_score": profile.readiness_score,
                    "extracted_skills": profile.current_skills,
                    "skill_gaps": profile.skill_gaps,
                    "recommended_courses": analysis.recommended_courses,
                    "resume_improvements": profile.resume_improvements,
                    "interview_questions": profile.interview_questions,
                    "bio": profile.bio,
                    "projects": profile.projects,
                    "experience": profile.experience,
                    "academic_records": [
                        {
                            "degree": r.degree,
                            "institution": r.institution,
                            "graduation_year": r.graduation_year,
                            "cgpa": float(r.cgpa),
                        }
                        for r in profile.academics.all()
                    ],
                },
                status=status.HTTP_200_OK,
            )

        except Exception as e:  # noqa: BLE001
            traceback.print_exc()
            error_msg = str(e)
            status_code = status.HTTP_500_INTERNAL_SERVER_ERROR

            # Map known errors to appropriate HTTP responses
            if (
                "429" in error_msg
                or "ResourceExhausted" in error_msg
                or "quota" in error_msg.lower()
            ):
                status_code = status.HTTP_429_TOO_MANY_REQUESTS
                error_msg = "AI provider rate limit exceeded. Please wait about 30 seconds and try again."
            elif "404" in error_msg or "NOT_FOUND" in error_msg:
                status_code = status.HTTP_502_BAD_GATEWAY
                error_msg = "AI provider model not found or currently unavailable."
            elif "API_KEY" in error_msg or "api_key" in error_msg:
                status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
                error_msg = (
                    "Server configuration error: Google API Key is missing or invalid."
                )
            elif (
                "PDF" in error_msg.upper()
                or "decode" in error_msg.lower()
                or "EOF" in error_msg
            ):
                status_code = status.HTTP_400_BAD_REQUEST
                error_msg = "Failed to parse the uploaded PDF. Please ensure it is a valid, readable text PDF."

            return Response({"error": error_msg, "details": str(e)}, status=status_code)


class ResumeAnalysisHistoryAPIView(generics.ListAPIView):
    """Fetch all past resume analysis results for the logged-in user."""

    serializer_class = ResumeAnalysisSerializer
    permission_classes = (IsAuthenticated,)

    def get_queryset(self):
        return ResumeAnalysis.objects.filter(user=self.request.user).order_by(
            "-created_at"
        )


class CoverLetterHistoryAPIView(generics.ListAPIView):
    """Fetch all past generated cover letters for the logged-in user."""

    serializer_class = ProfileMatchSerializer
    permission_classes = (IsAuthenticated,)

    def get_queryset(self):
        return (
            ProfileMatch.objects.filter(profile__user=self.request.user)
            .exclude(cover_letter="")
            .order_by("-created_at")
        )


class OpportunityListAPIView(generics.ListAPIView):
    """Search and filter catalog of opportunities."""

    queryset = Opportunity.objects.filter(is_active=True)
    serializer_class = OpportunitySerializer
    filter_backends = (
        filters.SearchFilter,
        filters.OrderingFilter,
    )
    search_fields = (
        "title",
        "provider",
        "description",
        "required_skills__skill_name",
    )
    ordering_fields = (
        "created_at",
        "title",
        "deadline",
    )
    ordering = ("-created_at",)

    def get_queryset(self):
        search_query = self.request.query_params.get("search")
        if search_query:
            # Note: We rely on the Celery background worker to populate opportunities.
            # Inline blocking scraping is removed to prevent 'database is locked' errors on SQLite.
            pass

        qs = Opportunity.objects.filter(is_active=True)
        opp_type = self.request.query_params.get("type")
        is_free = self.request.query_params.get("is_free")

        if opp_type:
            qs = qs.filter(opportunity_type__icontains=opp_type)
        if is_free is not None and is_free != "":
            qs = qs.filter(is_free=(is_free.lower() == "true"))
        return qs.distinct()


class OpportunityTypesAPIView(APIView):
    def get(self, request, *args, **kwargs):
        types = (
            Opportunity.objects.exclude(opportunity_type="")
            .values_list("opportunity_type", flat=True)
            .distinct()
        )
        return Response([t for t in types])


class RecommendedMatchesAPIView(APIView):
    """Retrieves ranked opportunities for the authenticated user's profile."""

    permission_classes = (IsAuthenticated,)

    def get(self, request, *args, **kwargs):
        try:
            profile = StudentProfile.objects.get(user=request.user)
        except StudentProfile.DoesNotExist:
            profile = StudentProfile.objects.create(
                user=request.user, target_role="Undecided"
            )

        matches = ProfileMatch.objects.filter(profile=profile).select_related(
            "opportunity"
        )

        # Categorize matches for the frontend
        schemes = [m for m in matches if m.opportunity.opportunity_type == "Scheme"]
        others = [m for m in matches if m.opportunity.opportunity_type != "Scheme"]

        return Response(
            {
                "schemes": ProfileMatchSerializer(schemes, many=True).data,
                "opportunities": ProfileMatchSerializer(others, many=True).data,
            }
        )


@method_decorator(csrf_exempt, name="dispatch")
class SocialLoginAPIView(APIView):
    def post(self, request, *args, **kwargs):
        token = request.data.get("token")
        if not token:
            return Response(
                {"error": "Token is required"}, status=status.HTTP_400_BAD_REQUEST
            )

        try:
            idinfo = id_token.verify_oauth2_token(
                token,
                google_requests.Request(),
                audience=settings.GOOGLE_CLIENT_ID or None,
            )
            email = idinfo["email"]
            name = idinfo.get("name", "Student")

            user, _created = User.objects.get_or_create(
                username=email, defaults={"email": email, "first_name": name}
            )
            StudentProfile.objects.get_or_create(
                user=user,
                defaults={"full_name": name, "target_role": "Student"},
            )
            login(request, user)
            return Response(
                {
                    "message": "Successfully logged in",
                    "user_id": user.id,
                    "username": user.username,
                    "email": user.email,
                }
            )
        except ValueError:
            return Response(
                {"error": "Invalid token"}, status=status.HTTP_401_UNAUTHORIZED
            )


@method_decorator(csrf_exempt, name="dispatch")
class ChatbotAPIView(APIView):
    permission_classes = (IsAuthenticated,)

    def post(self, request, *args, **kwargs):
        message = request.data.get("message")
        if not message:
            return Response(
                {"error": "Message is required"}, status=status.HTTP_400_BAD_REQUEST
            )

        context_msg = "You are a helpful CareerAI chatbot."
        profile_id = None
        try:
            profile = StudentProfile.objects.get(user=request.user)
            profile_id = profile.id
            context_msg += (
                f"\nThe user is targeting {profile.target_role}."
                f"\nCurrent skills: {', '.join(profile.current_skills)}."
                f"\nSkill gaps: {', '.join(profile.skill_gaps)}."
            )
            matched_opportunities = (
                ProfileMatch.objects.filter(profile=profile)
                .select_related("opportunity")
                .order_by("-relevance_score")[:3]
            )
            opportunity_context = [
                f"{match.opportunity.title} ({match.opportunity.provider}): "
                f"{match.opportunity.description[:240]}"
                for match in matched_opportunities
            ]
            if opportunity_context:
                context_msg += "\nTop matched opportunities:\n- " + "\n- ".join(
                    opportunity_context
                )
        except StudentProfile.DoesNotExist:
            pass

        api_key = os.getenv("GOOGLE_API_KEY")
        model_name = os.getenv("GEMINI_MODEL", "gemini-1.5-flash")
        if api_key:
            from langchain_google_genai import ChatGoogleGenerativeAI

            llm = ChatGoogleGenerativeAI(
                model=model_name, google_api_key=api_key, temperature=0.7
            )
            try:
                response = llm.invoke(f"{context_msg}\n\nUser: {message}\nAI:")
                content = response.content
                if isinstance(content, list):
                    content = "".join(
                        p.get("text", "") if isinstance(p, dict) else str(p)
                        for p in content
                    )
                return Response({"response": content})
            except Exception:  # noqa: BLE001, S110
                # API failed (likely 429 quota exhausted). Fallback to local heuristic.
                pass

        # --- LOCAL NLP FALLBACK ---
        local_context = "I am CareerAI, your local career assistant! "
        if profile_id:
            try:
                profile = StudentProfile.objects.get(id=profile_id)
                local_context += (
                    f"I see you're interested in being a {profile.target_role}. "
                )
            except StudentProfile.DoesNotExist:
                pass

        msg_lower = message.lower()
        if any(word in msg_lower for word in ["hello", "hi", "hey"]):
            ai_text = f"{local_context}How can I help you with your career goals today?"
        elif any(word in msg_lower for word in ["resume", "cv"]):
            ai_text = "I recommend highlighting your technical skills at the top of your resume and quantifying your achievements with metrics."
        elif any(word in msg_lower for word in ["interview", "prep"]):
            ai_text = "For interviews, always use the STAR method (Situation, Task, Action, Result) to structure your behavioral answers."
        elif any(word in msg_lower for word in ["course", "learn", "study"]):
            ai_text = "I recommend checking out SWAYAM or NPTEL for certified courses. I can match you with specific courses if you upload your resume."
        elif any(word in msg_lower for word in ["job", "internship", "scheme"]):
            ai_text = "You can browse the Opportunity Hub tab to see the latest jobs, internships, and government schemes matching your profile."
        else:
            ai_text = "That's an interesting point! I am currently running on my lightweight offline model due to high demand, but I recommend uploading your resume to get the most tailored career advice."

        return Response({"response": ai_text})


@method_decorator(csrf_exempt, name="dispatch")
class LoginAPIView(APIView):
    def post(self, request, *args, **kwargs):
        username = request.data.get("username")
        password = request.data.get("password")

        user = authenticate(username=username, password=password)
        if user is not None:
            login(request, user)
            return Response(
                {
                    "message": "Successfully logged in",
                    "user_id": user.id,
                    "username": user.username,
                },
                status=status.HTTP_200_OK,
            )
        else:
            return Response(
                {"error": "Invalid username or password"},
                status=status.HTTP_401_UNAUTHORIZED,
            )


@method_decorator(csrf_exempt, name="dispatch")
class RegisterAPIView(APIView):
    def post(self, request, *args, **kwargs):
        username = request.data.get("username")
        password = request.data.get("password")
        email = request.data.get("email", "")

        if not username or not password:
            return Response(
                {"error": "Username and password are required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if User.objects.filter(username=username).exists():
            return Response(
                {"error": "Username already exists"}, status=status.HTTP_400_BAD_REQUEST
            )

        user = User.objects.create_user(
            username=username, email=email, password=password
        )
        StudentProfile.objects.create(user=user, target_role="Student")

        login(request, user)
        return Response(
            {
                "message": "Registration successful",
                "user_id": user.id,
                "username": user.username,
            },
            status=status.HTTP_201_CREATED,
        )


class LogoutAPIView(APIView):
    def post(self, request, *args, **kwargs):
        logout(request)
        return Response(
            {"message": "Successfully logged out"}, status=status.HTTP_200_OK
        )


# get_object_or_404 is imported at the top of the file


class ToggleBookmarkAPIView(APIView):
    permission_classes = (IsAuthenticated,)

    def post(self, request, opp_id, *args, **kwargs):
        opportunity = get_object_or_404(Opportunity, id=opp_id)
        profile, _ = StudentProfile.objects.get_or_create(
            user=request.user, defaults={"target_role": "Undecided"}
        )
        match, _created = ProfileMatch.objects.get_or_create(
            profile=profile,
            opportunity=opportunity,
            defaults={
                "relevance_score": 50.0,
                "reasoning": "Manually interacted by user.",
            },
        )
        match.is_bookmarked = not match.is_bookmarked
        match.save()
        return Response(
            {"is_bookmarked": match.is_bookmarked}, status=status.HTTP_200_OK
        )


class GenerateCoverLetterAPIView(APIView):
    permission_classes = (IsAuthenticated,)

    def post(self, request, opp_id, *args, **kwargs):
        opportunity = get_object_or_404(Opportunity, id=opp_id)
        profile = get_object_or_404(StudentProfile, user=request.user)

        # Check if we already have a generated cover letter for this match
        match, _created = ProfileMatch.objects.get_or_create(
            profile=profile,
            opportunity=opportunity,
            defaults={
                "relevance_score": 50.0,
                "reasoning": "Interacted via cover letter generation.",
            },
        )

        if match.cover_letter:
            return Response(
                {"cover_letter": match.cover_letter}, status=status.HTTP_200_OK
            )

        api_key = os.getenv("GOOGLE_API_KEY")
        model_name = os.getenv("GEMINI_MODEL", "gemini-1.5-flash")
        cover_letter = None
        if api_key:
            try:
                from langchain_google_genai import ChatGoogleGenerativeAI

                llm = ChatGoogleGenerativeAI(
                    model=model_name, google_api_key=api_key, temperature=0.7
                )
                prompt = f"""
                Write a professional cover letter for the following job opportunity.
                Candidate Name: {profile.full_name}
                Target Role: {profile.target_role}
                Candidate Skills: {", ".join(profile.current_skills)}

                Job Title: {opportunity.title}
                Company/Provider: {opportunity.provider}
                Job Description: {opportunity.description}

                The cover letter should be concise, professional, and highlight the alignment between the candidate's skills and the job requirements.
                """
                response = llm.invoke(prompt)
                cover_letter = response.content
                if isinstance(cover_letter, list):
                    cover_letter = "".join(
                        p.get("text", "") if isinstance(p, dict) else str(p)
                        for p in cover_letter
                    )
            except Exception as e:  # noqa: BLE001
                logger.warning(
                    "Cover letter provider unavailable; using local fallback: %s", e
                )

        if not cover_letter:
            cover_letter = generate_local_cover_letter(profile, opportunity)

        try:
            match.cover_letter = cover_letter
            match.save(update_fields=["cover_letter"])

            return Response({"cover_letter": cover_letter}, status=status.HTTP_200_OK)
        except Exception as e:  # noqa: BLE001
            return Response(
                {"error": f"Failed to generate cover letter: {e!s}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class InterviewEvaluationAPIView(APIView):
    permission_classes = (IsAuthenticated,)

    def post(self, request, *args, **kwargs):
        question = request.data.get("question")
        answer = request.data.get("answer")

        if not question or not answer:
            return Response(
                {"error": "Question and answer are required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        analysis_id = request.data.get("analysis_id")
        feedback = None
        api_key = os.getenv("GOOGLE_API_KEY")
        model_name = os.getenv("GEMINI_MODEL", "gemini-1.5-flash")
        if api_key:
            try:
                from langchain_google_genai import ChatGoogleGenerativeAI

                llm = ChatGoogleGenerativeAI(
                    model=model_name, google_api_key=api_key, temperature=0.7
                )
                response = llm.invoke(f"""
                You are an expert technical interviewer evaluating a candidate's answer.
                Question: {question}
                Candidate's Answer: {answer}
                Evaluate the candidate's answer in 5-6 concise sentences. Identify
                strengths, missing points, and give a rating out of 10.
                """)
                feedback = response.content
                if isinstance(feedback, list):
                    feedback = "".join(
                        p.get("text", "") if isinstance(p, dict) else str(p)
                        for p in feedback
                    )
            except Exception as e:  # noqa: BLE001
                logger.warning(
                    "Interview evaluation provider unavailable; using local fallback: %s",
                    e,
                )

        if not feedback:
            feedback = evaluate_local_interview_answer(question, answer)

        try:
            # Update StudentProfile
            profile = StudentProfile.objects.filter(user=request.user).first()
            if profile:
                if not isinstance(profile.interview_feedbacks, dict):
                    profile.interview_feedbacks = {}
                profile.interview_feedbacks[question] = {
                    "answer": answer,
                    "feedback": feedback,
                }
                profile.save(update_fields=["interview_feedbacks"])

            if analysis_id:
                analysis = ResumeAnalysis.objects.filter(id=analysis_id, user=request.user).first()
            else:
                analysis = ResumeAnalysis.objects.filter(user=request.user).order_by("-created_at").first()

            if analysis:
                if not isinstance(analysis.interview_feedbacks, dict):
                    analysis.interview_feedbacks = {}

                # Store both answer and feedback, keyed by the question text
                analysis.interview_feedbacks[question] = {
                    "answer": answer,
                    "feedback": feedback,
                }
                analysis.save(update_fields=["interview_feedbacks"])

            return Response({"feedback": feedback}, status=status.HTTP_200_OK)
        except Exception as e:  # noqa: BLE001
            return Response(
                {"error": f"Failed to save interview evaluation: {e!s}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
