"""
Data Normalizer Module
======================
Transforms raw scraped data from any source into a standardized format.

This ensures consistency across all hackathon sources, making it easy to
search, filter, and display data regardless of where it came from.
"""

import re
import hashlib
from datetime import datetime, date
from typing import Dict, List, Optional, Any, Union
from dataclasses import dataclass, asdict, field
from enum import Enum


class EventMode(Enum):
    """Event participation modes."""
    IN_PERSON = "in-person"
    ONLINE = "online"
    HYBRID = "hybrid"
    UNKNOWN = "unknown"


class EventStatus(Enum):
    """Current status of the event."""
    UPCOMING = "upcoming"
    ONGOING = "ongoing"
    ENDED = "ended"
    UNKNOWN = "unknown"


@dataclass
class HackathonEvent:
    """
    Standardized hackathon event data structure.
    
    This is the canonical format for all hackathon data in our system.
    Every scraper must convert its raw data to this format.
    """
    # Required fields
    id: str                          # Unique identifier (generated hash)
    source: str                      # Source platform (e.g., "MLH", "Devpost")
    title: str                       # Event name
    url: str                         # Registration/info URL
    
    # Date fields
    start_date: Optional[str] = None         # ISO format: "2026-02-15"
    end_date: Optional[str] = None           # ISO format: "2026-02-17"
    registration_deadline: Optional[str] = None
    
    # Location fields
    location: Optional[str] = None           # City, Country or "Online"
    mode: str = EventMode.UNKNOWN.value      # in-person, online, hybrid
    
    # Details
    description: Optional[str] = None        # Short description
    prize_pool: Optional[str] = None         # "$10,000" or "10000" (normalized)
    prize_pool_numeric: Optional[float] = 0  # Numeric value for sorting
    
    # Categorization
    tags: List[str] = field(default_factory=list)   # ["AI", "Web3", "Student"]
    themes: List[str] = field(default_factory=list)  # ["Healthcare", "Climate"]
    
    # Images
    image_url: Optional[str] = None
    logo_url: Optional[str] = None
    
    # Metadata
    organizer: Optional[str] = None
    participants_count: Optional[int] = None
    team_size_min: Optional[int] = None
    team_size_max: Optional[int] = None
    
    # System fields
    status: str = EventStatus.UNKNOWN.value
    scraped_at: Optional[str] = None         # When we scraped this
    last_updated: Optional[str] = None       # When source last updated
    
    def to_dict(self) -> Dict:
        """Convert to dictionary for JSON serialization."""
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'HackathonEvent':
        """Create from dictionary."""
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})


