"""Deep Scrape - Get 1000+ hackathons"""
import requests
import sys
import time
sys.path.insert(0, '.')

from database.db_manager import DatabaseManager
from utils.data_normalizer import DataNormalizer

headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0', 'Accept': 'application/json'}
db = DatabaseManager('hackathons.db')
normalizer = DataNormalizer()

def scrape_devpost_deep():
    """Scrape ALL Devpost pages"""
    print('\n📦 Deep scraping Devpost (20 pages)...')
    saved = 0
    for page in range(1, 21):  # 20 pages x 50 = 1000
        try:
            r = requests.get(f'https://devpost.com/api/hackathons?page={page}&per_page=50', headers=headers, timeout=30)
            hackathons = r.json().get('hackathons', [])
            if not hackathons:
                print(f'  Page {page}: No more data')
                break
            for h in hackathons:
                try:
                    raw = {
                        'title': h.get('title'),
                        'url': h.get('url'),
                        'start_date': h.get('submission_period_dates'),
                        'location': 'Online' if h.get('online_only') else h.get('displayed_location', ''),
                        'prize': h.get('prize_amount'),
                        'description': h.get('tagline'),
                        'mode': 'online' if h.get('online_only') else 'in-person',
                        'tags': h.get('themes', [])
                    }
                    if raw['title']:
                        db.save_event(normalizer.normalize(raw, 'Devpost'))
                        saved += 1
                except: pass
            print(f'  Page {page}: +{len(hackathons)} (total: {saved})')
            time.sleep(0.3)  # Be nice to the API
        except Exception as e:
            print(f'  Page {page} error: {e}')
            break
    return saved

def scrape_unstop_deep():
    """Scrape more Unstop pages"""
    print('\n🎪 Deep scraping Unstop (10 pages)...')
    saved = 0
    for page in range(1, 11):  # 10 pages
        try:
            r = requests.get(f'https://unstop.com/api/public/opportunity/search-result?opportunity=hackathons&per_page=100&page={page}', headers=headers, timeout=30)
            items = r.json().get('data', {}).get('data', [])
            if not items:
                print(f'  Page {page}: No more data')
                break
            for h in items:
                try:
                    raw = {
                        'title': h.get('title'),
                        'url': f"https://unstop.com/{h.get('public_url')}" if h.get('public_url') else None,
                        'start_date': h.get('start_date'),
                        'end_date': h.get('end_date'),
                        'prize': h.get('prizes'),
                        'mode': 'online'
                    }
                    if raw['title'] and raw['url']:
                        db.save_event(normalizer.normalize(raw, 'Unstop'))
                        saved += 1
                except: pass
            print(f'  Page {page}: +{len(items)} (total: {saved})')
            time.sleep(0.3)
        except Exception as e:
            print(f'  Page {page} error: {e}')
            break
    return saved

def scrape_devfolio_deep():
    """Scrape more Devfolio"""
    print('\n🎯 Deep scraping Devfolio (500 results)...')
    saved = 0
    for offset in range(0, 500, 100):
        try:
            r = requests.post('https://api.devfolio.co/api/search/hackathons', 
                json={"type": "all", "from": offset, "size": 100}, headers=headers, timeout=30)
            hits = r.json().get('hits', {}).get('hits', [])
            if not hits:
                break
            for h in hits:
                try:
                    src = h.get('_source', {})
                    raw = {
                        'title': src.get('name'),
                        'url': f"https://devfolio.co/{src.get('slug')}" if src.get('slug') else None,
                        'start_date': src.get('starts_at'),
                        'end_date': src.get('ends_at'),
                        'location': src.get('location'),
                        'prize': src.get('prize_amount'),
                        'mode': 'online' if src.get('is_online_event') else 'in-person'
                    }
                    if raw['title'] and raw['url']:
                        db.save_event(normalizer.normalize(raw, 'Devfolio'))
                        saved += 1
                except: pass
            print(f'  Offset {offset}: +{len(hits)} (total: {saved})')
            time.sleep(0.3)
        except Exception as e:
            print(f'  Offset {offset} error: {e}')
            break
    return saved

def main():
    print('='*50)
    print('  HackFind - DEEP SCRAPE (1000+ target)')
    print('='*50)
    
    total = 0
    total += scrape_devpost_deep()
    total += scrape_unstop_deep()
    total += scrape_devfolio_deep()
    
    print('\n' + '='*50)
    print(f'  This run: {total}')
    stats = db.get_statistics()
    print(f'  DATABASE TOTAL: {stats["total_events"]} hackathons')
    print('='*50)

if __name__ == '__main__':
    main()
