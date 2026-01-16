// Format date for display
export function formatDate(d) {
    if (!d) return 'TBD';
    const date = new Date(d);
    if (isNaN(date.getTime())) return 'TBD';
    return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' });
}

// Format date range
export function formatDateRange(startDate, endDate) {
    if (!startDate && !endDate) return 'Dates TBD';
    if (!startDate) return `Until ${formatDate(endDate)}`;
    if (!endDate) return `From ${formatDate(startDate)}`;

    const start = new Date(startDate);
    const end = new Date(endDate);

    if (start.getFullYear() === end.getFullYear() && start.getMonth() === end.getMonth()) {
        return `${start.toLocaleDateString('en-US', { month: 'short', day: 'numeric' })} - ${end.getDate()}, ${end.getFullYear()}`;
    }
    return `${formatDate(startDate)} - ${formatDate(endDate)}`;
}

// Format prize amount
export function formatPrize(prizePool) {
    if (!prizePool || prizePool === 0) return null;

    const num = parseFloat(prizePool);
    if (isNaN(num) || num <= 0) return null;

    // Format with commas
    const formatted = num.toLocaleString('en-US', { maximumFractionDigits: 0 });

    // Determine currency (default to $)
    return `$${formatted}`;
}

// Get location string
export function getLocation(loc) {
    if (!loc) return null;
    if (typeof loc === 'string') {
        // Check if it's a stringified object like "{'icon': 'globe', 'location': 'Online'}"
        if (loc.startsWith('{') && loc.includes(':')) {
            try {
                // Replace single quotes with double quotes for valid JSON
                const parsed = JSON.parse(loc.replace(/'/g, '"'));
                if (parsed.location) return parsed.location;
                if (parsed.city) return [parsed.city, parsed.state, parsed.country].filter(Boolean).join(', ');
            } catch {
                // If parsing fails, return null (don't show raw JSON)
                return null;
            }
        }
        return loc;
    }
    if (typeof loc === 'object') {
        // Handle {location: 'Online', icon: 'globe'} format
        if (loc.location && typeof loc.location === 'string') {
            return loc.location;
        }
        // Handle {city, state, country} format
        const parts = [];
        if (loc.city) parts.push(loc.city);
        if (loc.state) parts.push(loc.state);
        if (loc.country) parts.push(loc.country);
        if (parts.length > 0) return parts.join(', ');
        // Fallback: try to extract any string value
        for (const val of Object.values(loc)) {
            if (typeof val === 'string' && val !== 'globe' && val !== 'location' && val !== 'icon') {
                return val;
            }
        }
        return null;
    }
    return null;
}

// Capitalize string
export function capitalize(s) {
    if (!s) return '';
    return s.charAt(0).toUpperCase() + s.slice(1).toLowerCase();
}

// Debounce function
export function debounce(fn, wait) {
    let timeout;
    return (...args) => {
        clearTimeout(timeout);
        timeout = setTimeout(() => fn(...args), wait);
    };
}

// Calculate relevance score
export function calculateRelevanceScore(event) {
    let score = 0;

    // Prize weight (50%)
    const prize = parseFloat(event.prize_pool) || 0;
    score += Math.min((prize / 100000) * 50, 50);

    // Participants weight (30%)
    const participants = parseInt(event.participants) || 0;
    score += Math.min((participants / 500) * 30, 30);

    // Days left weight (20%)
    if (event.deadline) {
        const daysLeft = Math.max(0, (new Date(event.deadline) - new Date()) / (1000 * 60 * 60 * 24));
        score += Math.min((daysLeft / 30) * 20, 20);
    }

    return score;
}

// Calculate hackathon status
export function calculateStatus(hackathon) {
    const now = new Date();
    const deadline = hackathon.deadline ? new Date(hackathon.deadline) : null;
    const startDate = hackathon.start_date ? new Date(hackathon.start_date) : null;
    const endDate = hackathon.end_date ? new Date(hackathon.end_date) : null;

    if (deadline && deadline < now) return 'ended';
    if (endDate && endDate < now) return 'ended';
    if (startDate && startDate <= now && (!endDate || endDate >= now)) return 'ongoing';
    return 'upcoming';
}
