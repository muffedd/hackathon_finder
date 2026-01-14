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
    isLoading: true,
    bookmarks: new Set(JSON.parse(localStorage.getItem('bookmarks') || '[]')),
    selectedSources: new Set(), // Will be filled in init
    allSources: []
};

// ... (lines 26-518 unchanged)

function initializeSourceFilter() {
    // Extract unique sources from hackathons
    state.allSources = [...new Set(state.hackathons.map(h => h.source))].sort();

    console.log('All sources:', state.allSources);

    // Always default to ALL sources on refresh (remove local storage persistence for sources)
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
    clearAllSources: document.getElementById('clearAllSources')
};

// === Init ===
document.addEventListener('DOMContentLoaded', init);

async function init() {
    showLoading(true);

    try {
        const response = await fetch(`${API_BASE}/hackathons`);
        if (response.ok) {
            state.hackathons = await response.json();
            console.log(`Loaded ${state.hackathons.length} hackathons from API`);
        } else {
            throw new Error('API failed');
        }
    } catch (error) {
        console.log('API not available, no data to show');
        state.hackathons = [];
    }

    // Initialize source filter
    initializeSourceFilter();

    applyFiltersAndSort();
    bindEvents();

    setTimeout(() => {
        showLoading(false);
        renderHackathons();
    }, 500);
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
        if (remaining > 0) {
            isLoadingMore = true;
            renderHackathons(true);
            isLoadingMore = false;
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

function applyFiltersAndSort() {
    let filtered = [...state.hackathons];

    if (state.searchQuery) {
        const q = state.searchQuery.toLowerCase();
        filtered = filtered.filter(h =>
            (h.title || '').toLowerCase().includes(q) ||
            (h.description || '').toLowerCase().includes(q) ||
            (h.location || '').toLowerCase().includes(q) ||
            (h.source || '').toLowerCase().includes(q) ||
            (h.tags || []).some(t => t.toLowerCase().includes(q))
        );
    }

    // Apply source filter
    if (state.selectedSources.size > 0 && state.selectedSources.size < state.allSources.length) {
        filtered = filtered.filter(h => state.selectedSources.has(h.source));
    }

    // Apply filters with client-side status calculation
    switch (state.currentFilter) {
        case 'upcoming':
            filtered = filtered.filter(h => calculateStatus(h) === 'upcoming');
            break;
        case 'ongoing':
            filtered = filtered.filter(h => calculateStatus(h) === 'ongoing');
            break;
        case 'online':
            filtered = filtered.filter(h => {
                const mode = (h.mode || '').toLowerCase();
                return mode === 'online' || mode.includes('online');
            });
            break;
        case 'in-person':
            filtered = filtered.filter(h => {
                const mode = (h.mode || '').toLowerCase();
                return mode === 'in-person' || mode.includes('in-person') || mode.includes('in person');
            });
            break;
    }

    switch (state.currentSort) {
        case 'latest': filtered.sort((a, b) => new Date(b.start_date || 0) - new Date(a.start_date || 0)); break;
        case 'deadline': filtered.sort((a, b) => new Date(a.start_date || 0) - new Date(b.start_date || 0)); break;
        case 'prize': filtered.sort((a, b) => (b.prize_pool_numeric || 0) - (a.prize_pool_numeric || 0)); break;
        case 'title': filtered.sort((a, b) => (a.title || '').localeCompare(b.title || '')); break;
    }

    state.filteredHackathons = filtered;
    state.displayedCount = 0;
    updateResultsCount();
}

function handleSearch() {
    state.searchQuery = elements.searchInput?.value.trim() || '';
    applyFiltersAndSort();
    renderHackathons();
}

function handleFilterChange(pill) {
    elements.filterPills.forEach(p => p.classList.remove('active'));
    pill.classList.add('active');
    state.currentFilter = pill.dataset.filter;

    console.log(`Filter changed to: ${state.currentFilter}`);
    console.log(`Total hackathons before filter: ${state.hackathons.length}`);

    applyFiltersAndSort();

    console.log(`Filtered hackathons: ${state.filteredHackathons.length}`);
    if (state.currentFilter === 'in-person') {
        console.log('In-person filter samples:', state.filteredHackathons.slice(0, 5).map(h => ({
            title: h.title,
            mode: h.mode
        })));
    }

    renderHackathons();
}

function handleSortChange(opt) {
    elements.sortOptions.forEach(o => o.classList.remove('active'));
    opt.classList.add('active');
    state.currentSort = opt.dataset.sort;
    elements.sortBtn.querySelector('span').textContent = `Sort: ${opt.textContent}`;
    elements.sortDropdown?.classList.remove('open');
    applyFiltersAndSort();
    renderHackathons();
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

    if (remaining > 0) {
        container.style.display = 'flex';
        container.innerHTML = `
            <div class="scroll-indicator">
                <span class="loading-spinner"></span>
                Showing ${state.displayedCount} of ${state.filteredHackathons.length} • Scroll for more
            </div>
        `;
    } else {
        container.style.display = state.displayedCount > 0 ? 'flex' : 'none';
        container.innerHTML = state.displayedCount > 0 ? `<span class="all-loaded">All ${state.displayedCount} hackathons loaded</span>` : '';
    }
}

function loadMore() {
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

function initializeSourceFilter() {
    // Extract unique sources from hackathons
    state.allSources = [...new Set(state.hackathons.map(h => h.source))].sort();

    console.log('All sources:', state.allSources);
    console.log('Selected sources from localStorage:', [...state.selectedSources]);

    // Validate selectedSources - remove any that don't exist in current data
    const validSelectedSources = [...state.selectedSources].filter(s => state.allSources.includes(s));

    // If no valid sources selected or localStorage was empty, select all by default
    if (validSelectedSources.length === 0) {
        state.selectedSources = new Set(state.allSources);
        localStorage.setItem('selectedSources', JSON.stringify([...state.selectedSources]));
        console.log('Initialized with all sources:', [...state.selectedSources]);
    } else {
        // Update to only valid sources
        state.selectedSources = new Set(validSelectedSources);
        localStorage.setItem('selectedSources', JSON.stringify([...state.selectedSources]));
        console.log('Using validated sources:', [...state.selectedSources]);
    }

    // Generate checkboxes
    renderSourceCheckboxes();
    updateSourceCount();
}

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
