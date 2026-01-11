"""
HTTP Scraper Module
===================
Scraper for sites that work with simple HTTP requests.
No JavaScript rendering needed.

Best for:
- Static HTML sites
- Sites with no Cloudflare/reCAPTCHA
- Sites with discoverable API endpoints

Sites: Devpost, HackerEarth, MyCareernet
"""

import json
import requests
from bs4 import BeautifulSoup
from typing import List, Dict, Optional, Any
from urllib.parse import urljoin, urlparse, parse_qs
import logging
import re

from scrapers.base_scraper import BaseScraper, ScrapingError

logger = logging.getLogger(__name__)


class HttpScraper(BaseScraper):
    """
    HTTP-based scraper using requests + BeautifulSoup.
    
    Suitable for:
    - Sites with server-rendered HTML
    - Sites without anti-bot protection
    - Sites with accessible JSON APIs
    """
    
    def __init__(self, site_config: Dict, db_manager=None, normalizer=None):
        super().__init__(site_config, db_manager, normalizer)
        self.session = requests.Session()
        self.session.headers.update(self.headers)
    
    def _scrape_with_http(self) -> List[Dict]:
        """
        Main HTTP scraping implementation.
        Handles pagination if configured.
        """
        all_events = []
        
        # Check if we should try API first
        if self.config.get('api_hints', {}).get('investigate'):
            try:
                events = self._try_api_endpoint()
                if events:
                    logger.info(f"Found {len(events)} events via API")
                    return events
            except Exception as e:
                logger.debug(f"API attempt failed: {e}")
        
        # Fall back to HTML scraping
        pagination_type = self.pagination.get('type', 'none')
        
        if pagination_type == 'none':
            # Single page
            all_events = self._scrape_single_page(self.url)
            
        elif pagination_type == 'numbered':
            # Paginated with page numbers
            all_events = self._scrape_numbered_pages()
            
        elif pagination_type == 'next_prev':
            # Paginated with next/prev links
            all_events = self._scrape_next_prev_pages()
        
        logger.info(f"Scraped {len(all_events)} events from {self.name}")
        return all_events
    
    def _scrape_with_browser(self) -> List[Dict]:
        """
        Fallback: Use browser automation.
        Delegates to BrowserScraper.
        """
        from scrapers.browser_scraper import BrowserScraper
        browser_scraper = BrowserScraper(self.config, self.db, self.normalizer)
        return browser_scraper._scrape_with_browser()
    
    def _scrape_single_page(self, url: str) -> List[Dict]:
        """Scrape a single page and extract events."""
        self._respect_rate_limit()
        
        try:
            response = self.session.get(url, timeout=30)
            response.raise_for_status()
        except requests.RequestException as e:
            raise ScrapingError(f"HTTP request failed: {e}")
        
        soup = BeautifulSoup(response.text, 'html.parser')
        return self._parse_events(soup, response.url)
    
    def _scrape_numbered_pages(self, max_pages: int = 10) -> List[Dict]:
        """Scrape paginated results with numbered pages."""
        all_events = []
        page_param = self.pagination.get('param', 'page')
        
        for page_num in range(1, max_pages + 1):
            # Construct URL with page parameter
            if '?' in self.url:
                url = f"{self.url}&{page_param}={page_num}"
            else:
                url = f"{self.url}?{page_param}={page_num}"
            
            logger.debug(f"Scraping page {page_num}: {url}")
            
            try:
                events = self._scrape_single_page(url)
            except ScrapingError as e:
                logger.warning(f"Page {page_num} failed: {e}")
                break
            
            if not events:
                # No more events, stop pagination
                logger.debug(f"No events on page {page_num}, stopping")
                break
            
            all_events.extend(events)
            
            # Check for duplicates (indicates we've looped)
            if len(all_events) != len(set(e.get('url', i) for i, e in enumerate(all_events))):
                logger.debug("Detected duplicate events, stopping pagination")
                break
        
        return all_events
    
    def _scrape_next_prev_pages(self, max_pages: int = 10) -> List[Dict]:
        """Scrape paginated results following next links."""
        all_events = []
        current_url = self.url
        visited_urls = set()
        
        for page_num in range(max_pages):
            if current_url in visited_urls:
                break
            visited_urls.add(current_url)
            
            self._respect_rate_limit()
            
            try:
                response = self.session.get(current_url, timeout=30)
                response.raise_for_status()
            except requests.RequestException as e:
                logger.warning(f"Request failed for {current_url}: {e}")
                break
            
            soup = BeautifulSoup(response.text, 'html.parser')
            events = self._parse_events(soup, response.url)
            
            if not events:
                break
            
            all_events.extend(events)
            
            # Find next page link
            next_link = soup.select_one(
                self.pagination.get('next_selector', 'a[rel="next"], a:contains("Next")')
            )
            
            if not next_link or not next_link.get('href'):
                break
            
            current_url = self._make_absolute_url(next_link['href'])
        
        return all_events
    
    def _try_api_endpoint(self) -> Optional[List[Dict]]:
        """
        Attempt to discover and use API endpoints.
        Many sites have JSON APIs that aren't officially documented.
        """
        api_hints = self.config.get('api_hints', {})
        
        if api_hints.get('possible_endpoint'):
            # Try the hinted endpoint
            base_url = urlparse(self.url)
            api_url = f"{base_url.scheme}://{base_url.netloc}{api_hints['possible_endpoint']}"
            
            try:
                response = self.session.get(api_url, timeout=15)
                if response.status_code == 200:
                    data = response.json()
                    return self._parse_api_response(data)
            except Exception:
                pass
        
        # Try common API patterns
        common_patterns = [
            '/api/hackathons',
            '/api/v1/hackathons',
            '/api/events',
            '/api/competitions',
            '/_next/data/hackathons.json',
        ]
        
        base_url = urlparse(self.url)
        for pattern in common_patterns:
            api_url = f"{base_url.scheme}://{base_url.netloc}{pattern}"
            try:
                response = self.session.get(api_url, timeout=10)
                if response.status_code == 200:
                    content_type = response.headers.get('content-type', '')
                    if 'json' in content_type:
                        data = response.json()
                        if isinstance(data, (list, dict)):
                            events = self._parse_api_response(data)
                            if events:
                                logger.info(f"Found API at {api_url}")
                                return events
            except Exception:
                continue
        
        return None
    
    def _parse_api_response(self, data: Any) -> List[Dict]:
        """Parse JSON API response into event list."""
        events = []
        
        # Handle various API response formats
        if isinstance(data, list):
            items = data
        elif isinstance(data, dict):
            # Common patterns: {'data': [...]}, {'hackathons': [...]}, {'events': [...]}
            for key in ['data', 'hackathons', 'events', 'competitions', 'results', 'items']:
                if key in data and isinstance(data[key], list):
                    items = data[key]
                    break
            else:
                items = [data]  # Maybe the dict itself is the event
        else:
            return []
        
        for item in items:
            if not isinstance(item, dict):
                continue
            
            # Map common API field names to our format
            event = {
                'title': item.get('title') or item.get('name') or item.get('hackathon_name'),
                'url': item.get('url') or item.get('link') or item.get('hackathon_url'),
                'start_date': item.get('start_date') or item.get('starts_at') or item.get('start'),
                'end_date': item.get('end_date') or item.get('ends_at') or item.get('end'),
                'deadline': item.get('deadline') or item.get('registration_deadline'),
                'location': item.get('location') or item.get('city') or item.get('venue'),
                'prize': item.get('prize_pool') or item.get('prizes') or item.get('total_prizes'),
                'description': item.get('description') or item.get('tagline') or item.get('summary'),
                'image': item.get('image_url') or item.get('thumbnail') or item.get('cover_image'),
                'tags': item.get('tags') or item.get('themes') or item.get('categories'),
                'mode': item.get('mode') or item.get('format') or item.get('type'),
            }
            
            # Filter out items without essential fields
            if event['title'] and (event['url'] or event['start_date']):
                events.append(event)
        
        return events
    
    def _parse_events(self, soup: BeautifulSoup, base_url: str) -> List[Dict]:
        """
        Parse events from HTML using configured selectors.
        
        This is a generic implementation. Site-specific scrapers
        can override for custom parsing.
        """
        events = []
        
        container_selector = self.selectors.get('event_container')
        if not container_selector:
            logger.warning(f"No event_container selector for {self.name}")
            return self._parse_jsonld_events(soup, base_url)
        
        containers = soup.select(container_selector)
        logger.debug(f"Found {len(containers)} event containers")
        
        for container in containers:
            try:
                event = self._parse_single_event(container, base_url)
                if event and event.get('title'):
                    events.append(event)
            except Exception as e:
                logger.debug(f"Failed to parse event: {e}")
                continue
        
        if events:
            return events

        return self._parse_jsonld_events(soup, base_url)
    
    def _parse_single_event(self, container, base_url: str) -> Optional[Dict]:
        """Parse a single event container into a dict."""
        event = {}
        
        # Title
        if self.selectors.get('title'):
            event['title'] = self._extract_text(container, self.selectors['title'])
        
        # URL
        url_selector = self.selectors.get('url', 'a')
        url = self._extract_attribute(container, url_selector, 'href')
        if url:
            event['url'] = urljoin(base_url, url)
        
        # Date
        if self.selectors.get('date'):
            event['date'] = self._extract_text(container, self.selectors['date'])
        
        # Location
        if self.selectors.get('location'):
            event['location'] = self._extract_text(container, self.selectors['location'])
        
        # Prize
        if self.selectors.get('prize'):
            event['prize'] = self._extract_text(container, self.selectors['prize'])
        
        # Image
        if self.selectors.get('image'):
            img_url = self._extract_attribute(container, self.selectors['image'], 'src')
            if img_url:
                event['image'] = urljoin(base_url, img_url)
        
        # Tags (might be multiple elements)
        if self.selectors.get('tags'):
            tags_elements = container.select(self.selectors['tags'])
            event['tags'] = [el.get_text(strip=True) for el in tags_elements if el.get_text(strip=True)]
        
        return event if event else None

    def _parse_jsonld_events(self, soup: BeautifulSoup, base_url: str) -> List[Dict]:
        events: List[Dict] = []
        scripts = soup.find_all('script', type='application/ld+json')
        if not scripts:
            return events

        for script in scripts:
            raw = script.string or script.get_text()
            if not raw:
                continue
            try:
                data = json.loads(raw)
            except Exception:
                continue

            events.extend(self._extract_events_from_jsonld(data, base_url))

        if events:
            logger.info(f"Parsed {len(events)} events from JSON-LD for {self.name}")

        return events

    def _extract_events_from_jsonld(self, data: Any, base_url: str) -> List[Dict]:
        items: List[Any] = []
        if isinstance(data, list):
            items = data
        elif isinstance(data, dict):
            if isinstance(data.get('@graph'), list):
                items = data['@graph']
            else:
                items = [data]

        events: List[Dict] = []
        for item in items:
            if not isinstance(item, dict):
                continue

            event_type = item.get('@type')
            if isinstance(event_type, list):
                is_event = any(str(t).lower() == 'event' for t in event_type)
            else:
                is_event = str(event_type).lower() == 'event'

            if not is_event:
                continue

            title = item.get('name') or item.get('title')
            url = item.get('url') or item.get('@id')
            if url and isinstance(url, str) and url.startswith('/'):
                url = urljoin(base_url, url)

            start_date = item.get('startDate') or item.get('start_date')
            end_date = item.get('endDate') or item.get('end_date')
            description = item.get('description')
            image = item.get('image')
            if isinstance(image, list) and image:
                image = image[0]

            location_value = item.get('location')
            location = ''
            if isinstance(location_value, dict):
                location = location_value.get('name') or ''
                address = location_value.get('address')
                if isinstance(address, dict):
                    parts = [
                        address.get('streetAddress'),
                        address.get('addressLocality'),
                        address.get('addressRegion'),
                        address.get('addressCountry'),
                    ]
                    address_text = ', '.join([p for p in parts if p])
                    location = location or address_text
            elif isinstance(location_value, list) and location_value:
                first_loc = location_value[0]
                if isinstance(first_loc, dict):
                    location = first_loc.get('name') or ''
                elif isinstance(first_loc, str):
                    location = first_loc
            elif isinstance(location_value, str):
                location = location_value

            mode = None
            attendance = item.get('eventAttendanceMode')
            if isinstance(attendance, str):
                if 'online' in attendance.lower():
                    mode = 'online'
                elif 'offline' in attendance.lower() or 'inperson' in attendance.lower():
                    mode = 'in-person'

            if location and location.lower() == 'online':
                mode = mode or 'online'

            event = {
                'title': title,
                'url': url,
                'start_date': start_date,
                'end_date': end_date,
                'location': location,
                'description': description,
                'image': image,
            }
            if mode:
                event['mode'] = mode

            if event['title'] and event['url']:
                events.append(event)

        return events


