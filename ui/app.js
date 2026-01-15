/**
 * HackFind - Frontend Application
 * ================================
 * - Clean card design
 * - Infinite scroll (loads 100 at a time)
 * - All hackathons from database
 */

const API_BASE = '/api';
const ITEMS_PER_LOAD = 100;
let isLoadingMore = false;

let state = {
    hackathons: [],
    filteredHackathons: [],
    displayedCount: 0,
    currentFilter: 'all',  // Default to all
    currentSort: 'prize',
    searchQuery: '',
    locationFilter: '', // Location filter text
    isLoading: true,
    bookmarks: new Set(JSON.parse(localStorage.getItem('bookmarks') || '[]')),
    selectedSources: new Set(), // Will be filled in init
    allSources: []
};

// ... (lines 26-518 unchanged)

async function initializeSourceFilter() {
    // Fetch all sources from API (ensures we show all sources, not just loaded ones)
    try {
        const response = await fetch(`${API_BASE}/sources`);
        if (response.ok) {
            const data = await response.json();
            state.allSources = data.sources || [];
        }
    } catch (e) {
        // Fallback: extract from loaded events
        state.allSources = [...new Set(state.hackathons.map(h => h.source).filter(Boolean))].sort();
    }

    console.log('All sources:', state.allSources);

    // Always default to ALL sources on refresh
    state.selectedSources = new Set(state.allSources);
    console.log('Initialized with all sources');

    // Generate checkboxes
    renderSourceCheckboxes();
    updateSourceCount();
}

const elements = {
    searchInput: document.getElementById('searchInput'),
    searchBtn: document.getElementById('searchBtn'),
    sortBtn: document.getElementById('sortBtn'),
    sortMenu: document.getElementById('sortMenu'),
    bentoGrid: document.getElementById('bentoGrid'),
    loadingState: document.getElementById('loadingState'),
    emptyState: document.getElementById('emptyState'),
    resultsCount: document.getElementById('resultsCount'),
    filterPills: document.querySelectorAll('.filter-pill'),
    sortOptions: document.querySelectorAll('.sort-option'),
    sortDropdown: document.querySelector('.sort-dropdown'),
    sourceFilterToggle: document.getElementById('sourceFilterToggle'),
    sourceFilterPanel: document.getElementById('sourceFilterPanel'),
    sourceCheckboxes: document.getElementById('sourceCheckboxes'),
    sourceCount: document.getElementById('sourceCount'),
    selectAllSources: document.getElementById('selectAllSources'),
    clearAllSources: document.getElementById('clearAllSources'),
    // Location filter
    locationInput: document.getElementById('locationInput'),
    nearbyBtn: document.getElementById('nearbyBtn'),
    // AI Search
    aiSearchInput: document.getElementById('aiSearchInput'),
    aiSearchBtn: document.getElementById('aiSearchBtn'),
    aiThinking: document.getElementById('aiThinking'),
    aiResults: document.getElementById('aiResults')
};

// === Init ===
document.addEventListener('DOMContentLoaded', init);

async function init() {
    showLoading(true);

    try {
        // Fetch first page only (fast initial load)
        const response = await fetch(`${API_BASE}/hackathons?page=1&page_size=50&sort_by=prize`);
        if (response.ok) {
            const data = await response.json();
            state.hackathons = data.events || [];
            state.totalEvents = data.total || 0;
            state.currentPage = data.page || 1;
            state.totalPages = data.total_pages || 1;
            console.log(`Loaded ${state.hackathons.length}/${state.totalEvents} hackathons (Page 1)`);
        } else {
            throw new Error('API failed');
        }
    } catch (error) {
        console.log('API not available:', error);
        state.hackathons = [];
    }

    // Initialize source filter (fetches all sources from API)
    await initializeSourceFilter();

    // For paginated API, filtered = all loaded events
    state.filteredHackathons = state.hackathons;
    bindEvents();

    showLoading(false);
    renderHackathons();
}

