from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.http import HttpResponse
from django.urls import include, path

urlpatterns = [
    path("favicon.ico", lambda _: HttpResponse(status=204)),
    path("admin/", admin.site.urls),
    # This automatically imports all API endpoints from career_app/urls.py
    path("api/", include("career_app.urls")),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
