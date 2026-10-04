import asyncio
import hashlib
import logging
import os
import urllib.parse

import httpx
from bs4 import BeautifulSoup

NS = "Not Specified"

logger = logging.getLogger(__name__)


class UniversalScraperAdapter:
    def __init__(self):
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
        }

    def _compute_hash(self, url: str) -> str:
        return hashlib.sha256(url.encode("utf-8")).hexdigest()

    async def scrape_internshala(self, query: str) -> list[dict]:
        """Live scrape from Internshala"""
        results = []
        try:
            query_formatted = urllib.parse.quote(query.replace(" ", "-"))
            url = f"https://internshala.com/internships/keywords-{query_formatted}/"
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    url, headers=self.headers, follow_redirects=True, timeout=10.0
                )

            if response.status_code == 200:
                soup = BeautifulSoup(response.text, "html.parser")
                cards = soup.find_all("div", class_="individual_internship")

                for card in cards[:3]:
                    title_elem = card.find("h3", class_="heading_4_5")
                    company_elem = card.find("p", class_="company_name") or card.find(
                        "a", class_="link_display_like_text"
                    )
                    if title_elem and company_elem:
                        title = title_elem.text.strip()
                        company = company_elem.text.strip()
                        link_tag = title_elem.find("a")
                        job_url = (
                            "https://internshala.com" + link_tag["href"]
                            if link_tag
                            else url
                        )

                        results.append(
                            {
                                "dedupe_hash": self._compute_hash(job_url),
                                "title": title,
                                "provider": f"Internshala - {company}",
                                "opportunity_type": "Internship",
                                "is_free": True,
                                "stipend_or_cost": NS,
                                "mode": NS,
                                "location": NS,
                                "url": job_url,
                                "description": f"Internship at {company} as {title}.",
                                "eligibility": "Students & Graduates",
                                "skills": [query],
                            }
                        )
        except Exception as e:  # noqa: BLE001
            logger.warning(f"Internshala scraping error: {e}")
        return results

    async def scrape_google_dorks(
        self, query: str, site: str, provider: str, opp_type: str
    ) -> list[dict]:
        """Live scrape relying on Google/DuckDuckGo syntax for sites that block bots (LinkedIn/Naukri)"""
        results = []
        try:
            # Using DuckDuckGo HTML for simple scraping without JS
            url = f"https://html.duckduckgo.com/html/?q=site:{site}+{urllib.parse.quote(query)}+{urllib.parse.quote(opp_type)}"
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    url, headers=self.headers, follow_redirects=True, timeout=10.0
                )

            if response.status_code == 200:
                soup = BeautifulSoup(response.text, "html.parser")
                results_divs = soup.find_all("div", class_="result")

                for div in results_divs[:3]:
                    title_elem = div.find("h2", class_="result__title")
                    snippet_elem = div.find("a", class_="result__snippet")
                    link_elem = div.find("a", class_="result__url", href=True)

                    if title_elem and link_elem:
                        raw_url = link_elem["href"]
                        # DuckDuckGo wraps links in /l/?uddg=...
                        parsed_url = urllib.parse.urlparse(raw_url)
                        qs = urllib.parse.parse_qs(parsed_url.query)
                        job_url = qs.get("uddg", [raw_url])[0]

                        title = title_elem.text.strip()
                        desc = snippet_elem.text.strip() if snippet_elem else ""

                        if len(title) > 5 and site in job_url:
                            results.append(
                                {
                                    "dedupe_hash": self._compute_hash(job_url),
                                    "title": title[:100],
                                    "provider": provider,
                                    "opportunity_type": opp_type.capitalize(),
                                    "is_free": True,
                                    "stipend_or_cost": NS,
                                    "mode": NS,
                                    "location": NS,
                                    "url": job_url,
                                    "description": desc,
                                    "eligibility": "Varies",
                                    "skills": [query],
                                }
                            )
        except Exception as e:  # noqa: BLE001
            logger.warning(f"DuckDuckGo scraping error for {site}: {e}")
        return results

    async def fetch_adzuna_jobs(self, query: str) -> list[dict]:
        """Fetch live jobs using the Adzuna API."""
        results = []
        app_id = os.getenv("ADZUNA_APP_ID")
        app_key = os.getenv("ADZUNA_APP_KEY")
        if not app_id or not app_key:
            return results

        try:
            url = "https://api.adzuna.com/v1/api/jobs/in/search/1"
            params = {
                "app_id": app_id,
                "app_key": app_key,
                "results_per_page": 5,
                "what": query,
            }
            async with httpx.AsyncClient() as client:
                response = await client.get(url, params=params, timeout=10.0)

            if response.status_code == 200:
                data = response.json()
                for job in data.get("results", []):
                    results.append(
                        {
                            "dedupe_hash": self._compute_hash(
                                job.get("redirect_url", "")
                            ),
                            "title": job.get("title", ""),
                            "provider": f"Adzuna - {job.get('company', {}).get('display_name', 'Unknown')}",
                            "opportunity_type": "Job",
                            "is_free": True,
                            "stipend_or_cost": "Salary",
                            "mode": "Hybrid",
                            "location": job.get("location", {}).get(
                                "display_name", "India"
                            ),
                            "url": job.get("redirect_url", ""),
                            "description": job.get("description", "")[:200] + "...",
                            "eligibility": "Varies",
                            "skills": [query],
                        }
                    )
        except Exception as e:  # noqa: BLE001
            logger.warning(f"Adzuna API error: {e}")
        return results

    async def fetch_youtube_tutorials(self, query: str) -> list[dict]:
        """Fetch free tutorials using the YouTube Data API v3."""
        results = []
        api_key = os.getenv("YOUTUBE_API_KEY")
        if not api_key:
            return results

        try:
            url = "https://www.googleapis.com/youtube/v3/search"
            params = {
                "part": "snippet",
                "q": f"{query} tutorial course",
                "type": "video",
                "maxResults": 5,
                "key": api_key,
            }
            async with httpx.AsyncClient() as client:
                response = await client.get(url, params=params, timeout=10.0)

            if response.status_code == 200:
                data = response.json()
                for item in data.get("items", []):
                    video_id = item.get("id", {}).get("videoId")
                    if not video_id:
                        continue
                    snippet = item.get("snippet", {})
                    video_url = f"https://www.youtube.com/watch?v={video_id}"
                    results.append(
                        {
                            "dedupe_hash": self._compute_hash(video_url),
                            "title": snippet.get("title", ""),
                            "provider": f"YouTube - {snippet.get('channelTitle', '')}",
                            "opportunity_type": "Course",
                            "is_free": True,
                            "stipend_or_cost": NS,
                            "mode": NS,
                            "location": NS,
                            "url": video_url,
                            "description": snippet.get("description", "")[:200] + "...",
                            "eligibility": "Everyone",
                            "skills": [query],
                        }
                    )
        except Exception as e:  # noqa: BLE001
            logger.warning(f"YouTube API error: {e}")
        return results

    async def fetch_jobs_and_internships(self, query: str) -> list[dict]:
        """Concurrently run live scrapers"""
        results = []
        tasks = [
            self.scrape_internshala(query),
            self.scrape_google_dorks(query, "naukri.com/job-listings", "Naukri", "job"),
            self.scrape_google_dorks(query, "linkedin.com/jobs", "LinkedIn", "job"),
            self.scrape_google_dorks(query, "aicte-india.org", "AICTE", "internship"),
            self.fetch_adzuna_jobs(query),
        ]
        scraped_data = await asyncio.gather(*tasks)
        for data in scraped_data:
            results.extend(data)
        return results

    async def fetch_schemes_and_courses(self, query: str) -> list[dict]:
        """Fetch general Hackathons, MPSeDC, and MMSKY opportunities via search indexing"""
        results = []
        tasks = [
            self.scrape_google_dorks(
                "hackathon", "unstop.com", "Unstop Hackathons", "Hackathon"
            ),
            self.scrape_google_dorks(
                "scholarship", "buddy4study.com", "Buddy4Study", "Scholarship"
            ),
            self.scrape_google_dorks(
                "workshop", "eventbrite.com", "Eventbrite", "Workshop"
            ),
            self.scrape_google_dorks(
                "skill", "mmsky.mp.gov.in", "MMSKY (MP Govt)", "Scheme"
            ),
            self.scrape_google_dorks(
                "course", "nptel.ac.in", "IIT Madras / Ministry of Education", "Course"
            ),
            self.fetch_youtube_tutorials(query),
        ]
        scraped_data = await asyncio.gather(*tasks)
        for data in scraped_data:
            results.extend(data)
        return results

    def fetch_all(self, target_role: str) -> list[dict]:
        """Synchronous wrapper for Celery tasks"""
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            jobs = loop.run_until_complete(self.fetch_jobs_and_internships(target_role))
            schemes = loop.run_until_complete(
                self.fetch_schemes_and_courses(target_role)
            )
            return jobs + schemes
        finally:
            loop.close()
