## Car Mechanics Lead Scraper (Pages 3–5)

This tool searches for car mechanics in small US/UK cities, targets results from Google pages 3–5 (rank > 10), crawls a few pages per site, and extracts contact details to CSV.

### Features
- Google Programmable Search Engine (CSE) or SerpAPI provider
- Query templates like: "mechanic" "Cheltenham" or "auto repair" "Bath" (with optional `site:*.business.site`)
- Pulls ~30–40 results per city (pages 3–5), excludes page-1
- Visits a handful of pages per domain (home, /contact, /about, footer links)
- Extracts emails, phones, business name (JSON-LD), and address
- Suppression list support; simple DNS/MX email domain validation

### Setup
1. Python 3.10+
2. Create venv and install deps (Windows CMD):
```
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

### Configuration
Create `.env` (see `.env.example`):
- `SEARCH_PROVIDER=cse` or `serpapi`
- For CSE: `GOOGLE_API_KEY`, `GOOGLE_CSE_ID`
- For SerpAPI: `SERPAPI_KEY`
- Optional: `USER_AGENT`, `REQUEST_TIMEOUT=15`, `DELAY_SECONDS=1.0`

### Usage
Basic example:
```
python main.py --services "mechanic,auto repair" --cities "Cheltenham,Bath" --provider cse --output leads.csv
```
Include `site:` targeting:
```
python main.py --services "mechanic" --cities "Cheltenham" --site-filter "site:*.business.site" --provider cse --output leads.csv
```
From a file of cities (one per line):
```
python main.py --services "auto repair" --cities-file cities.txt --provider serpapi --output leads.csv
```

### CSV Columns
`service, city, rank, domain, page_url_found, business_name, email, phone`

### Compliance & Deliverability
- Respect opt-outs; never email addresses that say "no marketing"
- Keep and apply a suppression list (`suppression_list.txt`)
- B2B outreach: identify yourself, include an easy opt-out; follow UK PECR/GDPR or US CAN-SPAM as applicable
- Validate emails (consider Kickbox/ZeroBounce APIs); this tool does basic DNS/MX checks only
- Warm your sending domain; configure SPF/DKIM/DMARC

### Notes
- Be polite: the crawler limits pages and waits between requests
- Do not scrape Google HTML; use CSE or SerpAPI
