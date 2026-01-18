"""
Browser Scraper Module
======================
Scraper using Playwright for JavaScript-rendered sites
and those with anti-bot protection (Cloudflare, reCAPTCHA).

Uses:
- Playwright for browser automation
- Optional CAPTCHA Solver extension for auto-solving
- Stealth techniques to avoid detection

Sites: MLH, DoraHacks, Devfolio, Unstop, etc.
"""

import time
import logging
import json
from typing import List, Dict, Optional, Any
from pathlib import Path

from scrapers.base_scraper import BaseScraper, ScrapingError

logger = logging.getLogger(__name__)

try:
    from bs4 import BeautifulSoup
except ImportError:  # pragma: no cover - handled at runtime
    BeautifulSoup = None

# Check if Playwright is available
try:
    from playwright.sync_api import sync_playwright, Page, Browser
    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    PLAYWRIGHT_AVAILABLE = False
    logger.warning("Playwright not installed. Browser scraping disabled.")


class BrowserScraper(BaseScraper):
    """
    Browser-based scraper using Playwright.
    
    Features:
    - Full JavaScript execution
    - CAPTCHA solver extension support
    - Cloudflare bypass via real browser
    - Infinite scroll handling
    - Load more button clicking
    
    Suitable for:
    - JS-heavy React/Vue/Angular sites
    - Cloudflare protected sites
    - Sites with reCAPTCHA (with extension)
    """
    
    def __init__(self, site_config: Dict, db_manager=None, normalizer=None):
        super().__init__(site_config, db_manager, normalizer)
        
        # Browser config
        browser_config = site_config.get('browser_config', {})
        self.headless = browser_config.get('headless', True)
        self.timeout = browser_config.get('timeout_ms', 30000)
        self.captcha_wait = browser_config.get('wait_for_captcha_ms', 60000)
        self.extension_path = browser_config.get('extension_path')
        
        # Viewport settings (desktop)
        self.viewport = {'width': 1920, 'height': 1080}
        
        # Browser instance (lazy loaded)
        self._playwright = None
        self._browser = None
    
    def _scrape_with_http(self) -> List[Dict]:
        """
        HTTP fallback not suitable for browser sites.
        Raise to trigger browser method.
        """
        raise ScrapingError("HTTP method not suitable for this site")
    
    def _scrape_with_browser(self) -> List[Dict]:
        """
        Main browser scraping implementation.
        """
        if not PLAYWRIGHT_AVAILABLE:
            raise ScrapingError("Playwright not installed")
        
        events = []
        
        with sync_playwright() as playwright:
            browser = self._launch_browser(playwright)
            
            try:
                page = browser.new_page()
                self._setup_page(page)
                
                # Navigate to the target URL
                logger.info(f"Navigating to {self.url}")
                page.goto(self.url, wait_until='domcontentloaded', timeout=self.timeout)
                
                # Handle Cloudflare challenge if present
                self._wait_for_cloudflare(page)
                
                # Handle CAPTCHA if present
                if self.config.get('has_recaptcha'):
                    self._wait_for_captcha(page)
                
                # Wait for content to load
                self._wait_for_content(page)
                
                # Handle pagination
                events = self._handle_pagination(page)
                
            except Exception as e:
                logger.error(f"Browser scraping failed: {e}")
                raise ScrapingError(f"Browser scraping failed: {e}")
            
            finally:
                browser.close()
        
        logger.info(f"Scraped {len(events)} events via browser from {self.name}")
        return events
    
    def _launch_browser(self, playwright) -> 'Browser':
        """
        Launch browser with appropriate settings.
        Optionally loads CAPTCHA solver extension.
        """
        launch_args = [
            '--disable-blink-features=AutomationControlled',
            '--no-sandbox',
            '--disable-dev-shm-usage',
        ]
        
        # Add extension if configured
        if self.extension_path and Path(self.extension_path).exists():
            launch_args.extend([
                f'--disable-extensions-except={self.extension_path}',
                f'--load-extension={self.extension_path}',
            ])
            logger.info(f"Loading CAPTCHA solver extension from {self.extension_path}")
        
        browser = playwright.chromium.launch(
            headless=self.headless,
            args=launch_args,
        )
        
        return browser
    
    def _setup_page(self, page: 'Page'):
        """Configure page with stealth settings."""
        # Set realistic viewport
        page.set_viewport_size(self.viewport)
        
        # Override detection properties
        page.add_init_script("""
            // Override navigator.webdriver
            Object.defineProperty(navigator, 'webdriver', {
                get: () => undefined,
            });
            
            // Override chrome property
            window.chrome = {
                runtime: {},
            };
            
            // Override permissions
            const originalQuery = window.navigator.permissions.query;
            window.navigator.permissions.query = (parameters) => (
                parameters.name === 'notifications' ?
                    Promise.resolve({ state: Notification.permission }) :
                    originalQuery(parameters)
            );
            
            // Override plugins length
            Object.defineProperty(navigator, 'plugins', {
                get: () => [1, 2, 3, 4, 5],
            });
            
            // Override languages
            Object.defineProperty(navigator, 'languages', {
                get: () => ['en-US', 'en'],
            });
        """)
        
        # Set user agent
        page.set_extra_http_headers({
            'User-Agent': self.headers.get('User-Agent', ''),
            'Accept-Language': 'en-US,en;q=0.9',
        })
    
    def _wait_for_cloudflare(self, page: 'Page', max_wait: int = 15):
        """Wait for Cloudflare challenge to complete."""
        cf_selectors = [
            '#cf-challenge-running',
            '.cf-browser-verification',
            'div[id*="challenge"]',
        ]
        
        # Check if Cloudflare challenge is present
        for selector in cf_selectors:
            if page.locator(selector).count() > 0:
                logger.info("Cloudflare challenge detected, waiting...")
                break
        else:
            return  # No Cloudflare challenge
        
        # Wait for challenge to complete
        start_time = time.time()
        while time.time() - start_time < max_wait:
            # Check if challenge is still running
            challenge_present = any(
                page.locator(sel).count() > 0 for sel in cf_selectors
            )
            if not challenge_present:
                logger.info("Cloudflare challenge passed")
                return
            time.sleep(0.5)
        
        logger.warning("Cloudflare challenge may not have completed")
    
    def _wait_for_captcha(self, page: 'Page'):
        """
        Wait for CAPTCHA to be solved.
        Relies on CAPTCHA Solver extension if available.
        """
        captcha_selectors = [
            'iframe[src*="recaptcha"]',
            'iframe[src*="hcaptcha"]',
            '.g-recaptcha',
            '#cf-turnstile',
        ]
        
        # Check if CAPTCHA is present
        captcha_present = any(
            page.locator(sel).count() > 0 for sel in captcha_selectors
        )
        
        if not captcha_present:
            return
        
        logger.info("CAPTCHA detected, waiting for auto-solve...")
        
        # Wait for CAPTCHA to be solved (extension should handle it)
        start_time = time.time()
        while time.time() - start_time < self.captcha_wait / 1000:
            # Check if CAPTCHA is still present and unsolved
            try:
                # reCAPTCHA: check if verified
                recaptcha_response = page.evaluate("""
                    () => {
                        const el = document.querySelector('[name="g-recaptcha-response"]');
                        return el ? el.value : '';
                    }
                """)
                if recaptcha_response:
                    logger.info("CAPTCHA solved")
                    return
                
                # Also check if CAPTCHA frame disappeared
                if not any(page.locator(sel).count() > 0 for sel in captcha_selectors):
                    logger.info("CAPTCHA no longer present")
                    return
                    
            except Exception:
                pass
            
            time.sleep(1)
        
        logger.warning(f"CAPTCHA may not be solved after {self.captcha_wait/1000}s")
    
    def _wait_for_content(self, page: 'Page'):
        """Wait for main content to load."""
        container_selector = self.selectors.get('event_container')
        
        if container_selector:
            try:
                page.wait_for_selector(
                    container_selector,
                    timeout=10000,
                    state='attached'
                )
                logger.debug(f"Content loaded: {container_selector}")
            except Exception as e:
                logger.warning(f"Content selector not found: {e}")

        try:
            page.wait_for_load_state('networkidle', timeout=10000)
        except Exception:
            pass
        
        # Additional wait for JavaScript rendering
        time.sleep(2)
    
    def _handle_pagination(self, page: 'Page') -> List[Dict]:
        """
        Handle different pagination types:
        - none: single page
        - load_more: click load more button
        - infinite_scroll: scroll to load more
        """
        pagination_type = self.pagination.get('type', 'none')
        
        if pagination_type == 'load_more':
            return self._handle_load_more(page)
        elif pagination_type == 'infinite_scroll':
            return self._handle_infinite_scroll(page)
        else:
            return self._parse_page_events(page)
    
    def _handle_load_more(self, page: 'Page', max_clicks: int = 10) -> List[Dict]:
        """Click 'Load More' button to load all events."""
        button_selector = self.pagination.get('button_selector', '.load-more')
        
        for _ in range(max_clicks):
            try:
                button = page.locator(button_selector)
                if button.count() == 0 or not button.is_visible():
                    break
                
                button.click()
                time.sleep(2)  # Wait for content to load
                
            except Exception as e:
                logger.debug(f"Load more button issue: {e}")
                break
        
        return self._parse_page_events(page)
    
    def _handle_infinite_scroll(self, page: 'Page', max_scrolls: int = 10) -> List[Dict]:
        """Scroll down to load all events."""
        previous_height = 0
        
        for _ in range(max_scrolls):
            # Get current scroll height
            current_height = page.evaluate("document.body.scrollHeight")
            
            if current_height == previous_height:
                break  # No more content to load
            
            previous_height = current_height
            
            # Scroll to bottom
            page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            time.sleep(2)  # Wait for content to load
        
        return self._parse_page_events(page)
    
    def _parse_page_events(self, page: 'Page') -> List[Dict]:
        """Parse events from the current page state."""
        events = []
        
        container_selector = self.selectors.get('event_container')
        if not container_selector:
            logger.warning(f"No event_container selector for {self.name}")
            return self._parse_fallback_html(page.content(), page.url)
        
        # Get all event containers
        containers = page.locator(container_selector).all()
        logger.debug(f"Found {len(containers)} event containers")
        
        for container in containers:
            try:
                event = self._parse_browser_event(container, page.url)
                if event and event.get('title'):
                    events.append(event)
            except Exception as e:
                logger.debug(f"Failed to parse event: {e}")
                continue
        
        if events:
            return events

        return self._parse_fallback_html(page.content(), page.url)
    
    def _parse_browser_event(self, container, base_url: str) -> Optional[Dict]:
        """Parse a single event from a Playwright locator."""
        event = {}
        
        try:
            # Title
            if self.selectors.get('title'):
                title_el = container.locator(self.selectors['title']).first
                if title_el.count() > 0:
                    event['title'] = title_el.inner_text().strip()
            
            # URL
            url_selector = self.selectors.get('url', 'a')
            url_el = container.locator(url_selector).first
            if url_el.count() > 0:
                href = url_el.get_attribute('href')
                if href:
                    event['url'] = self._make_absolute_url(href)
            
            # Date
            if self.selectors.get('date'):
                date_el = container.locator(self.selectors['date']).first
                if date_el.count() > 0:
                    event['date'] = date_el.inner_text().strip()
            
            # Location
            if self.selectors.get('location'):
                loc_el = container.locator(self.selectors['location']).first
                if loc_el.count() > 0:
                    event['location'] = loc_el.inner_text().strip()
            
            # Prize
            if self.selectors.get('prize'):
                prize_el = container.locator(self.selectors['prize']).first
                if prize_el.count() > 0:
                    event['prize'] = prize_el.inner_text().strip()
            
            # Image
            if self.selectors.get('image'):
                img_el = container.locator(self.selectors['image']).first
                if img_el.count() > 0:
                    src = img_el.get_attribute('src')
                    if src:
                        event['image'] = self._make_absolute_url(src)
            
        except Exception as e:
            logger.debug(f"Error parsing event fields: {e}")
        
        return event if event else None

    def _parse_fallback_html(self, html: str, base_url: str) -> List[Dict]:
        if not BeautifulSoup:
            return []

        soup = BeautifulSoup(html, 'html.parser')
        events = self._parse_jsonld_events(soup, base_url)
        if events:
            return events

        containers = self._select_fallback_containers(soup)
        for container in containers:
            event = self._parse_fallback_container(container, base_url)
            if event and event.get('title'):
                events.append(event)

        if events:
            logger.info(f"Fallback HTML parsing found {len(events)} events for {self.name}")

        return events

    def _select_fallback_containers(self, soup: 'BeautifulSoup') -> List[Any]:
        selectors = []
        if self.selectors.get('event_container'):
            selectors.append(self.selectors['event_container'])

        # Extended list of generic container selectors
        selectors.extend([
            'article',
            '[class*="event"]',
            '[class*="hackathon"]',
            '[class*="challenge"]',
            '[class*="opportunity"]',
            '[class*="contest"]',
            '[class*="competition"]',
            '[class*="bounty"]',
            '[class*="listing"]',
            '[class*="card"]',
            '[class*="item"]',
            '[class*="tile"]',
            '[class*="wrapper"]',
            '[class*="box"]',
            'li',  # List items often contain events
            'section',
            'div[role="listitem"]',
            '[data-testid]',  # React/testing patterns
        ])

        best = []
        for selector in selectors:
            try:
                candidates = soup.select(selector)
            except Exception:
                continue
            # Filter to containers with links
            candidates = [c for c in candidates if c.find('a', href=True)]
            # Prefer containers with more text content (likely real events)
            candidates = [c for c in candidates if len(c.get_text(strip=True)) > 20]
            if len(candidates) > len(best):
                best = candidates

        # Fallback: find all links with event-like URLs and get their parent containers
        if not best:
            event_links = soup.find_all('a', href=lambda h: h and any(
                kw in h.lower() for kw in ['event', 'hackathon', 'challenge', 'competition', 'bounty', '/e/', '/h/']
            ))
            seen_parents = set()
            for link in event_links:
                parent = link.find_parent(['article', 'section', 'div', 'li'])
                if parent and id(parent) not in seen_parents:
                    seen_parents.add(id(parent))
                    best.append(parent)


        return best

    def _parse_fallback_container(self, container, base_url: str) -> Optional[Dict]:
        event = {}

        def select_text(selector: Optional[str]) -> str:
            if not selector:
                return ""
            found = container.select_one(selector)
            return found.get_text(strip=True) if found else ""

        title = select_text(self.selectors.get('title'))
        if not title:
            heading = container.select_one('h1, h2, h3, h4')
            if heading:
                title = heading.get_text(strip=True)

        url = ""
        if self.selectors.get('url'):
            link = container.select_one(self.selectors.get('url'))
            if link and link.get('href'):
                url = link.get('href')
        if not url:
            link = container.find('a', href=True)
            if link:
                url = link.get('href', '')

        if url:
            url = self._make_absolute_url(url)

        date = select_text(self.selectors.get('date'))
        if not date:
            time_el = container.select_one('time')
            if time_el:
                date = time_el.get_text(strip=True)

        location = select_text(self.selectors.get('location'))
        if not location:
            loc_el = container.select_one('[class*="location"], [class*="city"]')
            if loc_el:
                location = loc_el.get_text(strip=True)

        prize = select_text(self.selectors.get('prize'))

        tags = []
        if self.selectors.get('tags'):
            tags_elements = container.select(self.selectors['tags'])
            tags = [el.get_text(strip=True) for el in tags_elements if el.get_text(strip=True)]

        event = {
            'title': title,
            'url': url,
            'date': date,
            'location': location,
            'prize': prize,
            'tags': tags,
        }

        if event['title'] and event['url']:
            return event

        return None

    def _parse_jsonld_events(self, soup: 'BeautifulSoup', base_url: str) -> List[Dict]:
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
                url = self._make_absolute_url(url)

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

