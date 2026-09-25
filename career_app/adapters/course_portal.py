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
                "title": "Junior .NET Core Developer",
                "provider": "Tech Mahindra (via MP Rojgar)",
                "opportunity_type": "Job",
                "is_free": True,
                "stipend_or_cost": "₹4,50,000 / year",
                "mode": "Hybrid",
                "location": "Indore, Madhya Pradesh",
                "url": "https://mprojgar.gov.in/",
                "description": "Entry-level enterprise web application development using ASP.NET Core, C#, and SQL Server.",
                "eligibility": "B.Tech/MCA/BCA with knowledge of Object Oriented Programming",
                "skills": [".NET Core", "C#", "ASP.NET", "SQL Server", "Entity Framework", "RESTful API"]
            },
            {
                "title": "Backend Engineering Internship (C# & .NET)",
                "provider": "TCS NextStep",
                "opportunity_type": "Internship",
                "is_free": True,
                "stipend_or_cost": "₹15,000 / month",
                "mode": "Online",
                "location": "Pan-India",
                "url": "https://nextstep.tcs.com/",
                "description": "6-month remote internship building microservices using C# and .NET 8.",
                "eligibility": "Pre-final or final year computer science students",
                "skills": ["C#", ".NET", "Web API", "Git", "SQL"]
            },
            {
                "title": "NPTEL: Programming in C# and .NET Framework",
                "provider": "IIT Kharagpur",
                "opportunity_type": "Course",
                "is_free": True,
                "stipend_or_cost": "Free to Audit",
                "mode": "Online",
                "location": "Pan-India",
                "url": "https://swayam.gov.in/",
                "description": "Comprehensive 12-week course covering advanced C# paradigms, memory management, and .NET web frameworks.",
                "eligibility": "Basic programming fundamentals required",
                "skills": ["C#", ".NET Framework", "Object-Oriented Programming", "ASP.NET"]
            },
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
            },
            {
                "title": "Full Stack Python Developer",
                "provider": "MP State Electronics Development Corporation",
                "opportunity_type": "Job",
                "is_free": True,
                "stipend_or_cost": "₹8,00,000 / year",
                "mode": "Hybrid",
                "location": "Bhopal, Madhya Pradesh",
                "url": "https://mpsedc.mp.gov.in/",
                "description": "Develop and maintain robust state e-governance platforms using Python, Django, and SQL databases.",
                "eligibility": "B.Tech/MCA with minimum 2 years experience in Python frameworks",
                "skills": ["Python", "Django", "SQL", "REST APIs", "Full Stack", "Git"]
            },
            {
                "title": "Java Backend Engineer",
                "provider": "Tech Mahindra (via MP Rojgar)",
                "opportunity_type": "Job",
                "is_free": True,
                "stipend_or_cost": "₹6,50,000 / year",
                "mode": "On-site",
                "location": "Indore, Madhya Pradesh",
                "url": "https://mprojgar.gov.in/",
                "description": "Build scalable enterprise microservices using Java Spring Boot.",
                "eligibility": "B.E./B.Tech in Computer Science",
                "skills": ["Java", "Spring Boot", "Microservices", "Hibernate", "MySQL"]
            },

            # --- FRONT-END & MOBILE ---
            {
                "title": "Front-End React Engineer",
                "provider": "Skill India Digital Hub",
                "opportunity_type": "Job",
                "is_free": True,
                "stipend_or_cost": "₹5,00,000 / year",
                "mode": "Remote",
                "location": "Pan-India",
                "url": "https://www.skillindiadigital.gov.in/",
                "description": "Create responsive and highly interactive user interfaces for educational tech platforms.",
                "eligibility": "Any Graduate with strong portfolio",
                "skills": ["React", "JavaScript", "HTML", "CSS", "Redux", "TypeScript"]
            },
            {
                "title": "Flutter Mobile App Developer Intern",
                "provider": "Startup India Initiative",
                "opportunity_type": "Internship",
                "is_free": True,
                "stipend_or_cost": "₹20,000 / month",
                "mode": "Hybrid",
                "location": "Bhopal, Madhya Pradesh",
                "url": "https://mprojgar.gov.in/",
                "description": "Assist in building cross-platform mobile applications for local agritech startups.",
                "eligibility": "Currently enrolled in a degree program",
                "skills": ["Flutter", "Dart", "Mobile Development", "Firebase", "UI/UX"]
            },

            # --- DATA, ML & AI ---
            {
                "title": "Data Scientist",
                "provider": "NASSCOM FutureSkills",
                "opportunity_type": "Job",
                "is_free": True,
                "stipend_or_cost": "₹12,00,000 / year",
                "mode": "Hybrid",
                "location": "Pune / Remote",
                "url": "https://futureskillsprime.in/",
                "description": "Analyze large datasets to extract actionable insights and build predictive models.",
                "eligibility": "Master's in Data Science, Statistics, or related field",
                "skills": ["Python", "Machine Learning", "Pandas", "Scikit-Learn", "Data Visualization", "SQL"]
            },
            {
                "title": "NPTEL: Deep Learning and AI Foundation",
                "provider": "IIT Madras",
                "opportunity_type": "Course",
                "is_free": True,
                "stipend_or_cost": "Free to Audit",
                "mode": "Online",
                "location": "Pan-India",
                "url": "https://swayam.gov.in/",
                "description": "Learn the fundamentals of neural networks, TensorFlow, and PyTorch.",
                "eligibility": "Basic Python and linear algebra knowledge",
                "skills": ["AI", "Deep Learning", "TensorFlow", "PyTorch", "Neural Networks"]
            },
            {
                "title": "Data Engineer",
                "provider": "MP Rojgar",
                "opportunity_type": "Job",
                "is_free": True,
                "stipend_or_cost": "₹9,00,000 / year",
                "mode": "On-site",
                "location": "Jabalpur, Madhya Pradesh",
                "url": "https://mprojgar.gov.in/",
                "description": "Design and optimize data pipelines and warehouse architecture.",
                "eligibility": "B.Tech with experience in big data tools",
                "skills": ["Apache Spark", "Hadoop", "ETL", "AWS", "Python", "SQL"]
            },

            # --- CLOUD, DEVOPS & SRE ---
            {
                "title": "Cloud Architect (AWS/Azure)",
                "provider": "Skill India Digital",
                "opportunity_type": "Job",
                "is_free": True,
                "stipend_or_cost": "₹18,00,000 / year",
                "mode": "Remote",
                "location": "Pan-India",
                "url": "https://www.skillindiadigital.gov.in/",
                "description": "Design secure, highly available, and scalable cloud infrastructure for government portals.",
                "eligibility": "5+ years experience, AWS/Azure certifications preferred",
                "skills": ["AWS", "Azure", "Cloud Architecture", "Kubernetes", "Terraform"]
            },
            {
                "title": "Site Reliability Engineer (SRE)",
                "provider": "Tech Mahindra",
                "opportunity_type": "Job",
                "is_free": True,
                "stipend_or_cost": "₹14,00,000 / year",
                "mode": "Hybrid",
                "location": "Indore, Madhya Pradesh",
                "url": "https://mprojgar.gov.in/",
                "description": "Bridge the gap between development and operations to ensure maximum system uptime.",
                "eligibility": "Experience with CI/CD and monitoring tools",
                "skills": ["Linux", "Docker", "Kubernetes", "CI/CD", "Prometheus", "DevOps"]
            },

            # --- HARDWARE, EMBEDDED & GAMING ---
            {
                "title": "Embedded Systems / IoT Engineer",
                "provider": "Smart City Mission MP",
                "opportunity_type": "Job",
                "is_free": True,
                "stipend_or_cost": "₹7,50,000 / year",
                "mode": "On-site",
                "location": "Gwalior, Madhya Pradesh",
                "url": "https://mprojgar.gov.in/",
                "description": "Develop firmware for smart city traffic and lighting sensors.",
                "eligibility": "B.E. in Electronics or Computer Science",
                "skills": ["C", "C++", "Microcontrollers", "IoT", "RTOS", "Firmware"]
            },
            {
                "title": "C++ Game Engine Developer",
                "provider": "Digital India Gaming Initiative",
                "opportunity_type": "Internship",
                "is_free": True,
                "stipend_or_cost": "₹25,000 / month",
                "mode": "Remote",
                "location": "Pan-India",
                "url": "https://www.skillindiadigital.gov.in/",
                "description": "Work on rendering engines and physics simulations for educational games.",
                "eligibility": "Strong math and C++ fundamentals",
                "skills": ["C++", "Unreal Engine", "3D Math", "OpenGL", "Game Development"]
            },

            # --- CYBERSECURITY & BLOCKCHAIN ---
            {
                "title": "Cybersecurity Analyst",
                "provider": "CERT-In Collaboration",
                "opportunity_type": "Job",
                "is_free": True,
                "stipend_or_cost": "₹8,50,000 / year",
                "mode": "Hybrid",
                "location": "Bhopal, Madhya Pradesh",
                "url": "https://mprojgar.gov.in/",
                "description": "Monitor network traffic for security breaches and conduct vulnerability assessments.",
                "eligibility": "CEH or CompTIA Security+ certification",
                "skills": ["Network Security", "Penetration Testing", "Linux", "SIEM", "Cryptography"]
            },
            {
                "title": "Blockchain Smart Contract Developer",
                "provider": "NITI Aayog Tech Hub",
                "opportunity_type": "Job",
                "is_free": True,
                "stipend_or_cost": "₹15,00,000 / year",
                "mode": "Remote",
                "location": "Pan-India",
                "url": "https://www.skillindiadigital.gov.in/",
                "description": "Develop decentralized applications (dApps) for secure land registry management.",
                "eligibility": "Experience with Web3 and Ethereum",
                "skills": ["Solidity", "Blockchain", "Web3.js", "Ethereum", "Smart Contracts"]
            },

            # --- QA, SDET & IT SUPPORT ---
            {
                "title": "Software Development Engineer in Test (SDET)",
                "provider": "TCS NextStep",
                "opportunity_type": "Job",
                "is_free": True,
                "stipend_or_cost": "₹7,00,000 / year",
                "mode": "On-site",
                "location": "Indore, Madhya Pradesh",
                "url": "https://nextstep.tcs.com/",
                "description": "Build automated testing frameworks for continuous integration pipelines.",
                "eligibility": "B.Tech with coding proficiency",
                "skills": ["Selenium", "Java", "Python", "Test Automation", "CI/CD", "API Testing"]
            },
            {
                "title": "Network Engineer / Help Desk Technician",
                "provider": "MP State Wide Area Network (SWAN)",
                "opportunity_type": "Job",
                "is_free": True,
                "stipend_or_cost": "₹3,50,000 / year",
                "mode": "On-site",
                "location": "Bhopal, Madhya Pradesh",
                "url": "https://mpsedc.mp.gov.in/",
                "description": "Provide L2 technical support and maintain local intranet infrastructure for govt offices.",
                "eligibility": "Diploma or B.Sc in IT/Networking",
                "skills": ["Networking", "Troubleshooting", "TCP/IP", "Windows Server", "Help Desk"]
            },

            # --- MANAGEMENT & LEADERSHIP ---
            {
                "title": "Engineering Manager",
                "provider": "Startup India Tech Hub",
                "opportunity_type": "Job",
                "is_free": True,
                "stipend_or_cost": "₹25,00,000 / year",
                "mode": "Hybrid",
                "location": "Indore, Madhya Pradesh",
                "url": "https://mprojgar.gov.in/",
                "description": "Lead cross-functional engineering teams, oversee software architecture, and drive agile delivery.",
                "eligibility": "8+ years of engineering experience with 2+ years in management",
                "skills": ["Team Leadership", "System Architecture", "Agile", "Project Management", "Scrum"]
            },
            {
                "title": "Technical Product Manager",
                "provider": "Skill India Digital",
                "opportunity_type": "Job",
                "is_free": True,
                "stipend_or_cost": "₹16,00,000 / year",
                "mode": "Remote",
                "location": "Pan-India",
                "url": "https://www.skillindiadigital.gov.in/",
                "description": "Define product roadmaps and work closely with dev teams to launch high-impact digital tools.",
                "eligibility": "Experience in product lifecycle management and tech background",
                "skills": ["Product Strategy", "Agile", "Jira", "User Experience (UX)", "Data Analytics"]
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