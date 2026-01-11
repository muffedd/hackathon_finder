"""
API Scraper Module
==================
Scrapers for sites with stable JSON endpoints.
"""

import logging
from typing import List, Dict, Any, Optional

import requests

from scrapers.base_scraper import BaseScraper, ScrapingError

logger = logging.getLogger(__name__)


class BaseApiScraper(BaseScraper):
    """Base class for API-driven scrapers."""

    def _scrape_with_http(self) -> List[Dict]:
        raise ScrapingError("HTTP method not supported for this API scraper")

    def _scrape_with_browser(self) -> List[Dict]:
        raise ScrapingError("Browser method not supported for this API scraper")

    def _request_json(self, method: str, url: str, **kwargs) -> Any:
        self._respect_rate_limit()
        try:
            response = requests.request(
                method,
                url,
                headers=self.headers,
                timeout=30,
                **kwargs,
            )
        except requests.RequestException as e:
            raise ScrapingError(f"API request failed: {e}")

        if response.status_code != 200:
            raise ScrapingError(f"API returned {response.status_code}")

        try:
            return response.json()
        except ValueError as e:
            raise ScrapingError(f"API invalid JSON: {e}")


class DevpostApiScraper(BaseApiScraper):
    """Devpost API scraper with pagination."""

    def _scrape_with_api(self) -> List[Dict]:
        config = self.config.get("api_config", {})
        endpoint = config.get("endpoint", "https://devpost.com/api/hackathons")
        per_page = int(config.get("per_page", 50))
        max_pages = int(config.get("max_pages", 20))

        events: List[Dict] = []
        for page in range(1, max_pages + 1):
            data = self._request_json(
                "GET",
                endpoint,
                params={"page": page, "per_page": per_page},
            )
            items = data.get("hackathons", [])
            if not items:
                break

            for h in items:
                dates = h.get("submission_period_dates")
                start_date = None
                end_date = None
                if isinstance(dates, dict):
                    start_date = dates.get("starts_at")
                    end_date = dates.get("ends_at")
                elif isinstance(dates, str):
                    start_date = dates

                raw = {
                    "title": h.get("title"),
                    "url": h.get("url"),
                    "start_date": start_date,
                    "end_date": end_date,
                    "location": "Online" if h.get("online_only") else h.get("displayed_location", ""),
                    "prize": h.get("prize_amount"),
                    "description": h.get("tagline"),
                    "image": h.get("thumbnail_url"),
                    "tags": h.get("themes") if isinstance(h.get("themes"), list) else [],
                    "mode": "online" if h.get("online_only") else "in-person",
                }
                if raw["title"] and raw["url"]:
                    events.append(raw)

        logger.info("Devpost API returned %d events", len(events))
        return events


class DevfolioApiScraper(BaseApiScraper):
    """Devfolio API scraper with offset pagination."""

    def _scrape_with_api(self) -> List[Dict]:
        config = self.config.get("api_config", {})
        endpoint = config.get("endpoint", "https://api.devfolio.co/api/search/hackathons")
        size = int(config.get("size", 100))
        max_results = int(config.get("max_results", 1000))
        list_type = config.get("type", "all")

        events: List[Dict] = []
        for offset in range(0, max_results, size):
            payload = {"type": list_type, "from": offset, "size": size}
            data = self._request_json("POST", endpoint, json=payload)
            hits = data.get("hits", {}).get("hits", [])
            if not hits:
                break

            for h in hits:
                src = h.get("_source", {})
                raw = {
                    "title": src.get("name"),
                    "url": f"https://devfolio.co/{src.get('slug')}" if src.get("slug") else None,
                    "start_date": src.get("starts_at"),
                    "end_date": src.get("ends_at"),
                    "location": src.get("location") or ("Online" if src.get("is_online_event") else ""),
                    "prize": src.get("prize_amount"),
                    "description": src.get("tagline"),
                    "mode": "online" if src.get("is_online_event") else "in-person",
                    "tags": src.get("themes", []),
                }
                if raw["title"] and raw["url"]:
                    events.append(raw)

        logger.info("Devfolio API returned %d events", len(events))
        return events


class UnstopApiScraper(BaseApiScraper):
    """Unstop API scraper with pagination."""

    def _scrape_with_api(self) -> List[Dict]:
        config = self.config.get("api_config", {})
        endpoint = config.get(
            "endpoint",
            "https://unstop.com/api/public/opportunity/search-result",
        )
        per_page = int(config.get("per_page", 100))
        max_pages = int(config.get("max_pages", 10))
        opportunity = config.get("opportunity", "hackathons")

        events: List[Dict] = []
        for page in range(1, max_pages + 1):
            params = {"opportunity": opportunity, "per_page": per_page, "page": page}
            data = self._request_json("GET", endpoint, params=params)
            items = data.get("data", {}).get("data", [])
            if not items:
                break

            for h in items:
                has_city = bool(h.get("city"))
                raw = {
                    "title": h.get("title"),
                    "url": f"https://unstop.com/{h.get('public_url')}" if h.get("public_url") else None,
                    "start_date": h.get("start_date"),
                    "end_date": h.get("end_date"),
                    "location": h.get("city") or "Online",
                    "prize": h.get("prize_money") or h.get("prizes"),
                    "description": h.get("seo_details", {}).get("meta_description")
                    if isinstance(h.get("seo_details"), dict)
                    else None,
                    "mode": "in-person" if has_city else "online",
                    "tags": [opportunity],
                }
                if raw["title"] and raw["url"]:
                    events.append(raw)

        logger.info("Unstop API returned %d events", len(events))
        return events


class GeeksforGeeksApiScraper(BaseApiScraper):
    """GeeksforGeeks API scraper."""

    def _scrape_with_api(self) -> List[Dict]:
        config = self.config.get("api_config", {})
        endpoint = config.get(
            "endpoint",
            "https://practice.geeksforgeeks.org/api/v1/events/",
        )
        params = {"type": config.get("type", "contest")}
        data = self._request_json("GET", endpoint, params=params)
        items = data.get("results", [])

        events: List[Dict] = []
        for h in items:
            raw = {
                "title": h.get("name"),
                "url": h.get("url")
                or f"https://practice.geeksforgeeks.org/contest/{h.get('slug')}",
                "start_date": h.get("start_time"),
                "end_date": h.get("end_time"),
                "mode": "online",
            }
            if raw["title"] and raw["url"]:
                events.append(raw)

        logger.info("GeeksforGeeks API returned %d events", len(events))
        return events
