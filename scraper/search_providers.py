import os
from typing import Dict, List, Optional

import requests
from dotenv import load_dotenv

load_dotenv()

Result = Dict[str, str]


class BaseSearchProvider:
    def search(self, query: str, start_index: int) -> List[Result]:
        raise NotImplementedError


class GoogleCSEProvider(BaseSearchProvider):
    def __init__(self) -> None:
        self.api_key = os.getenv("GOOGLE_API_KEY")
        self.cse_id = os.getenv("GOOGLE_CSE_ID")
        if not self.api_key or not self.cse_id:
            raise RuntimeError("GOOGLE_API_KEY and GOOGLE_CSE_ID must be set for CSE provider")

    def search(self, query: str, start_index: int) -> List[Result]:
        params = {
            "key": self.api_key,
            "cx": self.cse_id,
            "q": query,
            "start": start_index,
            "num": 10,
        }
        try:
            r = requests.get("https://www.googleapis.com/customsearch/v1", params=params, timeout=20)
            if r.status_code == 400:
                print(f"Bad Request (400) for query: {query}")
                print(f"Response: {r.text}")
                return []
            elif r.status_code == 403:
                print(f"Quota exceeded (403) or invalid API key for query: {query}")
                print(f"Response: {r.text}")
                return []
            r.raise_for_status()
            data = r.json()
            items = data.get("items", [])
            results: List[Result] = []
            for item in items:
                link = item.get("link")
                title = item.get("title")
                snippet = item.get("snippet")
                if not link:
                    continue
                results.append({"link": link, "title": title or "", "snippet": snippet or ""})
            return results
        except requests.exceptions.RequestException as e:
            print(f"Search API error for query '{query}': {e}")
            return []


class SerpApiProvider(BaseSearchProvider):
    def __init__(self) -> None:
        self.api_key = os.getenv("SERPAPI_KEY")
        if not self.api_key:
            raise RuntimeError("SERPAPI_KEY must be set for SerpAPI provider")

    def search(self, query: str, start_index: int) -> List[Result]:
        # start_index is 1-based; SerpAPI for Google supports 'start' offset (0,10,20,...)
        start_offset = max(0, start_index - 1)
        params = {
            "engine": "google",
            "q": query,
            "start": start_offset,
            "num": 10,
            "api_key": self.api_key,
        }
        r = requests.get("https://serpapi.com/search.json", params=params, timeout=20)
        r.raise_for_status()
        data = r.json()
        results: List[Result] = []
        for item in data.get("organic_results", []):
            link = item.get("link")
            title = item.get("title") or ""
            snippet = item.get("snippet") or ""
            if not link:
                continue
            results.append({"link": link, "title": title, "snippet": snippet})
        return results


def get_provider(name: Optional[str]) -> BaseSearchProvider:
    name = (name or os.getenv("SEARCH_PROVIDER", "cse")).strip().lower()
    if name == "cse":
        return GoogleCSEProvider()
    if name == "serpapi":
        return SerpApiProvider()
    raise RuntimeError(f"Unknown search provider: {name}")


def collect_results_for_pages(query: str, provider: BaseSearchProvider, start_page: int = 3, end_page: int = 5) -> List[Dict]:
    # Google pages are 10 results each; start index is 1-based
    results: List[Dict] = []
    rank_counter = 1
    for page in range(start_page, end_page + 1):
        start_index = (page - 1) * 10 + 1
        page_results = provider.search(query, start_index)
        for r in page_results:
            r_copy = dict(r)
            r_copy["rank"] = str((page - 1) * 10 + rank_counter)
            results.append(r_copy)
            rank_counter += 1
        rank_counter = 1  # reset within page ranks
    return results
