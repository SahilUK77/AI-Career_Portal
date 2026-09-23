from django.contrib import admin
from django.urls import path, include
from career_app.views import dashboard_view

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', dashboard_view, name='dashboard'),
    
    # This automatically imports all API endpoints from career_app/urls.py
    path('api/', include('career_app.urls')),
]