"""
Deep scraper for HackerEarth, HackCulture, and Superteam
"""
import requests
import sys
import time
sys.path.insert(0, '.')

from database.db_manager import DatabaseManager
from utils.data_normalizer import DataNormalizer
from bs4 import BeautifulSoup

headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0', 'Accept': 'text/html,application/json'}
db = DatabaseManager('hackathons.db')
normalizer = DataNormalizer()

def scrape_hackerearth():
    """Scrape HackerEarth challenges - multiple pages and types"""
    print('\n🌍 Deep scraping HackerEarth...')
    saved = 0
    
    # Different challenge types
    types = ['hackathon', 'hiring', 'competitive']
    
    for ctype in types:
        print(f'  Type: {ctype}')
        for page in range(1, 6):  # 5 pages each
            try:
                url = f'https://www.hackerearth.com/challenges/{ctype}/?page={page}'
                r = requests.get(url, headers=headers, timeout=30)
                
                if r.status_code != 200:
                    break
                    
                soup = BeautifulSoup(r.text, 'html.parser')
                
                # Try multiple selectors
                cards = soup.select('.challenge-card-modern, .challenge-card, .upcoming .card, .ongoing .card, [class*="challenge"]')
                
                if not cards:
                    # Fallback: find any cards with links
                    cards = soup.select('a[href*="/challenges/"]')
                    
                print(f'    Page {page}: {len(cards)} cards')
                
                if not cards:
                    break
                    
                for card in cards:
                    try:
                        # Get title
                        title_el = card.select_one('.challenge-name, .challenge-title, h3, h4, .title')
                        if title_el:
                            title = title_el.get_text(strip=True)
                        elif card.name == 'a':
                            title = card.get_text(strip=True)
                        else:
                            continue
                        
                        # Get URL
                        if card.name == 'a':
                            href = card.get('href', '')
                        else:
                            link = card.select_one('a[href]')
                            href = link.get('href', '') if link else ''
                        
                        if not href.startswith('http'):
                            href = 'https://www.hackerearth.com' + href
                        
                        # Get other info
                        date_el = card.select_one('.challenge-date, .date, time, .timing')
                        prize_el = card.select_one('.prize-money, .prize, .challenge-prize')
                        
                        raw = {
                            'title': title,
                            'url': href,
                            'start_date': date_el.get_text(strip=True) if date_el else None,
                            'prize': prize_el.get_text(strip=True) if prize_el else None,
                            'mode': 'online',
                            'tags': [ctype]
                        }
                        
                        if raw['title'] and raw['url'] and len(raw['title']) > 3:
                            db.save_event(normalizer.normalize(raw, 'HackerEarth'))
                            saved += 1
                    except:
                        pass
                
                time.sleep(0.5)
            except Exception as e:
                print(f'    Error: {e}')
                break
    
    print(f'  ✓ Saved {saved} HackerEarth events')
    return saved

def scrape_hackculture():
    """Scrape HackCulture"""
    print('\n🎨 Deep scraping HackCulture...')
    saved = 0
    
    try:
        r = requests.get('https://hackculture.io/', headers=headers, timeout=30)
        soup = BeautifulSoup(r.text, 'html.parser')
        
        # Try to find events
        cards = soup.select('article, .event-card, .hackathon-card, .card, [class*="event"], [class*="hack"]')
        print(f'  Found {len(cards)} potential cards')
        
        for card in cards:
            try:
                title_el = card.select_one('h1, h2, h3, h4, .title, .name')
                link = card.select_one('a[href]') or card.find_parent('a')
                
                if not title_el:
                    continue
                    
                title = title_el.get_text(strip=True)
                href = link.get('href', '') if link else ''
                
                if not href.startswith('http'):
                    href = 'https://hackculture.io' + href
                
                if title and len(title) > 3:
                    raw = {
                        'title': title,
                        'url': href or 'https://hackculture.io',
                        'mode': 'online'
                    }
                    db.save_event(normalizer.normalize(raw, 'HackCulture'))
                    saved += 1
            except:
                pass
                
        # Also check for JSON-LD
        scripts = soup.find_all('script', type='application/ld+json')
        for script in scripts:
            try:
                import json
                data = json.loads(script.string or script.get_text())
                if isinstance(data, list):
                    items = data
                elif isinstance(data, dict):
                    items = data.get('@graph', [data])
                else:
                    items = []
                    
                for item in items:
                    if isinstance(item, dict) and item.get('@type', '').lower() == 'event':
                        raw = {
                            'title': item.get('name'),
                            'url': item.get('url'),
                            'start_date': item.get('startDate'),
                            'location': item.get('location', {}).get('name') if isinstance(item.get('location'), dict) else str(item.get('location', '')),
                            'mode': 'online'
                        }
                        if raw['title'] and raw['url']:
                            db.save_event(normalizer.normalize(raw, 'HackCulture'))
                            saved += 1
            except:
                pass
                
    except Exception as e:
        print(f'  Error: {e}')
    
    print(f'  ✓ Saved {saved} HackCulture events')
    return saved

