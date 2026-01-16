import { useState, useRef, useEffect } from 'react';

export default function SourcesDropdown({ allSources, selectedSources, onSourcesChange }) {
    const [isOpen, setIsOpen] = useState(false);
    const panelRef = useRef(null);
    const toggleRef = useRef(null);

    // Close on outside click
    useEffect(() => {
        const handleClickOutside = (e) => {
            if (panelRef.current && !panelRef.current.contains(e.target) &&
                toggleRef.current && !toggleRef.current.contains(e.target)) {
                setIsOpen(false);
            }
        };
        document.addEventListener('click', handleClickOutside);
        return () => document.removeEventListener('click', handleClickOutside);
    }, []);

    const handleToggle = (e) => {
        e.stopPropagation();
        setIsOpen(!isOpen);
    };

    const handleSourceChange = (source, checked) => {
        const newSelected = new Set(selectedSources);
        if (checked) {
            newSelected.add(source);
        } else {
            newSelected.delete(source);
        }
        onSourcesChange(newSelected);
    };

    const selectAll = () => {
        onSourcesChange(new Set(allSources));
    };

    const clearAll = () => {
        onSourcesChange(new Set());
    };

    return (
        <div className="source-filter-container">
            <button
                className={`source-filter-toggle ${isOpen ? 'active' : ''}`}
                id="sourceFilterToggle"
                ref={toggleRef}
                onClick={handleToggle}
            >
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" width="16" height="16">
                    <path d="M22 3H2l8 9.46V19l4 2v-8.54L22 3z" />
                </svg>
                <span>Sources</span>
                <span id="sourceCount">({selectedSources.size}/{allSources.length})</span>
                <svg className="chevron" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" width="16" height="16">
                    <path d="m6 9 6 6 6-6" />
                </svg>
            </button>

            <div
                className={`source-filter-panel ${isOpen ? 'show' : ''}`}
                id="sourceFilterPanel"
                ref={panelRef}
            >
                <div className="source-filter-actions">
                    <button id="selectAllSources" onClick={selectAll}>All</button>
                    <button id="clearAllSources" onClick={clearAll}>Clear</button>
                </div>
                <div className="source-checkboxes two-column" id="sourceCheckboxes">
                    {allSources.map(source => (
                        <label key={source} className="source-checkbox-item">
                            <input
                                type="checkbox"
                                value={source}
                                checked={selectedSources.has(source)}
                                onChange={(e) => handleSourceChange(source, e.target.checked)}
                            />
                            <span style={{ marginLeft: '8px', fontSize: '14px' }}>{source}</span>
                        </label>
                    ))}
                </div>
            </div>
        </div>
    );
}
