"""
Multi-Site Hackathon Scraper - Consolidated
===========================================
Single entry point for all hackathon scraping logic.
Combines API-based scraping (fast) and Browser-based scraping (robust).
"""
import sys
import re
import json
import time
import requests
from datetime import datetime, timedelta
from urllib.parse import urljoin, urlparse
from bs4 import BeautifulSoup
from concurrent.futures import ThreadPoolExecutor, as_completed

# Add local path
sys.path.insert(0, '.')

from database.db_manager import DatabaseManager
from utils.data_normalizer import DataNormalizer

# Initialize global objects
headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0', 
    'Accept': 'application/json, text/html, */*'
}
db = DatabaseManager('hackathons.db')
normalizer = DataNormalizer()

# ==========================================
# Metadata Extraction Helpers
# ==========================================

def clean_html(html_text):
    """Remove HTML tags and clean text"""
    if not html_text:
        return ""
    soup = BeautifulSoup(html_text, 'html.parser')
    text = soup.get_text(separator=' ', strip=True)
    # Remove extra whitespace
    text = re.sub(r'\s+', ' ', text)
    return text.strip()

def extract_tags_from_text(text, max_tags=10):
    """Extract relevant keywords as tags from text"""
    if not text:
        return []
    
    # Common tech keywords to look for
    keywords = [
        'AI', 'ML', 'machine learning', 'blockchain', 'web3', 'crypto',
        'mobile', 'app', 'android', 'ios', 'web', 'frontend', 'backend',
        'cloud', 'security', 'cybersecurity', 'data', 'IoT', 'AR', 'VR',
        'gaming', 'fintech', 'healthcare', 'education', 'sustainability',
        'beginner', 'student', 'online', 'virtual', 'remote'
    ]
    
    text_lower = text.lower()
    found_tags = []
    
    for kw in keywords:
        if kw.lower() in text_lower and kw not in found_tags:
            found_tags.append(kw)
            if len(found_tags) >= max_tags:
                break
    
    return found_tags

# ==========================================
# Detail Page Scrapers
# ==========================================

def scrape_devpost_details(event_url):
    """Scrape description, tags, themes from Devpost event page"""
    try:
        r = requests.get(event_url, headers=headers, timeout=10)
        if r.status_code != 200:
            return None
        
        soup = BeautifulSoup(r.text, 'html.parser')
        
        # Description from .content or fallback to large text blocks
        description = ""
        for selector in ['.content', '#content', '.challenge-description', '.software-body']:
            content = soup.select_one(selector)
            if content:
                description = content.get_text(separator=' ', strip=True)[:1000]
                if len(description) > 50:  # Found meaningful content
                    break
        
        # Fallback: get all paragraphs
        if len(description) < 50:
            paragraphs = soup.select('p')
            description = ' '.join([p.get_text(strip=True) for p in paragraphs[:10]])[:1000]
        
        # Tags from eligibility requirements
        tags = []
        requirements = soup.select('.requirements-col li, .requirements li')
        for req in requirements:
            text = req.get_text(strip=True).lower()
            if 'student' in text: tags.append('student')
            if 'beginner' in text: tags.append('beginner')
            if 'college' in text: tags.append('student')
        
        # Extract more tags from description
        tags.extend(extract_tags_from_text(description))
        tags = list(set(tags))[:10]  # Deduplicate and limit
        
        # Themes from JSON-LD metadata
        themes = []
        jsonld = soup.select_one('script[type="application/ld+json"]')
        if jsonld:
            try:
                import json
                data = json.loads(jsonld.string)
                if isinstance(data, dict):
                    # Try to get keywords or category
                    if data.get('keywords'):
                        themes = data['keywords'] if isinstance(data['keywords'], list) else [data['keywords']]
            except:
                pass
                
        # Scrape Team Size from Text
        team_size = None
        ts_text = soup.get_text()
        ts_match = re.search(r'Team\s*Size:?\s*(\d+)(?:\s*[-–]\s*(\d+))?', ts_text, re.IGNORECASE)
        if ts_match:
            min_s = ts_match.group(1)
            max_s = ts_match.group(2)
            team_size = f"{min_s}-{max_s}" if max_s else min_s

        # Scrape Participants count
        participants = None
        p_match = re.search(r'([\d,]+)\s+registered', ts_text, re.IGNORECASE)
        if p_match:
            participants = int(p_match.group(1).replace(',', ''))

        # Scrape Prize (Total)
        prize = None
        prize_match = re.search(r'([\$\£\€][\d,]+)', ts_text)
        if prize_match and 'prize' in ts_text.lower():
             prize = prize_match.group(1)

        # Scrape Location/Mode
        location = None
        mode = None
        
        # Check metadata sidebar or header
        if 'online' in ts_text.lower() or 'virtual' in ts_text.lower():
             mode = 'online'
             if not location: location = 'Online'
        
        # Try to find date meta tags if available, otherwise rely on text
        # (Dates are usually parsed from listing, but detail page helps if listing failed)
        
        return {
            'description': description, 
            'tags': tags, 
            'themes': themes, 
            'team_size_max': team_size, # Map to 'team_size_max' key preferred by normalizer?
            'participants_count': participants,
            'prize': prize,
            'location': location,
            'mode': mode
        }
        
        return {'description': description, 'tags': tags, 'themes': themes, 'team_size': team_size}
    except Exception as e:
        return None

def scrape_devfolio_details(event_slug):
    """Scrape description and domains from Devfolio event page"""
    try:
        url = f"https://{event_slug}.devfolio.co/overview"
        r = requests.get(url, headers=headers, timeout=10)
        if r.status_code != 200:
            return None
        
        soup = BeautifulSoup(r.text, 'html.parser')
        
        # Get page text, skip nav/header elements
        # Remove nav and header elements first
        for nav in soup.select('nav, header, footer, script, style'):
            nav.decompose()
        
        # Get main content paragraphs
        paragraphs = []
        for p in soup.select('p, h1, h2, h3, li'):
            text = p.get_text(strip=True)
            if len(text) > 30 and 'Overview' not in text and 'Prizes' not in text:
                paragraphs.append(text)
        
        description = " ".join(paragraphs[:10])[:1000]
        
        # Themes/Domains - look for domain keywords in full page text
        themes = []
        page_text = soup.get_text()
        domain_keywords = [
            'AI', 'Machine Learning', 'Web3', 'Blockchain', 'Cloud', 
            'Security', 'FinTech', 'Healthcare', 'IoT', 'AR/VR',
            'Mobile', 'Open Innovation', 'Social Good', 'Education'
        ]
        for kw in domain_keywords:
            if kw.lower() in page_text.lower():
                themes.append(kw)
        themes = themes[:10]
        
        # Extract tags from description
        tags = extract_tags_from_text(description)
        
        return {'description': description, 'tags': tags, 'themes': themes}
    except Exception as e:
        return None

