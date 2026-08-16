# Appartments Scanner — Project Context

## Overview
Automated real estate scanner for 2-bedroom apartments in central Bucharest. Scans Storia.ro, classifies zones via `addressLocality` JSON-LD metadata, verifies seismic risk individually, maintains persistent JSON DB with price history.

## Repo structure
```
skill/SKILL.md                        — Cowork skill definition (scanning workflow)
data/apartamente_bucuresti.json       — Persistent DB (162 active, 22 eliminated, ~112 possibly_removed)
dashboards/dashboard.html             — Interactive listing dashboard (Chart.js 4.5.0, dark theme)
dashboards/funnel.html                — Filtering funnel visualization
dashboards/index.html                 — Landing page linking both dashboards
```

## Key files also on local machine
- `~/galexand/lita-home/apartamente_bucuresti.json` — same DB, used by Cowork skill
- `~/galexand/lita-home/apartamente-bucuresti-*.html` — same dashboards, accessible from Finder

## Search criteria
- 2 camere, min 50m², max 160,000€, central Bucharest
- Zone classification: EXCLUSIVELY via `addressLocality` from JSON-LD (never URL slugs)
- ~50 excluded zones (Militari, Berceni, Rahova, Titan, Pantelimon, etc.)
- Full excluded list in `skill/SKILL.md`

## Critical technical lessons
1. **URL slugs are unreliable for zone classification** — 86/160 listings had wrong zones from slugs. Agencies stuff SEO keywords (dorobanti, floreasca) into URLs for apartments in Crangasi, Colentina, even Focsani (150km away).
2. **Only `addressLocality` from JSON-LD is reliable** — extract via: `html.match(/"addressLocality"\s*:\s*"([^"]+)"/)`
3. **Seismic risk must be verified individually** — never trust batch regex scanning
4. **`data-cy="listing-item"` no longer works on Storia.ro** — use regex: `/\/oferta\/([\w-]+-ID([A-Za-z0-9]{4,8}))/g`
5. **Search page HTML doesn't contain parseable price/area** — extract only IDs from search pages, batch-fetch individual pages for data

## Storia.ro scanning workflow
1. Extract listing IDs from search pages via `fetch()` + regex (batches of 15-20 pages)
2. Batch-fetch individual listing pages (10 at a time with Promise.all, 800ms delays)
3. From each page: extract `addressLocality`, price, area from JSON-LD
4. Filter by zone (addressLocality vs excluded list) and area/price
5. Check seismic risk keywords in page HTML
6. Update DB: new listings, price changes, disappeared listings

## Base search URL
```
https://www.storia.ro/ro/rezultate/vanzare/apartament/bucuresti?roomsNumber=%5BTWO%5D&areaMin=50&distanceRadius=0&priceMax=160000&page={PAGE}
```

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
      "id": "IDxxxxxx",
      "price_eur": 120000,
      "area_mp": 55,
      "price_per_mp": 2182,
      "zone": "Dristor",
      "sub_zone": "",
      "sector": 3,
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
