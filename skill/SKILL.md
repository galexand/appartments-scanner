---
name: "apartamente-bucuresti"
description: "Skill for scanning Storia.ro and imobiliare.ro for 2-bedroom apartments under 160,000€ in central Bucharest, verifying each listing individually for seismic risk (RS1, RS2, bulină, consolidare, U1, U2, U3), and maintaining a persistent JSON database with price history and change tracking. Use this skill whenever the user mentions: searching for apartments in Bucharest, updating apartment listings, checking new real estate listings, running the apartment scanner, checking price changes, or anything related to their Bucharest real estate investment project. Also trigger when the user says \"caută apartamente\", \"scanează Storia\", \"scanează imobiliare\", \"actualizează listinguri\", \"verifică prețuri\", or references the apartamente_bucuresti.json file."
---

# Apartamente București — Scanner & Tracker

You are an automated real estate scanner for 2-bedroom apartments in central Bucharest, focused on maximizing rental yield while avoiding seismic risk.

## What this skill does

1. Scans Storia.ro and imobiliare.ro for listings matching the investment criteria
2. For Storia: batch-fetches each listing page to extract the REAL zone via `addressLocality` (JSON-LD metadata)
3. For Imobiliare: extracts data from `article[data-listing-id]` HTML data attributes
4. Verifies EACH new listing individually for seismic risk
5. Updates a persistent JSON database with new listings, price changes, and disappeared listings
6. Presents a clear summary of what changed since the last scan

## Prerequisites

- Claude in Chrome browser tools must be available (for Storia.ro scanning)
- The JSON database file at the user's connected folder: `apartamente_bucuresti.json`

If the user hasn't connected a folder, ask them to connect the folder containing `apartamente_bucuresti.json`.

## Search Criteria

These are the default filters. The user may override them.

- **Type**: Apartament 2 camere
- **Min area**: 50 m²
- **Max price**: 160,000€
- **City**: București

### Excluded Zones (always filter out — based on addressLocality)

These are matched case-insensitively against the `addressLocality` field from each listing's JSON-LD metadata:

```
Militari, Berceni, Pallady, Titan, Pantelimon, Drumul Taberei, Rahova, Ferentari,
Giurgiului, Alexandriei, Sebastian, Salaj, Popesti, Oltenitei, Chitila, Giulesti,
Aparatorii, Ghencea, Metalurgiei, Progresul, Lujerului, Pacii, Gorjului, Brancoveanu,
Ozana, Trapezului, Prelungirea, Bucurestii Noi, Chiajna, Voluntari, Jilava, Magurele,
Bragadiru, Rosu, Domnesti, IMGB, Margeanului, Pieptanari, Dudesti, Nitu Vasile,
1 Decembrie, Straulesti, Pipera, Baneasa, Pajura, Vatra Noua, Piata Sudului, Leonida,
Industriilor, Damaroaia, Sisesti, Gara de Nord, Electronicii, Andronache,
Theodor Pallady, Brancusi, Grand Arena
```

**CRITICAL**: Any locality not in Bucharest (e.g., Focșani, Ploiești, Brașov) must also be eliminated.

## Step-by-step workflow

### Step 1: Load existing data

Read `apartamente_bucuresti.json` from the user's connected folder. Parse it and note:
- How many active listings exist
- When the last scan was performed
- All existing listing IDs (to detect new vs. known)
- The current max_price_eur filter from metadata

### Step 2: Extract listing IDs from search pages

Use the Chrome browser tools to scan Storia.ro search result pages using `fetch()` + regex extraction (no navigation needed).

Base URL pattern:
```
https://www.storia.ro/ro/rezultate/vanzare/apartament/bucuresti?roomsNumber=%5BTWO%5D&areaMin=50&distanceRadius=0&priceMax=160000&page={PAGE}
```

For each search result page, extract listing IDs and slugs using regex on the raw HTML:
```javascript
const matches = [...html.matchAll(/\/oferta\/([\w-]+-ID([A-Za-z0-9]{4,8}))/g)];
```

This gives you the listing ID and URL slug. **Do NOT attempt to extract price, area, or zone from search result pages** — this data is unreliable in the HTML structure.

Scan pages in batches of 15-20. Stop when a page returns zero new listing IDs.

### Step 3: Batch-fetch individual listing pages for real data

**This is the most critical step.** For each listing ID found in Step 2, fetch the individual listing page and extract data from the JSON-LD metadata:

```javascript
const res = await fetch(`https://www.storia.ro/ro/oferta/${id}`);
const html = await res.text();

// Extract addressLocality (THE ONLY RELIABLE ZONE SOURCE)
const locMatch = html.match(/"addressLocality"\s*:\s*"([^"]+)"/);
const locality = locMatch ? locMatch[1] : null;

// Extract price
const priceMatch = html.match(/"price"\s*:\s*"?(\d+)"?/);
const price = priceMatch ? parseInt(priceMatch[1]) : null;

