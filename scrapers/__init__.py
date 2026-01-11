# Scrapers Package
"""
Scraper modules for hackathon data extraction.

Available scrapers:
- BaseScraper: Abstract base class with waterfall approach
- HttpScraper: For static HTML sites
- BrowserScraper: For JS-heavy/protected sites
"""

from scrapers.base_scraper import BaseScraper, ScraperFactory, ScrapingError