def fetch_unstop_details_api(event_id):
    """
    Fetch details for a single event ID from Unstop API.
    Returns parsed dict or None.
    """
    try:
        api_url = f"https://unstop.com/api/public/competition/{event_id}?round_lang=1"
        r = requests.get(api_url, headers=headers, timeout=10)
        
        if r.status_code != 200:
            return None
        
        data = r.json()
        comp = data.get('data', {}).get('competition', {})
        if not comp:
             return None
             
        # Extract fields
        reg_req = comp.get('regnRequirements', {})
        
        # Deadlines
        reg_end_iso = reg_req.get('end_regn_dt')
        reg_start_iso = reg_req.get('start_regn_dt')
        
        # Description
        raw_desc = comp.get('details', '')
        # Simple clean since we don't have the clean_html helper here, use BS4
        description = ""
        if raw_desc:
            soup = BeautifulSoup(raw_desc, 'html.parser')
            description = soup.get_text(separator=' ', strip=True)[:3000]
            
        # Team Size
        ts_min = None
        ts_max = None
        
        if 'min_team_size' in reg_req:
            ts_min = reg_req.get('min_team_size')
        if 'max_team_size' in reg_req:
            ts_max = reg_req.get('max_team_size')
            
        if ts_min is None or ts_max is None:
            ts_str = reg_req.get('teamSize')
            if ts_str:
                parts = re.findall(r'\d+', str(ts_str))
                if len(parts) >= 2:
                    ts_min = int(parts[0])
                    ts_max = int(parts[1])
                elif len(parts) == 1:
                    val = int(parts[0])
                    ts_min = val
                    ts_max = val
        
        # Extract tags from description
        tags = extract_tags_from_text(description)
        
        return {
            'end_date': reg_end_iso, # Prefer reg end date
            'reg_start': reg_start_iso,
            'description': description,
            'tags': tags,
            'themes': [],
            'team_size_min': ts_min,
            'team_size_max': ts_max,
            'team_size_max': ts_max,
            'region': comp.get('region'),
            'city': comp.get('address_with_country_logo', {}).get('city'),
            'state': comp.get('address_with_country_logo', {}).get('state'),
            'registerCount': comp.get('registerCount', 0)
        }
    except Exception as e:
        return None

# ==========================================
# Parallel Scraper Helpers
# ==========================================

def fetch_details_parallel(items, fetch_func, max_workers=20):
    """
    Fetch details for a list of items in parallel.
    items: list of dicts with 'url_or_id' key
    fetch_func: function that takes url_or_id and returns dict
    """
    results = {}
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_to_item = {executor.submit(fetch_func, item['url_or_id']): item for item in items}
        
        for future in as_completed(future_to_item):
            item = future_to_item[future]
            try:
                data = future.result()
                if data:
                    results[item['id']] = data
            except Exception as e:
                pass
    return results

# ==========================================
# Helpers
# ==========================================

def parse_epoch(timestamp):
    """Convert epoch timestamp to ISO date string."""
    if not timestamp: return None
    try:
        ts = int(timestamp)
        if ts > 9999999999: ts = ts / 1000
        return datetime.fromtimestamp(ts).strftime('%Y-%m-%d')
    except: return None

def parse_iso_timestamp(ts):
    """Parse ISO timestamp to date string."""
    if not ts: return None
    try:
        if isinstance(ts, str): return ts[:10] if len(ts) >= 10 else None
        return None
    except: return None

def safe_get(url, timeout=30):
    try: return requests.get(url, headers=headers, timeout=timeout)
    except: return None

def _extract_jsonld_events(data, base_url):
    """Extract events from JSON-LD data."""
    items = []
    if isinstance(data, list): items = data
    elif isinstance(data, dict):
        items = data.get('@graph', [data])

    events = []
    for item in items:
        if not isinstance(item, dict): continue
        
        # Check type
        etype = item.get('@type')
        is_event = False
        if isinstance(etype, list): is_event = any(str(t).lower() == 'event' for t in etype)
        else: is_event = str(etype).lower() == 'event'
        if not is_event: continue

        title = item.get('name') or item.get('title')
        url = item.get('url') or item.get('@id')
        if url and isinstance(url, str) and url.startswith('/'):
            url = urljoin(base_url, url)

        start = item.get('startDate') or item.get('start_date')
        end = item.get('endDate') or item.get('end_date')
        
        # Location parsing
        loc_val = item.get('location')
        location = ''
        if isinstance(loc_val, dict):
            location = loc_val.get('name') or ''
        elif isinstance(loc_val, str):
            location = loc_val

        if title and url:
            events.append({
                'title': title, 'url': url, 'start_date': start, 'end_date': end, 
                'location': location, 'image': item.get('image')
            })
    return events

# ==========================================
# API Scrapers
# ==========================================

def scrape_devpost():
    print('\n📦 Devpost...')
    saved = 0
    # Regex patterns
    pat_full = re.compile(r'([A-Za-z]{3}\s+\d{1,2},\s+\d{4})')
    pat_same_month = re.compile(r'([A-Za-z]{3})\s+(\d{1,2})\s*-\s*(\d{1,2}),\s+(\d{4})')
    pat_diff_month = re.compile(r'([A-Za-z]{3})\s+(\d{1,2})\s*-\s*([A-Za-z]{3})\s+(\d{1,2}),\s+(\d{4})')
    
    print(f'  Fetching pages...')
    
    # 1. Collect all events first
    total_hackathons = []
    
    for page in range(1, 6):
        try:
            r = safe_get(f'https://devpost.com/api/hackathons?page={page}&per_page=50')
            if not r: break
            
            hackathons = r.json().get('hackathons', [])
            if not hackathons: break
            
            total_hackathons.extend(hackathons)
        except: break
            
    print(f'  Found {len(total_hackathons)} events. Fetching details in parallel...')
    
    # Prepare for parallel fetch
    to_fetch = []
    for h in total_hackathons:
        if h.get('url'):
            to_fetch.append({'id': h['url'], 'url_or_id': h['url']})
    
    # Fetch details
    details_map = fetch_details_parallel(to_fetch, scrape_devpost_details, max_workers=20)
    
    # Save events with details
    saved = 0
    for h in total_hackathons:
        try:
            # Dates logic (kept from original)
            dates = h.get('submission_period_dates', {})
            start_date = None
            end_date = None
            
            if isinstance(dates, dict):
                start_date = parse_iso_timestamp(dates.get('starts_at'))
                end_date = parse_iso_timestamp(dates.get('ends_at'))
            elif isinstance(dates, str) and dates:
                dates = dates.replace(u'\xa0', u' ').strip()
                # Try Same Month
                m2 = pat_same_month.search(dates)
                if m2:
                    mon, d1, d2, y = m2.groups()
                    start_date = datetime.strptime(f"{mon} {d1}, {y}", '%b %d, %Y').strftime('%Y-%m-%d')
                    end_date = datetime.strptime(f"{mon} {d2}, {y}", '%b %d, %Y').strftime('%Y-%m-%d')
                # Try Diff Month
                if not start_date:
                    m3 = pat_diff_month.search(dates)
                    if m3:
                        mon1, d1, mon2, d2, y = m3.groups()
                        start_date = datetime.strptime(f"{mon1} {d1}, {y}", '%b %d, %Y').strftime('%Y-%m-%d')
                        end_date = datetime.strptime(f"{mon2} {d2}, {y}", '%b %d, %Y').strftime('%Y-%m-%d')
                # Try Full
                if not start_date:
                    matches = pat_full.findall(dates)
                    if matches:
                        try:
                            start_date = datetime.strptime(matches[0], '%b %d, %Y').strftime('%Y-%m-%d')
                            if len(matches) > 1:
                                end_date = datetime.strptime(matches[1], '%b %d, %Y').strftime('%Y-%m-%d')
                        except: pass
            
            # Get details
            details = details_map.get(h.get('url'))
            if details:
                description = details.get('description', '')
                tags = details.get('tags', [])
                themes = details.get('themes', [])
                # Prefer detail team size if found
                if details.get('team_size'):
                    h['team_size'] = details.get('team_size')
            else:
                # Fallback to tagline
                description = h.get('tagline', '')
                tags = extract_tags_from_text(description)
                themes = h.get('themes', [])
            
            raw = {
                'title': h.get('title'),
                'url': h.get('url'),
                'start_date': start_date,
                'end_date': end_date,
                'location': 'Online' if h.get('online_only') else h.get('displayed_location', ''),
                'prize': h.get('prize_amount'),
                'mode': 'online' if h.get('online_only') else 'in-person',
                'participants_count': h.get('registrations_count'),
                'team_size_max': h.get('team_size'),
                'description': description,
                'tags': tags,
                'themes': themes
            }
            if raw['title']: db.save_event(normalizer.normalize(raw, 'Devpost')); saved += 1
        except: pass
        
    print(f'  ✓ {saved}')
    return saved