# ============ Site-Specific Implementations ============

class DevpostScraper(HttpScraper):
    """
    Specialized scraper for Devpost.
    Handles Devpost's specific HTML structure.
    """
    
    def _parse_single_event(self, container, base_url: str) -> Optional[Dict]:
        """Custom parsing for Devpost hackathon tiles."""
        event = {}
        
        # Title
        title_el = container.select_one('.challenge-title, .hackathon-title, h4, h3')
        if title_el:
            event['title'] = title_el.get_text(strip=True)
        
        # URL
        link = container.select_one('a.block-wrapper-link, a[href*="devpost.com"]')
        if link and link.get('href'):
            event['url'] = urljoin(base_url, link['href'])
        
        # Date/Submission period
        date_el = container.select_one('.submission-period, .date-range, .dates')
        if date_el:
            event['date'] = date_el.get_text(strip=True)
        
        # Location/Tags
        info_els = container.select('.tag, .info-with-icon')
        tags = []
        for el in info_els:
            text = el.get_text(strip=True)
            if text:
                # Check if it's a location or a tag
                if any(loc_word in text.lower() for loc_word in ['online', 'virtual', 'remote', 'city', 'usa', 'india']):
                    event['location'] = text
                else:
                    tags.append(text)
        event['tags'] = tags
        
        # Prize
        prize_el = container.select_one('.prize-amount, .prizes')
        if prize_el:
            event['prize'] = prize_el.get_text(strip=True)
        
        # Image
        img_el = container.select_one('img.hackathon-thumbnail, img.cover-image')
        if img_el and img_el.get('src'):
            event['image'] = urljoin(base_url, img_el['src'])
        
        return event if event.get('title') else None


