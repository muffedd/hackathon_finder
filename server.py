"""
HackFind Server (FastAPI)
=========================
FastAPI server with API for hackathon data.
Auto-generated Swagger docs at /docs
"""
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, Query
from fastapi.responses import FileResponse, JSONResponse
import uvicorn

BASE_DIR = Path(__file__).parent.absolute()
UI_DIR = BASE_DIR / 'ui'
sys.path.insert(0, str(BASE_DIR))

app = FastAPI(
    title="HackFind API",
    description="Hackathon Aggregator API with semantic search",
    version="2.0.0"
)

db = None


def get_db():
    global db
    if db is None:
        from database.db_manager import DatabaseManager
        db = DatabaseManager(str(BASE_DIR / "hackathons.db"))
    return db


def recalculate_status(event_dict):
    """Recalculate status based on current date (not scrape date)."""
    today = datetime.now().date()
    
    start_date = event_dict.get('start_date')
    end_date = event_dict.get('end_date')
    
    if not start_date:
        event_dict['status'] = 'unknown'
        return event_dict
    
    try:
        # Parse start date
        if isinstance(start_date, str):
            start = datetime.strptime(start_date[:10], "%Y-%m-%d").date()
        else:
            start = start_date
        
        # Parse end date (fall back to start if not available)
        if end_date:
            if isinstance(end_date, str):
                end = datetime.strptime(end_date[:10], "%Y-%m-%d").date()
            else:
                end = end_date
        else:
            end = start
        
        # Determine current status
        if today < start:
            event_dict['status'] = 'upcoming'
        elif start <= today <= end:
            event_dict['status'] = 'ongoing'
        else:
            event_dict['status'] = 'ended'
            
    except (ValueError, TypeError):
        event_dict['status'] = 'unknown'
    
    return event_dict


# === Serve UI ===
@app.get("/", include_in_schema=False)
async def home():
    return FileResponse(str(UI_DIR / 'index.html'))


@app.get("/styles.css", include_in_schema=False)
async def styles():
    return FileResponse(str(UI_DIR / 'styles.css'), media_type='text/css')


@app.get("/app.js", include_in_schema=False)
async def appjs():
    return FileResponse(str(UI_DIR / 'app.js'), media_type='application/javascript')


# === API ===
# Cache for recalculated events (refreshes every 5 minutes)
_events_cache = {"data": None, "timestamp": 0}
CACHE_TTL = 300  # 5 minutes

def get_all_events_cached():
    """Get all events with caching for repeated requests."""
    global _events_cache
    import time
    now = time.time()
    
    if _events_cache["data"] and (now - _events_cache["timestamp"]) < CACHE_TTL:
        return _events_cache["data"]
    
    database = get_db()
    events, _ = database.query_events(page=1, page_size=10000)
    
    events_data = []
    today = datetime.now().date()
    
    for e in events:
        ed = e.to_dict()
        try:
            s_date = datetime.strptime(ed.get('start_date', ''), "%Y-%m-%d").date() if ed.get('start_date') else None
            e_date = datetime.strptime(ed.get('end_date', ''), "%Y-%m-%d").date() if ed.get('end_date') else s_date
            if s_date and s_date > today:
                ed['status'] = 'upcoming'
            elif s_date and e_date and s_date <= today <= e_date:
                ed['status'] = 'ongoing'
            else:
                ed['status'] = 'ended'
        except:
            ed['status'] = 'unknown'
        events_data.append(ed)
    
    _events_cache = {"data": events_data, "timestamp": now}
    return events_data

@app.get("/api/hackathons", tags=["Hackathons"])
async def api_hackathons(
    page: int = Query(default=1, ge=1, description="Page number"),
    page_size: int = Query(default=50, ge=1, le=200, description="Items per page"),
    sort_by: str = Query(default="prize", description="Sort by: prize, date, latest"),
    status: str = Query(default="", description="Filter by status: upcoming, ongoing, ended"),
    mode: str = Query(default="", description="Filter by mode: online, offline"),
    source: str = Query(default="", description="Filter by source platform"),
    search: str = Query(default="", description="Search query")
):
    """Get hackathons with pagination and filters."""
    import time
    t0 = time.time()
    
    try:
        # Get cached events
        all_events = get_all_events_cached()
        
        # Apply filters
        result = all_events
        
        if status:
            result = [e for e in result if e.get('status') == status.lower()]
        if mode:
            result = [e for e in result if e.get('mode') and mode.lower() in e['mode'].lower()]
        if source:
            result = [e for e in result if e.get('source') and source.lower() in e['source'].lower()]
        if search:
            search_lower = search.lower()
            result = [e for e in result if 
                      search_lower in (e.get('title') or '').lower() or
                      search_lower in (e.get('description') or '').lower() or
                      any(search_lower in t.lower() for t in (e.get('tags') or []))]
        
        # Sort
        if sort_by == "prize":
            result.sort(key=lambda x: x.get('prize_pool_numeric') or 0, reverse=True)
        elif sort_by == "date":
            result.sort(key=lambda x: x.get('start_date') or '9999', reverse=False)
        elif sort_by == "latest":
            result.sort(key=lambda x: x.get('scraped_at') or '', reverse=True)
        
        # Paginate
        total = len(result)
        start = (page - 1) * page_size
        end = start + page_size
        paginated = result[start:end]
        
        print(f"API: Page {page}, {len(paginated)}/{total} events in {time.time()-t0:.3f}s")
        
        return {
            "events": paginated,
            "total": total,
            "page": page,
            "page_size": page_size,
            "total_pages": (total + page_size - 1) // page_size
        }
    except Exception as e:
        print(f"API Error: {e}")
        import traceback
        traceback.print_exc()
        return {"events": [], "total": 0, "page": 1, "page_size": page_size, "total_pages": 0}

