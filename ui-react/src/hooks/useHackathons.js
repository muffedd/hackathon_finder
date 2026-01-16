import { useState, useEffect, useCallback } from 'react';
import { fetchHackathons, fetchSources } from '../utils/api';
import { calculateStatus, calculateRelevanceScore } from '../utils/formatters';

// Load all hackathons at once (no pagination)

export function useHackathons() {
    const [hackathons, setHackathons] = useState([]);
    const [filteredHackathons, setFilteredHackathons] = useState([]);
    const [displayedCount, setDisplayedCount] = useState(0);
    const [isLoading, setIsLoading] = useState(true);
    const [allSources, setAllSources] = useState([]);
    const [selectedSources, setSelectedSources] = useState(new Set());

    // Filters
    const [currentFilter, setCurrentFilter] = useState('all');
    const [currentSort, setCurrentSort] = useState('relevance');
    const [searchQuery, setSearchQuery] = useState('');
    const [locationFilter, setLocationFilter] = useState('');

    // Fetch initial data
    useEffect(() => {
        async function loadData() {
            setIsLoading(true);
            try {
                // Fetch sources first
                try {
                    const sourcesData = await fetchSources();
                    const sources = sourcesData.sources || [];
                    setAllSources(sources);
                    setSelectedSources(new Set(sources));
                } catch {
                    console.log('Sources API not available, will extract from events');
                }

                // Fetch hackathons
                const data = await fetchHackathons({ sortBy: 'prize' });
                const events = data.events || [];
                setHackathons(events);

                // Extract sources from events if not fetched
                if (allSources.length === 0) {
                    const extractedSources = [...new Set(events.map(h => h.source).filter(Boolean))].sort();
                    setAllSources(extractedSources);
                    setSelectedSources(new Set(extractedSources));
                }
            } catch (error) {
                console.error('Failed to load hackathons:', error);
            } finally {
                setIsLoading(false);
            }
        }
        loadData();
    }, []);

    // Apply filters and sort whenever dependencies change
    useEffect(() => {
        let filtered = [...hackathons];

        // Source filter
        if (selectedSources.size > 0 && selectedSources.size < allSources.length) {
            filtered = filtered.filter(h => selectedSources.has(h.source));
        }

        // Status filter
        if (currentFilter !== 'all') {
            filtered = filtered.filter(h => {
                const status = calculateStatus(h);
                if (currentFilter === 'upcoming') return status === 'upcoming';
                if (currentFilter === 'live') return status === 'ongoing';
                if (currentFilter === 'online') return h.mode?.toLowerCase().includes('online');
                if (currentFilter === 'in-person') return h.mode?.toLowerCase().includes('in-person') || h.mode?.toLowerCase().includes('offline');
                return true;
            });
        }

        // Search query
        if (searchQuery) {
            const query = searchQuery.toLowerCase();
            filtered = filtered.filter(h =>
                h.title?.toLowerCase().includes(query) ||
                h.description?.toLowerCase().includes(query) ||
                h.organizer?.toLowerCase().includes(query)
            );
        }

        // Location filter
        if (locationFilter) {
            const loc = locationFilter.toLowerCase();
            filtered = filtered.filter(h => {
                const location = typeof h.location === 'string' ? h.location :
                    (h.location?.city || '') + (h.location?.country || '');
                return location.toLowerCase().includes(loc);
            });
        }

        // Sort
        if (currentSort === 'relevance') {
            filtered.sort((a, b) => calculateRelevanceScore(b) - calculateRelevanceScore(a));
        } else if (currentSort === 'prize') {
            filtered.sort((a, b) => (parseFloat(b.prize_pool) || 0) - (parseFloat(a.prize_pool) || 0));
        } else if (currentSort === 'deadline') {
            filtered.sort((a, b) => new Date(a.deadline || '2099-12-31') - new Date(b.deadline || '2099-12-31'));
        } else if (currentSort === 'participants') {
            filtered.sort((a, b) => (parseInt(b.participants) || 0) - (parseInt(a.participants) || 0));
        }

        setFilteredHackathons(filtered);
        // Show all filtered hackathons (no pagination)
        setDisplayedCount(filtered.length);
    }, [hackathons, selectedSources, allSources.length, currentFilter, currentSort, searchQuery, locationFilter]);

    // Load more
    const loadMore = useCallback(() => {
        setDisplayedCount(prev => Math.min(prev + ITEMS_PER_LOAD, filteredHackathons.length));
    }, [filteredHackathons.length]);

    // Get displayed hackathons
    const displayedHackathons = filteredHackathons.slice(0, displayedCount);
    const hasMore = displayedCount < filteredHackathons.length;

    return {
        hackathons: displayedHackathons,
        totalCount: filteredHackathons.length,
        isLoading,
        hasMore,
        loadMore,
        // Filters
        currentFilter,
        setCurrentFilter,
        currentSort,
        setCurrentSort,
        searchQuery,
        setSearchQuery,
        locationFilter,
        setLocationFilter,
        // Sources
        allSources,
        selectedSources,
        setSelectedSources,
    };
}