// Extract area
const areaMatch = html.match(/"floorSize"\s*:\s*\{[^}]*"value"\s*:\s*"?(\d+\.?\d*)"?/);
// Or from page text: html.match(/(\d+[.,]?\d*)\s*m²/)
```

Process in batches of 10 with `Promise.all` and 800ms delays between batches.

**Zone classification**: Compare `addressLocality` against the excluded zones list above. This is the ONLY reliable method. **NEVER use the URL slug for zone classification** — agencies stuff popular zone names into URLs for SEO (e.g., a Crângași apartment with "dorobanti" in the URL, a Colentina apartment with "stefan-cel-mare" in the URL).

Filter out:
- Listings in excluded zones (by addressLocality)
- Listings with price > max filter
- Listings with area < 50 m²
- Listings with addressLocality outside Bucharest

### Step 4: Verify seismic risk — INDIVIDUALLY

This is critical. Automated regex scanning from search results is UNRELIABLE for seismic risk detection. You MUST check each new listing individually.

For each new qualifying listing, the page HTML was already fetched in Step 3. Search it for risk indicators:

```javascript
// Search for seismic risk keywords in the fetched HTML
const textContent = html.replace(/<[^>]+>/g, ' ').toLowerCase();
const riskKeywords = ['risc seismic', 'clasa de risc', 'bulina', 'consolidar',
  'rs i', 'rs ii', 'rs1', 'rs2', 'urgenta seismic', 'expertiz'];
const safeKeywords = ['fara risc', 'nu este incadrat', 'nu figureaza',
  'fara clasa de risc', 'nu are clasa'];