class MLHScraper(BrowserScraper):
    """Specialized scraper for Major League Hacking."""
    
    def _parse_browser_event(self, container, base_url: str) -> Optional[Dict]:
        event = {}
        
        try:
            # MLH-specific parsing
            event['title'] = container.locator('.event-name, h3').first.inner_text().strip()
            
            href = container.locator('a').first.get_attribute('href')
            if href:
                event['url'] = self._make_absolute_url(href)
            
            event['date'] = container.locator('.event-date, .date').first.inner_text().strip()
            event['location'] = container.locator('.event-location, .location').first.inner_text().strip()
            
            # MLH events are typically in-person
            event['mode'] = 'in-person'
            
            # MLH logo
            logo = container.locator('img').first
            if logo.count() > 0:
                event['image'] = logo.get_attribute('src')
                
        except Exception:
            pass
        
        return event if event.get('title') else None


if __name__ == "__main__":
    # Test browser scraper (requires Playwright)
    import json
    
    if not PLAYWRIGHT_AVAILABLE:
        print("Playwright not installed. Run: pip install playwright && playwright install chromium")
        exit(1)
    
    # Load config
    with open('config/websites.json', 'r') as f:
        config = json.load(f)
    
    # Test MLH (Cloudflare protected but no reCAPTCHA)
    mlh_config = config['websites']['mlh']
    mlh_config['default_headers'] = config['default_headers']
    mlh_config['browser_config'] = config.get('browser_config', {})
    mlh_config['browser_config']['headless'] = False  # Show browser for testing
    
    scraper = MLHScraper(mlh_config)
    print(f"Testing {scraper.name}...")
    
    try:
        events = scraper._scrape_with_browser()
        print(f"Found {len(events)} events")
        if events:
            print(f"First event: {events[0].get('title')}")
    except Exception as e:
        print(f"Error: {e}")
