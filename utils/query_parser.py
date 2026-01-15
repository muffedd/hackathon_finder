"""
AI Query Parser
===============
Parses natural language queries into structured filters using Gemini Flash.
Minimal token usage (~100 tokens per request).
"""
import os
import json
from typing import Optional, Dict, Any

# System prompt tuned for hackathon search intent parsing
SYSTEM_PROMPT = """You are a hackathon search query parser. Convert user queries into structured filters.

Return a JSON object with ONLY the fields implied by the query:

{
  "mode": "online" | "offline" | null,
  "tags": ["python", "ai", "web3", ...],  // lowercase tech/themes
  "exclude_tags": ["crypto", ...],         // if user says "NOT X"
  "has_prize": true | false | null,
  "prize_min": number | null,              // in USD
  "date_range": "this_week" | "this_month" | "upcoming" | null,
  "location": "India" | "USA" | null,      // country or city
  "source": "Devpost" | "MLH" | null       // specific platform
}

Rules:
- Only include fields the query implies
- Tags should be lowercase, common tech terms
- Infer "has_prize": true if user mentions "prizes", "money", "rewards"
- Infer mode from: "remote"/"virtual" = online, "in-person"/"physical" = offline
- Be concise, return ONLY valid JSON
"""

def parse_user_query(query: str) -> Dict[str, Any]:
    """
    Parse a natural language query into structured filters.
    
    Args:
        query: User's search query (e.g., "python hackathon online with prizes")
        
    Returns:
        Dictionary with parsed filters
    """
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        # Fallback: return empty filters (will return all events)
        return {"error": "GEMINI_API_KEY not set"}
    
    try:
        import google.generativeai as genai
        
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel(
            'models/gemini-2.5-flash-preview-09-2025',
            system_instruction=SYSTEM_PROMPT
        )
        
        response = model.generate_content(
            query,
            generation_config={
                "response_mime_type": "application/json",
                "temperature": 0.1  # Low temp for consistent parsing
            }
        )
        
        # Parse response
        try:
            filters = json.loads(response.text)
        except json.JSONDecodeError:
            # Try to extract JSON from markdown code block
            text = response.text.replace('```json', '').replace('```', '').strip()
            filters = json.loads(text)
        
        print(f"Query Parser: '{query[:50]}...' -> {filters}")
        return filters
        
    except Exception as e:
        print(f"Query Parser Error: {e}")
        return {"error": str(e)}


def apply_filters_to_events(events: list, filters: Dict[str, Any]) -> list:
    """
    Apply parsed filters to a list of events locally.
    
    Args:
        events: List of event dictionaries
        filters: Parsed filter dictionary from parse_user_query
        
    Returns:
        Filtered list of events
    """
    if not filters or "error" in filters:
        return events
    
    result = events
    
    # Filter by mode
    if filters.get("mode"):
        mode = filters["mode"].lower()
        result = [e for e in result if e.get("mode", "").lower() == mode]
    
    # Filter by tags (any match)
    if filters.get("tags"):
        search_tags = set(t.lower() for t in filters["tags"])
        def has_tag(event):
            event_tags = event.get("tags", [])
            if isinstance(event_tags, str):
                event_tags = [event_tags]
            event_tags_lower = set(t.lower() for t in event_tags if t)
            # Also check title and description
            title = (event.get("title") or "").lower()
            desc = (event.get("description") or "").lower()
            text = f"{title} {desc} {' '.join(event_tags_lower)}"
            return any(tag in text for tag in search_tags)
        result = [e for e in result if has_tag(e)]
    
    # Exclude tags
    if filters.get("exclude_tags"):
        exclude = set(t.lower() for t in filters["exclude_tags"])
        def no_excluded_tag(event):
            event_tags = event.get("tags", [])
            if isinstance(event_tags, str):
                event_tags = [event_tags]
            event_tags_lower = set(t.lower() for t in event_tags if t)
            title = (event.get("title") or "").lower()
            return not any(tag in title or tag in event_tags_lower for tag in exclude)
        result = [e for e in result if no_excluded_tag(e)]
    
    # Filter by prize
    if filters.get("has_prize"):
        result = [e for e in result if e.get("prize_pool_numeric", 0) > 0]
    
    if filters.get("prize_min"):
        min_prize = filters["prize_min"]
        result = [e for e in result if e.get("prize_pool_numeric", 0) >= min_prize]
    
    # Filter by source
    if filters.get("source"):
        source = filters["source"].lower()
        result = [e for e in result if source in (e.get("source") or "").lower()]
    
    # Filter by location
    if filters.get("location"):
        loc = filters["location"].lower()
        result = [e for e in result if loc in (e.get("location") or "").lower()]
    
    return result
