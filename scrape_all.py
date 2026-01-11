"""
Multi-Site Hackathon Scraper - ALL SITES
===========================================
"""
import json
import requests
import sys
import time
from urllib.parse import urljoin
sys.path.insert(0, '.')

from database.db_manager import DatabaseManager
from utils.data_normalizer import DataNormalizer

headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0', 'Accept': 'application/json, text/html, */*'}
db = DatabaseManager('hackathons.db')
normalizer = DataNormalizer()

def safe_get(url, timeout=30):
    try:
        return requests.get(url, headers=headers, timeout=timeout)
    except:
        return None

def _extract_jsonld_events(data, base_url):
    items = []
    if isinstance(data, list):
        items = data
    elif isinstance(data, dict):
        if isinstance(data.get('@graph'), list):
            items = data['@graph']
        else:
            items = [data]

    events = []
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

        event = {
            'title': title,
            'url': url,
            'start_date': start_date,
            'end_date': end_date,
            'location': location,
            'description': description,
            'image': image,
        }
        if event['title'] and event['url']:
            events.append(event)

    return events

def scrape_devpost():
    print('\n📦 Devpost...')
    saved = 0
    for page in range(1, 6):
        try:
            r = safe_get(f'https://devpost.com/api/hackathons?page={page}&per_page=50')
            if not r: break
            for h in r.json().get('hackathons', []):
                try:
                    raw = {'title': h.get('title'), 'url': h.get('url'), 'start_date': h.get('submission_period_dates'),
                           'location': 'Online' if h.get('online_only') else h.get('displayed_location', ''),
                           'prize': h.get('prize_amount'), 'description': h.get('tagline'),
                           'mode': 'online' if h.get('online_only') else 'in-person'}
                    if raw['title']: db.save_event(normalizer.normalize(raw, 'Devpost')); saved += 1
                except: pass
        except: break
    print(f'  ✓ {saved}')
    return saved

def scrape_devfolio():
    print('\n🎯 Devfolio...')
    saved = 0
    try:
        r = requests.post('https://api.devfolio.co/api/search/hackathons', json={"type": "application_open", "from": 0, "size": 100}, headers=headers, timeout=30)
        for h in r.json().get('hits', {}).get('hits', []):
            try:
                src = h.get('_source', {})
                raw = {'title': src.get('name'), 'url': f"https://devfolio.co/{src.get('slug')}" if src.get('slug') else None,
                       'start_date': src.get('starts_at'), 'end_date': src.get('ends_at'), 'location': src.get('location'),
                       'prize': src.get('prize_amount'), 'mode': 'online' if src.get('is_online_event') else 'in-person'}
                if raw['title'] and raw['url']: db.save_event(normalizer.normalize(raw, 'Devfolio')); saved += 1
            except: pass
    except: pass
    print(f'  ✓ {saved}')
    return saved



def scrape_hackculture():
    print('\nHackCulture...')
    saved = 0
    try:
        r = safe_get('https://hackculture.io/')
        if r:
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(r.text, 'html.parser')
            events = []
            for script in soup.find_all('script', type='application/ld+json'):
                raw = script.string or script.get_text()
                if not raw:
                    continue
                try:
                    data = json.loads(raw)
                except Exception:
                    continue
                events.extend(_extract_jsonld_events(data, 'https://hackculture.io/'))

            if not events:
                for card in soup.select('article, .event-card, .hackathon-card, .card, .listing'):
                    title_el = card.select_one('h1, h2, h3, .title, .event-title, .hackathon-title')
                    link_el = card.select_one('a[href]')
                    if title_el and link_el:
                        href = link_el.get('href', '')
                        url = urljoin('https://hackculture.io/', href) if href else None
                        raw_event = {
                            'title': title_el.get_text(strip=True),
                            'url': url,
                        }
                        events.append(raw_event)

            for raw in events:
                if raw.get('title') and raw.get('url'):
                    db.save_event(normalizer.normalize(raw, 'HackCulture'))
                    saved += 1
    except Exception:
        pass
    print(f'  {saved}')
    return saved


def scrape_unstop():
    print('\n🎪 Unstop...')
    saved = 0
    try:
        r = safe_get('https://unstop.com/api/public/opportunity/search-result?opportunity=hackathons&per_page=100')
        for h in r.json().get('data', {}).get('data', []):
            try:
                raw = {'title': h.get('title'), 'url': f"https://unstop.com/{h.get('public_url')}" if h.get('public_url') else None,
                       'start_date': h.get('start_date'), 'end_date': h.get('end_date'), 'mode': 'online'}
                if raw['title'] and raw['url']: db.save_event(normalizer.normalize(raw, 'Unstop')); saved += 1
            except: pass
    except: pass
    print(f'  ✓ {saved}')
    return saved

def scrape_hackerearth():
    print('\n🌍 HackerEarth...')
    saved = 0
    try:
        r = safe_get('https://www.hackerearth.com/challenges/hackathon/')
        if r:
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(r.text, 'html.parser')
            for card in soup.select('.challenge-card-modern, .challenge-card, .event-card, [class*="challenge"]')[:50]:
                try:
                    link = card.select_one('a[href]')
                    title = card.select_one('.challenge-name, .title, h3, h4')
                    if title and link:
                        href = link.get('href', '')
                        if not href.startswith('http'): href = 'https://www.hackerearth.com' + href
                        raw = {'title': title.get_text(strip=True), 'url': href, 'mode': 'online'}
                        db.save_event(normalizer.normalize(raw, 'HackerEarth')); saved += 1
                except: pass
    except: pass
    print(f'  ✓ {saved}')
    return saved

def scrape_geeksforgeeks():
    print('\n📗 GeeksforGeeks...')
    saved = 0
    try:
        r = safe_get('https://practice.geeksforgeeks.org/api/v1/events/?type=contest')
        if r:
            for h in r.json().get('results', []):
                try:
                    raw = {'title': h.get('name'), 'url': h.get('url') or f"https://practice.geeksforgeeks.org/contest/{h.get('slug')}",
                           'start_date': h.get('start_time'), 'end_date': h.get('end_time'), 'mode': 'online'}
                    if raw['title']: db.save_event(normalizer.normalize(raw, 'GeeksforGeeks')); saved += 1
                except: pass
    except: pass
    print(f'  ✓ {saved}')
    return saved

def scrape_kaggle():
    print('\n📊 Kaggle...')
    saved = 0
    try:
        r = safe_get('https://www.kaggle.com/competitions.json')
        if r:
            for h in r.json()[:50]:
                try:
                    raw = {'title': h.get('competitionTitle') or h.get('title'), 
                           'url': f"https://www.kaggle.com/competitions/{h.get('competitionSlug') or h.get('slug')}",
                           'prize': h.get('reward'), 'mode': 'online', 'tags': ['Data Science', 'ML']}
                    if raw['title']: db.save_event(normalizer.normalize(raw, 'Kaggle')); saved += 1
                except: pass
    except: pass
    print(f'  ✓ {saved}')
    return saved

def scrape_mlh():
    print('\n🏆 MLH...')
    saved = 0
    try:
        from bs4 import BeautifulSoup
        for year in ['2025', '2026']:
            r = safe_get(f'https://mlh.io/seasons/{year}/events')
            if r:
                soup = BeautifulSoup(r.text, 'html.parser')
                for card in soup.select('.event, .event-card, [class*="event"]')[:30]:
                    try:
                        link = card.select_one('a[href*="mlh"]')
                        title = card.select_one('.event-name, .title, h3')
                        if title:
                            href = link.get('href', '') if link else ''
                            if not href.startswith('http'): href = 'https://mlh.io' + href
                            raw = {'title': title.get_text(strip=True), 'url': href or 'https://mlh.io', 'mode': 'in-person'}
                            db.save_event(normalizer.normalize(raw, 'MLH')); saved += 1
                    except: pass
    except: pass
    print(f'  ✓ {saved}')
    return saved


def scrape_dorahacks():
    print('\n🚀 DoraHacks...')
    saved = 0
    try:
        r = safe_get('https://dorahacks.io/api/hackathon/search?page=1&limit=50')
        if r and r.status_code == 200:
            data = r.json()
            items = data.get('data', {}).get('list', []) if isinstance(data.get('data'), dict) else data.get('data', [])
            for h in items:
                try:
                    raw = {'title': h.get('name') or h.get('title'), 'url': f"https://dorahacks.io/hackathon/{h.get('hackerlink_id') or h.get('id')}",
                           'prize': h.get('total_prize'), 'mode': 'online', 'tags': ['Web3']}
                    if raw['title']: db.save_event(normalizer.normalize(raw, 'DoraHacks')); saved += 1
                except: pass
    except: pass
    print(f'  ✓ {saved}')
    return saved

def scrape_superteam():
    print('\n☀️ Superteam...')
    saved = 0
    try:
        r = safe_get('https://earn.superteam.fun/api/listings/?type=hackathon')
        if r:
            for h in r.json()[:50]:
                try:
                    raw = {'title': h.get('title'), 'url': f"https://earn.superteam.fun/listings/{h.get('slug')}" if h.get('slug') else h.get('link'),
                           'prize': h.get('rewardAmount'), 'mode': 'online', 'tags': ['Solana', 'Web3']}
                    if raw['title']: db.save_event(normalizer.normalize(raw, 'Superteam')); saved += 1
                except: pass
    except: pass
    print(f'  ✓ {saved}')
    return saved

def scrape_techgig():
    print('\n💻 TechGig...')
    saved = 0
    try:
        from bs4 import BeautifulSoup
        r = safe_get('https://www.techgig.com/hackathon')
        if r:
            soup = BeautifulSoup(r.text, 'html.parser')
            for card in soup.select('.challenge-box, .hackathon-card, [class*="challenge"]')[:30]:
                try:
                    link = card.select_one('a[href]')
                    title = card.select_one('.title, h3, h4')
                    if title and link:
                        href = link.get('href', '')
                        if not href.startswith('http'): href = 'https://www.techgig.com' + href
                        raw = {'title': title.get_text(strip=True), 'url': href, 'mode': 'online'}
                        db.save_event(normalizer.normalize(raw, 'TechGig')); saved += 1
                except: pass
    except: pass
    print(f'  ✓ {saved}')
    return saved

def scrape_mycareernet():
    print('\n🇰🇷 MyCareerNet...')
    saved = 0
    try:
        from bs4 import BeautifulSoup
        r = safe_get('https://www.mycareernet.co.kr/competitions')
        if r:
            soup = BeautifulSoup(r.text, 'html.parser')
            for card in soup.select('.competition-card, [class*="card"]')[:30]:
                try:
                    link = card.select_one('a[href]')
                    title = card.select_one('.title, h3, h4')
                    if title:
                        raw = {'title': title.get_text(strip=True), 'url': link.get('href') if link else 'https://www.mycareernet.co.kr', 'mode': 'online'}
                        db.save_event(normalizer.normalize(raw, 'MyCareerNet')); saved += 1
                except: pass
    except: pass
    print(f'  ✓ {saved}')
    return saved

def scrape_hackquest():
    print('\n🎮 HackQuest...')
    saved = 0
    try:
        r = safe_get('https://www.hackquest.io/api/hackathon/list?page=1&limit=50')
        if r:
            items = r.json().get('data', []) if isinstance(r.json().get('data'), list) else []
            for h in items:
                try:
                    raw = {'title': h.get('name'), 'url': f"https://www.hackquest.io/hackathon/{h.get('id')}", 'mode': 'online'}
                    if raw['title']: db.save_event(normalizer.normalize(raw, 'HackQuest')); saved += 1
                except: pass
    except: pass
    print(f'  ✓ {saved}')
    return saved

def scrape_devdisplay():
    print('\n🖥️ DevDisplay...')
    saved = 0
    try:
        from bs4 import BeautifulSoup
        r = safe_get('https://www.devdisplay.org/hackathons')
        if r:
            soup = BeautifulSoup(r.text, 'html.parser')
            for card in soup.select('[class*="card"], [class*="hackathon"]')[:30]:
                try:
                    link = card.select_one('a[href]')
                    title = card.select_one('h2, h3, h4, .title')
                    if title:
                        raw = {'title': title.get_text(strip=True), 'url': link.get('href') if link else 'https://www.devdisplay.org', 'mode': 'online'}
                        db.save_event(normalizer.normalize(raw, 'DevDisplay')); saved += 1
                except: pass
    except: pass
    print(f'  ✓ {saved}')
    return saved

def scrape_contra():
    print('\n🎨 Contra...')
    saved = 0
    try:
        r = safe_get('https://contra.com/api/hackathons')
        if r:
            for h in r.json()[:30]:
                try:
                    raw = {'title': h.get('title') or h.get('name'), 'url': h.get('url') or 'https://contra.com', 'mode': 'online'}
                    if raw['title']: db.save_event(normalizer.normalize(raw, 'Contra')); saved += 1
                except: pass
    except: pass
    print(f'  ✓ {saved}')
    return saved

def main():
    print('='*50)
    print('  HackFind - ALL SITES Scraper')
    print('='*50)
    
    scrapers = [
        scrape_devpost, scrape_devfolio, scrape_hackculture, scrape_unstop,
        scrape_hackerearth, scrape_geeksforgeeks, scrape_kaggle, scrape_mlh,
        scrape_dorahacks, scrape_superteam, scrape_techgig, scrape_mycareernet,
        scrape_hackquest, scrape_devdisplay, scrape_contra
    ]
    
    total = 0
    for scraper in scrapers:
        try:
            total += scraper()
        except Exception as e:
            print(f'  Error: {e}')
        time.sleep(0.5)
    
    print('\n' + '='*50)
    print(f'  Total this run: {total}')
    stats = db.get_statistics()
    print(f'  Database total: {stats["total_events"]} hackathons')
    print('='*50)

if __name__ == '__main__':
    main()
