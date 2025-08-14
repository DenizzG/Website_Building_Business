import csv
from typing import Dict, List, Optional, Set

from .crawler import crawl_site
from .extractors import extract_business_info_from_jsonld, extract_emails, extract_phones
from .search_providers import BaseSearchProvider, collect_results_for_pages
from .util import (
    is_suppressed,
    is_excluded_domain,
    is_automotive_business,
    load_suppression_list,
    normalize_domain,
    page_disallows_marketing,
    validate_email_for_outreach,
)

Row = Dict[str, Optional[str]]


def build_query(service: str, city: str, site_filter: Optional[str] = None) -> str:
    parts = [f'"{service.strip()}"', f'"{city.strip()}"']
    if site_filter:
        parts.append(site_filter.strip())
    return " ".join(parts)


def dedupe_by_domain(results: List[Dict[str, str]]) -> List[Dict[str, str]]:
    seen: Set[str] = set()
    deduped: List[Dict[str, str]] = []
    for r in results:
        domain = normalize_domain(r.get("link", ""))
        if not domain or domain in seen:
            continue
        seen.add(domain)
        deduped.append(r)
    return deduped


def process_result(result: Dict[str, str], service: str, city: str, suppression: Set[str]) -> List[Row]:
    link = result["link"]
    rank_str = result.get("rank", "")
    domain = normalize_domain(link) or ""
    
    # Skip excluded domains (job sites, forums, etc.)
    if is_excluded_domain(link):
        print(f"    Skipping excluded domain: {domain}")
        return []

    # Collect all data from all pages for this domain
    all_emails: Set[str] = set()
    all_phones: Set[str] = set()
    business_names: Set[str] = set()
    page_urls: List[str] = []

    # Check if this is actually an automotive business
    automotive_business = False
    
    for page_url, soup in crawl_site(link, max_pages=5):
        page_text = soup.get_text(" ", strip=True)
        if page_disallows_marketing(page_text):
            continue
        
        # Check if this page suggests automotive business
        if is_automotive_business(page_text):
            automotive_business = True

        # Collect emails from this page
        page_emails = [e for e in extract_emails(soup, page_text) if not is_suppressed(e, suppression)]
        page_emails = [e for e in page_emails if validate_email_for_outreach(e, strict_mx_check=False)]
        all_emails.update(page_emails)

        # Collect phones from this page
        page_phones = extract_phones(soup, page_text)
        all_phones.update(page_phones)

        # Collect business name from this page
        business_name, _address = extract_business_info_from_jsonld(soup)
        if business_name:
            business_names.add(business_name)
        
        page_urls.append(page_url)

    # Skip if not an automotive business
    if not automotive_business:
        print(f"    Skipping non-automotive business: {domain}")
        return []

    # If no useful data found, skip this domain
    if not all_emails and not all_phones and not business_names:
        return []

    # Create single row for this domain with combined data
    combined_emails = "; ".join(sorted(all_emails)) if all_emails else ""
    # Limit to max 3 phone numbers for diversity
    limited_phones = sorted(all_phones)[:3] if all_phones else []
    combined_phones = "; ".join(limited_phones)
    combined_business_name = "; ".join(sorted(business_names)) if business_names else ""
    main_page_url = page_urls[0] if page_urls else link

    return [{
        "service": service,
        "city": city,
        "rank": rank_str,
        "domain": domain,
        "page_url_found": main_page_url,
        "business_name": combined_business_name,
        "email": combined_emails,
        "phone": combined_phones,
    }]


def run_pipeline(
    provider: BaseSearchProvider,
    services: List[str],
    cities: List[str],
    site_filter: Optional[str],
    start_page: int,
    end_page: int,
    output_csv: str,
    max_per_city: int = 40,
) -> None:
    suppression = load_suppression_list()

    with open(output_csv, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=[
                "service",
                "city",
                "rank",
                "domain",
                "page_url_found",
                "business_name",
                "email",
                "phone",
            ],
        )
        writer.writeheader()

        for city in cities:
            for service in services:
                query = build_query(service, city, site_filter)
                print(f"\nSearching: {query}")
                results = collect_results_for_pages(query, provider, start_page, end_page)
                print(f"Found {len(results)} search results")
                results = dedupe_by_domain(results)
                print(f"After deduplication: {len(results)} unique domains")
                results = results[:max_per_city]
                print(f"Processing {len(results)} results...")
                
                rows_written = 0
                for i, r in enumerate(results, 1):
                    print(f"  [{i}/{len(results)}] Processing: {r.get('link', 'Unknown URL')}")
                    rows = process_result(r, service, city, suppression)
                    for row in rows:
                        writer.writerow(row)
                        rows_written += 1
                
                # Force write to disk after each city/service combination
                f.flush()
                print(f"Wrote {rows_written} rows for {service} in {city} (saved to disk)")
