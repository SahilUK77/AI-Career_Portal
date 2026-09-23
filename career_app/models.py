from django.db import models
from django.contrib.auth.models import User

class StudentProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, null=True, blank=True)
    full_name = models.CharField(max_length=255, default="Student")
    target_role = models.CharField(max_length=255, blank=True, db_index=True)
    current_skills = models.JSONField(default=list, help_text="List of extracted candidate skills")
    skill_gaps = models.JSONField(default=list, help_text="List of missing skills for target role")
    resume_improvements = models.JSONField(default=list, help_text="Actionable formatting/content suggestions")
    interview_questions = models.JSONField(default=list, help_text="Tailored mock interview questions")
    readiness_score = models.IntegerField(default=50)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.full_name} ({self.target_role})"


class Opportunity(models.Model):
    TYPE_CHOICES = [
        ('Scheme', 'Government Scheme'),
        ('Course', 'Free/Paid Course'),
        ('Internship', 'Internship'),
        ('Job', 'Job Opening'),
        ('Hackathon', 'Hackathon/Contest'),
        ('Certification', 'Certification Program'),
    ]
    MODE_CHOICES = [
        ('Online', 'Online'),
        ('Offline', 'Offline'),
        ('Hybrid', 'Hybrid'),
    ]

    dedupe_hash = models.CharField(max_length=64, unique=True, db_index=True)
    title = models.CharField(max_length=500)
    provider = models.CharField(max_length=255, db_index=True)
    opportunity_type = models.CharField(max_length=30, choices=TYPE_CHOICES, db_index=True)
    is_free = models.BooleanField(default=True, db_index=True)
    stipend_or_cost = models.CharField(max_length=100, blank=True, default="Free")
    mode = models.CharField(max_length=20, choices=MODE_CHOICES, default='Online')
    location = models.CharField(max_length=255, default="Pan-India", db_index=True)
    deadline = models.DateField(null=True, blank=True, db_index=True)
    url = models.URLField(max_length=1000)
    description = models.TextField(blank=True)
    eligibility = models.TextField(blank=True)
    metadata_json = models.JSONField(default=dict, blank=True)
    is_active = models.BooleanField(default=True, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name_plural = "Opportunities"
        indexes = [
            models.Index(fields=['opportunity_type', 'is_free', 'is_active']),
        ]

    def __str__(self):
        return f"[{self.opportunity_type}] {self.title} - {self.provider}"


class OpportunitySkill(models.Model):
    opportunity = models.ForeignKey(Opportunity, on_delete=models.CASCADE, related_name="required_skills")
    skill_name = models.CharField(max_length=100, db_index=True)

    class Meta:
        unique_together = ('opportunity', 'skill_name')

    def __str__(self):
        return f"{self.skill_name} -> {self.opportunity.title}"


class ProfileMatch(models.Model):
    profile = models.ForeignKey(StudentProfile, on_delete=models.CASCADE, related_name="matches")
    opportunity = models.ForeignKey(Opportunity, on_delete=models.CASCADE, related_name="profile_matches")
    relevance_score = models.FloatField(db_index=True)
    matching_skills = models.JSONField(default=list)
    reasoning = models.TextField(blank=True)
    is_bookmarked = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('profile', 'opportunity')
        ordering = ['-relevance_score']

    def __str__(self):
        return f"{self.profile.full_name} <-> {self.opportunity.title} ({self.relevance_score}%)"