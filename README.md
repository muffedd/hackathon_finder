# HackFind - Hackathon Aggregator

A web application that aggregates hackathons from multiple sources into one unified platform.

## Features

- 🔍 **Multi-source scraping** - Devpost, Devfolio, Unstop, HackerEarth, Superteam, MLH, and more
- ♾️ **Infinite scroll** - Loads hackathons as you scroll
- 🏷️ **Filtering** - Filter by mode (online/in-person), status (upcoming/ongoing)
- 🔎 **Search** - Full-text search across all hackathons
- 📊 **2600+ hackathons** in database

## Tech Stack

- **Backend**: Python, Flask, SQLite
- **Frontend**: Vanilla HTML, CSS, JavaScript
- **Scraping**: Requests, BeautifulSoup, Playwright (for JS-rendered sites)

## Getting Started

```bash
# Install dependencies
pip install -r requirements.txt

# Run scrapers to populate database
python scrape_all.py
python scrape_mega.py

# Start the server
python server.py

# Open http://localhost:8000
```

## Project Structure

```
├── server.py           # Flask server
├── ui/                 # Frontend files
│   ├── index.html
│   ├── app.js
│   └── styles.css
├── scrapers/           # Scraping modules
├── database/           # SQLite database manager
├── utils/              # Data normalization
└── config/             # Website configurations
```

## Scrapers

| Source | Method | Count |
|--------|--------|-------|
| Unstop | API | ~1400 |
| Devpost | API | ~800 |
| Devfolio | API | ~350 |
| HackerEarth | HTML | ~360 |
| Superteam | API | ~96 |
| MLH | Browser | ~1 |

## License

MIT
