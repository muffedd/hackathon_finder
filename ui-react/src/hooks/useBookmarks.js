import { useState, useEffect, useCallback } from 'react';

export function useBookmarks() {
    const [bookmarks, setBookmarks] = useState(() => {
        try {
            return new Set(JSON.parse(localStorage.getItem('bookmarks') || '[]'));
        } catch {
            return new Set();
        }
    });

    // Persist to localStorage
    useEffect(() => {
        localStorage.setItem('bookmarks', JSON.stringify([...bookmarks]));
    }, [bookmarks]);

    const toggleBookmark = useCallback((id) => {
        setBookmarks(prev => {
            const next = new Set(prev);
            if (next.has(id)) {
                next.delete(id);
            } else {
                next.add(id);
            }
            return next;
        });
    }, []);

    const isBookmarked = useCallback((id) => {
        return bookmarks.has(id);
    }, [bookmarks]);

    return {
        bookmarks,
        toggleBookmark,
        isBookmarked,
    };
}
