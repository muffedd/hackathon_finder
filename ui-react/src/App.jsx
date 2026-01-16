import Header from './components/Header';
import Hero from './components/Hero';
import FilterBar from './components/FilterBar';
import HackathonGrid from './components/HackathonGrid';
import ScrollToTop from './components/ScrollToTop';

import { useHackathons } from './hooks/useHackathons';
import { useAISearch } from './hooks/useAISearch';
import { useBookmarks } from './hooks/useBookmarks';
import { useScrollBehavior } from './hooks/useScrollBehavior';

export default function App() {
  // Hackathon data and filters
  const {
    hackathons,
    totalCount,
    isLoading,
    hasMore,
    loadMore,
    currentFilter,
    setCurrentFilter,
    currentSort,
    setCurrentSort,
    searchQuery,
    setSearchQuery,
    locationFilter,
    setLocationFilter,
    allSources,
    selectedSources,
    setSelectedSources,
  } = useHackathons();

  // AI Search
  const {
    search: aiSearch,
    isSearching,
    currentStep,
    results: aiResults,
    query: aiQuery,
  } = useAISearch();

  // Bookmarks
  const { isBookmarked, toggleBookmark } = useBookmarks();

  // Scroll behavior
  const { showScrollTop, showStickyHeader, scrollToTop } = useScrollBehavior();

  return (
    <>
      <Header activeNav="explore" />

      <Hero
        onSearch={aiSearch}
        isSearching={isSearching}
        currentStep={currentStep}
        results={aiResults}
        query={aiQuery}
      />

      <FilterBar
        currentFilter={currentFilter}
        onFilterChange={setCurrentFilter}
        currentSort={currentSort}
        onSortChange={setCurrentSort}
        searchQuery={searchQuery}
        onSearchChange={setSearchQuery}
        locationFilter={locationFilter}
        onLocationChange={setLocationFilter}
        allSources={allSources}
        selectedSources={selectedSources}
        onSourcesChange={setSelectedSources}
        totalCount={totalCount}
        showStickyHeader={showStickyHeader}
      />

      <HackathonGrid
        hackathons={hackathons}
        isLoading={isLoading}
        hasMore={hasMore}
        onLoadMore={loadMore}
        isBookmarked={isBookmarked}
        onBookmark={toggleBookmark}
      />

      <ScrollToTop
        isVisible={showScrollTop}
        onClick={scrollToTop}
      />
    </>
  );
}
