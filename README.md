<p align="center">
  <h1 align="center">🔍 HackFind</h1>
  <p align="center">
    <strong>The Hackathon Discovery Platform</strong><br>
    <em>Aggregating 900+ hackathons from 15+ sources into one unified experience.</em>
  </p>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/version-0.4.1-blue" alt="Version">
  <img src="https://img.shields.io/badge/python-3.9+-green" alt="Python">
  <img src="https://img.shields.io/badge/license-MIT-lightgrey" alt="License">
</p>

---

## 📖 Table of Contents

- [Features](#-features)
- [Quick Start](#-quick-start)
- [Changelog](#-changelog)
- [Data Sources](#-data-sources)
- [Project Structure](#-project-structure)
- [Roadmap](#-roadmap)
- [Product Vision](#-product-vision-v10)
- [License](#license)

---

## ✨ Features

| Feature | Description |
|---------|-------------|
| 🔄 **Multi-Source Aggregation** | Devpost, Devfolio, Unstop, MLH, DoraHacks, and more. |
| 🎯 **Smart Date Parsing** | Handles ISO, Epoch, and complex date ranges. |
| ⚡ **Direct API Integration** | Fast, accurate data fetching for Unstop & Devfolio. |
| 🔎 **Hybrid Search** | Vector (Semantic) + Keyword (Lexical) for best-in-class relevance. |
| 📊 **Normalized Data** | Consistent schema across all sources. |
| 🧠 **AI Semantic Search** | ChromaDB + MiniLM for natural language queries. |

---

## 🚀 Quick Start

```bash
# 1. Clone the repository
git clone https://github.com/yourusername/hackfind.git
cd hackfind

# 2. Install dependencies
pip install -r requirements.txt
playwright install chromium

# 3. Run the scraper
python scrape_all.py

# 4. Start the server
python server.py

# 5. Open in browser
# → http://localhost:8001
```

---

## 📝 Changelog

### Version 0.4.1 (2026-01-13)

**Unstop Data Accuracy**
- 🌍 **Mode Detection**: robust hybrid/online/offline detection using API region data.
- 👥 **Real-time Participants**: Fetches live registration counts (`registerCount`).
- 📅 **Date Precision**: Correctly prioritizes Registration Deadline over Event End Date.
- 🔢 **Team Size**: Accurate parsing of team allocations (e.g., "1-4 Members", "Solo").

**Frontend Enhancements**
- ⏳ **Smart Status**: displays "Upcoming" icon for events with 0 participants.
- 👥 **Participant Counts**: Shows live participant numbers for ongoing events.
- 🧹 **Clean Defaults**: "All Sources" and "All Statuses" selected by default on refresh.

### Version 0.4.0 (2026-01-13)

**Major Enhancements**
- 🧠 **Hybrid AI Search**: Combined Vector Search (Semantic) with Keyword Search (Lexical) using Reciprocal Rank Fusion.
  - Improved "loose relevance" pass rate from 26% to 38%.
  - Better handling of exact technical terms (e.g., "frontend", "web3").
- ⚡ **Unstop Data Overhaul**: Replaced browser scraping with Direct API Polling.
  - Scrapes 415 events in seconds (vs 30 mins).
  - Captures exact **Registration Deadlines** (fixing "Upcoming" vs "Ended" status accuracy).
  - Retrieves full rich-text descriptions for superior search context.

**UI / UX**
- 📅 **Registration Deadlines**: Frontend now prioritizes showing "Reg: [Deadline]" to clearly indicate entry cutoffs.
- 🎨 **Status Badges**: Improved accuracy of "Live Now" vs "Upcoming" based on refined date data.

**Technical**
- 🧹 **Codebase Cleanup**: Removed legacy browser automation scripts for Unstop.
- 🔄 **Optimization**: Parallelized API fetching for maximum throughput.

### Version 0.3.2 (2026-01-12)

**New Features**
- 🎯 **Source Filter**: Multi-select checkbox filter for all 14 sources (Devpost, Unstop, MLH, Kaggle, etc.)
- 📊 Collapsible filter panel with "Select All" / "Clear All" buttons
- 💾 Source filter selections persist across page refreshes (localStorage)
- 🔄 Source filter works seamlessly with existing status, mode, and search filters

**Data Extraction Improvements**
- ✅ **Unstop**: Fixed prize extraction from `prizes` array (₹ currency support)
- ✅ **Unstop**: Fixed date extraction from `regnRequirements` (start_regn_dt, end_regn_dt)
- ✅ **Unstop**: Fixed location extraction from `address_with_country_logo` (city, state)
- 📈 **Unstop**: Now showing 98% valid dates, 62% valid prizes, 100% valid locations (400+ events)
- 🔧 Added generic nav link filters for TechGig and HackerEarth scrapers

**Prize Display Improvements**
- 💰 Smart prize display with 3 modes: monetary prizes (e.g., ₹15,000), "Prize TBD" for missing prizes, "Non-Cash Prize" for non-monetary rewards
- 🎨 Styled TBD and non-cash prizes with muted colors to distinguish from monetary prizes
- 🔢 Changed prize format from K/M abbreviations to comma-separated numbers for better readability
- ✅ Fixed $0/₹0 prizes to show as "Prize TBD" instead of displaying zero amounts

**Bug Fixes**
- Fixed source filter initialization to validate localStorage sources against current data
- Fixed text variable scope issues in TechGig scraper
- Added debug logging for source filter troubleshooting

**Technical**
- Enhanced `scrape_unstop` with nested JSON field mapping
- Improved scraper robustness with better error handling
- Added responsive grid layout for source checkboxes (mobile-friendly)

### Version 0.3.1 (2026-01-12)

**UI Improvements**
- Removed all emojis from dashboard for cleaner, professional appearance
- Added date range display showing both start and end dates
- Repositioned bookmark buttons to card headers for always-visible access
- Enhanced mode badges with colored backgrounds

**Filter Fixes**
- Implemented client-side status calculation for upcoming/ongoing filters
- Fixed mode filters to handle case variations and partial matches
- Status now calculated dynamically based on current date (no database updates needed)
- All filters now work with instant, client-side filtering

**Data Quality**
- Fixed currency detection to preserve original symbols (₹, €, £, ¥, $) from source data
- Fixed mode detection to properly handle location dictionaries
- Corrected 119 misclassified events (online events marked as in-person)
- Database migration to fix existing data inconsistencies

**Technical**
- Mode detection now extracts location strings from dictionaries correctly
- Currency normalization preserves source currency instead of forcing USD
- Filter logic uses case-insensitive matching with partial string support

### Version 0.3: AI Search ✅ IMPLEMENTED
| Feature | Tech Stack | Status |
|---------|------------|:------:|
| 🧠 AI Search | ChromaDB + MiniLM | ✅ Done |
| 📊 961 Events Vectorized | Sentence-Transformers | ✅ Done |

**API Endpoint**: `GET /api/search/ai?q=<natural language query>`

### Version 0.3: Mobile & Push
| Feature | Tech Stack | Priority |
|---------|------------|:--------:|
| 📱 Mobile App | Flutter | High |
| ⚡ Magic Fill | WebView JS Injection | Medium |
| 🔔 Push Notifications | Firebase FCM | Medium |

### Version 0.4: Intelligence & Personalization
| Feature | Description |
|---------|-------------|
| 🌍 **Geographic Personalization** | Auto-detect user location; prioritize country-specific platforms (Unstop for India, MLH for USA). |
| 🎯 **Smart Ranking** | Offline events: local first. Online events: high-stakes global hackathons. |
| 🌐 **Global Platform Expansion** | Add region-specific scrapers (Europe: HackZurich, APAC: local platforms, Africa: AfriHacks). |
| 📈 **Win Probability** | `Prize ÷ Participants` algorithm. |
| ⏰ **Deadline Tracker** | Watch events for updates. |
| 👥 **Team Matchmaking** | Connect hackers by skills. |
| ✅ **Verified Organizers** | Trust badges for reliable hosts. |
| 📍 **Proximity Bonus** | Rank in-person events by distance from user. |

### Infrastructure
| Current | Target |
|---------|--------|
| SQLite | TiDB Cloud |
| Flask | FastAPI |
| Vanilla JS | Next.js |

---

## 🎯 Product Vision (V1.0)

**The Complete Hackathon Companion** — One app for the entire journey.

```
DISCOVER → PREPARE → EXECUTE → SUBMIT → REFLECT
```

### Lifecycle Features

| Phase | Key Features |
|:------|:-------------|
| 🔍 **Discover** | AI Search, Win Probability, Watchlist, Team Finder |
| 📝 **Prepare** | Dashboard, Team Chat, Calendar Sync, Mentor Booking |
| ⚡ **Execute** | Live Schedule, Task Board, Progress Tracker |
| 🚀 **Submit** | Deadline Alerts, Link Validator, Demo Recorder |
| 🏆 **Reflect** | Result Tracker, Hacker Stats, Portfolio Export |

### Core Philosophy

> *"Every feature asks: Does this move the user closer to clicking 'Apply'?"*

### Competitive Edge

| Competitor | Gap |
|:-----------|:----|
| Devpost | Single source. No lifecycle. |
| Notion | Generic. No hackathon workflows. |
| **HackFind** | **Full lifecycle. 15+ sources. AI-powered.** |

---

## License

MIT © 2026 HackFind

---

<p align="center">
  <strong>Built with ❤️ for hackers, by hackers.</strong>
</p>
