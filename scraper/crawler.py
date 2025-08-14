from typing import List, Set, Tuple
from urllib.parse import urljoin, urlparse

from bs4 import BeautifulSoup

from .util import polite_get, is_same_registered_domain


def candidate_paths() -> List[str]:
    return ["/", "/contact", "/contact-us", "/about", "/about-us"]


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
    visited: Set[str] = set()
    to_visit: List[str] = []

    parsed = urlparse(start_url)
    base_origin = f"{parsed.scheme}://{parsed.netloc}"

    # Seed with common paths
    for p in candidate_paths():
        to_visit.append(urljoin(base_origin, p))

    results: List[Tuple[str, BeautifulSoup]] = []

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
        # harvest footer-like links from this page
        for link in discover_footer_links(url, soup):
            if link not in visited and link not in to_visit and len(results) + len(to_visit) < max_pages:
                to_visit.append(link)

    return results