class HackerEarthScraper(HttpScraper):
    """
    Specialized scraper for HackerEarth.
    Handles HackerEarth's challenge card structure.
    """
    
    def _parse_single_event(self, container, base_url: str) -> Optional[Dict]:
        """Custom parsing for HackerEarth challenge cards."""
        event = {}
        
        # Title
        title_el = container.select_one('.challenge-name, .event-title, h3, h4')
        if title_el:
            event['title'] = title_el.get_text(strip=True)
        
        # URL
        link = container.select_one('a')
        if link and link.get('href'):
            event['url'] = urljoin(base_url, link['href'])
        
        # Date
        date_el = container.select_one('.date, .timing, .challenge-date')
        if date_el:
            event['date'] = date_el.get_text(strip=True)
        
        # Type (hackathon, hiring challenge, etc.)
        type_el = container.select_one('.challenge-type, .type-label')
        if type_el:
            event['tags'] = [type_el.get_text(strip=True)]
        
        # Prize
        prize_el = container.select_one('.prize, .prize-money')
        if prize_el:
            event['prize'] = prize_el.get_text(strip=True)
        
        # Company/Organizer
        org_el = container.select_one('.company-name, .organizer')
        if org_el:
            event['organizer'] = org_el.get_text(strip=True)
        
        return event if event.get('title') else None


if __name__ == "__main__":
    # Test the HTTP scraper
    import json
    
    # Load config
    with open('config/websites.json', 'r') as f:
        config = json.load(f)
    
    # Test Devpost
    devpost_config = config['websites']['devpost']
    devpost_config['default_headers'] = config['default_headers']
    
    scraper = DevpostScraper(devpost_config)
    print(f"Testing {scraper.name}...")
    
    try:
        events = scraper._scrape_with_http()
        print(f"Found {len(events)} events")
        if events:
            print(f"First event: {events[0].get('title')}")
    except Exception as e:
        print(f"Error: {e}")
