from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import (
    AcademicRecordViewSet,
    ChatbotAPIView,
    CoverLetterHistoryAPIView,
    GenerateCoverLetterAPIView,
    InterviewEvaluationAPIView,
    LoginAPIView,
    LogoutAPIView,
    OpportunityListAPIView,
    OpportunityTypesAPIView,
    RecommendedMatchesAPIView,
    RegisterAPIView,
    ResumeAnalysisHistoryAPIView,
    SocialLoginAPIView,
    StudentProfileViewSet,
    ToggleBookmarkAPIView,
    UploadResumeAPIView,
)

router = DefaultRouter()
router.register(r"profiles", StudentProfileViewSet, basename="profile")
router.register(r"academics", AcademicRecordViewSet, basename="academic")

urlpatterns = [
    path("", include(router.urls)),
    path("upload-resume/", UploadResumeAPIView.as_view(), name="api_upload_resume"),
    path(
        "resume-history/",
        ResumeAnalysisHistoryAPIView.as_view(),
        name="api_resume_history",
    ),
    path(
        "cover-letter-history/",
        CoverLetterHistoryAPIView.as_view(),
        name="api_cover_letter_history",
    ),
    path("opportunities/", OpportunityListAPIView.as_view(), name="api_opportunities"),
    path(
        "opportunities/types/",
        OpportunityTypesAPIView.as_view(),
        name="api_opportunity_types",
    ),
    path(
        "recommendations/",
        RecommendedMatchesAPIView.as_view(),
        name="api_recommendations",
    ),
    path(
        "bookmark/<int:opp_id>/", ToggleBookmarkAPIView.as_view(), name="api_bookmark"
    ),
    path(
        "cover-letter/<int:opp_id>/",
        GenerateCoverLetterAPIView.as_view(),
        name="api_cover_letter",
    ),
    path(
        "interview-evaluate/",
        InterviewEvaluationAPIView.as_view(),
        name="api_interview_evaluate",
    ),
    path("social-login/", SocialLoginAPIView.as_view(), name="api_social_login"),
    path("login/", LoginAPIView.as_view(), name="api_login"),
    path("register/", RegisterAPIView.as_view(), name="api_register"),
    path("logout/", LogoutAPIView.as_view(), name="api_logout"),
    path("chatbot/", ChatbotAPIView.as_view(), name="api_chatbot"),
]
