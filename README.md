# Appartments Scanner

Automated real estate scanner for 2-bedroom apartments in central Bucharest, built to maximize rental yield while avoiding seismic risk.

## What it does

1. Scans [Storia.ro](https://www.storia.ro) for listings matching investment criteria
2. Classifies each listing's real zone via `addressLocality` (JSON-LD metadata) — URL slugs are unreliable due to SEO manipulation
3. Verifies each listing individually for seismic risk (RS1, RS2, bulina, consolidare, U1-U3)
4. Maintains a persistent JSON database with price history and change tracking
5. Generates interactive HTML dashboards with filters, charts, and zone distribution

## Search criteria

- 2-bedroom apartments in Bucharest
- Minimum 50 m²
- Maximum 160,000 EUR
- Central zones only (Dristor, Tineretului, Obor, Floreasca, Dorobanti, Stefan cel Mare, etc.)
- ~50 peripheral zones excluded (Militari, Berceni, Rahova, Titan, etc.)

## Project structure

```
skill/          Cowork skill definition (SKILL.md) — automated scanning instructions
data/           Persistent JSON database with all listings, price history, eliminations
dashboards/     Interactive HTML dashboards (open index.html in browser)
```

## Dashboards

Open `dashboards/index.html` in any browser to access:

- **Listings Dashboard** — all active apartments with interactive filters, zone distribution chart, price/area scatter plot, sortable table
- **Filtering Funnel** — visualization of the complete filtering pipeline (1,814 raw → 162 qualifying)

## Key insight: never trust URL slugs for zone classification

In a batch of 160 listings, **86 had wrong zones** when classified by URL slug. Agencies put popular zone names (Dorobanti, Floreasca, Stefan cel Mare) in URLs for SEO even when the apartment is in Crangasi, Colentina, or even Focsani (150km away). The only reliable source is `addressLocality` from each page's JSON-LD structured data.

## Current stats (Aug 2026)

- 162 active listings
- 22 eliminated (seismic risk or bad zone)
- 34 distinct zones
- Price range: 70,990 - 160,000 EUR
- Best value: ~1,300 EUR/m² (Splai, Piata Romana)

## Built with

[Claude Cowork](https://claude.ai) + [Claude in Chrome](https://chromewebstore.google.com/detail/claude-in-chrome/) for automated browser scanning
