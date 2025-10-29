import argparse
import os
from typing import List

from dotenv import load_dotenv

from scraper.pipeline import run_pipeline
from scraper.search_providers import get_provider

# ============================================================================
# CONFIGURE YOUR CITIES AND SERVICES HERE
# ============================================================================

CITIES = ["Lambeth",
"Blackfriars",
"Temple",
"Holborn",
"Clerkenwell",
"Farringdon",
"Barbican",
"Aldgate",
"Whitechapel",
"Shoreditch",
"Hoxton",
"Spitalfields",
"Bethnal Green",
"Rotherhithe",
"Canada Water",
"Surrey Quays",
"Deptford",
"New Cross",
"Peckham",
"Camberwell",
"Oval",
"Stockwell",
"Brixton",
"Herne Hill",
"Dulwich",
"Greenwich",
"Isle of Dogs",
"Canary Wharf",
"Poplar",
"Limehouse",
"Stepney",
"Bow",
"Mile End",
"Hackney",
"Stratford",
"Wapping",
"Shadwell",
"Tower Hill",
"Monument",
"Covent Garden",
"Soho",
"Fitzrovia",
"Marylebone",
"Mayfair",
"St James",
"Paddington",
"Pimlico",
"Chelsea",
"Battersea",
"Nine Elms",
"Clapham",
"Wandsworth",
"Putney",
"Fulham",
"Hammersmith",
"Shepherds Bush",
"White City",
"Notting Hill",
"Kensington",
"South Kensington",
"Earls Court",
"West Kensington",
"Holland Park",
"Chiswick",
"Acton",
"Ealing",
"Brentford",
"Richmond",
"Twickenham",
"Kew",
"Barnes",
"Hounslow",
"Isleworth",
"Kingston",
"Surbiton",
"Wimbledon",
"Merton",
"Tooting",
"Balham",
"Streatham",
"Norbury",
"Croydon",
"Crystal Palace",
"Sydenham",
"Forest Hill",
"Lewisham",
"Catford",
"Blackheath",
"Charlton",
"Woolwich",
"Plumstead",
"Thamesmead",
"Erith",
"Belvedere",
"Bexley",
"Bexleyheath",
"Sidcup",
"Eltham"
]

SERVICES = [
    "beauty salon london",

    # Add more service terms here - paste your long list
]

# Configuration (you can override with command line args)
DEFAULT_PROVIDER = "cse"  # or "serpapi"
DEFAULT_PAGES = "1-2"
DEFAULT_OUTPUT = "beauty_salon.csv"
DEFAULT_SITE_FILTER = ""  # or "site:*.business.site"
DEFAULT_MAX_PER_CITY = 35

# ============================================================================


def parse_list(value: str) -> List[str]:
    return [x.strip() for x in value.split(",") if x.strip()]


def load_cities_from_file(path: str) -> List[str]:
    with open(path, "r", encoding="utf-8") as f:
        return [line.strip() for line in f if line.strip()]


def main() -> None:
    load_dotenv()

    parser = argparse.ArgumentParser(description="Car mechanics lead scraper (pages 3–5)")
    parser.add_argument("--services", type=str, help="Comma-separated list (overrides SERVICES array)")
    parser.add_argument("--cities", type=str, help="Comma-separated city list (overrides CITIES array)")
    parser.add_argument("--cities-file", type=str, help="Path to a text file with one city per line (overrides CITIES array)")
    parser.add_argument("--site-filter", type=str, default=DEFAULT_SITE_FILTER, help="Optional site: filter, e.g. 'site:*.business.site'")
    parser.add_argument("--provider", type=str, default=os.getenv("SEARCH_PROVIDER", DEFAULT_PROVIDER), choices=["cse", "serpapi"], help="Search provider")
    parser.add_argument("--pages", type=str, default=DEFAULT_PAGES, help="Page range, e.g. '3-5'")
    parser.add_argument("--max-per-city", type=int, default=DEFAULT_MAX_PER_CITY, help="Max deduped domains per city")
    parser.add_argument("--output", type=str, default=DEFAULT_OUTPUT, help="Output CSV path")

    args = parser.parse_args()

    # Use arrays from file or command line overrides
    if args.services:
        services = parse_list(args.services)
    else:
        services = SERVICES

    if args.cities:
        cities = parse_list(args.cities)
    elif args.cities_file:
        cities = load_cities_from_file(args.cities_file)
    else:
        cities = CITIES

    if "-" in args.pages:
        start_page_str, end_page_str = args.pages.split("-", 1)
        start_page = int(start_page_str)
        end_page = int(end_page_str)
    else:
        start_page = end_page = int(args.pages)

    print(f"Running scraper with {len(services)} services and {len(cities)} cities...")
    print(f"Services: {services[:3]}{'...' if len(services) > 3 else ''}")
    print(f"Cities: {cities[:3]}{'...' if len(cities) > 3 else ''}")
    print(f"Provider: {args.provider}, Pages: {args.pages}, Output: {args.output}")

    provider = get_provider(args.provider)
    run_pipeline(
        provider=provider,
        services=services,
        cities=cities,
        site_filter=args.site_filter or None,
        start_page=start_page,
        end_page=end_page,
        output_csv=args.output,
        max_per_city=args.max_per_city,
    )


if __name__ == "__main__":
    main()
