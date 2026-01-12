<p align="center">
  <h1 align="center">🔍 HackFind</h1>
  <p align="center">
    <strong>The Hackathon Discovery Platform</strong><br>
    <em>Aggregating 900+ hackathons from 15+ sources into one unified experience.</em>
  </p>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/version-0.3.1-blue" alt="Version">
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
| 🤖 **Browser Automation** | Playwright-powered scraping for JS-heavy sites. |
| 🔎 **Full-Text Search** | SQLite FTS5 for fast, fuzzy searching. |
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

### Version 0.4: Intelligence
| Feature | Description |
|---------|-------------|
| 📈 Win Probability | `Prize ÷ Participants` algorithm. |
| ⏰ Deadline Tracker | Watch events for updates. |
| 👥 Team Matchmaking | Connect hackers by skills. |
| ✅ Verified Organizers | Trust badges for reliable hosts. |

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
