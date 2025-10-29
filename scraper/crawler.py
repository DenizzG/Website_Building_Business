from typing import List, Set, Tuple
from urllib.parse import urljoin, urlparse

from bs4 import BeautifulSoup

from .util import polite_get, is_same_registered_domain


def candidate_paths() -> List[str]:
    return ["/", "/contact", "/contact-us", "/about", "/about-us"]


def discover_header_links(base_url: str, soup: BeautifulSoup) -> Set[str]:
    links: Set[str] = set()
    header_sections = soup.select("header, nav, [class*=\"header\"], [class*=\"nav\"]")
    for section in header_sections:
        for a in section.select("a[href]"):
            href = a.get("href", "").strip()
            if not href:
                continue
            text = (a.get_text() or "").lower()
            # Restrict to contact/help/support related links
            href_l = href.lower()
            keywords_href = [
                "contact",
                "contact-us",
                "get-in-touch",
                "enquiry",
                "enquiries",
                "help",
                "support",
                "customer-support",
                "customer-service",
                "faq",
            ]
            keywords_text = [
                "contact",
                "contact us",
                "get in touch",
                "enquiry",
                "enquiries",
                "help",
                "support",
                "customer support",
                "customer service",
                "faq",
            ]
            if any(k in href_l for k in keywords_href) or any(k in text for k in keywords_text):
                full = urljoin(base_url, href)
                if is_same_registered_domain(base_url, full):
                    links.add(full)
    return links


def discover_footer_links(base_url: str, soup: BeautifulSoup) -> Set[str]:
    links: Set[str] = set()
    for a in soup.select("a[href]"):
        href = a.get("href", "").strip()
        if not href:
            continue
        text = (a.get_text() or "").lower()
        if any(k in href.lower() for k in ["contact", "about", "service", "repair", "automotive", "auto"]) or any(k in text for k in ["contact", "about", "service"]):
            full = urljoin(base_url, href)
            if is_same_registered_domain(base_url, full):
                links.add(full)
    return links


def crawl_site(start_url: str, max_pages: int = 5) -> List[Tuple[str, BeautifulSoup]]:
    """Crawl homepage first, then header-linked contact/help/support pages."""
    visited: Set[str] = set()
    to_visit: List[str] = []

    parsed = urlparse(start_url)
    base_origin = f"{parsed.scheme}://{parsed.netloc}"

    # Fetch homepage and include it for scanning (emails often on landing page)
    home_resp = polite_get(base_origin + "/")
    if not home_resp or not home_resp.content:
        return []
    home_soup = BeautifulSoup(home_resp.content, "lxml")
    results: List[Tuple[str, BeautifulSoup]] = []
    results.append((base_origin + "/", home_soup))
    if len(results) >= max_pages:
        return results
    header_contact_links = list(discover_header_links(base_origin, home_soup))
    to_visit.extend(header_contact_links)

    while to_visit and len(results) < max_pages:
        url = to_visit.pop(0)
        if url in visited:
            continue
        visited.add(url)
        resp = polite_get(url)
        if not resp or not resp.content:
            continue
        soup = BeautifulSoup(resp.content, "lxml")
        results.append((url, soup))
        # Do not expand to footer or other pages; keep scope to header-linked contact pages only

    return results