function bindEvents() {
    elements.searchInput?.addEventListener('input', debounce(handleSearch, 300));
    elements.searchBtn?.addEventListener('click', handleSearch);
    elements.searchInput?.addEventListener('keypress', e => { if (e.key === 'Enter') handleSearch(); });

    elements.filterPills.forEach(pill => pill.addEventListener('click', () => handleFilterChange(pill)));

    elements.sortBtn?.addEventListener('click', toggleSortMenu);
    elements.sortOptions.forEach(opt => opt.addEventListener('click', () => handleSortChange(opt)));

    document.addEventListener('click', e => {
        if (!elements.sortDropdown?.contains(e.target)) {
            elements.sortDropdown?.classList.remove('open');
        }
    });

    // Source filter events
    elements.sourceFilterToggle?.addEventListener('click', toggleSourceFilter);
    elements.selectAllSources?.addEventListener('click', selectAllSources);
    elements.clearAllSources?.addEventListener('click', clearAllSources);

    // Location filter events
    elements.locationInput?.addEventListener('input', debounce(handleLocationFilter, 500));
    elements.locationInput?.addEventListener('keypress', e => { if (e.key === 'Enter') handleLocationFilter(); });
    elements.nearbyBtn?.addEventListener('click', handleNearbyEvents);

    // AI Search events - get elements directly since they may not be in cache
    const aiSearchBtn = document.getElementById('aiSearchBtn');
    const aiSearchInput = document.getElementById('aiSearchInput');

    if (aiSearchBtn) {
        aiSearchBtn.addEventListener('click', handleAISearch);
        console.log('AI Search button event bound');
    } else {
        console.warn('AI Search button not found');
    }

    if (aiSearchInput) {
        aiSearchInput.addEventListener('keypress', e => {
            if (e.key === 'Enter') handleAISearch();
        });
    }

    // Infinite scroll
    window.addEventListener('scroll', debounce(handleScroll, 100));
}

function handleScroll() {
    if (isLoadingMore) return;

    const scrollY = window.scrollY;
    const windowHeight = window.innerHeight;
    const docHeight = document.documentElement.scrollHeight;

    // Load more when 300px from bottom
    if (scrollY + windowHeight >= docHeight - 300) {
        const remaining = state.filteredHackathons.length - state.displayedCount;
        const hasMorePages = state.currentPage < state.totalPages;

        if (remaining > 0 || hasMorePages) {
            loadMore(); // This is async, will fetch next page if needed
        }
    }
}

// === Filtering & Sorting ===
function calculateStatus(hackathon) {
    /**
     * Calculate hackathon status based on current date (client-side)
     * This ensures filters work correctly without database updates
     */
    if (!hackathon.start_date) {
        return 'unknown';
    }

    const today = new Date();
    today.setHours(0, 0, 0, 0); // Reset to start of day for accurate comparison

    try {
        const startDate = new Date(hackathon.start_date);
        const endDate = hackathon.end_date ? new Date(hackathon.end_date) : startDate;

        if (today < startDate) {
            return 'upcoming';
        } else if (today >= startDate && today <= endDate) {
            return 'ongoing';
        } else {
            return 'ended';
        }
    } catch (e) {
        return 'unknown';
    }
}

