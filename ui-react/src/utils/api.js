// API Configuration
// In production (Netlify), set VITE_API_URL environment variable
// In development, falls back to localhost
export const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000/api';

// Fetch all hackathons with pagination (backend limits to 200 per page)
export async function fetchHackathons(params = {}) {
    const pageSize = 200; // Backend max
    let allEvents = [];
    let page = 1;
    let hasMore = true;

    while (hasMore) {
        const searchParams = new URLSearchParams({
            page: page,
            page_size: pageSize,
            sort_by: params.sortBy || 'prize',
        });

        const response = await fetch(`${API_BASE}/hackathons?${searchParams}`);
        if (!response.ok) throw new Error('Failed to fetch hackathons');

        const data = await response.json();
        const events = data.events || [];
        allEvents = allEvents.concat(events);

        // Check if there are more pages
        if (events.length < pageSize || allEvents.length >= (data.total || 0)) {
            hasMore = false;
        } else {
            page++;
        }
    }

    return { events: allEvents, total: allEvents.length };
}

// Fetch available sources
export async function fetchSources() {
    const response = await fetch(`${API_BASE}/sources`);
    if (!response.ok) throw new Error('Failed to fetch sources');
    return response.json();
}

// AI Search
export async function aiSearch(query) {
    const response = await fetch(`${API_BASE}/search/ai?q=${encodeURIComponent(query)}`);
    if (!response.ok) throw new Error('AI search failed');
    return response.json();
}
