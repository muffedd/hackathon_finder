"""
Database Manager Module
=======================
Handles persistent storage of scraped hackathon data using SQLite.

Features:
- Efficient caching with TTL (time-to-live)
- Full-text search support
- Filtering by date, tags, source, mode
- Pagination
- Deduplication
"""

import sqlite3
import json
import os
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple
from contextlib import contextmanager
from pathlib import Path

# Import from within package when used as module
try:
    from utils.data_normalizer import HackathonEvent
except ImportError:
    from data_normalizer import HackathonEvent


class DatabaseManager:
    """
    SQLite-based storage for hackathon events.
    
    Provides:
    - CRUD operations for events
    - Caching with automatic expiration
    - Advanced filtering and search
    - Pagination support
    """
    
    def __init__(self, db_path: str = "hackathons.db"):
        """
        Initialize database connection.
        
        Args:
            db_path: Path to SQLite database file
        """
        self.db_path = db_path
        self._ensure_db_directory()
        self._init_database()
    
    def _ensure_db_directory(self):
        """Create database directory if it doesn't exist."""
        db_dir = os.path.dirname(self.db_path)
        if db_dir and not os.path.exists(db_dir):
            os.makedirs(db_dir)
    
    @contextmanager
    def _get_connection(self):
        """Context manager for database connections."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()
    
    def _init_database(self):
        """Create database tables if they don't exist."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            # Main events table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS events (
                    id TEXT PRIMARY KEY,
                    source TEXT NOT NULL,
                    title TEXT NOT NULL,
                    url TEXT NOT NULL,
                    start_date TEXT,
                    end_date TEXT,
                    registration_deadline TEXT,
                    location TEXT,
                    mode TEXT,
                    description TEXT,
                    prize_pool TEXT,
                    prize_pool_numeric REAL DEFAULT 0,
                    image_url TEXT,
                    logo_url TEXT,
                    organizer TEXT,
                    participants_count INTEGER,
                    team_size_min INTEGER,
                    team_size_max INTEGER,
                    status TEXT,
                    scraped_at TEXT,
                    last_updated TEXT,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Tags table (many-to-many)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS event_tags (
                    event_id TEXT NOT NULL,
                    tag TEXT NOT NULL,
                    PRIMARY KEY (event_id, tag),
                    FOREIGN KEY (event_id) REFERENCES events(id) ON DELETE CASCADE
                )
            """)
            
            # Themes table (many-to-many)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS event_themes (
                    event_id TEXT NOT NULL,
                    theme TEXT NOT NULL,
                    PRIMARY KEY (event_id, theme),
                    FOREIGN KEY (event_id) REFERENCES events(id) ON DELETE CASCADE
                )
            """)
            
            # Scraping metadata table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS scrape_metadata (
                    source TEXT PRIMARY KEY,
                    last_scraped TEXT,
                    event_count INTEGER DEFAULT 0,
                    success BOOLEAN DEFAULT 1,
                    error_message TEXT
                )
            """)
            
            # Create indexes for common queries
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_events_source ON events(source)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_events_start_date ON events(start_date)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_events_status ON events(status)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_events_mode ON events(mode)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_events_prize ON events(prize_pool_numeric)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_tags_tag ON event_tags(tag)")
            
            # Create FTS (Full-Text Search) virtual table
            cursor.execute("""
                CREATE VIRTUAL TABLE IF NOT EXISTS events_fts USING fts5(
                    title, description, location, organizer,
                    content='events',
                    content_rowid='rowid'
                )
            """)
            
            # Triggers to keep FTS in sync
            cursor.execute("""
                CREATE TRIGGER IF NOT EXISTS events_ai AFTER INSERT ON events BEGIN
                    INSERT INTO events_fts(rowid, title, description, location, organizer)
                    VALUES (NEW.rowid, NEW.title, NEW.description, NEW.location, NEW.organizer);
                END
            """)
            
            cursor.execute("""
                CREATE TRIGGER IF NOT EXISTS events_ad AFTER DELETE ON events BEGIN
                    INSERT INTO events_fts(events_fts, rowid, title, description, location, organizer)
                    VALUES ('delete', OLD.rowid, OLD.title, OLD.description, OLD.location, OLD.organizer);
                END
            """)
            
            cursor.execute("""
                CREATE TRIGGER IF NOT EXISTS events_au AFTER UPDATE ON events BEGIN
                    INSERT INTO events_fts(events_fts, rowid, title, description, location, organizer)
                    VALUES ('delete', OLD.rowid, OLD.title, OLD.description, OLD.location, OLD.organizer);
                    INSERT INTO events_fts(rowid, title, description, location, organizer)
                    VALUES (NEW.rowid, NEW.title, NEW.description, NEW.location, NEW.organizer);
                END
            """)
    
    # ============ CRUD Operations ============
    
    def save_event(self, event: HackathonEvent) -> bool:
        """
        Save or update a single event.
        
        Args:
            event: HackathonEvent object to save
            
        Returns:
            True if successful
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            # Upsert event
            cursor.execute("""
                INSERT OR REPLACE INTO events (
                    id, source, title, url, start_date, end_date,
                    registration_deadline, location, mode, description,
                    prize_pool, prize_pool_numeric, image_url, logo_url,
                    organizer, participants_count, team_size_min, team_size_max,
                    status, scraped_at, last_updated
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                event.id, event.source, event.title, event.url,
                event.start_date, event.end_date, event.registration_deadline,
                event.location, event.mode, event.description,
                event.prize_pool, event.prize_pool_numeric,
                event.image_url, event.logo_url, event.organizer,
                event.participants_count, event.team_size_min, event.team_size_max,
                event.status, event.scraped_at, event.last_updated
            ))
            
            # Update tags
            cursor.execute("DELETE FROM event_tags WHERE event_id = ?", (event.id,))
            for tag in event.tags:
                cursor.execute(
                    "INSERT OR IGNORE INTO event_tags (event_id, tag) VALUES (?, ?)",
                    (event.id, tag)
                )
            
            # Update themes
            cursor.execute("DELETE FROM event_themes WHERE event_id = ?", (event.id,))
            for theme in event.themes:
                cursor.execute(
                    "INSERT OR IGNORE INTO event_themes (event_id, theme) VALUES (?, ?)",
                    (event.id, theme)
                )
            
            return True
    
    def save_events(self, events: List[HackathonEvent], source: str) -> int:
        """
        Save multiple events from a source.
        Updates scrape metadata.
        
        Args:
            events: List of HackathonEvent objects
            source: Source platform name
            
        Returns:
            Number of events saved
        """
        count = 0
        for event in events:
            if self.save_event(event):
                count += 1
        
        # Update scrape metadata
        self.update_scrape_metadata(source, count, True)
        
        return count
    
    def get_event(self, event_id: str) -> Optional[HackathonEvent]:
        """Get a single event by ID."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM events WHERE id = ?", (event_id,))
            row = cursor.fetchone()
            
            if not row:
                return None
            
            return self._row_to_event(dict(row), cursor)
    
    def delete_event(self, event_id: str) -> bool:
        """Delete an event by ID."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM events WHERE id = ?", (event_id,))
            return cursor.rowcount > 0
    
    def delete_old_events(self, days: int = 90) -> int:
        """Delete events that ended more than X days ago."""
        cutoff = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "DELETE FROM events WHERE end_date < ? OR (end_date IS NULL AND start_date < ?)",
                (cutoff, cutoff)
            )
            return cursor.rowcount
    
    # ============ Query Operations ============
    
    def query_events(
        self,
        search: Optional[str] = None,
        source: Optional[str] = None,
        sources: Optional[List[str]] = None,
        mode: Optional[str] = None,
        tags: Optional[List[str]] = None,
        status: Optional[str] = None,
        start_after: Optional[str] = None,
        start_before: Optional[str] = None,
        min_prize: Optional[float] = None,
        sort_by: str = "start_date",
        sort_order: str = "asc",
        page: int = 1,
        page_size: int = 50
    ) -> Tuple[List[HackathonEvent], int]:
        """
        Advanced query with filtering, sorting, and pagination.
        
        Args:
            search: Full-text search query
            source: Filter by single source
            sources: Filter by multiple sources
            mode: Filter by mode (in-person, online, hybrid)
            tags: Filter by tags (any match)
            status: Filter by status (upcoming, ongoing, ended)
            start_after: Events starting after this date
            start_before: Events starting before this date
            min_prize: Minimum prize pool (numeric)
            sort_by: Field to sort by (start_date, prize_pool_numeric, title)
            sort_order: asc or desc
            page: Page number (1-indexed)
            page_size: Results per page
            
        Returns:
            Tuple of (events list, total count)
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            # Build query
            conditions = []
            params = []
            
            # Full-text search
            if search:
                conditions.append("""
                    id IN (
                        SELECT e.id FROM events e
                        JOIN events_fts ON events_fts.rowid = e.rowid
                        WHERE events_fts MATCH ?
                    )
                """)
                params.append(search)
            
            # Source filter
            if source:
                conditions.append("source = ?")
                params.append(source)
            elif sources:
                placeholders = ",".join("?" * len(sources))
                conditions.append(f"source IN ({placeholders})")
                params.extend(sources)
            
            # Mode filter
            if mode:
                conditions.append("mode = ?")
                params.append(mode)
            
            # Status filter
            if status:
                conditions.append("status = ?")
                params.append(status)
            
            # Date filters
            if start_after:
                conditions.append("start_date >= ?")
                params.append(start_after)
            if start_before:
                conditions.append("start_date <= ?")
                params.append(start_before)
            
            # Prize filter
            if min_prize is not None:
                conditions.append("prize_pool_numeric >= ?")
                params.append(min_prize)
            
            # Tags filter
            if tags:
                tag_placeholders = ",".join("?" * len(tags))
                conditions.append(f"""
                    id IN (
                        SELECT event_id FROM event_tags
                        WHERE tag IN ({tag_placeholders})
                    )
                """)
                params.extend(tags)
            
            # Build WHERE clause
            where_clause = " AND ".join(conditions) if conditions else "1=1"
            
            # Validate sort field
            valid_sort_fields = ["start_date", "prize_pool_numeric", "title", "scraped_at", "source"]
            if sort_by not in valid_sort_fields:
                sort_by = "start_date"
            
            sort_direction = "DESC" if sort_order.lower() == "desc" else "ASC"
            
            # Get total count
            count_query = f"SELECT COUNT(*) FROM events WHERE {where_clause}"
            cursor.execute(count_query, params)
            total = cursor.fetchone()[0]
            
            # Get paginated results
            offset = (page - 1) * page_size
            query = f"""
                SELECT * FROM events
                WHERE {where_clause}
                ORDER BY {sort_by} {sort_direction}
                LIMIT ? OFFSET ?
            """
            cursor.execute(query, params + [page_size, offset])
            
            events = [self._row_to_event(dict(row), cursor) for row in cursor.fetchall()]
            
            return events, total
    
    def get_all_tags(self) -> List[Tuple[str, int]]:
        """Get all unique tags with their counts."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT tag, COUNT(*) as count
                FROM event_tags
                GROUP BY tag
                ORDER BY count DESC
            """)
            return [(row['tag'], row['count']) for row in cursor.fetchall()]
    
    def get_all_sources(self) -> List[Tuple[str, int]]:
        """Get all sources with their event counts."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT source, COUNT(*) as count
                FROM events
                GROUP BY source
                ORDER BY count DESC
            """)
            return [(row['source'], row['count']) for row in cursor.fetchall()]
    
    def get_statistics(self) -> Dict:
        """Get database statistics."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            # Total events
            cursor.execute("SELECT COUNT(*) FROM events")
            total = cursor.fetchone()[0]
            
            # By status
            cursor.execute("""
                SELECT status, COUNT(*) as count
                FROM events GROUP BY status
            """)
            by_status = {row['status']: row['count'] for row in cursor.fetchall()}
            
            # By source
            cursor.execute("""
                SELECT source, COUNT(*) as count
                FROM events GROUP BY source
            """)
            by_source = {row['source']: row['count'] for row in cursor.fetchall()}
            
            # By mode
            cursor.execute("""
                SELECT mode, COUNT(*) as count
                FROM events GROUP BY mode
            """)
            by_mode = {row['mode']: row['count'] for row in cursor.fetchall()}
            
            return {
                "total_events": total,
                "by_status": by_status,
                "by_source": by_source,
                "by_mode": by_mode
            }
    
    # ============ Cache Operations ============
    
    def is_cache_fresh(self, source: str, max_age_hours: int = 6) -> bool:
        """Check if cached data for a source is still fresh."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT last_scraped FROM scrape_metadata WHERE source = ?",
                (source,)
            )
            row = cursor.fetchone()
            
            if not row or not row['last_scraped']:
                return False
            
            last_scraped = datetime.fromisoformat(row['last_scraped'])
            age = datetime.now() - last_scraped
            
            return age.total_seconds() < max_age_hours * 3600
    
    def update_scrape_metadata(
        self,
        source: str,
        event_count: int,
        success: bool,
        error_message: Optional[str] = None
    ):
        """Update scraping metadata for a source."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT OR REPLACE INTO scrape_metadata 
                (source, last_scraped, event_count, success, error_message)
                VALUES (?, ?, ?, ?, ?)
            """, (
                source,
                datetime.now().isoformat(),
                event_count,
                success,
                error_message
            ))
    
    def get_scrape_metadata(self, source: str) -> Optional[Dict]:
        """Get scraping metadata for a source."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT * FROM scrape_metadata WHERE source = ?",
                (source,)
            )
            row = cursor.fetchone()
            return dict(row) if row else None
    
    def get_stale_sources(self, max_age_hours: int = 6) -> List[str]:
        """Get list of sources that need refreshing."""
        cutoff = (datetime.now() - timedelta(hours=max_age_hours)).isoformat()
        
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT source FROM scrape_metadata
                WHERE last_scraped < ? OR last_scraped IS NULL
            """, (cutoff,))
            
            return [row['source'] for row in cursor.fetchall()]
    
    # ============ Helper Methods ============
    
    def _row_to_event(self, row: Dict, cursor) -> HackathonEvent:
        """Convert database row to HackathonEvent object."""
        # Get tags
        cursor.execute(
            "SELECT tag FROM event_tags WHERE event_id = ?",
            (row['id'],)
        )
        tags = [r['tag'] for r in cursor.fetchall()]
        
        # Get themes
        cursor.execute(
            "SELECT theme FROM event_themes WHERE event_id = ?",
            (row['id'],)
        )
        themes = [r['theme'] for r in cursor.fetchall()]
        
        return HackathonEvent(
            id=row['id'],
            source=row['source'],
            title=row['title'],
            url=row['url'],
            start_date=row['start_date'],
            end_date=row['end_date'],
            registration_deadline=row['registration_deadline'],
            location=row['location'],
            mode=row['mode'],
            description=row['description'],
            prize_pool=row['prize_pool'],
            prize_pool_numeric=row['prize_pool_numeric'] or 0,
            tags=tags,
            themes=themes,
            image_url=row['image_url'],
            logo_url=row['logo_url'],
            organizer=row['organizer'],
            participants_count=row['participants_count'],
            team_size_min=row['team_size_min'],
            team_size_max=row['team_size_max'],
            status=row['status'],
            scraped_at=row['scraped_at'],
            last_updated=row['last_updated'],
        )


if __name__ == "__main__":
    # Test the database manager
    import sys
    sys.path.insert(0, str(Path(__file__).parent.parent))
    
    db = DatabaseManager("test_hackathons.db")
    
    # Create test event
    test_event = HackathonEvent(
        id="test123",
        source="MLH",
        title="HackMIT 2026",
        url="https://hackmit.org",
        start_date="2026-02-15",
        end_date="2026-02-17",
        location="Cambridge, MA",
        mode="in-person",
        prize_pool="$50K",
        prize_pool_numeric=50000,
        tags=["AI", "Student", "Web3"],
        status="upcoming"
    )
    
    # Save
    db.save_event(test_event)
    print("✓ Event saved")
    
    # Retrieve
    retrieved = db.get_event("test123")
    print(f"✓ Retrieved: {retrieved.title}")
    
    # Query
    events, total = db.query_events(tags=["AI"])
    print(f"✓ Query found {total} events with 'AI' tag")
    
    # Statistics
    stats = db.get_statistics()
    print(f"✓ Stats: {stats}")
    
    # Cleanup
    os.remove("test_hackathons.db")
    print("✓ Test database cleaned up")
