import { formatPrize, getLocation, calculateStatus } from '../utils/formatters';

// Source logo URLs
const SOURCE_LOGOS = {
    'Devpost': 'devpost.com',
    'Devfolio': 'devfolio.co',
    'Unstop': 'unstop.com',
    'MLH': 'mlh.io',
    'DoraHacks': 'dorahacks.io',
    'Kaggle': 'kaggle.com',
    'HackerEarth': 'hackerearth.com',
    'TechGig': 'techgig.com',
    'Superteam': 'superteam.fun',
    'HackQuest': 'hackquest.io',
    'DevDisplay': 'devdisplay.org',
    'HackCulture': 'hackculture.com',
    'MyCareerNet': 'mycareernet.in',
    'Lisk': 'lisk.com',
    'ETHGlobal': 'ethglobal.com',
    'Taikai': 'taikai.network',
    'Hack2Skill': 'hack2skill.com'
};

function renderSourceIcon(source) {
    if (!source) return '?';
    const domain = SOURCE_LOGOS[source];
    if (domain) {
        return (
            <img
                src={`https://www.google.com/s2/favicons?domain=${domain}&sz=64`}
                alt={source}
                onError={(e) => { e.target.outerHTML = source.charAt(0); }}
            />
        );
    }
    return source.charAt(0).toUpperCase();
}

function formatMode(mode) {
    if (!mode) return 'Unknown';
    if (mode.toLowerCase() === 'in-person') return 'Offline';
    return mode.charAt(0).toUpperCase() + mode.slice(1);
}

export default function HackathonCard({ hackathon, isBookmarked, onBookmark }) {
    const h = hackathon;
    const location = getLocation(h.location);
    const status = calculateStatus(h);

    // Determine mode
    let mode = h.mode || 'unknown';
    const locLower = (location || '').toLowerCase();
    if (locLower === 'online' || locLower === 'virtual' || locLower === 'remote' || locLower.includes('online')) {
        mode = 'online';
    }

    // Hide location if redundant
    const isLocationRedundant = mode === 'online' && ['online', 'virtual', 'remote'].includes(locLower);

    // Parse date for calendar badge
    const dateObj = h.end_date ? new Date(h.end_date) : null;
    const month = dateObj ? dateObj.toLocaleDateString('en-US', { month: 'short' }).toUpperCase() : 'TBA';
    const day = dateObj ? dateObj.getDate() : '--';

    // Prize display logic
    const prize = h.prize_pool;
    let prizeText = 'Prize TBD';
    let prizeClass = 'tbd';

    if (prize) {
        const isMonetary = /^[\$€£¥₹][\d,]+/.test(prize);
        if (isMonetary) {
            prizeText = prize;
            prizeClass = '';
        } else {
            const isZeroValue = prize.match(/^[\$€£¥₹]?0(\.0+)?$/);
            if (isZeroValue) {
                prizeText = 'Prize TBD';
                prizeClass = 'tbd';
            } else {
                prizeText = 'Non-Cash Prize';
                prizeClass = 'non-cash';
            }
        }
    }

    // Stats
    const count = parseInt(h.participants_count || 0);
    const stats = [];

    if (status === 'upcoming' && count === 0) {
        stats.push({ icon: '⏳', text: 'Upcoming' });
    } else if (count > 0) {
        stats.push({ icon: '👥', text: count.toLocaleString() });
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
        stats.push({ icon: '👤', text: teamText });
    }

    const handleBookmarkClick = (e) => {
        e.preventDefault();
        e.stopPropagation();
        onBookmark(h.id);
    };

    const handleCardClick = () => {
        if (h.url) {
            window.open(h.url, '_blank');
        }
    };

    return (
        <article className="bento-card" data-url={h.url || '#'} onClick={handleCardClick}>
            {/* Calendar Badge */}
            <div className="bento-calendar">
                <div className="calendar-month">{month}</div>
                <div className="calendar-day">{day}</div>
            </div>

            {/* Source Icon */}
            <div className="bento-source-icon" title={h.source || 'Unknown'}>
                {renderSourceIcon(h.source)}
            </div>

            {/* Content */}
            <div className="bento-content">
                <h3 className="bento-title">{h.title || 'Untitled'}</h3>
                {h.ai_reason && <div className="ai-reason">{h.ai_reason}</div>}

                <div className="bento-mode-row">
                    <span className={`bento-mode ${mode}`}>{formatMode(mode)}</span>
                    {!isLocationRedundant && location && (
                        <span className="bento-location">{location}</span>
                    )}
                </div>

                <div className={`bento-prize ${prizeClass}`}>{prizeText}</div>

                {stats.length > 0 && (
                    <div className="bento-stats-row">
                        {stats.map((stat, i) => (
                            <span key={i} className="bento-stat">
                                <span className="stat-icon">{stat.icon}</span>
                                {stat.text}
                            </span>
                        ))}
                    </div>
                )}

                {h.tags && h.tags.length > 0 && (
                    <div className="bento-tags">
                        {h.tags.slice(0, 3).map((tag, i) => (
                            <span key={i} className="bento-tag">{tag}</span>
                        ))}
                    </div>
                )}
            </div>

            {/* Divider */}
            <div className="bento-divider"></div>

            {/* Footer with View Details and Bookmark */}
            <div className="bento-footer">
                <button
                    className="bento-cta"
                    onClick={(e) => {
                        e.stopPropagation();
                        if (h.url) window.open(h.url, '_blank');
                    }}
                >
                    View Details
                </button>
                <button
                    className={`bento-bookmark ${isBookmarked ? 'active' : ''}`}
                    data-id={h.id}
                    onClick={handleBookmarkClick}
                >
                    {isBookmarked ? '★' : '☆'}
                </button>
            </div>
        </article>
    );
}
