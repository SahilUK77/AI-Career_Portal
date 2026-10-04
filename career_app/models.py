from django.contrib.auth.models import User
from django.db import models


class StudentProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, null=True, blank=True)
    full_name = models.CharField(max_length=255, default="Student")
    bio = models.TextField(blank=True)
    target_role = models.CharField(max_length=255, blank=True, db_index=True)
    current_skills = models.JSONField(
        default=list, help_text="List of extracted candidate skills"
    )
    skill_gaps = models.JSONField(
        default=list, help_text="List of missing skills for target role"
    )
    resume_improvements = models.JSONField(
        default=list, help_text="Actionable formatting/content suggestions"
    )
    interview_questions = models.JSONField(
        default=list, help_text="Tailored mock interview questions"
    )
    interview_feedbacks = models.JSONField(
        default=dict, help_text="Saved mock interview answers and feedbacks"
    )
    projects = models.JSONField(
        default=list, help_text="List of extracted project details"
    )
    experience = models.JSONField(
        default=list, help_text="List of extracted work experience"
    )
    readiness_score = models.IntegerField(default=50)
    employability_score = models.IntegerField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.full_name} ({self.target_role})"


class AcademicRecord(models.Model):
    student = models.ForeignKey(
        StudentProfile, on_delete=models.CASCADE, related_name="academics"
    )
    degree = models.CharField(
        max_length=150, help_text="e.g., B.Tech in Computer Science"
    )
    institution = models.CharField(max_length=200)
    graduation_year = models.IntegerField()
    cgpa = models.DecimalField(max_digits=4, decimal_places=2, help_text="e.g., 7.90")

    def __str__(self):
        return f"{self.degree} - {self.institution}"


class Opportunity(models.Model):
    dedupe_hash = models.CharField(max_length=64, unique=True, db_index=True)
    title = models.CharField(max_length=500)
    provider = models.CharField(max_length=255, db_index=True)
    opportunity_type = models.CharField(
        max_length=100,
        db_index=True,
        help_text="e.g., Job, Internship, Scheme, Fellowship",
    )
    is_free = models.BooleanField(default=True, db_index=True)
    stipend_or_cost = models.CharField(max_length=100, blank=True, default="Free")
    mode = models.CharField(max_length=50, default="Online")
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
            models.Index(fields=["opportunity_type", "is_free", "is_active"]),
        ]

    def __str__(self):
        return f"[{self.opportunity_type}] {self.title} - {self.provider}"


class OpportunitySkill(models.Model):
    opportunity = models.ForeignKey(
        Opportunity, on_delete=models.CASCADE, related_name="required_skills"
    )
    skill_name = models.CharField(max_length=100, db_index=True)

    class Meta:
        unique_together = ("opportunity", "skill_name")

    def __str__(self):
        return f"{self.skill_name} -> {self.opportunity.title}"


class ProfileMatch(models.Model):
    profile = models.ForeignKey(
        StudentProfile, on_delete=models.CASCADE, related_name="matches"
    )
    opportunity = models.ForeignKey(
        Opportunity, on_delete=models.CASCADE, related_name="profile_matches"
    )
    relevance_score = models.FloatField(db_index=True)
    matching_skills = models.JSONField(default=list)
    reasoning = models.TextField(blank=True)
    is_bookmarked = models.BooleanField(default=False)
    cover_letter = models.TextField(blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("profile", "opportunity")
        ordering = ["-relevance_score"]

    def __str__(self):
        return f"{self.profile.full_name} <-> {self.opportunity.title} ({self.relevance_score}%)"


class CareerRole(models.Model):
    title = models.CharField(max_length=255, unique=True, db_index=True)
    description = models.TextField(blank=True)

    def __str__(self):
        return self.title


class RoleSkill(models.Model):
    role = models.ForeignKey(
        CareerRole, on_delete=models.CASCADE, related_name="skills"
    )
    skill_name = models.CharField(max_length=100)

    def __str__(self):
        return f"{self.skill_name} ({self.role.title})"


class CourseRecommendation(models.Model):
    skill_name = models.CharField(max_length=100, db_index=True)
    course_title = models.CharField(max_length=255)
    url = models.URLField(max_length=1000, blank=True)
    provider = models.CharField(max_length=255, blank=True)

    def __str__(self):
        return f"{self.skill_name} -> {self.course_title}"


class InterviewQuestion(models.Model):
    role = models.ForeignKey(
        CareerRole, on_delete=models.CASCADE, related_name="questions"
    )
    question_text = models.TextField()

    def __str__(self):
        return f"{self.role.title} - {self.question_text[:30]}..."


class ResumeAnalysis(models.Model):
    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="resume_analyses"
    )
    resume_file = models.FileField(upload_to="resumes/", null=True, blank=True)
    target_role = models.CharField(max_length=255, blank=True)
    current_skills = models.JSONField(default=list)
    skill_gaps = models.JSONField(default=list)
    resume_improvements = models.JSONField(default=list)
    interview_questions = models.JSONField(default=list)
    interview_feedbacks = models.JSONField(default=dict)
    projects = models.JSONField(default=list)
    experience = models.JSONField(default=list)
    readiness_score = models.IntegerField(default=50)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Analysis for {self.user.username} - {self.created_at.strftime('%Y-%m-%d %H:%M')}"