async function fetchFilteredEvents() {
    /**
     * HYBRID APPROACH: Fetch events from server with filter params
     * This ensures filters work correctly across ALL events, not just loaded ones.
     */
    showLoading(true);

    // Build query params based on current filters
    const params = new URLSearchParams();
    params.set('page', '1');
    params.set('page_size', '100'); // Fetch more when filtering
    params.set('sort_by', state.currentSort === 'deadline' ? 'date' : state.currentSort);

    // Status filter
    if (state.currentFilter === 'upcoming' || state.currentFilter === 'ongoing') {
        params.set('status', state.currentFilter);
    }

    // Mode filter
    if (state.currentFilter === 'online') {
        params.set('mode', 'online');
    } else if (state.currentFilter === 'in-person') {
        params.set('mode', 'offline');
    }

    // Search query
    if (state.searchQuery) {
        params.set('search', state.searchQuery);
    }

    // Source filter (if not all selected)
    if (state.selectedSources.size > 0 && state.selectedSources.size < state.allSources.length) {
        // API doesn't support multiple sources, so we'll filter client-side for sources
        // But we still fetch server-filtered data for other filters
    }

    try {
        const response = await fetch(`${API_BASE}/hackathons?${params.toString()}`);
        if (response.ok) {
            const data = await response.json();
            state.hackathons = data.events || [];
            state.totalEvents = data.total || 0;
            state.currentPage = data.page || 1;
            state.totalPages = data.total_pages || 1;
            console.log(`Fetched ${state.hackathons.length}/${state.totalEvents} filtered events`);
        }
    } catch (e) {
        console.error('Filter fetch failed:', e);
    }

    // Apply source filter client-side (API doesn't support multiple sources)
    let filtered = [...state.hackathons];
    if (state.selectedSources.size > 0 && state.selectedSources.size < state.allSources.length) {
        filtered = filtered.filter(h => state.selectedSources.has(h.source));
    }

    state.filteredHackathons = filtered;
    state.displayedCount = 0;

    showLoading(false);
    updateResultsCount();
    renderHackathons();
}

function applyFiltersAndSort() {
    // Client-side only filtering for source (since it's multi-select)
    let filtered = [...state.hackathons];

    // Apply source filter
    if (state.selectedSources.size > 0 && state.selectedSources.size < state.allSources.length) {
        filtered = filtered.filter(h => state.selectedSources.has(h.source));
    }

    state.filteredHackathons = filtered;
    state.displayedCount = 0;
    updateResultsCount();
}

function handleSearch() {
    state.searchQuery = elements.searchInput?.value.trim() || '';
    fetchFilteredEvents(); // Call API with search param
}

function handleFilterChange(pill) {
    elements.filterPills.forEach(p => p.classList.remove('active'));
    pill.classList.add('active');
    state.currentFilter = pill.dataset.filter;
    console.log(`Filter changed to: ${state.currentFilter}`);
    fetchFilteredEvents(); // Call API with filter param
}

// === Location Filter ===
function handleLocationFilter() {
    state.locationFilter = elements.locationInput?.value.trim() || '';
    console.log(`Location filter: ${state.locationFilter}`);

    if (state.locationFilter) {
        // Filter locally for matching locations
        const loc = state.locationFilter.toLowerCase();
        const filtered = state.hackathons.filter(h =>
            (h.location || '').toLowerCase().includes(loc)
        );
        state.filteredHackathons = filtered;
        state.displayedCount = 0;
        updateResultsCount();
        renderHackathons();
    } else {
        // Clear location filter - reset to all loaded events
        state.filteredHackathons = state.hackathons;
        state.displayedCount = 0;
        updateResultsCount();
        renderHackathons();
    }
}

async function handleNearbyEvents() {
    const btn = elements.nearbyBtn;
    if (!btn) return;

    btn.classList.add('loading');

    if (!navigator.geolocation) {
        alert('Geolocation is not supported by your browser');
        btn.classList.remove('loading');
        return;
    }

    try {
        const position = await new Promise((resolve, reject) => {
            navigator.geolocation.getCurrentPosition(resolve, reject, {
                enableHighAccuracy: false,
                timeout: 10000,
                maximumAge: 300000 // Cache for 5 minutes
            });
        });

        const { latitude, longitude } = position.coords;
        console.log(`User location: ${latitude}, ${longitude}`);

        // Use Nominatim reverse geocoding (free, no API key needed)
        const geoResponse = await fetch(
            `https://nominatim.openstreetmap.org/reverse?format=json&lat=${latitude}&lon=${longitude}&zoom=10`,
            { headers: { 'Accept-Language': 'en' } }
        );

        if (geoResponse.ok) {
            const geoData = await geoResponse.json();
            const address = geoData.address || {};
            // Get district/city level
            const district = address.county || address.city || address.state_district ||
                address.town || address.municipality || address.suburb || '';
            const city = address.city || address.town || '';
            const state = address.state || '';

            const locationText = district || city || state || 'Unknown';
            console.log(`Detected location: ${locationText}`);

            // Update input field and filter
            if (elements.locationInput) {
                elements.locationInput.value = locationText;
            }
            state.locationFilter = locationText;
            handleLocationFilter();
        }
    } catch (error) {
        console.error('Geolocation error:', error);
        if (error.code === 1) {
            alert('Location access denied. Please enable location permissions or enter location manually.');
        } else {
            alert('Could not get your location. Please enter location manually.');
        }
    }

    btn.classList.remove('loading');
}

