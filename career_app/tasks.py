import logging

from celery import shared_task
from django.db import transaction

from .ml_pipeline import calculate_opportunity_relevance
from .models import Opportunity, OpportunitySkill, ProfileMatch, StudentProfile

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=3)
def run_universal_scraper(self, profile_id: int):
    """Fetches live opportunities for a given student profile and stores them."""
    try:
        from .adapters.universal_scraper import UniversalScraperAdapter

        profile = StudentProfile.objects.get(id=profile_id)
        adapter = UniversalScraperAdapter()
        raw_records = adapter.fetch_all(profile.target_role)
        records_saved = 0
        for norm in raw_records:
            skills = norm.pop("skills", [])
            # Guard: skip records with empty or malformed URLs / titles
            if not norm.get("url") or not norm.get("title"):
                continue
            with transaction.atomic():
                opp, _created = Opportunity.objects.update_or_create(
                    dedupe_hash=norm["dedupe_hash"], defaults=norm
                )
                for s in skills:
                    if s and s.strip():
                        OpportunitySkill.objects.get_or_create(
                            opportunity=opp, skill_name=s.strip()
                        )
            records_saved += 1
        logger.info(
            f"Successfully processed {records_saved} universal opportunities for profile #{profile_id}."
        )

        # Trigger match scoring after fresh data ingestion
        calculate_matches_for_profile.delay(profile_id)

    except StudentProfile.DoesNotExist:
        logger.error(f"Profile {profile_id} not found for universal scraper task.")
    except Exception as exc:
        logger.exception("Error executing universal scraper for profile %s", profile_id)
        raise self.retry(exc=exc, countdown=60)


@shared_task(bind=True, max_retries=3)
def calculate_matches_for_profile(self, profile_id: int):
    """Calculates relevance scores between a student profile and active catalog listings."""
    try:
        profile = StudentProfile.objects.get(id=profile_id)
        active_opps = Opportunity.objects.filter(is_active=True).prefetch_related(
            "required_skills"
        )

        matched = 0
        for opp in active_opps:
            try:
                score, matching_skills, reasoning = calculate_opportunity_relevance(
                    candidate_skills=profile.current_skills,
                    target_role=profile.target_role,
                    opportunity=opp,
                )

                # Persist matches above threshold or all government schemes
                if score >= 30.0 or opp.opportunity_type == "Scheme":
                    ProfileMatch.objects.update_or_create(
                        profile=profile,
                        opportunity=opp,
                        defaults={
                            "relevance_score": score,
                            "matching_skills": matching_skills,
                            "reasoning": reasoning,
                        },
                    )
                    matched += 1
            except Exception as e:  # noqa: BLE001
                logger.warning(
                    f"Failed to calculate relevance for opportunity {opp.id}: {e}"
                )
                continue

        logger.info(
            f"Completed match generation for profile #{profile_id}: {matched} matches persisted."
        )
    except StudentProfile.DoesNotExist:
        logger.error(f"Profile {profile_id} not found for match calculation.")
    except Exception as exc:
        logger.exception("Error calculating matches for profile %s", profile_id)
        raise self.retry(exc=exc, countdown=60)


@shared_task
def nightly_refresh_all_profiles():
    """Beat task: refreshes opportunity data for all student profiles nightly."""
    profile_ids = list(
        StudentProfile.objects.exclude(target_role="").values_list("id", flat=True)
    )
    for pid in profile_ids:
        run_universal_scraper.delay(pid)
    logger.info(f"Nightly refresh: queued {len(profile_ids)} profile scraping jobs.")
