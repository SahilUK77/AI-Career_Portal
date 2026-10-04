import json
import os

from django.conf import settings
from django.core.management.base import BaseCommand

from career_app.models import (
    CareerRole,
    CourseRecommendation,
    InterviewQuestion,
    RoleSkill,
)


class Command(BaseCommand):
    help = "Seeds the database with essential Career Roles, Skills, Courses and Interview Questions from JSON"

    def add_arguments(self, parser):
        parser.add_argument(
            "--file",
            type=str,
            help="Path to the JSON file containing core career data",
            default=os.path.join(
                settings.BASE_DIR,
                "career-readiness-platform",
                "Additional Scripts",
                "core_career_data.json",
            ),
        )

    def handle(self, *args, **kwargs):
        json_file_path = kwargs["file"]

        if not os.path.exists(json_file_path):
            self.stdout.write(
                self.style.ERROR(f"Data file not found: {json_file_path}")
            )
            return

        with open(json_file_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        for item in data:
            target_role = item.get("target_role")
            if not target_role:
                continue

            role_obj, _ = CareerRole.objects.get_or_create(title=target_role)

            mandatory_skills = item.get("mandatory_skills", [])
            for skill in mandatory_skills:
                RoleSkill.objects.get_or_create(role=role_obj, skill_name=skill)

            recommended_courses = item.get("recommended_courses", [])
            for i, course in enumerate(recommended_courses):
                # If there are courses, assign them to the first few skills
                # (or just the first skill if it's general)
                target_skill = (
                    mandatory_skills[i % len(mandatory_skills)]
                    if mandatory_skills
                    else "General"
                )
                CourseRecommendation.objects.get_or_create(
                    skill_name=target_skill,
                    course_title=course.get("course_name", "Unknown Course"),
                    defaults={
                        "provider": course.get("provider", "Unknown Provider"),
                    },
                )

            # Seed interview questions from JSON, with fallback
            interview_questions = item.get("interview_questions", [])
            if not interview_questions:
                interview_questions = [
                    f"What is your experience with {skill}?"
                    for skill in mandatory_skills[:3]
                ]

            for q in interview_questions:
                InterviewQuestion.objects.get_or_create(role=role_obj, question_text=q)

        self.stdout.write(self.style.SUCCESS("Successfully seeded database from JSON!"))