// === AI Search with Thinking Process ===
async function handleAISearch() {
    // Get input directly from DOM in case elements cache is stale
    const inputEl = document.getElementById('aiSearchInput');
    const query = inputEl?.value?.trim();

    if (!query) {
        alert('Please enter a search query (e.g., \'hackathons for beginners in India\').');
        return;
    }

    // Get all elements directly from DOM (cache may be stale)
    const btn = document.getElementById('aiSearchBtn');
    const thinkingEl = document.getElementById('aiThinking');
    const resultsEl = document.getElementById('aiResults');

    // Reset and show thinking
    btn?.classList.add('loading');
    if (thinkingEl) {
        thinkingEl.style.display = 'block';
        thinkingEl.querySelectorAll('.thinking-step').forEach(s => {
            s.classList.remove('active', 'done');
        });
    }
    if (resultsEl) {
        resultsEl.style.display = 'none';
        resultsEl.innerHTML = '';
    }

    // Animate thinking steps
    const steps = thinkingEl?.querySelectorAll('.thinking-step');
    const activateStep = async (index) => {
        if (steps && steps[index]) {
            if (index > 0 && steps[index - 1]) {
                steps[index - 1].classList.remove('active');
                steps[index - 1].classList.add('done');
            }
            steps[index].classList.add('active');
        }
        await new Promise(r => setTimeout(r, 600));
    };

    try {
        await activateStep(0); // Understanding query
        await activateStep(1); // Searching hackathons

        const response = await fetch(`${API_BASE}/search/ai?q=${encodeURIComponent(query)}`);

        await activateStep(2); // Analyzing matches

        if (response.ok) {
            const results = await response.json();
            await activateStep(3); // Generating recommendations

            // Mark all done
            steps?.forEach(s => {
                s.classList.remove('active');
                s.classList.add('done');
            });

            // Show results (limit to 4)
            const topResults = Array.isArray(results) ? results.slice(0, 4) : [];
            displayAIResults(topResults, query);
        } else {
            const error = await response.json();
            throw new Error(error.error || 'AI search failed');
        }
    } catch (error) {
        console.error('AI Search error:', error);
        if (resultsEl) {
            resultsEl.style.display = 'block';
            resultsEl.innerHTML = `<div class="ai-error">Error: ${error.message}</div>`;
        }
    }

    btn?.classList.remove('loading');
    setTimeout(() => {
        if (thinkingEl) thinkingEl.style.display = 'none';
    }, 1000);
}

function displayAIResults(results, query) {
    const container = elements.aiResults;
    if (!container) return;

    if (results.length === 0) {
        container.innerHTML = '<div class="ai-no-results">No matching hackathons found. Try a different query.</div>';
        container.style.display = 'block';
        return;
    }

    container.innerHTML = `
        <div class="ai-results-header">
            <h3>Top ${results.length} Recommendations</h3>
            <p class="ai-query-echo">Based on: "${query}"</p>
        </div>
        <div class="ai-results-grid">
            ${results.map(h => `
                <div class="ai-result-card">
                    <div class="ai-result-header">
                        <span class="ai-result-source">${h.source || 'Unknown'}</span>
                        <span class="ai-result-prize">${h.prize_pool || 'Prize TBD'}</span>
                    </div>
                    <h4 class="ai-result-title">${h.title || 'Untitled'}</h4>
                    ${h.ai_reason ? `<p class="ai-result-reason">${h.ai_reason}</p>` : ''}
                    <div class="ai-result-meta">
                        <span>${h.mode || 'TBD'}</span>
                        <span>${h.location || 'Online'}</span>
                    </div>
                    <a href="${h.url || '#'}" target="_blank" class="ai-result-cta">View Details</a>
                </div>
            `).join('')}
        </div>
    `;
    container.style.display = 'block';
}

