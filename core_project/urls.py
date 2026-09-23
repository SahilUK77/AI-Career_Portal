from django.contrib import admin
from django.urls import path
from career_app import views

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', views.dashboard_view, name='dashboard'),
    # Add this to your existing URL patterns
    path('api/upload-resume/', views.upload_resume_view, name='upload_resume'),
]