"""
Base Scraper Module
===================
Abstract base class implementing the unified "waterfall" scraping approach.

The scraping waterfall:
1. Check cache - return if fresh (<6 hours)
2. Try API endpoint - if site has known API
3. Try simple HTTP - fast, low resource
4. Fall back to browser automation - for JS/CAPTCHA sites

All site-specific scrapers inherit from this class.
"""

import json
import time
import logging
from abc import ABC, abstractmethod
from typing import List, Dict, Optional, Any
from pathlib import Path
from datetime import datetime

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class ScrapingError(Exception):
    """Custom exception for scraping errors."""
    pass


class BaseScraper(ABC):
    """
    Abstract base class for all scrapers.
    
    Implements the waterfall approach to scraping:
    Cache → API → HTTP → Browser
    
    Each child class just needs to implement:
    - _scrape_with_http()
    - _scrape_with_browser()
    - _parse_events()
    
    The base class handles:
    - Cache checking
    - Rate limiting
    - Error handling
    - Retry logic
    - Data normalization
    """
    
    def __init__(
        self,
        site_config: Dict,
        db_manager: Optional[Any] = None,
        normalizer: Optional[Any] = None
    ):
        """
        Initialize the scraper.
        
        Args:
            site_config: Configuration dict for this site
            db_manager: Database manager instance (optional)
            normalizer: Data normalizer instance (optional)
        """
        self.config = site_config
        self.name = site_config.get('name', 'Unknown')
        self.short_name = site_config.get('short_name', self.name)
        self.url = site_config.get('url', '')
        self.method = site_config.get('method', 'http')
        self.difficulty = site_config.get('difficulty', 'MEDIUM')
        self.selectors = site_config.get('selectors', {})
        self.pagination = site_config.get('pagination', {})
        
        self.db = db_manager
        self.normalizer = normalizer
        
        # Default headers
        self.headers = site_config.get('default_headers', {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
                          'AppleWebKit/537.36 (KHTML, like Gecko) '
                          'Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
        })
        
        # Rate limiting
        self.request_delay = 2  # seconds between requests
        self.last_request_time = 0
        
        # Retry configuration
        self.max_retries = 3
        self.retry_delay = 5  # seconds
        
        # Cache TTL
        self.cache_ttl_hours = 6
        
        logger.info(f"Initialized scraper for {self.name}")
    
    def scrape(self, force_refresh: bool = False) -> List[Dict]:
        """
        Main scraping method. Implements the waterfall approach.
        
        Args:
            force_refresh: If True, skip cache and scrape fresh
            
        Returns:
            List of normalized event dictionaries
        """
        logger.info(f"Starting scrape for {self.name}")
        
        # Step 1: Check cache
        if not force_refresh and self._is_cache_fresh():
            logger.info(f"Using cached data for {self.name}")
            return self._get_cached_events()
        
        # Step 2: Try scraping with waterfall order (API -> HTTP -> Browser)
        events = []
        error = None

        for method_name, method in self._get_method_sequence():
            try:
                logger.info(f"Using {method_name.upper()} method for {self.name}")
                events = method()
                if events:
                    break
                logger.info(f"{method_name.upper()} method returned no events for {self.name}")
            except ScrapingError as e:
                error = e
                logger.warning(f"{method_name.upper()} method failed for {self.name}: {e}")
            except Exception as e:
                error = e
                logger.warning(f"{method_name.upper()} method error for {self.name}: {e}")
        
        # Step 3: Normalize and save
        if events:
            normalized = self._normalize_events(events)
            self._save_to_cache(normalized)
            return normalized
        else:
            if error:
                logger.error(f"All scraping methods failed for {self.name}: {error}")
            return []
    
    def _is_cache_fresh(self) -> bool:
        """Check if cached data is still fresh."""
        if not self.db:
            return False
        return self.db.is_cache_fresh(self.short_name, self.cache_ttl_hours)
    
    def _get_cached_events(self) -> List[Dict]:
        """Retrieve events from cache."""
        if not self.db:
            return []
        events, _ = self.db.query_events(source=self.short_name)
        return [e.to_dict() for e in events]
    
    def _save_to_cache(self, events: List[Dict]) -> None:
        """Save normalized events to cache."""
        if not self.db or not self.normalizer:
            return
        
        from utils.data_normalizer import HackathonEvent
        
        event_objects = [HackathonEvent.from_dict(e) for e in events]
        self.db.save_events(event_objects, self.short_name)
        logger.info(f"Saved {len(events)} events to cache for {self.name}")
    
    def _get_method_sequence(self) -> List[tuple]:
        methods = []

        api_hint = bool(self.config.get('api_hints') or self.config.get('api_config'))
        if self.method == 'api' or api_hint:
            methods.append(("api", self._scrape_with_api))

        methods.append(("http", self._scrape_with_http))
        methods.append(("browser", self._scrape_with_browser))

        return methods
    
    def _normalize_events(self, raw_events: List[Dict]) -> List[Dict]:
        """Normalize raw event data."""
        if not self.normalizer:
            return raw_events
        
        from utils.data_normalizer import normalize_events
        events = normalize_events(raw_events, self.short_name)
        return [e.to_dict() for e in events]
    
    def _respect_rate_limit(self) -> None:
        """Ensure we don't overwhelm the target server."""
        elapsed = time.time() - self.last_request_time
        if elapsed < self.request_delay:
            sleep_time = self.request_delay - elapsed
            logger.debug(f"Rate limiting: sleeping {sleep_time:.2f}s")
            time.sleep(sleep_time)
        self.last_request_time = time.time()
    
    def _retry_with_backoff(self, func, *args, **kwargs) -> Any:
        """
        Execute function with retries and exponential backoff.
        
        Args:
            func: Function to execute
            *args, **kwargs: Arguments to pass to function
            
        Returns:
            Function result
            
        Raises:
            ScrapingError: If all retries fail
        """
        last_error = None
        
        for attempt in range(self.max_retries):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                last_error = e
                wait_time = self.retry_delay * (2 ** attempt)
                logger.warning(
                    f"Attempt {attempt + 1}/{self.max_retries} failed: {e}. "
                    f"Retrying in {wait_time}s..."
                )
                time.sleep(wait_time)
        
        raise ScrapingError(f"All {self.max_retries} attempts failed: {last_error}")
    
    # ============ Abstract Methods (Child classes must implement) ============
    
    @abstractmethod
    def _scrape_with_http(self) -> List[Dict]:
        """
        Scrape using simple HTTP requests.
        
        Returns:
            List of raw event dictionaries
            
        Raises:
            ScrapingError: If HTTP scraping fails
        """
        pass
    
    @abstractmethod
    def _scrape_with_browser(self) -> List[Dict]:
        """
        Scrape using browser automation (Playwright).
        
        Returns:
            List of raw event dictionaries
            
        Raises:
            ScrapingError: If browser scraping fails
        """
        pass
    
    def _scrape_with_api(self) -> List[Dict]:
        """
        Scrape using official API.
        Override in child class if site has API.
        
        Returns:
            List of raw event dictionaries
        """
        raise ScrapingError(f"API method not implemented for {self.name}")
    
    # ============ Utility Methods ============
    
    def _extract_text(self, element, selector: str) -> str:
        """Safely extract text from an element using selector."""
        try:
            found = element.select_one(selector)
            return found.get_text(strip=True) if found else ""
        except Exception:
            return ""
    
    def _extract_attribute(self, element, selector: str, attr: str) -> str:
        """Safely extract attribute from an element."""
        try:
            found = element.select_one(selector)
            return found.get(attr, "") if found else ""
        except Exception:
            return ""
    
    def _make_absolute_url(self, url: str) -> str:
        """Convert relative URL to absolute."""
        if not url:
            return ""
        if url.startswith('http'):
            return url
        from urllib.parse import urljoin
        return urljoin(self.url, url)