def scrape_devfolio():
    print('\n🎯 Devfolio (API-Enhanced)...')
    saved = 0
    try:
        # 1. Collect all events first via search API
        all_events = []
        for list_type in ['application_open', 'all']:
            try:
                r = requests.post('https://api.devfolio.co/api/search/hackathons', 
                                 json={"type": list_type, "from": 0, "size": 100}, 
                                 headers=headers, timeout=30)
                all_events.extend(r.json().get('hits', {}).get('hits', []))
            except: pass
        
        # Deduplicate by slug
        unique_events = {}
        for h in all_events:
            src = h.get('_source', {})
            slug = src.get('slug')
            if slug: unique_events[slug] = src
        
        total_events = list(unique_events.values())
        print(f'  Found {len(total_events)} events. Fetching details via API...')
        
        # 2. Fetch details via API for each hackathon
        for i, src in enumerate(total_events):
            try:
                slug = src.get('slug')
                if not slug:
                    continue
                
                # Fetch detailed data via API
                details = fetch_devfolio_details_api(slug)
                
                if details:
                    # Use API data (priority)
                    start_date = details.get('start_date')
                    end_date = details.get('end_date')  # This is registration end date
                    prize = details.get('prize', 'Prize TBD')
                    team_size_min = details.get('team_size_min')
                    team_size_max = details.get('team_size_max')
                    mode = details.get('mode', 'online')
                    location = details.get('location', 'Online')
                    participants_count = details.get('participants_count')
                    description = details.get('description', '')
                else:
                    # Fallback to search API data
                    s_at, e_at = src.get('starts_at'), src.get('ends_at')
                    start_date = parse_epoch(s_at) if isinstance(s_at, (int, float)) else parse_iso_timestamp(s_at)
                    end_date = parse_epoch(e_at) if isinstance(e_at, (int, float)) else parse_iso_timestamp(e_at)
                    prize = src.get('prize_amount') or 'Prize TBD'
                    team_size_min = src.get('team_min')
                    team_size_max = src.get('team_size')
                    mode = 'online' if src.get('is_online_event') else 'in-person'
                    location = src.get('location') or ('Online' if src.get('is_online_event') else '')
                    participants_count = src.get('participants_count')
                    tagline = src.get('tagline', '')
                    desc = src.get('desc', '')
                    description = f"{tagline}. {desc}"[:500]
                
                # Extract tags from description
                tags = extract_tags_from_text(description)
                themes = src.get('themes', [])
                
                raw = {
                    'title': src.get('name'),
                    'url': f"https://{slug}.devfolio.co/",
                    'start_date': start_date,
                    'end_date': end_date,
                    'location': location,
                    'prize': prize,
                    'mode': mode,
                    'participants_count': participants_count,
                    'team_size_min': team_size_min,
                    'team_size_max': team_size_max,
                    'description': description,
                    'tags': tags,
                    'themes': themes
                }
                if raw['title'] and raw['url']:
                    db.save_event(normalizer.normalize(raw, 'Devfolio'))
                    saved += 1
                    
                # Progress indicator
                if (i + 1) % 20 == 0:
                    print(f'    Processed {i + 1}/{len(total_events)}...')
                    
            except Exception as e:
                pass
                
    except Exception as e:
        print(f'  Error: {e}')
    print(f'  ✓ {saved}')
    return saved





def scrape_hackculture():
    print('\n🏛️ HackCulture (Browser)...')
    saved = 0
    try:
        from playwright.sync_api import sync_playwright
        from bs4 import BeautifulSoup
        
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            # Visit /challenges directly
            page.goto('https://hackculture.io/challenges', wait_until='networkidle', timeout=60000)
            
            # Scroll to trigger lazy loading
            for _ in range(3):
                page.evaluate('window.scrollTo(0, document.body.scrollHeight)')
                page.wait_for_timeout(1000)
            
            html = page.content()
            browser.close()

        soup = BeautifulSoup(html, 'html.parser')
        
        # Extract events from rendered HTML
        seen = set()
        for a in soup.find_all('a', href=True):
            href = a['href']
            # Look for challenge links
            if '/challenges/' in href and len(href) > 15:
                if href in seen: continue
                seen.add(href)
                
                # Ensure full URL
                if not href.startswith('http'): 
                    href = urljoin('https://hackculture.io', href)
                
                # Extract title from card text or alt text
                title = a.get_text(strip=True)
                if not title:
                    title = a.find('h3').get_text(strip=True) if a.find('h3') else a.get_text(strip=True)
            
            # Extract Text for parsing
            text = a.get_text(separator=' ', strip=True)
            
            # Extract Date (e.g. "Oct 1 - Oct 5") - HackQuest dates are often range without year on card
            # We will try to parse assuming current/next year context in normalizer if needed, or just leave as text if logic allows
            start_date = None
            # Regex for "Mon DD"
            date_match = re.search(r'([A-Za-z]{3}\s+\d{1,2})', text)
            if date_match:
                 # Minimal effort date parsing, often insufficient without year, but better than nothing?
                 # Actually, let's leave start_date None if no year, to avoid bad data.
                 # Unless we assume 2025?
                 pass

            # Extract Prize
            prize = "Prize TBD"
            prize_match = re.search(r'[₹$]\s?[\d,]+', text)
            if prize_match: prize = prize_match.group(0)

            if len(title) > 3:
                raw = {
                    'title': title, 
                    'url': href, 
                    'start_date': None, # Difficult to extract year from card
                    'mode': 'online',
                    'prize': prize,
                    'participants_count': None,
                    'team_size_max': None
                }
                db.save_event(normalizer.normalize(raw, 'HackCulture')); saved += 1
                    
    except Exception as e: print(f'  Error: {e}')
    print(f'  ✓ {saved}')
    return saved



