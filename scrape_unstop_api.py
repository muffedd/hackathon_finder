
"""
High-performance API scraper for Unstop.
Uses internal API: https://unstop.com/api/public/competition/{id}
No browser required.
"""
import requests
import json
import re
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime

# Add project root to path
sys.path.insert(0, '.')
from database.db_manager import DatabaseManager
from scrape_all import extract_tags_from_text

# Headers to mimic browser (optional but good practice)
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "application/json, text/plain, */*",
    "Referer": "https://unstop.com/hackathons"
}

def clean_html(raw_html):
    """Simple cleaner to remove HTML tags for description storage."""
    cleanr = re.compile('<.*?>')
    cleantext = re.sub(cleanr, ' ', raw_html)
    return re.sub(r'\s+', ' ', cleantext).strip()

def fetch_details(event_id, event_url):
    """
    Fetch details for a single event ID from Unstop API.
    Returns parsed dict or None.
    """
    try:
        api_url = f"https://unstop.com/api/public/competition/{event_id}?round_lang=1"
        r = requests.get(api_url, headers=HEADERS, timeout=10)
        
        if r.status_code != 200:
            return None
        
        data = r.json()
        comp = data.get('data', {}).get('competition', {})
        if not comp:
             return None
             
        # Extract fields
        reg_req = comp.get('regnRequirements', {})
        
        # Deadlines
        reg_end_iso = reg_req.get('end_regn_dt') # "2025-11-30T23:59:00+05:30"
        reg_start_iso = reg_req.get('start_regn_dt')
        
        # Parse Dates
        end_date = None
        if reg_end_iso:
            try:
                # Keep ISO format or simplify to YYYY-MM-DD
                # DB expects YYYY-MM-DD usually for simplified checks, but we can store ISO string if column supports it.
                # Let's strip time for consistency with other scrapers usually returning YYYY-MM-DD
                end_date = reg_end_iso.split('T')[0]
            except: pass
            
        # Description
        raw_desc = comp.get('details', '')
        description = clean_html(raw_desc)[:3000] # Limit size
        
        # Team Size
        # API usually returns 'teamSize' (e.g. "1 - 4") or min/max fields
        ts_min = None
        ts_max = None
        
        # Try direct integer fields first
        if 'min_team_size' in reg_req:
            ts_min = reg_req.get('min_team_size')
        if 'max_team_size' in reg_req:
            ts_max = reg_req.get('max_team_size')
            
        # Try parsing string if ints missing
        if ts_min is None or ts_max is None:
            ts_str = reg_req.get('teamSize')
            if ts_str:
                # Expected formats: "1 - 4", "1-4", "4", "1 - 4 Members"
                parts = re.findall(r'\d+', str(ts_str))
                if len(parts) >= 2:
                    ts_min = int(parts[0])
                    ts_max = int(parts[1])
                elif len(parts) == 1:
                    val = int(parts[0])
                    ts_min = val
                    ts_max = val

        return {
            'end_date': end_date,
            'description': description,
            'reg_start': reg_start_iso,
            'team_size_min': ts_min,
            'team_size_max': ts_max,
            'region': comp.get('region'), # "online" or "offline"
            'city': comp.get('address_with_country_logo', {}).get('city'),
            'state': comp.get('address_with_country_logo', {}).get('state'),
            'registerCount': comp.get('registerCount', 0)
        }
        
    except Exception as e:
        # print(f"Error {event_id}: {e}")
        return None

def extract_id_from_url(url):
    # https://unstop.com/hackathons/name-12345
    # or just 12345
    parts = url.strip('/').split('-')
    if parts[-1].isdigit():
        return parts[-1]
    return None

def main():
    db = DatabaseManager('hackathons.db')
    print("Querying Unstop events...")
    events, total = db.query_events(sources=['Unstop'], page_size=10000)
    
    print(f"Found {len(events)} events. Starting API fetch...")
    
    to_process = []
    for e in events:
        if e.url:
            eid = extract_id_from_url(e.url)
            if eid:
                to_process.append({'db_event': e, 'api_id': eid})
                
    success_count = 0
    fail_count = 0
    
    print(f"Processing {len(to_process)} events with 5 workers...")
    
    with ThreadPoolExecutor(max_workers=5) as executor:
        future_map = {executor.submit(fetch_details, item['api_id'], item['db_event'].url): item for item in to_process}
        
        for future in as_completed(future_map):
            item = future_map[future]
            try:
                res = future.result()
                if res:
                    # Update DB Object
                    e = item['db_event']
                    updated = False
                    
                    if res['description'] and len(res['description']) > 50:
                        e.description = res['description']
                        e.tags = extract_tags_from_text(res['description'])
                        updated = True
                        
                    if res['end_date']:
                        e.end_date = res['end_date'] # Override with Reg Deadline
                        updated = True

                    if res.get('team_size_min') is not None:
                        e.team_size_min = res['team_size_min']
                        updated = True
                    
                    if res.get('team_size_max') is not None:
                        e.team_size_max = res['team_size_max']
                        updated = True
                        
                    # Mode & Location
                    reg = res.get('region')
                    if reg:
                        if reg.lower() == 'online':
                            e.mode = 'online'
                            e.location = 'Online'
                        elif reg.lower() == 'offline':
                            e.mode = 'in-person'
                            parts = [p for p in [res.get('city'), res.get('state')] if p]
                            e.location = ", ".join(parts) if parts else "In-Person"
                        updated = True
                        
                    # Participants
                    if res.get('registerCount') is not None:
                         e.participants_count = res['registerCount']
                         updated = True
                    
                    if updated:
                        db.save_event(e)
                        success_count += 1
                        ts_display = f" (Team: {e.team_size_min}-{e.team_size_max})" if e.team_size_max else ""
                        print(f"  ✓ {e.title[:20]}... (Date: {res['end_date']}){ts_display}")
                    else:
                        fail_count += 1
                else:
                    print(f"  ❌ No Data for {item['api_id']} (Status != 200 or No Comp Data)")
                    fail_count += 1
            except Exception as e:
                print(f"  ❌ Error processing {item['api_id']}: {e}")
                fail_count += 1

    print("="*40)
    print(f"API Scrape Complete.")
    print(f"Updated: {success_count}")
    print(f"Failed/NoData: {fail_count}")

if __name__ == "__main__":
    main()
