# career_app/views.py
import traceback
from django.shortcuts import render
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from .models import StudentProfile
from .ml_pipeline import analyze_resume

def dashboard_view(request):
    return render(request, 'index.html')

@csrf_exempt
def upload_resume_view(request):
    if request.method == 'POST' and request.FILES.get('resume'):
        try:
            resume_file = request.FILES['resume']
            analysis = analyze_resume(resume_file.read())

            if request.user.is_authenticated:
                student, _ = StudentProfile.objects.get_or_create(user=request.user)
            else:
                student = StudentProfile.objects.create(full_name="Guest Student")

            student.target_role = analysis.target_professions[0] if analysis.target_professions else ""
            student.current_skills = ", ".join(analysis.extracted_skills)
            student.skill_gaps = ", ".join(analysis.skill_gaps)
            student.save()

            return JsonResponse(analysis.model_dump())
        except Exception as e:
            # Print full traceback to VS Code terminal
            traceback.print_exc()
            return JsonResponse({"error": str(e)}, status=500)

    return JsonResponse({"error": "No resume file provided"}, status=400)