def scrape_unstop():
    print('\n🎪 Unstop...')
    saved = 0
    try:
        # 1. Collect all events first
        all_events = []
        for page in range(1, 4):  # Limit pages for speed if needed, or keep original range
            try:
                r = requests.get(f'https://unstop.com/api/public/opportunity/search-result?opportunity=hackathons&per_page=100&page={page}',
                                headers=headers, timeout=30)
                data = r.json().get('data', {}).get('data', [])
                if not data: break
                all_events.extend(data)
            except: pass
        
        print(f'  Found {len(all_events)} events. Fetching details in parallel...')
        
        # 2. Prepare for parallel fetch
        to_fetch = []
        for h in all_events:
            # Prefer ID for API lookup
            eid = h.get('id')
            if eid:
                to_fetch.append({'id': str(eid), 'url_or_id': eid})
        
        # 3. Fetch details
        details_map = fetch_details_parallel(to_fetch, fetch_unstop_details_api, max_workers=20)
        
        # 4. Save events with details
        for h in all_events:
            try:
                # Dates: try regnRequirements or top level
                regn = h.get('regnRequirements', {})
                start = h.get('start_date')
                if not start: start = regn.get('start_regn_dt')
                
                end = h.get('end_date')
                if not end: end = regn.get('end_regn_dt')
                
                start_date = parse_iso_timestamp(start)
                end_date = parse_iso_timestamp(end)
                
                # Location
                addr = h.get('address_with_country_logo', {})
                city = addr.get('city')
                state = addr.get('state')
                location = "Online"
                mode = "online"
                
                region = h.get('region')
                if region == 'offline' or city:
                    mode = 'in-person'
                    loc_parts = [p for p in [city, state] if p]
                    location = ", ".join(loc_parts) if loc_parts else "In-Person"
                
                # Prize
                prize = "TBD"
                prizes_list = h.get('prizes', [])
                if prizes_list:
                    total_cash = 0
                    currency = "₹"
                    for p in prizes_list:
                        try:
                            total_cash += int(float(str(p.get('cash', 0))))
                            if p.get('currency') == 'fa-rupee': currency = "₹"
                            elif p.get('currency') == 'fa-dollar': currency = "$"
                        except: pass
                    if total_cash > 0:
                        prize = f"{currency}{total_cash:,}"
                
                # Get details
                eid = str(h.get('id', ''))
                details = details_map.get(eid)
                
                description = ""
                tags = []
                themes = []
                ts_min = None
                ts_max = None
                
                if details:
                    description = details.get('description', '')
                    tags = details.get('tags', [])
                    themes = details.get('themes', [])
                    ts_min = details.get('team_size_min')
                    ts_max = details.get('team_size_max')
                    # Prefer detailed dates
                    if details.get('end_date'): end_date = parse_iso_timestamp(details.get('end_date'))
                    
                    # Mode & Location from details
                    reg = details.get('region')
                    if reg:
                        if reg.lower() == 'online':
                            mode = 'online'
                            location = 'Online'
                        elif reg.lower() == 'offline':
                            mode = 'in-person'
                            parts = [p for p in [details.get('city'), details.get('state')] if p]
                            location = ", ".join(parts) if parts else "In-Person"
                            
                    # Participants
                    if details.get('registerCount') is not None:
                         # Prefer details count
                         h['registerCount'] = details.get('registerCount')

                else:
                    # Fallback
                    eligibility = h.get('eligibility', '')
                    description = eligibility[:500]
                    tags = extract_tags_from_text(description)
                    themes = []
                    # Do NOT map 'show_team_size' here as it's often 0/1 boolean
                
                public_url = h.get('public_url', '')
                full_url = f"https://unstop.com/{public_url}" if not public_url.startswith('http') else public_url

                raw = {
                    'title': h.get('title'), 
                    'url': full_url,
                    'start_date': start_date, 
                    'end_date': end_date, 
                    'location': location,
                    'mode': mode,
                    'prize': prize,
                    'participants_count': h.get('registerCount'),
                    'team_size_min': ts_min,
                    'team_size_max': ts_max,
                    'description': description,
                    'tags': tags,
                    'themes': themes
                }
                db.save_event(normalizer.normalize(raw, 'Unstop')); saved += 1
            except Exception as e: 
                # print(f"Unstop Error: {e}") 
                pass
    except: pass
    print(f'  ✓ {saved}')
    return saved


def scrape_mlh():
    print('\n🏆 MLH...')
    saved = 0
    try:
        from bs4 import BeautifulSoup
        import concurrent.futures
        
        events_to_process = []
        
        # 1. Scrape Listing
        for year in ['2025', '2026']:
            r = safe_get(f'https://mlh.io/seasons/{year}/events')
            if not r: continue
            
            soup = BeautifulSoup(r.text, 'html.parser')
            for link in soup.find_all('a', href=True):
                href = link['href']
                
                # Filter: Allow external links OR useful MLH subdomains
                # Exclude simple nav links like /, /login, /about, /seasons
                if href in ['/', '#'] or '/seasons' in href or '/signin' in href or '/oauth' in href:
                    continue
                if 'http' not in href:
                    if href.startswith('/'): href = f'https://mlh.io{href}'
                
                # Validation: Link must have some text content
                text_blob = link.get_text(" | ", strip=True) 
                if len(text_blob) < 5: continue
                
                # Heuristics extraction
                # Title: Try H3, else first chunk
                title = "Unknown MLH Event"
                h3 = link.find('h3')
                if h3:
                    title = h3.get_text(strip=True)
                else:
                    title = text_blob.split('|')[0].strip()
                    
                # Date Regex (Robust)
                # Matches: "May 5", "May 5th", "May 5 - 7", "May 5 - May 7"
                date_match = re.search(r'(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\.?\s+(\d{1,2})(?:st|nd|rd|th)?(?:\s*[-–]\s*(?:(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\.?\s+)?(\d{1,2}))?', text_blob, re.IGNORECASE)
                
                start_date = None
                end_date = None
                if date_match:
                    try:
                        month = date_match.group(1)
                        day = date_match.group(2)
                        year_val = year
                        # Construct ISO date (simple logic)
                        from datetime import datetime
                        # Handle "Dec" events in "2025" season usually appearing in late 2024? 
                        # Assume season year for now.
                        d_str = f"{month} {day} {year_val}"
                         # Parse
                        dt = datetime.strptime(d_str, '%b %d %Y')
                        start_date = dt.strftime('%Y-%m-%d')
                        # End date
                        if date_match.group(3):
                             end_day = date_match.group(3)
                             dt_end = dt.replace(day=int(end_day)) # simplistic (ignoring month rollover)
                             end_date = dt_end.strftime('%Y-%m-%d')
                        else:
                             end_date = start_date
                    except: pass
                    
                # Location: Look for pattern "City, State"
                location = "Online" if ('virtual' in text_blob.lower() or 'online' in text_blob.lower()) else "TBA"
                if location == "TBA":
                    # Try to find "City, State"
                    loc_match = re.search(r'([A-Z][a-zA-Z\s\.]+,\s*[A-Z][a-zA-Z\s\.]+)', text_blob)
                    if loc_match:
                         location = loc_match.group(1).strip()
                    
                mode = 'online' if location == 'Online' else 'in-person'
                
                raw = {
                    'title': title,
                    'url': href,
                    'mode': mode,
                    'source': 'MLH',
                    'start_date': start_date,
                    'end_date': end_date,
                    'location': location
                }
                events_to_process.append(raw)

        # Unique by URL
        unique_events = {e['url']: e for e in events_to_process}.values()
        print(f"  Found {len(unique_events)} potential events. Enriching...")

        # 2. Enrich Data (Parallel)
        def fetch_enrichment(e):
            url = e['url']
            try:
                # Devpost
                if 'devpost.com' in url:
                    return scrape_devpost_details(url)
                # Devfolio
                elif 'devfolio.co' in url:
                    slug = None
                    if 'devfolio.co/' in url:
                         slug = url.split('devfolio.co/')[1].split('/')[0]
                    else:
                         slug = url.split('//')[1].split('.')[0]
                    if slug: 
                        return fetch_devfolio_details_api(slug)
                # Generic / Custom Site
                else:
                    # Visit page to get meta tags or better title/date
                    sub_r = safe_get(url)
                    if sub_r:
                        sub_soup = BeautifulSoup(sub_r.text, 'html.parser')
                        # Extract meta description
                        meta_desc = ""
                        og_desc = sub_soup.select_one('meta[property="og:description"]')
                        if og_desc: meta_desc = og_desc.get('content')
                        
                        # JSON-LD?
                        json_data = _extract_jsonld_events(sub_soup, url) # Helper exists in file? Or _extract_events_from_structure? 
                        # _extract_jsonld_events checks for list of events, we assume single?
                        # Let's inspect title
                        page_title = sub_soup.title.string if sub_soup.title else ""
                        
                        return {'description': meta_desc, 'page_title': page_title}
            except: pass
            return None

        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
            future_to_event = {executor.submit(fetch_enrichment, e): e for e in unique_events}
            
            for future in concurrent.futures.as_completed(future_to_event):
                e = future_to_event[future]
                result = future.result()
                
                if result:
                    # Merge details
                    e.update(result)
                    
                    # If we got a generic page title and original title was "Unknown", update it
                    if e['title'] == "Unknown MLH Event" and result.get('page_title'):
                         e['title'] = result.get('page_title').split('|')[0].strip()
                    
                    # Fix devpost participants mapping
                    if 'participants' in result and not 'participants_count' in e:
                         e['participants_count'] = result['participants']

                # Save
                db.save_event(normalizer.normalize(e, 'MLH'))
                saved += 1
                
    except Exception as e: 
        print(f"  MLH Error: {e}")
        import traceback
        traceback.print_exc()
        
    print(f'  ✓ {saved}')
    return saved

