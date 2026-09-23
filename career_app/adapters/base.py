import hashlib
from abc import ABC, abstractmethod
from typing import List, Dict, Any

class BaseAdapter(ABC):
    """Base interface and deduplication contract for opportunity ingestion."""
    
    def __init__(self, provider_name: str):
        self.provider_name = provider_name
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36 CareerAIBot/2.0",
            "Accept": "application/json, text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8"
        }

    @abstractmethod
    def fetch(self) -> List[Dict[str, Any]]:
        """Fetch raw listings from API or HTML endpoints."""
        pass

    @abstractmethod
    def normalize(self, raw_item: Dict[str, Any]) -> Dict[str, Any]:
        """Normalize raw attributes into the standard schema dictionary."""
        pass

    def compute_dedupe_hash(self, url: str, title: str) -> str:
        """Create a deterministic SHA-256 fingerprint for idempotency."""
        normalized_str = f"{self.provider_name.strip().lower()}|{title.strip().lower()}|{url.strip().lower()}"
        return hashlib.sha256(normalized_str.encode('utf-8')).hexdigest()