class DataNormalizer:
    """
    Transforms raw scraped data into standardized HackathonEvent objects.
    
    Handles:
    - Date parsing (multiple formats)
    - Prize normalization ($10k -> 10000)
    - Location standardization
    - Mode detection (in-person/online/hybrid)
    - Tag extraction
    - Unique ID generation
    """
    
    def __init__(self):
        # Common date formats we encounter
        self.date_formats = [
            "%Y-%m-%d",                    # 2026-02-15
            "%B %d, %Y",                   # February 15, 2026
            "%b %d, %Y",                   # Feb 15, 2026
            "%d %B %Y",                    # 15 February 2026
            "%d %b %Y",                    # 15 Feb 2026
            "%m/%d/%Y",                    # 02/15/2026
            "%d/%m/%Y",                    # 15/02/2026
            "%Y/%m/%d",                    # 2026/02/15
            "%B %d",                       # February 15 (assume current year)
            "%b %d",                       # Feb 15
        ]
        
        # Keywords that indicate online events
        self.online_keywords = [
            "online", "virtual", "remote", "worldwide", "global",
            "anywhere", "digital", "internet", "web-based"
        ]
        
        # Keywords that indicate in-person events
        self.in_person_keywords = [
            "in-person", "in person", "onsite", "on-site", "offline",
            "physical", "venue", "campus"
        ]
        
        # Common tag mappings for normalization
        self.tag_mappings = {
            "artificial intelligence": "AI",
            "machine learning": "ML",
            "blockchain": "Web3",
            "cryptocurrency": "Web3",
            "smart contracts": "Web3",
            "defi": "Web3",
            "nft": "Web3",
            "healthcare": "Health",
            "health tech": "Health",
            "financial technology": "FinTech",
            "internet of things": "IoT",
            "augmented reality": "AR/VR",
            "virtual reality": "AR/VR",
            "open source": "Open Source",
        }
    
    def normalize(self, raw_data: Dict, source: str) -> HackathonEvent:
        """
        Main normalization method. Takes raw scraped data and returns
        a standardized HackathonEvent object.
        
        Args:
            raw_data: Raw dictionary from scraper
            source: Source platform name (e.g., "MLH")
            
        Returns:
            HackathonEvent: Normalized event object
        """
        # Generate unique ID
        unique_id = self._generate_id(source, raw_data)
        
        # Extract and normalize each field
        title = self._normalize_text(raw_data.get('title', ''))
        url = self._normalize_url(raw_data.get('url', ''))
        
        # Parse dates
        start_date = self._parse_date(raw_data.get('start_date') or raw_data.get('date'))
        end_date = self._parse_date(raw_data.get('end_date'))
        deadline = self._parse_date(raw_data.get('deadline') or raw_data.get('registration_deadline'))
        
        # Parse location and mode
        location = self._normalize_location(raw_data.get('location', ''))
        mode = self._detect_mode(location, raw_data)
        
        # Parse prize
        prize_str, prize_num = self._normalize_prize(raw_data.get('prize') or raw_data.get('prize_pool'))
        
        # Parse tags
        tags = self._normalize_tags(raw_data.get('tags', []))
        
        # Determine status
        status = self._determine_status(start_date, end_date)
        
        return HackathonEvent(
            id=unique_id,
            source=source,
            title=title,
            url=url,
            start_date=start_date,
            end_date=end_date,
            registration_deadline=deadline,
            location=location,
            mode=mode,
            description=self._normalize_text(raw_data.get('description', ''))[:500],
            prize_pool=prize_str,
            prize_pool_numeric=prize_num,
            tags=tags,
            themes=raw_data.get('themes', []),
            image_url=raw_data.get('image_url') or raw_data.get('image'),
            logo_url=raw_data.get('logo_url') or raw_data.get('logo'),
            organizer=raw_data.get('organizer'),
            participants_count=self._parse_int(raw_data.get('participants')),
            team_size_min=self._parse_int(raw_data.get('team_size_min')),
            team_size_max=self._parse_int(raw_data.get('team_size_max')),
            status=status,
            scraped_at=datetime.utcnow().isoformat(),
            last_updated=raw_data.get('last_updated'),
        )
    
    def _generate_id(self, source: str, data: Dict) -> str:
        """
        Generate a unique, stable ID for an event.
        Uses source + URL hash to ensure same event gets same ID.
        """
        unique_string = f"{source}:{data.get('url', '')}:{data.get('title', '')}"
        return hashlib.md5(unique_string.encode()).hexdigest()[:16]
    
    def _normalize_text(self, text: Any) -> str:
        """Clean and normalize text."""
        if not text:
            return ""
        if not isinstance(text, str):
            text = str(text)
        # Remove extra whitespace
        text = re.sub(r'\s+', ' ', text)
        return text.strip()
    
    def _normalize_url(self, url: Any) -> str:
        """Ensure URL is valid and complete."""
        if not url:
            return ""
        if not isinstance(url, str):
            url = str(url)
        url = url.strip()
        # Remove any tracking parameters (optional)
        url = re.sub(r'\?utm_[^&]+&?', '?', url)
        url = re.sub(r'&utm_[^&]+', '', url)
        url = url.rstrip('?&')
        return url
    
    def _parse_date(self, date_str: Any) -> Optional[str]:
        """
        Parse various date formats into ISO format (YYYY-MM-DD).
        Returns None if parsing fails.
        """
        if not date_str:
            return None
        
        if isinstance(date_str, (datetime, date)):
            return date_str.strftime("%Y-%m-%d")
        
        if not isinstance(date_str, str):
            return None
        
        date_str = date_str.strip()
        
        # Try each format
        for fmt in self.date_formats:
            try:
                parsed = datetime.strptime(date_str, fmt)
                # If year wasn't in format, assume current or next year
                if "%Y" not in fmt and "%y" not in fmt:
                    today = datetime.now()
                    parsed = parsed.replace(year=today.year)
                    # If date is in the past, assume next year
                    if parsed < today:
                        parsed = parsed.replace(year=today.year + 1)
                return parsed.strftime("%Y-%m-%d")
            except ValueError:
                continue
        
        # Try to extract date from strings like "Feb 15 - Feb 17, 2026"
        range_match = re.search(
            r'(\w+\s+\d+)\s*[-–]\s*(\w+\s+\d+),?\s*(\d{4})?',
            date_str
        )
        if range_match:
            month_day = range_match.group(1)
            year = range_match.group(3) or str(datetime.now().year)
            try:
                parsed = datetime.strptime(f"{month_day}, {year}", "%b %d, %Y")
                return parsed.strftime("%Y-%m-%d")
            except ValueError:
                pass
        
        return None
    
    def _normalize_location(self, location: Any) -> str:
        """Normalize location string."""
        if not location:
            return ""
        if not isinstance(location, str):
            location = str(location)
        
        location = location.strip()
        
        # Standardize common variations
        location = re.sub(r'\s+', ' ', location)
        location = location.replace('USA', 'United States')
        location = location.replace('UK', 'United Kingdom')
        
        return location
    
    def _detect_mode(self, location: str, raw_data: Dict) -> str:
        """Detect if event is in-person, online, or hybrid."""
        # Check explicit mode field first (safely handle None)
        explicit_mode = (raw_data.get('mode') or '').lower()
        if 'hybrid' in explicit_mode:
            return EventMode.HYBRID.value
        if any(kw in explicit_mode for kw in ['online', 'virtual', 'remote']):
            return EventMode.ONLINE.value
        if any(kw in explicit_mode for kw in ['in-person', 'in person', 'onsite']):
            return EventMode.IN_PERSON.value
        
        # Analyze location and description (safely handle None)
        location_str = location or ''
        description_str = raw_data.get('description') or ''
        text_to_check = f"{location_str} {description_str}".lower()
        
        has_online = any(kw in text_to_check for kw in self.online_keywords)
        has_inperson = any(kw in text_to_check for kw in self.in_person_keywords)
        
        if has_online and has_inperson:
            return EventMode.HYBRID.value
        if has_online:
            return EventMode.ONLINE.value
        if has_inperson or (location and location.lower() not in ['online', 'virtual', 'remote']):
            return EventMode.IN_PERSON.value
        
        return EventMode.UNKNOWN.value
    
    def _normalize_prize(self, prize: Any) -> tuple[Optional[str], float]:
        """
        Normalize prize pool to standard format.
        Returns (display_string, numeric_value).
        """
        if not prize:
            return None, 0.0
        
        if not isinstance(prize, str):
            prize = str(prize)
        
        prize = prize.strip()
        
        # Extract numeric value
        # Handle formats like "$10,000", "$10K", "10000 USD", "₹50,000"
        numeric_match = re.search(r'[\d,]+\.?\d*', prize.replace(',', ''))
        if not numeric_match:
            return prize, 0.0
        
        numeric_str = numeric_match.group().replace(',', '')
        try:
            value = float(numeric_str)
        except ValueError:
            return prize, 0.0
        
        # Handle K/M suffixes
        if re.search(r'\dk\b', prize.lower()):
            value *= 1000
        elif re.search(r'\dm\b', prize.lower()):
            value *= 1000000
        
        # Format display string (always in USD for consistency)
        if value >= 1000000:
            display = f"${value/1000000:.1f}M"
        elif value >= 1000:
            display = f"${value/1000:.0f}K"
        else:
            display = f"${value:.0f}"
        
        return display, value
    
    def _normalize_tags(self, tags: Any) -> List[str]:
        """Normalize and deduplicate tags."""
        if not tags:
            return []
        
        if isinstance(tags, str):
            # Split by common delimiters
            tags = re.split(r'[,;|]', tags)
        
        normalized = []
        seen = set()
        
        for tag in tags:
            if not isinstance(tag, str):
                continue
            
            tag = tag.strip().lower()
            
            # Apply mappings
            if tag in self.tag_mappings:
                tag = self.tag_mappings[tag]
            else:
                # Title case for display
                tag = tag.title()
            
            # Deduplicate
            if tag.lower() not in seen:
                normalized.append(tag)
                seen.add(tag.lower())
        
        return normalized[:10]  # Limit to 10 tags
    
    def _determine_status(self, start_date: Optional[str], end_date: Optional[str]) -> str:
        """Determine event status based on dates."""
        if not start_date:
            return EventStatus.UNKNOWN.value
        
        today = datetime.now().date()
        
        try:
            start = datetime.strptime(start_date, "%Y-%m-%d").date()
        except ValueError:
            return EventStatus.UNKNOWN.value
        
        if end_date:
            try:
                end = datetime.strptime(end_date, "%Y-%m-%d").date()
            except ValueError:
                end = start
        else:
            end = start
        
        if today < start:
            return EventStatus.UPCOMING.value
        elif start <= today <= end:
            return EventStatus.ONGOING.value
        else:
            return EventStatus.ENDED.value
    
    def _parse_int(self, value: Any) -> Optional[int]:
        """Safely parse integer."""
        if value is None:
            return None
        try:
            return int(value)
        except (ValueError, TypeError):
            return None