def scrape_superteam():
    print('\n☀️ Superteam...')
    saved = 0
    try:
        r = safe_get('https://earn.superteam.fun/api/listings/?type=hackathon')
        if r:
            for h in r.json()[:50]:
                raw = {'title': h.get('title'), 'url': h.get('link'), 'prize': h.get('rewardAmount'), 'mode': 'online',
                       'participants_count': h.get('_count', {}).get('Submission') if isinstance(h.get('_count'), dict) else None,
                       'team_size_max': h.get('team_size')}
                db.save_event(normalizer.normalize(raw, 'Superteam')); saved += 1
    except: pass
    print(f'  ✓ {saved}')
    return saved



# ==========================================
# Browser Scrapers (Consolidated)
# ==========================================




def scrape_dorahacks():
    print('\n🐶 DoraHacks (Browser - Anti-Bot)...')
    saved = 0
    try:
        from playwright.sync_api import sync_playwright
        from bs4 import BeautifulSoup
        import random
        
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            # Use stealthy context options
            context = browser.new_context(
                user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                viewport={'width': 1366, 'height': 768},
                device_scale_factor=1,
            )
            page = context.new_page()
            
            # Go to home first
            try:
                page.goto('https://dorahacks.io/', wait_until='domcontentloaded', timeout=30000)
                page.wait_for_timeout(2000 + random.randint(100, 1000))
                
                # Look for "Hackathon" link
                # Typically in nav
                page.click('a[href="/hackathon"]')
                page.wait_for_load_state('networkidle', timeout=30000)
                
            except:
                # Fallback to direct navigation if click fails
                page.goto('https://dorahacks.io/hackathon', wait_until='domcontentloaded', timeout=40000)

            # Wait for content
            try: page.wait_for_selector('.hackathon-list, a[href*="/hackathon/"]', timeout=20000)
            except: pass
            
            # Scroll
            for _ in range(3):
                page.evaluate('window.scrollTo(0, document.body.scrollHeight)')
                page.wait_for_timeout(1000)
                
            html = page.content()
            browser.close()
        
        soup = BeautifulSoup(html, 'html.parser')
        seen = set()
        
        # Selectors might be generic or specific classes
        # DoraHacks cards are usually <a> links
        for card in soup.select('a[href*="/hackathon/"]'):
            href = card.get('href', '')
            if not href.startswith('http'): href = 'https://dorahacks.io' + href
            
            if href in seen: continue
            seen.add(href)
            
            # Extract title
            title_el = card.select_one('.font-semibold, h3, h4')
            if not title_el: title_el = card.find('div', class_=lambda c: c and 'title' in c.lower())
            
            title = title_el.get_text(strip=True) if title_el else ""
            if len(title) > 3:
                # Extract participants count from card text
                text = card.get_text(separator=' ', strip=True)
                participants = None
                p_match = re.search(r'(\d+)\s+Participants?', text, re.IGNORECASE)
                if p_match:
                    participants = int(p_match.group(1))
                
                raw = {
                    'title': title,
                    'url': href,
                    'mode': 'online', 
                    'tags': ['Web3'],
                    'participants_count': participants,
                    'team_size_max': None
                }
                db.save_event(normalizer.normalize(raw, 'DoraHacks')); saved += 1
                
    except Exception as e: print(f'  Error: {e}')
    print(f'  ✓ {saved}')
    return saved







def scrape_techgig():
    print('\n💻 TechGig (Browser - Broad)...')
    saved = 0
    try:
        from playwright.sync_api import sync_playwright
        from bs4 import BeautifulSoup
        
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            # Try engage subdomain directly as it seemed to have links in debug
            page.goto('https://engage.techgig.com/hackathons', wait_until='networkidle', timeout=60000)
            
            # Scroll
            for _ in range(3):
                page.evaluate('window.scrollTo(0, document.body.scrollHeight)')
                page.wait_for_timeout(1000)
                
            html = page.content()
            browser.close()
        
        soup = BeautifulSoup(html, 'html.parser')
        seen = set()
        
        # Broadest possible search: All links with 'hackathon' or 'challenge'
        for link in soup.find_all('a', href=True):
            href = link['href']
            
            # Strict-ish filtering to avoid garbage
            if 'void(0)' in href or len(href) < 10: continue
            if 'contact-us' in href or 'about-us' in href or 'login' in href: continue
             
            # accepted patterns
            is_valid = False
            if '/hackathon' in href or '/challenge' in href: is_valid = True
            
            if not is_valid: continue
            
            if href in seen: continue
            seen.add(href)
            
            if not href.startswith('http'): 
                if href.startswith('/'):
                    href = 'https://engage.techgig.com' + href
                else:
                    href = 'https://engage.techgig.com/' + href
            
            # Title extraction - try link text first
            title = link.get_text(strip=True)
            
            # If link text is empty/generic (e.g. "View"), try finding a title sibling/parent
            if not title or len(title) < 5 or title.lower() in ['view', 'participate', 'register']:
                # Inspect parent
                card = link.find_parent('div') 
                if card:
                    h_tag = card.find(['h2', 'h3', 'h4', 'h5'])
                    if h_tag: title = h_tag.get_text(strip=True)

            if not title: continue # Skip if no title found
            
            # Filter mega generic nav items
            if title.lower() in ['hackathons', 'challenges', 'view all', 'explore', 'browse']: continue
            
            if len(title) > 3:
                # Extract participants and text from card
                participants = None
                text = ""
                # Check parent card text
                card = link.find_parent('div')
                if card:
                    text = card.get_text(separator=' ', strip=True)
                    p_match = re.search(r'(\d+)\s+Registered', text, re.IGNORECASE)
                    if p_match: participants = int(p_match.group(1))

                # Extract dates
                start_date = None
                # Debug logging
                if saved < 2: print(f"  [TechGig Debug] Text: {text[:100]}...")
                date_match = re.search(r'([A-Za-z]{3}\s+\d{1,2},\s+\d{4})', text)
                if date_match:
                    try: 
                        from datetime import datetime
                        start_date = datetime.strptime(date_match.group(1), '%b %d, %Y').strftime('%Y-%m-%d')
                    except: pass
                
                # Extract prize
                prize = "Prize TBD"
                prize_match = re.search(r'[₹$]\s?[\d,]+', text)
                if prize_match: prize = prize_match.group(0)

                raw = {
                    'title': title,
                    'url': href, 
                    'start_date': start_date,
                    'mode': 'online',
                    'prize': prize,
                    'participants_count': participants, 
                    'team_size_max': None
                }
                db.save_event(normalizer.normalize(raw, 'TechGig')); saved += 1
                
    except Exception as e: print(f'  Error: {e}')
    print(f'  ✓ {saved}')
    return saved






