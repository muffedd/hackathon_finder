"""Scrape Devpost API with pagination - FIXED"""
import requests
import sys
sys.path.insert(0, '.')
from database.db_manager import DatabaseManager
from utils.data_normalizer import DataNormalizer

headers = {'User-Agent': 'Mozilla/5.0', 'Accept': 'application/json'}
db = DatabaseManager('hackathons.db')
normalizer = DataNormalizer()

all_hackathons = []
for page in range(1, 5):
    url = f'https://devpost.com/api/hackathons?page={page}&per_page=50'
    print(f'Fetching page {page}...')
    r = requests.get(url, headers=headers, timeout=30)
    data = r.json()
    hackathons = data.get('hackathons', [])
    print(f'  Got {len(hackathons)} hackathons')
    if not hackathons:
        break
    all_hackathons.extend(hackathons)

print(f'\nTotal: {len(all_hackathons)} hackathons')

# Debug first one
if all_hackathons:
    h = all_hackathons[0]
    print(f'\nSample hackathon keys: {list(h.keys())}')

saved = 0
for h in all_hackathons:
    try:
        # Handle dates - might be string or dict
        dates = h.get('submission_period_dates')
        if isinstance(dates, dict):
            start = dates.get('starts_at')
            end = dates.get('ends_at')
        elif isinstance(dates, str):
            # Parse from string like "Jan 15 - Feb 15, 2026"
            start = dates
            end = None
        else:
            start = None
            end = None
        
        raw = {
            'title': h.get('title'),
            'url': h.get('url'),
            'start_date': start,
            'end_date': end,
            'location': 'Online' if h.get('online_only') else (h.get('displayed_location') or h.get('location', {}).get('location') if isinstance(h.get('location'), dict) else h.get('location')),
            'prize': h.get('prize_amount'),
            'description': h.get('tagline'),
            'image': h.get('thumbnail_url'),
            'tags': h.get('themes') if isinstance(h.get('themes'), list) else [],
            'mode': 'online' if h.get('online_only') else 'in-person'
        }
        event = normalizer.normalize(raw, 'Devpost')
        db.save_event(event)
        saved += 1
    except Exception as e:
        print(f'  Error for {h.get("title", "?")}: {e}')

print(f'\nSaved {saved} to database')
stats = db.get_statistics()
print(f'Database now has {stats["total_events"]} total events')
