"""
Hackathon Website Analyzer
Tests each website to determine:
1. Is it static HTML or dynamic (React/Vue/Angular)?
2. Does it have reCAPTCHA or other anti-bot measures?
3. Does it use lazy loading/infinite scroll?
4. Can we detect API endpoints?
5. What's the pagination type?
6. Does it require authentication?
"""

import requests
from bs4 import BeautifulSoup
import json
import time
import re
from typing import Dict, List
from urllib.parse import urlparse

# Terminal colors
class Colors:
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    MAGENTA = '\033[95m'
    RESET = '\033[0m'
    BOLD = '\033[1m'

# All websites to test
WEBSITES = {
    "MLH": "https://mlh.io/seasons/2025/events",
    "Devpost": "https://devpost.com/hackathons",
    "DoraHacks": "https://dorahacks.io/hackathon",
    "Devfolio": "https://devfolio.co/hackathons",
    "GeeksforGeeks": "https://www.geeksforgeeks.org/events/",
    "Unstop": "https://unstop.com/hackathons",
    "DevDisplay": "https://www.devdisplay.org/hackathons",
    "Superteam": "https://earn.superteam.fun/",
    "DevNovate": "https://devnovate.co/events",
    "Contra": "https://contra.com/community/topic/framerhackathon",
    "Maximally": "https://maximally.in/codehypothesis",
    "HackQuest": "https://www.hackquest.io/",
    "MyCareernet": "https://mycareernet.in/mycareernet/contests",
    "HackerEarth": "https://www.hackerearth.com/challenges/",
    "Hack2Skill": "https://www.hack2skill.com/",
    "TechGig": "https://www.techgig.com/challenge",
    "Kaggle": "https://www.kaggle.com/competitions",
    # Add more as needed
}

