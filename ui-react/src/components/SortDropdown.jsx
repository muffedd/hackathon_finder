import { useState, useRef, useEffect } from 'react';

const SORT_OPTIONS = [
    { id: 'relevance', label: 'Relevance' },
    { id: 'prize', label: 'Prize' },
    { id: 'deadline', label: 'Deadline' },
    { id: 'participants', label: 'Participants' },
];

export default function SortDropdown({ currentSort, onSortChange }) {
    const [isOpen, setIsOpen] = useState(false);
    const dropdownRef = useRef(null);

    // Close on outside click
    useEffect(() => {
        const handleClickOutside = (e) => {
            if (dropdownRef.current && !dropdownRef.current.contains(e.target)) {
                setIsOpen(false);
            }
        };
        document.addEventListener('click', handleClickOutside);
        return () => document.removeEventListener('click', handleClickOutside);
    }, []);

    const currentLabel = SORT_OPTIONS.find(o => o.id === currentSort)?.label || 'Relevance';

    const handleSelect = (sortId) => {
        onSortChange(sortId);
        setIsOpen(false);
    };

    return (
        <div className={`sort-dropdown ${isOpen ? 'open' : ''}`} ref={dropdownRef}>
            <button
                className="sort-btn"
                id="sortBtn"
                onClick={() => setIsOpen(!isOpen)}
            >
                <span>Sort: {currentLabel}</span>
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" width="16" height="16">
                    <path d="m6 9 6 6 6-6" />
                </svg>
            </button>
            <div className="sort-menu" id="sortMenu">
                {SORT_OPTIONS.map(option => (
                    <button
                        key={option.id}
                        className={`sort-option ${currentSort === option.id ? 'active' : ''}`}
                        data-sort={option.id}
                        onClick={() => handleSelect(option.id)}
                    >
                        {option.label}
                    </button>
                ))}
            </div>
        </div>
    );
}
