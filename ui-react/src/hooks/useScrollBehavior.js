import { useState, useEffect, useCallback } from 'react';

export function useScrollBehavior() {
    const [showScrollTop, setShowScrollTop] = useState(false);
    const [showStickyHeader, setShowStickyHeader] = useState(false);
    const [lastScrollY, setLastScrollY] = useState(0);

    useEffect(() => {
        const handleScroll = () => {
            const currentY = window.scrollY;

            // Scroll-to-top visibility
            setShowScrollTop(currentY > 300);

            // Sticky header (show on scroll up when past filters)
            const filtersSection = document.getElementById('filtersSection');
            if (filtersSection) {
                const rect = filtersSection.getBoundingClientRect();
                const isPast = rect.bottom < 60;

                if (isPast) {
                    setShowStickyHeader(currentY < lastScrollY);
                } else {
                    setShowStickyHeader(false);
                }
            }

            setLastScrollY(currentY);
        };

        window.addEventListener('scroll', handleScroll, { passive: true });
        return () => window.removeEventListener('scroll', handleScroll);
    }, [lastScrollY]);

    const scrollToTop = useCallback(() => {
        window.scrollTo({ top: 0, behavior: 'smooth' });
    }, []);

    return {
        showScrollTop,
        showStickyHeader,
        scrollToTop,
    };
}
