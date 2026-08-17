# Appartments Scanner — Project Context

## Overview
Automated real estate scanner for 2-bedroom apartments in central Bucharest. Scans Storia.ro and imobiliare.ro, classifies zones via `addressLocality` (Storia) or `data-area` attribute (imobiliare), verifies seismic risk individually, maintains persistent JSON DB with price history.

## Repo structure
```
scripts/build_db.py                   — JSON → SQLite → site data export
data/apartamente_bucuresti.json       — Persistent JSON DB (canonical source)
data/apartamente.db                   — SQLite DB (built from JSON, gitignored)
docs/                                 — GitHub Pages static site
  index.html                          — Main SPA (filters, charts, compare, detail modals)
  data/listings.json                  — Exported site data (built by build_db.py)
skill/SKILL.md                        — Cowork skill definition (scanning workflow)
dashboards/                           — Legacy standalone dashboards
```

## Build & deploy
```bash
python3 scripts/build_db.py           # JSON → SQLite → docs/data/listings.json
python3 scripts/build_db.py --serve   # + local server at :8080
# GitHub Pages serves from docs/ folder
```

## Key files also on local machine
- `~/galexand/lita-home/apartamente_bucuresti.json` — same DB, used by Cowork skill
- `~/galexand/lita-home/apartamente-bucuresti-*.html` — legacy dashboards

## Search criteria
- 2 camere, min 50m², max 160,000€, central Bucharest
- Zone classification: EXCLUSIVELY via `addressLocality` from JSON-LD (never URL slugs)
- ~50 excluded zones (Militari, Berceni, Rahova, Titan, Pantelimon, etc.)
- Full excluded list in `skill/SKILL.md`

## Data sources

### Storia.ro (primary)
- Scannable via `fetch()` from browser console — no SPA issues
- Zone: EXCLUSIVELY via `addressLocality` from JSON-LD (never URL slugs)
- Listing IDs: `IDxxxxxx` format
- Base URL: `https://www.storia.ro/ro/rezultate/vanzare/apartament/bucuresti?roomsNumber=%5BTWO%5D&areaMin=50&distanceRadius=0&priceMax=160000&page={PAGE}`

### Imobiliare.ro (secondary)
- **SPA** — `fetch()` returns empty shells; requires real browser navigation via Claude in Chrome
- **URL pagination doesn't work** — `/pagina-N` ignored by SPA
- **Aggressive anti-bot** — blocks IP after rapid operations; blocks persist ~15 min
- Navigate zone-by-zone: `https://www.imobiliare.ro/vanzare-apartamente/bucuresti/{zone}/2-camere`
- Listing IDs: numeric format (e.g., `X72M1100N`)
- Individual listing: `https://www.imobiliare.ro/oferta/{slug}-{listingId}`

#### Imobiliare.ro data extraction
All data in HTML data attributes on `article[data-listing-id]` elements:
```javascript
document.querySelectorAll('article[data-listing-id]').forEach(a => {
  const data = {
    id: a.getAttribute('data-listing-id'),
    price: parseInt(a.getAttribute('data-item-price')),  // EUR
    zone: a.getAttribute('data-area'),                    // reliable zone name
    area: parseFloat(a.getAttribute('data-surface')),     // m²
    sector: a.getAttribute('data-city'),                  // "Sector N, București"
    sellerType: a.getAttribute('data-sellertype'),
    daysOnMarket: parseInt(a.getAttribute('data-days-market')),
    url: a.querySelector('a[href*="/oferta/"]')?.href
  };
});
```

#### Imobiliare.ro target zones
dristor, obor, vitan, tineretului, iancului, tei, colentina, floreasca, dorobanti, stefan-cel-mare, eminescu, mosilor, decebal, cismigiu, grivita, timpuri-noi, piata-romana, centrul-civic, centrul-istoric, vacaresti, vatra-luminoasa, carol, cotroceni, victoriei, universitate, nerva-traian, splai, domenii, armeneasca

## Critical technical lessons
1. **URL slugs are unreliable for zone classification (Storia.ro)** — 86/160 listings had wrong zones. Agencies stuff SEO keywords into URLs.
2. **Only `addressLocality` from JSON-LD is reliable for Storia.ro** — extract via: `html.match(/"addressLocality"\s*:\s*"([^"]+)"/)`
3. **Imobiliare.ro `data-area` attribute is reliable** — unlike Storia URL slugs
4. **Seismic risk must be verified individually** — never trust batch regex scanning
5. **`data-cy="listing-item"` no longer works on Storia.ro** — use regex: `/\/oferta\/([\w-]+-ID([A-Za-z0-9]{4,8}))/g`
6. **Search page HTML doesn't contain parseable price/area (Storia)** — extract only IDs, batch-fetch individual pages
7. **Imobiliare.ro is a SPA** — `fetch()` returns empty shells; must use real browser navigation
8. **Imobiliare.ro URL pagination is ignored** — navigate zone-by-zone instead
9. **Imobiliare.ro rate limiting is aggressive** — space requests 3-5s, avoid JS DOM queries that trigger extra XHR

## Storia.ro scanning workflow
1. Extract listing IDs from search pages via `fetch()` + regex (batches of 15-20 pages)
2. Batch-fetch individual listing pages (10 at a time with Promise.all, 800ms delays)
3. From each page: extract `addressLocality`, price, area from JSON-LD
4. Filter by zone (addressLocality vs excluded list) and area/price
5. Check seismic risk keywords in page HTML
6. Update DB: new listings, price changes, disappeared listings

## Imobiliare.ro scanning workflow
1. Navigate to each target zone URL via Chrome browser tools
2. Extract listing data from `article[data-listing-id]` data attributes
3. Filter by price/area/zone criteria
4. Navigate to each qualifying listing individually for seismic risk check
5. Update DB with `source: "imobiliare"` — IDs are numeric, not IDxxxxxx format

## DB schema (apartamente_bucuresti.json)
```json
{
  "metadata": {
    "last_scan": "2026-08-15",
    "filters": { "max_price_eur": 160000, "min_area_mp": 50, ... },
    "scan_funnel": { "stages": [...], "final_qualifying": 73 }
  },
  "listings": [
    {
      "id": "IDxxxxxx",           // Storia: IDxxxxxx, Imobiliare: numeric
      "price_eur": 120000,
      "area_mp": 55,
      "price_per_mp": 2182,
      "zone": "Dristor",
      "sub_zone": "",
      "sector": 3,
      "source": "storia|imobiliare",
      "seismic_risk": "none",
      "status": "active|possibly_removed",
      "first_seen": "2026-08-15",
      "last_seen": "2026-08-15",
      "price_history": [{"date": "...", "price": 120000}],
      "url": "https://www.storia.ro/ro/oferta/..."
    }
  ],
  "eliminated": [
    { "id": "...", "zone": "...", "reason": "Risc seismic RS2", ... }
  ]
}
```

## Current stats (Aug 15, 2026)
- 162 active listings across 34 zones
- Top zones: Dristor (19), Colentina (12), Vitan (12), Obor (12), Tei (11)
- 22 eliminated (seismic risk + bad zones discovered post-scan)
- Price range: 70,990 - 160,000€
- Best €/m²: ~1,300 (Splai, Piata Romana)

## GitHub
Repo: https://github.com/galexand/appartments-scanner
