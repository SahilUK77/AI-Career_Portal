import os
import requests
from typing import List, Dict, Any
from .base import BaseAdapter

class CommercialJobsAdapter(BaseAdapter):
    def __init__(self):
        super().__init__(provider_name="Commercial Boards (LinkedIn/Indeed)")
        self.api_key = os.environ.get("RAPIDAPI_KEY")

    def fetch(self) -> List[Dict[str, Any]]:
        if not self.api_key:
            print("Missing RAPIDAPI_KEY. Skipping commercial jobs.")
            return []
            
        url = "https://jsearch.p.rapidapi.com/search"
        # You can change this query dynamically later based on the user's profile
        querystring = {"query": "Software Engineer in Madhya Pradesh", "page": "1", "num_pages": "1"}
        
        headers = {
            "X-RapidAPI-Key": self.api_key,
            "X-RapidAPI-Host": "jsearch.p.rapidapi.com"
        }
        
        try:
            response = requests.get(url, headers=headers, params=querystring)
            if response.status_code == 200:
                # Returns the live jobs from LinkedIn, Indeed, Glassdoor, etc.
                return response.json().get("data", [])
            return []
        except Exception as e:
            print(f"Failed to fetch commercial jobs: {e}")
            return []

    def normalize(self, raw_item: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "dedupe_hash": self.compute_dedupe_hash(
                raw_item.get("job_apply_link", ""), 
                raw_item.get("job_title", "")
            ),
            "title": raw_item.get("job_title", "Unknown Role"),
            "provider": raw_item.get("employer_name", "Unknown Company"),
            "opportunity_type": "Job",
            "is_free": True,
            "stipend_or_cost": "Salary Undisclosed",
            "mode": "Remote" if raw_item.get("job_is_remote") else "On-site",
            "location": f"{raw_item.get('job_city', '')}, {raw_item.get('job_country', '')}",
            # This is the actual, working URL to apply on LinkedIn/Indeed
            "url": raw_item.get("job_apply_link", ""), 
            "description": raw_item.get("job_description", "")[:500] + "...",
            "eligibility": "See job description for details",
            # We leave skills empty; your Gemini background task will read the description and find the skills automatically!
            "skills": [], 
            "metadata_json": {"source": "jsearch_rapidapi"}
        }