function handleSortChange(opt) {
    elements.sortOptions.forEach(o => o.classList.remove('active'));
    opt.classList.add('active');
    state.currentSort = opt.dataset.sort;
    elements.sortBtn.querySelector('span').textContent = `Sort: ${opt.textContent}`;
    elements.sortDropdown?.classList.remove('open');
    fetchFilteredEvents(); // Call API with sort param
}

function toggleSortMenu(e) {
    e.stopPropagation();
    elements.sortDropdown?.classList.toggle('open');
}

function toggleBookmark(e, id) {
    e.stopPropagation();
    const btn = e.currentTarget;
    if (state.bookmarks.has(id)) {
        state.bookmarks.delete(id);
        btn.classList.remove('active');
    } else {
        state.bookmarks.add(id);
        btn.classList.add('active');
    }
    localStorage.setItem('bookmarks', JSON.stringify([...state.bookmarks]));
}

// === Rendering ===
function renderHackathons(append = false) {
    if (!append) {
        state.displayedCount = 0;
        elements.bentoGrid.innerHTML = '';
    }

    const items = state.filteredHackathons.slice(state.displayedCount, state.displayedCount + ITEMS_PER_LOAD);

    if (items.length === 0 && state.displayedCount === 0) {
        elements.emptyState?.classList.remove('hidden');
        document.getElementById('paginationContainer').style.display = 'none';
        return;
    }

    elements.emptyState?.classList.add('hidden');

    const html = items.map(h => createCard(h)).join('');
    elements.bentoGrid.insertAdjacentHTML('beforeend', html);

    state.displayedCount += items.length;

    // Bind new card events (card click does nothing, only CTA button redirects)
    document.querySelectorAll('.bento-card:not([data-bound])').forEach(card => {
        card.dataset.bound = 'true';
    });

    document.querySelectorAll('.bento-bookmark:not([data-bound])').forEach(btn => {
        btn.dataset.bound = 'true';
        btn.addEventListener('click', e => toggleBookmark(e, btn.dataset.id));
    });

    // CTA button redirects to hackathon URL
    document.querySelectorAll('.bento-cta:not([data-bound])').forEach(btn => {
        btn.dataset.bound = 'true';
        btn.addEventListener('click', e => {
            e.stopPropagation();
            const card = btn.closest('.bento-card');
            const url = card?.dataset.url;
            if (url && url.startsWith('http')) window.open(url, '_blank', 'noopener');
        });
    });

    renderLoadMore();
}

function renderLoadMore() {
    const container = document.getElementById('paginationContainer');
    const remaining = state.filteredHackathons.length - state.displayedCount;
    const hasMorePages = state.currentPage < state.totalPages;

    if (remaining > 0 || hasMorePages) {
        container.style.display = 'flex';
        const totalLoaded = state.hackathons.length;
        const totalAvailable = state.totalEvents || totalLoaded;
        container.innerHTML = `
            <div class="scroll-indicator">
                <span class="loading-spinner"></span>
                Showing ${state.displayedCount} of ${totalAvailable} • ${hasMorePages ? 'Scroll for more' : 'All loaded'}
            </div>
        `;
    } else {
        container.style.display = state.displayedCount > 0 ? 'flex' : 'none';
        container.innerHTML = state.displayedCount > 0 ? `<span class="all-loaded">All ${state.displayedCount} hackathons loaded</span>` : '';
    }
}