def scrape_superteam():
    """Deep scrape Superteam Earn - bounties and hackathons"""
    print('\n☀️ Deep scraping Superteam...')
    saved = 0
    
    # Try the API first
    try:
        # Listings API
        for listing_type in ['hackathon', 'bounty', 'grant', 'project']:
            url = f'https://earn.superteam.fun/api/listings/?type={listing_type}&take=100'
            r = requests.get(url, headers=headers, timeout=30)
            
            if r.status_code == 200:
                data = r.json()
                items = data if isinstance(data, list) else data.get('data', []) if isinstance(data, dict) else []
                print(f'  Type {listing_type}: {len(items)} items')
                
                for h in items:
                    try:
                        raw = {
                            'title': h.get('title') or h.get('name'),
                            'url': f"https://earn.superteam.fun/listings/{h.get('slug')}" if h.get('slug') else h.get('link'),
                            'prize': h.get('rewardAmount') or h.get('reward'),
                            'description': h.get('description'),
                            'mode': 'online',
                            'tags': ['Solana', 'Web3', listing_type]
                        }
                        if raw['title'] and raw['url']:
                            db.save_event(normalizer.normalize(raw, 'Superteam'))
                            saved += 1
                    except:
                        pass
            
            time.sleep(0.3)
            
    except Exception as e:
        print(f'  API error: {e}')
    
    # Fallback: scrape HTML
    try:
        r = requests.get('https://earn.superteam.fun/', headers=headers, timeout=30)
        soup = BeautifulSoup(r.text, 'html.parser')
        
        cards = soup.select('[class*="card"], [class*="listing"], [class*="bounty"], [class*="opportunity"]')
        print(f'  HTML: {len(cards)} cards')
        
        for card in cards:
            try:
                title = card.select_one('h2, h3, h4, .title')
                link = card.select_one('a[href]')
                prize = card.select_one('[class*="reward"], [class*="amount"], [class*="prize"]')
                
                if title:
                    href = link.get('href', '') if link else ''
                    if not href.startswith('http'):
                        href = 'https://earn.superteam.fun' + href
                    
                    raw = {
                        'title': title.get_text(strip=True),
                        'url': href or 'https://earn.superteam.fun',
                        'prize': prize.get_text(strip=True) if prize else None,
                        'mode': 'online',
                        'tags': ['Solana', 'Web3']
                    }
                    if raw['title'] and len(raw['title']) > 3:
                        db.save_event(normalizer.normalize(raw, 'Superteam'))
                        saved += 1
            except:
                pass
    except Exception as e:
        print(f'  HTML error: {e}')
    
    print(f'  ✓ Saved {saved} Superteam events')
    return saved

def main():
    print('='*50)
    print('  Deep Scrape: HackerEarth, HackCulture, Superteam')
    print('='*50)
    
    before = db.get_statistics()['total_events']
    
    he = scrape_hackerearth()
    hc = scrape_hackculture()
    st = scrape_superteam()
    
    after = db.get_statistics()
    
    print('\n' + '='*50)
    print(f'  HackerEarth: +{he}')
    print(f'  HackCulture: +{hc}')
    print(f'  Superteam: +{st}')
    print(f'  Total added: {after["total_events"] - before}')
    print(f'  Database now: {after["total_events"]}')
    print('='*50)

if __name__ == '__main__':
    main()
