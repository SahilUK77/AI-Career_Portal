import logging
from typing import List, Dict, Any
from .base import BaseAdapter

logger = logging.getLogger(__name__)

class GovtSchemesAdapter(BaseAdapter):
    def __init__(self):
        super().__init__(provider_name="Govt of India / MP Skill Portals")

    def fetch(self) -> List[Dict[str, Any]]:
        # Seeded ingestion targets: In production, query public JSON endpoints (e.g., Skill India, NPTEL, MP Rojgar)
        return [
            {
                "title": "Mukhyamantri Seekho Kamao Yojana (MMSKY)",
                "provider": "MP State Skill Development",
                "opportunity_type": "Scheme",
                "is_free": True,
                "stipend_or_cost": "Stipend ₹8,000 - ₹10,000/month",
                "mode": "Offline",
                "location": "Madhya Pradesh",
                "url": "https://mmsky.mp.gov.in/",
                "description": "On-the-job training program for youth in Madhya Pradesh across technical, industrial, and software domains with monthly allowance.",
                "eligibility": "12th / ITI / Diploma / Any Graduate (Age 18-29)",
                "skills": ["Data Cleaning", "Advanced Excel", "Office Automation", "Python"]
            },
            {
                "title": "Skill India Digital Free IT & Cloud Certification",
                "provider": "NSDC / Skill India Digital",
                "opportunity_type": "Certification",
                "is_free": True,
                "stipend_or_cost": "100% Free Government Verified",
                "mode": "Online",
                "location": "Pan-India",
                "url": "https://www.skillindiadigital.gov.in/",
                "description": "Government supported national certification in cloud fundamentals, data analytics, and digital technology tools.",
                "eligibility": "Open to all enrolled college students and graduates",
                "skills": ["Cloud Platforms", "AWS", "Azure", "Data Visualization", "SQL"]
            },
            {
                "title": "SWAYAM NPTEL: Python for Data Science & AI",
                "provider": "Ministry of Education / IIT Madras",
                "opportunity_type": "Course",
                "is_free": True,
                "stipend_or_cost": "Free to Audit / Optional ₹1000 Exam Fee",
                "mode": "Online",
                "location": "Pan-India",
                "url": "https://swayam.gov.in/nc_details/NPTEL",
                "description": "Comprehensive university-grade course addressing practical data science, numpy, pandas, and predictive statistics.",
                "eligibility": "Basic knowledge of high school mathematics or programming",
                "skills": ["Python", "Data Cleaning", "Predictive Modeling", "Pandas", "NumPy"]
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
            "metadata_json": {"source": "official_portal_feed"}
        }