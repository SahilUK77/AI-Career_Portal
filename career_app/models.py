from django.db import models
from django.contrib.auth.models import User

class StudentProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, null=True, blank=True)
    full_name = models.CharField(max_length=255, blank=True, default="Student")
    target_role = models.CharField(max_length=255, blank=True)
    current_skills = models.TextField(blank=True, help_text="Comma-separated extracted skills")
    skill_gaps = models.TextField(blank=True, help_text="Comma-separated skill gaps")
    readiness_score = models.IntegerField(default=50)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.full_name or f"Student #{self.id}"


class CareerPath(models.Model):
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    required_skills = models.TextField(blank=True, help_text="Comma-separated list of required skills")

    def __str__(self):
        return self.title