export default function ScrollToTop({ isVisible, onClick }) {
    if (!isVisible) return null;

    return (
        <button
            className="scroll-top-btn visible"
            id="scrollTopBtn"
            onClick={onClick}
            title="Scroll to top"
        >
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" width="24" height="24">
                <path d="M12 19V5M5 12l7-7 7 7" />
            </svg>
        </button>
    );
}
