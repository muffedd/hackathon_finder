import { useState, useEffect, useRef } from 'react';
import FilterPills from './FilterPills';
import SourcesDropdown from './SourcesDropdown';
import SortDropdown from './SortDropdown';
import { debounce } from '../utils/formatters';

export default function FilterBar({
    currentFilter,
    onFilterChange,
    currentSort,
    onSortChange,
    searchQuery,
    onSearchChange,
    locationFilter,
    onLocationChange,
    allSources,
    selectedSources,
    onSourcesChange,
    totalCount,
    showStickyHeader,
}) {
    const [localSearch, setLocalSearch] = useState(searchQuery);
    const [localLocation, setLocalLocation] = useState(locationFilter);
    const debouncedSearch = useRef(debounce(onSearchChange, 300));
    const debouncedLocation = useRef(debounce(onLocationChange, 500));

    useEffect(() => {
        debouncedSearch.current(localSearch);
    }, [localSearch]);

    useEffect(() => {
        debouncedLocation.current(localLocation);
    }, [localLocation]);

    const handleNearby = () => {
        if (navigator.geolocation) {
            navigator.geolocation.getCurrentPosition(
                (position) => {
                    // For now, just set a placeholder - could integrate with geocoding API
                    setLocalLocation('Near me');
                    onLocationChange('Near me');
                },
                (error) => {
                    console.error('Geolocation error:', error);
                    alert('Could not get your location. Please enter it manually.');
                }
            );
        } else {
            alert('Geolocation is not supported by your browser.');
        }
    };

    return (
        <section className="filters" id="filtersSection">
            <h2 className="explore-heading" id="exploreHeading">Explore</h2>
            <div className={`filters-content ${showStickyHeader ? 'sticky-active' : ''}`} id="filtersContent">
                <div className="filters-layout-split">
                    {/* Left Column: Pills + Sources */}
                    <div className="filters-left-col">
                        {/* Row 1: Filter Pills */}
                        <FilterPills
                            currentFilter={currentFilter}
                            onFilterChange={onFilterChange}
                        />

                        {/* Row 2: Sources Filter */}
                        <SourcesDropdown
                            allSources={allSources}
                            selectedSources={selectedSources}
                            onSourcesChange={onSourcesChange}
                        />
                    </div>

                    {/* Right Column: Search + Loc/Sort/Count */}
                    <div className="filters-right-col">
                        {/* Row 1: Keyword Search */}
                        <div className="filters-right-row-top">
                            <div className="keyword-search-container full-width">
                                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" width="18" height="18">
                                    <circle cx="11" cy="11" r="8" />
                                    <path d="m21 21-4.35-4.35" />
                                </svg>
                                <input
                                    type="text"
                                    className="keyword-search-input"
                                    id="searchInput"
                                    placeholder="Search keywords..."
                                    value={localSearch}
                                    onChange={(e) => setLocalSearch(e.target.value)}
                                />
                            </div>
                        </div>

                        {/* Row 2: Location + Sort + Count */}
                        <div className="filters-right-row-bottom">
                            {/* Location Input */}
                            <div className="location-filter-group">
                                <input
                                    type="text"
                                    className="location-input"
                                    id="locationInput"
                                    placeholder="Location..."
                                    value={localLocation}
                                    onChange={(e) => setLocalLocation(e.target.value)}
                                />
                                <button className="nearby-btn" id="nearbyBtn" onClick={handleNearby} title="Use my location">
                                    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" width="18" height="18">
                                        <path d="M12 2v4M12 18v4M2 12h4M18 12h4" />
                                    </svg>
                                </button>
                            </div>

                            {/* Sort Dropdown */}
                            <SortDropdown
                                currentSort={currentSort}
                                onSortChange={onSortChange}
                            />

                            {/* Results Count */}
                            <span className="results-count" id="resultsCount">
                                {totalCount} hackathons
                            </span>
                        </div>
                    </div>
                </div>
            </div>
        </section>
    );
}
