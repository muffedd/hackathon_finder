import HackathonCard from './HackathonCard';

export default function HackathonGrid({
    hackathons,
    isLoading,
    hasMore,
    onLoadMore,
    isBookmarked,
    onBookmark
}) {
    if (isLoading) {
        return (
            <section className="results">
                <div className="loading-state" id="loadingState">
                    <div className="loading-spinner"></div>
                    <p>Loading hackathons...</p>
                </div>
            </section>
        );
    }

    if (!hackathons || hackathons.length === 0) {
        return (
            <section className="results">
                <div className="empty-state" id="emptyState">
                    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" width="48" height="48">
                        <circle cx="11" cy="11" r="8" />
                        <path d="m21 21-4.35-4.35" />
                    </svg>
                    <h3>No hackathons found</h3>
                    <p>Try adjusting your filters or search query.</p>
                </div>
            </section>
        );
    }

    return (
        <section className="results">
            <div className="bento-grid" id="bentoGrid">
                {hackathons.map((hackathon) => (
                    <HackathonCard
                        key={hackathon.id}
                        hackathon={hackathon}
                        isBookmarked={isBookmarked(hackathon.id)}
                        onBookmark={onBookmark}
                    />
                ))}
            </div>

            {hasMore && (
                <div className="load-more-container">
                    <button className="load-more-btn" onClick={onLoadMore}>
                        Load More
                        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" width="18" height="18">
                            <path d="M12 5v14M5 12l7 7 7-7" />
                        </svg>
                    </button>
                </div>
            )}
        </section>
    );
}
