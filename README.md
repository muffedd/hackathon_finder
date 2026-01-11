<p align="center">
  <h1 align="center">🔍 HackFind</h1>
  <p align="center">
    <strong>The Hackathon Discovery Platform</strong><br>
    <em>Aggregating 900+ hackathons from 15+ sources into one unified experience.</em>
  </p>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/version-0.3-blue" alt="Version">
  <img src="https://img.shields.io/badge/python-3.9+-green" alt="Python">
  <img src="https://img.shields.io/badge/license-MIT-lightgrey" alt="License">
</p>

---

## 📖 Table of Contents

- [Features](#-features)
- [Quick Start](#-quick-start)
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

## � Data Sources

### ✅ Fully Operational

| Source | Method | Count | Notes |
|:-------|:------:|:-----:|:------|
| Unstop | API | 400 | High volume, stable. |
| Devpost | API | 200 | Regex date parsing. |
| DevDisplay | Browser | 70 | Lazy-load handled. |
| Devfolio | API | 45 | ISO/Epoch fallback. |
| MLH | Scraper | 29 | Reliable. |
| Superteam | API | 26 | Stable. |

### ⚠️ Working (Monitoring Required)

| Source | Method | Count | Notes |
|:-------|:------:|:-----:|:------|
| DoraHacks | Browser | 24 | Playwright. |
| MyCareerNet | Browser | 16 | Fixed selectors. |
| TechGig | Browser | 13 | Date parsing fixed. |
| HackQuest | Browser | 11 | Successful. |
| GeeksforGeeks | Browser | 6 | Custom selectors. |
| HackerEarth | Browser | 1 | Bot protection. |

### ❌ Broken (Needs Fix)

| Source | Issue |
|:-------|:------|
| HackCulture | Site layout changed. |
| Kaggle | API endpoint blocked. |
| Contra | Empty response. |

---

## 📁 Project Structure

```
hackfind/
├── server.py           # Flask API server
├── scrape_all.py       # Consolidated scraper (API + Browser)
├── hackathons.db       # SQLite database
├── ui/                 # Frontend (HTML/CSS/JS)
│   ├── index.html
│   ├── styles.css
│   └── app.js
├── database/           # Database manager
│   └── db_manager.py
└── utils/              # Data normalization
    └── data_normalizer.py
```

---

## 🗺️ Roadmap

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
