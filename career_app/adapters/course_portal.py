import logging
from typing import List, Dict, Any
from .base import BaseAdapter

logger = logging.getLogger(__name__)

class CoursePortalAdapter(BaseAdapter):
    def __init__(self):
        super().__init__(provider_name="Tech Career Catalog")

    def fetch(self) -> List[Dict[str, Any]]:
        return [
            {
                "title": "Smart India Hackathon (SIH) Collegiate Edition",
                "provider": "AICTE / MoE Innovation Cell",
                "opportunity_type": "Hackathon",
                "is_free": True,
                "stipend_or_cost": "Cash Prizes Up to ₹1,00,000",
                "mode": "Hybrid",
                "location": "Pan-India",
                "url": "https://www.sih.gov.in/",
                "description": "Nationwide digital product building challenge focused on agriculture, education, state governance, and AI applications.",
                "eligibility": "Regular college students pursuing graduation or post-graduation",
                "skills": ["RESTful API Development", "Predictive Modeling", "Containerization", "Python"]
            },
            {
                "title": "Junior Data Analyst Internship",
                "provider": "MP State Electronics Development Corporation (MPSeDC)",
                "opportunity_type": "Internship",
                "is_free": True,
                "stipend_or_cost": "₹15,000 / month",
                "mode": "Hybrid",
                "location": "Bhopal, Madhya Pradesh",
                "url": "https://mpsedc.mp.gov.in/",
                "description": "3-month paid internship developing departmental analytics dashboards and automated report generation systems.",
                "eligibility": "B.Sc Maths/Stats, BCA, B.Tech or relevant IT degrees",
                "skills": ["Data Visualization", "SQL", "Advanced Excel", "Power BI", "Tableau"]
            }
        ]

    def normalize(self, raw_item: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "dedupe_hash": self.compute_dedupe_hash(raw_item["url"], raw_item["title"]),
            "title": raw_item["title"],
            "provider": raw_item["provider"],
            "opportunity_type": raw_item["opportunity_type"],
            "is_free": raw_item.get("is_free", True),
            "stipend_or_cost": raw_item.get("stipend_or_cost", "Free"),
            "mode": raw_item.get("mode", "Online"),
            "location": raw_item.get("location", "Pan-India"),
            "url": raw_item["url"],
            "description": raw_item.get("description", ""),
            "eligibility": raw_item.get("eligibility", ""),
            "skills": raw_item.get("skills", []),
            "metadata_json": {"source": "direct_partner_feed"}
        }