class WebsiteAnalyzer:
    def __init__(self):
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
        }
        self.results = {}
    
    def analyze_website(self, name: str, url: str) -> Dict:
        """Comprehensive analysis of a single website"""
        print(f"\n{Colors.BOLD}{Colors.CYAN}━━━ Analyzing: {name} ━━━{Colors.RESET}")
        print(f"URL: {url}")
        
        analysis = {
            'url': url,
            'accessible': False,
            'status_code': None,
            'content_type': 'Unknown',
            'framework': 'Unknown',
            'has_recaptcha': False,
            'has_cloudflare': False,
            'requires_auth': False,
            'has_api_hints': False,
            'pagination_type': 'Unknown',
            'lazy_loading': False,
            'event_count_estimate': 0,
            'scraping_difficulty': 'Unknown',
            'recommended_method': 'Unknown',
            'notes': []
        }
        
        try:
            # Make request
            response = requests.get(url, headers=self.headers, timeout=15, allow_redirects=True)
            analysis['status_code'] = response.status_code
            analysis['accessible'] = response.status_code == 200
            
            if not analysis['accessible']:
                analysis['notes'].append(f"HTTP {response.status_code}")
                self._print_result(name, analysis)
                return analysis
            
            html = response.text
            soup = BeautifulSoup(html, 'html.parser')
            
            # 1. Detect framework/type
            analysis['framework'] = self._detect_framework(html, soup)
            analysis['content_type'] = self._detect_content_type(html, soup)
            
            # 2. Check for anti-bot measures
            analysis['has_recaptcha'] = self._check_recaptcha(html)
            analysis['has_cloudflare'] = self._check_cloudflare(html, response.headers)
            
            # 3. Check for authentication requirements
            analysis['requires_auth'] = self._check_auth_required(html, soup, response.url)
            
            # 4. Look for API hints
            analysis['has_api_hints'] = self._detect_api_hints(html)
            
            # 5. Detect pagination type
            analysis['pagination_type'] = self._detect_pagination(soup)
            
            # 6. Check for lazy loading
            analysis['lazy_loading'] = self._check_lazy_loading(html, soup)
            
            # 7. Estimate event count on page
            analysis['event_count_estimate'] = self._estimate_event_count(soup)
            
            # 8. Determine scraping difficulty
            analysis['scraping_difficulty'] = self._assess_difficulty(analysis)
            
            # 9. Recommend scraping method
            analysis['recommended_method'] = self._recommend_method(analysis)
            
        except requests.exceptions.Timeout:
            analysis['notes'].append("Request timeout")
        except requests.exceptions.ConnectionError:
            analysis['notes'].append("Connection failed")
        except Exception as e:
            analysis['notes'].append(f"Error: {str(e)[:50]}")
        
        self._print_result(name, analysis)
        return analysis
    
    def _detect_framework(self, html: str, soup: BeautifulSoup) -> str:
        """Detect if site uses React, Vue, Angular, etc."""
        frameworks = []
        
        # Check for React
        if 'react' in html.lower() or soup.find(id=re.compile('.*react.*', re.I)):
            frameworks.append('React')
        if '__NEXT_DATA__' in html or '_next' in html:
            frameworks.append('Next.js')
        
        # Check for Vue
        if 'vue' in html.lower() or soup.find(attrs={'data-v-': True}):
            frameworks.append('Vue.js')
        
        # Check for Angular
        if 'ng-' in html or 'angular' in html.lower():
            frameworks.append('Angular')
        
        # Check for static generators
        if 'gatsby' in html.lower():
            frameworks.append('Gatsby')
        
        return ' + '.join(frameworks) if frameworks else 'Static HTML'
    
    def _detect_content_type(self, html: str, soup: BeautifulSoup) -> str:
        """Determine if content is static or dynamic"""
        # Check if page has substantial content
        text_length = len(soup.get_text(strip=True))
        
        # Look for JS-rendered content indicators
        js_indicators = [
            '__NEXT_DATA__',
            'window.__INITIAL_STATE__',
            'window.__data',
            '<div id="root"></div>',
            '<div id="app"></div>',
        ]
        
        has_js_indicators = any(indicator in html for indicator in js_indicators)
        
        if text_length < 1000 and has_js_indicators:
            return 'Dynamic (JS-rendered)'
        elif text_length > 1000:
            return 'Static HTML with content'
        else:
            return 'Hybrid'
    
    def _check_recaptcha(self, html: str) -> bool:
        """Check for reCAPTCHA"""
        recaptcha_patterns = [
            'google.com/recaptcha',
            'g-recaptcha',
            'recaptcha',
            'hcaptcha',
            'cf-turnstile',  # Cloudflare Turnstile
        ]
        return any(pattern in html.lower() for pattern in recaptcha_patterns)
    
    def _check_cloudflare(self, html: str, headers: Dict) -> bool:
        """Check for Cloudflare protection"""
        cf_indicators = [
            'cloudflare' in html.lower(),
            'cf-ray' in str(headers).lower(),
            '__cf_bm' in html,
            'Cloudflare' in headers.get('Server', ''),
        ]
        return any(cf_indicators)
    
    def _check_auth_required(self, html: str, soup: BeautifulSoup, final_url: str) -> bool:
        """Check if page requires authentication"""
        auth_indicators = [
            'login' in final_url.lower(),
            'signin' in final_url.lower(),
            soup.find('input', {'type': 'password'}) is not None,
            'sign in' in html.lower() and 'to view' in html.lower(),
            'create account' in html.lower() and 'required' in html.lower(),
        ]
        return any(auth_indicators)
    
    def _detect_api_hints(self, html: str) -> bool:
        """Look for hints that site uses API calls"""
        api_patterns = [
            r'/api/v\d+/',
            r'/api/',
            r'fetch\(',
            r'axios\.',
            r'\.json\(\)',
            r'graphql',
            r'apollo',
        ]
        return any(re.search(pattern, html, re.I) for pattern in api_patterns)
    
    def _detect_pagination(self, soup: BeautifulSoup) -> str:
        """Detect pagination type"""
        # Check for numbered pagination
        if soup.find_all('a', string=re.compile(r'^\d+$')):
            return 'Numbered pages'
        
        # Check for next/prev buttons
        if soup.find('a', string=re.compile(r'next|›|»', re.I)):
            return 'Next/Prev buttons'
        
        # Check for load more button
        if soup.find('button', string=re.compile(r'load more|show more', re.I)):
            return 'Load more button'
        
        # Check for infinite scroll indicators
        infinite_scroll_classes = ['infinite-scroll', 'lazy-load', 'auto-load']
        if any(soup.find(class_=re.compile(cls, re.I)) for cls in infinite_scroll_classes):
            return 'Infinite scroll'
        
        return 'No pagination detected'
    
    def _check_lazy_loading(self, html: str, soup: BeautifulSoup) -> bool:
        """Check if images/content are lazy loaded"""
        lazy_indicators = [
            soup.find_all('img', {'loading': 'lazy'}),
            'IntersectionObserver' in html,
            'data-src' in html,
            'lazy' in html.lower(),
        ]
        return any(lazy_indicators)
    
    def _estimate_event_count(self, soup: BeautifulSoup) -> int:
        """Estimate number of events visible on page"""
        # Look for common event card patterns
        possible_containers = [
            soup.find_all('div', class_=re.compile(r'event|hackathon|card|item', re.I)),
            soup.find_all('article'),
            soup.find_all('li', class_=re.compile(r'event|hackathon', re.I)),
        ]
        
        counts = [len(containers) for containers in possible_containers if containers]
        return max(counts) if counts else 0
    
    def _assess_difficulty(self, analysis: Dict) -> str:
        """Assess overall scraping difficulty"""
        difficulty_score = 0
        
        # Increase difficulty for various factors
        if analysis['content_type'] == 'Dynamic (JS-rendered)':
            difficulty_score += 3
        if analysis['has_recaptcha']:
            difficulty_score += 2
        if analysis['has_cloudflare']:
            difficulty_score += 1
        if analysis['requires_auth']:
            difficulty_score += 3
        if analysis['lazy_loading']:
            difficulty_score += 1
        if 'Infinite scroll' in analysis['pagination_type']:
            difficulty_score += 1
        
        # Decrease difficulty for positive factors
        if analysis['framework'] == 'Static HTML':
            difficulty_score -= 2
        if analysis['has_api_hints']:
            difficulty_score -= 1
        
        if difficulty_score >= 5:
            return 'HARD'
        elif difficulty_score >= 2:
            return 'MEDIUM'
        else:
            return 'EASY'
    
    def _recommend_method(self, analysis: Dict) -> str:
        """Recommend the best scraping approach"""
        if not analysis['accessible']:
            return 'BLOCKED - Needs investigation'
        
        if analysis['requires_auth']:
            return 'Browser automation with login'
        
        if analysis['has_api_hints'] and analysis['content_type'] == 'Dynamic (JS-rendered)':
            return 'API reverse-engineering (check network tab)'
        
        if analysis['content_type'] == 'Dynamic (JS-rendered)':
            return 'Browser automation (Playwright/Selenium)'
        
        if analysis['has_cloudflare'] or analysis['has_recaptcha']:
            return 'Browser automation with anti-detection'
        
        if analysis['framework'] == 'Static HTML':
            return 'Simple HTTP + BeautifulSoup ✓'
        
        return 'HTTP requests with API detection'
    
    def _print_result(self, name: str, analysis: Dict):
        """Print analysis results in a readable format"""
        print(f"\n{Colors.BOLD}Results:{Colors.RESET}")
        
        # Status
        status_color = Colors.GREEN if analysis['accessible'] else Colors.RED
        print(f"  Status: {status_color}{analysis['status_code']}{Colors.RESET}")
        
        # Framework
        framework_color = Colors.GREEN if 'Static' in analysis['framework'] else Colors.YELLOW
        print(f"  Framework: {framework_color}{analysis['framework']}{Colors.RESET}")
        
        # Content type
        print(f"  Content Type: {analysis['content_type']}")
        
        # Anti-bot measures
        if analysis['has_recaptcha']:
            print(f"  {Colors.RED}⚠ Has reCAPTCHA{Colors.RESET}")
        if analysis['has_cloudflare']:
            print(f"  {Colors.YELLOW}⚠ Cloudflare detected{Colors.RESET}")
        if analysis['requires_auth']:
            print(f"  {Colors.RED}⚠ Requires authentication{Colors.RESET}")
        
        # API hints
        if analysis['has_api_hints']:
            print(f"  {Colors.GREEN}✓ API endpoints detected{Colors.RESET}")
        
        # Pagination
        print(f"  Pagination: {analysis['pagination_type']}")
        
        # Events count
        if analysis['event_count_estimate'] > 0:
            print(f"  Events on page: ~{analysis['event_count_estimate']}")
        
        # Difficulty
        diff_color = {
            'EASY': Colors.GREEN,
            'MEDIUM': Colors.YELLOW,
            'HARD': Colors.RED
        }.get(analysis['scraping_difficulty'], Colors.RESET)
        print(f"  Difficulty: {diff_color}{analysis['scraping_difficulty']}{Colors.RESET}")
        
        # Recommendation
        print(f"\n  {Colors.BOLD}{Colors.CYAN}Recommended Method:{Colors.RESET}")
        print(f"  → {analysis['recommended_method']}")
        
        # Notes
        if analysis['notes']:
            print(f"\n  {Colors.MAGENTA}Notes: {', '.join(analysis['notes'])}{Colors.RESET}")
    
    def analyze_all(self):
        """Analyze all websites"""
        print(f"{Colors.BOLD}{Colors.BLUE}")
        print("=" * 60)
        print("  HACKATHON WEBSITE ANALYZER")
        print("=" * 60)
        print(f"{Colors.RESET}\n")
        
        for name, url in WEBSITES.items():
            self.results[name] = self.analyze_website(name, url)
            time.sleep(2)  # Be respectful with requests
        
        self._print_summary()
    
    def _print_summary(self):
        """Print summary of all results"""
        print(f"\n\n{Colors.BOLD}{Colors.BLUE}")
        print("=" * 60)
        print("  SUMMARY")
        print("=" * 60)
        print(f"{Colors.RESET}\n")
        
        # Group by difficulty
        easy = []
        medium = []
        hard = []
        blocked = []
        
        for name, analysis in self.results.items():
            if not analysis['accessible']:
                blocked.append(name)
            elif analysis['scraping_difficulty'] == 'EASY':
                easy.append(name)
            elif analysis['scraping_difficulty'] == 'MEDIUM':
                medium.append(name)
            else:
                hard.append(name)
        
        print(f"{Colors.GREEN}EASY (Simple HTTP + HTML parsing):{Colors.RESET}")
        for site in easy:
            method = self.results[site]['recommended_method']
            print(f"  ✓ {site:20} - {method}")
        
        print(f"\n{Colors.YELLOW}MEDIUM (May need browser automation):{Colors.RESET}")
        for site in medium:
            method = self.results[site]['recommended_method']
            print(f"  ⚠ {site:20} - {method}")
        
        print(f"\n{Colors.RED}HARD (Complex scraping required):{Colors.RESET}")
        for site in hard:
            method = self.results[site]['recommended_method']
            print(f"  ✗ {site:20} - {method}")
        
        if blocked:
            print(f"\n{Colors.RED}BLOCKED/ERROR:{Colors.RESET}")
            for site in blocked:
                notes = self.results[site]['notes']
                print(f"  ✗ {site:20} - {', '.join(notes)}")
        
        # Statistics
        print(f"\n{Colors.BOLD}Statistics:{Colors.RESET}")
        print(f"  Total sites: {len(self.results)}")
        print(f"  {Colors.GREEN}Easy: {len(easy)}{Colors.RESET}")
        print(f"  {Colors.YELLOW}Medium: {len(medium)}{Colors.RESET}")
        print(f"  {Colors.RED}Hard: {len(hard)}{Colors.RESET}")
        print(f"  {Colors.RED}Blocked: {len(blocked)}{Colors.RESET}")
        
        # Save to JSON
        self._save_results()
    
    def _save_results(self):
        """Save results to JSON file"""
        filename = 'website_analysis_results.json'
        with open(filename, 'w') as f:
            json.dump(self.results, f, indent=2)
        print(f"\n{Colors.CYAN}Results saved to: {filename}{Colors.RESET}")


if __name__ == "__main__":
    analyzer = WebsiteAnalyzer()
    analyzer.analyze_all()
