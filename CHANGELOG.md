# Changelog

All notable changes to the HackFind project will be documented in this file.

## [Version 7.0] - 2026-01-18

### Added
- **AI Search Enhancements**: 
  - Added visual "Ctrl + K" hint in search bar.
  - Implemented keyboard shortcuts: `Ctrl/Cmd + K` to focus, `/` to focus (smart), `Esc` to clear/blur.
  - Added suggestion chips ("Beginner Friendly", "India with Prizes", etc.) that auto-fill search.
  - Added "Clear" (X) button to search input.
- **Client-Side Filters**: 
  - Added **Solo/Team** toggle filters (filters by team size).
  - Added **Weekend/Weekday** toggle filters (filters by start date).
- **Visited State**: 
  - Cards now track "Visited" status in LocalStorage.
  - Visited cards display with reduced opacity and purple title (Google-style).
  - Added "Clear History" button in navigation to reset visited status.
- **Share Functionality**: 
  - Click "Share" on card to instantly copy link to clipboard.
  - Added toast notification ("✓ Link copied to clipboard!") for feedback.
- **UI Animations**: 
  - Added smooth fade-in animations for cards during infinite scroll.
  - Added toast notification animations.

### Changed
- **Filter Layout**: 
  - Fixed "Sticky" filter bar overlapping cards (switched to relative positioning for better compatibility).
  - Updated filter pill styling and layout.
- **Navigation**: 
  - Removed "Saved" link from main navigation.
- **Performance**:
  - Optimized infinite scroll behavior.

### Fixed
- Resolved issue where cards were hidden behind fixed headers.
- Fixed layout z-index stacking contexts.
