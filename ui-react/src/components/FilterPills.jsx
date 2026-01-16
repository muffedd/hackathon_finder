const FILTERS = [
    { id: 'all', label: 'All' },
    { id: 'upcoming', label: 'Upcoming' },
    { id: 'live', label: 'Live Now' },
    { id: 'online', label: 'Online' },
    { id: 'in-person', label: 'Offline' },
];

export default function FilterPills({ currentFilter, onFilterChange }) {
    return (
        <div className="filter-pills">
            {FILTERS.map(filter => (
                <button
                    key={filter.id}
                    className={`filter-pill ${currentFilter === filter.id ? 'active' : ''}`}
                    data-filter={filter.id}
                    onClick={() => onFilterChange(filter.id)}
                >
                    {filter.label}
                </button>
            ))}
        </div>
    );
}
