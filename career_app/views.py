import traceback
from django.shortcuts import render
from rest_framework import generics, filters, status
from rest_framework.views import APIView
from rest_framework.response import Response
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator

from .models import Opportunity, ProfileMatch, StudentProfile
from .serializers import OpportunitySerializer, ProfileMatchSerializer, StudentProfileSerializer
from .ml_pipeline import analyze_resume
from .tasks import calculate_matches_for_profile, run_govt_schemes_scraper, run_courses_scraper

def dashboard_view(request):
    """Renders the single-page application dashboard interface."""
    return render(request, 'index.html')


@method_decorator(csrf_exempt, name='dispatch')
class UploadResumeAPIView(APIView):
    """Parses resume PDF, stores profile in MySQL, and queues match scoring."""
    def post(self, request, *args, **kwargs):
        resume_file = request.FILES.get('resume')
        if not resume_file:
            return Response({"error": "No PDF file supplied."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            # 1. AI Parsing Pipeline
            analysis = analyze_resume(resume_file.read())

            # 2. Persist to MySQL
            if request.user.is_authenticated:
                profile, _ = StudentProfile.objects.get_or_create(user=request.user)
            else:
                profile = StudentProfile.objects.create(full_name=analysis.full_name)

            profile.target_role = analysis.target_professions[0] if analysis.target_professions else "Junior Analyst"
            profile.current_skills = analysis.extracted_skills
            profile.skill_gaps = analysis.skill_gaps
            profile.resume_improvements = analysis.resume_improvements
            profile.interview_questions = analysis.interview_questions
            
            # Dynamic Readiness Calculation
            penalty = len(analysis.skill_gaps) * 8
            profile.readiness_score = max(35, 100 - penalty)
            profile.save()

            # 3. Synchronously ensure baseline opportunities exist
            if Opportunity.objects.count() == 0:
                run_govt_schemes_scraper()
                run_courses_scraper()

            # 4. Trigger Celery Asynchronous Match Engine
            calculate_matches_for_profile.delay(profile.id)

            return Response({
                "profile_id": profile.id,
                "full_name": profile.full_name,
                "target_role": profile.target_role,
                "readiness_score": profile.readiness_score,
                "extracted_skills": profile.current_skills,
                "skill_gaps": profile.skill_gaps,
                "recommended_courses": analysis.recommended_courses,
                "resume_improvements": profile.resume_improvements,
                "interview_questions": profile.interview_questions
            }, status=status.HTTP_200_OK)

        except Exception as e:
            traceback.print_exc()
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class OpportunityListAPIView(generics.ListAPIView):
    """Search and filter catalog of opportunities."""
    queryset = Opportunity.objects.filter(is_active=True)
    serializer_class = OpportunitySerializer
    filter_backends = [filters.SearchFilter]
    search_fields = ['title', 'provider', 'description', 'required_skills__skill_name']

    def get_queryset(self):
        qs = super().get_queryset()
        opp_type = self.request.query_params.get('type')
        is_free = self.request.query_params.get('is_free')

        if opp_type:
            qs = qs.filter(opportunity_type=opp_type)
        if is_free is not None:
            qs = qs.filter(is_free=(is_free.lower() == 'true'))
        return qs.distinct()


class RecommendedMatchesAPIView(APIView):
    """Retrieves ranked opportunities for a specific profile ID."""
    def get(self, request, profile_id, *args, **kwargs):
        matches = ProfileMatch.objects.filter(profile_id=profile_id).select_related('opportunity')
        
        # Categorize matches for the frontend
        schemes = [m for m in matches if m.opportunity.opportunity_type == 'Scheme']
        others = [m for m in matches if m.opportunity.opportunity_type != 'Scheme']

        return Response({
            "schemes": ProfileMatchSerializer(schemes, many=True).data,
            "opportunities": ProfileMatchSerializer(others, many=True).data
        })