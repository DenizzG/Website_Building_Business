import argparse
import os
from typing import List

from dotenv import load_dotenv

from scraper.pipeline import run_pipeline
from scraper.search_providers import get_provider

# ============================================================================
# CONFIGURE YOUR CITIES AND SERVICES HERE
# ============================================================================

CITIES = [
"Joliet",
"Bridgeport",
"Mesquite",
"Pasadena",
"Olathe",
"Escondido",
"Savannah",
"McAllen",
"Gainesville",
"Pomona",
"Rockford",
"Thornton",
"Waco",
"Visalia",
"Syracuse",
"Columbia",
"Midland",
"Miramar",
"Palm Bay",
"Lakewood[w]",
"Jackson",
"Coral Springs",
"Victorville",
"Elizabeth",
"Fullerton",
"Meridian",
"Torrance",
"Stamford",
"West Valley City",
"Orange",
"Cedar Rapids",
"Warren",
"Hampton[l]",
"New Haven",
"Pasadena",
"Kent",
"Dayton",
"Fargo",
"Lewisville",
"Carrollton",
"Round Rock",
"Sterling Heights",
"Santa Clara",
"Norman",
"Columbia",
"Abilene",
"Pearland",
"Athens[x]",
"College Station",
"Clovis",
"West Palm Beach",
"Allentown",
"North Charleston",
"Simi Valley",
"Topeka",
"Wilmington",
"Lakeland",
"Thousand Oaks",
"Concord",
"Rochester",
"Vallejo",
"Ann Arbor",
"Broken Arrow",
"Fairfield",
"Lafayette[y]",
"Hartford",
"Arvada",
"Berkeley",
"Independence",
"Billings",
"Cambridge",
"Lowell",
"Odessa",
"High Point",
"League City",
"Antioch",
"Richardson",
"Goodyear",
"Pompano Beach",
"Nampa",
"Menifee",
"Las Cruces",
"Clearwater",
"West Jordan",
"New Braunfels",
"Manchester",
"Miami Gardens",
"Waterbury",
"Provo",
"Evansville",
"Richmond",
"Westminster",
"Elgin",
"Conroe",
"Greeley",
"Lansing",
"Buckeye",
"Tuscaloosa",
"Allen",
"Carlsbad",
"Everett",
"Springfield",
"Beaumont",
"Murrieta",
"Rio Rancho",
"Temecula",
"Concord",
"Tyler",
"Davie",
"South Fulton",
"Peoria",
"Sparks",
"Gresham",
"Santa Maria",
"Pueblo",
"Hillsboro",
"Edison[w]",
"Sugar Land",
"Ventura[z]",
"Downey",
"Costa Mesa",
"Centennial",
"Edinburg",
"Spokane Valley",
"Jurupa Valley",
"Bend",
"West Covina",
"Boulder",
"Palm Coast",
"Lee's Summit",
"Dearborn",
"Green Bay",
"St. George",
"Woodbridge[w]",
"Brockton",
"Renton",
"Sandy Springs",
"Rialto",
"El Monte",
"Vacaville",
"Fishers",
"South Bend",
"Carmel",
"Yuma",
"Burbank",
"Lynn",
"Quincy",
"El Cajon",
"Fayetteville",
"Suffolk[l]",
"San Mateo",
"Chico",
"Inglewood",
"Wichita Falls",
"Boca Raton",
"Hesperia",
"Daly City",
"Clinton[aa]",
"Georgetown",
"New Bedford",
"Albany",
"Davenport",
"Plantation",
"Deltona",
"Federal Way",
"San Angelo",
"Tracy",
"Sunrise",

    # Add more cities here - paste your long list
]

SERVICES = [
    "car mechanic", 

    # Add more service terms here - paste your long list
]

# Configuration (you can override with command line args)
DEFAULT_PROVIDER = "cse"  # or "serpapi"
DEFAULT_PAGES = "3-5"
DEFAULT_OUTPUT = "leads_real_final_continued.csv"
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