class ScraperFactory:
    """
    Factory for creating appropriate scraper instances.
    
    Usage:
        factory = ScraperFactory("config/websites.json")
        scraper = factory.get_scraper("mlh")
        events = scraper.scrape()
    """
    
    def __init__(self, config_path: str = "config/websites.json"):
        """Load configuration."""
        self.config_path = Path(config_path)
        self.config = self._load_config()
        self._scrapers = {}
    
    def _load_config(self) -> Dict:
        """Load website configuration."""
        if not self.config_path.exists():
            raise FileNotFoundError(f"Config not found: {self.config_path}")
        
        with open(self.config_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    
    def get_scraper(
        self,
        site_key: str,
        db_manager: Optional[Any] = None,
        normalizer: Optional[Any] = None
    ) -> BaseScraper:
        """
        Get or create a scraper for a specific site.
        
        Args:
            site_key: Key from websites.json (e.g., "mlh", "devpost")
            db_manager: Optional database manager
            normalizer: Optional data normalizer
            
        Returns:
            Appropriate scraper instance
        """
        if site_key not in self.config.get('websites', {}):
            raise ValueError(f"Unknown site: {site_key}")
        
        site_config = self.config['websites'][site_key]
        site_config['default_headers'] = self.config.get('default_headers', {})
        
        # Import appropriate scraper class based on method
        method = site_config.get('method', 'http')
        
        if method == 'http':
            from scrapers.http_scraper import HttpScraper
            return HttpScraper(site_config, db_manager, normalizer)
        elif method == 'browser':
            from scrapers.browser_scraper import BrowserScraper
            return BrowserScraper(site_config, db_manager, normalizer)
        elif method == 'api':
            if site_key == 'kaggle':
                from scrapers.kaggle_scraper import KaggleScraper
                return KaggleScraper(site_config, db_manager, normalizer)
            if site_key == 'devpost':
                from scrapers.api_scraper import DevpostApiScraper
                return DevpostApiScraper(site_config, db_manager, normalizer)
            if site_key == 'devfolio':
                from scrapers.api_scraper import DevfolioApiScraper
                return DevfolioApiScraper(site_config, db_manager, normalizer)
            if site_key == 'unstop':
                from scrapers.api_scraper import UnstopApiScraper
                return UnstopApiScraper(site_config, db_manager, normalizer)
            if site_key == 'geeksforgeeks':
                from scrapers.api_scraper import GeeksforGeeksApiScraper
                return GeeksforGeeksApiScraper(site_config, db_manager, normalizer)
            raise ValueError(f"No API scraper for {site_key}")
        else:
            raise ValueError(f"Unknown method: {method}")
    
    def get_all_scrapers(
        self,
        db_manager: Optional[Any] = None,
        normalizer: Optional[Any] = None,
        tier: Optional[str] = None
    ) -> List[BaseScraper]:
        """
        Get scrapers for all configured sites.
        
        Args:
            db_manager: Optional database manager
            normalizer: Optional data normalizer
            tier: Optional tier filter ('tier_1_high_value', 'tier_2_medium', 'tier_3_low')
            
        Returns:
            List of scraper instances
        """
        scrapers = []
        
        if tier:
            site_keys = self.config.get('scraping_priority', {}).get(tier, [])
        else:
            site_keys = self.config.get('websites', {}).keys()
        
        for site_key in site_keys:
            try:
                scraper = self.get_scraper(site_key, db_manager, normalizer)
                scrapers.append(scraper)
            except Exception as e:
                logger.warning(f"Failed to create scraper for {site_key}: {e}")
        
        return scrapers
    
    @property
    def available_sites(self) -> List[str]:
        """Get list of available site keys."""
        return list(self.config.get('websites', {}).keys())
    
    @property
    def priority_tiers(self) -> Dict[str, List[str]]:
        """Get scraping priority tiers."""
        return self.config.get('scraping_priority', {})


if __name__ == "__main__":
    # Quick test
    factory = ScraperFactory("config/websites.json")
    print(f"Available sites: {factory.available_sites}")
    print(f"Priority tiers: {factory.priority_tiers}")