@app.get("/api/sources", tags=["Metadata"])
async def api_sources():
    """Get all unique source platforms."""
    all_events = get_all_events_cached()
    sources = sorted(set(e.get('source') for e in all_events if e.get('source')))
    return {"sources": sources}

@app.get("/api/locations", tags=["Metadata"])
async def api_locations():
    """Get all unique locations (countries/cities)."""
    all_events = get_all_events_cached()
    locations = set()
    for e in all_events:
        loc = e.get('location')
        if loc and loc.strip() and loc.lower() not in ['online', 'virtual', 'remote', 'tbd', 'tba']:
            # Clean and normalize location
            locations.add(loc.strip())
    return {"locations": sorted(locations)}


@app.get("/api/search/ai", tags=["Search"])
async def ai_search(
    q: str = Query(default="", description="Natural language search query")
):
    """
    AI-Powered Search using Query Parser architecture.
    1. Gemini parses query -> Structured filters (minimal tokens)
    2. Local Python applies filters -> Results
    """
    query = q.strip()
    if not query:
        return JSONResponse(status_code=400, content={"error": "Missing query parameter 'q'"})
    
    import time
    t0 = time.time()
    
    try:
        from utils.query_parser import parse_user_query, apply_filters_to_events
        
        # Step 1: Parse query with Gemini (minimal tokens ~100)
        filters = parse_user_query(query)
        t1 = time.time()
        
        if "error" in filters:
            return JSONResponse(status_code=503, content={"error": filters["error"]})
        
        # Step 2: Fetch all upcoming/ongoing events
        database = get_db()
        events, _ = database.query_events(page_size=2000)
        
        # Convert to dicts and filter by status
        today = datetime.now().date()
        active_events = []
        for e in events:
            e_dict = recalculate_status(e.to_dict())
            if e_dict.get("status") in ["upcoming", "ongoing"]:
                active_events.append(e_dict)
        
        t2 = time.time()
        
        # Step 3: Apply parsed filters locally (instant)
        filtered = apply_filters_to_events(active_events, filters)
        t3 = time.time()
        
        # Step 4: Sort by prize (highest first) and limit to 4
        filtered.sort(key=lambda x: x.get("prize_pool_numeric", 0) or 0, reverse=True)
        results = filtered[:4]  # Limit to 4 recommendations
        
        # Add AI reason to each result based on filters
        for r in results:
            reasons = []
            if filters.get("mode"):
                reasons.append(f"Mode: {filters['mode']}")
            if filters.get("tags"):
                matching_tags = [t for t in filters["tags"] if t.lower() in (r.get("title", "")).lower()]
                if matching_tags:
                    reasons.append(f"Matches: {', '.join(matching_tags)}")
            if filters.get("has_prize") and r.get("prize_pool_numeric", 0) > 0:
                reasons.append(f"Has prize: {r.get('prize_pool', 'Yes')}")
            if filters.get("location") and filters["location"].lower() in (r.get("location") or "").lower():
                reasons.append(f"Location: {filters['location']}")
            
            r["ai_reason"] = " | ".join(reasons) if reasons else "Good match for your query"
            r["ai_filters"] = filters
        
        print(f"AI Search v2: Parse={t1-t0:.2f}s, Fetch={t2-t1:.2f}s, Filter={t3-t2:.2f}s, Total={t3-t0:.2f}s, Results={len(results)}")
        
        return results
        
    except Exception as e:
        print(f"AI Search Error: {e}")
        import traceback
        traceback.print_exc()
        if "429" in str(e) or "Quota" in str(e):
            return JSONResponse(status_code=429, content={"error": "AI Quota Exceeded. Please wait 1 minute and try again."})
        return JSONResponse(status_code=500, content={"error": str(e)})


@app.get("/api/stats", tags=["Stats"])
async def api_stats():
    """Get database statistics."""
    try:
        database = get_db()
        return database.get_statistics()
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={'error': str(e)}
        )


if __name__ == '__main__':
    print(f"\n{'='*50}")
    print(f"  HackFind Server (FastAPI)")
    print(f"  Port: 8000")
    print(f"  UI: {UI_DIR}")
    print(f"{'='*50}")
    print(f"  Open: http://localhost:8000")
    print(f"  API Docs: http://localhost:8000/docs")
    print(f"{'='*50}\n")
    uvicorn.run("server:app", host='127.0.0.1', port=8000, reload=True)
