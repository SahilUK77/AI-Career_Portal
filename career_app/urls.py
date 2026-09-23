from django.urls import path
from .views import (
    UploadResumeAPIView,
    OpportunityListAPIView,
    RecommendedMatchesAPIView
)

urlpatterns = [
    path('upload-resume/', UploadResumeAPIView.as_view(), name='api_upload_resume'),
    path('opportunities/', OpportunityListAPIView.as_view(), name='api_opportunities'),
    path('recommendations/<int:profile_id>/', RecommendedMatchesAPIView.as_view(), name='api_recommendations'),
]