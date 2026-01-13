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
@app.get("/api/hackathons", tags=["Hackathons"])
async def api_hackathons(
    search: str = Query(default="", description="Search query for title/description"),
    mode: str = Query(default="", description="Filter by mode (online, in-person)"),
    location: str = Query(default="", description="Filter by location")
):
    """Get ALL hackathons from database with optional filters."""
    try:
        database = get_db()

        # Get ALL events - use large page_size to get everything
        events, total = database.query_events(
            search=search if search else None,
            page=1,
            page_size=50000  # Return all events
        )
        
        print(f"API: Returning {len(events)} hackathons (total in DB: {total})")
        
        # Filter by mode if specified
        if mode:
            events = [e for e in events if e.mode and mode.lower() in e.mode.lower()]
        
        # Filter by location if specified  
        if location:
            events = [e for e in events if e.location and location.lower() in e.location.lower()]
        
        # Recalculate status dynamically based on current date
        result = [recalculate_status(e.to_dict()) for e in events]
        return result
    except Exception as e:
        print(f"API Error: {e}")
        import traceback
        traceback.print_exc()
        return []


@app.get("/api/search/ai", tags=["Search"])
async def ai_search(
    q: str = Query(default="", description="Search query for semantic search")
):
    """Semantic search using AI embeddings (hybrid: vector + keyword)."""
    query = q.strip()
    if not query:
        return JSONResponse(
            status_code=400,
            content={"error": "Missing query parameter 'q'"}
        )
    
    # Limit query length for performance
    if len(query) > 500:
        query = query[:500]
    
    try:
        from utils.embeddings import generate_embedding
        from database.vector_store import search_similar, get_collection_count
        
        # Check if vector store has data
        count = get_collection_count()
        if count == 0:
            return JSONResponse(
                status_code=503,
                content={"error": "Vector store is empty. Run vectorize_events.py first."}
            )
        
        # Generate embedding for query (cached via lru_cache)
        query_embedding = generate_embedding(query)
        if not query_embedding:
            return JSONResponse(
                status_code=500,
                content={"error": "Failed to generate embedding"}
            )
        
        # 1. Vector Search (Semantic)
        vector_results = search_similar(query_embedding, top_k=20)
        
        # 2. Keyword Search (Lexical)
        database = get_db()
        keyword_events, _ = database.query_events(search=query, page_size=20)
        
        # 3. Merge and Rank (Hybrid)
        rank_map = {}
        
        # Process Vector Results
        for r in vector_results:
            rank_map[r['id']] = {
                'event': None,
                'id': r['id'],
                'score': r['score'],
                'matches': ['semantic']
            }
            
        # Process Keyword Results
        keyword_base_score = 0.4
        keyword_boost = 0.2
        
        for ke in keyword_events:
            k_dict = recalculate_status(ke.to_dict())
             
            if ke.id in rank_map:
                rank_map[ke.id]['score'] += keyword_boost
                rank_map[ke.id]['matches'].append('keyword')
                rank_map[ke.id]['event_dict'] = k_dict
            else:
                rank_map[ke.id] = {
                    'event_dict': k_dict,
                    'id': ke.id,
                    'score': keyword_base_score,
                    'matches': ['keyword']
                }
                 
        # Fetch missing vector event objects
        for vid, item in rank_map.items():
            if 'event_dict' not in item:
                event = database.get_event(vid)
                if event:
                    item['event_dict'] = recalculate_status(event.to_dict())
                else:
                    item['event_dict'] = None

        # Filter out None events and Sort
        final_list = []
        for item in rank_map.values():
            if item['event_dict']:
                ed = item['event_dict']
                ed['similarity_score'] = round(item['score'], 4)
                ed['match_types'] = item['matches']
                final_list.append(ed)
                
        # Sort by score descending
        final_list.sort(key=lambda x: x['similarity_score'], reverse=True)
        
        enriched = final_list[:30]
        
        print(f"AI Search (Hybrid): '{query[:50]}...' -> {len(enriched)} results")
        return enriched
        
    except ImportError as e:
        return JSONResponse(
            status_code=503,
            content={"error": f"AI dependencies not installed: {e}"}
        )
    except Exception as e:
        print(f"AI Search Error: {e}")
        import traceback
        traceback.print_exc()
        return JSONResponse(
            status_code=500,
            content={"error": str(e)}
        )


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