# Convenience function for quick normalization
def normalize_event(raw_data: Dict, source: str) -> HackathonEvent:
    """
    Quick helper to normalize a single event.
    
    Usage:
        event = normalize_event({'title': 'HackMIT', 'url': '...'}, 'MLH')
    """
    normalizer = DataNormalizer()
    return normalizer.normalize(raw_data, source)


def normalize_events(raw_events: List[Dict], source: str) -> List[HackathonEvent]:
    """
    Normalize a list of events from the same source.
    
    Usage:
        events = normalize_events(scraped_data, 'Devpost')
    """
    normalizer = DataNormalizer()
    return [normalizer.normalize(event, source) for event in raw_events]


if __name__ == "__main__":
    # Test the normalizer
    test_data = {
        "title": "  HackMIT 2026  ",
        "url": "https://hackmit.org/?utm_source=test",
        "date": "February 15, 2026",
        "end_date": "Feb 17, 2026",
        "location": "Cambridge, MA, USA",
        "prize": "$50,000 in prizes",
        "tags": "AI, machine learning, blockchain",
        "description": "Join us for an in-person hackathon!"
    }
    
    event = normalize_event(test_data, "MLH")
    print("Normalized Event:")
    print(f"  ID: {event.id}")
    print(f"  Title: {event.title}")
    print(f"  URL: {event.url}")
    print(f"  Dates: {event.start_date} to {event.end_date}")
    print(f"  Location: {event.location}")
    print(f"  Mode: {event.mode}")
    print(f"  Prize: {event.prize_pool} ({event.prize_pool_numeric})")
    print(f"  Tags: {event.tags}")
    print(f"  Status: {event.status}")