def scrape_geeksforgeeks():
    print('\n📗 GeeksforGeeks (Browser)...')
    saved = 0
    try:
        from playwright.sync_api import sync_playwright
        from datetime import datetime
        
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            page.goto('https://www.geeksforgeeks.org/events/', wait_until='networkidle', timeout=30000)
            page.wait_for_timeout(3000)
            
            cards = page.query_selector_all('a[href^="/event/"]')
            seen = set()
            for card in cards:
                href = card.get_attribute('href')
                if not href or href in seen: continue
                seen.add(href)
                if not href.startswith('http'): href = 'https://www.geeksforgeeks.org' + href
                
                # Extract text for parsing
                text = card.inner_text().strip()
                lines = [l.strip() for l in text.split('\n') if l.strip()]
                
                title = ""
                start_date = None
                
                if lines:
                    title = max(lines, key=len)
                    
                    for line in lines:
                        if line == title: continue
                        clean_line = line.replace('|', '').strip()
                        # Try parsing "February 24, 2025" format
                        try:
                            # Try standard full date
                            dt = datetime.strptime(clean_line, '%B %d, %Y')
                            start_date = dt.strftime('%Y-%m-%d')
                            break
                        except: pass
                
                # Extract Prize
                prize = "Prize TBD"
                for line in lines:
                    if '₹' in line or '$' in line:
                        import re
                        pm = re.search(r'[₹$]\s?[\d,]+', line)
                        if pm: prize = pm.group(0); break

                if title:
                    raw = {
                        'title': title, 
                        'url': href,
                        'start_date': start_date,
                        'mode': 'online',
                        'prize': prize,
                        'participants_count': None,
                        'team_size_max': None
                    }
                    db.save_event(normalizer.normalize(raw, 'GeeksforGeeks')); saved += 1
            browser.close()
    except Exception as e: print(f'  Error: {e}')
    print(f'  ✓ {saved}')
    return saved





def scrape_hackerearth():
    print('\n🧠 HackerEarth (Browser)...')
    saved = 0
    try:
        from playwright.sync_api import sync_playwright
        from bs4 import BeautifulSoup
        
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            # Use stealthy context options (restored)
            context = browser.new_context(
                user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                viewport={'width': 1366, 'height': 768}
            )
            page = context.new_page()
            page.goto('https://www.hackerearth.com/challenges/', wait_until='networkidle', timeout=60000)
            
            # Scroll to load more
            for _ in range(5):
                page.evaluate('window.scrollTo(0, document.body.scrollHeight)')
                page.wait_for_timeout(1000)
                
            html = page.content()
            browser.close()

            
        soup = BeautifulSoup(html, 'html.parser')
        seen = set()
        
        # Select challenge cards
        # Typically they have class 'challenge-card-modern' or similar
        # We'll use a broad selector for links to event pages
        for card in soup.select('a[href*="/challenges/"], .challenge-card-modern a'):
            href = card.get('href', '')
            if not href: continue
             
            # Clean href
            if not href.startswith('http'): href = 'https://www.hackerearth.com' + href
            
            # Filter
            if '/hackathon/' not in href and '/challenge/' not in href: continue
            if 'hackerearth.com/challenges/' in href and len(href) < 45: continue # likely just the list page
            
            if href in seen: continue
            seen.add(href)
            
            # Extract title
            title = ""
            # Try to find title in common containers within the link or parent
            # If the link itself is the title
            if len(card.get_text(strip=True)) > 5:
                title = card.get_text(strip=True)
            else:
                # Look in parent
                parent = card.find_parent(class_='challenge-card-modern')
                if parent:
                    t_el = parent.select_one('.challenge-list-title')
                    if t_el: title = t_el.get_text(strip=True)
            
            if not title: continue
            
            # Skip generic nav/header text
            if title.lower() in ['hackathons', 'challenges', 'view all', 'explore', 'browse', 'ongoing', 'upcoming']: continue

            # Extract participants
            participants = None
            parent = card.find_parent(class_='challenge-card-modern') or card.find_parent(class_='challenge-card')
            if parent:
                # Extract Text for parsing
                text = parent.get_text(separator=' ', strip=True)
                if saved < 2: print(f"  [HE Debug] Text: {text[:100]}...")
                # pattern: "2000 Registered" or "2000+ Registered"
                p_match = re.search(r'([\d,]+)\+?\s+Registered', text, re.IGNORECASE)
                if p_match:
                    p_str = p_match.group(1).replace(',', '')
                    participants = int(p_str)
            else:
                text = "" # Ensure text is defined even if no parent card is found

            if len(title) > 3:
                # Extract dates
                start_date = None
                date_match = re.search(r'(?:Starts on|STARTS ON)\s*:?\s*([A-Za-z]{3}\s+\d{1,2},\s+\d{2,4})', text, re.IGNORECASE)
                if date_match:
                    try:
                        from datetime import datetime
                        dt_str = date_match.group(1)
                        # Handle 2-digit year
                        if ',' in dt_str and len(dt_str.split(',')[-1].strip()) == 2:
                             dt_str = dt_str.rsplit(' ', 1)[0] + ' 20' + dt_str.split(',')[-1].strip()
                        start_date = datetime.strptime(dt_str, '%b %d, %Y').strftime('%Y-%m-%d')
                    except: pass

                # Extract prize
                prize = "Prize TBD"
                prize_match = re.search(r'[₹$]\s?[\d,]+', text)
                if prize_match: prize = prize_match.group(0)

                raw = {
                    'title': title, 
                    'url': href, 
                    'start_date': start_date,
                    'mode': 'online',
                    'prize': prize,
                    'participants_count': participants,
                    'team_size_max': None
                }
                db.save_event(normalizer.normalize(raw, 'HackerEarth')); saved += 1
                
    except Exception as e: print(f'  Error: {e}')
    print(f'  ✓ {saved}')
    return saved