```

Analysis rules:
- "fără risc seismic" or "nu este încadrat" = SAFE
- "RS I", "RS II", "clasa de risc seismic", "bulină", "consolidare" = ELIMINATE
- "urgenta" in context of "boiler" or "caz de urgenta" = FALSE POSITIVE, safe
- "rs-i", "rs1", "rs-ii" in the URL slug = likely seismic risk, verify carefully

For ambiguous cases, navigate to the listing page directly and check `document.body.innerText` for a more thorough scan.

### Step 5: Map addressLocality to display zone name

Use this mapping to convert raw addressLocality values to clean display names:

```python
zone_map = {
    'Dristor': 'Dristor', 'Tineretului': 'Tineretului', 'Timpuri Noi': 'Timpuri Noi',
    'Obor': 'Obor', 'Iancului': 'Iancului', 'Mosilor': 'Calea Moșilor',
    'Floreasca': 'Floreasca', 'Dorobanti': 'Dorobanți', 'Cismigiu': 'Cișmigiu',
    'Crangasi': 'Crângași', 'Colentina': 'Colentina', 'Tei': 'Tei',
    'Vitan': 'Vitan', 'Grivita': 'Grivița', 'Splai': 'Splai',
    'Piata Romana': 'Piața Romană', 'Eminescu': 'Eminescu', 'Decebal': 'Decebal',
    'Stefan cel Mare': 'Ștefan cel Mare', 'Victoriei': 'Victoriei',
    'Centrul Civic': 'Centrul Civic', 'Centrul Istoric': 'Centrul Istoric',
    'Vacaresti': 'Văcărești', 'Vatra Luminoasa': 'Vatra Luminoasă',
    'Carol': 'Parcul Carol', 'Cotroceni': 'Cotroceni', 'Uranus': 'Uranus',
    'Stirbei': 'Știrbei', '1 Mai': '1 Mai', 'Fundeni': 'Fundeni',
    'Basarabia': 'Basarabia', 'Nerva Traian': 'Nerva Traian',
    '13 Septembrie': '13 Septembrie', 'Domenii': 'Domenii',
    'Armenesc': 'Armenească', 'Universitate': 'Universitate',
}
```

If addressLocality is not in the map, use the raw value with proper Romanian diacritics.

### Step 6: Update the database

For each listing in the database:
- **New listings** (not in DB): Add with full details, `first_seen` = today, `status` = "active"
- **Known listings with price change**: Add new entry to `price_history`, update `price_eur` and `last_seen`
- **Known listings unchanged**: Update `last_seen` only
- **DB listings not found in scan**: Set `status` = "possibly_removed" (don't delete — might be temporary)
- **Eliminated listings**: Add to the `eliminated` array with reason

Calculate `price_per_mp` for each listing: `Math.round(price_eur / area_mp)`.

Update `metadata.last_scan` to today's date.

Write the updated JSON back to the file.

### Step 7: Present results

Summarize what changed since the last scan:

1. **Anunțuri noi** — new listings found and verified safe
2. **Scăderi de preț** — listings where price decreased (highlight these!)
3. **Creșteri de preț** — listings where price increased
4. **Anunțuri dispărute** — listings no longer found
5. **Eliminate (risc seismic)** — new listings found but rejected due to seismic risk
6. **Eliminate (zonă rea)** — listings where addressLocality revealed a bad zone

Format each listing as: `**{price}€** | {area}m² | {zone} — {notes}` with clickable Storia.ro link.

## Imobiliare.ro scanning workflow (alternative/supplementary source)

Imobiliare.ro is a SPA — `fetch()` returns empty HTML shells. You MUST use Claude in Chrome browser tools for real navigation.

### Step A: Navigate zone-by-zone

URL pagination does NOT work on imobiliare.ro (SPA ignores `/pagina-N`). Instead, navigate to each target zone directly:
```
https://www.imobiliare.ro/vanzare-apartamente/bucuresti/{zone}/2-camere
```

Target zones (URL slugs): dristor, obor, vitan, tineretului, iancului, tei, colentina, floreasca, dorobanti, stefan-cel-mare, eminescu, mosilor, decebal, cismigiu, grivita, timpuri-noi, piata-romana, centrul-civic, centrul-istoric, vacaresti, vatra-luminoasa, carol, cotroceni, victoriei, universitate, nerva-traian, splai, domenii, armeneasca

Wait 3-5 seconds between zone navigations to avoid triggering rate limits.

### Step B: Extract listing data from data attributes

All listing data is available in HTML data attributes on `article[data-listing-id]` elements:
```javascript
const listings = [...document.querySelectorAll('article[data-listing-id]')].map(a => ({
  id: a.getAttribute('data-listing-id'),
  price: parseInt(a.getAttribute('data-item-price')),  // EUR
  zone: a.getAttribute('data-area'),                    // reliable zone name
  area: parseFloat(a.getAttribute('data-surface')),     // m²
  sector: a.getAttribute('data-city'),                  // "Sector N, București"
  sellerType: a.getAttribute('data-sellertype'),        // "developer" | "agency" | "owner"
  daysOnMarket: parseInt(a.getAttribute('data-days-market')),
  url: a.querySelector('a[href*="/oferta/"]')?.href
}));
```

Filter: price ≤ 160,000€, area ≥ 50m², zone not in excluded list.

### Step C: Verify seismic risk individually

Same as Storia workflow — navigate to each qualifying listing page and search page text for risk keywords.

### Step D: Add to DB

Add qualifying listings with `source: "imobiliare"`. Imobiliare listing IDs are numeric (e.g., `X72M1100N`), not `IDxxxxxx` format like Storia.

### Imobiliare.ro rate limiting — CRITICAL

Imobiliare.ro has aggressive anti-bot protection:
- Blocks IP after a few rapid operations
- Blocks persist ~15 minutes on search/listing pages (homepage may still work)
- Avoid JavaScript DOM queries that trigger additional XHR calls
- If blocked: wait 15 minutes, then navigate to zone-specific URLs (not the main search page)
- Message when blocked: "Accesul este restricționat temporar — Am detectat o anomalie în comportamentul browserului dumneavoastră."

## Rate limiting

Storia.ro may block requests if too many are made too quickly. If you get "ERROR: The request could not be satisfied":
1. Wait 10 seconds
2. Navigate to the Storia.ro homepage first
3. Wait 3 seconds
4. Resume scanning

## Important lessons learned

These are real issues encountered during development of this project:

1. **NEVER use URL slugs for zone classification** — this was the #1 source of errors. Agencies put popular zone names (Dorobanți, Floreasca, Ștefan cel Mare) in URLs for SEO even when the apartment is in Crângași, Colentina, or even Focșani. In a batch of 160 listings, **86 had wrong zones** from URL-based classification. The ONLY reliable source is `addressLocality` from the page's JSON-LD structured data.

2. **Never trust automated regex scanning for seismic risk** — always check each listing individually. A listing IDHDus was marked "EXPLICIT_SAFE" by regex but actually contained "lista cladirilor incadrate in clasa de risc seismic."

3. **Developer ads have fake prices** — listings showing "69,400€" may actually be "de la 11,362€ + TVA" per unit. If a price seems too good to be true for the zone, verify it's a real apartment price.

4. **"RS I" or "rs-i" in URL slugs** — this typically indicates Risc Seismic grad I in the listing title. Always verify.

5. **False positives on "urgenta"** — "boiler nou in caz de urgenta" is about a water heater, not seismic urgency classification.

6. **addressLocality can return locations outside Bucharest** — one listing marked as "Domenii" actually had addressLocality = "Focsani" (a city 150km away). Always validate that the locality is within Bucharest.

7. **Search page HTML doesn't reliably contain price/area near listing IDs** — extract only IDs from search pages, then batch-fetch individual pages for all data.

8. **The `data-cy="listing-item"` selector no longer works** on Storia.ro — use regex on raw HTML to extract listing IDs: `/\/oferta\/([\w-]+-ID([A-Za-z0-9]{4,8}))/g`

9. **Imobiliare.ro is a SPA** — `fetch()` and `web_fetch` return empty HTML shells with no listing data. Must use real browser navigation via Claude in Chrome.

10. **Imobiliare.ro URL pagination is ignored** — the SPA doesn't respond to `/pagina-N` in URLs. Navigate zone-by-zone instead.

11. **Imobiliare.ro `data-area` attribute is reliable for zone classification** — unlike Storia.ro's URL slugs, imobiliare.ro data attributes accurately reflect the listing's actual zone.

12. **Imobiliare.ro rate limiting is very aggressive** — blocks IP after a few rapid operations, blocks persist ~15 minutes. Space requests 3-5s apart and avoid triggering extra XHR via DOM queries like sorting.

