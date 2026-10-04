from unittest.mock import patch

from django.contrib.auth.models import User
from django.test import TestCase
from rest_framework import status
from rest_framework.test import APIClient

from career_app.models import (
    AcademicRecord,
    Opportunity,
    ProfileMatch,
    ResumeAnalysis,
    StudentProfile,
)


class CareerAppTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(
            username="testuser", password="testpassword"
        )
        self.profile = StudentProfile.objects.create(
            user=self.user,
            target_role="Software Engineer",
            current_skills=["Python", "Django"],
        )

        self.opportunity = Opportunity.objects.create(
            dedupe_hash="opp1",
            title="Django Developer",
            provider="TechCorp",
            opportunity_type="Job",
            is_free=True,
            url="http://example.com/job1",
        )
        ProfileMatch.objects.create(
            profile=self.profile, opportunity=self.opportunity, relevance_score=85.0
        )

    def test_login_api(self):
        response = self.client.post(
            "/api/login/",
            {"username": "testuser", "password": "testpassword"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("user_id", response.data)

    def test_register_api(self):
        response = self.client.post(
            "/api/register/",
            {"username": "newuser", "password": "newpassword", "email": "new@test.com"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(User.objects.filter(username="newuser").exists())

    def test_opportunities_list(self):
        response = self.client.get("/api/opportunities/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertGreaterEqual(len(response.data["results"]), 1)

    def test_opportunities_can_filter_by_type_and_free_status(self):
        Opportunity.objects.create(
            dedupe_hash="opp2",
            title="Paid Bootcamp",
            provider="LearnCorp",
            opportunity_type="Course",
            is_free=False,
            url="http://example.com/course1",
        )

        response = self.client.get(
            "/api/opportunities/", {"type": "job", "is_free": "true"}
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["results"]), 1)
        self.assertEqual(response.data["results"][0]["title"], "Django Developer")

    def test_opportunity_types_api(self):
        response = self.client.get("/api/opportunities/types/")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data, ["Job"])

    def test_recommendations_api(self):
        self.client.force_authenticate(user=self.user)
        response = self.client.get("/api/recommendations/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("opportunities", response.data)
        self.assertEqual(len(response.data["opportunities"]), 1)

    def test_profile_unauthenticated(self):
        # Should block access to profiles without auth
        response = self.client.get("/api/profiles/")
        self.assertIn(
            response.status_code,
            [status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN],
        )

    def test_toggle_bookmark(self):
        self.client.force_authenticate(user=self.user)
        match = ProfileMatch.objects.first()
        response = self.client.post(f"/api/bookmark/{match.id}/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data["is_bookmarked"])

        response = self.client.post(f"/api/bookmark/{match.id}/")
        self.assertFalse(response.data["is_bookmarked"])

    def test_resume_and_cover_letter_history_are_scoped_to_user(self):
        ResumeAnalysis.objects.create(
            user=self.user,
            target_role="Software Engineer",
            current_skills=["Python"],
        )
        ProfileMatch.objects.filter(profile=self.profile).update(
            cover_letter="Dear hiring team"
        )

        self.client.force_authenticate(user=self.user)
        resume_response = self.client.get("/api/resume-history/")
        cover_letter_response = self.client.get("/api/cover-letter-history/")

        self.assertEqual(resume_response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(resume_response.data["results"]), 1)
        self.assertEqual(cover_letter_response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(cover_letter_response.data["results"]), 1)
        self.assertIn("created_at", cover_letter_response.data["results"][0])

    @patch("career_app.views.os.getenv", return_value=None)
    def test_chatbot_local_fallback(self, _mock_getenv):
        self.client.force_authenticate(user=self.user)

        response = self.client.post(
            "/api/chatbot/",
            {"message": "How should I improve my resume?"},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("resume", response.data["response"].lower())

    def test_chatbot_requires_message(self):
        self.client.force_authenticate(user=self.user)

        response = self.client.post("/api/chatbot/", {}, format="json")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    @patch("career_app.views.os.getenv", return_value=None)
    def test_cover_letter_uses_local_fallback_without_api_key(self, _mock_getenv):
        self.client.force_authenticate(user=self.user)

        response = self.client.post(f"/api/cover-letter/{self.opportunity.id}/")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("Django Developer", response.data["cover_letter"])
        self.assertTrue(
            ProfileMatch.objects.get(
                profile=self.profile, opportunity=self.opportunity
            ).cover_letter
        )

    @patch("career_app.views.os.getenv", return_value=None)
    def test_interview_evaluation_uses_local_fallback_without_api_key(
        self, _mock_getenv
    ):
        self.client.force_authenticate(user=self.user)

        response = self.client.post(
            "/api/interview-evaluate/",
            {
                "question": "Describe a project you delivered.",
                "answer": "I improved the deployment process and reduced release time.",
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("Rating:", response.data["feedback"])

    def test_social_login_invalid_token(self):
        response = self.client.post(
            "/api/social-login/", {"token": "invalid_token"}, format="json"
        )
        # Google Auth will throw ValueError for 'invalid_token'
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    @patch("career_app.views.id_token.verify_oauth2_token")
    def test_social_login_creates_profile_and_returns_username(self, mock_verify):
        mock_verify.return_value = {
            "email": "google-user@example.com",
            "name": "Google User",
        }

        response = self.client.post(
            "/api/social-login/", {"token": "valid-token"}, format="json"
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        user = User.objects.get(username="google-user@example.com")
        self.assertEqual(response.data["username"], user.username)
        self.assertTrue(StudentProfile.objects.filter(user=user).exists())

    @patch("career_app.views.analyze_resume")
    @patch("career_app.tasks.run_universal_scraper.delay")
    def test_upload_resume_api(self, mock_scraper, mock_analyze):
        # Mock analysis result
        class MockAnalysis:
            def __init__(self):
                self.full_name = "Jane Doe"
                self.target_professions = ["Data Scientist"]
                self.extracted_skills = ["Python"]
                self.skill_gaps = []
                self.recommended_courses = []
                self.resume_improvements = []
                self.interview_questions = []
                self.summary = "Data-focused software professional."
                self.projects = ["Resume analyzer"]
                self.experience = ["Software engineering intern"]
                self.academic_records = [
                    {
                        "degree": "B.Tech",
                        "institution": "Example University",
                        "graduation_year": 2024,
                        "cgpa": 8.5,
                    }
                ]

        mock_analyze.return_value = MockAnalysis()

        self.client.force_authenticate(user=self.user)
        # We simulate a PDF file upload
        from django.core.files.uploadedfile import SimpleUploadedFile

        pdf = SimpleUploadedFile(
            "resume.pdf", b"file_content", content_type="application/pdf"
        )

        response = self.client.post(
            "/api/upload-resume/", {"resume": pdf}, format="multipart"
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["full_name"], "Jane Doe")
        self.assertEqual(response.data["target_role"], "Data Scientist")
        self.assertEqual(response.data["bio"], "Data-focused software professional.")
        self.assertEqual(len(response.data["academic_records"]), 1)
        self.assertEqual(AcademicRecord.objects.count(), 1)