def scrape_hackquest():
    print('\n🎮 HackQuest (Browser)...')
    saved = 0
    try:
        from playwright.sync_api import sync_playwright
        from bs4 import BeautifulSoup
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            page.goto('https://www.hackquest.io/hackathons', wait_until='networkidle', timeout=60000)
            for _ in range(3): page.evaluate('window.scrollTo(0, document.body.scrollHeight)'); page.wait_for_timeout(1000)
            html = page.content()
            browser.close()
            
        soup = BeautifulSoup(html, 'html.parser')
        seen = set()
        for card in soup.select('a[href^="/hackathons/"]'):
            href = card.get('href', '')
            if not href or href in seen: continue
            seen.add(href)
            if not href.startswith('http'): href = 'https://www.hackquest.io' + href
            
            title = ""
            h2 = card.find('h2')
            if h2: title = h2.get_text(strip=True)
            if title:
                raw = {'title': title, 'url': href, 'mode': 'online',
                       'participants_count': None, 'team_size_max': None}
                db.save_event(normalizer.normalize(raw, 'HackQuest')); saved += 1
    except Exception as e: print(f'  Error: {e}')
    print(f'  ✓ {saved}')
    return saved

def fetch_devfolio_details_api(slug):
    """Fetch hackathon details from Devfolio REST API (fast ~0.5s)."""
    try:
        r = requests.get(
            f'https://api.devfolio.co/api/hackathons/{slug}',
            headers={'Accept': 'application/json'},
            timeout=10
        )
        if r.status_code != 200:
            return None
        
        data = r.json()
        hs = data.get('hackathon_setting', {})
        
        # Registration end date (priority) - from Schedule tab
        reg_end = parse_iso_timestamp(hs.get('reg_ends_at'))
        event_start = parse_iso_timestamp(data.get('starts_at'))
        event_end = parse_iso_timestamp(data.get('ends_at'))
        
        # Mode and location
        is_online = data.get('is_online', True)
        mode = 'online' if is_online else 'in-person'
        city = data.get('city', '')
        country = data.get('country', '')
        location = 'Online' if is_online else f"{city}, {country}".strip(', ') or 'In-Person'
        
        # Get prizes from separate endpoint
        prize = 'Prize TBD'
        try:
            pr = requests.get(
                f'https://api.devfolio.co/api/hackathons/{slug}/prizes',
                headers={'Accept': 'application/json'},
                timeout=10
            )
            if pr.status_code == 200:
                prizes = pr.json()
                if prizes:
                    total = sum(float(p.get('amount', 0)) for p in prizes)
                    if total > 0:
                        currency = prizes[0].get('currency', 'USD')
                        symbol = {'USD': '$', 'INR': '₹', 'EUR': '€', 'GBP': '£'}.get(currency, '$')
                        prize = f"{symbol}{int(total):,}"
        except: pass
        
        return {
            'start_date': event_start,
            'end_date': reg_end or event_end,  # Prefer registration end date
            'team_size_min': data.get('team_min'),
            'team_size_max': data.get('team_size'),
            'mode': mode,
            'location': location,
            'participants_count': data.get('participants_count'),
            'prize': prize,
            'description': (data.get('desc') or '')[:500]
        }
    except Exception as e:
        print(f'    Devfolio API error: {e}')
        return None


def scrape_devdisplay():
    """Scrape DevDisplay hackathons with fast API-based detail fetching."""
    print('\n🖥️ DevDisplay (API-Enhanced)...')
    saved = 0
    try:
        from playwright.sync_api import sync_playwright
        from bs4 import BeautifulSoup
        
        # Step 1: Get listing page (browser required - JS-rendered page)
        print('  Fetching listing page via browser...')
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            page.goto('https://www.devdisplay.org/hackathons', wait_until='networkidle', timeout=60000)
            page.wait_for_timeout(2000)
            html = page.content()
            browser.close()
        
        soup = BeautifulSoup(html, 'html.parser')
        hackathons_to_scrape = []
        seen = set()
        
        # Extract hackathon cards
        for link in soup.find_all('a'):
            if 'apply now' not in link.get_text(strip=True).lower():
                continue
            href = link.get('href')
            if not href or href in seen:
                continue
            seen.add(href)
            
            card = link.find_parent('div')
            if card:
                card = card.find_parent('div')
            if not card:
                continue
            
            # Extract title
            title_el = card.find('h2')
            title = title_el.get_text(strip=True) if title_el else ''
            if not title:
                title = (card.get('id') or '').replace('-', ' ').title()
            
            # Extract date from card text (format: "Sep 20 - 21")
            card_text = card.get_text(separator=' ', strip=True)
            date_match = re.search(r'([A-Z][a-z]{2})\s+(\d{1,2})\s*[-–]\s*(\d{1,2})', card_text)
            start_date = None
            end_date = None
            if date_match:
                month = date_match.group(1)
                day_start = date_match.group(2)
                day_end = date_match.group(3)
                from datetime import datetime
                year = datetime.now().year
                try:
                    start_dt = datetime.strptime(f"{month} {day_start} {year}", "%b %d %Y")
                    end_dt = datetime.strptime(f"{month} {day_end} {year}", "%b %d %Y")
                    if end_dt < datetime.now():
                        year += 1
                        start_dt = datetime.strptime(f"{month} {day_start} {year}", "%b %d %Y")
                        end_dt = datetime.strptime(f"{month} {day_end} {year}", "%b %d %Y")
                    start_date = start_dt.strftime('%Y-%m-%d')
                    end_date = end_dt.strftime('%Y-%m-%d')
                except: pass
            
            # Extract location from card
            location = 'Online'
            mode = 'online'
            if 'India' in card_text or 'Bengaluru' in card_text or 'Mumbai' in card_text or 'Delhi' in card_text:
                loc_match = re.search(r'([A-Za-z]+,?\s*India)', card_text)
                if loc_match:
                    location = loc_match.group(1)
                    mode = 'in-person'
            elif 'Online' in card_text:
                location = 'Online'
                mode = 'online'
            
            # Extract tags
            tags = []
            tag_patterns = ['AI/ML', 'Web3', 'Blockchain', 'Open Innovation', 'Fintech', 'Healthcare', 'EdTech']
            for tag in tag_patterns:
                if tag.lower() in card_text.lower():
                    tags.append(tag)
            
            hackathons_to_scrape.append({
                'title': title,
                'url': href,
                'start_date': start_date,
                'end_date': end_date,
                'location': location,
                'mode': mode,
                'tags': tags
            })
        
        print(f'  Found {len(hackathons_to_scrape)} hackathons, fetching details via API...')
        
        # Step 2: Fetch details via fast API calls
        for i, h in enumerate(hackathons_to_scrape):
            url = h['url']
            print(f'    [{i+1}/{len(hackathons_to_scrape)}] {h["title"][:40]}...')
            
            try:
                if 'devfolio.co' in url:
                    # Extract slug from URL (handle both "slug.devfolio.co" and "devfolio.co/slug")
                    slug = None
                    # Try subdomain match first
                    sub_match = re.search(r'https?://([^.]+)\.devfolio\.co', url)
                    if sub_match and sub_match.group(1) != 'www':
                        slug = sub_match.group(1)
                    else:
                        # Try path match
                        path_match = re.search(r'devfolio\.co/([^/?]+)', url)
                        if path_match:
                            slug = path_match.group(1)
                            
                    if slug:
                        # Enforce canonical URL to prevent duplicates (e.g. devfolio.co/slug -> slug.devfolio.co)
                        h['url'] = f"https://{slug}.devfolio.co/"
                        
                        details = fetch_devfolio_details_api(slug)
                        if details:
                            # Merge details (API data takes priority)
                            if details.get('start_date'): h['start_date'] = details['start_date']
                            if details.get('end_date'): h['end_date'] = details['end_date']
                            if details.get('prize'): h['prize'] = details['prize']
                            if details.get('team_size_min'): h['team_size_min'] = details['team_size_min']
                            if details.get('team_size_max'): h['team_size_max'] = details['team_size_max']
                            if details.get('mode'): h['mode'] = details['mode']
                            if details.get('location'): h['location'] = details['location']
                            if details.get('participants_count'): h['participants_count'] = details['participants_count']
                        
                elif 'unstop.com' in url:
                    # Extract event ID from end of URL (e.g., "...-154300")
                    match = re.search(r'-(\d+)$', url)
                    if match:
                        details = fetch_unstop_details_api(match.group(1))
                        if details:
                            if details.get('end_date'): h['end_date'] = parse_iso_timestamp(details['end_date'])
                            if details.get('team_size_min'): h['team_size_min'] = details['team_size_min']
                            if details.get('team_size_max'): h['team_size_max'] = details['team_size_max']
                            if details.get('registerCount'): h['participants_count'] = details['registerCount']
                            # Mode and location from region
                            region = details.get('region', '')
                            if region and region.lower() == 'online':
                                h['mode'] = 'online'
                                h['location'] = 'Online'
                            elif region and region.lower() == 'offline':
                                h['mode'] = 'in-person'
                                city = details.get('city', '')
                                state = details.get('state', '')
                                h['location'] = f"{city}, {state}".strip(', ') or 'In-Person'
            except Exception as e:
                print(f'      Error: {e}')
            
            # Save event
            raw = {
                'title': h['title'],
                'url': h['url'],
                'start_date': h.get('start_date'),
                'end_date': h.get('end_date'),
                'location': h.get('location', 'Online'),
                'mode': h.get('mode', 'online'),
                'prize': h.get('prize', 'Prize TBD'),
                'team_size_min': h.get('team_size_min'),
                'team_size_max': h.get('team_size_max'),
                'participants_count': h.get('participants_count'),
                'tags': h.get('tags', []),
                'description': h.get('description', '')
            }
            db.save_event(normalizer.normalize(raw, 'DevDisplay'))
            saved += 1
            
    except Exception as e:
        print(f'  Error: {e}')
        import traceback
        traceback.print_exc()
    
    print(f'  ✓ {saved}')
    return saved

