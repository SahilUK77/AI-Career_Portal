import logging
from celery import shared_task
from django.db import transaction
from .models import StudentProfile, Opportunity, OpportunitySkill, ProfileMatch
from .adapters.govt_schemes import GovtSchemesAdapter
from .adapters.course_portal import CoursePortalAdapter
from .ml_pipeline import calculate_opportunity_relevance
from .adapters.commercial_jobs import CommercialJobsAdapter

logger = logging.getLogger(__name__)

def ingest_from_adapter(adapter):
    """Executes an adapter, performs deduplication, and stores opportunities and skill links in MySQL."""
    raw_records = adapter.fetch()
    records_saved = 0

    for raw in raw_records:
        norm = adapter.normalize(raw)
        skills = norm.pop("skills", [])

        with transaction.atomic():
            opp, created = Opportunity.objects.update_or_create(
                dedupe_hash=norm["dedupe_hash"],
                defaults=norm
            )
            for s in skills:
                OpportunitySkill.objects.get_or_create(
                    opportunity=opp,
                    skill_name=s.strip()
                )
        records_saved += 1

    return records_saved

@shared_task(bind=True, max_retries=3)
def run_govt_schemes_scraper(self):
    try:
        count = ingest_from_adapter(GovtSchemesAdapter())
        logger.info(f"Successfully processed {count} government scheme opportunities.")
    except Exception as exc:
        logger.error(f"Error executing government schemes scraper: {exc}")
        raise self.retry(exc=exc, countdown=60)

@shared_task
def run_courses_scraper():
    adapters = [
        CoursePortalAdapter(),
        CommercialJobsAdapter()  # <-- Add your real-time API here
    ]

@shared_task(bind=True, max_retries=3)
def run_courses_scraper(self):
    try:
        count = ingest_from_adapter(CoursePortalAdapter())
        logger.info(f"Successfully processed {count} course/hackathon opportunities.")
    except Exception as exc:
        logger.error(f"Error executing courses scraper: {exc}")
        raise self.retry(exc=exc, countdown=60)

@shared_task(rate_limit='10/m')
def calculate_matches_for_profile(profile_id: int):
    """Calculates scores between an uploaded resume profile and active catalog listings."""
    try:
        profile = StudentProfile.objects.get(id=profile_id)
        active_opps = Opportunity.objects.filter(is_active=True).prefetch_related('required_skills')

        for opp in active_opps:
            score, matching_skills, reasoning = calculate_opportunity_relevance(
                candidate_skills=profile.current_skills,
                target_role=profile.target_role,
                opportunity=opp
            )

            # Persist matches above threshold or guaranteed schemes
            if score >= 30.0 or opp.opportunity_type == 'Scheme':
                ProfileMatch.objects.update_or_create(
                    profile=profile,
                    opportunity=opp,
                    defaults={
                        'relevance_score': score,
                        'matching_skills': matching_skills,
                        'reasoning': reasoning
                    }
                )
        logger.info(f"Completed match generation for student profile #{profile_id}")
    except StudentProfile.DoesNotExist:
        logger.error(f"Profile {profile_id} not found for match calculation.")