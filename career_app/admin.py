from django.contrib import admin

from .models import (
    AcademicRecord,
    Opportunity,
    OpportunitySkill,
    ProfileMatch,
    StudentProfile,
)


@admin.register(StudentProfile)
class StudentProfileAdmin(admin.ModelAdmin):
    list_display = ["full_name", "target_role", "readiness_score", "created_at"]
    search_fields = ["full_name", "target_role"]
    list_filter = ["target_role"]
    readonly_fields = ["created_at", "updated_at"]


@admin.register(Opportunity)
class OpportunityAdmin(admin.ModelAdmin):
    list_display = [
        "title",
        "provider",
        "opportunity_type",
        "is_free",
        "is_active",
        "created_at",
    ]
    search_fields = ["title", "provider", "description"]
    list_filter = ["opportunity_type", "is_free", "is_active", "mode"]
    readonly_fields = ["dedupe_hash", "created_at", "updated_at"]


@admin.register(ProfileMatch)
class ProfileMatchAdmin(admin.ModelAdmin):
    list_display = ["profile", "opportunity", "relevance_score", "is_bookmarked"]
    list_filter = ["is_bookmarked"]
    search_fields = ["profile__full_name", "opportunity__title"]


@admin.register(AcademicRecord)
class AcademicRecordAdmin(admin.ModelAdmin):
    list_display = ["student", "degree", "institution", "graduation_year", "cgpa"]
    search_fields = ["student__full_name", "institution"]


admin.site.register(OpportunitySkill)