async function loadMore() {
    if (isLoadingMore) return;

    // If we've displayed all loaded events and there are more pages, fetch next page
    if (state.displayedCount >= state.filteredHackathons.length && state.currentPage < state.totalPages) {
        isLoadingMore = true;
        try {
            const nextPage = state.currentPage + 1;
            const response = await fetch(`${API_BASE}/hackathons?page=${nextPage}&page_size=50&sort_by=${state.currentSort}`);
            if (response.ok) {
                const data = await response.json();
                const newEvents = data.events || [];
                state.hackathons = [...state.hackathons, ...newEvents];
                state.filteredHackathons = [...state.filteredHackathons, ...newEvents];
                state.currentPage = data.page;
                console.log(`Loaded page ${nextPage}: ${newEvents.length} more events`);
            }
        } catch (e) {
            console.error('Failed to load more:', e);
        }
        isLoadingMore = false;
    }

    renderHackathons(true);
}

function createCard(h) {
    const isBookmarked = state.bookmarks.has(h.id);
    const location = getLocation(h.location);

    // Determine mode
    let mode = h.mode || 'unknown';
    const locLower = location.toLowerCase();
    if (locLower === 'online' || locLower === 'virtual' || locLower === 'remote' || locLower.includes('online')) {
        mode = 'online';
    }

    // Hide location if it's redundant (e.g. "Online" mode and location "Online")
    const isLocationRedundant = mode === 'online' &&
        ['online', 'virtual', 'remote'].includes(location.toLowerCase());

    // Parse date for calendar badge
    const dateObj = h.end_date ? new Date(h.end_date) : null;
    const month = dateObj ? dateObj.toLocaleDateString('en-US', { month: 'short' }).toUpperCase() : 'TBA';
    const day = dateObj ? dateObj.getDate() : '--';

    // Prize display logic
    const getPrizeDisplay = () => {
        const prize = h.prize_pool;
        if (!prize) return { text: 'Prize TBD', class: 'tbd' };
        const isMonetary = /^[\$€£¥₹][\d,]+/.test(prize);
        if (isMonetary) return { text: prize, class: '' };
        const isZeroValue = prize.match(/^[\$€£¥₹]?0(\.0+)?$/);
        if (isZeroValue) return { text: 'Prize TBD', class: 'tbd' };
        return { text: 'Non-Cash Prize', class: 'non-cash' };
    };
    const prizeInfo = getPrizeDisplay();

    // Stats section
    const getStatsHtml = () => {
        let stats = [];
        const count = parseInt(h.participants_count || 0);
        const status = calculateStatus(h);

        if (status === 'upcoming' && count === 0) {
            stats.push(`<span class="bento-stat"><span class="stat-icon">⏳</span>Upcoming</span>`);
        } else if (count > 0) {
            stats.push(`<span class="bento-stat"><span class="stat-icon">👥</span>${count.toLocaleString()}</span>`);
        }

        if (h.team_size_min || h.team_size_max) {
            let teamText;
            if (h.team_size_min && h.team_size_max) {
                teamText = h.team_size_min === h.team_size_max
                    ? (h.team_size_max === 1 ? 'Solo' : `Team: ${h.team_size_max}`)
                    : `Team: ${h.team_size_min}-${h.team_size_max}`;
            } else {
                const size = h.team_size_max || h.team_size_min;
                teamText = size === 1 ? 'Solo' : `Team: ${size}`;
            }
            stats.push(`<span class="bento-stat"><span class="stat-icon">👤</span>${teamText}</span>`);
        }

        return stats.join('');
    };

    // Format mode display (in-person -> Offline)
    const formatMode = (m) => {
        if (!m) return 'Unknown';
        if (m.toLowerCase() === 'in-person') return 'Offline';
        return m.charAt(0).toUpperCase() + m.slice(1);
    };

    // Get source initial
    // Get source logo
    const renderSourceIcon = (source) => {
        if (!source) return '?';
        const domains = {
            'Devpost': 'devpost.com', 'Devfolio': 'devfolio.co', 'Unstop': 'unstop.com',
            'MLH': 'mlh.io', 'DoraHacks': 'dorahacks.io', 'Kaggle': 'kaggle.com',
            'HackerEarth': 'hackerearth.com', 'Superteam': 'superteam.fun',
            'HackQuest': 'hackquest.io', 'DevDisplay': 'devdisplay.org',
            'HackCulture': 'hackculture.com', 'MyCareerNet': 'mycareernet.in',
            'Lisk': 'lisk.com', 'ETHGlobal': 'ethglobal.com', 'Taikai': 'taikai.network',
            'Hack2Skill': 'hack2skill.com'
        };

        const domain = domains[source];
        if (domain) {
            return `<img src="https://www.google.com/s2/favicons?domain=${domain}&sz=64" alt="${source}" onerror="this.outerHTML='${source.charAt(0)}'">`;
        }
        return source.charAt(0).toUpperCase();
    };

    return `
        <article class="bento-card" data-url="${h.url || '#'}">
            <!-- Calendar Badge -->
            <div class="bento-calendar">
                <div class="calendar-month">${month}</div>
                <div class="calendar-day">${day}</div>
            </div>

            <!-- Source Icon -->
            <div class="bento-source-icon" title="${h.source || 'Unknown'}">
                ${renderSourceIcon(h.source)}
            </div>

            <!-- Content -->
            <div class="bento-content">
                <h3 class="bento-title">${h.title || 'Untitled'}</h3>
                ${h.ai_reason ? `<div class="ai-reason">${h.ai_reason}</div>` : ''}
                
                <div class="bento-mode-row">
                    <span class="bento-mode ${mode}">${formatMode(mode)}</span>
                    ${!isLocationRedundant ? `<span class="bento-location">${location}</span>` : ''}
                </div>

                <div class="bento-prize ${prizeInfo.class}">${prizeInfo.text}</div>

                <div class="bento-stats-row">
                    ${getStatsHtml()}
                </div>

                ${h.tags?.length ? `<div class="bento-tags">${h.tags.slice(0, 3).map(t => `<span class="bento-tag">${t}</span>`).join('')}</div>` : ''}
            </div>

            <!-- Divider -->
            <div class="bento-divider"></div>

            <!-- Footer -->
            <div class="bento-footer">
                <button class="bento-cta">View Details</button>
                <button class="bento-bookmark ${isBookmarked ? 'active' : ''}" data-id="${h.id}">
                    ${isBookmarked ? '★' : '☆'}
                </button>
            </div>
        </article>
    `;
}

