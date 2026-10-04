from rest_framework import serializers

from .models import (
    AcademicRecord,
    Opportunity,
    ProfileMatch,
    ResumeAnalysis,
    StudentProfile,
)


class OpportunitySerializer(serializers.ModelSerializer):
    required_skills = serializers.SlugRelatedField(
        many=True, read_only=True, slug_field="skill_name"
    )
    has_cover_letter = serializers.SerializerMethodField()

    class Meta:
        model = Opportunity
        fields = (
            "id",
            "title",
            "provider",
            "opportunity_type",
            "is_free",
            "stipend_or_cost",
            "mode",
            "location",
            "deadline",
            "url",
            "description",
            "eligibility",
            "required_skills",
            "has_cover_letter",
        )

    def get_has_cover_letter(self, obj):
        request = self.context.get('request')
        if not request or not request.user.is_authenticated:
            return False
        return ProfileMatch.objects.filter(
            profile__user=request.user, 
            opportunity=obj, 
            cover_letter__isnull=False
        ).exclude(cover_letter="").exists()


class ProfileMatchSerializer(serializers.ModelSerializer):
    opportunity = OpportunitySerializer(read_only=True)

    class Meta:
        model = ProfileMatch
        fields = (
            "id",
            "relevance_score",
            "matching_skills",
            "reasoning",
            "is_bookmarked",
            "opportunity",
            "cover_letter",
            "created_at",
        )


class AcademicRecordSerializer(serializers.ModelSerializer):
    class Meta:
        model = AcademicRecord
        fields = ["id", "degree", "institution", "graduation_year", "cgpa"]


class StudentProfileSerializer(serializers.ModelSerializer):
    academics = AcademicRecordSerializer(many=True, read_only=True)
    first_name = serializers.SerializerMethodField()
    last_name = serializers.SerializerMethodField()

    def get_first_name(self, obj):
        return obj.user.first_name if obj.user else ""

    def get_last_name(self, obj):
        return obj.user.last_name if obj.user else ""

    class Meta:
        model = StudentProfile
        fields = [
            "id",
            "first_name",
            "last_name",
            "full_name",
            "bio",
            "target_role",
            "current_skills",
            "skill_gaps",
            "resume_improvements",
            "interview_questions",
            "interview_feedbacks",
            "projects",
            "experience",
            "readiness_score",
            "employability_score",
            "academics",
        ]


class ResumeAnalysisSerializer(serializers.ModelSerializer):
    class Meta:
        model = ResumeAnalysis
        fields = "__all__"
