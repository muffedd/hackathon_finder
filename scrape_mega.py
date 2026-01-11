"""
MEGA Scraper - 1000 each from Devfolio and Unstop
"""
import requests
import sys
import time
sys.path.insert(0, '.')

from database.db_manager import DatabaseManager
from utils.data_normalizer import DataNormalizer

headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0', 'Accept': 'application/json'}
db = DatabaseManager('hackathons.db')
normalizer = DataNormalizer()

def scrape_devfolio_mega():
    """Scrape 1000+ from Devfolio"""
    print('\n🎯 MEGA Devfolio Scrape (targeting 1000)...')
    saved = 0
    
    # Devfolio has different listing types
    types = ['all', 'application_open', 'past', 'upcoming']
    
    for list_type in types:
        print(f'\n  Type: {list_type}')
        for offset in range(0, 300, 100):  # 300 per type = 1200 total
            try:
                payload = {"type": list_type, "from": offset, "size": 100}
                r = requests.post('https://api.devfolio.co/api/search/hackathons', 
                    json=payload, headers=headers, timeout=30)
                
                if r.status_code != 200:
                    print(f'    Status {r.status_code}, stopping')
                    break
                    
                hits = r.json().get('hits', {}).get('hits', [])
                if not hits:
                    print(f'    No more results')
                    break
                    
                batch_saved = 0
                for h in hits:
                    try:
                        src = h.get('_source', {})
                        raw = {
                            'title': src.get('name'),
                            'url': f"https://devfolio.co/{src.get('slug')}" if src.get('slug') else None,
                            'start_date': src.get('starts_at'),
                            'end_date': src.get('ends_at'),
                            'location': src.get('location') or ('Online' if src.get('is_online_event') else ''),
                            'prize': src.get('prize_amount'),
                            'description': src.get('tagline'),
                            'mode': 'online' if src.get('is_online_event') else 'in-person',
                            'tags': src.get('themes', [])
                        }
                        if raw['title'] and raw['url']:
                            db.save_event(normalizer.normalize(raw, 'Devfolio'))
                            saved += 1
                            batch_saved += 1
                    except: pass
                print(f'    Offset {offset}: +{batch_saved} (total: {saved})')
                time.sleep(0.5)
            except Exception as e:
                print(f'    Error at offset {offset}: {e}')
                break
        
        if saved >= 1000:
            break
    
    return saved

def scrape_unstop_mega():
    """Scrape 1000+ from Unstop"""
    print('\n🎪 MEGA Unstop Scrape (targeting 1000)...')
    saved = 0
    
    # Unstop has different opportunity types
    types = ['hackathons', 'competitions', 'quizzes', 'ideathon']
    
    for opp_type in types:
        print(f'\n  Type: {opp_type}')
        for page in range(1, 15):  # 15 pages x 100 = 1500 per type
            try:
                url = f'https://unstop.com/api/public/opportunity/search-result?opportunity={opp_type}&per_page=100&page={page}'
                r = requests.get(url, headers=headers, timeout=30)
                
                if r.status_code != 200:
                    print(f'    Status {r.status_code}, stopping')
                    break
                
                data = r.json().get('data', {})
                items = data.get('data', [])
                
                if not items:
                    print(f'    No more results')
                    break
                
                batch_saved = 0
                for h in items:
                    try:
                        raw = {
                            'title': h.get('title'),
                            'url': f"https://unstop.com/{h.get('public_url')}" if h.get('public_url') else None,
                            'start_date': h.get('start_date'),
                            'end_date': h.get('end_date'),
                            'location': h.get('city') if h.get('city') else 'Online',
                            'prize': h.get('prize_money') or h.get('prizes'),
                            'description': h.get('seo_details', {}).get('meta_description') if isinstance(h.get('seo_details'), dict) else None,
                            'mode': 'online' if not h.get('city') else 'in-person',
                            'tags': [opp_type]
                        }
                        if raw['title'] and raw['url']:
                            db.save_event(normalizer.normalize(raw, 'Unstop'))
                            saved += 1
                            batch_saved += 1
                    except: pass
                print(f'    Page {page}: +{batch_saved} (total: {saved})')
                time.sleep(0.3)
            except Exception as e:
                print(f'    Error on page {page}: {e}')
                break
        
        if saved >= 1000:
            break
    
    return saved

def main():
    print('='*60)
    print('  HackFind - MEGA SCRAPE (1000 Devfolio + 1000 Unstop)')
    print('='*60)
    
    stats_before = db.get_statistics()
    print(f'\n  Starting with: {stats_before["total_events"]} hackathons')
    
    devfolio = scrape_devfolio_mega()
    unstop = scrape_unstop_mega()
    
    stats_after = db.get_statistics()
    
    print('\n' + '='*60)
    print(f'  Devfolio scraped: {devfolio}')
    print(f'  Unstop scraped: {unstop}')
    print(f'  Total this run: {devfolio + unstop}')
    print(f'  DATABASE TOTAL: {stats_after["total_events"]} hackathons')
    print('='*60)

if __name__ == '__main__':
    main()