function getLocation(loc) {
    if (!loc) return 'TBA';

    // If it's already a clean string
    if (typeof loc === 'string') {
        // Check if it's a stringified dict like "{'icon': 'globe', 'location': 'Online'}"
        if (loc.includes("'location':") || loc.includes('"location":')) {
            // Extract the location value using regex
            const match = loc.match(/['"]location['"]\s*:\s*['"]([^'"]+)['"]/);
            if (match) return match[1];
        }
        // Check for other patterns
        if (loc.includes("'name':") || loc.includes('"name":')) {
            const match = loc.match(/['"]name['"]\s*:\s*['"]([^'"]+)['"]/);
            if (match) return match[1];
        }
        // If it starts with { it's probably a stringified object
        if (loc.startsWith('{')) {
            // Try to extract any meaningful location-like value
            const match = loc.match(/['"]([^'"]+)['"](?:\s*}|\s*,\s*['"]icon)/);
            if (match && match[1] !== 'globe' && match[1] !== 'location') return match[1];
        }
        return loc;
    }

    // If it's an actual object
    if (typeof loc === 'object') {
        if (loc.location) return loc.location;
        if (loc.name) return loc.name;
        if (loc.city) return loc.city;
        const values = Object.values(loc).filter(v => typeof v === 'string' && v.length > 1);
        return values[0] || 'TBA';
    }

    return String(loc);
}

// === Helpers ===
function showLoading(show) {
    state.isLoading = show;
    if (elements.loadingState) elements.loadingState.style.display = show ? 'block' : 'none';
    if (elements.bentoGrid) elements.bentoGrid.style.display = show ? 'none' : 'grid';
}

function updateResultsCount() {
    if (elements.resultsCount) {
        elements.resultsCount.textContent = `${state.filteredHackathons.length} hackathons`;
    }
}

function formatDate(d) {
    if (!d) return 'TBA';
    try {
        return new Date(d).toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' });
    } catch { return 'TBA'; }
}

function formatDateRange(startDate, endDate) {
    if (!startDate) return 'TBA';

    const start = formatDate(startDate);

    if (!endDate || endDate === startDate) {
        return start;
    }

    const end = formatDate(endDate);
    return `${start} - ${end}`;
}

function formatPrize(prizePool) {
    if (!prizePool) return null;

    const prizeStr = String(prizePool).trim();

    // If it already has a currency symbol, return as is
    if (/^[\$€£¥₹]/.test(prizeStr) || /USD|EUR|INR|GBP/.test(prizeStr)) {
        return prizeStr;
    }

    // If it's just a number, add $ symbol
    if (/^[\d,]+$/.test(prizeStr)) {
        return `$${prizeStr}`;
    }

    // Otherwise return as is
    return prizeStr;
}

function capitalize(s) {
    return s ? s.charAt(0).toUpperCase() + s.slice(1) : '';
}

function debounce(fn, wait) {
    let t;
    return (...args) => { clearTimeout(t); t = setTimeout(() => fn(...args), wait); };
}

function resetFilters() {
    state.currentFilter = 'all';
    state.searchQuery = '';
    if (elements.searchInput) elements.searchInput.value = '';
    elements.filterPills.forEach(p => p.classList.toggle('active', p.dataset.filter === 'all'));
    applyFiltersAndSort();
    renderHackathons();
}

window.loadMore = loadMore;
window.resetFilters = resetFilters;


// === Source Filter Functions ===
// initializeSourceFilter is defined at the top of the file (async version that fetches from API)

function renderSourceCheckboxes() {
    if (!elements.sourceCheckboxes) return;

    elements.sourceCheckboxes.innerHTML = state.allSources.map(source => `
        <label class="source-checkbox-item">
            <input 
                type="checkbox" 
                value="${source}" 
                ${state.selectedSources.has(source) ? 'checked' : ''}
                onchange="handleSourceChange(this)"
            />
            <label>${source}</label>
        </label>
    `).join('');
}

function toggleSourceFilter() {
    elements.sourceFilterToggle?.classList.toggle('active');
    elements.sourceFilterPanel?.classList.toggle('active');
}

function handleSourceChange(checkbox) {
    const source = checkbox.value;

    if (checkbox.checked) {
        state.selectedSources.add(source);
    } else {
        state.selectedSources.delete(source);
    }

    // Save to localStorage
    localStorage.setItem('selectedSources', JSON.stringify([...state.selectedSources]));

    // Update UI and re-filter
    updateSourceCount();
    applyFiltersAndSort();
    renderHackathons();
}

function selectAllSources() {
    state.selectedSources = new Set(state.allSources);
    localStorage.setItem('selectedSources', JSON.stringify([...state.selectedSources]));
    renderSourceCheckboxes();
    updateSourceCount();
    applyFiltersAndSort();
    renderHackathons();
}

function clearAllSources() {
    state.selectedSources.clear();
    localStorage.setItem('selectedSources', JSON.stringify([]));
    renderSourceCheckboxes();
    updateSourceCount();
    applyFiltersAndSort();
    renderHackathons();
}

function updateSourceCount() {
    if (elements.sourceCount) {
        elements.sourceCount.textContent = `(${state.selectedSources.size}/${state.allSources.length})`;
    }
}

// Make handleSourceChange global
window.handleSourceChange = handleSourceChange;
// Make handleSourceChange global
window.handleSourceChange = handleSourceChange;