def scrape_mycareernet():
    print('\n💼 MyCareerNet (Browser)...')
    saved = 0
    try:
        from playwright.sync_api import sync_playwright
        from bs4 import BeautifulSoup
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            page.goto('https://mycareernet.in/mycareernet/contests', wait_until='networkidle', timeout=60000)
            page.wait_for_timeout(3000)
            html = page.content()
            browser.close()
            
        soup = BeautifulSoup(html, 'html.parser')
        seen = set()
        for card in soup.select('.hackathonCard'):
            link = card.find('a', href=True)
            if not link: continue
            href = link['href']
            if not href or href in seen: continue
            seen.add(href)
            if href.startswith('/'): href = 'https://mycareernet.in' + href
            
            title = card.get_text().split('\n')[0][:100] # Simplification
            if title:
                raw = {'title': title, 'url': href, 'mode': 'online',
                       'participants_count': None, 'team_size_max': None}
                db.save_event(normalizer.normalize(raw, 'MyCareerNet')); saved += 1
    except Exception as e: print(f'  Error: {e}')
    print(f'  ✓ {saved}')
    return saved


def scrape_kaggle():
    print('\n📊 Kaggle (Browser)...')
    saved = 0
    try:
        from playwright.sync_api import sync_playwright
        from bs4 import BeautifulSoup
        import re
        
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            page.goto('https://www.kaggle.com/competitions', wait_until='networkidle', timeout=60000)
            
            # Scroll to load more
            for _ in range(5):
                page.evaluate('window.scrollTo(0, document.body.scrollHeight)')
                page.wait_for_timeout(1000)
                
            html = page.content()
            browser.close()
            

        soup = BeautifulSoup(html, 'html.parser')
        seen = set()
        print(f"  Debug: Soup has {len(soup.find_all('a'))} links")
        
        # Select competition links
        for link in soup.find_all('a', href=True):
            href = link['href']
            

            # Filter
            if '/competitions/' not in href and '/c/' not in href: 
                # print(f"  Skipped (pattern): {href}")
                continue
            # if href.count('/') < 2: continue # e.g. /competitions
            if 'about' in href or 'documentation' in href: continue
            
            # Debug match
            print(f"  Checking {href}")
             
            # Clean href
            if not href.startswith('http'): href = 'https://www.kaggle.com' + href
            
            if href in seen: continue
            seen.add(href)
            

            # Extract info from parent container
            # Traverse parents to find a substantial container (div/li)
            container = link.parent
            found = False
            for _ in range(3): # Go up 3 levels max
                if not container: break
                if container.name in ['div', 'li'] and len(container.get_text(strip=True)) > 50:
                    found = True
                    break
                container = container.parent
            
            if not found or not container:
                # print(f"  Debug: Link match {href} but no valid container found")
                continue
            
            # Start parsing text
            text = container.get_text(separator=' ', strip=True)
            
            # Extract Title (Clean split to avoid concatenation like "TitlePrize")
            full_text = link.get_text(separator='|', strip=True)
            parts = [p.strip() for p in full_text.split('|') if p.strip()]
            title = parts[0] if parts else "Unknown Kaggle Event"
            
            # Remove "Featured" if it appears
            if title.lower() == 'featured' and len(parts) > 1:
                title = parts[1]
                # If still no title, try container header
                if not title:
                     h = container.find(['h2', 'h3'], class_=not None) # simple check
                     if h: title = h.get_text(strip=True)
            
            if not title: 
                # print(f"  Debug: No title for {href}")
                continue
            
            # Debug successful match
            # print(f"  Debug Matches: {title[:20]}...")
            
            # Prize
            prize = "Prize TBD"
            prize_match = re.search(r'\$[\d,]+', text)
            if prize_match:
                prize = prize_match.group(0)
            
            # Teams
            participants = None
            tm_match = re.search(r'([\d,]+)\s+Teams?', text, re.IGNORECASE)
            if tm_match:
                p_str = tm_match.group(1).replace(',', '')
                participants = int(p_str)

            if len(title) > 3:


                raw = {
                    'title': title, 
                    'url': href, 
                    'mode': 'online',
                    'prize': prize,
                    'participants_count': participants,
                    'team_size_max': 5
                }
                db.save_event(normalizer.normalize(raw, 'Kaggle')); saved += 1
                
    except Exception as e: print(f'  Error: {e}')
    print(f'  ✓ {saved}')
    return saved


def main():
    print('='*50)
    print('  HackFind - CONSOLIDATED Scraper')
    print('='*50)
    
    scrapers = [
        scrape_devpost, scrape_devfolio, scrape_unstop,
        scrape_mlh, scrape_superteam,
        scrape_dorahacks, 
        scrape_hackerearth, scrape_hackquest, scrape_devdisplay, scrape_mycareernet,
        scrape_kaggle
    ]
    
    total = 0
    for s in scrapers:
        try: total += s()

        except Exception as e: print(f"  Error running scraper: {e}")
        time.sleep(0.5)
        
    print('\n' + '='*50)
    print(f'  Total this run: {total}')
    print(f'  Database total: {db.get_statistics()["total_events"]} hackathons')
    print('='*50)

if __name__ == '__main__':
    main()
