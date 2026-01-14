from database.db_manager import DatabaseManager
import sqlite3

def inspect_data():
    db = DatabaseManager()
    
    print("--- INSPECTING 'Electrothon 8.0' ---")
    # Search specifically for Electrothon
    # Note: query_events returns (events_list, total_count)
    events, count = db.query_events(search='Electrothon', page_size=20)
    
    if not events:
        print("No events found matching 'Electrothon'.")
    
    for e in events:
        print(f"ID: {e.id}")
        print(f"Title: {e.title}")
        print(f"Source: {e.source}")
        print(f"URL: {e.url}")
        print(f"Dates: {e.start_date} to {e.end_date}")
        print(f"Prize: {e.prize_pool}")
        print(f"Team: {e.team_size_min}-{e.team_size_max}")
        print("-" * 30)

    print("\n--- CHECKING FOR COMMON DUPLICATES ---")
    # Direct DB query for duplicates
    conn = sqlite3.connect('hackathons.db')
    cursor = conn.cursor()
    
    # 1. Duplicates by Title across different sources
    print("\nDuplicate Titles (Count > 1):")
    cursor.execute("""
        SELECT title, COUNT(*), GROUP_CONCAT(source) 
        FROM events 
        GROUP BY title 
        HAVING COUNT(*) > 1 
        ORDER BY COUNT(*) DESC 
        LIMIT 10
    """)
    rows = cursor.fetchall()
    for row in rows:
        title, count, sources = row
        print(f"Title: '{title}' | Count: {count} | Sources: {sources}")
        
    conn.close()

if __name__ == "__main__":
    inspect_data()
