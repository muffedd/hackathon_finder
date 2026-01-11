"""
HackFind Server
===============
Flask server with API for hackathon data.
"""
import os
import sys
import threading
import time
from datetime import datetime
from pathlib import Path
from flask import Flask, send_file, jsonify, request

BASE_DIR = Path(__file__).parent.absolute()
UI_DIR = BASE_DIR / 'ui'
sys.path.insert(0, str(BASE_DIR))

app = Flask(__name__)

db = None

def get_db():
    global db
    if db is None:
        from database.db_manager import DatabaseManager
        db = DatabaseManager(str(BASE_DIR / "hackathons.db"))
    return db

# === Serve UI ===
@app.route('/')
def home():
    return send_file(str(UI_DIR / 'index.html'))

@app.route('/styles.css')
def styles():
    return send_file(str(UI_DIR / 'styles.css'), mimetype='text/css')

@app.route('/app.js')
def appjs():
    return send_file(str(UI_DIR / 'app.js'), mimetype='application/javascript')

# === API ===
@app.route('/api/hackathons')
def api_hackathons():
    """Get ALL hackathons from database"""
    try:
        database = get_db()
        search = request.args.get('search', '')
        mode = request.args.get('mode', '')
        location = request.args.get('location', '')

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
        
        return jsonify([e.to_dict() for e in events])
    except Exception as e:
        print(f"API Error: {e}")
        import traceback
        traceback.print_exc()
        return jsonify([])

@app.route('/api/stats')
def api_stats():
    """Get database stats"""
    try:
        database = get_db()
        return jsonify(database.get_statistics())
    except Exception as e:
        return jsonify({'error': str(e)})

if __name__ == '__main__':
    print(f"\n{'='*50}")
    print(f"  HackFind Server")
    print(f"  Port: 8000")
    print(f"  UI: {UI_DIR}")
    print(f"{'='*50}")
    print(f"  Open: http://localhost:8000")
    print(f"{'='*50}\n")
    app.run(port=8000, debug=False, host='127.0.0.1')
