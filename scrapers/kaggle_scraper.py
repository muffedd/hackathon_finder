"""
Kaggle Scraper Module
=====================
Uses Kaggle API endpoints to fetch competitions.
"""

import os
import logging
from typing import List, Dict, Any

import requests

from scrapers.base_scraper import BaseScraper, ScrapingError

logger = logging.getLogger(__name__)


class KaggleScraper(BaseScraper):
    """Scraper for Kaggle competitions using API endpoints."""

    def _scrape_with_http(self) -> List[Dict]:
        raise ScrapingError("Kaggle scraping requires the API method")

    def _scrape_with_browser(self) -> List[Dict]:
        raise ScrapingError("Kaggle scraping requires the API method")

    def _scrape_with_api(self) -> List[Dict]:
        events = self._scrape_with_authenticated_api()
        if events:
            return events
        return self._scrape_with_public_endpoint()

    def _scrape_with_authenticated_api(self) -> List[Dict]:
        username = os.getenv("KAGGLE_USERNAME")
        key = os.getenv("KAGGLE_KEY")
        if not username or not key:
            return []

        url = "https://www.kaggle.com/api/v1/competitions/list"
        self._respect_rate_limit()

        try:
            response = requests.get(
                url,
                auth=(username, key),
                headers=self.headers,
                timeout=30,
            )
        except requests.RequestException as e:
            raise ScrapingError(f"Kaggle API request failed: {e}")

        if response.status_code in (401, 403):
            raise ScrapingError("Kaggle API authentication failed")
        if response.status_code != 200:
            raise ScrapingError(f"Kaggle API returned {response.status_code}")

        try:
            data = response.json()
        except ValueError as e:
            raise ScrapingError(f"Kaggle API invalid JSON: {e}")

        return self._parse_competitions(data, authenticated=True)

    def _scrape_with_public_endpoint(self) -> List[Dict]:
        url = self.config.get("api_config", {}).get(
            "public_endpoint",
            "https://www.kaggle.com/competitions.json",
        )
        self._respect_rate_limit()

        try:
            response = requests.get(url, headers=self.headers, timeout=30)
        except requests.RequestException as e:
            raise ScrapingError(f"Kaggle public request failed: {e}")

        if response.status_code != 200:
            raise ScrapingError(f"Kaggle public endpoint returned {response.status_code}")

        try:
            data = response.json()
        except ValueError as e:
            raise ScrapingError(f"Kaggle public invalid JSON: {e}")

        return self._parse_competitions(data, authenticated=False)

    def _parse_competitions(self, data: Any, authenticated: bool) -> List[Dict]:
        events: List[Dict] = []
        if not isinstance(data, list):
            return events

        for item in data:
            if not isinstance(item, dict):
                continue

            if authenticated:
                title = item.get("title") or item.get("competitionTitle")
                slug = item.get("ref") or item.get("competitionSlug") or item.get("slug")
                start_date = item.get("enabledDate") or item.get("startDate")
                end_date = item.get("deadline") or item.get("endDate")
                prize = item.get("reward") or item.get("totalPrize")
                description = item.get("description")
            else:
                title = item.get("competitionTitle") or item.get("title")
                slug = item.get("competitionSlug") or item.get("slug")
                start_date = item.get("startDate")
                end_date = item.get("deadline") or item.get("endDate")
                prize = item.get("reward")
                description = item.get("description")

            url = f"https://www.kaggle.com/competitions/{slug}" if slug else None
            event = {
                "title": title,
                "url": url,
                "start_date": start_date,
                "end_date": end_date,
                "prize": prize,
                "description": description,
                "mode": "online",
                "tags": ["Data Science", "ML"],
            }

            if event["title"] and event["url"]:
                events.append(event)

        logger.info("Kaggle returned %d competitions", len(events))
        return events
